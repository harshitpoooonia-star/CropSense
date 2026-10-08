#!/usr/bin/env python3
"""Build data/mandis.csv: mandi towns in the target districts with coordinates.

List: mandi towns from a 1996 Lok Sabha table of UP mandis (old: confirm each
against the market names Agmarknet actually reports; see the Gate 0 script).
Coordinates: the town's point on Wikidata (CC0). A mandi yard is in or next
to its town, so this is approximate, and distances are shown as straight-line.

    python scripts/build_mandis.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "mandis.csv"
LIST_SOURCE = "Lok Sabha table of UP mandis, 1996 (eparlib 11_II_11091996_p160_p163_T259); confirm against Agmarknet market names"

# district code -> mandi towns (as spelled in the 1996 table, corrected where the
# modern name is clear: Ghjazibad -> Ghaziabad, Jawar -> Jewar, Khain -> Khair)
SEED = {
    "UP-ghaziabad": ["Ghaziabad", "Muradnagar"],
    "UP-hapur": ["Hapur"],
    "UP-gautam-buddh-nagar": ["Dadri", "Dankaur", "Jewar"],
    "UP-bulandshahr": ["Bulandshahr", "Jahangirabad", "Gulaothi", "Siana", "Khurja", "Sikandrabad", "Dibai",
                       "Anupshahr", "Shikarpur"],
    "UP-aligarh": ["Aligarh", "Khair", "Chharra", "Atrauli"],
}
# Extra spellings to match Agmarknet market names against.
ALIASES = {"Bulandshahr": "Bulandshahar", "Anupshahr": "Anupshahar", "Siana": "Siyana"}

QUERY = """
SELECT ?item ?label ?coord WHERE {
  VALUES ?name { %s }
  ?item rdfs:label ?label ; wdt:P625 ?coord ; wdt:P131+ wd:%s .
  FILTER(LANG(?label) = "en" && STR(?label) = ?name)
}"""


def wikidata(names: list[str], district_qid: str) -> dict[str, tuple[str, float, float]]:
    values = " ".join(f'"{n}"' for n in names)
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
        {"query": QUERY % (values, district_qid), "format": "json"})
    request = urllib.request.Request(url, headers={"User-Agent": "AgriSense-student-project/0.1 (mandi table)"})
    out = {}
    for row in json.load(urllib.request.urlopen(request, timeout=120))["results"]["bindings"]:
        name = row["label"]["value"]
        lon, lat = map(float, re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", row["coord"]["value"]).groups())
        out.setdefault(name, (row["item"]["value"].rsplit("/", 1)[1], round(lat, 4), round(lon, 4)))
    return out


def nearest_in_up(name: str, lat: float, lon: float) -> tuple[str, float, float] | None:
    """Fallback when Wikidata doesn't link the town under its district: same
    name anywhere in UP (Q1498), nearest to the district's point, within 60 km."""
    candidates = wikidata_any(name)
    ranked = sorted(candidates, key=lambda c: (c[1] - lat) ** 2 + (c[2] - lon) ** 2)
    if ranked and ((ranked[0][1] - lat) ** 2 + (ranked[0][2] - lon) ** 2) ** 0.5 * 111 <= 60:
        return ranked[0]
    return None


def wikidata_any(name: str) -> list[tuple[str, float, float]]:
    query = f"""SELECT ?item ?coord WHERE {{ ?item rdfs:label "{name}"@en ; wdt:P625 ?coord ; wdt:P131+ wd:Q1498 . }}"""
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query, "format": "json"})
    request = urllib.request.Request(url, headers={"User-Agent": "AgriSense-student-project/0.1 (mandi table)"})
    out = []
    for row in json.load(urllib.request.urlopen(request, timeout=120))["results"]["bindings"]:
        lon, lat = map(float, re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", row["coord"]["value"]).groups())
        out.append((row["item"]["value"].rsplit("/", 1)[1], round(lat, 4), round(lon, 4)))
    return out


def main() -> int:
    with (ROOT / "data" / "districts.csv").open(encoding="utf-8") as f:
        district_rows = {r["code"]: r for r in csv.DictReader(f)}
    qids = {code: r["source"].split()[1] for code, r in district_rows.items()}
    today = date.today().isoformat()
    rows = []
    for district, towns in SEED.items():
        found = wikidata(towns, qids[district])
        d = district_rows[district]
        for town in towns:
            if town not in found:
                hit = nearest_in_up(town, float(d["lat"]), float(d["lon"]))
                if hit:
                    found[town] = hit
        for town in towns:
            hit = found.get(town)
            rows.append({
                "market": town, "aliases": ALIASES.get(town, ""), "district_code": district,
                "lat": hit[1] if hit else "", "lon": hit[2] if hit else "",
                "coord_source": f"Wikidata {hit[0]} (P625), town point" if hit else "",
                "list_source": LIST_SOURCE, "verified": "false", "as_of": today,
                "notes": "" if hit else "TODO: no Wikidata point for this town name; find the mandi yard's location",
            })
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    missing = [r["market"] for r in rows if not r["lat"]]
    print(f"wrote {len(rows)} mandis, {len(rows) - len(missing)} with coordinates; missing: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
