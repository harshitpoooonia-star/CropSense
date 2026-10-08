"""Reading and returning the farm profile on each request (spec 01 R2, R7).

Logged-in users: the DB is the truth. Guests: whatever valid profile their
browser sent. Views call `current_profile()` and, after changing it,
`render_with_profile()` so the browser's copy is updated.
"""

from __future__ import annotations

from flask import g, render_template, request, session

from . import farm_profile, farm_store
from .extensions import db


def is_htmx() -> bool:
    return request.headers.get("HX-Request") == "true"


def current_profile() -> dict:
    if g.get("user") is not None:
        return farm_store.profile_for(db.session, g.user)
    return farm_profile.parse(request.form.get("profile") or request.args.get("profile"))


def request_sync() -> None:
    """After login/save: send the saved profile to the browser on the next page."""
    session["profile_sync"] = "saved"


def request_clear() -> None:
    """After logout/delete: remove the profile from this (maybe shared) phone."""
    session["profile_sync"] = "clear"


def pending_sync() -> dict | None:
    """Template context for base.html's data-profile-update block. Computed
    once per request, because one request may render several templates."""
    key = "agrisense.profile_sync"  # per request: g can outlive a request
    if key not in request.environ:
        action = session.pop("profile_sync", None)
        if action == "clear":
            request.environ[key] = {"value": None}
        elif action == "saved" and g.get("user") is not None:
            request.environ[key] = {"value": farm_store.profile_for(db.session, g.user)}
        else:
            request.environ[key] = None
    return request.environ[key]


def render_with_profile(template: str, profile: dict, **context) -> str:
    """Render a partial (HTMX) or the full page, carrying the updated profile."""
    return render_template(
        template,
        profile=profile,
        profile_json=farm_profile.dumps(profile),
        partial=is_htmx(),
        **context,
    )
