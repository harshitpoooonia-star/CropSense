"""Advisor thresholds (data/weather_thresholds.csv). Every value carries a
status: 'cited' (with its source) or 'proposed' (a product choice waiting for
team review). Rules read them from here, never from literals in code."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache

from ..units import DATA


@dataclass(frozen=True)
class Threshold:
    key: str
    value: Decimal
    unit: str
    status: str  # cited | proposed
    source: str


@lru_cache(maxsize=1)
def thresholds() -> dict[str, Threshold]:
    with (DATA / "weather_thresholds.csv").open(encoding="utf-8") as f:
        return {r["key"]: Threshold(r["key"], Decimal(r["value"]), r["unit"], r["status"], r["source"])
                for r in csv.DictReader(f)}


def value(key: str) -> float:
    return float(thresholds()[key].value)


def any_proposed(keys) -> bool:
    return any(thresholds()[k].status == "proposed" for k in keys)
