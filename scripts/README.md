# Scripts

Operational and utility scripts live here.

Current scripts that matter:
- `use_finlens_env.ps1`
- `uv_sync.ps1`
- `smoke_test.ps1`
- `run_local_pipeline.py`
- `start_finlens.ps1`
- `start_api.ps1`
- `sync_control_plane_to_postgres.py`

Current recommended workflow:
- copy `.env.example` to `.env`
- fill the active connector values when available
- run `powershell -ExecutionPolicy Bypass -File .\scripts\start_finlens.ps1`

`start_finlens.ps1` now starts the app even when optional connectors are missing. It runs ready
sources, writes the connector report, and leaves missing values visible in the technical surface.
