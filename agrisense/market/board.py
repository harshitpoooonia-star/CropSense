"""Price board and offer checker (spec 04).

For a farm and a crop: the 5 nearest mandis, each with its latest min /
modal / max in the last PRICE_WINDOW_DAYS, the price date, an "old" flag past
PRICE_STALE_DAYS, and a net price after the farmer's own transport rate.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..data.base import SourceInfo
from ..models import CachedPrice
from . import commodities, mandis

ONE = Decimal("1")


@dataclass
class Quote:
    mandi: mandis.Mandi
    km: float
    arrival_date: date
    min_price: Decimal | None
    modal_price: Decimal
    max_price: Decimal | None
    varieties: list[str]
    stale: bool
    days_old: int
    transport: Decimal | None = None  # Rs per quintal for this distance
    net: Decimal | None = None


@dataclass
class Board:
    crop: str
    quotes: list[Quote]  # mandis with a price, nearest first
    without_data: list[tuple[mandis.Mandi, float]] = field(default_factory=list)
    source: SourceInfo | None = None

    @property
    def reference(self) -> Quote | None:
        """The nearest mandi with a fresh price, else the nearest with any price."""
        fresh = [q for q in self.quotes if not q.stale]
        return (fresh or self.quotes or [None])[0]


def board(session: Session, lat: float, lon: float, crop: str, today: date, *, window_days: int,
          stale_days: int, transport_rate: Decimal | None, n: int = 5) -> Board:
    near = mandis.nearest(lat, lon, n)
    since = today - timedelta(days=window_days)
    rows = session.scalars(select(CachedPrice).where(
        CachedPrice.arrival_date >= since, CachedPrice.arrival_date <= today)).all()
    by_mandi: dict[str, list[CachedPrice]] = {}
    for row in rows:
        if not commodities.matches(crop, row.commodity):
            continue
        mandi = mandis.match(row.market)
        if mandi is not None:
            by_mandi.setdefault(mandi.market, []).append(row)

    quotes, missing = [], []
    for mandi, km in near:
        rows_here = by_mandi.get(mandi.market)
        if not rows_here:
            missing.append((mandi, km))
            continue
        latest = max(r.arrival_date for r in rows_here)
        day_rows = [r for r in rows_here if r.arrival_date == latest]
        # Several varieties on one day: the median modal, and the widest min-max.
        modal = Decimal(str(statistics.median(float(r.modal_price) for r in day_rows))).quantize(ONE, ROUND_HALF_UP)
        mins = [r.min_price for r in day_rows if r.min_price is not None]
        maxs = [r.max_price for r in day_rows if r.max_price is not None]
        quote = Quote(
            mandi=mandi, km=km, arrival_date=latest, min_price=min(mins) if mins else None, modal_price=modal,
            max_price=max(maxs) if maxs else None, varieties=sorted({r.variety for r in day_rows if r.variety}),
            days_old=(today - latest).days, stale=(today - latest).days > stale_days,
        )
        if transport_rate is not None:
            quote.transport = (transport_rate * Decimal(str(km))).quantize(ONE, ROUND_HALF_UP)
            quote.net = modal - quote.transport
        quotes.append(quote)

    newest = max((q.arrival_date for q in quotes), default=None)
    fetched = max((r.fetched_at for r in rows), default=None)
    source = SourceInfo(name="Agmarknet", as_of=newest, fetched_at=fetched,
                        stale=newest is None or (today - newest).days > stale_days)
    return Board(crop=crop, quotes=quotes, without_data=missing, source=source)


@dataclass(frozen=True)
class Verdict:
    status: str  # below | fair | above
    gap: Decimal  # offer - modal, Rs per quintal
    gap_pct: Decimal


def check_offer(offer: Decimal, modal: Decimal, band_pct: Decimal) -> Verdict:
    """Fair = within band_pct of the modal price, edges included."""
    gap = offer - modal
    pct = (gap / modal * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)
    if gap < -(modal * band_pct / 100):
        status = "below"
    elif gap > modal * band_pct / 100:
        status = "above"
    else:
        status = "fair"
    return Verdict(status, gap.quantize(ONE, ROUND_HALF_UP), pct)


def price_change(session: Session, mandi: mandis.Mandi, crop: str, today: date, window_days: int) -> tuple | None:
    """(latest date, latest modal, previous date, previous modal) at one mandi, for the Today tab."""
    since = today - timedelta(days=window_days)
    rows = [r for r in session.scalars(select(CachedPrice).where(CachedPrice.arrival_date >= since)).all()
            if commodities.matches(crop, r.commodity) and mandis.match(r.market) == mandi]
    by_day: dict[date, list[float]] = {}
    for r in rows:
        by_day.setdefault(r.arrival_date, []).append(float(r.modal_price))
    days = sorted(by_day, reverse=True)
    if len(days) < 2:
        return None
    latest, previous = days[0], days[1]
    return (latest, Decimal(str(statistics.median(by_day[latest]))).quantize(ONE),
            previous, Decimal(str(statistics.median(by_day[previous]))).quantize(ONE))
