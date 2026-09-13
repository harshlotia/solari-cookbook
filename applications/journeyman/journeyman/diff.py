"""Run the pixel diff inside a disposable Solari Sandbox.

Why bother routing a Pillow call through a microVM instead of just importing
`diff_algorithm` in-process? Two reasons this project cares about: the two
screenshots being compared can come from an untrusted or third-party render
(a customer's page, a GUI app neither of us wrote), and running the comparison
next to disposable, network-isolated compute is exactly the case Sandbox
exists for — same reason `sandbox-scan-untrusted-code-ts` runs code there
instead of on the caller's machine. The tradeoff is latency (a sandbox boot),
which is why one sandbox is reused across every diff in a run.
"""

from __future__ import annotations

import inspect
import json
import textwrap

from .diff_algorithm import compute_diff
from .models import DiffResult

_RUNNER_TEMPLATE = """
import io  # compute_diff's own import; inspect.getsource only captures its body

{source}

import json

pct, diff_png = compute_diff(
    open("/tmp/journeyman_baseline.png", "rb").read(),
    open("/tmp/journeyman_current.png", "rb").read(),
)
open("/tmp/journeyman_diff.png", "wb").write(diff_png)
print(json.dumps({{"pct_changed": pct}}))
"""


def _build_script() -> str:
    source = textwrap.dedent(inspect.getsource(compute_diff))
    return _RUNNER_TEMPLATE.format(source=source)


class SandboxDiffer:
    """Wraps one Solari sandbox, reused across every `diff()` call."""

    def __init__(self, sandbox) -> None:
        self._sandbox = sandbox

    @classmethod
    async def create(cls, client) -> "SandboxDiffer":
        sandbox = await client.create(template="base", timeout_ms=5 * 60_000)
        await sandbox.connect()
        return cls(sandbox)

    @property
    def sandbox_id(self) -> str:
        return self._sandbox.sandboxId

    async def diff(self, baseline_png: bytes | None, current_png: bytes) -> DiffResult:
        if baseline_png is None:
            return DiffResult(compared=False, pct_changed=None, diff_png=None, note="no baseline yet; this run becomes the baseline")

        await self._sandbox.files.write("/tmp/journeyman_baseline.png", baseline_png)
        await self._sandbox.files.write("/tmp/journeyman_current.png", current_png)

        out = await self._sandbox.commands.run("python3", args=["-c", _build_script()])
        if out.exitCode != 0:
            return DiffResult(compared=False, pct_changed=None, diff_png=None, note=f"sandbox diff failed: {out.stderr.strip()[:300]}")

        payload = json.loads(out.stdout.strip().splitlines()[-1])
        diff_png = await self._sandbox.files.read("/tmp/journeyman_diff.png")
        pct = payload["pct_changed"]
        note = f"{pct}% of pixels changed vs. last known-good baseline"
        return DiffResult(compared=True, pct_changed=pct, diff_png=diff_png, note=note)

    async def close(self) -> None:
        await self._sandbox.kill()
