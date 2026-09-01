"""
FetchDocTextTool -- reads the full text body of a real Google Doc via
zeocore's real zeo_core.integrations.google.docs.GoogleDocsService (a real
OAuth installed-app flow, not a mocked/stubbed call).

Follows the exact IntegrationEnabledMixin pattern
apps/data_cleaning/src/data_cleaning/drive_tools.py demonstrates for Google
Drive: the Google Docs service is resolved from ctx.services (runner-
provided), never constructed by the tool itself. If no "google_docs"
service was wired into ctx.services, this tool returns a
CapabilityResult.skip -- not an error -- so a caller who hasn't set up real
credentials still gets a clear, typed, non-crashing outcome (see
apps/doc_to_bluesky/README.md for how to actually wire a real
GoogleDocsService).

VERIFIED (this app has never been run against live credentials -- see
README): GoogleDocsService.get_document_text(document_id) ->
IntegrationResult[str], confirmed against the installed zeocore package by
inspect.signature. When no config file exists at any of the integration's
default search locations, .initialize() and .get_document_text() both
return success=False with error exactly "Configuration file not found in
default locations." -- no traceback, no crash, confirmed live from a fresh
directory with zero credentials.
"""

from __future__ import annotations

from pydantic import BaseModel
from zeo_core.contracts import CapabilityResult
from zeo_core.integrations.google.docs import GoogleDocsService
from zeo_core.tools import BaseZeoTool, IntegrationEnabledMixin, ToolContext


class FetchDocTextRequest(BaseModel):
    """
    Args:
        document_id: The Google Doc's document ID (the long id in a Doc's
            URL, e.g. https://docs.google.com/document/d/<document_id>/edit).
    """

    document_id: str


class FetchDocTextResponse(BaseModel):
    """Response payload carried inside CapabilityResult.data on success."""

    document_id: str
    text: str


class FetchDocTextTool(IntegrationEnabledMixin, BaseZeoTool):
    """
    Fetches the full text body of a real Google Doc via zeocore's real
    GoogleDocsService.get_document_text.

    Typical use in this app: fetch a Doc's text, then hand the returned
    text straight to PostToBlueskyTool -- see run_demo.py for the full,
    real, wired example (against a fresh-directory config error, since no
    real credentials exist on this machine -- see README "Never run against
    live credentials").
    """

    name = "fetch_doc_text"
    version = "1.0.0"

    def run(
        self, request: FetchDocTextRequest, ctx: ToolContext
    ) -> CapabilityResult[FetchDocTextResponse]:
        logger = ctx.require_logger()

        docs = self.get_service("google_docs", ctx, expected_type=GoogleDocsService)
        if docs is None:
            if logger is not None:
                logger.info(
                    f"[{self.name}] no 'google_docs' service was provided in "
                    "ctx.services -- skipping fetch. This is the expected "
                    "outcome for anyone running this demo without real "
                    "Google credentials; see README.md to wire a real "
                    "GoogleDocsService for the real-integration path."
                )
            return CapabilityResult.skip(
                reason=(
                    "No 'google_docs' service wired into ctx.services -- "
                    "real Google credentials are required for this capability. "
                    "See README.md."
                ),
                code="ZEO_SKIP_NO_DOCS_SERVICE",
            )

        result = docs.get_document_text(request.document_id)

        if not result.success:
            return CapabilityResult.fail(
                msg=f"Failed to fetch text for document {request.document_id}: "
                f"{result.error}",
                code="ZEO_IO_DOCS_FETCH_FAILED",
            )

        text = result.content
        if text is None:
            # get_document_text's own IntegrationResult contract returns
            # content=the document's text on every success=True result; a
            # None here would mean the integration violated its own
            # contract. Defensive, not an expected runtime path (same
            # posture drive_tools.py's DownloadFromDriveTool takes for its
            # analogous local_path None-narrowing check).
            return CapabilityResult.fail(
                msg="Google Docs reported success but returned no text",
                code="ZEO_IO_DOCS_FETCH_FAILED",
            )

        if logger is not None:
            logger.info(
                f"[{self.name}] fetched {len(text)} chars from document "
                f"{request.document_id}"
            )

        return CapabilityResult.ok(
            data=FetchDocTextResponse(document_id=request.document_id, text=text),
            msg=f"Fetched text from document {request.document_id}",
            metadata={"tool": f"{self.name} v{self.version}"},
        )
