"""Machine endpoints (ADR-004): the daily price warm-up called by GitHub Actions.

Protected by a bearer token (REFRESH_TOKEN). Without a configured token the
endpoint doesn't exist (404), so a missing secret can't leave it open.
"""

from __future__ import annotations

import hmac

from flask import Blueprint, abort, current_app, jsonify, request

from ..extensions import csrf, db
from ..market import agmarknet

bp = Blueprint("internal", __name__, url_prefix="/internal")
MAX_DAYS = 7


def _authorised() -> bool:
    token = current_app.config.get("REFRESH_TOKEN")
    if not token:
        abort(404)
    sent = request.headers.get("Authorization", "")
    return hmac.compare_digest(sent.encode(), f"Bearer {token}".encode())


@bp.post("/refresh/prices")
@csrf.exempt
def refresh_prices():
    if not _authorised():
        return jsonify(error="unauthorised"), 401
    days = min(max(int(request.args.get("days", 3)), 1), MAX_DAYS)
    report = agmarknet.refresh(db.session, current_app.config.get("DATA_GOV_IN_KEY"), days=days)
    status = 200 if report.error is None else 502
    return jsonify(days=report.days, rows_seen=report.rows_seen, rows_stored=report.rows_stored,
                   failed_days=[d.isoformat() for d in report.failed_days], error=report.error), status
