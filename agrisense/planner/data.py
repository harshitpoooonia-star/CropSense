"""Planner tables in data/ (built by scripts/build_crop_data.py, build_climate.py).

Every row carries its source. Loaders turn blanks into None; nothing is filled in.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import lru_cache

from ..units import DATA

SEASONS = ("kharif", "rabi", "zaid")


def _dec(value: str) -> Decimal | None:
    return Decimal(value) if value and value.strip() else None


def _rows(name: str) -> list[dict]:
    with (DATA / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@dataclass(frozen=True)
class SeasonCrop:
    district_code: str
    crop: str
    season: str
    mean_area_ha: int
    years: str
    source: str


@dataclass(frozen=True)
class Economics:
    district_code: str
    crop: str
    season: str
    yield_low: Decimal  # quintal per acre
    yield_median: Decimal
    yield_high: Decimal
    yield_years: str
    yield_source: str
    cost: Decimal | None  # Rs per acre, A2+FL (paid-out costs + family labour)
    cost_year: str
    cost_source: str
    water_need: str | None  # low | medium | high
    water_source: str
    verified: bool

    @property
    def cost_start_year(self) -> int | None:
        return int(self.cost_year[:4]) if self.cost_year else None


@dataclass(frozen=True)
class Msp:
    crop: str
    marketing_season: str
    price: Decimal  # Rs per quintal
    announced: date
    source: str
    verified: bool


@dataclass(frozen=True)
class Climate:
    district_code: str
    season: str
    temperature_c: float
    humidity_pct: float
    rainfall_mm_per_month: float
    years: str
    source: str


@lru_cache(maxsize=1)
def season_crops() -> list[SeasonCrop]:
    return [SeasonCrop(r["district_code"], r["crop"], r["season"], int(r["mean_area_ha"]), r["years"], r["source"])
            for r in _rows("crop_seasons.csv")]


@lru_cache(maxsize=1)
def economics_table() -> dict[tuple[str, str, str], Economics]:
    table = {}
    for r in _rows("district_crop_economics.csv"):
        table[(r["district_code"], r["crop"], r["season"])] = Economics(
            district_code=r["district_code"], crop=r["crop"], season=r["season"],
            yield_low=Decimal(r["yield_qtl_acre_low"]), yield_median=Decimal(r["yield_qtl_acre_median"]),
            yield_high=Decimal(r["yield_qtl_acre_high"]), yield_years=r["yield_years"],
            yield_source=r["yield_source"], cost=_dec(r["cost_a2fl_inr_acre"]), cost_year=r["cost_year"],
            cost_source=r["cost_source"], water_need=r["water_need"] or None, water_source=r["water_source"],
            verified=r["verified"].strip().lower() == "true",
        )
    return table


@lru_cache(maxsize=1)
def msp_table() -> dict[str, Msp]:
    """Latest announced MSP per crop."""
    latest: dict[str, Msp] = {}
    for r in _rows("msp.csv"):
        row = Msp(r["crop"], r["marketing_season"], Decimal(r["msp_inr_qtl"]), date.fromisoformat(r["announced"]),
                  r["source"], r["verified"].strip().lower() == "true")
        if row.crop not in latest or row.announced > latest[row.crop].announced:
            latest[row.crop] = row
    return latest


@lru_cache(maxsize=1)
def climate_table() -> dict[tuple[str, str], Climate]:
    return {(r["district_code"], r["season"]): Climate(
        r["district_code"], r["season"], float(r["temperature_c"]), float(r["humidity_pct"]),
        float(r["rainfall_mm_per_month"]), r["years"], r["source"]) for r in _rows("district_climate.csv")}


def candidates(district_code: str, season: str) -> list[SeasonCrop]:
    """Crops the district's own statistics show in this season, biggest area first."""
    rows = [c for c in season_crops() if c.district_code == district_code and c.season == season]
    return sorted(rows, key=lambda c: -c.mean_area_ha)


def economics(district_code: str, crop: str, season: str) -> Economics | None:
    return economics_table().get((district_code, crop, season))


def has_district(district_code: str | None) -> bool:
    return any(c.district_code == district_code for c in season_crops())
