from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATCH_SCRIPT = Path(__file__).parents[1] / "airflow" / "fix_fab_moment_bundle.py"
SPEC = importlib.util.spec_from_file_location("fix_fab_moment_bundle", PATCH_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load patch script: {PATCH_SCRIPT}")
PATCH_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH_MODULE)

MARKER = PATCH_MODULE.MARKER
TARGET = PATCH_MODULE.TARGET
patch_template = PATCH_MODULE.patch_template

VALID_TEMPLATE = f"""{{% block tail_js %}}
{TARGET}
  <script src="{{{{ url_for_asset('main.js') }}}}"></script>
{{% endblock %}}
"""
VALID_CHUNK = """
(self.webpackChunkAirflow=self.webpackChunkAirflow||[]).push([[844],{
  844(module,exports,require){(module.exports=require(356)).tz.load(require(500))}
}]);
"""


class FabMomentTemplatePatchTests(unittest.TestCase):
    def make_assets(self, directory: Path, chunk: str = VALID_CHUNK) -> Path:
        asset_dir = directory / "dist"
        asset_dir.mkdir()
        (asset_dir / "manifest.json").write_text(
            json.dumps({"844.js": "844.test.js"}), encoding="utf-8"
        )
        (asset_dir / "844.test.js").write_text(chunk, encoding="utf-8")
        return asset_dir

    def test_patch_is_idempotent_and_orders_dependency_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "main.html"
            template.write_text(VALID_TEMPLATE, encoding="utf-8")
            asset_dir = self.make_assets(root)

            patched, changed = patch_template(template, asset_dir)
            self.assertEqual(template, patched)
            self.assertTrue(changed)
            result = template.read_text(encoding="utf-8")
            self.assertEqual(1, result.count(MARKER))
            self.assertLess(result.index("844.js"), result.index("moment.js"))
            self.assertIn("{% if current_user.is_authenticated %}", result)
            self.assertIn("{% endif %}", result)
            self.assertIn(
                "Airflow.serverTimezone = Airflow.serverTimezone || 'UTC'", result
            )
            self.assertIn(
                "Airflow.defaultUITimezone = Airflow.defaultUITimezone || 'UTC'", result
            )

            _, changed_again = patch_template(template, asset_dir)
            self.assertFalse(changed_again)
            self.assertEqual(1, template.read_text(encoding="utf-8").count(MARKER))

    def test_patch_rejects_unexpected_template(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "main.html"
            template.write_text("{% block tail_js %}{% endblock %}", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "expected one unpatched"):
                patch_template(template, self.make_assets(root))

    def test_patch_rejects_unexpected_dependency_chunk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "main.html"
            template.write_text(VALID_TEMPLATE, encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unexpected FAB chunk 844"):
                patch_template(template, self.make_assets(root, "not the expected chunk"))


if __name__ == "__main__":
    unittest.main()
