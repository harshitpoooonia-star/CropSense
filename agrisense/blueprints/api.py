from flask import Blueprint, g, jsonify
from sqlalchemy import text

from .. import farm_store
from ..extensions import db

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    """For the deploy checklist's smoke test: app up and database reachable."""
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001  (report, don't crash the health check)
        db.session.rollback()
        return jsonify(status="degraded", db="unreachable"), 503
    return jsonify(status="ok", db="ok")


@bp.get("/profile")
def profile():
    """A saved farm in the guest-profile shape (spec 01, R7). Never cached."""
    if g.get("user") is None:
        return jsonify(error="not_logged_in"), 401
    response = jsonify(farm_store.profile_for(db.session, g.user))
    response.headers["Cache-Control"] = "no-store"
    return response
