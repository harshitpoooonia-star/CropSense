"""Price per quintal for the profit range (spec 02, R3).

1. Recent mandi modal prices from the cache (filled by Section 7's
   Agmarknet adapter): interquartile range of the last 30 days in the farmer's
   district.
2. Otherwise the crop's MSP, labelled as such: a floor for procured crops,
   not what a trader pays.
3. Otherwise unknown.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..districts import District
from ..models import CachedPrice
from .data import msp_table

WINDOW_DAYS = 30
MIN_ROWS = 3

# Agmarknet commodity names vary; match on keywords (include, exclude).
COMMODITY_KEYWORDS = {
    "wheat": (("wheat",), ("atta", "flour")),
    "paddy": (("paddy",), ()),
    "mustard": (("mustard",), ("oil",)),
    "potato": (("potato",), ("sweet",)),
    "maize": (("maize",), ()),
    "barley": (("barley",), ()),
    "bajra": (("bajra", "pearl millet"), ()),
    "chickpea": (("bengal gram", "gram"), ("green gram", "black gram", "flour", "dal")),
    "blackgram": (("black gram", "urad"), ("dal",)),
    "mungbean": (("green gram", "moong"), ("dal",)),
    "pigeonpeas": (("arhar", "tur"), ("dal",)),
    "lentil": (("lentil", "masur", "masoor"), ("dal",)),
    "sugarcane": (("sugarcane",), ()),
}


@dataclass(frozen=True)
class PriceInfo:
    kind: str  # mandi | msp
    low: Decimal
    high: Decimal
    as_of: date
    source: str
    verified: bool = True


def matches(crop: str, commodity: str) -> bool:
    include, exclude = COMMODITY_KEYWORDS.get(crop, ((), ()))
    name = " ".join(commodity.lower().split())
    return any(k in name for k in include) and not any(k in name for k in exclude)


def recent_mandi(session: Session, district: District, crop: str, today: date) -> PriceInfo | None:
    since = today - timedelta(days=WINDOW_DAYS)
    rows = session.scalars(select(CachedPrice).where(
        CachedPrice.arrival_date >= since, CachedPrice.modal_price.is_not(None))).all()
    name = district.name_en.lower()
    picked = [r for r in rows if name.split()[0] in r.district.lower() and matches(crop, r.commodity)]
    if len(picked) < MIN_ROWS:
        return None
    modal = sorted(float(r.modal_price) for r in picked)
    q1, _median, q3 = statistics.quantiles(modal, n=4, method="inclusive")
    latest = max(r.arrival_date for r in picked)
    markets = sorted({r.market for r in picked})
    return PriceInfo("mandi", Decimal(str(round(q1))), Decimal(str(round(q3))), latest,
                     f"Agmarknet, {', '.join(markets[:3])}")


def msp(crop: str) -> PriceInfo | None:
    row = msp_table().get(crop)
    if row is None:
        return None
    return PriceInfo("msp", row.price, row.price, row.announced,
                     f"MSP {row.marketing_season}: {row.source}", row.verified)


def price_for(session: Session, district: District, crop: str, today: date) -> PriceInfo | None:
    return recent_mandi(session, district, crop, today) or msp(crop)
