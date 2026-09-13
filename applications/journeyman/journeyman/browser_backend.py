"""Run a journey's steps in a real Solari cloud browser."""

from __future__ import annotations

import time

from .models import Evidence, Journey


async def run_browser_journey(journey: Journey, *, api_key: str) -> Evidence:
    from solari_browser import Solari

    started = time.monotonic()
    async with Solari(api_key=api_key) as solari:
        # recording=True costs nothing extra here but means a failed run always
        # has a replay to look at, not just the final screenshot.
        browser = await solari.launch(recording=True)
        try:
            page = await browser.new_page()
            await page.goto(journey.url, wait_until="load")

            for step in journey.steps:
                if step.action == "fill":
                    await page.locator(step.selector).fill(step.text)
                elif step.action == "click":
                    await page.locator(step.selector).click()
                elif step.action == "wait":
                    await page.wait_for_timeout(step.ms)
                else:
                    raise ValueError(f"browser backend cannot run step action {step.action!r}")

            title = await page.title()
            visible_text = await page.locator("body").inner_text(timeout=5000)
            screenshot = await page.screenshot(full_page=True)
            url = page.url

            return Evidence(
                title=title,
                url=url,
                visible_text=visible_text,
                screenshot_png=screenshot,
                session_id=browser.id,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        finally:
            await browser.close()
