import unittest

from journeyman.judge import heuristic_judge
from journeyman.models import Evidence, Expectation


def _evidence(url="https://example.com/secure", text="You logged into a secure area!") -> Evidence:
    return Evidence(title="t", url=url, visible_text=text, screenshot_png=b"", session_id="s", duration_ms=1)


class HeuristicJudgeTests(unittest.TestCase):
    def test_passes_when_all_expectations_met(self):
        expect = Expectation(url_contains="/secure", text_contains=("secure area",), text_absent=("invalid",))
        verdict = heuristic_judge(_evidence(), expect)
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.judge, "heuristic")

    def test_fails_when_required_text_missing(self):
        expect = Expectation(text_contains=("Welcome, Admin Dashboard",))
        verdict = heuristic_judge(_evidence(), expect)
        self.assertFalse(verdict.passed)
        self.assertIn("Welcome, Admin Dashboard", verdict.reasons[0])

    def test_fails_when_forbidden_text_present(self):
        expect = Expectation(text_absent=("invalid",))
        verdict = heuristic_judge(_evidence(text="Your password is invalid!"), expect)
        self.assertFalse(verdict.passed)

    def test_fails_when_url_does_not_match(self):
        expect = Expectation(url_contains="/secure")
        verdict = heuristic_judge(_evidence(url="https://example.com/login"), expect)
        self.assertFalse(verdict.passed)

    def test_case_insensitive_text_match(self):
        expect = Expectation(text_contains=("SECURE AREA",))
        verdict = heuristic_judge(_evidence(text="you logged into a secure area!"), expect)
        self.assertTrue(verdict.passed)

    def test_empty_expectation_always_passes(self):
        verdict = heuristic_judge(_evidence(), Expectation())
        self.assertTrue(verdict.passed)


if __name__ == "__main__":
    unittest.main()
