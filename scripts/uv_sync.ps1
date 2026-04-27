$envPath = Join-Path $env:LOCALAPPDATA "FinLens\.venv"

if (-not (Test-Path $envPath)) {
    uv venv $envPath --seed --python C:\Users\vaddh\AppData\Local\Programs\Python\Python314\python.exe --link-mode=copy
}

$env:VIRTUAL_ENV = $envPath
$env:PATH = "$envPath\Scripts;$env:PATH"

uv sync --all-groups --active --link-mode=copy @args
