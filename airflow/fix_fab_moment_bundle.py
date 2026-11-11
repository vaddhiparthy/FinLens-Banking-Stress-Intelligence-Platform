"""Load the generated FAB Moment dependency chunk before its entry bundle.

Same patch as the FinLens image fix, but the dependency chunk id is read from the Moment entry bundle
(844 in FAB 3.9, 206 in FAB 3.11) instead of being fixed."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path


# Found from the installed Airflow package, so the path follows the Python version of the image.
FAB_ROOT = Path(importlib.util.find_spec("airflow").submodule_search_locations[0]) / "providers/fab/www"
DEFAULT_TEMPLATE = FAB_ROOT / "templates/airflow/main.html"
DEFAULT_ASSET_DIR = FAB_ROOT / "static/dist"
MARKER = "finlens-fab-moment-chunk-load-v1"
TARGET = """  <script src="{{ url_for_asset('runtime.js') }}"></script>
  <script src="{{ url_for_asset('moment.js') }}"></script>"""


def replacement(chunk_id: str) -> str:
    return f"""  {{# {MARKER}: legacy FAB page assets require authenticated page context #}}
  {{% if current_user.is_authenticated %}}
    <script src="{{{{ url_for_asset('runtime.js') }}}}"></script>
    <script>
      window.Airflow = window.Airflow || {{}};
      Airflow.serverTimezone = Airflow.serverTimezone || 'UTC';
      Airflow.defaultUITimezone = Airflow.defaultUITimezone || 'UTC';
    </script>
    <script src="{{{{ url_for_asset('{chunk_id}.js') }}}}"></script>
    <script src="{{{{ url_for_asset('moment.js') }}}}"></script>"""


def validate_chunk(asset_dir: Path) -> str:
    manifest = json.loads((asset_dir / "manifest.json").read_text(encoding="utf-8"))
    entry_name = manifest.get("moment.js")
    if not isinstance(entry_name, str) or not entry_name:
        raise RuntimeError("FAB asset manifest does not map moment.js")
    ids = set(re.findall(r"\.O\(0,\[(\d+)\]", (asset_dir / entry_name).read_text(encoding="utf-8")))
    if len(ids) != 1:
        raise RuntimeError(f"cannot identify the FAB Moment dependency chunk: {sorted(ids)}")
    chunk_id = ids.pop()
    chunk_name = manifest.get(f"{chunk_id}.js")
    if not isinstance(chunk_name, str) or not chunk_name:
        raise RuntimeError(f"FAB asset manifest does not map {chunk_id}.js")
    chunk = asset_dir / chunk_name
    if not chunk.is_file():
        raise RuntimeError(f"FAB Moment dependency chunk is absent: {chunk}")
    source = chunk.read_text(encoding="utf-8")
    missing = [f for f in ("webpackChunkAirflow", f".push([[{chunk_id}]", ".tz.load(") if f not in source]
    if missing:
        raise RuntimeError(f"unexpected FAB chunk {chunk_id}; missing: {', '.join(missing)}")
    return chunk_id


def patch_template(template: Path, asset_dir: Path) -> tuple[Path, bool]:
    chunk_id = validate_chunk(asset_dir)
    source = template.read_text(encoding="utf-8")
    if MARKER in source:
        required_patch_fragments = (
            "{% if current_user.is_authenticated %}",
            f"url_for_asset('{chunk_id}.js')",
            "Airflow.serverTimezone = Airflow.serverTimezone || 'UTC'",
            "Airflow.defaultUITimezone = Airflow.defaultUITimezone || 'UTC'",
        )
        if source.count(MARKER) != 1 or any(
            fragment not in source for fragment in required_patch_fragments
        ):
            raise RuntimeError("inconsistent existing FAB Moment chunk patch")
        return template, False
    if source.count(TARGET) != 1:
        raise RuntimeError("expected one unpatched FAB runtime/Moment script block")
    patched = source.replace(TARGET, replacement(chunk_id))
    main_script = "  <script src=\"{{ url_for_asset('main.js') }}\"></script>"
    if patched.count(main_script) != 1:
        raise RuntimeError("expected one FAB main script tag")
    patched = patched.replace(main_script, f"    {main_script.strip()}\n  {{% endif %}}")
    template.write_text(patched, encoding="utf-8")
    return template, True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--asset-dir", type=Path, default=DEFAULT_ASSET_DIR)
    args = parser.parse_args()
    template, changed = patch_template(args.template, args.asset_dir)
    print(f"{'patched' if changed else 'already-patched'}: {template}")


if __name__ == "__main__":
    main()
