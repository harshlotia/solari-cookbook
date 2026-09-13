import tempfile
import unittest
from pathlib import Path

from journeyman.report import render_index, render_run_report, write_run_artifacts

RECORD = {
    "run_id": "demo-1",
    "journey": "login-success",
    "backend": "browser",
    "timestamp": "2026-01-01 00:00:00 UTC",
    "passed": True,
    "judge": "heuristic",
    "verdict_reasons": ["all text/url expectations satisfied"],
    "session_id_short": "abc123",
    "duration_ms": 1234,
    "diff_pct": 0.0,
    "diff_note": "0.0% of pixels changed vs. last known-good baseline",
}

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)


class ReportRenderingTests(unittest.TestCase):
    def test_run_report_shows_pass_badge_and_reasons(self):
        html_out = render_run_report(RECORD, TINY_PNG, None)
        self.assertIn("PASS", html_out)
        self.assertIn("login-success", html_out)
        self.assertIn("all text/url expectations satisfied", html_out)

    def test_run_report_shows_fail_badge(self):
        failing = dict(RECORD, passed=False, verdict_reasons=["expected page text to contain 'x'"])
        html_out = render_run_report(failing, TINY_PNG, None)
        self.assertIn("FAIL", html_out)

    def test_run_report_includes_diff_image_when_present(self):
        html_out = render_run_report(RECORD, TINY_PNG, TINY_PNG)
        self.assertIn("Visual diff", html_out)

    def test_index_reports_pass_count(self):
        html_out = render_index([RECORD, dict(RECORD, run_id="demo-2", passed=False)])
        self.assertIn("1/2 passing", html_out)

    def test_index_handles_empty_ledger(self):
        html_out = render_index([])
        self.assertIn("No runs yet", html_out)

    def test_write_run_artifacts_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as d:
            runs_dir = Path(d)
            write_run_artifacts(runs_dir, RECORD, TINY_PNG, None)
            run_dir = runs_dir / RECORD["run_id"]
            self.assertTrue((run_dir / "capture.png").exists())
            self.assertTrue((run_dir / "report.html").exists())
            self.assertFalse((run_dir / "diff.png").exists())


if __name__ == "__main__":
    unittest.main()
