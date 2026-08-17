"""
Rebuild of business-transformation-tracker's own billion_tracker.py ::
submit_weekly_metrics() as a zeocore BaseZeoTool.

THE REAL BUG THIS FIXES (confirmed by reading the original source and
independently reproducing it before writing this file -- see the app
README's "the bug, reproduced" section for the exact repro):

  manual_hours = total_hours_worked - automated_hours
  automation_index = (automated_hours / total_hours_worked * 100) if total_hours_worked > 0 else 0
  ...
  revenue_efficiency_multiple = (revenue_ratio_to_baseline / total_hours_worked) / (baseline_revenue / baseline_hours)
  client_capacity_score = (active_clients / total_hours_worked) / (baseline_clients / baseline_hours)

Two real, distinct problems in the original:

1. `automation_index`'s own guard (`if total_hours_worked > 0 else 0`) only
   protects THAT one calculation. `revenue_efficiency_multiple` and
   `client_capacity_score` divide by `total_hours_worked` and `baseline_hours`
   with ZERO guard -- a week-1 submission with `total_hours_worked=0`, or any
   later week where `baseline_hours` (week 1's own total_hours) was 0,
   raises a real ZeroDivisionError. Reproduced directly, see README.

2. There is no validation anywhere that `automated_hours <= total_hours_worked`.
   The original silently accepts `automated_hours=50, total_hours_worked=10`,
   producing `manual_hours=-40` (negative) and `automation_index=500%` --
   nonsensical output, accepted and stored without complaint. Also
   reproduced directly, see README.

FIX: WeeklyMetricsRequest (a pydantic BaseModel) validates both problems AT
THE REQUEST BOUNDARY, before any calculation runs -- `total_hours_worked`
and `automated_hours` are constrained to be non-negative and reject
`total_hours_worked <= 0` outright (a real week always has positive hours;
this tool has no "week 1 might be zero" case to accommodate, unlike the
original's own baseline-guard logic which only defends automation_index and
leaves the other two calculations exposed), and a model_validator rejects
`automated_hours > total_hours_worked`. A ValidationError is the correct
outcome for bad input -- not a crash, not a silently-accepted nonsensical
result.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator
from zeo_core.contracts import CapabilityResult
from zeo_core.tools import BaseZeoTool, ToolContext

from metrics_tracker.storage import get_baseline, init_database, insert_week


class WeeklyMetricsRequest(BaseModel):
    """
    Typed replacement for the original's bare positional-argument function
    signature. Field constraints close the original's real bug class at the
    boundary -- see this module's own docstring for exactly which bug and
    how.
    """

    week_number: int = Field(ge=1)
    total_hours_worked: float = Field(
        gt=0,
        description="Must be > 0 -- a week with zero hours worked cannot "
        "produce a meaningful automation/efficiency ratio, and the "
        "original code's unguarded division on this exact value is the "
        "root cause of the ZeroDivisionError this constraint prevents.",
    )
    automated_hours: float = Field(ge=0)
    active_clients: int = Field(ge=0)
    revenue_ratio_to_baseline: float = Field(
        gt=0, description="Ratio to week 1's own baseline, never an absolute figure."
    )
    recurring_revenue_percentage: float = Field(ge=0, le=100)
    what_i_automated_this_week: str = Field(min_length=1)
    biggest_bottleneck_now: str = Field(min_length=1)

    @model_validator(mode="after")
    def automated_hours_cannot_exceed_total(self) -> "WeeklyMetricsRequest":
        if self.automated_hours > self.total_hours_worked:
            raise ValueError(
                f"automated_hours ({self.automated_hours}) cannot exceed "
                f"total_hours_worked ({self.total_hours_worked}) -- the "
                "original code accepted this silently and produced a "
                "negative manual_hours / automation_index over 100%."
            )
        return self


class WeeklyMetricsResponse(BaseModel):
    """Typed replacement for the original's print-only return (None)."""

    week_number: int
    manual_hours: float
    automation_index: float
    time_saved_vs_baseline: float
    revenue_efficiency_multiple: float
    client_capacity_score: float


class SubmitWeeklyMetricsTool(BaseZeoTool):
    """Rebuild of business-transformation-tracker's submit_weekly_metrics()."""

    name = "submit_weekly_metrics"
    version = "1.0.0"

    def __init__(self, db_path: str, name: str | None = None, version: str | None = None) -> None:
        super().__init__(name=name, version=version)
        self._db_path = db_path
        init_database(db_path)

    def run(
        self, request: WeeklyMetricsRequest, ctx: ToolContext
    ) -> CapabilityResult[WeeklyMetricsResponse]:
        logger = ctx.require_logger()

        manual_hours = request.total_hours_worked - request.automated_hours
        automation_index = request.automated_hours / request.total_hours_worked * 100

        baseline = get_baseline(self._db_path)

        if baseline and request.week_number > 1:
            baseline_hours, baseline_clients, baseline_revenue = baseline
            # baseline_hours is guaranteed > 0 here: it can only have been
            # written by THIS tool's own week-1 submission, and
            # total_hours_worked's field constraint (gt=0) makes a
            # baseline_hours<=0 row unreachable through this tool -- the
            # exact gap the original code left open.
            time_saved = baseline_hours - request.total_hours_worked
            revenue_efficiency_multiple = (
                request.revenue_ratio_to_baseline / request.total_hours_worked
            ) / (baseline_revenue / baseline_hours)
            client_capacity_score = (request.active_clients / request.total_hours_worked) / (
                baseline_clients / baseline_hours
            )
        else:
            time_saved = 0.0
            revenue_efficiency_multiple = 1.0
            client_capacity_score = 1.0

        insert_week(
            self._db_path,
            [
                request.week_number,
                datetime.now().date(),
                request.total_hours_worked,
                request.automated_hours,
                manual_hours,
                request.active_clients,
                request.revenue_ratio_to_baseline,
                request.recurring_revenue_percentage,
                request.what_i_automated_this_week,
                request.biggest_bottleneck_now,
                automation_index,
                time_saved,
                revenue_efficiency_multiple,
                client_capacity_score,
            ],
        )

        if logger is not None:
            logger.info(
                f"[{self.name}] week {request.week_number} submitted, "
                f"automation_index={automation_index:.1f}%"
            )

        return CapabilityResult.ok(
            data=WeeklyMetricsResponse(
                week_number=request.week_number,
                manual_hours=manual_hours,
                automation_index=automation_index,
                time_saved_vs_baseline=time_saved,
                revenue_efficiency_multiple=revenue_efficiency_multiple,
                client_capacity_score=client_capacity_score,
            ),
            msg=f"Week {request.week_number} metrics submitted",
            metadata={"tool": f"{self.name} v{self.version}"},
        )
