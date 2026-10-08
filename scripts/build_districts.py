#!/usr/bin/env python3
"""Build data/districts.csv: UP and Haryana districts with coordinates.

Source: Wikidata (CC0), districts of India (Q1149652) located in Uttar
Pradesh (Q1498) or Haryana (Q1174), not dissolved, with a coordinate (P625).
Where an item has several coordinates they are averaged. The coordinate is
approximate (Wikidata's point for the district, often its headquarters), so
the app always asks the farmer to confirm the suggested district.

    python scripts/build_districts.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "districts.csv"
STATES = {"Q1498": "UP", "Q1174": "HR"}
QUERY = """
SELECT DISTINCT ?d ?en ?hi ?state ?coord WHERE {
  VALUES ?state { wd:Q1498 wd:Q1174 }
  ?d wdt:P31/wdt:P279* wd:Q1149652 ; wdt:P131+ ?state ; wdt:P625 ?coord .
  FILTER NOT EXISTS { ?d wdt:P576 ?dissolved }
  OPTIONAL { ?d rdfs:label ?en FILTER(LANG(?en) = "en") }
  OPTIONAL { ?d rdfs:label ?hi FILTER(LANG(?hi) = "hi") }
}"""


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def clean(name: str, suffixes: tuple[str, ...]) -> str:
    for suffix in suffixes:
        if name.endswith(suffix):
            return name[: -len(suffix)].strip()
    return name.strip()


def main() -> int:
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": QUERY, "format": "json"})
    request = urllib.request.Request(url, headers={"User-Agent": "AgriSense-student-project/0.1 (district table)"})
    rows = json.load(urllib.request.urlopen(request, timeout=120))["results"]["bindings"]

    items: dict[str, dict] = {}
    coords: dict[str, set[tuple[float, float]]] = defaultdict(set)
    for row in rows:
        qid = row["d"]["value"].rsplit("/", 1)[1]
        lon, lat = map(float, re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", row["coord"]["value"]).groups())
        coords[qid].add((round(lat, 4), round(lon, 4)))
        items[qid] = {
            "state": STATES[row["state"]["value"].rsplit("/", 1)[1]],
            "en": clean(row.get("en", {}).get("value", ""), (" district", " District")),
            "hi": clean(row.get("hi", {}).get("value", ""), (" जिला", " ज़िला")),
        }

    today = date.today().isoformat()
    out_rows = []
    for qid, item in items.items():
        if not item["en"]:
            print(f"skipping {qid}: no English label", file=sys.stderr)
            continue
        points = coords[qid]
        lat = round(sum(p[0] for p in points) / len(points), 4)
        lon = round(sum(p[1] for p in points) / len(points), 4)
        out_rows.append({
            "code": f"{item['state']}-{slug(item['en'])}",
            "state": item["state"],
            "name_en": item["en"],
            "name_hi": item["hi"] or item["en"],
            "lat": lat,
            "lon": lon,
            "source": f"Wikidata {qid} (P625)" + (f", mean of {len(points)} points" if len(points) > 1 else ""),
            "as_of": today,
        })
    out_rows.sort(key=lambda r: (r["state"], r["name_en"]))
    codes = [r["code"] for r in out_rows]
    if len(codes) != len(set(codes)):
        sys.exit("duplicate district codes; check Wikidata labels")

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        writer.writeheader()
        writer.writerows(out_rows)
    counts = {s: sum(r["state"] == s for r in out_rows) for s in STATES.values()}
    print(f"wrote {len(out_rows)} districts {counts} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
