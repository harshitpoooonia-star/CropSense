from decimal import Decimal

import pytest

from agrisense import units
from agrisense.crops import crop_name, crops


def test_acre_and_hectare_round_trip():
    assert units.to_hectares("1", "acre") == Decimal("0.40468564224")
    assert units.from_hectares(units.to_hectares("2.5", "acre"), "acre") == Decimal("2.5")
    assert units.to_hectares("3", "hectare") == Decimal(3)


def test_quintal():
    assert units.kg_to_quintal("250") == Decimal("2.5")
    assert units.quintal_to_kg("1.2") == Decimal("120.0")


def test_bigha_needs_a_verified_district_size():
    # data/area_units.csv has no verified bigha size yet: refuse, don't guess.
    with pytest.raises(units.UnitUnavailable):
        units.to_hectares("5", "bigha", "UP-GBN")
    with pytest.raises(units.UnitUnavailable):
        units.to_hectares("5", "bigha", None)


def test_bigha_row_without_source_is_rejected(tmp_path, monkeypatch):
    (tmp_path / "area_units.csv").write_text(
        "district_code,unit,hectares_per_unit,source,as_of,notes\nUP-X,bigha,0.1,,,\n", encoding="utf-8"
    )
    monkeypatch.setattr(units, "DATA", tmp_path)
    units._bigha_table.cache_clear()
    try:
        with pytest.raises(ValueError, match="no source"):
            units.to_hectares("1", "bigha", "UP-X")
    finally:
        units._bigha_table.cache_clear()


@pytest.mark.parametrize("text, expected", [("2.5", "2.5"), ("2,5", "2.5"), ("२.५", "2.5"), (" 10 ", "10")])
def test_parse_decimal_accepts_phone_input(text, expected):
    assert units.parse_decimal(text) == Decimal(expected)


@pytest.mark.parametrize("text", ["", "abc", "-1", "NaN", "Infinity"])
def test_parse_decimal_rejects_junk(text):
    with pytest.raises(ValueError):
        units.parse_decimal(text)


def test_unknown_unit():
    with pytest.raises(ValueError):
        units.to_hectares("1", "killa")


def test_crop_names_in_both_languages():
    assert crop_name("wheat", "hi") == "गेहूँ"
    assert crop_name("wheat", "en") == "Wheat"
    assert crop_name("unknown-crop", "hi") == "unknown-crop"
    assert all(row["name_hi"] and row["name_en"] for row in crops().values())


def test_main_western_up_crops_are_listed():
    assert {"wheat", "paddy", "mustard", "potato", "sugarcane"} <= set(crops())
