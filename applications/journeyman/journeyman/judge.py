"""Decide whether a run passed.

The default judge is deliberately dumb: it reads the page's own visible text,
not screenshots, because that's the check that survives a soft-404, an SPA
shell, or a login wall wearing the site's chrome (see the cookbook's own
`browser-page-assertions-py`). It costs nothing and needs no vendor key.

A second, optional judge asks Claude to look at the screenshot and decide
against a plain-English criterion. It only activates when ANTHROPIC_API_KEY is
set — Journeyman runs, and its live proof was generated, without it.
"""

from __future__ import annotations

import base64
import os

from .models import Evidence, Expectation, Verdict


def heuristic_judge(evidence: Evidence, expect: Expectation) -> Verdict:
    reasons: list[str] = []
    passed = True

    if expect.url_contains and expect.url_contains not in evidence.url:
        passed = False
        reasons.append(f"expected URL to contain {expect.url_contains!r}, got {evidence.url!r}")

    haystack = evidence.visible_text.lower()
    for needle in expect.text_contains:
        if needle.lower() not in haystack:
            passed = False
            reasons.append(f"expected page text to contain {needle!r}")

    for needle in expect.text_absent:
        if needle.lower() in haystack:
            passed = False
            reasons.append(f"expected page text NOT to contain {needle!r}, but it does")

    if passed:
        reasons.append("all text/url expectations satisfied")

    return Verdict(passed=passed, reasons=reasons, judge="heuristic")


def llm_judge_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def llm_judge(evidence: Evidence, criterion: str, *, model: str = "claude-sonnet-5") -> Verdict:
    """Ask Claude to look at the screenshot. Requires ANTHROPIC_API_KEY.

    Kept as an explicit opt-in path rather than the default: a heuristic judge
    is deterministic and reproducible across runs, which matters more for a
    monitor than for a one-off assertion. Use this when the check genuinely
    needs judgment a selector can't express ("does the layout look broken").
    """
    from anthropic import Anthropic  # imported lazily: optional dependency path

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    image_b64 = base64.b64encode(evidence.screenshot_png).decode("ascii")

    response = client.messages.create(
        model=model,
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": image_b64},
                    },
                    {
                        "type": "text",
                        "text": (
                            "You are judging a screenshot from an automated browser run.\n"
                            f"Acceptance criterion: {criterion}\n"
                            "Reply with exactly one line: PASS or FAIL, followed by a dash and a "
                            "one-sentence reason, e.g. 'PASS - success banner is visible'."
                        ),
                    },
                ],
            }
        ],
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text").strip()
    passed = text.upper().startswith("PASS")
    return Verdict(passed=passed, reasons=[text or "no response text"], judge="llm")
