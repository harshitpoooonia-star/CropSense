#!/usr/bin/env python3
"""Fetch pinned front-end build assets, verifying checksums (ADR-001).

    python scripts/get_assets.py tailwind   # CLI binary -> .tools/ (not committed)
    python scripts/get_assets.py htmx       # -> agrisense/static/vendor/ (committed)
    python scripts/get_assets.py fonts      # Mukta woff2 -> agrisense/static/fonts/ (committed)

Bump a version by changing the constant and its checksum together.
"""

from __future__ import annotations

import base64
import hashlib
import io
import platform
import re
import stat
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / ".tools"
STATIC = ROOT / "agrisense" / "static"

TAILWIND_VERSION = "v4.3.3"
TAILWIND_RELEASE = f"https://github.com/tailwindlabs/tailwindcss/releases/download/{TAILWIND_VERSION}"

HTMX_VERSION = "2.0.11"
HTMX_TARBALL = f"https://registry.npmjs.org/htmx.org/-/htmx.org-{HTMX_VERSION}.tgz"
HTMX_INTEGRITY = "sha512-Thx/WtpeOQqSrqBCw/A1cwGJGg4UrVa3+sW0GmrM3p4gJgO89ecH4qtbnyzDDWFvBTqjnIMCgELTNt636dtamA=="

# Mukta (Ek Type, SIL OFL 1.1) covers Devanagari and Latin in one family.
FONT_CSS = "https://fonts.googleapis.com/css2?family=Mukta:wght@400;700&display=swap"
FONT_LICENSE = "https://raw.githubusercontent.com/google/fonts/main/ofl/mukta/OFL.txt"
FONT_SUBSETS = ("devanagari", "latin")
# Google serves woff2 + unicode-range splits only to modern browsers.
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36"


def fetch(url: str, ua: str | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": ua or "agrisense-get-assets"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def tailwind_asset_name() -> str:
    system = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}[platform.system()]
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x64"
    return f"tailwindcss-{system}-{arch}" + (".exe" if system == "windows" else "")


def tailwind_path() -> Path:
    return TOOLS / f"tailwindcss-{TAILWIND_VERSION}" / tailwind_asset_name()


def get_tailwind() -> Path:
    target = tailwind_path()
    if target.exists():
        print(f"tailwind: already at {target.relative_to(ROOT)}")
        return target
    name = tailwind_asset_name()
    sums = fetch(f"{TAILWIND_RELEASE}/sha256sums.txt").decode()
    expected = next(
        (line.split()[0] for line in sums.splitlines() if line.strip().endswith(name)), None
    )
    if not expected:
        sys.exit(f"tailwind: {name} not listed in sha256sums.txt")
    binary = fetch(f"{TAILWIND_RELEASE}/{name}")
    actual = hashlib.sha256(binary).hexdigest()
    if actual != expected:
        sys.exit(f"tailwind: checksum mismatch for {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(binary)
    target.chmod(target.stat().st_mode | stat.S_IEXEC)
    print(f"tailwind: {name} {TAILWIND_VERSION} verified -> {target.relative_to(ROOT)}")
    return target


def get_htmx() -> None:
    data = fetch(HTMX_TARBALL)
    algo, b64 = HTMX_INTEGRITY.split("-", 1)
    if base64.b64encode(hashlib.new(algo, data).digest()).decode() != b64:
        sys.exit("htmx: integrity mismatch")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        js = tar.extractfile("package/dist/htmx.min.js").read()
        license_text = tar.extractfile("package/LICENSE").read()
    out = STATIC / "vendor"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"htmx-{HTMX_VERSION}.min.js").write_bytes(js)
    (out / "htmx.LICENSE.txt").write_bytes(license_text)
    print(f"htmx: {HTMX_VERSION} verified -> agrisense/static/vendor/ ({len(js)} bytes)")


def get_fonts() -> None:
    css = fetch(FONT_CSS, ua=BROWSER_UA).decode()
    out = STATIC / "fonts"
    out.mkdir(parents=True, exist_ok=True)
    faces = []
    # Each block: /* subset */ @font-face { ... font-weight: N; src: url(...) format('woff2'); unicode-range: ...; }
    for subset, block in re.findall(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*{[^}]+})", css):
        if subset not in FONT_SUBSETS:
            continue
        weight = re.search(r"font-weight:\s*(\d+)", block).group(1)
        url = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
        unicode_range = re.search(r"unicode-range:\s*([^;]+);", block).group(1).strip()
        name = f"mukta-{weight}-{subset}.woff2"
        (out / name).write_bytes(fetch(url))
        faces.append(
            "@font-face {\n"
            "  font-family: 'Mukta';\n  font-style: normal;\n"
            f"  font-weight: {weight};\n  font-display: swap;\n"
            f"  src: url('../fonts/{name}') format('woff2');\n"
            f"  unicode-range: {unicode_range};\n}}"
        )
    if len(faces) != 2 * len(FONT_SUBSETS):
        sys.exit(f"fonts: expected {2 * len(FONT_SUBSETS)} faces, got {len(faces)}; Google's CSS format changed?")
    (out / "OFL.txt").write_bytes(fetch(FONT_LICENSE))
    header = "/* Generated by scripts/get_assets.py fonts. Mukta, SIL Open Font License 1.1 (fonts/OFL.txt). */\n"
    (STATIC / "src" / "fonts.css").write_text(header + "\n".join(faces) + "\n", encoding="utf-8")
    sizes = {p.name: p.stat().st_size for p in sorted(out.glob("*.woff2"))}
    print("fonts:", ", ".join(f"{k} {v // 1024} KB" for k, v in sizes.items()))


if __name__ == "__main__":
    actions = {"tailwind": get_tailwind, "htmx": get_htmx, "fonts": get_fonts}
    wanted = sys.argv[1:] or list(actions)
    for name in wanted:
        actions[name]()
