"""Crop Planner v2 (spec 02). Synthetic numbers in this file are test data only."""

import html as htmllib
import json
import subprocess
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from werkzeug.datastructures import MultiDict

from agrisense import farm_context
from agrisense import farm_profile as fp
from agrisense.crops import crops
from agrisense.extensions import db
from agrisense.models import CachedPrice, Event
from agrisense.planner import data, model, prices, rank

ROOT = Path(__file__).resolve().parent.parent
BULANDSHAHR = "UP-bulandshahr"
HX = {"HX-Request": "true"}


def profile(irrigation="tubewell", soil=None, district=BULANDSHAHR):
    p = fp.empty()
    fp.apply_where(p, MultiDict({"location_source": "district", "district_code": district}))
    fp.apply_area(p, MultiDict({"area": "1", "area_unit": "acre"}))
    fp.apply_water(p, MultiDict({"irrigation_source": irrigation}))
    fp.apply_soil(p, MultiDict(soil or {"skip": "1"}))
    return p


@pytest.fixture
def ctx_req(app):
    with app.test_request_context("/", headers={"Accept-Language": "en"}):
        yield


# ---------------------------------------------------------------- data tables


def test_every_economics_row_is_sourced_and_unverified_until_checked():
    rows = data.economics_table().values()
    assert len(rows) >= 50
    for r in rows:
        assert r.yield_source and r.yield_years and r.crop in crops()
        assert r.yield_low <= r.yield_median <= r.yield_high
        assert (r.cost is None) or (r.cost_source and r.cost_year)
        assert (r.water_need is None) or r.water_source
        assert r.verified is False  # a person flips this after checking the source


def test_seasons_come_from_district_statistics():
    rabi = {c.crop for c in data.candidates(BULANDSHAHR, "rabi")}
    kharif = {c.crop for c in data.candidates(BULANDSHAHR, "kharif")}
    assert {"wheat", "mustard", "potato"} <= rabi and "paddy" not in rabi
    assert {"paddy", "sugarcane", "maize"} <= kharif and "wheat" not in kharif
    assert all(c.source and c.mean_area_ha >= 100 for c in data.season_crops())


def test_msp_and_climate_rows_are_sourced():
    assert all(m.source and m.price > 0 for m in data.msp_table().values())
    assert data.msp_table()["wheat"].marketing_season == "rabi 2027-28"
    for c in data.climate_table().values():
        assert c.source.startswith("Open-Meteo") and c.season in data.SEASONS


# ---------------------------------------------------------------- rules


@pytest.mark.parametrize("need, irrigation, fit", [
    ("high", "tubewell", "good"), ("high", "canal", "good"), ("high", "rainfed", "poor"),
    ("medium", "rainfed", "caution"), ("low", "rainfed", "good"), ("high", "purchased", "caution"),
    ("medium", "other", "good"), (None, "tubewell", None), ("low", None, None),
])
def test_water_fit(need, irrigation, fit):
    assert rank.water_fit(need, irrigation) == fit


def _econ(crop, low, high, cost, water="medium"):
    return data.Economics(BULANDSHAHR, crop, "rabi", Decimal(low), Decimal(low), Decimal(high), "y", "src",
                          Decimal(cost) if cost is not None else None, "2021-22", "cost src", water, "water src", False)


@pytest.fixture
def fake_district(monkeypatch):
    """Three synthetic crops, so ranking maths can be checked exactly."""
    econ = {"wheat": _econ("wheat", 10, 20, 1000), "mustard": _econ("mustard", 5, 6, 500, "low"),
            "potato": _econ("potato", 100, 120, 5000)}
    monkeypatch.setattr(data, "candidates", lambda d, s: [
        data.SeasonCrop(d, c, s, area, "y", "src") for c, area in (("potato", 900), ("wheat", 800), ("mustard", 700))])
    monkeypatch.setattr(data, "economics", lambda d, c, s: econ.get(c))
    fixed = {"wheat": prices.PriceInfo("msp", Decimal(100), Decimal(100), date(2026, 9, 30), "MSP test", False),
             "mustard": prices.PriceInfo("msp", Decimal(500), Decimal(500), date(2026, 9, 30), "MSP test", False)}
    monkeypatch.setattr(prices, "price_for", lambda session, district, crop, today: fixed.get(crop))


def test_profit_is_yield_times_price_minus_cost(app, ctx_req, fake_district):
    plan = rank.plan(farm_context.build(profile()), "rabi", db.session, date(2026, 10, 8))
    wheat, mustard = plan.find("wheat"), plan.find("mustard")
    assert wheat.profit == (Decimal(10 * 100 - 1000), Decimal(20 * 100 - 1000))
    assert mustard.profit == (Decimal(5 * 500 - 500), Decimal(6 * 500 - 500))


def test_a_crop_without_a_price_cannot_win_on_profit(app, ctx_req, fake_district):
    plan = rank.plan(farm_context.build(profile()), "rabi", db.session, date(2026, 10, 8))
    assert [o.crop for o in plan.options] == ["mustard", "wheat", "potato"]
    potato = plan.find("potato")
    assert potato.profit is None and potato.trust.confidence == "low"
    assert any("Profit not known" in r for r in potato.trust.reasons)


def test_rainfed_field_marks_thirsty_crops_risky(app, ctx_req):
    plan = rank.plan(farm_context.build(profile("rainfed")), "kharif", db.session)
    paddy = plan.find("paddy")
    assert paddy.water == "poor" and paddy.risk == "high"
    assert any("risky in a dry year" in r for r in paddy.trust.reasons)


def test_unverified_data_caps_confidence_at_medium(app, ctx_req):
    plan = rank.plan(farm_context.build(profile()), "rabi", db.session)
    assert all(o.trust.confidence in ("medium", "low") for o in plan.options)
    # District-level planner: a district-only location isn't an estimated input here.
    assert all(o.trust.estimated_fields == [] for o in plan.options)
    assert plan.profit_ranked  # MSP gives a price for wheat and mustard


def test_mandi_prices_beat_msp_when_cached(app, ctx_req):
    today = date(2026, 10, 8)
    for i, modal in enumerate((2400, 2450, 2500, 2550, 2600)):
        db.session.add(CachedPrice(source="agmarknet", state="Uttar Pradesh", district="Bulandshahr",
                                   market="Test Mandi", commodity="Wheat", variety="Other", grade="FAQ",
                                   arrival_date=today - timedelta(days=i), modal_price=Decimal(modal)))
    db.session.commit()
    price = prices.price_for(db.session, farm_context.build(profile()).district, "wheat", today)
    assert price.kind == "mandi" and price.low == Decimal(2450) and price.high == Decimal(2550)
    assert price.as_of == today and "Agmarknet" in price.source


def test_old_mandi_rows_and_other_commodities_are_ignored(app, ctx_req):
    today = date(2026, 10, 8)
    for i in range(5):
        db.session.add(CachedPrice(source="agmarknet", state="UP", district="Bulandshahr", market="M",
                                   commodity="Wheat Atta", variety="v", grade=f"g{i}", arrival_date=today,
                                   modal_price=Decimal(3000)))
        db.session.add(CachedPrice(source="agmarknet", state="UP", district="Bulandshahr", market="M",
                                   commodity="Wheat", variety="v", grade=f"g{i}", arrival_date=today - timedelta(days=60),
                                   modal_price=Decimal(3000)))
    db.session.commit()
    assert prices.price_for(db.session, farm_context.build(profile()).district, "wheat", today).kind == "msp"


# ---------------------------------------------------------------- model


def test_model_has_no_pca_and_explains_real_inputs():
    pipe = model.bundle()["model"].calibrated_classifiers_[0].estimator
    assert list(pipe.named_steps) == ["scale", "forest"]
    values = {"N": 90, "P": 42, "K": 43, "temperature": 21, "humidity": 82, "ph": 6.5, "rainfall": 203}
    result = model.predict(values)
    assert abs(sum(result.probabilities.values()) - 1) < 1e-6
    assert set(result.contributions("rice")) == set(model.bundle()["features"])


def test_model_refuses_inputs_outside_its_range():
    assert model.out_of_range({"N": 300, "P": 40, "K": 40, "temperature": 20, "humidity": 70, "ph": 7, "rainfall": 100}) == ["N"]


def test_model_is_skipped_without_a_soil_card(app, ctx_req):
    plan = rank.plan(farm_context.build(profile()), "kharif", db.session)
    assert "needs your soil card" in plan.model_note
    assert all(o.suitability is None for o in plan.options)


def test_model_is_skipped_when_soil_values_are_out_of_range(app, ctx_req):
    soil = {"soil_n": "280", "soil_p": "40", "soil_k": "40", "soil_ph": "7.2"}  # SHC-style kg/ha N
    plan = rank.plan(farm_context.build(profile(soil=soil)), "kharif", db.session)
    assert "soil nitrogen" in plan.model_note


# ---------------------------------------------------------------- why not


def test_why_not(app, ctx_req):
    plan = rank.plan(farm_context.build(profile()), "rabi", db.session)
    assert "don't show this crop in" in rank.why_not(plan, "paddy", "Bulandshahr")[0]
    assert "already in the top 3" in rank.why_not(plan, plan.top[0].crop, "Bulandshahr")[0]
    fourth = plan.options[3].crop
    assert rank.why_not(plan, fourth, "Bulandshahr")


# ---------------------------------------------------------------- HTTP


@pytest.fixture
def english(client):
    client.set_cookie("lang", "en")


def test_plan_page_and_field_first(client, english):
    assert client.get("/plan").status_code == 200
    html = client.post("/plan/results", data={"season": "rabi", "profile": ""}, headers=HX).get_data(as_text=True)
    assert "First, tell us about your field" in html


def test_plan_results_show_three_cards_with_trust_layer(client, english):
    r = client.post("/plan/results", data={"season": "rabi", "profile": json.dumps(profile())}, headers=HX)
    html = r.get_data(as_text=True)
    assert html.count("<article") == 3
    assert "Source:" in html and "Medium confidence" in html and "Ask an expert" in html
    assert "/fertilizer?crop=" in html and "season=rabi" in html
    assert "wa.me" in html
    saved = json.loads(html.split("data-profile-update>")[1].split("</script>")[0])
    assert saved["last_results"]["planner"]["value"]["top"] == [o for o in saved["last_results"]["planner"]["value"]["top"]]
    assert len(saved["last_results"]["planner"]["value"]["top"]) == 3


def test_fertilizer_link_only_for_crops_with_a_cited_dose(client, english):
    """Found in the Section 11 task rehearsal: mustard topped a rabi plan, and its
    fertilizer link led to a page that can't count bags for mustard."""
    from agrisense.fertilizer import data as fertilizer_data

    html = client.post("/plan/results", data={"season": "rabi", "profile": json.dumps(profile())},
                       headers=HX).get_data(as_text=True)
    top = json.loads(html.split("data-profile-update>")[1].split("</script>")[0])["last_results"]["planner"]["value"]["top"]
    with_dose = set(fertilizer_data.crops_with_dose())
    for crop in top:
        assert (f"/fertilizer?crop={crop}&" in html) == (crop in with_dose), crop
    assert html.count("so we can't count bags for it") == len([c for c in top if c not in with_dose])


def test_district_without_crop_data(client, english):
    p = profile(district="HR-ambala")
    html = client.post("/plan/results", data={"season": "rabi", "profile": json.dumps(p)}, headers=HX).get_data(as_text=True)
    assert "isn't covered yet" in html


def test_why_endpoint(client, english):
    html = htmllib.unescape(client.post("/plan/why", data={"season": "rabi", "crop": "paddy", "profile": json.dumps(profile())},
                       headers=HX).get_data(as_text=True))
    assert "Why not Paddy?" in html and "don't show this crop" in html


@pytest.mark.parametrize("form", [{"season": "monsoon"}, {"season": "rabi", "crop": "coffee-x"}])
def test_bad_input_is_400(client, form):
    url = "/plan/why" if "crop" in form else "/plan/results"
    assert client.post(url, data={**form, "profile": json.dumps(profile())}, headers=HX).status_code == 400


def test_logged_in_results_are_stored_as_events(client, english):
    client.post("/farm/save", data={"phone": "9876543210", "pin": "4826", "pin_confirm": "4826",
                                    "consent": "yes", "profile": json.dumps(profile())})
    client.post("/plan/results", data={"season": "rabi", "profile": ""}, headers=HX)
    event = db.session.scalar(select(Event).where(Event.kind == "planner.result"))
    assert event is not None and len(event.payload["value"]["top"]) == 3


def test_plan_in_hindi(client):
    client.set_cookie("lang", "hi")
    html = client.post("/plan/results", data={"season": "rabi", "profile": json.dumps(profile())}, headers=HX).get_data(as_text=True)
    assert "सरसों" in html and "स्रोत:" in html


# ---------------------------------------------------------------- validation script


def test_validate_planner_script(tmp_path):
    records = tmp_path / "records.csv"
    records.write_text(
        "record_id,district_code,season,irrigation_source,area_acre,soil_n,soil_p,soil_k,soil_ph,soil_oc,chosen_crop,collected_on,collected_by,notes\n"
        "T1,UP-bulandshahr,rabi,tubewell,2,,,,,,wheat,2026-10-08,test,synthetic\n"
        "T2,UP-bulandshahr,rabi,tubewell,2,,,,,,paddy,2026-10-08,test,synthetic\n"
        "T3,UP-nowhere,rabi,tubewell,2,,,,,,wheat,2026-10-08,test,synthetic\n", encoding="utf-8")
    out = subprocess.run([sys.executable, "scripts/validate_planner.py", "--records", str(records)],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    assert "Top-3 hit rate: 1/2" in out and "skipped T3" in out and "Secondary:" in out
