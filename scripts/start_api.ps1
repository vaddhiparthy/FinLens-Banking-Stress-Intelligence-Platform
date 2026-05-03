$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    . "$PSScriptRoot\use_finlens_env.ps1"
    python -m uvicorn api.main:app --host 127.0.0.1 --port 8010
}
finally {
    Pop-Location
}
