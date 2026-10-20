"""Capture a real Streamlit demo screenshot for the FogSense slide deck."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "figures" / "app_demo.png"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
        page.goto("http://127.0.0.1:8501", wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(3000)

        # Sample selectbox: "(none)" + test images.
        sample = page.locator('div[data-testid="stSelectbox"]').nth(0)
        sample.click()
        page.wait_for_timeout(500)
        options = page.get_by_role("option")
        print("options:", options.count())
        # A visually clear indoor scene (dining room) from the SOTS test split.
        target = None
        for i in range(options.count()):
            text = options.nth(i).inner_text()
            if "sots_indoor_1400" in text:
                target = options.nth(i)
                break
        (target or options.nth(1)).click()
        page.wait_for_timeout(7000)

        # Enable the opt-in v2 pipeline.
        cbs = page.locator('div[data-testid="stCheckbox"]')
        for i in range(cbs.count()):
            if "Enable v2 pipeline" in cbs.nth(i).inner_text():
                cbs.nth(i).click()
                page.wait_for_timeout(7000)
                break

        # Bring the comparison / first result into view.
        page.evaluate("window.scrollTo(0, 190)")
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT), full_page=False)
        print("saved", OUT)
        print("page title:", page.title())
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
