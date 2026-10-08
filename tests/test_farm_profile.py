import json
from datetime import date, timedelta

import pytest
from werkzeug.datastructures import MultiDict

from agrisense import farm_profile as fp

BULANDSHAHR = "UP-bulandshahr"


def form(**fields):
    return MultiDict(dict(fields))


def test_garbage_becomes_an_empty_profile():
    for raw in (None, "", "not json", "[]", json.dumps({"v": 99}), json.dumps({"v": 1, "farm": "x"})):
        assert fp.parse(raw) == fp.empty()


def test_parse_keeps_valid_parts_and_drops_the_rest():
    raw = {
        "v": 1,
        "farm": {"lat": 28.41, "lon": 77.83, "district_code": BULANDSHAHR, "location_source": "map"},
        "plots": [{
            "area": {"value": "2.5", "unit": "acre"},
            "irrigation_source": "tubewell",
            "soil": {"n": "180", "p": "-4", "k": "abc", "ph": "7.2", "oc": "0.4", "sampled_on": "2099-01-01"},
        }],
        "last_results": {"planner": {"value": 1, "confidence": "high", "sources": [{"name": "x", "date": "2026-10-06"}]},
                         "hack": {"value": 1}, "market": {"confidence": "sure"}},
        "extra": "ignored",
    }
    profile = fp.parse(json.dumps(raw))
    p = fp.plot(profile)
    assert profile["farm"] == {"lat": 28.41, "lon": 77.83, "district_code": BULANDSHAHR, "location_source": "map"}
    assert p["area"] == {"value": "2.5", "unit": "acre"} and p["area_ha"] == "1.0117"
    assert p["irrigation_source"] == "tubewell"
    assert p["soil"] == {"n": "180", "p": None, "k": None, "ph": "7.2", "oc": "0.4", "sampled_on": None}
    assert list(profile["last_results"]) == ["planner"]
    assert "extra" not in profile


def test_parse_rejects_points_outside_india_and_unknown_districts():
    raw = {"v": 1, "farm": {"lat": 51.5, "lon": -0.1, "district_code": "XX-nowhere", "location_source": "teleport"}}
    assert fp.parse(json.dumps(raw))["farm"] == fp.empty()["farm"]


def test_round_trip_through_dumps():
    profile = fp.empty()
    fp.apply_where(profile, form(location_source="district", district_code=BULANDSHAHR))
    fp.apply_area(profile, form(area="3", area_unit="hectare"))
    assert fp.parse(fp.dumps(profile)) == profile


# ---------------------------------------------------------------- steps


def test_where_with_a_pin_suggests_the_nearest_district():
    profile = fp.empty()
    assert fp.apply_where(profile, form(location_source="gps", lat="28.40", lon="77.85")) == []
    assert profile["farm"]["district_code"] == BULANDSHAHR
    assert profile["farm"]["location_source"] == "gps"


def test_where_confirmation_can_change_the_district():
    profile = fp.empty()
    fp.apply_where(profile, form(location_source="map", lat="28.40", lon="77.85", district_code="UP-gautam-buddh-nagar"))
    assert profile["farm"]["district_code"] == "UP-gautam-buddh-nagar"
    assert profile["farm"]["lat"] == 28.4  # the pin is kept, only the district changes


def test_where_far_from_any_listed_district_asks_to_choose():
    profile = fp.empty()
    errors = fp.apply_where(profile, form(location_source="map", lat="12.97", lon="77.59"))  # Bengaluru
    assert [e.code for e in errors] == ["district_needed"]
    assert profile["farm"]["district_code"] is None


@pytest.mark.parametrize("fields", [{}, {"location_source": "map", "lat": "x", "lon": "1"},
                                    {"location_source": "gps", "lat": "40", "lon": "-74"}])
def test_where_rejects_bad_locations(fields):
    assert [e.code for e in fp.apply_where(fp.empty(), form(**fields))] == ["location_invalid"]


def test_where_by_district_uses_its_point_and_marks_the_source():
    profile = fp.empty()
    assert fp.apply_where(profile, form(location_source="district", district_code=BULANDSHAHR)) == []
    assert profile["farm"]["location_source"] == "district"
    assert profile["farm"]["lat"] is not None


def test_where_by_unknown_district_fails():
    assert [e.code for e in fp.apply_where(fp.empty(), form(location_source="district", district_code="nope"))] == ["district_needed"]


@pytest.mark.parametrize("value, unit, area_ha", [("2.5", "acre", "1.0117"), ("1", "hectare", "1"), ("२", "hectare", "2")])
def test_area(value, unit, area_ha):
    profile = fp.empty()
    assert fp.apply_area(profile, form(area=value, area_unit=unit)) == []
    assert fp.plot(profile)["area_ha"] == area_ha


@pytest.mark.parametrize("value, unit, code", [("0", "acre", "area_invalid"), ("-1", "acre", "area_invalid"),
                                               ("x", "acre", "area_invalid"), ("2", "killa", "area_invalid"),
                                               ("2", "bigha", "bigha_unknown")])
def test_area_errors(value, unit, code):
    profile = fp.empty()
    fp.apply_where(profile, form(location_source="district", district_code=BULANDSHAHR))
    assert [e.code for e in fp.apply_area(profile, form(area=value, area_unit=unit))] == [code]


def test_water():
    profile = fp.empty()
    assert fp.apply_water(profile, form(irrigation_source="canal")) == []
    assert fp.plot(profile)["irrigation_source"] == "canal"
    assert [e.code for e in fp.apply_water(profile, form(irrigation_source="river"))] == ["choose_one"]


def test_soil_values_and_skip():
    profile = fp.empty()
    assert fp.apply_soil(profile, form(soil_n="180", soil_ph="7,5", soil_sampled_on="2025-03-01")) == []
    soil = fp.plot(profile)["soil"]
    assert soil["n"] == "180" and soil["ph"] == "7.5" and soil["p"] is None and soil["sampled_on"] == "2025-03-01"
    assert not fp.plot(profile)["soil_skipped"]
    assert fp.apply_soil(profile, form(skip="1")) == []
    assert fp.plot(profile)["soil_skipped"] and fp.plot(profile)["soil"]["n"] is None


def test_soil_all_blank_counts_as_skipped():
    profile = fp.empty()
    fp.apply_soil(profile, form(soil_n=""))
    assert fp.plot(profile)["soil_skipped"]


@pytest.mark.parametrize("field, value", [("soil_ph", "15"), ("soil_oc", "101"), ("soil_n", "-5"), ("soil_k", "abc")])
def test_soil_rejects_impossible_values(field, value):
    errors = fp.apply_soil(fp.empty(), form(**{field: value}))
    assert [(e.field, e.code) for e in errors] == [(field, "number_invalid")]


def test_soil_date_cannot_be_in_the_future():
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert [e.code for e in fp.apply_soil(fp.empty(), form(soil_sampled_on=tomorrow))] == ["date_invalid"]


def test_next_step_and_completeness():
    profile = fp.empty()
    assert fp.next_step(profile) == "where" and not fp.is_complete(profile)
    fp.apply_where(profile, form(location_source="district", district_code=BULANDSHAHR))
    assert fp.next_step(profile) == "area"
    fp.apply_area(profile, form(area="1", area_unit="acre"))
    fp.apply_water(profile, form(irrigation_source="tubewell"))
    assert fp.next_step(profile) == "soil" and fp.is_complete(profile)
    fp.apply_soil(profile, form(skip="1"))
    assert fp.next_step(profile) is None
