"""Regression coverage for the script Journeyman ships into a live sandbox.

`SandboxDiffer` builds its remote script from `inspect.getsource(compute_diff)`,
which captures only the function body — not the `import io` line at module
scope in diff_algorithm.py that the body relies on. A live run against a real
Solari sandbox caught this (NameError: io is not defined) before this test
existed; it's here so the next refactor of diff_algorithm.py can't
reintroduce it silently, since nothing about it fails locally without
actually executing the generated script.
"""

import unittest

from journeyman.diff import _build_script


class BuildScriptTests(unittest.TestCase):
    def test_script_compiles(self):
        compile(_build_script(), "<sandbox-script>", "exec")

    def test_script_imports_everything_compute_diff_uses(self):
        script = _build_script()
        self.assertIn("import io", script)
        self.assertIn("def compute_diff", script)
        # the import must precede the function body, not follow it
        self.assertLess(script.index("import io"), script.index("def compute_diff"))

    def test_script_runs_end_to_end_against_real_files(self):
        import io
        import tempfile
        from pathlib import Path

        from PIL import Image

        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "journeyman_baseline.png"
            current = Path(d) / "journeyman_current.png"
            out = Path(d) / "journeyman_diff.png"

            buf = io.BytesIO()
            Image.new("RGB", (10, 10), (1, 2, 3)).save(buf, format="PNG")
            base.write_bytes(buf.getvalue())
            current.write_bytes(buf.getvalue())

            script = _build_script()
            script = script.replace("/tmp/journeyman_baseline.png", base.as_posix())
            script = script.replace("/tmp/journeyman_current.png", current.as_posix())
            script = script.replace("/tmp/journeyman_diff.png", out.as_posix())
            exec(compile(script, "<sandbox-script>", "exec"), {})

            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
