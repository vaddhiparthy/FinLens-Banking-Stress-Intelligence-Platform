"""Load the generated FAB Moment dependency chunk before its entry bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FAB_ROOT = Path(
    "/home/airflow/.local/lib/python3.11/site-packages/airflow/providers/fab/www"
)
DEFAULT_TEMPLATE = FAB_ROOT / "templates/airflow/main.html"
DEFAULT_ASSET_DIR = FAB_ROOT / "static/dist"
MARKER = "finlens-fab-moment-chunk-load-v1"
TARGET = """  <script src="{{ url_for_asset('runtime.js') }}"></script>
  <script src="{{ url_for_asset('moment.js') }}"></script>"""
REPLACEMENT = f"""  {{# {MARKER}: legacy FAB page assets require authenticated page context #}}
  {{% if current_user.is_authenticated %}}
    <script src="{{{{ url_for_asset('runtime.js') }}}}"></script>
    <script>
      window.Airflow = window.Airflow || {{}};
      Airflow.serverTimezone = Airflow.serverTimezone || 'UTC';
      Airflow.defaultUITimezone = Airflow.defaultUITimezone || 'UTC';
    </script>
    <script src="{{{{ url_for_asset('844.js') }}}}"></script>
    <script src="{{{{ url_for_asset('moment.js') }}}}"></script>"""


def validate_chunk(asset_dir: Path) -> Path:
    manifest_path = asset_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunk_name = manifest.get("844.js")
    if not isinstance(chunk_name, str) or not chunk_name:
        raise RuntimeError("FAB asset manifest does not map 844.js")

    chunk = asset_dir / chunk_name
    if not chunk.is_file():
        raise RuntimeError(f"FAB Moment dependency chunk is absent: {chunk}")
    source = chunk.read_text(encoding="utf-8")
    required_fragments = (
        "webpackChunkAirflow",
        ".push([[844]",
        ".tz.load(",
    )
    missing = [fragment for fragment in required_fragments if fragment not in source]
    if missing:
        raise RuntimeError(f"unexpected FAB chunk 844; missing: {', '.join(missing)}")
    return chunk


def patch_template(template: Path, asset_dir: Path) -> tuple[Path, bool]:
    validate_chunk(asset_dir)
    source = template.read_text(encoding="utf-8")
    if MARKER in source:
        required_patch_fragments = (
            "{% if current_user.is_authenticated %}",
            "url_for_asset('844.js')",
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
    patched = source.replace(TARGET, REPLACEMENT)
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
