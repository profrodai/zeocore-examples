# zeocore-examples

A **[zeocore](https://github.com/zeroemployeeorg/zeocore) dogfooding and
teaching example repo**. This is not a production tool — it exists to
(a) genuinely battle-test zeocore against real capability shapes, so that if
zeocore's own API is awkward, missing something, or wrong for a real use
case, that gets found here, not assumed away; and (b) teach other agents
("other little Claudes") how to build a real application on zeocore, by
example, not by prose alone.

It rebuilds two existing, small public course-artifact repos as two
separate zeocore-powered example applications:

- **[`apps/data_cleaning/`](apps/data_cleaning/)** — rebuilds
  [`agency-data-onboarding-kit`](https://github.com/zeroemployeeorg/agency-data-onboarding-kit)
  (B2B contact/company CSV data cleaning). Six typed tools: two pipeline
  tools (`clean_contacts`, `clean_accounts`), three small utility tools
  (`clean_email`, `normalize_country`, `extract_domain`) — the "many small
  typed tools" shape zeocore's own README pitches — plus, as of round 2
  (RULING-280 / CHARTER-03), `download_from_drive`: a real
  integration-backed tool that downloads a CSV from a real Google Drive
  file via zeocore's real `zeo_core.integrations.google.drive` module,
  then feeds it into the same cleaning tools unchanged. See
  [`SETUP.md`](SETUP.md) for the real Google OAuth walkthrough this
  capability needs (entirely optional — the dummy-data path below needs
  none of it).
- **[`apps/metrics_tracker/`](apps/metrics_tracker/)** — rebuilds
  [`business-transformation-tracker`](https://github.com/zeroemployeeorg/business-transformation-tracker)
  (weekly business-metrics self-tracking). One typed tool
  (`submit_weekly_metrics`) whose pydantic request model genuinely closes a
  real bug in the original code (unguarded division, no validation that
  automated hours can't exceed total hours) — see that app's own README for
  the exact bug, reproduced, and the fix.

Neither source repo is modified by this work — both stay exactly as they
are; this is a fresh rebuild in a new, separate repo.

## Install and run

**New to this repo? Start with [`SETUP.md`](SETUP.md)** — a complete,
zero-assumed-context walkthrough covering both the instant zero-credential
demo path and the (optional) real Google Drive integration path, including
the full Google Cloud OAuth setup.

The short version, for the zero-credential dummy-data path:

```bash
cd apps/data_cleaning && pip install -e . && python run_demo.py
cd apps/metrics_tracker && pip install -e . && python run_demo.py
```

Both apps run against dummy/synthetic data with **zero real credentials
required**. Each app is its own installable package, depending on the
real, published `zeocore` package from PyPI (not a local/editable
dependency on zeocore's own source, which would defeat the point of
dogfooding it as a real external user would experience it).

See each app's own README for what it demonstrates and its real output.

## The real-integration path (optional)

`apps/data_cleaning` also ships `download_from_drive`, a real tool backed
by zeocore's real `zeo_core.integrations.google.drive.GoogleDriveService`
— downloading a CSV from a real Google Drive file, then feeding it into
the same cleaning tools the dummy-data demo uses, unchanged. This needs a
real (your own, e.g. a free/test) Google Cloud OAuth credential — see
[`SETUP.md`](SETUP.md) §Path 2 for the full walkthrough, and
`apps/data_cleaning/run_demo_drive.py` for the runnable demo. This is
entirely additive: the dummy-data path above never needs it, and nothing
about it is a prerequisite for seeing zeocore work.

## Data discipline

Everything committed to this public repo is dummy/synthetic data —
obviously-fake names, `*-demo.test` email/website domains (`.test` is the
IANA-reserved TLD for exactly this purpose), and fabricated weekly numbers.
No real client records, no real business figures, no real secrets, ever,
under any framing. See `.env.example` for what a real live-testing session
(run locally, never committed) would need.

## Repo structure — a provisional choice, not yet finalized

Two fully independent top-level app directories under `apps/`, each its own
installable package with its own `pyproject.toml`, README, and dummy-data
directory. This was a genuinely open design fork
(`zeocore-dogfooding-DESIGN-01-repo-structure.md`) at the time this repo was
built — see that filing, and the SOW that built this repo, for the reasoning
and the alternative considered (a shared `zeocore`-usage-pattern library).

## What this repo is not

- Not a PR against either source repo — both stay untouched.
- Not a complete 1:1 port of every function in either original — each app's
  own README states exactly what was rebuilt and what was left out.
- Not a place for real API keys, real client data, or real business
  figures, under any circumstance.

## License

MIT — matching zeocore's own license. See [LICENSE](LICENSE).
