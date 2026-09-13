"""Wire one journey through: backend run -> judge -> sandbox diff -> ledger."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from . import judge as judge_mod
from . import ledger, report
from .browser_backend import run_browser_journey
from .desktop_backend import run_desktop_journey
from .diff import SandboxDiffer
from .journeys import Journey


def _run_id(journey_name: str) -> str:
    return f"{journey_name}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:6]}"


async def run_live_journey(journey: Journey, *, api_key: str, runs_dir: Path, differ: SandboxDiffer | None) -> dict:
    """Run one journey against real Solari, judge it, diff it, and record it."""
    if journey.backend == "browser":
        evidence = await run_browser_journey(journey, api_key=api_key)
    elif journey.backend == "desktop":
        evidence = await run_desktop_journey(journey, api_key=api_key)
    else:
        raise ValueError(f"unknown backend {journey.backend!r}")

    if judge_mod.llm_judge_available() and journey.description:
        verdict = judge_mod.llm_judge(evidence, journey.description)
    else:
        verdict = judge_mod.heuristic_judge(evidence, journey.expect)

    baseline = ledger.get_baseline(runs_dir, journey.name)
    if differ is not None:
        diff_result = await differ.diff(baseline, evidence.screenshot_png)
    else:
        diff_result = None

    if verdict.passed:
        ledger.set_baseline(runs_dir, journey.name, evidence.screenshot_png)

    record = {
        "run_id": _run_id(journey.name),
        "journey": journey.name,
        "backend": journey.backend,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "passed": verdict.passed,
        "judge": verdict.judge,
        "verdict_reasons": verdict.reasons,
        "session_id_short": ledger.short_session(evidence.session_id),
        "duration_ms": evidence.duration_ms,
        "diff_pct": diff_result.pct_changed if diff_result else None,
        "diff_note": diff_result.note if diff_result else "sandbox diffing disabled for this run",
    }

    diff_png = diff_result.diff_png if diff_result else None
    report.write_run_artifacts(runs_dir, record, evidence.screenshot_png, diff_png)
    ledger.append_run(runs_dir, record)
    report.write_index(runs_dir, ledger.read_ledger(runs_dir))
    return record
