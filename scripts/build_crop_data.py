#!/usr/bin/env python3
"""Build the Crop Planner's economics and season tables from public data.

Writes:
  data/district_crop_economics.csv  yield range (qtl/acre), cost (Rs/acre),
                                    water need, each with source and year
  data/crop_seasons.csv             which crops each district grows in which season

Sources (all Open Data Commons Attribution, via the India Data Portal):
  - District yields: DES "Area, Production, Yield" (APY) district series, and
    the newer UPAG extract of the same series (to 2024-25).
  - Cost of cultivation: DES Cost of Cultivation Scheme, Uttar Pradesh,
    A2+FL (paid-out costs + family labour) and C2, Rs/hectare.
  - Water need: FAO Irrigation Water Management Training Manual No. 3,
    Table 14 (crop water need, mm per season) and section 4.4 (extra water
    for flooded paddy); mustard from a lysimeter study in MAUSAM.

Every row is written with verified=false. A team member flips it after
checking the figure against the source. Nothing is estimated here: a crop
without a figure gets a blank.

    python scripts/build_crop_data.py            # uses data/raw/ extracts
    python scripts/build_crop_data.py --download # refresh the extracts first
"""

from __future__ import annotations

import csv
import io
import statistics
import sys
import urllib.request
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "AgriSense-student-project/0.1 (crop data build)"}

PORTAL = "https://ckandev.indiadataportal.com/dataset"
APY_URL = f"{PORTAL}/f2bbc28c-6c7c-462b-9064-ea4c4213d466/resource/f980409d-49a2-42ae-9eb0-182365005c04/download/crop-wise-area-production-yield.csv"
UPAG_URL = f"{PORTAL}/f2bbc28c-6c7c-462b-9064-ea4c4213d466/resource/6f70d961-3a4f-4caa-b08f-f72f708791e1/download/cropwise-area-production-yield-upag.csv"
COC_URL = f"{PORTAL}/41388795-3e3d-4c7e-82dc-d36335ad18b9/resource/be22e37e-acfc-43a9-859c-d4a066489a69/download/cost-of-cultivation.csv"

DISTRICTS = {  # name in the DES series -> our district code
    "bulandshahr": "UP-bulandshahr",
    "gautam buddha nagar": "UP-gautam-buddh-nagar",
    "ghaziabad": "UP-ghaziabad",
    "hapur": "UP-hapur",
    "aligarh": "UP-aligarh",
}
# our crop code -> (names in the APY/UPAG series, name in the cost series)
CROPS = {
    "wheat": (("Wheat",), "Wheat"),
    "paddy": (("Rice",), "Paddy"),
    "mustard": (("Rapeseed &Mustard", "Rapeseed & Mustard"), "Rapeseed & Mustard (Toria/Taramira)"),
    "potato": (("Potato",), "Potato"),
    "sugarcane": (("Sugarcane",), "Sugarcane"),
    "maize": (("Maize",), "Maize"),
    "barley": (("Barley",), "Barley"),
    "bajra": (("Bajra",), "Bajra"),
    "chickpea": (("Gram",), "Gram"),
    "blackgram": (("Urad",), "Urad"),
    "mungbean": (("Moong(Green Gram)", "Moong"), "Moong"),
    "pigeonpeas": (("Arhar/Tur",), "Tur (Arhar)"),
    "lentil": (("Masoor", "Masur"), "Masur"),
}
SEASONS = {"kharif": "kharif", "rabi": "rabi", "summer": "zaid"}

FAO = "FAO Irrigation Water Management Training Manual No. 3, Table 14"
FAO_RICE = FAO + "; section 4.4 (paddy also needs ~200 mm to saturate soil, ~100 mm water layer, 4-8 mm/day percolation)"
MAUSAM = "MAUSAM (IMD) lysimeter study, consumptive use of mustard at 100% PET, CAZRI Jodhpur 1986-88"
WATER = {  # crop -> (low mm, high mm, need, source)
    "wheat": (450, 650, "medium", FAO),
    "barley": (450, 650, "medium", FAO),
    "maize": (500, 800, "medium", FAO),
    "potato": (500, 700, "medium", FAO),
    "sugarcane": (1500, 2500, "high", FAO),
    # Crop water use alone is 450-700 mm; flooding adds the section 4.4 needs.
    "paddy": (450, 700, "high", FAO_RICE),
    "mustard": (327, 364, "low", MAUSAM),
}
YEARS = 5  # yield range over the latest 5 seasons with data
MIN_AREA_HA = 100  # a district "grows" a crop in a season if it averages this much area
LATEST_FROM = "2018"  # ...and the series still runs: ignore crop-seasons last seen decades ago
QTL_PER_TONNE = Decimal(10)
HA_PER_ACRE = Decimal("0.40468564224")


def fetch_filtered(url: str, keep) -> list[dict]:
    reader = csv.DictReader(io.TextIOWrapper(
        urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600), encoding="utf-8", errors="replace"))
    return [row for row in reader if keep(row)]


def is_target(row: dict) -> bool:
    return row["state_name"].strip().lower() == "uttar pradesh" and row["district_name"].strip().lower() in DISTRICTS


def download() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url, keep in [
        ("apy_target_districts.csv", APY_URL, is_target),
        ("upag_target_districts.csv", UPAG_URL, is_target),
        ("cost_of_cultivation_up.csv", COC_URL, lambda r: "uttar" in r["state_name"].lower()),
    ]:
        rows = fetch_filtered(url, keep)
        with (RAW / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"{name}: {len(rows)} rows")


def read(name: str) -> list[dict]:
    with (RAW / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def per_acre(value: Decimal) -> Decimal:
    return value * HA_PER_ACRE


def q(value: Decimal, places: str = "0.1") -> str:
    return str(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


def yields() -> dict:
    """(district, crop, season) -> {year: (yield qtl/ha, area ha, source)}; UPAG wins over APY."""
    out: dict = defaultdict(dict)
    for row in read("apy_target_districts.csv"):
        if not is_target(row) or row["yield_unit"] != "Tonnes/Hectare":
            continue
        _add(out, row, Decimal(row["yield"]) * QTL_PER_TONNE, "DES APY district series")
    for row in read("upag_target_districts.csv"):
        _add(out, row, Decimal(row["yield"]) / 100, "DES APY via UPAG")  # kg/ha -> qtl/ha
    return out


def _add(out, row, qtl_ha, source) -> None:
    season = SEASONS.get(row["season"].strip().lower())
    crop = next((code for code, (names, _) in CROPS.items() if row["crop_name"].strip() in names), None)
    if not season or not crop or not row["area"].strip():
        return
    area = Decimal(row["area"])
    if area <= 0 or qtl_ha <= 0:
        return
    key = (DISTRICTS[row["district_name"].strip().lower()], crop, season)
    out[key][row["year"]] = (qtl_ha, area, source)


def costs() -> dict:
    """crop -> (year, A2+FL Rs/ha, C2 Rs/ha), latest year."""
    latest: dict = {}
    for row in read("cost_of_cultivation_up.csv"):
        crop = next((code for code, (_, name) in CROPS.items() if row["crop_name"] == name), None)
        if crop and row["cul_cost_a2fl"].strip():
            if crop not in latest or row["year"] > latest[crop][0]:
                latest[crop] = (row["year"], Decimal(row["cul_cost_a2fl"]), Decimal(row["cul_cost_c2"] or 0))
    return latest


def main() -> int:
    if "--download" in sys.argv:
        download()
    today = date.today().isoformat()
    ylds, cost = yields(), costs()

    economics, seasons = [], []
    for (district, crop, season), by_year in sorted(ylds.items()):
        recent = sorted(by_year.items())[-YEARS:]
        mean_area = statistics.fmean(float(v[1]) for _y, v in recent[-3:])
        if mean_area < MIN_AREA_HA or recent[-1][0] < LATEST_FROM:
            continue
        values = [per_acre(v[0]) for _y, v in recent]
        sources = sorted({v[2] for _y, v in recent})
        seasons.append({
            "district_code": district, "crop": crop, "season": season,
            "mean_area_ha": round(mean_area), "years": f"{recent[-3][0] if len(recent) >= 3 else recent[0][0]}..{recent[-1][0]}",
            "source": "; ".join(sources), "as_of": today,
        })
        c = cost.get(crop)
        w = WATER.get(crop)
        economics.append({
            "district_code": district, "crop": crop, "season": season,
            "yield_qtl_acre_low": q(min(values)), "yield_qtl_acre_median": q(Decimal(statistics.median(values))),
            "yield_qtl_acre_high": q(max(values)),
            "yield_years": f"{recent[0][0]}..{recent[-1][0]}", "yield_source": "; ".join(sources),
            "cost_a2fl_inr_acre": q(per_acre(c[1]), "1") if c else "",
            "cost_c2_inr_acre": q(per_acre(c[2]), "1") if c and c[2] else "",
            "cost_year": c[0] if c else "",
            "cost_source": "DES Cost of Cultivation Scheme, Uttar Pradesh (state average)" if c else "",
            "water_mm_low": w[0] if w else "", "water_mm_high": w[1] if w else "",
            "water_need": w[2] if w else "", "water_source": w[3] if w else "",
            "verified": "false", "as_of": today,
            "notes": "" if c and w else "TODO: " + ", ".join(
                x for x, ok in (("cost not in DES series", c), ("water need not sourced", w)) if not ok),
        })

    _write(ROOT / "data" / "district_crop_economics.csv", economics)
    _write(ROOT / "data" / "crop_seasons.csv", seasons)
    print(f"economics: {len(economics)} rows, seasons: {len(seasons)} rows")
    return 0


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    sys.exit(main())
