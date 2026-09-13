import json
import tempfile
import unittest
from pathlib import Path

from journeyman.journeys import find_journey, load_all_journeys, load_journey_file, parse_journey


class ParseJourneyTests(unittest.TestCase):
    def test_parses_a_full_browser_journey(self):
        raw = {
            "name": "example",
            "backend": "browser",
            "description": "d",
            "url": "https://example.com",
            "steps": [{"action": "fill", "selector": "#x", "text": "y"}],
            "expect": {"url_contains": "/x", "text_contains": ["a"], "text_absent": ["b"]},
        }
        journey = parse_journey(raw)
        self.assertEqual(journey.name, "example")
        self.assertEqual(journey.steps[0].action, "fill")
        self.assertEqual(journey.expect.text_contains, ("a",))

    def test_rejects_missing_name(self):
        with self.assertRaises(ValueError):
            parse_journey({"backend": "browser", "url": "https://x"})

    def test_rejects_unknown_backend(self):
        with self.assertRaises(ValueError):
            parse_journey({"name": "n", "backend": "carrier-pigeon"})

    def test_browser_backend_requires_url(self):
        with self.assertRaises(ValueError):
            parse_journey({"name": "n", "backend": "browser"})

    def test_desktop_backend_does_not_require_url(self):
        journey = parse_journey({"name": "n", "backend": "desktop", "steps": [{"action": "open", "text": "mousepad"}]})
        self.assertIsNone(journey.url)

    def test_rejects_unknown_step_action(self):
        with self.assertRaises(ValueError):
            parse_journey({"name": "n", "backend": "browser", "url": "https://x", "steps": [{"action": "teleport"}]})


class LoadJourneyFilesTests(unittest.TestCase):
    def test_load_all_journeys_reads_every_json_file(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            (directory / "a.json").write_text(json.dumps({"name": "a", "backend": "browser", "url": "https://x"}))
            (directory / "b.json").write_text(json.dumps({"name": "b", "backend": "desktop"}))
            journeys = load_all_journeys(directory)
            self.assertEqual({j.name for j in journeys}, {"a", "b"})

    def test_load_all_journeys_raises_on_empty_directory(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                load_all_journeys(Path(d))

    def test_find_journey_by_name(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            (directory / "a.json").write_text(json.dumps({"name": "a", "backend": "browser", "url": "https://x"}))
            journey = find_journey(directory, "a")
            self.assertEqual(journey.name, "a")

    def test_find_journey_raises_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            (directory / "a.json").write_text(json.dumps({"name": "a", "backend": "browser", "url": "https://x"}))
            with self.assertRaises(KeyError):
                find_journey(directory, "nope")

    def test_load_journey_file_reports_path_on_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.json"
            path.write_text(json.dumps({"backend": "browser"}))
            with self.assertRaises(ValueError):
                load_journey_file(path)


if __name__ == "__main__":
    unittest.main()
