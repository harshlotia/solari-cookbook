"""The pixel-diff algorithm, kept as one dependency-light, testable function.

`diff.py`'s SandboxDiffer ships the exact source of `compute_diff` (via
`inspect.getsource`) into a Solari Sandbox and runs it there, so the code this
module's tests exercise locally is byte-for-byte what executes remotely. That
is the whole point of routing this through Sandbox rather than doing it
in-process: the comparison runs in a disposable microVM, not on whatever
machine happened to invoke the CLI.
"""

from __future__ import annotations

import io


def compute_diff(baseline_bytes: bytes, current_bytes: bytes) -> tuple[float, bytes]:
    """Return (pct_pixels_changed, diff_png_bytes).

    Images are resized to the smaller of the two shapes before comparing, so a
    baseline captured at a different viewport doesn't crash the run — it just
    reports a (probably large) diff, which is the honest answer anyway.
    """
    from PIL import Image, ImageChops

    baseline = Image.open(io.BytesIO(baseline_bytes)).convert("RGB")
    current = Image.open(io.BytesIO(current_bytes)).convert("RGB")

    if baseline.size != current.size:
        w = min(baseline.size[0], current.size[0])
        h = min(baseline.size[1], current.size[1])
        baseline = baseline.resize((w, h))
        current = current.resize((w, h))

    diff = ImageChops.difference(baseline, current)
    mask = diff.convert("L").point(lambda p: 255 if p > 24 else 0)

    changed = sum(1 for p in mask.getdata() if p)
    total = mask.size[0] * mask.size[1]
    pct_changed = round(100.0 * changed / total, 2) if total else 0.0

    highlight = current.copy()
    red_layer = Image.new("RGB", current.size, (255, 0, 0))
    highlight = Image.composite(red_layer, highlight, mask)

    out = io.BytesIO()
    highlight.save(out, format="PNG")
    return pct_changed, out.getvalue()
