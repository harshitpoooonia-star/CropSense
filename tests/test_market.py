"""Mandi Prices + offer checker (spec 04). Prices in the fixture are synthetic."""

import html as htmllib
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from werkzeug.datastructures import MultiDict

from agrisense import farm_profile as fp
from agrisense.extensions import db
from agrisense.market import agmarknet, board, commodities, mandis
from agrisense.models import CachedPrice, Event

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "agmarknet" / "day.json").read_text(encoding="utf-8"))
DAY = date(2026, 10, 7)
HX = {"HX-Request": "true"}


def fake_get(days_with_data=(DAY,)):
    calls = []

    def get(url, params, timeout):
        calls.append(params)
        day = agmarknet._date(params["filters[Arrival_Date]"])
        return FIXTURE if day in days_with_data else {"total": 0, "records": []}

    get.calls = calls
    return get


def load(session, today=DAY + timedelta(days=1)):
    return agmarknet.refresh(session, "test-key", days=3, today=today, get=fake_get())


# ---------------------------------------------------------------- adapter


def test_normalize_keeps_target_districts_and_valid_prices():
    rows = [r for r in map(agmarknet.normalize, FIXTURE["records"]) if r]
    assert {r["market"] for r in rows} == {"Khurja", "Bulandshahar", "Dadri"}  # Meerut dropped, zero modal dropped
    first = rows[0]
    assert first["arrival_date"] == DAY and first["modal_price"] == Decimal("2400")


def test_refresh_stores_and_is_idempotent(session):
    get = fake_get()
    report = agmarknet.refresh(session, "test-key", days=3, today=DAY + timedelta(days=1), get=get)
    assert report.days == 3 and report.rows_stored == 5 and report.error is None
    assert get.calls[0]["filters[State]"] == "Uttar Pradesh"
    assert get.calls[0]["filters[Arrival_Date]"] == "08/10/2026"
    agmarknet.refresh(session, "test-key", days=3, today=DAY + timedelta(days=1), get=fake_get())
    assert session.scalar(select(func.count(CachedPrice.id))) == 5


def test_refresh_without_key_does_nothing(session):
    assert agmarknet.refresh(session, None).error == "no_key"


def test_refresh_stops_on_a_bad_key_and_skips_failed_days(session):
    def bad(url, params, timeout):
        raise agmarknet.FatalApiError("HTTP 403 from data.gov.in")

    assert agmarknet.refresh(session, "k", days=3, today=DAY, get=bad).error.startswith("HTTP 403")

    def flaky(url, params, timeout):
        raise RuntimeError("data.gov.in failed after 3 tries (TimeoutError)")

    report = agmarknet.refresh(session, "k", days=2, today=DAY, get=flaky)
    assert report.failed_days == [DAY, DAY - timedelta(days=1)] and report.error is None


def test_fetch_day_paginates(monkeypatch):
    monkeypatch.setattr(agmarknet, "PAGE_LIMIT", 2)
    pages = [{"total": 3, "records": [{}, {}]}, {"total": 3, "records": [{}]}]
    seen = []

    def get(url, params, timeout):
        seen.append(params["offset"])
        return pages[len(seen) - 1]

    assert len(agmarknet.fetch_day("k", DAY, get)) == 3 and seen == [0, 2]


# ---------------------------------------------------------------- matching


@pytest.mark.parametrize("commodity, crop", [("Wheat", "wheat"), ("Mustard Oil", None), ("Mustard", "mustard"),
                                             ("Paddy(Dhan)(Common)", "paddy"), ("Bengal Gram(Gram)(Whole)", "chickpea"),
                                             ("Green Gram (Moong)(Whole)", "mungbean")])
def test_commodity_matching(commodity, crop):
    assert commodities.crop_for(commodity) == crop


def test_mandi_matching_and_nearest():
    assert mandis.match("Bulandshahar").market == "Bulandshahr"
    assert mandis.match("Khurja").district_code == "UP-bulandshahr"
    assert mandis.match("Meerut") is None
    near = mandis.nearest(28.41, 77.85, 5)
    assert near[0][0].market == "Bulandshahr" and len(near) == 5
    assert [km for _m, km in near] == sorted(km for _m, km in near)


def test_every_mandi_row_is_sourced():
    assert all(m.coord_source or m.lat is None for m in mandis.mandis())


# ---------------------------------------------------------------- board + offers


def test_board_quotes_nearest_mandis_with_dates(session):
    load(session)
    b = board.board(session, 28.41, 77.85, "wheat", DAY + timedelta(days=1), window_days=30, stale_days=3,
                    transport_rate=Decimal("1.5"))
    quotes = {q.mandi.market: q for q in b.quotes}
    khurja = quotes["Khurja"]
    assert khurja.modal_price == Decimal(2425)  # median of two varieties
    assert khurja.min_price == Decimal(2300) and khurja.max_price == Decimal(2550)
    assert not khurja.stale and khurja.days_old == 1
    assert khurja.net == khurja.modal_price - khurja.transport
    assert b.reference.mandi.market == "Bulandshahr"  # nearest with a fresh price
    assert "Sikandrabad" in {m.market for m, _km in b.without_data}


def test_old_prices_are_flagged(session):
    load(session)
    b = board.board(session, 28.41, 77.85, "wheat", DAY + timedelta(days=5), window_days=30, stale_days=3,
                    transport_rate=None)
    assert all(q.stale and q.days_old == 5 for q in b.quotes) and b.source.stale
    assert b.reference is not None  # an old price is still shown, labelled


@pytest.mark.parametrize("offer, status", [(2280, "fair"), (2279, "below"), (2520, "fair"), (2521, "above"), (2400, "fair")])
def test_offer_band_edges(offer, status):
    assert board.check_offer(Decimal(offer), Decimal(2400), Decimal(5)).status == status


def test_offer_gap():
    v = board.check_offer(Decimal(2160), Decimal(2400), Decimal(5))
    assert v.gap == Decimal(-240) and v.gap_pct == Decimal("-10.0")


# ---------------------------------------------------------------- HTTP


def profile(**prefs):
    p = fp.empty()
    fp.apply_where(p, MultiDict({"location_source": "gps", "lat": "28.41", "lon": "77.85"}))
    p["prefs"].update(prefs)
    return p


@pytest.fixture
def en(client):
    client.set_cookie("lang", "en")


def post_board(client, **form):
    data = {"crop": "wheat", "profile": json.dumps(profile()), **form}
    return client.post("/market/board", data=data, headers=HX).get_data(as_text=True)


def test_market_needs_a_field(client, en):
    html = client.post("/market/board", data={"crop": "wheat", "profile": ""}, headers=HX).get_data(as_text=True)
    assert "tell us where your field is" in html


def test_offer_verdict_over_http(client, en, session):
    load(session, today=date.today() - timedelta(days=0))
    html = post_board(client, offer="2000")
    # Fixture rows are dated 7 Oct 2026; relative to today they may be old, which the page must say.
    assert "Below the mandi price" in html and "Trader's offer: ₹2,000" in htmllib.unescape(html)
    assert "Bulandshahr" in html and "Agmarknet" in html
    saved = json.loads(html.split("data-profile-update>")[1].split("</script>")[0])
    assert saved["last_results"]["market"]["value"]["status"] == "below"


def test_no_prices_gives_an_empty_state(client, en):
    html = post_board(client, offer="2400")
    assert "No mandi prices for this crop near you" in html and "agmarknet.gov.in" in html


def test_transport_rate_is_remembered(client, en, session):
    load(session, today=date.today())
    html = post_board(client, transport_rate="2")
    saved = json.loads(html.split("data-profile-update>")[1].split("</script>")[0])
    assert saved["prefs"]["transport_rate"] == "2"
    assert "After transport" in html


@pytest.mark.parametrize("form, text", [({"offer": "abc"}, "rupees per quintal"), ({"transport_rate": "x"}, "transport cost"),
                                        ({"crop": "coffee"}, "Choose a crop")])
def test_bad_input(client, en, form, text):
    assert text in post_board(client, **form)


def test_market_in_hindi(client, session):
    load(session, today=date.today())
    client.set_cookie("lang", "hi")
    html = post_board(client, offer="2000")
    assert "मंडी भाव से कम" in html and "गेहूँ" in html


def test_logged_in_offer_check_is_an_event(client, en, session):
    client.post("/farm/save", data={"phone": "9876543210", "pin": "4826", "pin_confirm": "4826", "consent": "yes",
                                    "profile": json.dumps(profile())})
    load(session, today=date.today())
    client.post("/market/board", data={"crop": "wheat", "offer": "2400", "profile": ""}, headers=HX)
    assert session.scalar(select(Event).where(Event.kind == "market.offer_check")) is not None


def test_today_shows_the_price_change(client, en, session):
    for i, modal in ((1, 2450), (2, 2400)):
        session.add(CachedPrice(source="agmarknet", state="UP", district="Bulandshahar", market="Bulandshahar",
                                commodity="Wheat", variety="Other", grade="FAQ",
                                arrival_date=date.today() - timedelta(days=i), modal_price=Decimal(modal)))
    session.commit()
    p = profile()
    p["last_results"]["planner"] = {"value": {"top": ["wheat"]}, "confidence": "medium",
                                    "sources": [{"name": "x", "date": None}]}
    html = client.post("/today/prices", data={"profile": json.dumps(p)}, headers=HX).get_data(as_text=True)
    assert "Wheat at Bulandshahr: ₹2,450" in html and "Up ₹50" in html


# ---------------------------------------------------------------- warm-up


def test_refresh_endpoint_is_hidden_without_a_token(client):
    assert client.post("/internal/refresh/prices").status_code == 404


def test_refresh_endpoint_needs_the_token(app, client, monkeypatch):
    app.config["REFRESH_TOKEN"] = "s3cret-token"
    app.config["DATA_GOV_IN_KEY"] = "k"
    assert client.post("/internal/refresh/prices", headers={"Authorization": "Bearer nope"}).status_code == 401
    monkeypatch.setattr(agmarknet, "refresh", lambda session, key, days: agmarknet.RefreshReport(days=days, rows_stored=4))
    r = client.post("/internal/refresh/prices?days=99", headers={"Authorization": "Bearer s3cret-token"})
    assert r.status_code == 200 and r.get_json()["days"] == 7  # capped


def test_cli_refresh_needs_a_key(app):
    result = app.test_cli_runner().invoke(args=["agrisense", "refresh-prices"])
    assert result.exit_code != 0 and "DATA_GOV_IN_KEY" in result.output
