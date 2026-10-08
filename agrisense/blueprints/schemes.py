"""Scheme Finder (spec 06): six short questions -> likely-eligible schemes."""

from __future__ import annotations

import json
from decimal import Decimal

from flask import Blueprint, abort, current_app, g, render_template, request
from flask_babel import get_locale
from flask_babel import lazy_gettext as _l

from .. import districts, farm_store, units
from ..crops import crop_name, crops
from ..extensions import db
from ..models import Event, utcnow
from ..profile_io import current_profile, is_htmx
from ..schemes import catalog, engine
from ..trust import Source, TrustResult

bp = Blueprint("schemes", __name__)

STEPS = engine.QUESTIONS
ERRORS = {
    "land": _l("Enter the land as a number, like 2 or 2.5."),
    "age": _l("Enter your age in years, like 35."),
    "choose": _l("Choose one, or tap Skip."),
}
REASONS = {
    "state": _l("Only for farmers in %(states)s."),
    "ownership": _l("Not for your kind of landholding."),
    "land": _l("Only for farmers with up to %(max)s hectares."),
    "age": _l("Only for ages %(min)s to %(max)s."),
    "excluded": _l("Families with an income-tax payer, government job or large pension are excluded."),
    "irrigation": _l("Only for farms with a private tubewell connection."),
    "crop_unlisted": _l("Covers a list of crops; check whether yours is on it."),
    "category": _l("Only for certain categories."),
    "state_unknown": _l("Depends on your state."),
    "ownership_unknown": _l("Depends on whose land you farm."),
    "land_unknown": _l("Depends on how much land you have."),
    "age_unknown": _l("Depends on your age."),
    "exclusion_unknown": _l("Depends on income tax, government jobs or pensions in your family."),
    "irrigation_unknown": _l("Depends on having a private tubewell."),
    "crop_unknown": _l("Depends on your crop."),
    "category_unknown": _l("Depends on your category."),
}
STATE_NAMES = {"UP": _l("Uttar Pradesh"), "HR": _l("Haryana")}


@bp.app_template_filter("format_reason")
def format_reason(template, params: dict) -> str:
    """Fill a reason's placeholders; state codes become state names."""
    values = dict(params)
    if "states" in values:
        values["states"] = ", ".join(str(STATE_NAMES.get(s, s)) for s in values["states"])
    if "allowed" in values:
        values.pop("allowed")
    return str(template) % values if values else str(template)


def _answers_from(raw: str | None, profile: dict) -> dict:
    """Answers so far, with defaults from the saved field where the farmer hasn't answered."""
    try:
        answers = json.loads(raw) if raw else {}
    except ValueError:
        answers = {}
    if not isinstance(answers, dict):
        answers = {}
    answers = {k: v for k, v in answers.items()
               if (k in STEPS and v not in ("", None)) or (k.startswith("skip_") and k[5:] in STEPS and v is True)}
    district = districts.get(profile["farm"]["district_code"])
    if "state" not in answers and "skip_state" not in answers and district:
        answers["state"] = district.state
    if "land" not in answers and "skip_land" not in answers and profile["plots"][0]["area_ha"]:
        answers["land"] = profile["plots"][0]["area_ha"]
    return answers


def _to_engine(answers: dict, profile: dict) -> engine.Answers:
    return engine.Answers(
        state=answers.get("state") if answers.get("state") in ("UP", "HR", "other") else None,
        land_ha=Decimal(answers["land"]) if answers.get("land") else None,
        ownership=answers.get("ownership"),
        crop=answers.get("crop"),
        age=int(answers["age"]) if answers.get("age") else None,
        exclusion=answers.get("exclusion"),
        irrigation=profile["plots"][0]["irrigation_source"],
    )


def _read(step: str, form, district_code: str | None) -> tuple[str | None, str | None]:
    """The submitted value for a step, or an error code. Skip -> (None, None)."""
    if form.get("skip"):
        return None, None
    value = (form.get("value") or "").strip()
    if step == "land":
        if not value:
            return None, "land"
        try:
            hectares = units.to_hectares(value, form.get("value_unit") or "acre", district_code)
        except (ValueError, units.UnitUnavailable):
            return None, "land"
        return format(hectares.quantize(Decimal("0.0001")).normalize(), "f"), None
    if step == "age":
        return (value, None) if value.isdigit() and 0 < int(value) < 120 else (None, "age")
    allowed = {"state": ("UP", "HR", "other"), "ownership": ("owner", "tenant", "sharecropper"),
               "crop": tuple(crops()), "exclusion": ("yes", "no")}[step]
    return (value, None) if value in allowed else (None, "choose")


def _render_step(step: str, answers: dict, error: str | None = None):
    locale = str(get_locale())
    template = "schemes/_step.html" if is_htmx() else "schemes/index.html"
    return render_template(template, step=step, number=STEPS.index(step) + 1, total=len(STEPS),
                           answers=answers, answers_json=json.dumps(answers), error=error and str(ERRORS[error]),
                           crop_choices=sorted(((c, crop_name(c, locale)) for c in crops()), key=lambda x: x[1]),
                           state_names=STATE_NAMES)


@bp.get("/schemes")
def index():
    return render_template("schemes/index.html", step=None)


@bp.post("/schemes/step")
def show_step():
    step = request.form.get("step") or STEPS[0]
    if step not in STEPS:
        abort(404)
    return _render_step(step, _answers_from(request.form.get("answers"), current_profile()))


@bp.post("/schemes/answer/<step>")
def answer(step: str):
    if step not in STEPS:
        abort(404)
    profile = current_profile()
    answers = _answers_from(request.form.get("answers"), profile)
    value, error = _read(step, request.form, profile["farm"]["district_code"])
    if error:
        return _render_step(step, answers, error)
    if value is None:
        answers.pop(step, None)
        answers[f"skip_{step}"] = True
    else:
        answers[step] = value
    following = STEPS.index(step) + 1
    if following < len(STEPS):
        return _render_step(STEPS[following], answers)
    return _results(answers, profile)


def _results(answers: dict, profile: dict):
    locale = str(get_locale())
    shown = catalog.visible(current_app.config["SCHEMES_SHOW_UNVERIFIED"])
    found = engine.find(shown, _to_engine(answers, profile))
    unverified = [s for s in shown if not s.verified]
    trust = None
    if shown:
        trust = TrustResult(
            value={"likely": [m.scheme.id for m in found["likely"]], "maybe": [m.scheme.id for m in found["maybe"]]},
            confidence="low" if unverified else "medium",
            reasons=[str(_l("Based only on your answers. The scheme office decides; confirm at the official portal or a CSC.")),
                     *([str(_l("%(count)s of these schemes haven't been checked against their official page yet.",
                               count=len(unverified)))] if unverified else [])],
            sources=[Source(str(_l("AgriSense scheme list, from official and news sources (see each scheme)")))])
        profile["last_results"]["schemes"] = trust.to_dict()
        if g.get("user") is not None:
            row = farm_store.current_plot(db.session, g.user)
            if row is not None:
                db.session.add(Event(plot_id=row.id, kind="schemes.result", occurred_at=utcnow(),
                                     payload=trust.to_dict(), payload_version=1, source="app"))
                db.session.commit()
    template = "schemes/_results.html" if is_htmx() else "schemes/index.html"
    return render_template(template, step="done", found=found, trust=trust, profile=profile, locale=locale,
                           reasons=REASONS, answers_json=json.dumps(answers), nothing_shown=not shown)
