"""`journeyman demo` — the full pipeline with zero setup and zero network calls.

Runs three canned scenarios against bundled fixture screenshots (see
`journeyman/static/`) so a reader can see a passing run, a caught visual
regression, and a caught content failure without a Solari key or an Anthropic
key. The diff math is the same `compute_diff` that runs inside a real Solari
Sandbox in live mode — only the transport (in-process vs. a microVM) differs,
which is called out in each demo run's report.
"""

from __future__ import annotations

import time
import uuid
from importlib import resources
from pathlib import Path

from . import judge as judge_mod
from . import ledger, report
from .diff_algorithm import compute_diff
from .models import Evidence, Expectation

PASS_TEXT = "You logged into a secure area!"


def _fixture(name: str) -> bytes:
    return (resources.files("journeyman.static") / name).read_bytes()


def _demo_run_id(name: str) -> str:
    return f"{name}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:6]}"


def _record(runs_dir: Path, name: str, backend: str, verdict, screenshot: bytes, diff_png: bytes | None, diff_pct: float | None, diff_note: str) -> dict:
    record = {
        "run_id": _demo_run_id(name),
        "journey": name,
        "backend": backend,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "passed": verdict.passed,
        "judge": verdict.judge,
        "verdict_reasons": verdict.reasons,
        "session_id_short": "offline-demo",
        "duration_ms": 0,
        "diff_pct": diff_pct,
        "diff_note": diff_note,
    }
    report.write_run_artifacts(runs_dir, record, screenshot, diff_png)
    ledger.append_run(runs_dir, record)
    return record


def run_demo(runs_dir: Path) -> list[dict]:
    runs_dir.mkdir(parents=True, exist_ok=True)
    baseline = _fixture("demo_baseline.png")
    records = []

    expect = Expectation(text_contains=(PASS_TEXT,), text_absent=("error",))

    # Scenario 1: a clean repeat run. Establishes the baseline and passes.
    ev = Evidence(title="Secure Area", url="demo://login-success", visible_text=PASS_TEXT, screenshot_png=baseline, session_id="demo", duration_ms=0)
    verdict = judge_mod.heuristic_judge(ev, expect)
    records.append(_record(runs_dir, "demo-login-success", "browser", verdict, baseline, None, None,
                            "no baseline yet; this run becomes the baseline"))
    ledger.set_baseline(runs_dir, "demo-login-success", baseline)

    # Scenario 2: same journey, visually different page (a promo banner appeared).
    # The text the heuristic checks for is still there, so it still PASSES —
    # this is the case a text-only monitor would miss and Journeyman's sandbox
    # diff exists to catch.
    drift = _fixture("demo_drift.png")
    ev2 = Evidence(title="Secure Area", url="demo://login-success", visible_text=PASS_TEXT, screenshot_png=drift, session_id="demo", duration_ms=0)
    verdict2 = judge_mod.heuristic_judge(ev2, expect)
    pct, diff_png = compute_diff(baseline, drift)
    records.append(_record(runs_dir, "demo-login-success", "browser", verdict2, drift, diff_png, pct,
                            f"{pct}% of pixels changed vs. baseline (computed in-process for this offline demo; "
                            f"`journeyman run` computes the identical function inside a Solari Sandbox)"))

    # Scenario 3: a real content failure — the success banner is gone.
    broken = _fixture("demo_fail.png")
    ev3 = Evidence(title="Secure Area", url="demo://login-success", visible_text="500 Internal Server Error", screenshot_png=broken, session_id="demo", duration_ms=0)
    verdict3 = judge_mod.heuristic_judge(ev3, expect)
    pct3, diff_png3 = compute_diff(baseline, broken)
    records.append(_record(runs_dir, "demo-login-broken", "browser", verdict3, broken, diff_png3, pct3,
                            f"{pct3}% of pixels changed vs. baseline"))

    report.write_index(runs_dir, ledger.read_ledger(runs_dir))
    return records
