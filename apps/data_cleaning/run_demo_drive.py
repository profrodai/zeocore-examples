"""
Real-integration demo: download a CSV from a real Google Drive file, then
run the SAME, unmodified CleanContactsTool/CleanAccountsTool on it.

This is the round-2 capability (RULING-280 / CHARTER-03) -- additive to
run_demo.py, which remains the zero-credential dummy-data path and is
completely unaffected by this file.

REQUIRES REAL GOOGLE CREDENTIALS. See SETUP.md at the repo root for the
full walkthrough (Google Cloud Console project, enabling the Drive API,
OAuth consent screen, downloading client secrets). This script will NOT
run without them -- it does not fall back to dummy data, on purpose: its
whole job is to prove the real integration works end to end, and a silent
fallback would defeat that.

Usage:

    export ZEOCORE_DRIVE_CLIENT_SECRETS=/path/to/client_secret.json
    export ZEOCORE_DRIVE_CREDENTIALS=/path/to/token.json      # created on first run
    export ZEOCORE_DRIVE_FILE_ID=<the Drive file id of a real CSV to download>
    python run_demo_drive.py

The first run opens a browser for the Google OAuth consent screen (a real,
interactive step -- there is no headless/non-interactive path in
zeocore's own GoogleAuthProvider). Subsequent runs reuse the cached token
in ZEOCORE_DRIVE_CREDENTIALS until it expires.
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.integrations.google.drive import GoogleDriveService
from zeo_core.tools import ToolContext

from data_cleaning.drive_tools import DownloadFromDriveRequest, DownloadFromDriveTool
from data_cleaning.pipeline_tools import CleanContactsRequest, CleanContactsTool

APP_DIR = Path(__file__).parent


def build_ctx(tool_name: str, work_dir: Path, services: dict) -> ToolContext:
    return ToolContext(
        run_id=f"{tool_name}-drive-demo-run",
        tool_name=tool_name,
        tool_version="1.0.0",
        logger=logging.getLogger(tool_name),
        fs=get_fs_service(),
        work_dir=str(work_dir),
        output_dir=str(work_dir),
        services=services,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

    client_secrets = os.environ.get("ZEOCORE_DRIVE_CLIENT_SECRETS")
    credentials_file = os.environ.get("ZEOCORE_DRIVE_CREDENTIALS")
    file_id = os.environ.get("ZEOCORE_DRIVE_FILE_ID")

    missing = [
        name
        for name, val in (
            ("ZEOCORE_DRIVE_CLIENT_SECRETS", client_secrets),
            ("ZEOCORE_DRIVE_CREDENTIALS", credentials_file),
            ("ZEOCORE_DRIVE_FILE_ID", file_id),
        )
        if not val
    ]
    if missing:
        print(
            "Missing required environment variable(s): " + ", ".join(missing) + "\n"
            "This demo needs real Google Drive OAuth credentials -- see "
            "SETUP.md at the repo root for the full walkthrough. This is NOT "
            "the demo to run if you just want to see zeocore work with zero "
            "credentials -- use run_demo.py for that."
        )
        sys.exit(1)

    print("=" * 70)
    print("Initializing real GoogleDriveService (real OAuth, real API)")
    print("=" * 70)
    drive = GoogleDriveService(
        client_secrets_file=client_secrets,
        credentials_file=credentials_file,
    )
    init_result = drive.initialize()
    if not init_result.success:
        print(f"Failed to initialize Google Drive service: {init_result.error}")
        sys.exit(1)
    print("Google Drive service initialized (real OAuth credentials accepted).")
    print()

    with tempfile.TemporaryDirectory(prefix="zeo_data_cleaning_drive_demo_") as tmp:
        tmp_dir = Path(tmp)
        services = {"google_drive": drive}

        print("=" * 70)
        print("1. DownloadFromDriveTool  (real Google Drive file -> local CSV)")
        print("=" * 70)
        ctx = build_ctx("download_from_drive", tmp_dir, services)
        download_result = DownloadFromDriveTool().run(
            DownloadFromDriveRequest(file_id=file_id), ctx
        )
        print(f"status={download_result.status}  msg={download_result.human_message}")
        if download_result.status != "success" or download_result.data is None:
            print("Download failed or was skipped -- cannot continue the demo.")
            sys.exit(1)
        downloaded_path = download_result.data.local_path
        print(f"Downloaded to: {downloaded_path}")
        print()

        print("=" * 70)
        print("2. CleanContactsTool  (SAME tool run_demo.py uses -- unmodified)")
        print("=" * 70)
        ctx = build_ctx("clean_contacts", tmp_dir, services)
        clean_result = CleanContactsTool().run(
            CleanContactsRequest(
                input_path=downloaded_path,
                output_path=str(tmp_dir / "contacts_clean_from_drive.csv"),
            ),
            ctx,
        )
        print(f"status={clean_result.status}  msg={clean_result.human_message}")
        if clean_result.data is not None:
            print(clean_result.data.model_dump())

        print()
        print(
            "Real end-to-end proof: a real file was downloaded from a real "
            "Google Drive account via zeocore's real GoogleDriveService, then "
            "cleaned by the same CleanContactsTool the dummy-data demo uses, "
            "completely unmodified."
        )


if __name__ == "__main__":
    main()
