#!/usr/bin/env python3
"""Build the minified stylesheet with the Tailwind v4 standalone CLI (no Node).

    python scripts/build_css.py          # build agrisense/static/css/app.css
    python scripts/build_css.py --check  # CI: fail if the committed CSS is stale
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from get_assets import get_tailwind  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "agrisense" / "static" / "src" / "app.css"
OUT = ROOT / "agrisense" / "static" / "css" / "app.css"


def build(out: Path) -> None:
    cli = get_tailwind()
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(cli), "-i", str(SRC), "-o", str(out), "--minify"], cwd=SRC.parent, check=True)


def main() -> int:
    if "--check" in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "app.css"
            build(fresh)
            if fresh.read_bytes() != OUT.read_bytes():
                print("agrisense/static/css/app.css is stale: run python scripts/build_css.py")
                return 1
        print("CSS up to date")
        return 0
    build(OUT)
    print(f"built {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
