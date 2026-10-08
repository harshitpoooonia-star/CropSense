"""Field tab: the farm profile summary and the 4-step setup wizard (spec 01).

Every view works as a full page and as an HTMX partial. The profile travels
in the `profile` form field (profile.js fills it from localStorage); the
updated profile goes back in the response for the browser to save.
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, current_app, g, render_template, request
from flask_babel import get_locale
from flask_babel import lazy_gettext as _l

from .. import districts, farm_context, farm_profile, farm_store, offline, units
from ..extensions import db
from ..profile_io import current_profile, render_with_profile
from ..trust import Source, TrustResult, apply_input_rule

bp = Blueprint("field", __name__)

ERRORS = {
    "location_invalid": _l("Drop the pin on your field, or choose your district."),
    "district_needed": _l("Choose your district from the list."),
    "bigha_unknown": _l("We don't know the bigha size for your district yet. Please use acre or hectare."),
    "area_invalid": _l("Enter the field size as a number, like 2 or 2.5."),
    "choose_one": _l("Choose one."),
    "number_invalid": _l("Enter the number as printed on the card."),
    "date_invalid": _l("Enter the date printed on the card. It can't be in the future."),
}
IRRIGATION_LABELS = {
    "tubewell": _l("Tubewell or borewell"),
    "canal": _l("Canal"),
    "rainfed": _l("Rain only"),
    "purchased": _l("Water bought from others"),
    "other": _l("Other"),
}
SOIL_LABELS = {
    "n": (_l("Nitrogen (N)"), _l("kg per hectare, as on the card")),
    "p": (_l("Phosphorus (P)"), _l("kg per hectare, as on the card")),
    "k": (_l("Potassium (K)"), _l("kg per hectare, as on the card")),
    "ph": (_l("pH"), None),
    "oc": (_l("Organic carbon (OC)"), _l("percent, as on the card")),
}
# Map opens over the Phase 1 target districts until there's a pin (ADR-005).
MAP_CENTER = (28.47, 77.65)


def _errors(found) -> dict[str, str]:
    return {e.field: str(ERRORS[e.code]) for e in found}


def _bigha_known(code: str | None) -> bool:
    try:
        units.hectares_per("bigha", code)
    except units.UnitUnavailable:
        return False
    return True


def _render_step(step: str, profile: dict, errors: dict | None = None, **extra):
    locale = str(get_locale())
    district = districts.get(profile["farm"]["district_code"])
    return render_with_profile(
        f"field/step_{step}.html",
        profile,
        step=step,
        step_number=farm_profile.STEPS.index(step) + 1 if step in farm_profile.STEPS else None,
        errors=errors or {},
        district=district,
        district_choices=districts.choices(locale),
        irrigation_labels=IRRIGATION_LABELS,
        soil_labels=SOIL_LABELS,
        bigha_known=_bigha_known(profile["farm"]["district_code"]),
        map_center=MAP_CENTER,
        today=date.today().isoformat(),
        **extra,
    )


def summary_result(profile: dict) -> TrustResult:
    """The profile itself, with the trust layer: what is given, estimated, unknown."""
    ctx = farm_context.build(profile)
    confidence = apply_input_rule("high", any_estimated=bool(ctx.estimated), any_unknown=bool(ctx.unknown))
    reasons = []
    if ctx.unknown:
        reasons.append(str(_l("Not known yet: %(fields)s. Tools will say when this limits an answer.",
                              fields=", ".join(ctx.unknown_labels()))))
    return TrustResult(
        value=None,
        confidence=confidence,
        reasons=reasons,
        sources=[Source(str(_l("what you entered")), date.today()), *ctx.sources],
        estimated_fields=ctx.estimated_labels(),
    )


@bp.get("/field")
def index():
    return render_template("field.html")


@bp.post("/field/summary")
def summary():
    profile = current_profile()
    if not farm_profile.is_complete(profile):
        return render_with_profile("field/_summary_empty.html", profile)
    offline.keep()
    return render_with_profile(
        "field/_summary.html",
        profile,
        trust=summary_result(profile),
        ctx=farm_context.build(profile),
        irrigation_labels=IRRIGATION_LABELS,
        soil_labels=SOIL_LABELS,
    )


@bp.get("/field/setup")
def setup():
    step = request.args.get("step", "where")
    if step not in farm_profile.STEPS:
        abort(404)
    # Guests' saved values arrive by HTMX right after load (profile.js); a
    # logged-in user's come from the DB now.
    return _render_step(step, current_profile(), load_saved=g.get("user") is None)


@bp.post("/field/setup/show")
def show():
    step = request.form.get("step") or "where"
    if step not in farm_profile.STEPS:
        abort(404)
    return _render_step(step, current_profile())


@bp.post("/field/setup/<step>")
def submit(step: str):
    if step not in farm_profile.STEPS:
        abort(404)
    profile = current_profile()
    errors = _errors(farm_profile.APPLY[step](profile, request.form))

    if step == "where" and (errors or request.form.get("stage") == "pin"):
        # Show the suggested district for the farmer to confirm or change.
        return _render_step("where", profile, errors, confirm=True)
    if errors:
        return _render_step(step, profile, errors)

    if g.get("user") is not None:
        farm_store.save_profile(db.session, g.user, profile)
        db.session.commit()

    following = farm_profile.STEPS.index(step) + 1
    if following < len(farm_profile.STEPS):
        return _render_step(farm_profile.STEPS[following], profile)
    return render_with_profile(
        "field/step_done.html",
        profile,
        trust=summary_result(profile),
        ctx=farm_context.build(profile),
        irrigation_labels=IRRIGATION_LABELS,
        soil_labels=SOIL_LABELS,
        step="done",
    )


@bp.context_processor
def map_settings() -> dict:
    return {
        "map_tiles": current_app.config["MAP_TILE_URL"],
        "map_attribution": current_app.config["MAP_ATTRIBUTION"],
    }
