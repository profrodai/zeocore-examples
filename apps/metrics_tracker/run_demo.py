"""
Runnable end-to-end demo of the metrics_tracker app's zeocore tool, against
plausible fake weekly data. Requires zero real credentials.

    python run_demo.py

Runs:
  1. Eight weeks of a plausible fake automation-progression submission
     (accepted, real CapabilityResult output printed each week).
  2. Two bad-input cases that reproduce the ORIGINAL code's real bug class,
     shown to be genuinely REJECTED by pydantic validation now, not merely
     "happening" not to crash.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from pydantic import ValidationError
from zeo_core.tools import ToolContext

from metrics_tracker.submit_tool import SubmitWeeklyMetricsTool, WeeklyMetricsRequest

# Eight weeks of plausible fake progression: automation index climbing from
# ~20% toward ~75%, hours worked drifting down, clients growing, recurring
# revenue share climbing. All self-reported ratios/counts -- no PII, no real
# business figures, matching the original repo's own "Privacy First" design.
FAKE_WEEKS = [
    dict(week_number=1, total_hours_worked=45.0, automated_hours=9.0, active_clients=6,
         revenue_ratio_to_baseline=1.0, recurring_revenue_percentage=10.0,
         what_i_automated_this_week="Set up intake form automation",
         biggest_bottleneck_now="Manual client onboarding calls"),
    dict(week_number=2, total_hours_worked=44.0, automated_hours=12.0, active_clients=6,
         revenue_ratio_to_baseline=1.02, recurring_revenue_percentage=12.0,
         what_i_automated_this_week="Automated weekly status emails",
         biggest_bottleneck_now="Invoice generation still manual"),
    dict(week_number=3, total_hours_worked=42.0, automated_hours=16.0, active_clients=7,
         revenue_ratio_to_baseline=1.08, recurring_revenue_percentage=18.0,
         what_i_automated_this_week="Invoice generation via template",
         biggest_bottleneck_now="Reporting dashboards built by hand"),
    dict(week_number=4, total_hours_worked=41.0, automated_hours=20.0, active_clients=7,
         revenue_ratio_to_baseline=1.10, recurring_revenue_percentage=22.0,
         what_i_automated_this_week="Basic reporting dashboard automation",
         biggest_bottleneck_now="Content review cycle"),
    dict(week_number=5, total_hours_worked=40.0, automated_hours=24.0, active_clients=8,
         revenue_ratio_to_baseline=1.15, recurring_revenue_percentage=28.0,
         what_i_automated_this_week="Content review checklist bot",
         biggest_bottleneck_now="Client Q&A response time"),
    dict(week_number=6, total_hours_worked=39.0, automated_hours=27.0, active_clients=8,
         revenue_ratio_to_baseline=1.20, recurring_revenue_percentage=34.0,
         what_i_automated_this_week="FAQ auto-responder for common questions",
         biggest_bottleneck_now="New client contract drafting"),
    dict(week_number=7, total_hours_worked=38.0, automated_hours=29.0, active_clients=9,
         revenue_ratio_to_baseline=1.24, recurring_revenue_percentage=41.0,
         what_i_automated_this_week="Contract template generation",
         biggest_bottleneck_now="Manual QA pass before delivery"),
    dict(week_number=8, total_hours_worked=37.0, automated_hours=28.0, active_clients=9,
         revenue_ratio_to_baseline=1.27, recurring_revenue_percentage=47.0,
         what_i_automated_this_week="Automated QA checklist pass",
         biggest_bottleneck_now="Sales follow-up scheduling"),
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

    with tempfile.TemporaryDirectory(prefix="zeo_metrics_tracker_demo_") as tmp:
        db_path = str(Path(tmp) / "metrics_demo.db")

        tool = SubmitWeeklyMetricsTool(db_path=db_path)
        ctx = ToolContext(
            run_id="metrics-demo-run",
            tool_name="submit_weekly_metrics",
            tool_version="1.0.0",
            logger=logging.getLogger("submit_weekly_metrics"),
            fs=None,
            work_dir=tmp,
            output_dir=tmp,
        )

        print("=" * 70)
        print("1. Eight weeks of plausible fake progression (all accepted)")
        print("=" * 70)
        for week in FAKE_WEEKS:
            request = WeeklyMetricsRequest(**week)
            result = tool.run(request, ctx)
            assert result.data is not None
            d = result.data
            print(
                f"week {d.week_number}: automation_index={d.automation_index:.1f}%  "
                f"manual_hours={d.manual_hours:.1f}  "
                f"revenue_efficiency={d.revenue_efficiency_multiple:.2f}x  "
                f"client_capacity={d.client_capacity_score:.2f}x"
            )

        print()
        print("=" * 70)
        print("2. Bad input #1: total_hours_worked=0 (original: ZeroDivisionError)")
        print("=" * 70)
        try:
            WeeklyMetricsRequest(
                week_number=9,
                total_hours_worked=0.0,
                automated_hours=0.0,
                active_clients=9,
                revenue_ratio_to_baseline=1.3,
                recurring_revenue_percentage=48.0,
                what_i_automated_this_week="n/a",
                biggest_bottleneck_now="n/a",
            )
            print("UNEXPECTED: request was accepted (should have been rejected)")
        except ValidationError as e:
            print("REJECTED as expected -- pydantic ValidationError:")
            print(f"  {e.errors()[0]['msg']}")

        print()
        print("=" * 70)
        print("3. Bad input #2: automated_hours > total_hours_worked")
        print("   (original: silently accepted, manual_hours=-40, automation_index=500%)")
        print("=" * 70)
        try:
            WeeklyMetricsRequest(
                week_number=9,
                total_hours_worked=10.0,
                automated_hours=50.0,
                active_clients=9,
                revenue_ratio_to_baseline=1.3,
                recurring_revenue_percentage=48.0,
                what_i_automated_this_week="n/a",
                biggest_bottleneck_now="n/a",
            )
            print("UNEXPECTED: request was accepted (should have been rejected)")
        except ValidationError as e:
            print("REJECTED as expected -- pydantic ValidationError:")
            print(f"  {e.errors()[0]['msg']}")

        print()
        print(f"Demo database written to: {db_path}")


if __name__ == "__main__":
    main()
