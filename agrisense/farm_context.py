"""What every tool reads about the field (spec 01, R4).

Turns a profile into concrete inputs plus their provenance: which values the
farmer gave, which came from a sourced district default (estimated), and
which aren't known at all. Tools pass `estimated` / `unknown` into the trust
layer's confidence rule and show `estimated_labels()` on the result card.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from functools import lru_cache

from flask_babel import lazy_gettext as _l

from . import districts
from .farm_profile import SOIL_KEYS, plot
from .trust import Source
from .units import DATA

FIELD_LABELS = {
    "location": _l("field location"),
    "soil.n": _l("soil nitrogen"),
    "soil.p": _l("soil phosphorus"),
    "soil.k": _l("soil potassium"),
    "soil.ph": _l("soil pH"),
    "soil.oc": _l("organic carbon"),
}
_DEFAULT_COLUMNS = {"n": "n_kg_ha", "p": "p_kg_ha", "k": "k_kg_ha", "ph": "ph", "oc": "oc_pct"}


@lru_cache(maxsize=1)
def soil_defaults() -> dict[str, dict]:
    """district_code -> {key: Decimal, ...,"source": str, "as_of": date}. Rows
    without a source are ignored, whatever numbers they hold (CLAUDE.md)."""
    table = {}
    with (DATA / "district_soil_defaults.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row["source"].strip():
                continue
            values = {k: Decimal(row[col]) for k, col in _DEFAULT_COLUMNS.items() if row[col].strip()}
            table[row["district_code"]] = {
                **values,
                "source": row["source"].strip(),
                "as_of": date.fromisoformat(row["as_of"]) if row["as_of"].strip() else None,
            }
    return table


@dataclass
class FarmContext:
    district: districts.District | None
    lat: float | None
    lon: float | None
    area_ha: Decimal | None
    irrigation_source: str | None
    soil: dict[str, Decimal | None]
    estimated: list[str] = field(default_factory=list)  # keys of FIELD_LABELS
    unknown: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)

    def is_estimated(self, key: str) -> bool:
        return key in self.estimated

    def estimated_labels(self) -> list[str]:
        return [str(FIELD_LABELS[k]) for k in self.estimated]

    def unknown_labels(self) -> list[str]:
        return [str(FIELD_LABELS[k]) for k in self.unknown]


def build(profile: dict) -> FarmContext:
    farm, p = profile["farm"], plot(profile)
    district = districts.get(farm["district_code"])
    ctx = FarmContext(
        district=district,
        lat=farm["lat"],
        lon=farm["lon"],
        area_ha=Decimal(p["area_ha"]) if p["area_ha"] else None,
        irrigation_source=p["irrigation_source"],
        soil={},
    )
    if farm["location_source"] == "district":
        ctx.estimated.append("location")
        if district:
            ctx.sources.append(Source(str(_l("district centre, %(source)s", source=district.source))))

    card_used = False
    default = soil_defaults().get(farm["district_code"] or "")
    default_used = False
    for key in SOIL_KEYS:
        given = p["soil"][key]
        if given is not None:
            ctx.soil[key] = Decimal(given)
            card_used = True
        elif default and key in default:
            ctx.soil[key] = default[key]
            ctx.estimated.append(f"soil.{key}")
            default_used = True
        else:
            ctx.soil[key] = None
            ctx.unknown.append(f"soil.{key}")

    if card_used:
        sampled = p["soil"]["sampled_on"]
        ctx.sources.append(Source(str(_l("your soil card")), date.fromisoformat(sampled) if sampled else None))
    if default_used:
        ctx.sources.append(Source(str(_l("district average, %(source)s", source=default["source"])), default["as_of"]))
    return ctx
