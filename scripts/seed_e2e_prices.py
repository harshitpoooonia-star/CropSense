#!/usr/bin/env python3
"""Seed the throwaway e2e database with the synthetic Agmarknet fixture,
re-dated to yesterday so it counts as fresh. Test data only; never run
against a real database (refuses unless AGRISENSE_ENV=development)."""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agrisense import create_app  # noqa: E402
from agrisense.extensions import db  # noqa: E402
from agrisense.market import agmarknet  # noqa: E402


def main() -> int:
    if os.environ.get("AGRISENSE_ENV") != "development":
        sys.exit("refusing: seed only the development/e2e database")
    fixture = json.loads((ROOT / "tests" / "fixtures" / "agmarknet" / "day.json").read_text(encoding="utf-8"))
    yesterday = (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
    records = [{**r, "Arrival_Date": yesterday} for r in fixture["records"]]
    app = create_app()
    with app.app_context():
        rows = [r for r in map(agmarknet.normalize, records) if r]
        agmarknet.store(db.session, rows)
        db.session.commit()
    print(f"seeded {len(rows)} synthetic price rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
