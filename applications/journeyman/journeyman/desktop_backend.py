"""Run a journey's steps against a Solari Desktop (a sandbox with a screen).

Desktop journeys have no DOM to read text from, so the heuristic judge here
only ever checks what the journey's `expect` explicitly asks for (usually
nothing) — the real signal for a GUI target is the sandbox pixel-diff against
its baseline, not a text match. That asymmetry is deliberate, not a gap: a
title bar and a couple of icons are the only "text" most desktop apps expose
without OCR, and asserting on those would be testing the window manager, not
the app.
"""

from __future__ import annotations

import asyncio
import time

from .models import Evidence, Journey

BASE_URL = "https://api.getsolari.com"


async def run_desktop_journey(journey: Journey, *, api_key: str) -> Evidence:
    from solari_desktop import DesktopClient

    started = time.monotonic()
    async with DesktopClient(api_key=api_key, base_url=BASE_URL) as client:
        desktop = await client.create(template="default", resolution="1280x720", timeout_ms=5 * 60_000)
        try:
            await desktop.connect()

            for _ in range(30):
                health = await desktop.health()
                if getattr(health, "ready", False):
                    break
                await asyncio.sleep(1)

            for step in journey.steps:
                if step.action == "open":
                    await desktop.open(step.text)
                    await asyncio.sleep(4)  # let the window map before we click into it
                elif step.action == "type":
                    await desktop.keyboard.type(step.text)
                elif step.action == "wait":
                    await asyncio.sleep(step.ms / 1000)
                elif step.action == "click":
                    x, y = (int(v) for v in step.selector.split(","))
                    await desktop.mouse.click(x, y, humanize=True)
                else:
                    raise ValueError(f"desktop backend cannot run step action {step.action!r}")

            screenshot = await desktop.screenshot(format="png")

            return Evidence(
                title=journey.name,
                url="desktop://" + journey.name,
                visible_text="",
                screenshot_png=screenshot,
                session_id=desktop.sessionId,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        finally:
            await desktop.close()
            await client.destroy(desktop.sessionId)
