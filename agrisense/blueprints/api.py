from flask import Blueprint, jsonify
from sqlalchemy import text

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
