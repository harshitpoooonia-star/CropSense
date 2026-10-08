#!/usr/bin/env python3
"""Render the app icon (agrisense/static/icons/icon.svg) to the PNG sizes the
web app manifest and iOS need, and to favicon.ico (browsers ask for
/favicon.ico whatever the page links), using the Playwright Chromium the e2e
tests already install. Re-run after editing the SVG; the outputs are committed.

    python scripts/build_icons.py
"""

from __future__ import annotations

import struct
from pathlib import Path

from playwright.sync_api import sync_playwright

ICONS = Path(__file__).resolve().parent.parent / "agrisense" / "static" / "icons"
SIZES = {"icon-192.png": 192, "icon-512.png": 512, "apple-touch-icon.png": 180}
FAVICON_SIZES = (32, 48)


def ico(pngs: list[tuple[int, bytes]]) -> bytes:
    """An .ico holding PNG images (supported by every current browser)."""
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = len(header) + 16 * len(pngs)
    entries, data = b"", b""
    for size, png in pngs:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    return header + entries + data


def render(browser, svg: str, size: int) -> bytes:
    page = browser.new_page(viewport={"width": size, "height": size})
    page.set_content(f'<body style="margin:0">{svg.replace("<svg ", f"<svg width=\"{size}\" height=\"{size}\" ", 1)}</body>')
    png = page.screenshot(clip={"x": 0, "y": 0, "width": size, "height": size})
    page.close()
    return png


def main() -> None:
    svg = (ICONS / "icon.svg").read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, size in SIZES.items():
            (ICONS / name).write_bytes(render(browser, svg, size))
            print(f"{name}: {size}x{size}, {(ICONS / name).stat().st_size} bytes")
        favicon = ico([(size, render(browser, svg, size)) for size in FAVICON_SIZES])
        (ICONS / "favicon.ico").write_bytes(favicon)
        print(f"favicon.ico: {'+'.join(map(str, FAVICON_SIZES))} px, {len(favicon)} bytes")
        browser.close()


if __name__ == "__main__":
    main()
