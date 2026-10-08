"""Static files: content-hashed URLs and cache headers (Section 10).

`url_for("static", filename=...)` gets `?v=<hash of the file>`, so a changed
file always has a new URL. Versioned URLs are then cached for a year, and the
service worker can keep them without ever serving a stale copy.

Fonts are the exception: app.css asks for them by plain relative URL, and the
preload in base.html must use that same URL or the font downloads twice. They
are cached for 30 days and must be renamed, not edited, if they ever change.
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache

from flask import Flask, Response, request
from werkzeug.security import safe_join

UNVERSIONED = ("fonts/",)
ONE_YEAR = 365 * 24 * 3600
FONT_MAX_AGE = 30 * 24 * 3600


@lru_cache(maxsize=512)
def _digest(path: str, mtime_ns: int, size: int) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def version(static_folder: str, filename: str) -> str | None:
    """Short content hash of a static file, or None if it doesn't exist.
    Keyed on mtime and size, so an edited file is re-hashed without a restart."""
    path = safe_join(static_folder, filename)
    if path is None:
        return None
    try:
        st = os.stat(path)
    except OSError:
        return None
    return _digest(path, st.st_mtime_ns, st.st_size)


def init_app(app: Flask) -> None:
    @app.url_defaults
    def add_version(endpoint: str, values: dict) -> None:
        if endpoint != "static" or "v" in values:
            return
        filename = values.get("filename") or ""
        if filename.startswith(UNVERSIONED):
            return
        v = version(app.static_folder, filename)
        if v:
            values["v"] = v

    @app.after_request
    def cache_static(response: Response) -> Response:
        if request.endpoint != "static" or response.status_code not in (200, 304):
            return response
        filename = (request.view_args or {}).get("filename") or ""
        if filename.startswith(UNVERSIONED):
            response.cache_control.no_cache = None
            response.cache_control.public = True
            response.cache_control.max_age = FONT_MAX_AGE
        elif request.args.get("v") and request.args["v"] == version(app.static_folder, filename):
            response.cache_control.no_cache = None
            response.cache_control.public = True
            response.cache_control.max_age = ONE_YEAR
            response.cache_control.immutable = True
        return response
