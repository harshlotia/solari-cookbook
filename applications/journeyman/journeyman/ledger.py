"""Run history: one JSON file plus one directory per run.

Deliberately just files, no database — a run directory is self-contained
evidence (screenshot, optional diff image, report.html) and `ledger.json` is
an index over them. Never stores the Solari API key; session ids are
shortened before they're written, matching the evidence-contract convention
the cookbook's `worldline` application already established.
"""

from __future__ import annotations

import json
from pathlib import Path


def short_session(session_id: str) -> str:
    return session_id[:12] + "…" if len(session_id) > 12 else session_id


def ledger_path(runs_dir: Path) -> Path:
    return runs_dir / "ledger.json"


def read_ledger(runs_dir: Path) -> list[dict]:
    path = ledger_path(runs_dir)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def append_run(runs_dir: Path, record: dict) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    records = read_ledger(runs_dir)
    records.append(record)
    ledger_path(runs_dir).write_text(json.dumps(records, indent=2), encoding="utf-8")


def baseline_path(runs_dir: Path, journey_name: str) -> Path:
    return runs_dir / "baselines" / f"{journey_name}.png"


def get_baseline(runs_dir: Path, journey_name: str) -> bytes | None:
    path = baseline_path(runs_dir, journey_name)
    return path.read_bytes() if path.exists() else None


def set_baseline(runs_dir: Path, journey_name: str, png_bytes: bytes) -> None:
    path = baseline_path(runs_dir, journey_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes)
