#!/usr/bin/env python3
"""Seed the throwaway e2e database with synthetic test data, so the browser
tests never call outside services:
  - the Agmarknet fixture, re-dated to yesterday (fresh prices);
  - a 5-day synthetic Open-Meteo forecast for the test phone's GPS cell.
Refuses unless AGRISENSE_ENV=development: never run against a real database."""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agrisense import create_app  # noqa: E402
from agrisense.extensions import db  # noqa: E402
from agrisense.market import agmarknet  # noqa: E402
from agrisense.models import CachedWeather, utcnow  # noqa: E402

GPS_CELL = (Decimal("28.40"), Decimal("77.85"))  # tests/e2e/conftest.py gps_page
IST = timezone(timedelta(hours=5, minutes=30))


def forecast_payload() -> dict:
    """Breezy and dry, with rain likely tomorrow afternoon."""
    start = datetime.now(IST).replace(tzinfo=None, minute=0, second=0, microsecond=0) - timedelta(hours=48)
    hours = [start + timedelta(hours=i) for i in range(48 + 96)]
    tomorrow = (datetime.now(IST) + timedelta(days=1)).date()
    rainy = [h.date() == tomorrow and 14 <= h.hour < 20 for h in hours]
    return {"hourly": {
        "time": [h.isoformat(timespec="minutes") for h in hours],
        "precipitation_probability": [80 if r else 5 for r in rainy],
        "precipitation": [2.0 if r else 0.0 for r in rainy],
        "wind_speed_10m": [10.0] * len(hours),
        "relative_humidity_2m": [60] * len(hours),
        "temperature_2m": [28.0] * len(hours),
    }}


def main() -> int:
    if os.environ.get("AGRISENSE_ENV") != "development":
        sys.exit("refusing: seed only the development/e2e database")
    fixture = json.loads((ROOT / "tests" / "fixtures" / "agmarknet" / "day.json").read_text(encoding="utf-8"))
    yesterday = (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
    app = create_app()
    with app.app_context():
        rows = [r for r in map(agmarknet.normalize, ({**r, "Arrival_Date": yesterday} for r in fixture["records"])) if r]
        agmarknet.store(db.session, rows)
        now = utcnow()
        db.session.add(CachedWeather(source="open-meteo", lat_r=GPS_CELL[0], lon_r=GPS_CELL[1],
                                     payload=forecast_payload(), fetched_at=now, valid_until=now + timedelta(days=1)))
        db.session.commit()
    print(f"seeded {len(rows)} synthetic price rows and a synthetic forecast")
    return 0


if __name__ == "__main__":
    sys.exit(main())
