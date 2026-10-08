"""Mandi Prices + offer checker (spec 04)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from flask import Blueprint, current_app, g, render_template, request
from flask_babel import format_date, format_decimal, get_locale
from flask_babel import lazy_gettext as _l

from .. import farm_profile, farm_store, units
from ..crops import crop_name
from ..extensions import db
from ..market import board as market_board
from ..market import commodities, mandis
from ..models import Event, utcnow
from ..profile_io import current_profile, is_htmx
from ..trust import Source, TrustResult

bp = Blueprint("market", __name__)

ERRORS = {
    "crop": _l("Choose a crop."),
    "offer": _l("Enter the offer as a number of rupees per quintal, like 2400."),
    "rate": _l("Enter the transport cost as a number, like 1.5."),
}


def _crop_choices(locale: str) -> list[tuple[str, str]]:
    return sorted(((c, crop_name(c, locale)) for c in commodities.tradable()), key=lambda x: x[1])


@bp.get("/market")
def index():
    crop = request.args.get("crop")
    return render_template("market/index.html", form={"crop": crop if crop in commodities.tradable() else None},
                           crop_choices=_crop_choices(str(get_locale())))


def _money(value: Decimal) -> str:
    return format_decimal(int(value), format="#,##,##0")


def _offer_trust(quote, verdict, band: Decimal, offer: Decimal) -> TrustResult:
    reasons = [str(_l("Modal price at %(mandi)s on %(date)s: ₹%(modal)s per quintal.", mandi=quote.mandi.market,
                      date=format_date(quote.arrival_date, "medium"), modal=_money(quote.modal_price)))]
    if quote.min_price and quote.max_price:
        reasons.append(str(_l("Traders paid ₹%(low)s to ₹%(high)s there that day.",
                              low=_money(quote.min_price), high=_money(quote.max_price))))
    reasons.append(str(_l("An offer within %(band)s%% of the modal price counts as fair.", band=band)))
    confidence = "high"
    if quote.stale:
        reasons.insert(0, str(_l("This price is %(days)s days old, so today's may differ.", days=quote.days_old)))
        confidence = "low"
    return TrustResult(
        value={"offer": str(offer), "status": verdict.status, "gap": str(verdict.gap), "gap_pct": str(verdict.gap_pct),
               "mandi": quote.mandi.market, "modal": str(quote.modal_price), "date": quote.arrival_date.isoformat()},
        confidence=confidence, reasons=reasons,
        sources=[Source(f"Agmarknet, {quote.mandi.market}", quote.arrival_date)])


@bp.post("/market/board")
def show_board():
    locale = str(get_locale())
    form = request.form
    profile = current_profile()
    template = "market/_board.html" if is_htmx() else "market/index.html"
    context = {"form": form, "crop_choices": _crop_choices(locale), "profile": profile, "errors": {}}

    farm = profile["farm"]
    if farm["lat"] is None or farm["lon"] is None:
        return render_template(template, problem="no_field", **context)
    crop = form.get("crop")
    if crop not in commodities.tradable():
        context["errors"]["crop"] = str(ERRORS["crop"])
        return render_template(template, **context)

    rate_raw = (form.get("transport_rate") or "").strip()
    rate = farm_profile.transport_rate(rate_raw) if rate_raw else profile["prefs"]["transport_rate"]
    if rate_raw and rate is None:
        context["errors"]["transport_rate"] = str(ERRORS["rate"])
    elif rate_raw:
        profile["prefs"]["transport_rate"] = rate
        if g.get("user") is not None:
            g.user.prefs = dict(profile["prefs"])
            db.session.commit()

    offer = None
    offer_raw = (form.get("offer") or "").strip()
    if offer_raw:
        try:
            offer = units.parse_decimal(offer_raw)
            if offer <= 0:
                raise ValueError
        except ValueError:
            context["errors"]["offer"] = str(ERRORS["offer"])

    cfg = current_app.config
    today = date.today()
    result = market_board.board(
        db.session, farm["lat"], farm["lon"], crop, today, window_days=cfg["PRICE_WINDOW_DAYS"],
        stale_days=cfg["PRICE_STALE_DAYS"], transport_rate=Decimal(rate) if rate else None, n=cfg["NEAREST_MANDIS"])

    verdict = trust = None
    band = Decimal(cfg["FAIR_BAND_PCT"])
    reference = result.reference
    if offer is not None and reference is not None:
        verdict = market_board.check_offer(offer, reference.modal_price, band)
        trust = _offer_trust(reference, verdict, band, offer)
        profile["last_results"]["market"] = trust.to_dict()
        if g.get("user") is not None:
            row = farm_store.current_plot(db.session, g.user)
            if row is not None:
                db.session.add(Event(plot_id=row.id, kind="market.offer_check", occurred_at=utcnow(),
                                     payload=trust.to_dict(), payload_version=1, source="app"))
                db.session.commit()
    return render_template(template, board=result, verdict=verdict, trust=trust, offer=offer, crop=crop,
                           rate=rate, band=band, location_estimated=farm["location_source"] == "district",
                           **context)


@bp.post("/today/prices")
def today_prices():
    """Price change for the farmer's crop at the nearest mandi with two recent price days."""
    profile = current_profile()
    planner = profile["last_results"].get("planner", {}).get("value", {})
    crop = (planner.get("top") or [None])[0]
    farm = profile["farm"]
    if not crop or crop not in commodities.tradable() or farm["lat"] is None:
        return render_template("market/_today.html", change=None)
    cfg = current_app.config
    today = date.today()

    for mandi, km in mandis.nearest(farm["lat"], farm["lon"], cfg["NEAREST_MANDIS"]):
        change = market_board.price_change(db.session, mandi, crop, today, cfg["PRICE_WINDOW_DAYS"])
        if change:
            return render_template("market/_today.html", change=change, mandi=mandi, crop=crop,
                                   stale=(today - change[0]).days > cfg["PRICE_STALE_DAYS"])
    return render_template("market/_today.html", change=None, crop=crop)
