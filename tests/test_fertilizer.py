"""Fertilizer Calculator (spec 03). Card amounts and areas here are test data."""

import csv
import json
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from werkzeug.datastructures import MultiDict

from agrisense import farm_profile as fp
from agrisense.extensions import db
from agrisense.fertilizer import calc, data, service
from agrisense.models import Event
from agrisense.units import to_hectares

CASES = Path(__file__).resolve().parent.parent / "data" / "fert_cases.csv"
HX = {"HX-Request": "true"}


def _cases():
    with CASES.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _bags_for(case) -> dict[str, Decimal]:
    products, _prices = data.products()
    area = to_hectares(case["area_value"], case["area_unit"])
    if case["mode"] == "card":
        per = {k: Decimal(case[f"card_{k}"]) for k in ("urea", "dap", "mop", "ssp") if case[f"card_{k}"]}
        kg = calc.card_kg(per, case["card_unit"], area)
    else:
        row = data.doses()[(case["crop"], case["condition"])]
        dose = row.high if case["dose_end"] == "high" else row.low
        kg = calc.product_kg(dose, area, products, case["phosphate"])
    return {code: amount / products[code].bag_kg for code, amount in kg.items()}


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["case_id"])
def test_worked_cases(case):
    bags = _bags_for(case)
    for product in ("urea", "dap", "ssp", "mop"):
        expected = case[f"expected_{product}_bags"]
        if not expected:
            assert product not in bags
            continue
        got = bags[product]
        assert abs(got - Decimal(expected)) <= 1, f"{product}: spec P0-3 says within 1 bag"
        assert abs(got - Decimal(expected)) <= Decimal("0.02"), f"{product}: arithmetic drifted"


def test_there_are_ten_sourced_cases():
    cases = _cases()
    assert len(cases) == 10 and all(c["dose_source"] for c in cases)


# ---------------------------------------------------------------- calc rules


def products():
    return data.products()[0]


def test_dap_nitrogen_is_subtracted_from_urea():
    kg = calc.product_kg(calc.Dose(Decimal(100), Decimal(46), Decimal(0)), Decimal(1), products())
    assert kg["dap"] == Decimal(100)  # 46 kg P2O5 / 0.46
    assert kg["urea"] == (Decimal(100) - Decimal(18)) / Decimal("0.46")
    assert "mop" not in kg


def test_ssp_leaves_all_nitrogen_to_urea():
    kg = calc.product_kg(calc.Dose(Decimal(46), Decimal(16), Decimal(0)), Decimal(1), products(), "ssp")
    assert kg == {"ssp": Decimal(100), "urea": Decimal(100)}


def test_dap_can_cover_all_nitrogen():
    kg = calc.product_kg(calc.Dose(Decimal(10), Decimal(46), Decimal(0)), Decimal(1), products())
    assert "urea" not in kg  # DAP's 18 kg N already exceeds the 10 kg needed


def test_bags_to_buy_and_cost_use_whole_bags():
    plan = calc.to_plan({"urea": Decimal(91)}, products())
    line = plan.line("urea")
    assert line.bags == Decimal("2.0") and line.bags_to_buy == 3  # 91 kg = 2.02 bags of 45 kg
    assert line.cost == products()["urea"].price_per_bag * 3 == plan.total_cost


def test_card_dose_per_acre_scales_by_area():
    kg = calc.card_kg({"urea": Decimal(100), "dap": Decimal(0)}, "acre", calc.HECTARES_PER_ACRE * 2)
    assert kg == {"urea": Decimal(200)}


def test_split_follows_the_cited_schedule():
    row = data.doses()[("potato", "default")]
    schedule = calc.parse_split(row.split)
    stages = calc.split_by_stage(row.low, Decimal(1), products(), "dap", schedule)
    total = calc.product_kg(row.low, Decimal(1), products())
    assert set(stages) == {"basal", "earthing_up"}
    assert "dap" in stages["basal"] and "dap" not in stages["earthing_up"]
    assert abs(sum(s.get("urea", 0) for s in stages.values()) - total["urea"]) <= 2  # rounding per stage


# ---------------------------------------------------------------- data


def test_dose_rows_are_sourced_and_unverified():
    for row in data.doses().values():
        assert row.source and row.verified is False


def test_soil_adjustment_is_off():
    with (CASES.parent / "soil_rating_adjust.csv").open(encoding="utf-8") as f:
        assert all(r["active"] == "false" for r in csv.DictReader(f))


def test_products_are_types_not_brands():
    assert set(products()) == {"urea", "dap", "mop", "ssp"}
    _items, prices = data.products()
    assert all(p.source and p.as_of for p in prices.values())


# ---------------------------------------------------------------- service


def profile(area="2.5", unit="acre"):
    p = fp.empty()
    fp.apply_where(p, MultiDict({"location_source": "district", "district_code": "UP-bulandshahr"}))
    fp.apply_area(p, MultiDict({"area": area, "area_unit": unit}))
    fp.apply_water(p, MultiDict({"irrigation_source": "tubewell"}))
    return p


@pytest.fixture
def en(app):
    with app.test_request_context("/", headers={"Accept-Language": "en"}):
        yield


def calc_form(**fields):
    return service.calculate(MultiDict(fields), profile(), "en")


def test_standard_dose_uses_the_saved_area(en):
    out = calc_form(mode="standard", crop="wheat", condition="irrigated")
    assert out.area_ha == Decimal("1.0117")
    assert [l.product for l in out.plans[0][1].lines] == ["urea", "dap", "mop"]
    assert out.trust.confidence == "medium"  # dose and prices unverified
    assert any("Not adjusted for your soil test" in r for r in out.trust.reasons)
    assert "UP Agriculture Department" in out.trust.sources[0].name


def test_range_dose_gives_two_plans(en):
    out = calc_form(mode="standard", crop="potato")
    assert [label for label, _plan in out.plans] == ["low", "high"]
    assert out.plans[0][1].stages and out.plans[1][1].stages


def test_partial_dose_is_low_confidence(en):
    out = calc_form(mode="standard", crop="sugarcane")
    assert [l.product for l in out.plans[0][1].lines] == ["urea"]
    assert out.trust.confidence == "low"


def test_crop_without_a_cited_dose_says_so(en):
    out = calc_form(mode="standard", crop="mustard")
    assert out.no_dose and out.trust is None


def test_card_mode(en):
    out = calc_form(mode="card", card_urea="260", card_dap="130", card_mop="67", card_unit="hectare")
    assert {l.product for l in out.plans[0][1].lines} == {"urea", "dap", "mop"}
    assert out.trust.sources[0].name == "your Soil Health Card"
    assert out.trust.confidence == "medium"  # bags are the card's; prices are unverified


@pytest.mark.parametrize("fields, key", [
    ({"mode": "card"}, "card"),
    ({"mode": "card", "card_urea": "abc"}, "card"),
    ({"mode": "standard"}, "crop"),
    ({"mode": "standard", "crop": "wheat", "area": "x", "area_unit": "acre"}, "area"),
    ({"mode": "standard", "crop": "wheat", "area": "2", "area_unit": "bigha"}, "area"),
])
def test_errors(en, fields, key):
    assert key in calc_form(**fields).errors


def test_area_needed_without_profile(app, en):
    out = service.calculate(MultiDict({"mode": "standard", "crop": "wheat"}), fp.empty(), "en")
    assert "area" in out.errors


# ---------------------------------------------------------------- HTTP


def test_page_prefills_crop_from_the_planner_link(client):
    client.set_cookie("lang", "en")
    html = client.get("/fertilizer?crop=wheat&season=rabi").get_data(as_text=True)
    assert '<option value="wheat" selected>' in html
    html = client.get("/fertilizer?crop=mustard").get_data(as_text=True)
    assert "no cited dose for Mustard yet, so we can't count bags" in html


def test_result_partial(client):
    client.set_cookie("lang", "en")
    r = client.post("/fertilizer/result", headers=HX, data={
        "mode": "standard", "crop": "wheat", "condition": "irrigated", "phosphate": "dap",
        "profile": json.dumps(profile())})
    html = r.get_data(as_text=True)
    assert "<html" not in html and html.count('role="img"') == 3
    assert "Total: ₹" in html and "wa.me" in html and "Medium confidence" in html
    saved = json.loads(html.split("data-profile-update>")[1].split("</script>")[0])
    assert saved["last_results"]["fertilizer"]["value"]["crop"] == "wheat"


def test_result_in_hindi(client):
    client.set_cookie("lang", "hi")
    html = client.post("/fertilizer/result", headers=HX, data={
        "mode": "standard", "crop": "potato", "profile": json.dumps(profile())}).get_data(as_text=True)
    assert "यूरिया" in html and "मिट्टी चढ़ाते समय" in html


def test_logged_in_result_is_an_event(client):
    client.post("/farm/save", data={"phone": "9876543210", "pin": "4826", "pin_confirm": "4826",
                                    "consent": "yes", "profile": json.dumps(profile())})
    client.post("/fertilizer/result", headers=HX, data={"mode": "standard", "crop": "wheat", "profile": ""})
    assert db.session.scalar(select(Event).where(Event.kind == "fertilizer.result")) is not None
