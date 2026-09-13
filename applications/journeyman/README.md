# Journeyman

**A synthetic monitor that judges what a page actually shows, not just that
navigation succeeded — then proves a visual regression that a text check
would miss.**

Most uptime/E2E monitors either assert on brittle CSS selectors or trust that
a 200 response means the page is fine. Journeyman walks a real user journey
in a real Solari cloud browser (or a Solari Desktop, for GUI targets), reads
the page's own visible text to decide pass/fail — the check the cookbook's
own [`browser-page-assertions-py`](../../examples/browser-page-assertions-py)
example encodes as the one that survives a soft-404 or a login wall wearing
the site's chrome — and then goes one step further: it forks a Solari Sandbox
to pixel-diff the screenshot against the last known-good run. That catches
the case a text check can't: the page says everything it's supposed to say,
and still looks broken.

> A login form that returns the right words in a badly-clipped layout still
> passes a `text_contains` check. Journeyman still tells you the layout moved.

## The proof

A committed, sanitized run against real Solari infrastructure lives in
[`proof/live`](proof/live) — no credentials needed to look at it:

```bash
cd applications/journeyman
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
python -m pip install .
python -m journeyman serve --directory proof/live
```

Open http://127.0.0.1:8787/index.html. It shows two live runs of five journeys
against [the-internet.herokuapp.com](https://the-internet.herokuapp.com) (a
public site built for exactly this kind of automation, not a scrape target)
across the **browser** and **desktop** backends:

| Journey | Backend | What it proves |
| --- | --- | --- |
| `login-success` | browser | valid credentials reach the secure area; 0.0% diff on repeat |
| `login-invalid-credentials` | browser | the app correctly rejects a bad password (a negative-path check, not a bug) |
| `dynamic-content-visual-drift` | browser | header/copy stay stable (heuristic **passes** both times) while the page's own randomized content drifts **4.18%** — caught only by the sandbox diff |
| `desktop-notepad-smoke` | desktop | Mousepad opens and accepts input on a real Solari Desktop; 0.0% diff on repeat |
| `_demo_intentional_failure` | browser | deliberately asserts text the app never shows, to prove the failure path and incident report actually fire — **not** a real bug in the target site |

Every pixel-diff in that bundle was computed inside a disposable Solari
Sandbox, not on the machine that ran the CLI.

## Run it yourself

```bash
cd applications/journeyman
python -m venv .venv && source .venv/bin/activate
python -m pip install .
cp .env.example .env   # then edit it — see below
export SOLARI_API_KEY=slr_live_...

python -m journeyman demo          # offline, no keys — see the pipeline work in seconds
python -m journeyman list          # see the bundled journeys
python -m journeyman run --all     # live, against real Solari (run twice to see a diff)
python -m journeyman serve         # dashboard over ./runs
```

On Windows PowerShell, replace the activation command with
`.venv\Scripts\Activate.ps1`; the remaining commands are the same.

## Write your own journey

Drop a JSON file in `journeys/`:

```json
{
  "name": "checkout-smoke",
  "backend": "browser",
  "description": "A shopper reaches the order-confirmation page after checkout.",
  "url": "https://example.com/cart",
  "steps": [
    { "action": "click", "selector": "#checkout" },
    { "action": "fill", "selector": "#card-number", "text": "4242 4242 4242 4242" },
    { "action": "click", "selector": "#place-order" }
  ],
  "expect": {
    "url_contains": "/confirmation",
    "text_contains": ["Thanks for your order"],
    "text_absent": ["error", "declined"]
  }
}
```

`backend: "desktop"` journeys use `open` (launch an app by name), `type`
(keyboard input), and `click` with `"x,y"` as the selector, since a GUI target
has no CSS selectors to click — see
[`desktop-notepad-smoke.json`](journeys/desktop-notepad-smoke.json).

## What it needs, honestly

- **`SOLARI_API_KEY`** — required for `journeyman run`. Not read by
  `journeyman demo`, which ships its own fixture screenshots and needs no
  network access at all.
- **`ANTHROPIC_API_KEY`** — optional. When set, a journey with a
  `description` is judged by Claude looking at the actual screenshot instead
  of the deterministic text/URL heuristic (`journeyman/judge.py:llm_judge`).
  It is **not** used anywhere in the committed `proof/live` bundle — every
  verdict in there came from the heuristic judge, which needs no vendor key
  beyond Solari's. Turning this on trades determinism for judgment: useful
  when "does this look broken" genuinely can't be expressed as a selector.

## Why Sandbox for a pixel diff, not just Pillow in-process

The comparison could run wherever the CLI runs. It runs inside a disposable
Solari Sandbox instead because the two screenshots being compared can come
from a target neither the CLI's host nor its operator controls, and because
that's the same reason [`sandbox-scan-untrusted-code-ts`](../../examples/sandbox-scan-untrusted-code-ts)
runs code there rather than locally. One sandbox is created per `run --all`
invocation and reused across every journey's diff, then destroyed —
[`journeyman/diff.py`](journeyman/diff.py) never creates more than one at a
time, which matters on Solari's free tier (one concurrent sandbox or
desktop). The exact function that runs remotely
(`journeyman/diff_algorithm.py:compute_diff`) is unit-tested locally via
`inspect.getsource` — see [`tests/test_diff.py`](tests/test_diff.py) for the
regression this caught: the first live run threw `NameError: io` because
`getsource` captures a function's body, not the `import io` above it in the
same file.

## Test

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

All 36 tests are offline and deterministic — no Solari key required.

## Evidence contract

Every run records: the journey and backend, a timestamp, the judge used and
its reasons, a shortened session id, duration, and the sandbox diff
percentage against the previous passing baseline. The Solari API key is never
read into a report, the ledger, or a screenshot. Session ids are truncated
before they're written (`journeyman/ledger.py:short_session`). A baseline
only updates when a run passes, so a broken run can never become the
reference a later run is judged against.

## Non-goals

- Three bundled journeys against a public QA-testing site is a proof of the
  execution and evidence layer, not a claim that Journeyman ships a journey
  library for your product — you write your own, same as any monitoring tool.
- The heuristic judge reads visible text; it does not understand layout,
  color, or accessibility on its own. That gap is exactly what the sandbox
  diff exists to cover, and the LLM judge is the opt-in path when text and
  pixels both fall short of the actual question ("does this look right").
- `dynamic-content-visual-drift` is honestly noisy by construction — the
  target page randomizes its content on every load, so its diff percentage
  will never settle at 0%. A production deployment would want a
  per-journey drift threshold; this repo reports the raw number instead of
  inventing one.
