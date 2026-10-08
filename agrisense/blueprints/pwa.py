"""Install and offline support (Section 10): manifest, service worker, offline page.

The service worker is rendered here rather than shipped as a static file, so
its precache list carries the same content-hashed URLs as the pages, and its
version changes whenever an asset, the offline page or the worker changes.
"""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, Response, current_app, render_template, request, send_from_directory, url_for
from flask_babel import force_locale
from flask_babel import gettext as _

from .. import offline

bp = Blueprint("pwa", __name__)

TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "pwa"
THEME_COLOR = "#5a3b22"       # --color-soil, the top bar
BACKGROUND_COLOR = "#faf7f2"  # --color-bg

# The app shell: enough to open any page the farmer visited before, offline.
SHELL_STATIC = ("css/app.css", "vendor/htmx-2.0.11.min.js", "js/profile.js", "js/pwa.js", "js/wizard.js",
                "icons/icon.svg", "icons/icon-192.png")
FAVICON_MAX_AGE = 30 * 24 * 3600  # fixed URL, so not the year-long cache of ?v= files
FONTS = ("mukta-400-devanagari", "mukta-400-latin", "mukta-700-devanagari", "mukta-700-latin")


@lru_cache(maxsize=1)
def _template_digest() -> str:
    h = hashlib.sha256()
    for name in ("sw.js", "offline.html"):
        h.update((TEMPLATES / name).read_bytes())
    return h.hexdigest()


def precache() -> list[str]:
    return ([url_for("static", filename=f) for f in SHELL_STATIC]
            + [url_for("static", filename=f"fonts/{name}.woff2") for name in FONTS]
            + [url_for("pwa.offline_page")])


def cache_version(urls: list[str]) -> str:
    """Changes with any precached asset (their URLs carry content hashes), the
    worker or offline page templates, or the deployed commit (Render sets it)."""
    h = hashlib.sha256(json.dumps(urls).encode())
    h.update(_template_digest().encode())
    h.update(os.environ.get("RENDER_GIT_COMMIT", "").encode())
    return h.hexdigest()[:12]


@bp.get("/sw.js")
def service_worker():
    urls = precache()
    body = render_template(
        "pwa/sw.js",
        version=cache_version(urls),
        precache=urls,
        offline_url=url_for("pwa.offline_page"),
        static_prefix=current_app.static_url_path + "/",
        never_cache=list(offline.NEVER_CACHE),
        keep_header=offline.HEADER,
        saved_at_header=offline.SAVED_AT_HEADER,
    )
    response = Response(body, mimetype="text/javascript")
    # Browsers check for a new worker on every visit; never let a cache hide one.
    response.headers["Cache-Control"] = "no-cache"
    return response


@bp.get("/favicon.ico")
def favicon():
    """Browsers ask for /favicon.ico even when the page links an SVG icon."""
    return send_from_directory(Path(current_app.static_folder) / "icons", "favicon.ico",
                               mimetype="image/vnd.microsoft.icon", max_age=FAVICON_MAX_AGE)


@bp.get("/manifest.webmanifest")
def manifest():
    lang = request.args.get("lang")
    lang = lang if lang in current_app.config["LANGUAGES"] else current_app.config["BABEL_DEFAULT_LOCALE"]
    with force_locale(lang):
        data = {
            "id": "/today",
            "name": _("AgriSense"),
            "short_name": _("AgriSense"),
            "description": _("Answers for your own farm, with the reason and the source shown. No sign-up needed."),
            "lang": lang,
            "dir": "ltr",
            "start_url": url_for("today.index"),
            "scope": "/",
            "display": "standalone",
            "background_color": BACKGROUND_COLOR,
            "theme_color": THEME_COLOR,
            # One full-bleed design with the sprout inside the maskable safe zone.
            "icons": [
                {"src": url_for("static", filename=f"icons/icon-{size}.png"), "sizes": f"{size}x{size}",
                 "type": "image/png", "purpose": purpose}
                for size in (192, 512) for purpose in ("any", "maskable")
            ],
        }
    response = Response(json.dumps(data, ensure_ascii=False), mimetype="application/manifest+json")
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@bp.get("/offline")
def offline_page():
    """Shown when a page was never opened before and there's no network. It is
    cached once, so it can't follow the language choice: it shows both."""
    copy = {}
    for code in current_app.config["LANGUAGES"]:
        with force_locale(code):
            copy[code] = {
                "title": _("No internet"),
                "body": _("This page isn't saved on your phone yet. Pages you opened before still work, "
                          "with your last answers."),
                "retry": _("Try again"),
                "today": _("Open Today"),
            }
    return render_template("pwa/offline.html", copy=copy)
