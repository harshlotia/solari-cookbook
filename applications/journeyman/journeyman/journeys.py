"""Load and validate journey definitions from `journeys/*.json`."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Expectation, Journey, Step

VALID_BACKENDS = {"browser", "desktop"}
VALID_ACTIONS = {"fill", "click", "wait", "open", "type"}


def _parse_step(raw: dict) -> Step:
    action = raw.get("action")
    if action not in VALID_ACTIONS:
        raise ValueError(f"unknown step action {action!r} (expected one of {sorted(VALID_ACTIONS)})")
    return Step(
        action=action,
        selector=raw.get("selector"),
        text=raw.get("text"),
        ms=raw.get("ms"),
    )


def _parse_expectation(raw: dict) -> Expectation:
    return Expectation(
        url_contains=raw.get("url_contains"),
        text_contains=tuple(raw.get("text_contains", ())),
        text_absent=tuple(raw.get("text_absent", ())),
    )


def parse_journey(raw: dict, *, source: str = "<memory>") -> Journey:
    name = raw.get("name")
    if not name:
        raise ValueError(f"{source}: journey is missing 'name'")
    backend = raw.get("backend")
    if backend not in VALID_BACKENDS:
        raise ValueError(f"{source}: unknown backend {backend!r} (expected one of {sorted(VALID_BACKENDS)})")
    if backend == "browser" and not raw.get("url"):
        raise ValueError(f"{source}: backend 'browser' requires a 'url'")
    return Journey(
        name=name,
        backend=backend,
        description=raw.get("description", ""),
        url=raw.get("url"),
        steps=tuple(_parse_step(s) for s in raw.get("steps", ())),
        expect=_parse_expectation(raw.get("expect", {})),
    )


def load_journey_file(path: Path) -> Journey:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return parse_journey(raw, source=str(path))


def load_all_journeys(directory: Path) -> list[Journey]:
    files = sorted(directory.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"no journey files found in {directory}")
    return [load_journey_file(f) for f in files]


def find_journey(directory: Path, name: str) -> Journey:
    for journey in load_all_journeys(directory):
        if journey.name == name:
            return journey
    raise KeyError(f"no journey named {name!r} in {directory}")
