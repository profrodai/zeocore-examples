"""
DownloadFromDriveTool -- the real, integration-backed capability round 2
adds (RULING-280 / CHARTER-03). Downloads a CSV file from a real Google
Drive file into a local path, using zeocore's real
zeo_core.integrations.google.drive.GoogleDriveService (a real OAuth
installed-app flow, not a mocked/stubbed call).

This is additive, not a replacement: CleanContactsTool/CleanAccountsTool
(pipeline_tools.py) are completely unchanged. This tool's only job is to
put a real file at a local path; the existing tools then read that path
exactly as they already do for the dummy-data demo. That composition is
the whole design -- downloading from Drive is a new *source* for the
same, already-proven cleaning pipeline, not a new pipeline.

Follows the exact IntegrationEnabledMixin pattern zeocore's own
examples/toolkit_usage.py demonstrates: the Google Drive service is
resolved from ctx.services (runner-provided), never constructed by the
tool itself. If no "google_drive" service was wired into ctx.services,
this tool returns a CapabilityResult.skip -- not an error -- so a caller
who hasn't set up real credentials still gets a clear, typed, non-crashing
outcome (see SETUP.md for how to actually wire a real GoogleDriveService).
"""

from __future__ import annotations

from pydantic import BaseModel
from zeo_core.contracts import CapabilityResult
from zeo_core.integrations.google.drive import GoogleDriveService
from zeo_core.tools import BaseZeoTool, IntegrationEnabledMixin, ToolContext


class DownloadFromDriveRequest(BaseModel):
    """
    Args:
        file_id: The Google Drive file ID of the CSV to download (the long
            id in a Drive file's URL, e.g.
            https://drive.google.com/file/d/<file_id>/view).
        local_path: Optional local destination path. If omitted,
            GoogleDriveService downloads to a fresh temp directory under
            the file's own Drive name.
    """

    file_id: str
    local_path: str | None = None


class DownloadFromDriveResponse(BaseModel):
    """Response payload carried inside CapabilityResult.data on success."""

    local_path: str
    file_id: str


class DownloadFromDriveTool(IntegrationEnabledMixin, BaseZeoTool):
    """
    Downloads a real file from Google Drive to a local path via zeocore's
    real GoogleDriveService.download_file.

    Typical use in this app: download a messy contacts/accounts CSV that
    lives in a real (test/dummy) Google Drive folder, then hand the
    returned local_path straight to CleanContactsTool/CleanAccountsTool
    unchanged -- see run_demo_drive.py for the full, real, wired example.
    """

    name = "download_from_drive"
    version = "1.0.0"

    def run(
        self, request: DownloadFromDriveRequest, ctx: ToolContext
    ) -> CapabilityResult[DownloadFromDriveResponse]:
        logger = ctx.require_logger()

        drive = self.get_service("google_drive", ctx, expected_type=GoogleDriveService)
        if drive is None:
            if logger is not None:
                logger.info(
                    f"[{self.name}] no 'google_drive' service was provided in "
                    "ctx.services -- skipping download. This is the expected "
                    "outcome for anyone running the dummy-data demo without "
                    "real Google credentials; see SETUP.md to wire a real "
                    "GoogleDriveService for the real-integration path."
                )
            return CapabilityResult.skip(
                reason=(
                    "No 'google_drive' service wired into ctx.services -- "
                    "real Drive credentials are required for this capability. "
                    "See SETUP.md."
                ),
                code="QC_SKIP_NO_DRIVE_SERVICE",
            )

        result = drive.download_file(
            remote_id=request.file_id, local_path=request.local_path
        )

        if not result.success:
            return CapabilityResult.fail(
                msg=f"Failed to download file {request.file_id} from Google Drive: "
                f"{result.error}",
                code="QC_IO_DRIVE_DOWNLOAD_FAILED",
            )

        local_path = result.content
        if local_path is None:
            # download_file's own IntegrationResult contract returns content=
            # the local path on every success=True result; a None here would
            # mean the integration violated its own contract. Defensive, not
            # an expected runtime path (same posture GoogleDriveService's own
            # source takes for its analogous auth_provider/config_provider
            # None-narrowing checks).
            return CapabilityResult.fail(
                msg="Google Drive reported success but returned no local path",
                code="QC_IO_DRIVE_DOWNLOAD_FAILED",
            )

        if logger is not None:
            logger.info(f"[{self.name}] downloaded {request.file_id} -> {local_path}")

        return CapabilityResult.ok(
            data=DownloadFromDriveResponse(local_path=local_path, file_id=request.file_id),
            msg=f"Downloaded file to {local_path}",
            metadata={"tool": f"{self.name} v{self.version}"},
        )
