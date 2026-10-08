"""Open-Meteo adapter (ADR-004): 72-hour hourly forecast for a farm, cached.

Cache key is the pin rounded to 0.01 degree (about 1 km), so nearby farms
share a call and no exact location is stored with weather. A cached forecast
is reused for an hour (spec); past that we try once with a short timeout and
fall back to the cache, labelled with its age. Open-Meteo is free for
non-commercial use under CC BY 4.0: the source line credits it.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..data.base import Result, SourceInfo
from ..models import CachedWeather, aware, utcnow
from .rules import Hour

log = logging.getLogger(__name__)

API_URL = "https://api.open-meteo.com/v1/forecast"
SOURCE = "open-meteo"
CREDIT = "Open-Meteo.com (CC BY 4.0)"
HOURLY = "precipitation_probability,precipitation,wind_speed_10m,relative_humidity_2m,temperature_2m"
TTL = timedelta(hours=1)
TIMEZONE = "Asia/Kolkata"

Getter = Callable[[str, dict, float], dict]


@dataclass(frozen=True)
class Forecast:
    hours: list[Hour]
    fetched_at: datetime


def fetch_json(url: str, params: dict, timeout: float) -> dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": "AgriSense (non-commercial)"})
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return json.load(resp)


def cell(lat: float, lon: float) -> tuple[Decimal, Decimal]:
    return Decimal(str(round(lat, 2))), Decimal(str(round(lon, 2)))


def parse(payload: dict) -> list[Hour]:
    h = payload["hourly"]
    keys = ("precipitation_probability", "precipitation", "wind_speed_10m", "relative_humidity_2m", "temperature_2m")
    columns = [h.get(k) or [None] * len(h["time"]) for k in keys]
    return [Hour(datetime.fromisoformat(time), *(col[i] for col in columns)) for i, time in enumerate(h["time"])]


def forecast(session: Session, lat: float, lon: float, *, get: Getter = fetch_json, timeout: float = 4,
             stale_after: timedelta = timedelta(hours=3)) -> Result[Forecast]:
    lat_r, lon_r = cell(lat, lon)
    row = session.scalar(select(CachedWeather).where(
        CachedWeather.source == SOURCE, CachedWeather.lat_r == lat_r, CachedWeather.lon_r == lon_r))
    now = utcnow()
    if row is not None and aware(row.valid_until) > now:
        return _result(row, now, stale_after)
    try:
        payload = get(API_URL, {"latitude": str(lat_r), "longitude": str(lon_r), "hourly": HOURLY,
                                "forecast_days": 3, "past_days": 2, "timezone": TIMEZONE,
                                "wind_speed_unit": "kmh"}, timeout)
        parse(payload)  # reject a malformed response before caching it
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
        log.warning("Open-Meteo fetch failed: %s", type(exc).__name__)
        if row is None:
            return Result(None, SourceInfo(CREDIT, None, None, stale=True, note="unavailable"))
        result = _result(row, now, stale_after)
        return Result(result.data, SourceInfo(CREDIT, result.source.as_of, result.source.fetched_at,
                                              stale=result.source.stale, note="refresh_failed"))
    if row is None:
        row = CachedWeather(source=SOURCE, lat_r=lat_r, lon_r=lon_r, payload=payload, fetched_at=now,
                            valid_until=now + TTL)
        session.add(row)
    else:
        row.payload, row.fetched_at, row.valid_until = payload, now, now + TTL
    session.commit()
    return _result(row, now, stale_after)


def _result(row: CachedWeather, now: datetime, stale_after: timedelta) -> Result[Forecast]:
    fetched = aware(row.fetched_at)
    return Result(Forecast(parse(row.payload), fetched),
                  SourceInfo(CREDIT, fetched, fetched, stale=now - fetched > stale_after))
