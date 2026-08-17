"""
DuckDB storage layer, ported from business-transformation-tracker's own
billion_tracker.py (init_database, the INSERT OR REPLACE statement, and
get_metrics_df) -- schema and table name unchanged from the original.
"""

from __future__ import annotations

from datetime import date

import duckdb

TABLE_NAME = "transformation_metrics"


def init_database(db_path: str) -> None:
    """Create the transformation_metrics table if it doesn't exist yet."""
    con = duckdb.connect(db_path)
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            week_number INTEGER PRIMARY KEY,
            submission_date DATE,
            total_hours FLOAT,
            automated_hours FLOAT,
            manual_hours FLOAT,
            active_clients INTEGER,
            revenue_ratio FLOAT,
            recurring_revenue_pct FLOAT,
            automated_this_week TEXT,
            biggest_bottleneck TEXT,
            automation_index FLOAT,
            time_saved_vs_baseline FLOAT,
            revenue_efficiency_multiple FLOAT,
            client_capacity_score FLOAT
        )
    """)
    con.close()


def get_baseline(db_path: str) -> tuple[float, int, float] | None:
    """Fetch week 1's (total_hours, active_clients, revenue_ratio), or None."""
    con = duckdb.connect(db_path)
    row = con.execute(
        f"SELECT total_hours, active_clients, revenue_ratio "
        f"FROM {TABLE_NAME} WHERE week_number = 1"
    ).fetchone()
    con.close()
    return row


def insert_week(db_path: str, values: list) -> None:
    """Insert or replace one week's row. `values` must match the schema's
    14-column order exactly (see init_database)."""
    con = duckdb.connect(db_path)
    con.execute(
        f"INSERT OR REPLACE INTO {TABLE_NAME} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        values,
    )
    con.close()


def fetch_all_weeks(db_path: str) -> list[dict]:
    """All rows, ordered by week_number, as a list of plain dicts."""
    con = duckdb.connect(db_path)
    rows = con.execute(
        f"SELECT * FROM {TABLE_NAME} ORDER BY week_number"
    ).fetchall()
    columns = [d[0] for d in con.description]
    con.close()
    return [dict(zip(columns, row)) for row in rows]


__all__ = ["TABLE_NAME", "init_database", "get_baseline", "insert_week", "fetch_all_weeks", "date"]
