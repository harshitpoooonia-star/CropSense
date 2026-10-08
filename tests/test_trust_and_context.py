from datetime import date
from decimal import Decimal

import pytest
from werkzeug.datastructures import MultiDict

from agrisense import districts, farm_context, kvk
from agrisense import farm_profile as fp
from agrisense.trust import Source, TrustResult, apply_input_rule, cap

BULANDSHAHR = "UP-bulandshahr"


# ---------------------------------------------------------------- trust layer


def test_trust_result_needs_a_source_and_a_known_level():
    with pytest.raises(ValueError):
        TrustResult(value=1, confidence="high", sources=[])
    with pytest.raises(ValueError):
        TrustResult(value=1, confidence="certain", sources=[Source("x")])


def test_trust_result_round_trips_as_json():
    result = TrustResult(value={"bags": 3}, confidence="medium", reasons=["r"],
                         sources=[Source("Agmarknet", date(2026, 10, 6)), Source("your soil card")],
                         estimated_fields=["soil nitrogen"])
    data = result.to_dict()
    assert data["sources"] == [{"name": "Agmarknet", "date": "2026-10-06"}, {"name": "your soil card", "date": None}]
    assert TrustResult.from_dict(data) == result


@pytest.mark.parametrize("base, estimated, unknown, expected", [
    ("high", False, False, "high"), ("high", True, False, "medium"), ("high", True, True, "low"),
    ("medium", False, True, "low"), ("low", True, False, "low"),
])
def test_confidence_rule(base, estimated, unknown, expected):
    assert apply_input_rule(base, any_estimated=estimated, any_unknown=unknown) == expected


def test_cap():
    assert cap("high", "medium") == "medium" and cap("low", "high") == "low"


# ---------------------------------------------------------------- districts


def test_district_table_covers_up_and_haryana_with_sources():
    table = districts.districts()
    assert len([d for d in table.values() if d.state == "UP"]) >= 70
    assert len([d for d in table.values() if d.state == "HR"]) >= 20
    assert all(d.source.startswith("Wikidata Q") and d.name_hi for d in table.values())
    for code in ("UP-gautam-buddh-nagar", BULANDSHAHR, "UP-ghaziabad", "UP-hapur", "UP-aligarh"):
        assert code in table


def test_nearest_and_far_points():
    b = districts.get(BULANDSHAHR)
    assert districts.nearest(b.lat + 0.01, b.lon) == b
    assert districts.nearest(19.07, 72.88) is None  # Mumbai: not UP or Haryana


def test_choices_are_localised():
    assert any(label.startswith("बुलन्दशहर") and "उत्तर प्रदेश" in label for _code, label in districts.choices("hi"))


def test_kvk_rows_are_sourced_and_phone_free_until_verified():
    rows = kvk.contacts()
    assert {"UP-gautam-buddh-nagar", BULANDSHAHR} <= set(rows)
    assert all(r.source for r in rows.values())


# ---------------------------------------------------------------- farm context


def _profile(**soil):
    profile = fp.empty()
    fp.apply_where(profile, MultiDict({"location_source": "gps", "lat": "28.40", "lon": "77.85"}))
    fp.apply_area(profile, MultiDict({"area": "1", "area_unit": "acre"}))
    fp.apply_water(profile, MultiDict({"irrigation_source": "tubewell"}))
    fp.apply_soil(profile, MultiDict({f"soil_{k}": v for k, v in soil.items()}))
    return profile


def test_card_values_are_given_and_the_rest_unknown_without_defaults():
    ctx = farm_context.build(_profile(n="180", ph="7.2"))
    assert ctx.soil["n"] == Decimal("180") and ctx.soil["ph"] == Decimal("7.2")
    assert sorted(ctx.unknown) == ["soil.k", "soil.oc", "soil.p"]
    assert ctx.estimated == []
    assert [s.name for s in ctx.sources] == ["your soil card"]


def test_sourced_district_defaults_fill_gaps_and_are_flagged(monkeypatch):
    monkeypatch.setattr(farm_context, "soil_defaults", lambda: {
        BULANDSHAHR: {"p": Decimal("20"), "k": Decimal("250"), "source": "Test source", "as_of": date(2025, 1, 1)},
    })
    ctx = farm_context.build(_profile(n="180"))
    assert ctx.soil["p"] == Decimal("20") and ctx.is_estimated("soil.p") and ctx.is_estimated("soil.k")
    assert ctx.unknown == ["soil.ph", "soil.oc"]
    assert "soil phosphorus" in ctx.estimated_labels()
    assert any("Test source" in s.name and s.date == date(2025, 1, 1) for s in ctx.sources)


def test_unsourced_default_rows_are_ignored(tmp_path, monkeypatch):
    (tmp_path / "district_soil_defaults.csv").write_text(
        "district_code,n_kg_ha,p_kg_ha,k_kg_ha,ph,oc_pct,source,as_of,notes\n"
        f"{BULANDSHAHR},999,999,999,7,1,,,made up\n", encoding="utf-8")
    monkeypatch.setattr(farm_context, "DATA", tmp_path)
    farm_context.soil_defaults.cache_clear()
    try:
        assert farm_context.soil_defaults() == {}
    finally:
        farm_context.soil_defaults.cache_clear()


def test_shipped_soil_defaults_contain_no_unsourced_numbers():
    farm_context.soil_defaults.cache_clear()
    assert farm_context.soil_defaults() == {}  # target rows are TODO until a source is cited


def test_district_only_location_is_estimated():
    profile = fp.empty()
    fp.apply_where(profile, MultiDict({"location_source": "district", "district_code": BULANDSHAHR}))
    ctx = farm_context.build(profile)
    assert ctx.is_estimated("location")
    assert "field location" in ctx.estimated_labels()
