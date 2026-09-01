"""
PostToBlueskyTool -- posts real text to a real Bluesky account via zeocore's
real zeo_core.integrations.social.bluesky.BlueskyIntegration (real
app-password auth against the AT Protocol, not a mocked/stubbed call).

Follows the exact IntegrationEnabledMixin pattern
apps/data_cleaning/src/data_cleaning/drive_tools.py demonstrates: the
Bluesky service is resolved from ctx.services (runner-provided), never
constructed by the tool itself. If no "bluesky" service was wired into
ctx.services, this tool returns a CapabilityResult.skip -- not an error --
so a caller who hasn't set up real credentials still gets a clear, typed,
non-crashing outcome (see apps/doc_to_bluesky/README.md for how to
actually wire a real BlueskyIntegration).

THE BYTE-OFFSET HAZARD (read before building a links/mentions list by
hand): a Bluesky rich-text facet's index is a UTF-8 BYTE offset, never a
character offset. zeo_core.integrations.social.bluesky.facets.LinkSpan/
MentionSpan take the plain-text substring and its target (a URL, or a
resolved DID) -- BlueskyIntegration.post() computes the byte offsets for
you. Passing a hand-computed character offset instead silently mangles the
post's link placement with no error raised; this is the one real wrinkle
the library's own facets.py module docstring names explicitly (RULING-409
s6c/6b). This tool never computes an offset itself -- it only ever builds
LinkSpan objects from substrings and lets post() do the byte-accurate
placement.

VERIFIED (this app has never been run against live credentials -- see
README): BlueskyIntegration.post(text, links, mentions) ->
IntegrationResult[dict], confirmed against the installed zeocore package by
inspect.signature. Constructed with zero config and zero credentials,
.initialize() returns success=False with error "Failed to authenticate
Bluesky: No Bluesky identifier/app_password provided" -- an AUTH error,
NOT the same "Configuration file not found in default locations." error
Google Docs returns; confirmed live. A subsequent .post() call correctly
refuses with "Bluesky integration is not initialized. Call initialize()
first." rather than raising.
"""

from __future__ import annotations

from pydantic import BaseModel
from zeo_core.contracts import CapabilityResult
from zeo_core.integrations.social.bluesky import BlueskyIntegration
from zeo_core.integrations.social.bluesky.facets import LinkSpan
from zeo_core.tools import BaseZeoTool, IntegrationEnabledMixin, ToolContext


class PostToBlueskyRequest(BaseModel):
    """
    Args:
        text: The full post text (Bluesky's own 300-grapheme limit is
            enforced server-side, not by this tool).
        link_text: Optional exact substring of `text` to annotate as a
            link facet (e.g. "example.com"). Must appear verbatim in
            `text`, or the library silently skips the facet (see facets.py
            compute_facets' own documented degrade-to-plain-text behavior).
        link_uri: The link facet's target URL. Required if link_text is
            given; ignored otherwise.
    """

    text: str
    link_text: str | None = None
    link_uri: str | None = None


class PostToBlueskyResponse(BaseModel):
    """Response payload carried inside CapabilityResult.data on success."""

    text: str
    raw_result: dict[str, object]


class PostToBlueskyTool(IntegrationEnabledMixin, BaseZeoTool):
    """
    Posts real text to a real Bluesky account via zeocore's real
    BlueskyIntegration.post.

    Typical use in this app: take the text FetchDocTextTool returned from a
    real Google Doc and post it (or a summary of it) to Bluesky, optionally
    linking back to the source Doc -- see run_demo.py for the full, real,
    wired example (against a fresh, credential-free auth error, since no
    real credentials exist on this machine -- see README "Never run
    against live credentials").
    """

    name = "post_to_bluesky"
    version = "1.0.0"

    def run(
        self, request: PostToBlueskyRequest, ctx: ToolContext
    ) -> CapabilityResult[PostToBlueskyResponse]:
        logger = ctx.require_logger()

        bluesky = self.get_service("bluesky", ctx, expected_type=BlueskyIntegration)
        if bluesky is None:
            if logger is not None:
                logger.info(
                    f"[{self.name}] no 'bluesky' service was provided in "
                    "ctx.services -- skipping post. This is the expected "
                    "outcome for anyone running this demo without real "
                    "Bluesky credentials; see README.md to wire a real "
                    "BlueskyIntegration for the real-integration path."
                )
            return CapabilityResult.skip(
                reason=(
                    "No 'bluesky' service wired into ctx.services -- real "
                    "Bluesky credentials are required for this capability. "
                    "See README.md."
                ),
                code="ZEO_SKIP_NO_BLUESKY_SERVICE",
            )

        links: list[LinkSpan] | None = None
        if request.link_text is not None and request.link_uri is not None:
            links = [LinkSpan(text=request.link_text, uri=request.link_uri)]

        result = bluesky.post(request.text, links=links)

        if not result.success:
            return CapabilityResult.fail(
                msg=f"Failed to post to Bluesky: {result.error}",
                code="ZEO_IO_BLUESKY_POST_FAILED",
            )

        raw = result.content
        if raw is None:
            # post()'s own IntegrationResult contract returns content=the
            # raw API response dict on every success=True result; a None
            # here would mean the integration violated its own contract.
            # Defensive, not an expected runtime path (same posture
            # drive_tools.py's DownloadFromDriveTool takes for its
            # analogous local_path None-narrowing check).
            return CapabilityResult.fail(
                msg="Bluesky reported success but returned no result payload",
                code="ZEO_IO_BLUESKY_POST_FAILED",
            )

        if logger is not None:
            logger.info(f"[{self.name}] posted {len(request.text)} chars to Bluesky")

        return CapabilityResult.ok(
            data=PostToBlueskyResponse(text=request.text, raw_result=raw),
            msg="Posted to Bluesky",
            metadata={"tool": f"{self.name} v{self.version}"},
        )
