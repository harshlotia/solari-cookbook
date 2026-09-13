"""Data shapes shared across Journeyman's modules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Step:
    """One browser/desktop action. `action` selects which fields matter."""

    action: str  # "fill" | "click" | "wait" | "open" | "type"
    selector: str | None = None
    text: str | None = None
    ms: int | None = None


@dataclass(frozen=True)
class Expectation:
    """What a passing run must show. Evaluated against visible text, not markup."""

    url_contains: str | None = None
    text_contains: tuple[str, ...] = ()
    text_absent: tuple[str, ...] = ()


@dataclass(frozen=True)
class Journey:
    name: str
    backend: str  # "browser" | "desktop"
    description: str
    url: str | None = None  # required for backend == "browser"
    steps: tuple[Step, ...] = ()
    expect: Expectation = field(default_factory=Expectation)


@dataclass
class Evidence:
    """What a backend run produced, independent of whether it passed."""

    title: str
    url: str
    visible_text: str
    screenshot_png: bytes
    session_id: str
    duration_ms: int


@dataclass
class Verdict:
    passed: bool
    reasons: list[str]
    judge: str  # "heuristic" | "llm"


@dataclass
class DiffResult:
    compared: bool  # False when there was no baseline yet
    pct_changed: float | None
    diff_png: bytes | None
    note: str


@dataclass
class RunResult:
    run_id: str
    journey: str
    backend: str
    timestamp: str
    passed: bool
    verdict: Verdict
    diff: DiffResult
    session_id_short: str
    duration_ms: int
    screenshot_path: str
    diff_path: str | None
