"""Agmarknet adapter (ADR-004): data.gov.in daily mandi prices -> cached_price.

Reuses the Gate 0 script's findings: resource 35985678-..., capitalised field
names, dd/mm/yyyy dates, Rs per quintal. Fetches Uttar Pradesh for a day,
keeps rows from the target districts, and upserts them. Tests pass a fake
`get`; the network is never touched in the suite.

TODO(verify on the first live run, as in scripts/check_agmarknet.py):
resource id, Arrival_Date format, State spelling, page size.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CachedPrice, utcnow

log = logging.getLogger(__name__)

API_URL = "https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24"
API_DATE_FORMAT = "%d/%m/%Y"
PAGE_LIMIT = 1000
STATE = "Uttar Pradesh"
SOURCE = "agmarknet"
# Our district codes -> keywords in Agmarknet's district names.
DISTRICT_KEYS = {
    "UP-gautam-buddh-nagar": ("gautam", "noida"),
    "UP-ghaziabad": ("ghaziabad",),
    "UP-bulandshahr": ("bulandshahr", "bulandshahar"),
    "UP-hapur": ("hapur",),
    "UP-aligarh": ("aligarh",),
}

Getter = Callable[[str, dict, float], dict]


class FatalApiError(RuntimeError):
    """Retrying won't help: bad key, bad resource id."""


@dataclass
class RefreshReport:
    days: int = 0
    rows_seen: int = 0
    rows_stored: int = 0
    failed_days: list[date] = field(default_factory=list)
    error: str | None = None


def fetch_json(url: str, params: dict, timeout: float = 30, retries: int = 2) -> dict:
    """GET with backoff on 429/5xx. Errors never include the URL (it holds the key)."""
    query = urllib.parse.urlencode(params)
    last = ""
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(f"{url}?{query}", timeout=timeout) as resp:
                data = json.load(resp)
            if isinstance(data, dict) and data.get("status") == "error":
                raise FatalApiError(f"data.gov.in error: {data.get('message', 'unknown')}")
            return data
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403) or exc.code not in (429, 500, 502, 503, 504):
                raise FatalApiError(f"HTTP {exc.code} from data.gov.in") from None
            last = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = type(exc).__name__
        if attempt < retries:
            time.sleep(2**attempt)
    raise RuntimeError(f"data.gov.in failed after {retries + 1} tries ({last})")


def fetch_day(api_key: str, day: date, get: Getter = fetch_json, timeout: float = 30) -> list[dict]:
    rows: list[dict] = []
    while True:
        params = {"api-key": api_key, "format": "json", "limit": PAGE_LIMIT, "offset": len(rows),
                  "filters[State]": STATE, "filters[Arrival_Date]": day.strftime(API_DATE_FORMAT)}
        page = get(API_URL, params, timeout)
        records = page.get("records") or []
        rows.extend(records)
        total = int(page.get("total") or 0)
        if len(records) < PAGE_LIMIT or (total and len(rows) >= total):
            return rows


def _district(name: str) -> str | None:
    name = " ".join(str(name or "").lower().split())
    return next((code for code, keys in DISTRICT_KEYS.items() if any(k in name for k in keys)), None)


def _date(value: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _price(value) -> Decimal | None:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None
    return number if number.is_finite() and number > 0 else None


def normalize(raw: dict) -> dict | None:
    rec = {str(k).lower(): v for k, v in raw.items()}
    district = _district(rec.get("district"))
    day = _date(rec.get("arrival_date", ""))
    modal = _price(rec.get("modal_price"))
    if district is None or day is None or modal is None:
        return None
    return {
        "source": SOURCE, "state": str(rec.get("state", STATE)).strip(),
        "district": str(rec.get("district", "")).strip(), "market": str(rec.get("market", "")).strip(),
        "commodity": str(rec.get("commodity", "")).strip(), "variety": str(rec.get("variety", "")).strip(),
        "grade": str(rec.get("grade", "")).strip(), "arrival_date": day,
        "min_price": _price(rec.get("min_price")), "max_price": _price(rec.get("max_price")), "modal_price": modal,
    }


def store(session: Session, rows: list[dict]) -> int:
    """Upsert on (source, market, commodity, variety, grade, arrival_date). Doesn't commit."""
    stored = 0
    now = utcnow()
    for row in rows:
        existing = session.scalar(select(CachedPrice).where(
            CachedPrice.source == row["source"], CachedPrice.market == row["market"],
            CachedPrice.commodity == row["commodity"], CachedPrice.variety == row["variety"],
            CachedPrice.grade == row["grade"], CachedPrice.arrival_date == row["arrival_date"]))
        if existing is None:
            session.add(CachedPrice(**row, fetched_at=now))
        else:
            for key in ("min_price", "max_price", "modal_price", "district", "state"):
                setattr(existing, key, row[key])
            existing.fetched_at = now
        stored += 1
    session.flush()
    return stored


def refresh(session: Session, api_key: str | None, days: int = 3, today: date | None = None,
            get: Getter = fetch_json, timeout: float = 30) -> RefreshReport:
    """Fetch the last `days` days into the cache and commit. Never raises for API trouble."""
    report = RefreshReport()
    if not api_key:
        report.error = "no_key"
        return report
    today = today or date.today()
    for offset in range(days):
        day = today - timedelta(days=offset)
        try:
            raw = fetch_day(api_key, day, get, timeout)
        except FatalApiError as exc:
            report.error = str(exc)
            break
        except RuntimeError as exc:
            log.warning("Agmarknet %s skipped: %s", day, exc)
            report.failed_days.append(day)
            continue
        report.days += 1
        report.rows_seen += len(raw)
        report.rows_stored += store(session, [r for r in map(normalize, raw) if r])
    session.commit()
    return report
