$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    . "$PSScriptRoot\use_finlens_env.ps1"
    python .\scripts\run_local_pipeline.py --allow-missing-connectors --start-streamlit
}
finally {
    Pop-Location
}
