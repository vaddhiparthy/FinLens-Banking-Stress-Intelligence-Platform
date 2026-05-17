$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$repoVenvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$externalVenvPython = Join-Path $env:LOCALAPPDATA "FinLens\.venv\Scripts\python.exe"

if (Test-Path $repoVenvPython) {
    $python = $repoVenvPython
} elseif (Test-Path $externalVenvPython) {
    $python = $externalVenvPython
} else {
    $python = "python"
}

Push-Location $repoRoot
try {
    $previousPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = @(
        (Join-Path $repoRoot "src"),
        $repoRoot,
        $previousPythonPath
    ) -ne "" -join [System.IO.Path]::PathSeparator

    & $python -m ruff check .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    @'
from streamlit_app.lib.charts import (
    acquirer_chart,
    failures_by_year_chart,
    latest_macro_snapshot,
    macro_compare_chart,
    state_assets_map,
)
from streamlit_app.lib.data import load_acquirers, load_failures, load_metrics
from finlens.stress_lab import run_demo_stress_lab

failures = load_failures()
metrics = load_metrics()
acquirers = load_acquirers()
result = run_demo_stress_lab()

assert not failures.empty
assert not metrics.empty
assert not acquirers.empty
assert len(result.model_results) >= 3

for fig in [
    failures_by_year_chart(failures),
    state_assets_map(failures),
    latest_macro_snapshot(metrics),
    macro_compare_chart(metrics),
    acquirer_chart(acquirers),
]:
    assert fig.to_dict()

print("Smoke imports and figure generation passed.")
'@ | & $python -
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
    Pop-Location
}
