"""Fertilizer Calculator (spec 03): crop + area + dose -> bags, cost, split."""

from __future__ import annotations

from flask import Blueprint, g, render_template, request
from flask_babel import get_locale

from .. import farm_store, offline
from ..crops import crop_name
from ..extensions import db
from ..fertilizer import data, service
from ..models import Event, utcnow
from ..profile_io import current_profile, is_htmx

bp = Blueprint("fertilizer", __name__)


def _choices(locale: str) -> dict:
    crops = data.crops_with_dose()
    return {
        "crop_choices": sorted(((c, crop_name(c, locale)) for c in crops), key=lambda x: x[1]),
        "conditions": {c: [(cond, service.CONDITION_LABELS.get(cond, cond)) for cond in data.conditions(c)] for c in crops},
        "product_labels": service.PRODUCT_LABELS,
        "stage_labels": service.STAGE_LABELS,
    }


@bp.get("/fertilizer")
def index():
    locale = str(get_locale())
    crop = request.args.get("crop")
    return render_template("fertilizer/index.html", form={"crop": crop, "mode": "standard", "phosphate": "dap"},
                           unknown_crop=crop if crop and crop not in data.crops_with_dose() else None,
                           **_choices(locale))


@bp.post("/fertilizer/result")
def result():
    locale = str(get_locale())
    profile = current_profile()
    outcome = service.calculate(request.form, profile, locale)
    if outcome.trust is not None:
        offline.keep()
        profile["last_results"]["fertilizer"] = outcome.trust.to_dict()
        if g.get("user") is not None:
            row = farm_store.current_plot(db.session, g.user)
            if row is not None:
                db.session.add(Event(plot_id=row.id, kind="fertilizer.result", occurred_at=utcnow(),
                                     payload=outcome.trust.to_dict(), payload_version=1, source="app"))
                db.session.commit()
    template = "fertilizer/_result.html" if is_htmx() else "fertilizer/index.html"
    return render_template(template, outcome=outcome, form=request.form, profile=profile,
                           unknown_crop=None, **_choices(locale))
