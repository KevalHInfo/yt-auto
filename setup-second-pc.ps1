# One-time setup for a NEW Windows PC (e.g. the office PC) after unzipping this folder.
# Run:  powershell -ExecutionPolicy Bypass -File setup-second-pc.ps1
#
# It automates everything that CAN be automated (deps, tmp dir, secrets template,
# workflow import) and prints the few manual steps that cannot (credentials are
# encrypted per-machine and live in %USERPROFILE%\.n8n, outside this folder).

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "== Nexiora automation: second-PC setup ==" -ForegroundColor Cyan

# 1. Python -------------------------------------------------------------------
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "[ok] python: $(python --version)"
} else {
    Write-Warning "python NOT found. Install Python 3.x from https://python.org (tick 'Add to PATH'), then re-run this script."
}

# 2. ffmpeg (via winget) ------------------------------------------------------
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "[ok] ffmpeg on PATH"
} else {
    $pkg = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages") -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pkg) {
        Write-Host "[ok] ffmpeg present at $($pkg.DirectoryName) (open a NEW terminal so PATH resolves)"
    } else {
        Write-Host "Installing ffmpeg via winget..."
        winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
        Write-Host "[done] ffmpeg installed - open a NEW terminal so PATH refreshes."
    }
}

# 3. Python deps (edge-tts, etc.) --------------------------------------------
if (Get-Command python -ErrorAction SilentlyContinue) {
    python -c "import edge_tts" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing python deps from requirements.txt..."
        python -m pip install --user -r (Join-Path $RepoRoot "requirements.txt")
    } else {
        Write-Host "[ok] edge-tts installed"
    }
}

# 4. Working/temp dir ---------------------------------------------------------
$tmp = ($env:USERPROFILE -replace '\\', '/') + "/.n8n-files/tmp"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
Write-Host "[ok] tmp dir ready: $tmp"

# 5. Secrets file (tracked in git — fill empty values) -----------------------
$localEnv = Join-Path $RepoRoot "env.local.ps1"
if (Test-Path $localEnv) {
    Write-Host "[ok] env.local.ps1 already exists — fill YOUTUBE_API_KEY if empty"
} else {
    @(
        '# Secrets for run-n8n.ps1 (tracked — keep repo private if filled).',
        '$env:YOUTUBE_API_KEY = ""',
        '# $env:CURSOR_API_KEY = ""   # only needed for automation/ self-heal'
    ) | Set-Content -Path $localEnv -Encoding UTF8
    Write-Host "[created] env.local.ps1 - EDIT it and paste your YOUTUBE_API_KEY." -ForegroundColor Yellow
}

# 6. Import the workflow into this PC's local n8n -----------------------------
Write-Host "Importing workflow into local n8n (this may take a moment)..."
try {
    npx n8n import:workflow --input="$(Join-Path $RepoRoot 'YouTube-Daily-Automation.json')"
    Write-Host "[ok] workflow imported into local n8n."
} catch {
    Write-Warning "Auto-import failed. Import manually in the n8n editor: ... menu > Import from File > YouTube-Daily-Automation.json"
}

# --- Manual steps (cannot be automated) -------------------------------------
Write-Host ""
Write-Host "MANUAL steps left (credentials are encrypted per-machine):" -ForegroundColor Yellow
Write-Host "  1. Edit env.local.ps1 and paste your YOUTUBE_API_KEY."
Write-Host "  2. Start n8n:   powershell -ExecutionPolicy Bypass -File run-n8n.ps1"
Write-Host "  3. In the n8n editor, reconnect credentials on the relevant nodes:"
Write-Host "     Google Sheets, Google Drive, Groq, Pexels, YouTube OAuth2, MongoDB, Gmail."
Write-Host "  4. (Shortcut) To avoid re-entering creds, copy %USERPROFILE%\.n8n from the"
Write-Host "     other PC AND set the same N8N_ENCRYPTION_KEY on both machines."
Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
