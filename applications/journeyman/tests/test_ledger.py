import tempfile
import unittest
from pathlib import Path

from journeyman.ledger import append_run, get_baseline, read_ledger, set_baseline, short_session


class LedgerTests(unittest.TestCase):
    def test_read_ledger_returns_empty_list_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(read_ledger(Path(d)), [])

    def test_append_run_persists_and_accumulates(self):
        with tempfile.TemporaryDirectory() as d:
            runs_dir = Path(d)
            append_run(runs_dir, {"run_id": "a"})
            append_run(runs_dir, {"run_id": "b"})
            records = read_ledger(runs_dir)
            self.assertEqual([r["run_id"] for r in records], ["a", "b"])

    def test_baseline_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            runs_dir = Path(d)
            self.assertIsNone(get_baseline(runs_dir, "j"))
            set_baseline(runs_dir, "j", b"pngbytes")
            self.assertEqual(get_baseline(runs_dir, "j"), b"pngbytes")

    def test_short_session_truncates_long_ids(self):
        self.assertEqual(short_session("a" * 40), "aaaaaaaaaaaa…")

    def test_short_session_leaves_short_ids_alone(self):
        self.assertEqual(short_session("short"), "short")


if __name__ == "__main__":
    unittest.main()
