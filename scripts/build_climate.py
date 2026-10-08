#!/usr/bin/env python3
"""Build data/district_climate.csv: season climate normals per district.

Source: Open-Meteo Historical Weather API (ERA5-based reanalysis, CC BY 4.0),
daily mean temperature, mean relative humidity and precipitation for each
district's point in data/districts.csv, over YEARS full years.

These feed the legacy suitability model, which was trained on a public
dataset whose climate columns are undocumented. Two modelling assumptions,
kept here so they're visible and easy to change:
  - season months (SEASON_MONTHS below) are the usual Indian crop seasons;
  - "rainfall" is mean monthly rainfall over the season's months (mm/month),
    the reading of the dataset's 20-300 mm column that fits its range.

    python scripts/build_climate.py               # target districts
    python scripts/build_climate.py --all         # every district in districts.csv
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "district_climate.csv"
API = "https://archive-api.open-meteo.com/v1/archive"
YEARS = range(2015, 2025)
TARGETS = ("UP-gautam-buddh-nagar", "UP-bulandshahr", "UP-ghaziabad", "UP-hapur", "UP-aligarh")
SEASON_MONTHS = {
    "kharif": (6, 7, 8, 9, 10),
    "rabi": (11, 12, 1, 2, 3),
    "zaid": (3, 4, 5, 6),
}


def fetch(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": f"{YEARS[0]}-01-01", "end_date": f"{YEARS[-1]}-12-31",
        "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum",
        "timezone": "Asia/Kolkata",
    }
    request = urllib.request.Request(f"{API}?{urllib.parse.urlencode(params)}",
                                     headers={"User-Agent": "AgriSense-student-project/0.1 (climate normals)"})
    return json.load(urllib.request.urlopen(request, timeout=120))["daily"]


def normals(daily: dict) -> dict[str, dict]:
    by_month: dict = defaultdict(lambda: {"t": [], "rh": [], "rain": 0.0})
    for day, t, rh, rain in zip(daily["time"], daily["temperature_2m_mean"],
                                daily["relative_humidity_2m_mean"], daily["precipitation_sum"]):
        key = day[:7]  # YYYY-MM
        if t is not None:
            by_month[key]["t"].append(t)
        if rh is not None:
            by_month[key]["rh"].append(rh)
        by_month[key]["rain"] += rain or 0.0
    out = {}
    for season, months in SEASON_MONTHS.items():
        picked = [v for k, v in by_month.items() if int(k[5:7]) in months]
        out[season] = {
            "temperature_c": round(statistics.fmean(x for m in picked for x in m["t"]), 1),
            "humidity_pct": round(statistics.fmean(x for m in picked for x in m["rh"]), 1),
            "rainfall_mm_per_month": round(statistics.fmean(m["rain"] for m in picked), 1),
        }
    return out


def main() -> int:
    with (ROOT / "data" / "districts.csv").open(encoding="utf-8") as f:
        districts = {row["code"]: row for row in csv.DictReader(f)}
    codes = list(districts) if "--all" in sys.argv else list(TARGETS)
    rows = []
    for code in codes:
        d = districts[code]
        for season, values in normals(fetch(float(d["lat"]), float(d["lon"]))).items():
            rows.append({"district_code": code, "season": season, **values,
                         "years": f"{YEARS[0]}-{YEARS[-1]}",
                         "source": "Open-Meteo Historical Weather API (ERA5), CC BY 4.0",
                         "as_of": date.today().isoformat()})
        time.sleep(1)  # be gentle with the free API
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
