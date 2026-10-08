"""Crop Planner v2 (spec 02): season choice -> top 3 crops with the trust layer."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, g, render_template, request
from flask_babel import get_locale

from .. import farm_context, farm_profile, farm_store
from ..crops import crop_name, crops
from ..extensions import db
from ..models import Event, utcnow
from ..planner import data, rank
from ..profile_io import current_profile, is_htmx

bp = Blueprint("planner", __name__)


@bp.get("/plan")
def index():
    return render_template("planner/index.html", seasons=data.SEASONS, season_labels=rank.SEASON_LABELS)


def _plan_for(profile: dict, season: str):
    ctx = farm_context.build(profile)
    return ctx, rank.plan(ctx, season, db.session, date.today())


def _not_ready(profile: dict) -> str | None:
    if not farm_profile.is_complete(profile):
        return "no_field"
    if not data.has_district(profile["farm"]["district_code"]):
        return "no_district_data"
    return None


@bp.post("/plan/results")
def results():
    season = request.form.get("season")
    if season not in data.SEASONS:
        abort(400)
    profile = current_profile()
    problem = _not_ready(profile)
    template = "planner/_results.html" if is_htmx() else "planner/index.html"
    common = {"seasons": data.SEASONS, "season_labels": rank.SEASON_LABELS, "season": season}
    if problem:
        return render_template(template, problem=problem, **common)

    ctx, plan = _plan_for(profile, season)
    if plan.top:
        best = plan.top[0].trust.to_dict()
        best["value"] = {**best["value"], "top": [o.crop for o in plan.top]}
        profile["last_results"]["planner"] = best
        if g.get("user") is not None:
            row = farm_store.current_plot(db.session, g.user)
            if row is not None:
                db.session.add(Event(plot_id=row.id, kind="planner.result", occurred_at=utcnow(),
                                     payload=best, payload_version=1, source="app"))
                db.session.commit()
    locale = str(get_locale())
    shown = {o.crop for o in plan.top}
    others = sorted(((code, crop_name(code, locale)) for code in crops() if code not in shown), key=lambda c: c[1])
    return render_template(template, plan=plan, ctx=ctx, profile=profile, other_crops=others, **common)


@bp.post("/plan/why")
def why():
    season, crop = request.form.get("season"), request.form.get("crop")
    if season not in data.SEASONS or crop not in crops():
        abort(400)
    profile = current_profile()
    if _not_ready(profile):
        abort(400)
    ctx, plan = _plan_for(profile, season)
    reasons = rank.why_not(plan, crop, ctx.district.name(str(get_locale())))
    return render_template("planner/_why.html", crop=crop, reasons=reasons, option=plan.find(crop))
