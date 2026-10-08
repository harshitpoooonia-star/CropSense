#!/usr/bin/env python3
"""Check the performance budgets (CLAUDE.md) on a cold first load:
JS+CSS transferred < 300 KB and LCP < 3 s, at 360 px on emulated slow 4G
(150 ms latency, 1.6 Mbit/s down, 750 kbit/s up) with the CPU slowed 4x.

Starts its own Flask server on a throwaway SQLite database, measures each page
with Playwright's Chromium and exits 1 if any page is over budget.

    python scripts/perf_budget.py [--port 5077] [paths...]
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGES = ("/", "/today", "/plan", "/market", "/schemes")
JS_CSS_BUDGET_KB = 300
LCP_BUDGET_S = 3.0
SLOW_4G = {"offline": False, "latency": 150,
           "downloadThroughput": 1.6 * 1024 * 1024 / 8, "uploadThroughput": 750 * 1024 / 8}
CPU_SLOWDOWN = 4

LCP_JS = """() => new Promise(resolve => {
  let value = 0;
  new PerformanceObserver(list => { for (const e of list.getEntries()) value = e.startTime; })
    .observe({type: 'largest-contentful-paint', buffered: true});
  setTimeout(() => resolve(value), 1500);
})"""


def wait_for_port(port: int, seconds: float = 30) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            socket.create_connection(("127.0.0.1", port), 1).close()
            return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError(f"server didn't start on port {port}")


def measure(browser, url: str) -> dict:
    context = browser.new_context(viewport={"width": 360, "height": 740}, locale="hi-IN")
    page = context.new_page()
    cdp = context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
    cdp.send("Network.emulateNetworkConditions", SLOW_4G)
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": CPU_SLOWDOWN})
    sizes: dict[str, int] = {}
    kinds: dict[str, tuple[str, str | None]] = {}
    cdp.on("Network.loadingFinished", lambda ev: sizes.__setitem__(ev["requestId"], ev["encodedDataLength"]))
    cdp.on("Network.responseReceived", lambda ev: kinds.__setitem__(
        ev["requestId"], (ev["type"], {k.lower(): v for k, v in ev["response"]["headers"].items()}.get("content-encoding"))))
    page.goto(url, wait_until="networkidle")
    lcp_ms = page.evaluate(LCP_JS)
    totals = {"jscss": 0, "font": 0, "html": 0, "other": 0}
    encodings: set[str] = set()
    for request_id, size in sizes.items():
        kind, encoding = kinds.get(request_id, ("Other", None))
        key = {"Script": "jscss", "Stylesheet": "jscss", "Font": "font", "Document": "html"}.get(kind, "other")
        totals[key] += size
        if encoding:
            encodings.add(encoding)
    context.close()
    return {**{k: v / 1024 for k, v in totals.items()}, "lcp": lcp_ms / 1000, "encodings": sorted(encodings)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=5077)
    parser.add_argument("paths", nargs="*", default=list(PAGES))
    args = parser.parse_args()

    py = sys.executable
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "AGRISENSE_ENV": "development",
               "DATABASE_URL": f"sqlite:///{(Path(tmp) / 'perf.db').as_posix()}"}
        subprocess.run([py, "-m", "flask", "--app", "wsgi", "db", "upgrade"], cwd=ROOT, env=env, check=True,
                       capture_output=True)
        server = subprocess.Popen([py, "-m", "flask", "--app", "wsgi", "run", "--port", str(args.port)], cwd=ROOT,
                                  env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        failed = []
        try:
            wait_for_port(args.port)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                print(f"{'page':<10}{'JS+CSS':>10}{'fonts':>10}{'HTML':>9}{'LCP':>8}  encodings  result")
                for path in args.paths:
                    m = measure(browser, f"http://127.0.0.1:{args.port}{path}")
                    ok = m["jscss"] < JS_CSS_BUDGET_KB and 0 < m["lcp"] < LCP_BUDGET_S
                    if not ok:
                        failed.append(path)
                    print(f"{path:<10}{m['jscss']:>7.1f} KB{m['font']:>7.1f} KB{m['html']:>6.1f} KB{m['lcp']:>6.2f} s"
                          f"  {','.join(m['encodings']) or 'none':<9}  {'pass' if ok else 'OVER BUDGET'}")
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=10)
    print(f"budgets: JS+CSS < {JS_CSS_BUDGET_KB} KB, LCP < {LCP_BUDGET_S:g} s (slow 4G, {CPU_SLOWDOWN}x CPU, 360 px)")
    if failed:
        print("over budget: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
