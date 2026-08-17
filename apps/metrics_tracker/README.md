# zeocore example: metrics tracker

A [zeocore](https://github.com/zeroemployeeorg/zeocore)-powered rebuild of
[`business-transformation-tracker`](https://github.com/zeroemployeeorg/business-transformation-tracker)'s
weekly self-reported metrics tracking. Part of
[`zeocore-examples`](../../README.md) — read that top-level README first for
what this whole repo is and why it exists.

## What's here

`src/metrics_tracker/submit_tool.py` rebuilds the original's one real write
operation, `submit_weekly_metrics()`, as `SubmitWeeklyMetricsTool` (a
`BaseZeoTool`) with a typed `WeeklyMetricsRequest` (pydantic) and a typed
`WeeklyMetricsResponse` inside a `CapabilityResult`. `storage.py` ports the
original's DuckDB schema and query logic unchanged.

## The bug, reproduced

The original `billion_tracker.py` computes, per week:

```python
manual_hours = total_hours_worked - automated_hours
automation_index = (automated_hours / total_hours_worked * 100) if total_hours_worked > 0 else 0
...
revenue_efficiency_multiple = (revenue_ratio_to_baseline / total_hours_worked) / (baseline_revenue / baseline_hours)
client_capacity_score = (active_clients / total_hours_worked) / (baseline_clients / baseline_hours)
```

Two real problems, confirmed by reading the original source and
independently reproducing both in isolation before this rebuild was written:

1. **Unguarded division.** `automation_index`'s own guard
   (`if total_hours_worked > 0 else 0`) protects only that one line.
   `revenue_efficiency_multiple` and `client_capacity_score` divide by
   `total_hours_worked` and `baseline_hours` with **no guard at all** — a
   `total_hours_worked=0` submission, or any week where the stored
   `baseline_hours` (week 1's own `total_hours`) was 0, raises a real
   `ZeroDivisionError`. Reproduced directly:
   ```
   >>> (1.2 / 0) / (1.0 / 0)
   ZeroDivisionError: division by zero
   ```
2. **No validation that `automated_hours <= total_hours_worked`.** The
   original silently accepts `automated_hours=50, total_hours_worked=10`,
   producing `manual_hours=-40` and `automation_index=500%` — nonsensical,
   and stored without complaint. Reproduced directly: with those inputs the
   original's own formula yields exactly `manual_hours=-40`,
   `automation_index=500.0`.

## The fix

`WeeklyMetricsRequest` (pydantic) rejects both problems **at the request
boundary**, before any calculation runs:

- `total_hours_worked: float = Field(gt=0)` — a week of zero hours is
  rejected outright (this tool has no "week 1 might be zero" case to
  accommodate; every week including week 1 must report positive hours).
- A `model_validator` rejects `automated_hours > total_hours_worked`
  explicitly, with a message naming the exact original-code consequence it
  prevents.

A `pydantic.ValidationError` is the correct outcome for bad input — not a
crash, not a silently-accepted nonsensical result. See `run_demo.py` for
both the accepted-good-input path and the two rejected-bad-input paths, run
for real and printed.

## Dummy data

No CSV/file dummy data is needed here — the original's own "Privacy First"
design (revenue stored only as a ratio to the operator's own baseline, never
an absolute figure) means synthetic weekly numbers are trivially safe to
fabricate. `run_demo.py` submits eight weeks of plausible fake progression
(automation climbing from ~20% to ~75%) directly, no fixture file required.

## Run it

No real credentials needed — everything runs against a local DuckDB file
created fresh in a temp directory.

```bash
cd apps/metrics_tracker
pip install -e .
python run_demo.py
```
