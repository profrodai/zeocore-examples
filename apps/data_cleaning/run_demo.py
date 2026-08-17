"""
Runnable end-to-end demo of the data_cleaning app's zeocore tools, against
the dummy data shipped in data/. Requires zero real credentials.

    python run_demo.py

Runs all 5 tools (2 pipelines + 3 small utility tools) and prints real
CapabilityResult output for each.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.tools import ToolContext

from data_cleaning.pipeline_tools import (
    CleanAccountsRequest,
    CleanAccountsTool,
    CleanContactsRequest,
    CleanContactsTool,
)
from data_cleaning.small_tools import (
    CleanEmailRequest,
    CleanEmailTool,
    ExtractDomainRequest,
    ExtractDomainTool,
    NormalizeCountryRequest,
    NormalizeCountryTool,
)

APP_DIR = Path(__file__).parent


def build_ctx(tool_name: str, work_dir: Path) -> ToolContext:
    return ToolContext(
        run_id=f"{tool_name}-demo-run",
        tool_name=tool_name,
        tool_version="1.0.0",
        logger=logging.getLogger(tool_name),
        fs=get_fs_service(),
        work_dir=str(work_dir),
        output_dir=str(work_dir),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

    with tempfile.TemporaryDirectory(prefix="zeo_data_cleaning_demo_") as tmp:
        tmp_dir = Path(tmp)

        print("=" * 70)
        print("1. CleanContactsTool  (rebuild of clean_contacts.py)")
        print("=" * 70)
        ctx = build_ctx("clean_contacts", tmp_dir)
        result = CleanContactsTool().run(
            CleanContactsRequest(
                input_path=str(APP_DIR / "data" / "contacts_messy.csv"),
                output_path=str(tmp_dir / "contacts_clean.csv"),
            ),
            ctx,
        )
        print(f"status={result.status}  msg={result.human_message}")
        assert result.data is not None
        print(result.data.model_dump())
        print()

        print("=" * 70)
        print("2. CleanAccountsTool  (rebuild of clean_accounts.py)")
        print("=" * 70)
        ctx = build_ctx("clean_accounts", tmp_dir)
        result2 = CleanAccountsTool().run(
            CleanAccountsRequest(
                input_path=str(APP_DIR / "data" / "accounts_messy.csv"),
                output_path=str(tmp_dir / "accounts_clean.csv"),
            ),
            ctx,
        )
        print(f"status={result2.status}  msg={result2.human_message}")
        assert result2.data is not None
        print(result2.data.model_dump())
        print()

        print("=" * 70)
        print("3. Small tools: clean_email / normalize_country / extract_domain")
        print("=" * 70)
        ctx = build_ctx("clean_email", tmp_dir)
        r = CleanEmailTool().run(CleanEmailRequest(email="  SARAH.DEMO@ACME-DEMO.TEST "), ctx)
        print("clean_email:", r.data.model_dump() if r.data else None)

        ctx = build_ctx("normalize_country", tmp_dir)
        r = NormalizeCountryTool().run(NormalizeCountryRequest(country="uk"), ctx)
        print("normalize_country:", r.data.model_dump() if r.data else None)

        ctx = build_ctx("extract_domain", tmp_dir)
        r = ExtractDomainTool().run(
            ExtractDomainRequest(url="https://www.acme-demo.test/about"), ctx
        )
        print("extract_domain:", r.data.model_dump() if r.data else None)

        print()
        print("Cleaned files written to:", tmp_dir)
        for f in sorted(tmp_dir.glob("*.csv")):
            print(" -", f.name)


if __name__ == "__main__":
    main()
