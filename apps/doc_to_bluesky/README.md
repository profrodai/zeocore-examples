# zeocore example: Google Doc to Bluesky

Read the text of a **Google Doc** and publish it to **Bluesky**, using
[zeocore](https://github.com/zeroemployeeorg/zeocore) integrations. Part of
[`zeocore-examples`](../../README.md) — read that top-level README first for
what this whole repo is.

> **This has NEVER been run against live credentials.** No Google or Bluesky
> credentials existed on the machine where it was built and verified. Every
> code path below has been executed *up to* the live API call; the live call
> itself has not. Any API response shown in this README is **illustrative and
> labelled as such** — none of it was captured from a real request.

## Requirements

**Python 3.14 or newer.** zeocore 0.6.0 raised its floor to 3.14; on 3.13 the
install is *refused* by the resolver rather than failing later.

**[uv](https://docs.astral.sh/uv/)**, which every command here uses. If you do
not have it yet, install it first — the commands below assume it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or, on macOS with Homebrew:
brew install uv
```

## Run it, from a clean machine

Every command is copy-pasteable, in order, assuming nothing but `git` and `uv`.

```bash
git clone https://github.com/zeroemployeeorg/zeocore-examples.git
cd zeocore-examples/apps/doc_to_bluesky

uv venv --python 3.14
uv pip install -e .

uv run python run_demo.py
```

With **no credentials configured** — which is what you get on a fresh machine —
`run_demo.py` runs to completion and shows you the two real, *different*
failures you will hit first. It does not raise a traceback.

## Install the library directly

If you are installing zeocore into your own project rather than running this
app, **use the pinned form**:

```bash
uv pip install "zeocore[calendar,bluesky]>=0.6.0"
```

**Do not drop the `>=0.6.0`.** Within minutes of 0.6.0 being published, a bare
install resolved **0.5.0** from a stale package-index cache — and **0.5.0
contains neither the Google Docs nor the Bluesky integration.** You would get:

```
ModuleNotFoundError: No module named 'zeo_core.integrations.google.docs'
```

which is honest and maximally confusing, because the module genuinely is not
in that version. **The pin fails loudly on a stale index instead of silently
installing a version without the integrations.**

### There is no `[docs]`, `[sheets]` or `[slides]` extra

The Google integrations **share one dependency set**. `[calendar]` (or
`[google]`, `[drive]`, `[gmail]`, `[all]`) gives you Docs, Sheets, Slides,
Calendar, Drive and Gmail together. Asking for `zeocore[sheets]` is a
resolution error. Bluesky is its own extra, `[bluesky]`.

## Credentials

Copy `.env.example` to `.env` and fill it in **locally only** — `.env` is
gitignored and must never be committed.

| variable | what it is |
|---|---|
| `GOOGLE_CLIENT_SECRETS_FILE` | Path to the OAuth **client secrets** JSON you download from Google Cloud Console. |
| `GOOGLE_CREDENTIALS_FILE` | Path where the **stored user token** is written. **This file does not exist yet** — it is created when the OAuth consent flow completes in your browser on first run. |
| `BLUESKY_IDENTIFIER` | Your handle (`you.bsky.social`) or account email. |
| `BLUESKY_APP_PASSWORD` | An **app password**, from Settings → App Passwords. **Never your account password.** |
| `BLUESKY_SERVICE_URL` | Optional; only for a non-default PDS host. Defaults to `https://bsky.social`. |

Bluesky needs **no** developer app, no OAuth and no approval wait — an app
password from ordinary account settings is enough. Google does require a
Cloud Console project and a consent screen.

zeocore stores resolved credentials **outside this repository**, in an
OS-appropriate per-user directory, with file mode `600`. You cannot
accidentally commit them.

## The two errors you will hit first, verbatim

They are **different for the two integrations**, and that difference is real:

```
Google Docs:  Configuration file not found in default locations.
Bluesky:      Failed to authenticate Bluesky: No Bluesky identifier/app_password provided
```

Google Docs reports a **config-file** problem; Bluesky reports an **auth**
problem. Do not expect one message to cover both.

## Every call returns an `IntegrationResult`

```python
result = docs.get_document_text(document_id)
if not result.success:
    print(result.error)      # a string explaining what went wrong
else:
    text = result.content    # only safe to read once .success is True
```

**Always check `.success` before touching `.content`.** A bare `.content`
access is the most common mistake against this API.

## The byte-offset hazard — read this before hand-building a link

Bluesky locates links and mentions by **UTF-8 byte offset**, not character
offset. For ASCII-only text the two coincide, which is exactly why this bug
hides. With any accent or emoji they diverge:

```python
text = "café ☕ https://example.com done"
# byte offsets of the URL:      (10, 29)   <- what Bluesky needs
# character offsets of the URL: (7,  26)   <- what str.find() gives you
```

`é` is 2 UTF-8 bytes and `☕` is 3, so the character index runs three low. Feed
Bluesky the character offsets and it highlights three bytes into the URL: **a
mangled link, silently, with no error from the API.**

**The library computes this for you.** Pass a `LinkSpan` and let it do the
work — never hand-build the index:

```python
from zeo_core.integrations.social.bluesky.facets import LinkSpan

bluesky.post(
    text="Read this: https://example.com",
    links=[LinkSpan(text="https://example.com", uri="https://example.com")],
)
```

## What's here

- `run_demo.py` — wires both tools together and runs end to end without credentials.
- `src/doc_to_bluesky/doc_tools.py` — `FetchDocTextTool`, wrapping `GoogleDocsService.get_document_text`.
- `src/doc_to_bluesky/bluesky_tools.py` — `PostToBlueskyTool`, wrapping `BlueskyIntegration.post`.

## Wiring real credentials

Constructing the integrations against real credentials is the **operator's own
act**, deliberately not this demo's default path:

```python
bluesky = BlueskyIntegration()   # reads BLUESKY_* from the environment
bluesky.initialize()
```

**`BlueskyIntegration()` needs no config file** — it reads
`BLUESKY_IDENTIFIER`/`BLUESKY_APP_PASSWORD`/`BLUESKY_SERVICE_URL` straight
from the environment (see "Credentials" above).

**`GoogleDocsService` is less direct — confirmed by execution, not assumed
from the constructor signature.** Passing `client_secrets_file=`/
`credentials_file=` to `GoogleDocsService(...)` does **not** skip its
default-locations config check the way it might look like it should:
`GoogleDocsService(client_secrets_file="...", credentials_file="...")
.initialize()` still returns the same `"Configuration file not found in
default locations."` error as the zero-argument form — verified live,
reproduced twice. `BaseIntegrationService.initialize()` runs its own
config-file lookup before a subclass's constructor args are ever consulted.
Making this actually authenticate needs a real YAML config file (via
`config_path=`) shaped for `GoogleDocsConfig` (`client_secrets_file` /
`credentials_file` keys) — the exact shape was not pinned down further here,
on purpose: this repo never calls the live Google API, and guessing past
what was verified would trade one honest gap for a fabricated instruction.
Treat the constructor snippet above as unresolved for Docs; check zeocore's
own docs or source (`zeo_core/integrations/google/docs/service.py`,
`zeo_core/integrations/core/base.py`) before building a real Docs
integration against it.

```python
ctx = ToolContext(services={"google_docs": docs, "bluesky": bluesky})
```

**A real `post()` publishes publicly and cannot be un-published by this code.**
Run it deliberately, not to find out whether it works.
