"""Self-contained HTML: one report per run, one index over all of them.

Images are embedded as base64 data URIs so a report.html can be opened
directly from disk or emailed as a single file — no adjacent assets to lose.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

_STYLE = """
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; margin: 0;
       background: #0b0d12; color: #e6e8ee; }
header { padding: 24px 32px; border-bottom: 1px solid #1f2430; }
h1 { margin: 0 0 4px; font-size: 20px; }
.sub { color: #8b93a7; font-size: 13px; }
main { padding: 24px 32px; max-width: 1000px; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px;
         font-weight: 600; letter-spacing: .02em; }
.pass { background: #133a24; color: #57d98a; }
.fail { background: #3a1717; color: #ff7a7a; }
.card { background: #12151d; border: 1px solid #1f2430; border-radius: 10px; padding: 20px;
        margin-bottom: 20px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
img { max-width: 100%; border-radius: 6px; border: 1px solid #1f2430; display: block; }
ul { margin: 8px 0 0; padding-left: 20px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #1f2430; }
th { color: #8b93a7; font-weight: 600; }
a { color: #7aa2ff; text-decoration: none; }
a:hover { text-decoration: underline; }
code { background: #1a1e28; padding: 1px 6px; border-radius: 4px; }
"""


def _img_data_uri(png_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")


def render_run_report(record: dict, screenshot_png: bytes, diff_png: bytes | None) -> str:
    badge = "pass" if record["passed"] else "fail"
    label = "PASS" if record["passed"] else "FAIL"
    reasons = "".join(f"<li>{html.escape(r)}</li>" for r in record["verdict_reasons"])

    diff_block = ""
    if diff_png is not None:
        diff_block = f"""
        <div class="card">
          <h3>Visual diff vs. last known-good baseline</h3>
          <p>{html.escape(record["diff_note"])}</p>
          <img src="{_img_data_uri(diff_png)}" alt="diff highlighting changed pixels in red">
        </div>
        """
    elif record.get("diff_note"):
        diff_block = f'<div class="card"><h3>Visual diff</h3><p>{html.escape(record["diff_note"])}</p></div>'

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Journeyman — {html.escape(record['journey'])}</title>
<style>{_STYLE}</style></head>
<body>
<header>
  <h1>{html.escape(record['journey'])} <span class="badge {badge}">{label}</span></h1>
  <div class="sub">{html.escape(record['backend'])} backend · {html.escape(record['timestamp'])} ·
    run <code>{html.escape(record['run_id'])}</code> · session <code>{html.escape(record['session_id_short'])}</code> ·
    {record['duration_ms']} ms</div>
</header>
<main>
  <div class="card">
    <h3>Verdict ({html.escape(record['judge'])} judge)</h3>
    <ul>{reasons}</ul>
  </div>
  <div class="card">
    <h3>Screenshot</h3>
    <img src="{_img_data_uri(screenshot_png)}" alt="run screenshot">
  </div>
  {diff_block}
  <p><a href="index.html">&larr; back to dashboard</a></p>
</main>
</body></html>"""


def render_index(records: list[dict]) -> str:
    rows = []
    for r in reversed(records):
        badge = "pass" if r["passed"] else "fail"
        label = "PASS" if r["passed"] else "FAIL"
        diff_cell = f"{r['diff_pct']}%" if r.get("diff_pct") is not None else "—"
        rows.append(f"""<tr>
          <td><a href="{html.escape(r['run_id'])}/report.html">{html.escape(r['journey'])}</a></td>
          <td>{html.escape(r['backend'])}</td>
          <td><span class="badge {badge}">{label}</span></td>
          <td>{diff_cell}</td>
          <td>{html.escape(r['timestamp'])}</td>
          <td>{r['duration_ms']} ms</td>
        </tr>""")

    total = len(records)
    passed = sum(1 for r in records if r["passed"])

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Journeyman dashboard</title>
<style>{_STYLE}</style></head>
<body>
<header>
  <h1>Journeyman</h1>
  <div class="sub">{passed}/{total} passing · {total} run{'s' if total != 1 else ''} recorded</div>
</header>
<main>
  <div class="card">
    <table>
      <tr><th>Journey</th><th>Backend</th><th>Result</th><th>Visual diff</th><th>When</th><th>Duration</th></tr>
      {''.join(rows) if rows else '<tr><td colspan="6">No runs yet — try <code>journeyman demo</code> or <code>journeyman run --all</code>.</td></tr>'}
    </table>
  </div>
</main>
</body></html>"""


def write_run_artifacts(runs_dir: Path, record: dict, screenshot_png: bytes, diff_png: bytes | None) -> None:
    run_dir = runs_dir / record["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    # named "capture.png", not "screenshot.png": the cookbook's root .gitignore
    # excludes the latter globally so throwaway example output stays untracked,
    # which would silently drop this proof bundle's actual evidence.
    (run_dir / "capture.png").write_bytes(screenshot_png)
    if diff_png is not None:
        (run_dir / "diff.png").write_bytes(diff_png)
    (run_dir / "report.html").write_text(render_run_report(record, screenshot_png, diff_png), encoding="utf-8")


def write_index(runs_dir: Path, records: list[dict]) -> None:
    (runs_dir / "index.html").write_text(render_index(records), encoding="utf-8")
