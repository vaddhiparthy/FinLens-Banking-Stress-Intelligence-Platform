$envPath = Join-Path $env:LOCALAPPDATA "FinLens\.venv"

if (-not (Test-Path $envPath)) {
    throw "FinLens virtual environment not found at $envPath"
}

$env:VIRTUAL_ENV = $envPath
$env:PATH = "$envPath\Scripts;$env:PATH"

Write-Output "Activated FinLens environment: $envPath"
