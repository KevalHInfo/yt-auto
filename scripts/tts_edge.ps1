param(
    [Parameter(Mandatory = $true)]
    [string]$Text,

    [Parameter(Mandatory = $true)]
    [string]$Output
)

$scriptPath = Join-Path $PSScriptRoot "tts_edge.py"

if (-not (Test-Path $scriptPath)) {
    throw "Python script not found: $scriptPath"
}

python $scriptPath $Text $Output
exit $LASTEXITCODE
