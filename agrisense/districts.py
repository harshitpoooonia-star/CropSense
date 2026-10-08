"""UP and Haryana districts (data/districts.csv, built from Wikidata).

Coordinates are approximate points for each district, so a pin is matched
to the nearest one and the farmer always confirms it (spec 01, R3).
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from functools import lru_cache

from .units import DATA

MAX_SUGGEST_KM = 100  # further than this from every listed point: ask instead of guessing


@dataclass(frozen=True)
class District:
    code: str
    state: str
    name_en: str
    name_hi: str
    lat: float
    lon: float
    source: str
    as_of: str

    def name(self, locale: str) -> str:
        return self.name_hi if locale == "hi" else self.name_en


@lru_cache(maxsize=1)
def districts() -> dict[str, District]:
    with (DATA / "districts.csv").open(encoding="utf-8") as f:
        return {
            row["code"]: District(
                code=row["code"], state=row["state"], name_en=row["name_en"], name_hi=row["name_hi"],
                lat=float(row["lat"]), lon=float(row["lon"]), source=row["source"], as_of=row["as_of"],
            )
            for row in csv.DictReader(f)
        }


def get(code: str | None) -> District | None:
    return districts().get(code or "")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest(lat: float, lon: float, max_km: float = MAX_SUGGEST_KM) -> District | None:
    best = min(districts().values(), key=lambda d: haversine_km(lat, lon, d.lat, d.lon))
    return best if haversine_km(lat, lon, best.lat, best.lon) <= max_km else None


def choices(locale: str) -> list[tuple[str, str]]:
    """(code, "District, State") sorted by name in the user's language."""
    states = {"UP": ("उत्तर प्रदेश", "Uttar Pradesh"), "HR": ("हरियाणा", "Haryana")}
    rows = [
        (d.code, f"{d.name(locale)}, {states[d.state][0 if locale == 'hi' else 1]}")
        for d in districts().values()
    ]
    return sorted(rows, key=lambda r: r[1])
