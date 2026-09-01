"""
Runnable demo of the doc_to_bluesky app's two zeocore tools, wired together
exactly as a real run would use them: FetchDocTextTool reads a Google Doc,
PostToBlueskyTool posts (a summary of) its text to Bluesky.

NEVER RUN AGAINST LIVE CREDENTIALS (see README.md "Never run against live
credentials" -- no credentials exist on the machine this app was built and
verified on, and the first real post is the operator's own act, never a
side effect of building or verifying this demo).

This script constructs both real zeocore integrations
(GoogleDocsService, BlueskyIntegration) with ZERO credentials configured,
and shows the real, honest failure each one produces:

  - GoogleDocsService.initialize() / .get_document_text() fail with
    "Configuration file not found in default locations." -- a config-file
    error, no traceback.
  - BlueskyIntegration.initialize() fails with "Failed to authenticate
    Bluesky: No Bluesky identifier/app_password provided" -- an AUTH
    error, genuinely different from the Google Docs failure above, no
    traceback.

Both are IntegrationResult objects: always check .success before touching
.content, never assume a bare .content is safe to read.

To run this against REAL credentials instead (an operator's own act, not
this script's default path), see README.md "Wiring real credentials" --
you would construct GoogleDocsService(client_secrets_file=...,
credentials_file=...) and BlueskyIntegration() (it reads
BLUESKY_IDENTIFIER/BLUESKY_APP_PASSWORD/BLUESKY_SERVICE_URL from the
environment), call .initialize() on each, and pass them into
ToolContext(services={"google_docs": docs, "bluesky": bluesky}) instead of
the empty services={} this script uses.

    uv run python run_demo.py
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from zeo_core.integrations.google.docs import GoogleDocsService
from zeo_core.integrations.social.bluesky import BlueskyIntegration
from zeo_core.tools import ToolContext

from doc_to_bluesky.bluesky_tools import PostToBlueskyRequest, PostToBlueskyTool
from doc_to_bluesky.doc_tools import FetchDocTextRequest, FetchDocTextTool

# An illustrative-only Google Doc ID and post text -- ILLUSTRATIVE, not
# real output (see README.md "Illustrative output is labelled"). No
# document with this ID exists; no post with this text has ever been sent.
ILLUSTRATIVE_DOCUMENT_ID = "1a2b3c4d5e6f-illustrative-doc-id-only"
ILLUSTRATIVE_POST_TEXT = (
    "Just shipped a new feature -- read the full writeup: example.com"
)


def build_ctx(tool_name: str, work_dir: Path, services: dict) -> ToolContext:
    return ToolContext(
        run_id=f"{tool_name}-demo-run",
        tool_name=tool_name,
        tool_version="1.0.0",
        logger=logging.getLogger(tool_name),
        fs=None,
        work_dir=str(work_dir),
        output_dir=str(work_dir),
        services=services,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

    with tempfile.TemporaryDirectory(prefix="zeo_doc_to_bluesky_demo_") as tmp:
        tmp_dir = Path(tmp)

        print("=" * 70)
        print("1. Constructing real GoogleDocsService (zero credentials)")
        print("=" * 70)
        docs = GoogleDocsService()
        init_result = docs.initialize()
        print(f"initialize.success={init_result.success}")
        print(f"initialize.error={init_result.error}")
        print(
            "This is the expected, honest outcome with no Google OAuth "
            "credentials configured -- see README.md to wire real ones."
        )
        print()

        print("=" * 70)
        print("2. FetchDocTextTool  (no 'google_docs' service wired -> skip)")
        print("=" * 70)
        ctx = build_ctx("fetch_doc_text", tmp_dir, services={})
        fetch_result = FetchDocTextTool().run(
            FetchDocTextRequest(document_id=ILLUSTRATIVE_DOCUMENT_ID), ctx
        )
        print(f"status={fetch_result.status.value}  msg={fetch_result.human_message}")
        print()

        print("=" * 70)
        print("3. Constructing real BlueskyIntegration (zero credentials)")
        print("=" * 70)
        bluesky = BlueskyIntegration()
        bsky_init_result = bluesky.initialize()
        print(f"initialize.success={bsky_init_result.success}")
        print(f"initialize.error={bsky_init_result.error}")
        print(
            "Note this is an AUTH error, not the config-file error Google "
            "Docs produced above -- the two integrations fail differently "
            "and this demo does not paper over that difference."
        )
        print()

        print("=" * 70)
        print("4. PostToBlueskyTool  (no 'bluesky' service wired -> skip)")
        print("=" * 70)
        ctx = build_ctx("post_to_bluesky", tmp_dir, services={})
        post_result = PostToBlueskyTool().run(
            PostToBlueskyRequest(
                text=ILLUSTRATIVE_POST_TEXT,
                link_text="example.com",
                link_uri="https://example.com",
            ),
            ctx,
        )
        print(f"status={post_result.status.value}  msg={post_result.human_message}")
        print()

        print("=" * 70)
        print("ILLUSTRATIVE full-pipeline shape (not run -- no credentials)")
        print("=" * 70)
        print(
            "With real credentials wired (see README.md), the same two "
            "tools compose as:\n"
            "  1. FetchDocTextTool(document_id=...) -> real Doc text\n"
            "  2. PostToBlueskyTool(text=<derived from the Doc text>, "
            "link_text=..., link_uri=<link back to the Doc>) -> real post\n"
            "Neither tool changes between the skip path shown above and "
            "the real path -- only ctx.services differs."
        )


if __name__ == "__main__":
    main()
