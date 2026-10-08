"""Spray & Irrigation Advisor (spec 05)."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from flask import Blueprint, g, render_template
from flask_babel import format_time
from flask_babel import lazy_gettext as _l

from .. import farm_store
from ..extensions import db
from ..models import Event, utcnow
from ..profile_io import current_profile, is_htmx
from ..trust import Source, TrustResult, cap
from ..weather import openmeteo, rules
from ..weather.thresholds import thresholds, value

bp = Blueprint("weather", __name__)

IST = timezone(timedelta(hours=5, minutes=30))  # India has no daylight saving
SPRAY_WORDS = {"good": _l("Good to spray"), "warning": _l("Spray with care"), "critical": _l("Don't spray")}
IRRIGATE_WORDS = {"good": _l("Can irrigate"), "warning": _l("Check soil first"), "critical": _l("Hold irrigation")}


def _hour(h: int) -> str:
    return format_time(time(h % 24, 0), format="short")


def reason_text(reason: rules.Reason) -> str:
    p = reason.params
    texts = {
        "good_window": lambda: _l("Good time %(start)s to %(end)s: wind about %(wind)s km/h and no rain for %(hours)s hours after.",
                                  start=_hour(p["start"]), end=_hour(p["end"]), wind=p["wind"],
                                  hours=int(value("spray_rain_free_hours"))),
        "calm": lambda: _l("The air is almost still (%(start)s to %(end)s), so spray can drift. Spray with care or wait for a light breeze.",
                           start=_hour(p["start"]), end=_hour(p["end"])),
        "rain": lambda: _l("Rain %(prob)s%% likely around %(time)s.", prob=p["prob"], time=_hour(p["hour"])),
        "wind": lambda: _l("Wind up to %(wind)s km/h: the spray will blow away.", wind=p["wind"]),
        "window_passed": lambda: _l("Today's spraying hours are over."),
        "recent_rain": lambda: _l("About %(mm)s mm of rain in the 2 days before (fallen or forecast): hold irrigation.", mm=p["mm"]),
        "rain_coming": lambda: _l("About %(mm)s mm of rain expected today and tomorrow: hold irrigation.", mm=p["mm"]),
        "some_rain": lambda: _l("Some rain expected (about %(mm)s mm): check the soil before irrigating.", mm=p["mm"]),
        "no_rain": lambda: _l("No useful rain expected: irrigate if your crop needs it."),
    }
    return str(texts[reason.code]())


def _now_local() -> datetime:
    return datetime.now(IST).replace(tzinfo=None)


def _advice(profile: dict):
    farm = profile["farm"]
    if farm["lat"] is None or farm["lon"] is None:
        return None, None, None
    stale_hours = value("weather_stale_hours")
    result = openmeteo.forecast(db.session, farm["lat"], farm["lon"], stale_after=timedelta(hours=stale_hours))
    if result.data is None:
        return [], result.source, None
    t = {k: value(k) for k in thresholds()}
    verdicts = rules.days(result.data.hours, t, _now_local())

    confidence = "high"
    if any(th.status == "proposed" for th in thresholds().values()):
        confidence = cap(confidence, "medium")  # some cut-offs are still proposals
    estimated = []
    if farm["location_source"] == "district":
        confidence = cap(confidence, "medium")
        estimated.append(str(_l("field location")))
    if result.source.stale:
        confidence = "low"
    reasons = [str(_l("Spray windows follow cited guidance: wind %(low)s to %(high)s km/h, no rain for %(hours)s hours after spraying.",
                      low=int(value("spray_wind_min_kmh")), high=int(value("spray_wind_max_kmh")),
                      hours=int(value("spray_rain_free_hours")))),
               str(_l("Irrigation advice uses rain only, not your crop's stage or soil moisture yet. Check the soil."))]
    if result.source.stale:
        reasons.insert(0, str(_l("This forecast is old: we couldn't refresh it.")))
    trust = TrustResult(
        value={"days": [{"day": v.day.isoformat(), "spray": v.spray.status, "irrigate": v.irrigate.status}
                        for v in verdicts]},
        confidence=confidence, reasons=reasons,
        sources=[Source(openmeteo.CREDIT, result.source.fetched_at.date() if result.source.fetched_at else None),
                 Source(str(_l("AgriSense thresholds, some still proposed (see the advisor spec)")))],
        estimated_fields=estimated)
    return verdicts, result.source, trust


@bp.get("/weather")
def index():
    return render_template("weather/index.html")


@bp.post("/weather/advice")
def advice():
    profile = current_profile()
    verdicts, source, trust = _advice(profile)
    if trust is not None:
        profile["last_results"]["weather"] = trust.to_dict()
        if g.get("user") is not None:
            row = farm_store.current_plot(db.session, g.user)
            if row is not None:
                db.session.add(Event(plot_id=row.id, kind="weather.verdict", occurred_at=utcnow(),
                                     payload=trust.to_dict(), payload_version=1, source="app"))
                db.session.commit()
    template = "weather/_advice.html" if is_htmx() else "weather/index.html"
    return render_template(template, verdicts=verdicts, source=source, trust=trust, profile=profile,
                           reason_text=reason_text, spray_words=SPRAY_WORDS, irrigate_words=IRRIGATE_WORDS,
                           today=_now_local().date(), loaded=True)


@bp.post("/weather/today")
def today_card():
    verdicts, source, trust = _advice(current_profile())
    return render_template("weather/_today.html", day=(verdicts or [None])[0], source=source,
                           reason_text=reason_text, spray_words=SPRAY_WORDS, irrigate_words=IRRIGATE_WORDS,
                           no_field=verdicts is None)
