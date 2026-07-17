# Launches n8n locally with the environment the YouTube-Daily-Automation workflow needs.
# Usage:  right-click > Run with PowerShell, or:  powershell -ExecutionPolicy Bypass -File run-n8n.ps1

$ErrorActionPreference = "Stop"

# --- Paths this workflow reads via $env.* -----------------------------------
# All paths are derived from the repo location + current user profile, so this
# works on ANY Windows machine/username after unzipping (home laptop, office PC).
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$UserHome = $env:USERPROFILE -replace '\\', '/'
$env:YT_SCRIPTS_DIR = (Join-Path $RepoRoot "scripts") -replace '\\', '/'
$env:YT_TMP_DIR     = "$UserHome/.n8n-files/tmp"

# Fonts for ffmpeg drawtext (render_video.py / generate_thumbnail.py)
$env:YT_FONT_FILE = "C:/Windows/Fonts/arial.ttf"
$env:YT_FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"

# Allow Code nodes to read $env.* values
$env:N8N_BLOCK_ENV_ACCESS_IN_NODE = "false"

# n8n v2 disables the Execute Command node by default for security reasons.
# This workflow depends on it (TTS/render/thumbnail scripts), so re-enable it
# by overriding the default exclude list with an empty one.
$env:NODES_EXCLUDE = "[]"

# Verbose logging for debugging - shows in this terminal AND writes to a file
# so you can inspect it after the fact.
$env:N8N_LOG_LEVEL  = "debug"
$env:N8N_LOG_OUTPUT = "console,file"
$env:N8N_LOG_FILE_LOCATION = "$UserHome/.n8n-files/logs/n8n.log"
$logDir = Split-Path -Parent $env:N8N_LOG_FILE_LOCATION
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}
Write-Host "Debug log file: $($env:N8N_LOG_FILE_LOCATION)"

# --- Secrets (env.local.ps1 — tracked; keep repo private if filled) ---------
# Dot-sourced here if present. Fill empty "" values in env.local.ps1, e.g.:
#     $env:YOUTUBE_API_KEY = "AIza...."
$localEnv = Join-Path $RepoRoot "env.local.ps1"
if (Test-Path $localEnv) {
    . $localEnv
    Write-Host "Loaded env from env.local.ps1"
}

# --- Ensure the working/temp dir exists -------------------------------------
if (-not (Test-Path $env:YT_TMP_DIR)) {
    New-Item -ItemType Directory -Force -Path $env:YT_TMP_DIR | Out-Null
    Write-Host "Created temp dir: $($env:YT_TMP_DIR)"
}

# --- Sanity checks ----------------------------------------------------------
Write-Host "YT_SCRIPTS_DIR = $($env:YT_SCRIPTS_DIR)"
Write-Host "YT_TMP_DIR     = $($env:YT_TMP_DIR)"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    # Fallback: auto-discover a winget-installed ffmpeg and prepend it to PATH for this session.
    $pkgRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    $ff = Get-ChildItem -Path $pkgRoot -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($ff) {
        $env:Path = $ff.DirectoryName + ";" + $env:Path
        Write-Host "ffmpeg found (auto-added to PATH): $($ff.DirectoryName)"
    } else {
        Write-Warning "ffmpeg is NOT on PATH and not found under WinGet. Render + thumbnail steps will fail. Install: winget install Gyan.FFmpeg"
    }
} else {
    Write-Host "ffmpeg found: OK"
}

if (-not $env:YOUTUBE_API_KEY) {
    Write-Warning "YOUTUBE_API_KEY is not set - the 'YouTube Trending' source will fail. Set it in env.local.ps1 (see comment above)."
}

# --- Start n8n --------------------------------------------------------------
Write-Host "Starting n8n... open http://localhost:5678"
npx n8n
