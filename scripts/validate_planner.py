#!/usr/bin/env python3
"""Check Crop Planner v2 against real farms (spec 02, R6).

Reads data/farm_records.csv: one row per farmer, with their field and the
crop a good local farmer chose. Prints the share of records whose chosen crop
is in the planner's top 3 (target: 70% of 30 records). The Kaggle test
accuracy is printed only as a secondary number.

Prices: the planner uses whatever the price cache holds; offline, that's MSP.

    python scripts/validate_planner.py [--records path.csv]
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from werkzeug.datastructures import MultiDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agrisense import create_app, farm_context  # noqa: E402
from agrisense import farm_profile as fp  # noqa: E402
from agrisense.extensions import db  # noqa: E402
from agrisense.planner import model, rank  # noqa: E402

RECORDS = Path(__file__).resolve().parent.parent / "data" / "farm_records.csv"
TARGET = 0.70


def profile_for(row: dict) -> tuple[dict, list[str]]:
    profile = fp.empty()
    errors = []
    errors += fp.apply_where(profile, MultiDict({"location_source": "district", "district_code": row["district_code"]}))
    errors += fp.apply_area(profile, MultiDict({"area": row["area_acre"] or "1", "area_unit": "acre"}))
    errors += fp.apply_water(profile, MultiDict({"irrigation_source": row["irrigation_source"]}))
    soil = {f"soil_{k}": row.get(f"soil_{k}", "") for k in ("n", "p", "k", "ph", "oc")}
    errors += fp.apply_soil(profile, MultiDict(soil))
    return profile, [f"{e.field}:{e.code}" for e in errors]


def main() -> int:
    path = Path(sys.argv[sys.argv.index("--records") + 1]) if "--records" in sys.argv else RECORDS
    with path.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("record_id", "").strip()]

    app = create_app("testing")
    hits, used, skipped = 0, 0, []
    with app.app_context(), app.test_request_context("/"):
        db.create_all()
        for row in rows:
            profile, errors = profile_for(row)
            if errors:
                skipped.append((row["record_id"], errors))
                continue
            plan = rank.plan(farm_context.build(profile), row["season"], db.session)
            top = [o.crop for o in plan.top]
            hit = row["chosen_crop"] in top
            hits += hit
            used += 1
            print(f"{row['record_id']:>6} {row['season']:<7} chose {row['chosen_crop']:<10} top3 {top} {'HIT' if hit else 'miss'}")

    print()
    if used == 0:
        print(f"No usable farm records yet in {path.name}. Collect them in the Gate 0 interviews (target: 30).")
    else:
        rate = hits / used
        print(f"Top-3 hit rate: {hits}/{used} = {rate:.0%} (target {TARGET:.0%} of 30 records)"
              + ("" if used >= 30 else f"; only {used} records so far"))
    for record_id, errors in skipped:
        print(f"skipped {record_id}: {', '.join(errors)}")
    m = model.metrics()
    print(f"Secondary: suitability model on the Kaggle split, test accuracy {m['test_accuracy']:.1%} "
          f"(5-fold CV {m['cv_accuracy_mean']:.1%}). Says little about real farms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
