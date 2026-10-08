"""Spray & Irrigation Advisor (spec 05). Weather here is synthetic test data."""

import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from werkzeug.datastructures import MultiDict

from agrisense import farm_profile as fp
from agrisense.extensions import db
from agrisense.models import CachedWeather, Event, utcnow
from agrisense.weather import openmeteo, rules
from agrisense.weather.thresholds import thresholds, value

DATA = Path(__file__).resolve().parent.parent / "data"
CASES = json.loads((DATA / "weather_cases.json").read_text(encoding="utf-8"))["cases"]
HX = {"HX-Request": "true"}


def series(now: datetime, base: dict, overrides: list[dict]) -> list[rules.Hour]:
    start = now.replace(minute=0) - timedelta(hours=48)
    hours = []
    for i in range(48 + 72 + 24):
        t = start + timedelta(hours=i)
        v = dict(base)
        for o in overrides:
            if datetime.fromisoformat(o["from"]) <= t < datetime.fromisoformat(o["to"]):
                v.update({k: o[k] for k in o if k not in ("from", "to")})
        hours.append(rules.Hour(t, v["p"], v["mm"], v["w"], v["rh"], v["t"]))
    return hours


def t():
    return {k: value(k) for k in thresholds()}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_weather_cases(case):
    now = datetime.fromisoformat(case["now"])
    days = {d.day.isoformat(): d for d in rules.days(series(now, case["base"], case["overrides"]), t(), now)}
    exp = case["expect"]
    day = days[exp["day"]]
    assert day.spray.status == exp["spray"]
    if "spray_reason" in exp:
        assert day.spray.reason.code == exp["spray_reason"]
    if "window" in exp:
        assert list(day.spray.window) == exp["window"]
    for key, val in exp.get("reason_params", {}).items():
        assert day.spray.reason.params[key] == val
    assert day.irrigate.status == exp["irrigate"]
    if "irrigate_reason" in exp:
        assert day.irrigate.reason.code == exp["irrigate_reason"]
    for key, val in exp.get("irrigate_params", {}).items():
        assert day.irrigate.reason.params[key] == val


def test_there_are_ten_cases_and_three_days():
    assert len(CASES) == 10
    now = datetime(2026, 10, 10, 5)
    assert len(rules.days(series(now, CASES[0]["base"], []), t(), now)) == 3


def test_every_threshold_is_cited_or_marked_for_review():
    with (DATA / "weather_thresholds.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        assert r["status"] in ("cited", "proposed") and r["source"]
        if r["status"] == "proposed":
            assert "FOR REVIEW" in r["notes"]
    assert {r["key"] for r in rows if r["status"] == "cited"} >= {"spray_wind_max_kmh", "spray_rain_free_hours"}


def test_rules_read_no_literal_thresholds():
    source = (Path(rules.__file__)).read_text(encoding="utf-8")
    for literal in ("19", "50", "0.5"):
        assert f" {literal}" not in source.split('"""', 2)[2]  # outside the docstring


# ---------------------------------------------------------------- adapter


def payload(now: datetime, wind=10.0, prob=5) -> dict:
    hours = [now.replace(minute=0) - timedelta(hours=48) + timedelta(hours=i) for i in range(120)]
    return {"hourly": {"time": [h.isoformat(timespec="minutes") for h in hours],
                       "precipitation_probability": [prob] * 120, "precipitation": [0.0] * 120,
                       "wind_speed_10m": [wind] * 120, "relative_humidity_2m": [60] * 120,
                       "temperature_2m": [28.0] * 120}}


def test_forecast_is_fetched_once_then_cached(session):
    calls = []

    def get(url, params, timeout):
        calls.append(params)
        return payload(datetime(2026, 10, 10, 5))

    first = openmeteo.forecast(session, 28.4071, 77.8512, get=get)
    second = openmeteo.forecast(session, 28.4149, 77.8549, get=get)  # same 0.01 degree cell
    assert len(calls) == 1 and first.data and second.data
    p = calls[0]
    assert p["latitude"] == "28.41" and p["longitude"] == "77.85"
    assert p["forecast_days"] == 3 and p["past_days"] == 2 and p["timezone"] == "Asia/Kolkata"
    assert set(p["hourly"].split(",")) == {"precipitation_probability", "precipitation", "wind_speed_10m",
                                           "relative_humidity_2m", "temperature_2m"}
    assert first.source.name.startswith("Open-Meteo") and not first.source.stale


def test_failed_refresh_falls_back_to_the_cache_labelled_old(session):
    old = utcnow() - timedelta(hours=5)
    session.add(CachedWeather(source="open-meteo", lat_r=Decimal("28.41"), lon_r=Decimal("77.85"),
                              payload=payload(datetime(2026, 10, 10, 5)), fetched_at=old, valid_until=old + timedelta(hours=1)))
    session.commit()

    def down(url, params, timeout):
        raise TimeoutError

    result = openmeteo.forecast(session, 28.41, 77.85, get=down)
    assert result.data is not None and result.source.stale and result.source.note == "refresh_failed"


def test_no_cache_and_no_network_gives_no_data(session):
    def down(url, params, timeout):
        raise OSError

    result = openmeteo.forecast(session, 28.41, 77.85, get=down)
    assert result.data is None and result.source.note == "unavailable"


def test_malformed_response_is_not_cached(session):
    openmeteo.forecast(session, 28.41, 77.85, get=lambda u, p, t: {"oops": True})
    assert session.scalar(select(CachedWeather)) is None


# ---------------------------------------------------------------- HTTP


def seed(session, lat=28.41, lon=77.85, **kw):
    now = utcnow()
    local = datetime.now() .replace(minute=0, second=0, microsecond=0)
    session.add(CachedWeather(source="open-meteo", lat_r=Decimal(str(lat)), lon_r=Decimal(str(lon)),
                              payload=payload(local, **kw), fetched_at=now, valid_until=now + timedelta(hours=1)))
    session.commit()


def profile(source="gps"):
    p = fp.empty()
    if source == "gps":
        fp.apply_where(p, MultiDict({"location_source": "gps", "lat": "28.41", "lon": "77.85"}))
    else:
        fp.apply_where(p, MultiDict({"location_source": "district", "district_code": "UP-bulandshahr"}))
    return p


@pytest.fixture
def en(client):
    client.set_cookie("lang", "en")


def test_weather_page_loads_advice_by_htmx(client):
    html = client.get("/weather").get_data(as_text=True)
    assert 'hx-post="/weather/advice"' in html


def test_advice_needs_a_field(client, en):
    html = client.post("/weather/advice", data={"profile": ""}, headers=HX).get_data(as_text=True)
    assert "tell us where your field is" in html


def test_advice_from_cached_forecast(client, en, session):
    seed(session, wind=25)
    html = client.post("/weather/advice", data={"profile": json.dumps(profile())}, headers=HX).get_data(as_text=True)
    assert "Don&#39;t spray" in html or "Don't spray" in html
    assert "Wind up to 25 km/h" in html and "Open-Meteo.com (CC BY 4.0)" in html
    assert "Medium confidence" in html  # some thresholds are still proposals
    saved = json.loads(html.split("data-profile-update>")[1].split("</script>")[0])
    assert saved["last_results"]["weather"]["value"]["days"]


def test_district_location_is_marked_estimated(client, en, session):
    p = profile("district")
    seed(session, lat=round(p["farm"]["lat"], 2), lon=round(p["farm"]["lon"], 2))
    html = client.post("/weather/advice", data={"profile": json.dumps(p)}, headers=HX).get_data(as_text=True)
    assert "Estimated, not measured: field location" in html


def test_no_forecast_gives_a_clear_message(client, en, monkeypatch):
    monkeypatch.setattr(openmeteo, "fetch_json", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    import agrisense.weather.openmeteo as om
    original = om.forecast

    def no_network(session, lat, lon, **kw):
        kw["get"] = lambda *a: (_ for _ in ()).throw(OSError())
        return original(session, lat, lon, **kw)

    monkeypatch.setattr(om, "forecast", no_network)
    html = client.post("/weather/advice", data={"profile": json.dumps(profile())}, headers=HX).get_data(as_text=True)
    assert "couldn&#39;t get the forecast" in html or "couldn't get the forecast" in html


def test_today_card(client, en, session):
    seed(session)
    html = client.post("/weather/today", data={"profile": json.dumps(profile())}, headers=HX).get_data(as_text=True)
    assert "Spray or water today?" in html and "Can irrigate" in html


def test_advice_in_hindi(client, session):
    seed(session, wind=25)
    client.set_cookie("lang", "hi")
    html = client.post("/weather/advice", data={"profile": json.dumps(profile())}, headers=HX).get_data(as_text=True)
    assert "छिड़काव न करें" in html


def test_logged_in_advice_is_an_event(client, en, session):
    client.post("/farm/save", data={"phone": "9876543210", "pin": "4826", "pin_confirm": "4826", "consent": "yes",
                                    "profile": json.dumps(profile())})
    seed(session)
    client.post("/weather/advice", data={"profile": ""}, headers=HX)
    assert session.scalar(select(Event).where(Event.kind == "weather.verdict")) is not None
