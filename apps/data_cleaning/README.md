# zeocore example: data cleaning

A [zeocore](https://github.com/zeroemployeeorg/zeocore)-powered rebuild of
[`agency-data-onboarding-kit`](https://github.com/zeroemployeeorg/agency-data-onboarding-kit)'s
B2B contact/company CSV cleaning pipelines. Part of
[`zeocore-examples`](../../README.md) — read that top-level README first for
what this whole repo is and why it exists.

## What's here

Six real, runnable `BaseZeoTool` subclasses in `src/data_cleaning/`:

- **`pipeline_tools.py`** — the two main pipelines, matching the original's
  own `scripts/clean_contacts.py` and `scripts/clean_accounts.py`:
  - `CleanContactsTool` — normalizes columns, cleans email/phone/LinkedIn/country
    fields, filters invalid emails, deduplicates by completeness score.
  - `CleanAccountsTool` — normalizes columns, extracts domains from websites,
    cleans industry/country fields, deduplicates by domain (or name).
- **`small_tools.py`** — three of the original's own smaller reusable utility
  functions, each wrapped as its own tiny typed tool (the "many small typed
  tools" shape zeocore's own README pitches):
  - `CleanEmailTool`, `NormalizeCountryTool`, `ExtractDomainTool`.
- **`drive_tools.py`** — **round 2's real integration-backed capability**
  (RULING-280 / CHARTER-03): `DownloadFromDriveTool` downloads a real file
  from Google Drive via zeocore's real
  `zeo_core.integrations.google.drive.GoogleDriveService` (a real OAuth
  flow, not mocked), returning a local path that feeds straight into
  `CleanContactsTool`/`CleanAccountsTool` unchanged. If no `google_drive`
  service is wired into `ctx.services`, it returns a typed
  `CapabilityResult.skip` — not an error — so the zero-credential path
  never breaks. See the repo-root `SETUP.md` for the real Google Cloud
  OAuth walkthrough, and `run_demo_drive.py` (this directory) for the
  runnable end-to-end example.
- **`_utils.py`** — the plain-Python cleaning helpers themselves, ported
  near-verbatim from the original's `scripts/utils.py` (same repo, MIT
  licensed, linked above) — this module is the business-logic ring; the tool
  classes above are the zeocore doctrine ring around it.

## Dummy data

`data/contacts_messy.csv` and `data/accounts_messy.csv` are obviously-fake
synthetic records (`*-demo.test` email/website domains throughout — `.test`
is the IANA-reserved TLD for exactly this purpose, RFC 2606) written fresh
for this repo, in the same shape/spirit as the original repo's own
`samples/*.csv` (messy casing, duplicate rows, missing fields, a `test@`
junk row) — adapted, not copied verbatim.

## Run it

No real credentials needed for this path — everything runs against the
dummy CSVs above.

```bash
cd apps/data_cleaning
pip install -e .
python run_demo.py
```

This runs all 5 tools end to end and prints real `CapabilityResult` output
for each, including the two pipelines' cleaning statistics (rows read,
invalid-email rows filtered, duplicates removed, final row count).

## What a real (non-dummy) run would need

**For the cleaning pipelines themselves**: nothing extra. The original
`agency-data-onboarding-kit` also has a Postgres/Supabase storage layer this
rebuild does not (yet) reach — see the repo-level `.env.example` for the
placeholder that a future round adding that layer would fill in.

**For `DownloadFromDriveTool` (round 2's real integration)**: real Google
OAuth credentials — see the repo-root `SETUP.md` for the full walkthrough,
and `run_demo_drive.py` for the runnable demo. This is entirely optional;
`run_demo.py` above needs none of it.
