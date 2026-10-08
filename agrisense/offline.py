"""Which responses the service worker may keep for offline use (Section 10).

A tool view calls `keep()` once it has a real answer (not a form error). The
response then carries `X-Offline-Keep: 1`, and the service worker saves it as
that tool's last result, to show with an "offline" banner when the network
is gone. Nothing else is kept from POSTs.
"""

from __future__ import annotations

from flask import Flask, Response, g

HEADER = "X-Offline-Keep"
SAVED_AT_HEADER = "X-Offline-Saved-At"  # set by the service worker on a replayed copy

# Never cached or replayed by the service worker: accounts, PINs, the farm
# account pages, the language switch, and machine endpoints. Path prefixes.
NEVER_CACHE = (
    "/login", "/logout", "/pin/", "/helper/", "/farm/", "/lang/",
    "/api/", "/internal/", "/sw.js", "/manifest.webmanifest",
)


def keep() -> None:
    g.offline_keep = True


def init_app(app: Flask) -> None:
    @app.after_request
    def mark(response: Response) -> Response:
        if g.get("offline_keep") and response.status_code == 200:
            response.headers[HEADER] = "1"
        return response
