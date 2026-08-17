# SETUP — a from-zero walkthrough

Written for a reader with **zero prior context** — not on this repo, not on
this project, not on zeocore itself, not on Google Cloud. If a step feels
too basic, that's on purpose.

There are **two completely separate paths** through this repo:

1. **The dummy-data path.** Zero credentials, zero setup beyond installing
   the packages. Every tool in both apps runs against fake, synthetic data
   committed to the repo. Start here.
2. **The real-integration path.** Requires you to create your own (free)
   Google Cloud project and generate real OAuth credentials, so
   `apps/data_cleaning`'s `DownloadFromDriveTool` can download a real file
   from a real Google Drive account instead of reading a local CSV. This is
   entirely optional — the dummy-data path never needs it, and this repo
   works and demonstrates zeocore fully without it.

Do path 1 first. Only do path 2 if you specifically want to see zeocore's
real Google Drive integration work end to end.

---

## Path 1 — the dummy-data path (5 minutes, zero credentials)

### 1. Install Python

You need Python 3.10 or newer. Check what you have:

```bash
python3 --version
```

If that's below 3.10, install a newer Python first (e.g. via
[python.org](https://www.python.org/downloads/) or your OS package
manager) — that's outside this guide's scope.

### 2. Get the code

```bash
git clone https://github.com/zeroemployeeorg/zeocore-examples.git
cd zeocore-examples
```

### 3. Install and run the data-cleaning app

```bash
cd apps/data_cleaning
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -e .
python run_demo.py
```

You should see output showing five zeocore tools running against
synthetic contact/company CSV data — cleaning, validating, deduplicating —
with zero credentials, zero configuration, zero network calls.

### 4. Install and run the metrics-tracker app

```bash
cd ../metrics_tracker    # back to apps/, then into metrics_tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python run_demo.py
```

You should see eight weeks of fake automation-progress metrics submitted,
and two deliberately-bad inputs correctly rejected by typed validation.

**That's it — path 1 is done.** Everything above ran with zero real
credentials, zero real API keys, and touched no external service. If
that's all you wanted to see, you're finished.

---

## Path 2 — the real-integration path (Google Drive, ~20 minutes, one-time)

This proves `apps/data_cleaning`'s `DownloadFromDriveTool` against a REAL
Google Drive file in a real (you control it — use a throwaway/test Google
account if you'd rather not use your main one) Google account. It uses
zeocore's real `zeo_core.integrations.google.drive.GoogleDriveService` —
a real OAuth flow, not a simple API key paste.

### 2.1 Install the Drive extra

The base install (path 1) does not pull in Google's client libraries —
they're an optional "extra" so the dummy-data path stays lightweight:

```bash
cd apps/data_cleaning
source .venv/bin/activate   # if not already active
pip install -e ".[drive]" 2>/dev/null || pip install "zeocore[drive]"
```

(If your local checkout's `pyproject.toml` already lists `zeocore[drive]`
as a base dependency, a plain `pip install -e .` is enough — check
`apps/data_cleaning/pyproject.toml`'s `dependencies` list.)

### 2.2 Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/) and
   sign in with the Google account you want to use (a personal test
   account is fine — this never needs to be a work/organization account).
2. Click the project dropdown at the top of the page, then **"New
   Project"**.
3. Give it any name (e.g. `zeocore-drive-test`). Click **Create**.
4. Wait a few seconds for the project to be created, then select it from
   the project dropdown so it's your active project.

### 2.3 Enable the Google Drive API

1. In the Cloud Console, open the navigation menu (☰, top-left) →
   **APIs & Services** → **Library**.
2. Search for **"Google Drive API"**.
3. Click it, then click **Enable**.

### 2.4 Configure the OAuth consent screen

Google requires this before it will issue you an OAuth client, even for
your own personal testing use.

1. Navigate to **APIs & Services** → **OAuth consent screen**.
2. Choose **User type: External** (this works fine for personal Gmail
   accounts; "Internal" only appears if you have a Google Workspace
   organization).
3. Fill in the required fields: **App name** (anything, e.g.
   `zeocore-examples-test`), **User support email** (your email), and
   **Developer contact email** (your email again). Everything else on this
   page can be left as default.
4. Click **Save and Continue** through the Scopes screen (you don't need
   to add scopes here — the app requests them at runtime) and the Test
   Users screen.
5. **Add yourself as a test user** on the Test Users screen (click **Add
   Users**, enter the Google account email you're testing with). While
   your app is in "Testing" publishing status, only accounts you list here
   can complete the OAuth flow — this is expected and fine for this repo's
   purposes; you never need to publish the app.

### 2.5 Create OAuth client credentials

1. Navigate to **APIs & Services** → **Credentials**.
2. Click **+ Create Credentials** → **OAuth client ID**.
3. **Application type: Desktop app.**
4. Give it any name (e.g. `zeocore-examples-desktop`). Click **Create**.
5. A dialog shows your new client ID and secret. Click **Download JSON** —
   this downloads a file that looks like `client_secret_<long-id>.json`.

### 2.6 Place the credentials file

Move the downloaded JSON somewhere **outside the repo, or into a path
already covered by `.gitignore`** — never somewhere that could get
accidentally committed. This repo's `.gitignore` already excludes common
names for this file (`client_secret*.json`, `credentials.json`,
`token.json`, etc.) as a safety net, but the safest choice is a directory
outside the repo entirely, e.g.:

```bash
mkdir -p ~/.zeocore-examples-secrets
mv ~/Downloads/client_secret_*.json ~/.zeocore-examples-secrets/client_secret.json
```

**What this file contains** (do not put a real one in any file tracked by
git, ever): a JSON object shaped like

```json
{
  "installed": {
    "client_id": "<your-client-id>.apps.googleusercontent.com",
    "client_secret": "<your-client-secret>",
    "redirect_uris": ["http://localhost"]
  }
}
```

You never type these values into any file in this repo — the JSON you
downloaded from Google Cloud Console IS the file; you only need to know
where you put it.

### 2.7 Put a real CSV in Google Drive

Upload any CSV file to your Google Drive (a copy of
`apps/data_cleaning/data/contacts_messy.csv` works fine — or any CSV of
your own). Open it in Drive, and copy its **file ID** out of the URL:

```
https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/view
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^ this part
```

### 2.8 Run the real-integration demo

```bash
cd apps/data_cleaning
source .venv/bin/activate

export ZEOCORE_DRIVE_CLIENT_SECRETS=~/.zeocore-examples-secrets/client_secret.json
export ZEOCORE_DRIVE_CREDENTIALS=~/.zeocore-examples-secrets/token.json
export ZEOCORE_DRIVE_FILE_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz   # your real file id from 2.7

python run_demo_drive.py
```

**The first run opens your browser** to a real Google consent screen
(this is the OAuth "installed app" flow zeocore's `GoogleAuthProvider`
uses — there is no non-interactive path). Sign in with the same Google
account you added as a test user in step 2.4, and approve access. On
success, zeocore caches a token at the path you gave
`ZEOCORE_DRIVE_CREDENTIALS` (`token.json` in the example above) — this
file is also covered by `.gitignore`; never commit it. Every run after the
first reuses that cached token silently, until it expires.

Once authenticated, the script downloads your real Drive file to a local
temp path and runs it through the exact same `CleanContactsTool` the
dummy-data demo (`run_demo.py`) uses — unmodified. You're seeing zeocore's
real Google Drive integration and its typed tool-authoring pattern working
together, end to end, against a file that actually lives in your Google
account.

### Troubleshooting

- **"Client secrets file not found"** — check
  `ZEOCORE_DRIVE_CLIENT_SECRETS` points at the exact file you downloaded
  in step 2.5, with no typos in the path.
- **The browser flow fails / access blocked** — confirm you added your own
  account as a Test User in step 2.4; while the app is unpublished, only
  listed test users can complete the consent screen.
- **"File not found" / 404 from Drive** — double check the file ID from
  step 2.7 (easy to copy an extra character from the URL), and that the
  Google account you authenticated with actually owns or can see that
  file.
- **Missing environment variable errors** — `run_demo_drive.py` checks for
  all three variables up front and tells you exactly which is missing;
  it will not silently fall back to dummy data.

---

## What never happens, regardless of path

- No real credential, client secret, or token is ever committed to this
  repo, under any framing. `.gitignore` covers the common filenames; the
  discipline is to keep them outside the repo entirely as a second layer.
- The dummy-data path (path 1) never requires path 2's setup. They are
  fully independent; path 2 is additive.
- Nothing in this repo asks for your Google account password directly —
  authentication happens entirely through Google's own OAuth consent
  screen in your browser, the standard and correct way to authorize a
  desktop application.
