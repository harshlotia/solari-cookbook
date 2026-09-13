# Journeyman design

## Pipeline

```text
journey.json -> BACKEND RUN -> JUDGE -> SANDBOX DIFF -> LEDGER + REPORT
                (browser or          (heuristic          (vs. last
                 desktop)             or LLM)             passing
                                                           baseline)
```

One journey produces one `Evidence` object (title, url, visible text,
screenshot, session id, duration) regardless of which backend produced it.
Everything downstream — judging, diffing, recording, reporting — operates on
that shape, not on browser- or desktop-specific state. Adding a third backend
means writing one function that returns `Evidence`; nothing else changes.

## Trust boundaries

A journey definition controls only its own steps and expectations. It does
not control:

- which judge runs (heuristic by default; LLM only when a key is present and
  the journey happens to carry a `description`);
- baseline selection (always "the last run that passed", never "the last
  run", so a broken run can't poison the reference future runs are judged
  against);
- where the diff executes (always a fresh-per-invocation Solari Sandbox, never
  the caller's machine);
- what gets written to the ledger.

## Why one sandbox per invocation, not one per journey

Solari's free tier permits one concurrent sandbox or desktop. `journeyman run
--all` creates a single `SandboxDiffer` and threads it through every journey
sequentially, so five journeys with diffs cost one sandbox boot, not five.
Desktop and browser journeys still get their own session per journey — those
aren't reusable the way a stateless diff computation is.

## Observed platform behavior

`inspect.getsource(compute_diff)` returns only the function's body, not the
`import io` sitting above it at module scope in the same file. The first live
run against real Solari infrastructure caught this immediately: every diff
call failed with `NameError: name 'io' is not defined` inside the sandbox,
while the identical function worked fine locally under `unittest` because the
test file imports `io` itself at the top. `journeyman/diff.py` now prepends
that import explicitly to the generated script, and
`tests/test_diff.py::test_script_runs_end_to_end_against_real_files` executes
the generated script (not just the local function) so this class of bug fails
a local test run instead of a live one.

The free-tier account this was built against successfully created a browser,
a sandbox, and a desktop session in sequence — see `proof/live` for a real
five-journey run spanning both the browser and desktop backends alongside
sandbox-based diffing. Sessions were never run concurrently across backends;
this repo has not tested concurrent multi-backend use against a free-tier
account.

## Evidence format

`ledger.json` is an append-only list. Each entry: `run_id`, `journey`,
`backend`, `timestamp`, `passed`, `judge` (`"heuristic"` or `"llm"`),
`verdict_reasons`, a shortened `session_id_short`, `duration_ms`, and
`diff_pct` (`null` until a baseline exists). The API key is loaded from
process environment or an ignored `.env` and is never copied into a report,
the ledger, a screenshot, or a diff image.

## Non-goals

See the README's Non-goals section — it covers judge scope and the
intentionally noisy `dynamic-content-visual-drift` journey, which are design
decisions rather than implementation details.
