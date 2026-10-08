"""Mandis near a farm (data/mandis.csv, built by scripts/build_mandis.py).

Coordinates are each mandi town's point, so distances are straight-line and
approximate; the screen says so.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache

from ..districts import haversine_km
from ..units import DATA


@dataclass(frozen=True)
class Mandi:
    market: str
    aliases: tuple[str, ...]
    district_code: str
    lat: float | None
    lon: float | None
    coord_source: str
    verified: bool

    def names(self) -> set[str]:
        return {_norm(n) for n in (self.market, *self.aliases) if n}


def _norm(name: str) -> str:
    return " ".join(str(name).lower().replace("(", " ").replace(")", " ").split())


@lru_cache(maxsize=1)
def mandis() -> list[Mandi]:
    with (DATA / "mandis.csv").open(encoding="utf-8") as f:
        return [Mandi(
            market=r["market"], aliases=tuple(a.strip() for a in r["aliases"].split(";") if a.strip()),
            district_code=r["district_code"],
            lat=float(r["lat"]) if r["lat"] else None, lon=float(r["lon"]) if r["lon"] else None,
            coord_source=r["coord_source"], verified=r["verified"].strip().lower() == "true",
        ) for r in csv.DictReader(f)]


def match(market_name: str) -> Mandi | None:
    """The mandi an Agmarknet market name refers to ('Khurja', 'Bulandshahar (F&V)'...)."""
    name = _norm(market_name)
    for mandi in mandis():
        if any(name == n or name.startswith(n + " ") for n in mandi.names()):
            return mandi
    return None


def nearest(lat: float, lon: float, n: int = 5) -> list[tuple[Mandi, float]]:
    located = [(m, haversine_km(lat, lon, m.lat, m.lon)) for m in mandis() if m.lat is not None]
    return sorted(located, key=lambda pair: pair[1])[:n]
