"""Fertilizer tables in data/ (spec 03, R1). Rows without a source are ignored."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache

from ..units import DATA
from .calc import Dose, Product


def _dec(value: str) -> Decimal | None:
    return Decimal(value) if value and value.strip() else None


@dataclass(frozen=True)
class DoseRow:
    crop: str
    condition: str
    low: Dose
    high: Dose
    split: str
    source: str
    verified: bool
    complete: bool  # all of N, P2O5, K2O cited

    @property
    def is_range(self) -> bool:
        return self.low != self.high


@dataclass(frozen=True)
class PriceInfo:
    product: str
    as_of: str
    source: str
    composition_source: str
    verified: bool


@lru_cache(maxsize=1)
def doses() -> dict[tuple[str, str], DoseRow]:
    table = {}
    with (DATA / "fert_rdf.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r["source"].strip():
                continue
            values = {k: _dec(r[k]) for k in ("n_low", "n_high", "p2o5_low", "p2o5_high", "k2o_low", "k2o_high")}
            zero = Decimal(0)
            table[(r["crop"], r["condition"])] = DoseRow(
                crop=r["crop"], condition=r["condition"],
                low=Dose(values["n_low"] or zero, values["p2o5_low"] or zero, values["k2o_low"] or zero),
                high=Dose(values["n_high"] or zero, values["p2o5_high"] or zero, values["k2o_high"] or zero),
                split=r["split"].strip(), source=r["source"].strip(),
                verified=r["verified"].strip().lower() == "true",
                complete=all(v is not None for v in values.values()),
            )
    return table


@lru_cache(maxsize=1)
def products() -> tuple[dict[str, Product], dict[str, PriceInfo]]:
    items, prices = {}, {}
    with (DATA / "fert_products.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            items[r["product"]] = Product(
                code=r["product"], n_pct=Decimal(r["n_pct"]), p2o5_pct=Decimal(r["p2o5_pct"]),
                k2o_pct=Decimal(r["k2o_pct"]), bag_kg=Decimal(r["bag_kg"]), price_per_bag=Decimal(r["price_inr_bag"]))
            prices[r["product"]] = PriceInfo(r["product"], r["price_as_of"], r["price_source"],
                                             r["composition_source"], r["verified"].strip().lower() == "true")
    return items, prices


def conditions(crop: str) -> list[str]:
    return [cond for (c, cond) in doses() if c == crop]


def crops_with_dose() -> list[str]:
    return sorted({c for (c, _cond) in doses()})
