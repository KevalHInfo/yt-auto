# Nexiora — YouTube Daily Automation

A fully automated "faceless" YouTube channel pipeline, built as an **n8n workflow**
(`YouTube-Daily-Automation.json`) plus local Python helpers in `scripts/`. Once a day it:

1. Discovers a trending tech/AI topic (Hacker News, Dev.to, YouTube Trending).
2. Writes an editorial video script with an LLM (Groq).
3. Synthesizes a voiceover locally (edge-tts).
4. Assembles a video from stock footage (Pexels) with ffmpeg.
5. Generates a branded thumbnail.
6. Uploads to YouTube (scheduled, private → publishes next day) and logs the run to
  Google Sheets + Airtable.

The whole folder is **portable**: unzip it on any Windows PC and run — every path is derived
from the repo location and the current user profile, nothing is hardcoded.

## Prerequisites

- Node.js (for `npx n8n`)
- Python 3.x on PATH
- ffmpeg (auto-discovered if installed via `winget install Gyan.FFmpeg`, or already on PATH)
- API keys / accounts for: Groq, Pexels, YouTube Data API, Airtable, plus Google OAuth access
for Sheets, Drive, and Gmail



## Running the workflow (day-to-day)

```powershell
powershell -ExecutionPolicy Bypass -File run-n8n.ps1
```

**Always start n8n this way, not with a bare** `npx n8n`**.** This script sets several things the
workflow depends on to function at all:

- `NODES_EXCLUDE=[]` — n8n disables the Execute Command node by default; this workflow's
voiceover/render/thumbnail steps require it.
- `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` — the workflow reads `$env.YT_SCRIPTS_DIR`,
`$env.YT_TMP_DIR`, `$env.YOUTUBE_API_KEY` directly in node expressions.
- Loads your machine-local secrets from `env.local.ps1`.
- Resolves `YT_SCRIPTS_DIR` / `YT_TMP_DIR` / font paths and makes sure ffmpeg is on PATH.
- Writes a debug log to `%USERPROFILE%\.n8n-files\logs\n8n.log` — see **Troubleshooting** below.

Once it's running, open **[http://localhost:5678](http://localhost:5678)**, open the **YouTube Daily Automation**
workflow, and either wait for the daily trigger (08:00) or click **Execute workflow** to run it
on demand.

## First-time setup on a new PC

See `[SECOND-PC-SETUP.md](SECOND-PC-SETUP.md)` for the full walkthrough — it covers two
paths: setting every credential up from scratch, or carrying credentials over from an existing
machine via n8n's `export:credentials`/`import:credentials` CLI (faster, no re-authorizing
OAuth apps). Short version:

```powershell
powershell -ExecutionPolicy Bypass -File setup-second-pc.ps1
```

This installs prerequisites, creates the working directory, scaffolds `env.local.ps1`, and
imports the workflow JSON into that PC's local n8n. `credentials-checklist.local.txt` is a
personal, gitignored scratch file listing every credential the pipeline needs and exactly where
each one goes (which is functional vs. which is just reference notes for pasting into n8n).

## Secrets

- `env.local.ps1` — launcher secrets (`YOUTUBE_API_KEY`, optionally `CURSOR_API_KEY`).
  Tracked in git; fill the empty `""` values. Keep the repo private if keys are real:
  ```powershell
  $env:YOUTUBE_API_KEY = "AIza..."
  ```
- `credentials-export.json` — fillable n8n import file (Groq / Pexels / MongoDB). Fill the
  empty `""` fields, then:
  ```powershell
  npx n8n import:credentials --input=credentials-export.json
  ```
  n8n encrypts `data` on import. OAuth (YouTube, Sheets, Drive, Gmail) is connected in the
  n8n UI. If you commit real keys here, keep the GitHub repo **private**.
- **n8n Credentials vault** — encrypted under `%USERPROFILE%\.n8n` after import / OAuth.
- `credentials-checklist.local.txt` *(gitignored)* — personal scratch notes only.



## Troubleshooting

When a node fails in the n8n editor, the on-screen error is sometimes truncated or, for HTTP
nodes that error at the transport level, can be masked by a generic
`Converting circular structure to JSON` message. The full picture is usually in the debug log:

```
%USERPROFILE%\.n8n-files\logs\n8n.log
```

Search it for the failing node's name (e.g. `grep "Node Name" n8n.log`) — it logs each node's
start/finish, and any underlying HTTP status code or error detail n8n's own error formatting
dropped. This is how several real issues were diagnosed during setup (a Groq rate limit showing
as a generic 429, a YouTube 403 masked by a circular-JSON crash, etc.) — check it first before
assuming a node's on-screen error is the whole story.

Common gotchas already solved once, in case they resurface:

- **Groq returns malformed JSON** — `Parse Script JSON` has defensive repair logic for known
failure modes (truncation, raw newlines, split strings, missing braces, unescaped scare
quotes). If a new malformation shows up, extend that function rather than removing the checks
already there — each one fixes an observed real failure.
- **Pexels 401** — its Header Auth credential needs **Name:** `Authorization`, **Value:** the
raw API key with **no** `Bearer` **prefix** (unlike most APIs).
- **YouTube thumbnail 403** — custom thumbnails require a phone-verified channel
(`youtube.com/verify`), independent of OAuth scopes.
- **Airtable 422 on** `published_at` — the node has `typecast: true` set so Airtable
auto-converts values; if a column's actual type doesn't match what's being sent (e.g. it got
created as a Collaborator field instead of Date), fix the column type in Airtable itself.



## Layout

- `YouTube-Daily-Automation.json` — the n8n workflow (import into n8n).
- `run-n8n.ps1` — portable launcher (env vars + ffmpeg discovery + start n8n).
- `setup-second-pc.ps1` — one-time setup for a fresh PC.
- `SECOND-PC-SETUP.md` — full credential-migration guide for a second machine.
- `env.local.ps1` — launcher secrets (`YOUTUBE_API_KEY`). Tracked; keep repo private if filled.
- `credentials-checklist.local.txt` *(gitignored)* — personal reference notes only.
- `scripts/` — `tts_edge.py`, `render_video.py`, `generate_thumbnail.py` (+ ps1 wrapper).
- `automation/` — optional Cursor-SDK self-heal / A-B script generator (not in the run path).
- `.cursor/rules/yt-automation.mdc` — project memory / detailed architecture & fix history.

> Deployment (Docker/cloud) and a standalone secrets-management service were both explored and
> removed to keep this lean — see the "Deferred" section in `CLAUDE.md` for why, and recreate
> either if the need comes back.

