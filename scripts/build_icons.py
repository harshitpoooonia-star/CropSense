#!/usr/bin/env python3
"""Render the app icon (agrisense/static/icons/icon.svg) to the PNG sizes the
web app manifest and iOS need, using the Playwright Chromium the e2e tests
already install. Re-run after editing the SVG; the PNGs are committed.

    python scripts/build_icons.py
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ICONS = Path(__file__).resolve().parent.parent / "agrisense" / "static" / "icons"
SIZES = {"icon-192.png": 192, "icon-512.png": 512, "apple-touch-icon.png": 180}


def main() -> None:
    svg = (ICONS / "icon.svg").read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, size in SIZES.items():
            page = browser.new_page(viewport={"width": size, "height": size})
            page.set_content(f'<body style="margin:0">{svg.replace("<svg ", f"<svg width=\"{size}\" height=\"{size}\" ", 1)}</body>')
            page.screenshot(path=str(ICONS / name), clip={"x": 0, "y": 0, "width": size, "height": size})
            page.close()
            print(f"{name}: {size}x{size}, {(ICONS / name).stat().st_size} bytes")
        browser.close()


if __name__ == "__main__":
    main()
