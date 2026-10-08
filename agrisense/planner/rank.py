"""Rank crops for one field and season (spec 02, R3-R5).

score = weighted mean of the factors we actually have for a crop:
    profit       (0.55)  mid-point of the Rs/acre range, scaled among candidates
    water fit    (0.30)  crop's water need vs the field's irrigation source
    suitability  (0.15)  legacy model, only when its inputs are in range
A missing factor drops out of the mean and lowers confidence; with no price
for any crop, profit isn't ranked and the result says so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from flask_babel import format_decimal, get_locale
from flask_babel import lazy_gettext as _l
from sqlalchemy.orm import Session

from ..crops import crops
from ..farm_context import FarmContext
from ..trust import Source, TrustResult, apply_input_rule, cap
from . import data, model, prices

WEIGHTS = {"profit": 0.55, "water": 0.30, "suitability": 0.15}
WATER_SCORE = {"good": 1.0, "caution": 0.5, "poor": 0.0}
MISSING = {"profit": 0.0, "water": 0.5, "suitability": 0.5}
# Mention the model in a card's reasons only when it is fairly sure (product choice).
MODEL_REASON_MIN = 0.3
RISK_FOR_WATER = {"good": "low", "caution": "medium", "poor": "high"}
OLD_COST_YEARS = 2  # cost data older than this caps confidence at medium
TOP = 3

SEASON_LABELS = {"kharif": _l("kharif"), "rabi": _l("rabi"), "zaid": _l("zaid")}
WATER_LABELS = {"low": _l("low"), "medium": _l("medium"), "high": _l("high")}
IRRIGATION_PHRASES = {
    "tubewell": _l("tubewell"), "canal": _l("canal"), "rainfed": _l("rain-fed field"),
    "purchased": _l("bought water"), "other": _l("water source"),
}
FEATURE_LABELS = {
    "N": _l("soil nitrogen"), "P": _l("soil phosphorus"), "K": _l("soil potassium"), "ph": _l("soil pH"),
    "temperature": _l("season temperature"), "humidity": _l("season humidity"), "rainfall": _l("season rainfall"),
}


def water_fit(need: str | None, irrigation: str | None) -> str | None:
    """Product rule, not agronomy: can this field's water source meet the crop's need category?"""
    if need is None or irrigation is None:
        return None
    if irrigation in ("tubewell", "canal"):
        return "good"
    if irrigation == "rainfed":
        return {"low": "good", "medium": "caution", "high": "poor"}[need]
    return {"low": "good", "medium": "good", "high": "caution"}[need]  # bought water, other


@dataclass
class Option:
    crop: str
    season: str
    area_ha: int
    econ: data.Economics | None
    price: prices.PriceInfo | None = None
    profit: tuple[Decimal, Decimal] | None = None  # Rs per acre (low, high)
    water: str | None = None
    suitability: float | None = None
    top_features: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    rank: int = 0
    trust: TrustResult | None = None

    @property
    def risk(self) -> str | None:
        return RISK_FOR_WATER.get(self.water) if self.water else None


@dataclass
class Plan:
    district_code: str
    season: str
    options: list[Option]
    profit_ranked: bool
    model_note: str | None  # why the suitability model wasn't used, if it wasn't

    @property
    def top(self) -> list[Option]:
        return self.options[:TOP]

    def find(self, crop: str) -> Option | None:
        return next((o for o in self.options if o.crop == crop), None)


def plan(ctx: FarmContext, season: str, session: Session, today: date | None = None) -> Plan:
    today = today or date.today()
    district = ctx.district
    options = [
        Option(crop=c.crop, season=season, area_ha=c.mean_area_ha, econ=data.economics(district.code, c.crop, season))
        for c in data.candidates(district.code, season)
    ]

    for o in options:
        o.water = water_fit(o.econ.water_need if o.econ else None, ctx.irrigation_source)
        o.price = prices.price_for(session, district, o.crop, today)
        if o.econ and o.econ.cost is not None and o.price:
            o.profit = (o.econ.yield_low * o.price.low - o.econ.cost,
                        o.econ.yield_high * o.price.high - o.econ.cost)

    model_note = _apply_model(ctx, season, options)
    _score(options)
    options.sort(key=lambda o: (-o.score, -o.area_ha))
    for i, o in enumerate(options, start=1):
        o.rank = i
        o.trust = _trust(o, ctx, district, today)
    return Plan(district.code, season, options, any(o.profit for o in options), model_note)


def _apply_model(ctx: FarmContext, season: str, options: list[Option]) -> str | None:
    climate = data.climate_table().get((ctx.district.code, season))
    soil = {k: ctx.soil.get(k) for k in ("n", "p", "k", "ph")}
    if any(v is None for v in soil.values()) or climate is None:
        return str(_l("Soil-climate match not used: it needs your soil card's N, P, K and pH."))
    values = {"N": float(soil["n"]), "P": float(soil["p"]), "K": float(soil["k"]), "ph": float(soil["ph"]),
              "temperature": climate.temperature_c, "humidity": climate.humidity_pct,
              "rainfall": climate.rainfall_mm_per_month}
    outside = model.out_of_range(values)
    if outside:
        return str(_l("Soil-climate match not used: %(inputs)s is outside the public dataset it learned from.",
                      inputs=", ".join(str(FEATURE_LABELS[f]) for f in outside)))
    result = model.predict(values)
    labels = {code: row["dataset_label"] for code, row in crops().items() if row["dataset_label"]}
    for o in options:
        label = labels.get(o.crop)
        if label and label in result.probabilities:
            o.suitability = result.probabilities[label]
            contrib = result.contributions(label)
            o.top_features = [f for f, v in sorted(contrib.items(), key=lambda kv: -kv[1]) if v > 0][:2]
    return None


def _score(options: list[Option]) -> None:
    """A factor known for any candidate counts for all of them. A crop missing
    it scores MISSING[factor]: no profit -> 0, so a crop we can't price can't
    win on money; unknown water or suitability -> neutral. Confidence says the rest."""
    mids = [float(sum(o.profit) / 2) for o in options if o.profit]
    present = {
        "profit": bool(mids),
        "water": any(o.water for o in options),
        "suitability": any(o.suitability is not None for o in options),
    }
    best = max(mids, default=0.0)
    for o in options:
        if o.profit:
            # Share of the best mid-point profit; a loss scores 0, like no price.
            mid = float(sum(o.profit) / 2)
            o.scores["profit"] = max(mid, 0.0) / best if best > 0 else 0.0
        if o.water:
            o.scores["water"] = WATER_SCORE[o.water]
        if o.suitability is not None:
            o.scores["suitability"] = o.suitability  # calibrated probability, not rescaled
        used = [k for k, on in present.items() if on]
        weight = sum(WEIGHTS[k] for k in used)
        o.score = sum(WEIGHTS[k] * o.scores.get(k, MISSING[k]) for k in used) / weight if weight else 0.0


def _money(value: Decimal) -> str:
    return format_decimal(int(value.quantize(Decimal("1"))), format="#,##,##0")


def _trust(o: Option, ctx: FarmContext, district, today: date) -> TrustResult:
    reasons, sources = [], []
    confidence = "high"
    econ = o.econ

    if o.profit:
        if o.price.kind == "mandi":
            price_text = _l("recent mandi prices of ₹%(low)s-%(high)s per quintal",
                            low=_money(o.price.low), high=_money(o.price.high))
        else:
            price_text = _l("MSP of ₹%(price)s per quintal (not a mandi price)", price=_money(o.price.low))
        reasons.append(str(_l("Likely profit ₹%(low)s to ₹%(high)s per acre after costs, at %(price)s.",
                              low=_money(o.profit[0]), high=_money(o.profit[1]), price=price_text)))
    elif econ and econ.cost is None:
        reasons.append(str(_l("Profit not known: no cost-of-cultivation figure for this crop.")))
    else:
        reasons.append(str(_l("Profit not known: no price for this crop yet.")))

    if o.water:
        need = WATER_LABELS[econ.water_need]
        source = IRRIGATION_PHRASES.get(ctx.irrigation_source, IRRIGATION_PHRASES["other"])
        if o.water == "good":
            reasons.append(str(_l("Needs %(need)s water; your %(source)s can supply it.", need=need, source=source)))
        else:
            reasons.append(str(_l("Needs %(need)s water, and you have a %(source)s: risky in a dry year.",
                                  need=need, source=source)))

    if o.suitability is not None and o.suitability >= MODEL_REASON_MIN and o.top_features:
        reasons.append(str(_l("Your soil and season resemble fields where this crop grows in a public dataset (mostly %(inputs)s).",
                              inputs=", ".join(str(FEATURE_LABELS[f]) for f in o.top_features))))
    elif len(reasons) < 3:
        reasons.append(str(_l("Grown on about %(area)s hectares a year in %(district)s in %(season)s.",
                              area=_money(Decimal(o.area_ha)), district=district.name(str(get_locale())),
                              season=SEASON_LABELS[o.season])))

    if econ:
        sources.append(Source(f"{econ.yield_source}, {econ.yield_years}"))
        if econ.cost is not None:
            sources.append(Source(f"{econ.cost_source}, {econ.cost_year}"))
            if econ.cost_start_year and today.year - econ.cost_start_year > OLD_COST_YEARS:
                confidence = cap(confidence, "medium")
        if econ.water_need:
            sources.append(Source(econ.water_source))
        if not econ.verified:
            confidence = cap(confidence, "medium")
    if o.price:
        sources.append(Source(o.price.source, o.price.as_of))
        if o.price.kind == "msp" or not o.price.verified:
            confidence = cap(confidence, "medium")
    if o.suitability is not None:
        sources.append(Source(str(_l("Soil-climate model %(version)s (public dataset, not local farms)",
                                     version=model.bundle()["version"]))))
    sources.extend(ctx.sources)

    # The planner works at district level, so only soil inputs can be estimated
    # inputs here, and only when the model actually used them.
    estimated = [label for key, label in zip(ctx.estimated, ctx.estimated_labels())
                 if key.startswith("soil.") and o.suitability is not None]
    confidence = apply_input_rule(confidence, any_estimated=bool(estimated), any_unknown=o.profit is None)

    value = {
        "crop": o.crop, "season": o.season, "rank": o.rank,
        "profit_low": int(o.profit[0]) if o.profit else None,
        "profit_high": int(o.profit[1]) if o.profit else None,
        "price_kind": o.price.kind if o.price else None,
        "water_need": econ.water_need if econ else None,
        "water_fit": o.water, "risk": o.risk,
    }
    return TrustResult(value=value, confidence=confidence, reasons=reasons[:3], sources=sources,
                       estimated_fields=estimated)


def why_not(p: Plan, crop: str, district_name: str) -> list[str]:
    """Plain reasons a crop isn't in the top 3 (spec 02, R5)."""
    option = p.find(crop)
    season = SEASON_LABELS[p.season]
    if option is None:
        return [str(_l("%(district)s's crop statistics don't show this crop in %(season)s, so it isn't suggested.",
                       district=district_name, season=season))]
    if option.rank <= TOP:
        return [str(_l("It is already in the top 3, at number %(rank)s.", rank=option.rank))]
    reasons = []
    third = p.top[-1]
    if option.profit and third.profit and sum(option.profit) < sum(third.profit):
        gap = (sum(third.profit) - sum(option.profit)) / 2
        reasons.append(str(_l("Likely profit is about ₹%(gap)s per acre lower than the number 3 crop.",
                              gap=_money(gap))))
    elif option.profit is None and p.profit_ranked:
        reasons.append(str(_l("We have no price or cost for it, so its profit couldn't be compared.")))
    if option.water and third.water and WATER_SCORE[option.water] < WATER_SCORE[third.water]:
        reasons.append(str(_l("It needs more water than your field's source reliably gives.")))
    if option.suitability is not None and third.suitability is not None and option.suitability < third.suitability:
        reasons.append(str(_l("Your soil and season match it less well in the public dataset.")))
    if not reasons:
        reasons.append(str(_l("It scored a little lower overall: number %(rank)s of %(total)s.",
                              rank=option.rank, total=len(p.options))))
    return reasons
