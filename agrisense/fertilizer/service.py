"""Fertilizer request -> bags, cost, split and the trust layer (spec 03)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from flask_babel import format_decimal
from flask_babel import lazy_gettext as _l

from .. import districts, units
from ..crops import crop_name
from ..trust import Source, TrustResult, cap
from . import calc, data

PRODUCT_LABELS = {"urea": _l("Urea"), "dap": _l("DAP"), "mop": _l("MOP (potash)"), "ssp": _l("SSP")}
STAGE_LABELS = {"basal": _l("At sowing or planting"), "earthing_up": _l("At earthing up")}
CONDITION_LABELS = {
    "irrigated": _l("irrigated, sown on time"), "late": _l("late sown"), "rainfed": _l("rain-fed"),
    "transplanted": _l("transplanted"), "default": _l("standard"), "plant": _l("plant crop"),
}
CARD_PRODUCTS = ("urea", "dap", "mop", "ssp")


@dataclass
class Outcome:
    mode: str
    crop: str | None
    condition: str | None
    area_ha: Decimal | None
    plans: list[tuple[str, calc.Plan]] = field(default_factory=list)  # (label, plan); two for a dose range
    trust: TrustResult | None = None
    share_text: str = ""
    errors: dict[str, str] = field(default_factory=dict)
    no_dose: bool = False


ERRORS = {
    "area_needed": _l("Enter your field size, or set up your field first."),
    "area_invalid": _l("Enter the field size as a number, like 2 or 2.5."),
    "bigha_unknown": _l("We don't know the bigha size for your district yet. Please use acre or hectare."),
    "card_empty": _l("Enter at least one amount from your Soil Health Card."),
    "card_invalid": _l("Enter the amounts as numbers, as printed on the card."),
    "crop_needed": _l("Choose a crop."),
}


def _area(form, profile) -> tuple[Decimal | None, str | None]:
    raw = (form.get("area") or "").strip()
    district = profile["farm"]["district_code"]
    if not raw:
        saved = profile["plots"][0]["area_ha"]
        return (Decimal(saved), None) if saved else (None, "area_needed")
    try:
        area = units.to_hectares(raw, form.get("area_unit") or "acre", district)
    except units.UnitUnavailable:
        return None, "bigha_unknown"
    except ValueError:
        return None, "area_invalid"
    return (area, None) if area > 0 else (None, "area_invalid")


def calculate(form, profile, locale: str) -> Outcome:
    mode = "card" if form.get("mode") == "card" else "standard"
    crop = form.get("crop") or None
    phosphate = "ssp" if form.get("phosphate") == "ssp" else "dap"
    outcome = Outcome(mode=mode, crop=crop, condition=None, area_ha=None)
    area, err = _area(form, profile)
    if err:
        outcome.errors["area"] = str(ERRORS[err])
    outcome.area_ha = area
    products, prices = data.products()

    if mode == "card":
        per_unit = {}
        try:
            for code in CARD_PRODUCTS:
                raw = (form.get(f"card_{code}") or "").strip()
                if raw:
                    per_unit[code] = units.parse_decimal(raw)
        except ValueError:
            outcome.errors["card"] = str(ERRORS["card_invalid"])
        if not outcome.errors and not any(per_unit.values()):
            outcome.errors["card"] = str(ERRORS["card_empty"])
        if outcome.errors:
            return outcome
        unit = "acre" if form.get("card_unit") == "acre" else "hectare"
        plan = calc.to_plan(calc.card_kg(per_unit, unit, area), products)
        outcome.plans = [("", plan)]
        reasons = [str(_l("Dose copied from your Soil Health Card, scaled to your field."))]
        sources = [Source(str(_l("your Soil Health Card")))]
        confidence = "high"
    else:
        if not crop:
            outcome.errors["crop"] = str(ERRORS["crop_needed"])
            return outcome
        options = data.conditions(crop)
        condition = form.get("condition") if form.get("condition") in options else (options[0] if options else None)
        outcome.condition = condition
        row = data.doses().get((crop, condition)) if condition else None
        if row is None:
            outcome.no_dose = True
            return outcome
        if outcome.errors:
            return outcome
        ends = [("low", row.low), ("high", row.high)] if row.is_range else [("", row.low)]
        schedule = calc.parse_split(row.split)
        for label, dose in ends:
            plan = calc.to_plan(calc.product_kg(dose, area, products, phosphate), products)
            if schedule:
                plan.stages = calc.split_by_stage(dose, area, products, phosphate, schedule)
            outcome.plans.append((label, plan))
        reasons = [str(_l("Standard dose for %(crop)s (%(condition)s): N %(n)s, P2O5 %(p)s, K2O %(k)s kg per hectare.",
                          crop=crop_name(crop, locale), condition=CONDITION_LABELS.get(condition, condition),
                          n=_range(row.low.n, row.high.n), p=_range(row.low.p2o5, row.high.p2o5),
                          k=_range(row.low.k2o, row.high.k2o))),
                   str(_l("Not adjusted for your soil test. If your Soil Health Card gives a dose for this crop, use that instead."))]
        if not row.complete:
            reasons.append(str(_l("Only part of this dose has a cited source; the missing nutrients aren't shown. Ask your KVK.")))
        reasons.append(str(_l("Phosphate from DAP, which also gives some nitrogen; the rest of the nitrogen from urea."))
                       if phosphate == "dap" else str(_l("Phosphate from SSP; all nitrogen from urea.")))
        sources = [Source(row.source)]
        confidence = "medium" if row.verified is False else "high"
        if not row.complete:
            confidence = "low"
    used = {line.product for _label, plan in outcome.plans for line in plan.lines}
    for code in sorted(used):
        info = prices[code]
        sources.append(Source(f"{PRODUCT_LABELS[code]}: {info.source} ({info.as_of})"))
        if not info.verified:
            confidence = cap(confidence, "medium")
    if used:
        sources.append(Source(prices[sorted(used)[0]].composition_source))
    reasons.append(str(_l("Cost is for whole bags. Prices change: check the MRP printed on each bag.")))

    first = outcome.plans[0][1]
    outcome.trust = TrustResult(
        value={"mode": mode, "crop": crop, "condition": outcome.condition, "area_ha": str(area),
               "lines": [{"product": l.product, "kg": str(l.kg), "bags": str(l.bags), "buy": l.bags_to_buy,
                          "cost": str(l.cost)} for l in first.lines],
               "total_cost": str(first.total_cost)},
        confidence=confidence, reasons=reasons, sources=sources)
    outcome.share_text = share_text(outcome, locale)
    return outcome


def _range(low: Decimal, high: Decimal) -> str:
    return f"{low.normalize():f}" if low == high else f"{low.normalize():f}-{high.normalize():f}"


def share_text(outcome: Outcome, locale: str) -> str:
    plan = outcome.plans[0][1]
    items = ", ".join(str(_l("%(product)s %(bags)s bags", product=PRODUCT_LABELS[l.product], bags=l.bags_to_buy))
                      for l in plan.lines)
    what = crop_name(outcome.crop, locale) if outcome.crop else str(_l("my field"))
    return str(_l("AgriSense fertilizer for %(what)s: %(items)s, about ₹%(cost)s. Check with your KVK.",
                  what=what, items=items, cost=format_decimal(int(plan.total_cost), format="#,##,##0")))


def district_of(profile) -> districts.District | None:
    return districts.get(profile["farm"]["district_code"])
