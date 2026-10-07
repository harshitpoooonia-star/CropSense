"""Local units: acre / bigha / hectare and kg / quintal (spec P0-7).

Acre and quintal are fixed by definition. A bigha is not: its size differs
by district, so it comes only from data/area_units.csv, which carries a
source per row. With no verified row the app says so and asks for acre or
hectare instead of guessing (ADR-003, CLAUDE.md).
"""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

from flask_babel import lazy_gettext as _l

DATA = Path(__file__).resolve().parent.parent / "data"

HECTARES_PER_ACRE = Decimal("0.40468564224")  # international acre, exact
KG_PER_QUINTAL = Decimal(100)

AREA_UNITS = [("acre", _l("acre")), ("bigha", _l("bigha")), ("hectare", _l("hectare"))]
WEIGHT_UNITS = [("kg", _l("kg")), ("quintal", _l("quintal"))]


class UnitUnavailable(ValueError):
    """The unit has no verified size here (e.g. bigha in an unlisted district)."""


@lru_cache(maxsize=1)
def _bigha_table() -> dict[str, Decimal]:
    table: dict[str, Decimal] = {}
    with (DATA / "area_units.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["unit"] != "bigha" or not row["hectares_per_unit"].strip():
                continue
            if not row["source"].strip():
                raise ValueError(f"area_units.csv: {row['district_code']} bigha has no source")
            table[row["district_code"]] = Decimal(row["hectares_per_unit"])
    return table


def hectares_per(unit: str, district_code: str | None = None) -> Decimal:
    if unit == "hectare":
        return Decimal(1)
    if unit == "acre":
        return HECTARES_PER_ACRE
    if unit == "bigha":
        size = _bigha_table().get(district_code or "")
        if size is None:
            raise UnitUnavailable("bigha")
        return size
    raise ValueError(f"unknown area unit {unit!r}")


def to_hectares(value: Decimal | str | float, unit: str, district_code: str | None = None) -> Decimal:
    return parse_decimal(value) * hectares_per(unit, district_code)


def from_hectares(hectares: Decimal, unit: str, district_code: str | None = None) -> Decimal:
    return Decimal(hectares) / hectares_per(unit, district_code)


def kg_to_quintal(kg: Decimal | str | float) -> Decimal:
    return parse_decimal(kg) / KG_PER_QUINTAL


def quintal_to_kg(quintal: Decimal | str | float) -> Decimal:
    return parse_decimal(quintal) * KG_PER_QUINTAL


def parse_decimal(value: Decimal | str | float) -> Decimal:
    """Accepts '2.5', '2,5' and Devanagari digits ('२.५'), which phones type."""
    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace(",", ".")
    text = text.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"not a number: {value!r}") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"not a usable amount: {value!r}")
    return number
