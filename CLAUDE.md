# Nexiora — YouTube Daily Automation

A fully automated "faceless" YouTube channel pipeline built as an **n8n workflow**
(`YouTube-Daily-Automation.json`) plus local **Python helper scripts** (`scripts/`) and a
Cursor-SDK self-heal package (`automation/`). Runs once a day: discovers a trending tech
topic, writes an editorial script with an LLM, synthesizes a voiceover, assembles a video
from stock footage, generates a branded thumbnail, and uploads to YouTube — logging to
Google Sheets and Airtable.

**Git repository.** Prefer diagnose-only `automation/self_heal.py` (no `--apply`) unless you
intentionally want the agent to edit files; with git you can always revert.

## Layout
- `YouTube-Daily-Automation.json` — the n8n workflow, edited/maintained here and imported into n8n.
- `run-n8n.ps1` — portable launcher: sets `YT_*` env vars, loads `env.local.ps1` secrets,
  discovers ffmpeg, runs `npx n8n`.
- `setup-second-pc.ps1` — one-time fresh-PC bootstrap (ffmpeg, python deps, tmp dir, workflow import).
- `env.local.ps1` — secrets for the launcher (`$env:YOUTUBE_API_KEY = "..."`). Tracked in git;
  keep the repo private if real keys are filled in.
- `scripts/` — local helpers invoked by n8n `executeCommand` nodes:
  - `tts_edge.py` / `tts_edge.ps1` — edge-tts wrapper, `<textfile> <out.mp3> [voice]` (default `en-US-JennyNeural`).
  - `render_video.py` — reads `manifest.json` (clips/audio/title/output/clipLength), builds an
    ffmpeg filter_complex (scale/crop 1280x720@30, trim, concat, title overlay first 3s, mux voiceover).
  - `generate_thumbnail.py` — ffmpeg+drawtext thumbnail generator, deterministic-per-title
    palette/layout variation (md5 seed) + NEXIORA watermark + optional video-frame background.
- `automation/` — Cursor SDK package (optional, not in the default run path):
  - `_common.py` — key/model loading (`CURSOR_API_KEY`, `CURSOR_MODEL`), `run_one_shot()`, path constants.
  - `self_heal.py` — on workflow failure, launches a Cursor agent to diagnose (`--apply` to fix).
    Diagnose-only by default; writes `automation/heal_reports/heal-<ts>.md`. **Keep diagnose-only
    (`--apply` unsafe) until the repo is under git.**
  - `generate_script.py` — optional A/B script generator alternative to the Groq node.
- `.cursor/rules/yt-automation.mdc` — the original, very detailed architecture/history notes
  (Cursor IDE's memory format). Kept in sync conceptually with this file; read it for deeper
  node-by-node history and the full list of fixes already applied.

## n8n workflow pipeline (node order)
1. **Daily Trigger** (08:00) + parallel **Manual Web Trigger** (webhook `/webhook/generate-video`).
2. Fan-out HTTP: Hacker News (Algolia front_page), Dev.to trending, YouTube Trending (`YOUTUBE_API_KEY`).
3. **Merge HN and Trends** → **Merge All Sources**.
4. **Score and Pick Topic** (Code) — scores candidates, applies 2.5x `cpmBoost()` for high-CPM
   keywords (ai, llm, saas, startup, funding, enterprise, security, fintech...), picks top title.
5. **Log Topic to Sheets**.
6. **Generate Script (Groq)** — `llama-3.1-8b-instant`, `max_tokens: 4096`, Nexiora editorial
   voice prompt (8-10 min opinionated take, not a plain summary), strict JSON contract
   `{title, description, sections[], script}`.
7. **Parse Script JSON** (Code) — heavy defensive JSON repair for small-model output. **Do not
   simplify without a replacement safeguard** — each branch fixes an observed real failure.
8. Build/save script → **Generate Voiceover (Local TTS)** (`scripts/tts_edge.py`) → save audio.
9. **Extract Keywords** → **Split By Keyword** loop → Pexels fetch/pick/download clips.
10. **Prepare Render Manifest** → **Render Video (Local FFmpeg)** (`scripts/render_video.py`).
11. **Thumbnail (LOCAL)**: `Prepare Thumbnail Title` → write `thumb_title.txt` →
    `Generate Thumbnail (Local)` (`scripts/generate_thumbnail.py`) → read `thumbnail.png`
    (binary property `thumbnail`).
12. **Calculate Chapters** (adds subscribe CTA + `#Nexiora #TechNews #AI` footer) →
    **Set Publish Time** (tomorrow 5:00 PM America/New_York, DST-safe) →
    **Upload to YouTube** (private + `publishAt`, category 28, regionCode US, Nexiora tags) →
    **Attach Thumbnail Binary** → **Set YouTube Thumbnail** → **Save to Airtable**.
13. **Error Trigger** → **Send Error Email** (Gmail) on any node failure.

## Paths are env-driven, portable across machines
No hardcoded usernames/paths anywhere. `run-n8n.ps1` sets:
- `YT_SCRIPTS_DIR` — repo-relative `scripts/`.
- `YT_TMP_DIR` — `%USERPROFILE%/.n8n-files/tmp` (per-user).
- `YT_FONT_FILE` / `YT_FONT_BOLD` — ffmpeg drawtext fonts (fall back to Windows arial/arialbd).
- `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (Code nodes need this to read `$env.YT_*`).
`automation/_common.py` resolves `TMP_DIR` the same way. Credentials live in
`%USERPROFILE%\.n8n`, outside the repo — must be re-imported/reconnected on a new PC (or copy
`.n8n` + share `N8N_ENCRYPTION_KEY`).

## Deferred (deliberately removed, recreate when needed)
- `secrets-service/` — standalone Node/Express + MongoDB (Atlas M0) encrypted credential store
  with AES-256-GCM envelope encryption and a bearer-token CRUD API. Was built but never wired
  into the n8n workflow; removed 2026-07-12 once the credential-migration path (n8n's own
  `export:credentials`/`import:credentials` CLI, see `SECOND-PC-SETUP.md`) covered the actual
  need (moving credentials to a second PC) without a second always-on service to run/secure.
- Docker/compose deployment (`Dockerfile`, `docker-compose.yml`, root `.env.example`) — removed
  to keep the zip lean; owner runs locally on two Windows PCs via `run-n8n.ps1`.
- `web/index.html` one-button trigger page — deleted; use the n8n manual run or POST the
  webhook directly to trigger on demand.

## Channel identity & monetization (Nexiora)
Faceless, US-targeted daily tech/AI channel, handle **@TheNexiora**. Brand palette: dark navy
`#1a1a2e` + accent pink-red `#e94560`. Targets US audience (regionCode US, 5PM ET publish,
US trending sources) while payout/AdSense account is India-based — no VPN needed, set Country
of residence = United States in YouTube Studio.

YPP monetization: 1,000 subs + 4,000 public watch-hours/12mo for full ads; 500 subs + 3,000
hrs for early access. US tech CPM ~$8-25, AI/SaaS/fintech $15-90 (hence `cpmBoost`).

**Known risk:** YouTube's inauthentic-content policy targets mass-produced, templated,
low-variation faceless output. Mitigations already in place: editorial-voice script prompt,
per-title thumbnail variation, high-CPM topic bias. Recommended but not yet done: reduce
cadence to 3-4 higher-effort videos/week, enable YouTube's "altered content" AI disclosure.

## Working conventions
- Keep the workflow JSON importable/valid: preserve node `id`, connection names, `typeVersion`.
- Prefer env/config-driven paths over hardcoding.
- Don't weaken `Parse Script JSON` repair logic without a replacement safeguard.
- `automation/self_heal.py --apply` is unsafe with no git — keep diagnose-only until the repo
  is under version control.
- For deeper history of what was already fixed/changed, see `.cursor/rules/yt-automation.mdc`.
