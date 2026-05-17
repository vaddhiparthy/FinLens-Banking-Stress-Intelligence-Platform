$envPath = Join-Path $env:LOCALAPPDATA "FinLens\.venv"

if (-not (Test-Path $envPath)) {
    $python = (Get-Command python -ErrorAction Stop).Source
    uv venv $envPath --seed --python $python --link-mode=copy
}

$env:VIRTUAL_ENV = $envPath
$env:PATH = "$envPath\Scripts;$env:PATH"

uv sync --all-groups --active --link-mode=copy @args
