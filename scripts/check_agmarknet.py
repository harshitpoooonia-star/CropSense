#!/usr/bin/env python3
"""Gate 0: is Agmarknet mandi data fresh enough near Greater Noida?

Pulls the last N days (default 14) of mandi prices from the data.gov.in
Agmarknet API for wheat, paddy, mustard and potato; lists the mandis the API
has in Gautam Buddh Nagar, Ghaziabad, Bulandshahr, Hapur and Aligarh; picks
10; saves CSVs under data/raw/; and prints per mandi the days with data, the
latest price date and the longest gap.

Gate 0 tooling only, no app features. The real adapter comes in Section 7.

    $env:DATA_GOV_IN_KEY = "<your key>"      # PowerShell
    python scripts/check_agmarknet.py
    python scripts/check_agmarknet.py --markets "<market>,<market>"
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

# "Variety-wise Daily Market Prices Data of Commodity": historical daily rows.
# The other Agmarknet resource (9ef84268-...) only holds today's rows.
# https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity
# TODO(verify on first live run): resource id, that filters[Arrival_Date]
# takes dd/mm/yyyy, the State spelling, and the largest `limit` accepted.
API_URL = "https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24"
API_DATE_FORMAT = "%d/%m/%Y"
PAGE_LIMIT = 1000
STATE = "Uttar Pradesh"

# Nearest first, by district: Greater Noida is in Gautam Buddh Nagar,
# Ghaziabad and Bulandshahr border it, Hapur borders both, Aligarh lies past
# Bulandshahr. Approximate: mandi coordinates arrive with data/mandis.csv in
# Section 7. Check the pick by hand and override it with --markets.
TARGET_DISTRICTS: list[tuple[str, tuple[str, ...]]] = [
    ("Gautam Buddh Nagar", ("gautam", "noida")),
    ("Ghaziabad", ("ghaziabad",)),
    ("Bulandshahr", ("bulandshahr", "bulandshahar")),
    ("Hapur", ("hapur",)),
    ("Aligarh", ("aligarh",)),
]
DISTRICT_RANK = {name: i for i, (name, _) in enumerate(TARGET_DISTRICTS)}

# Commodity names vary between markets, so match on keywords (include,
# exclude) and print every raw name that matched for a person to check.
CROPS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "wheat": (("wheat",), ("atta", "flour")),
    "paddy": (("paddy",), ()),
    "mustard": (("mustard",), ("oil",)),
    "potato": (("potato",), ("sweet",)),
}

STALE_AFTER_DAYS = 3  # spec P0-4: say so when a price is older than 3 days
DEFAULT_OUT_DIR = Path("data/raw")

Getter = Callable[[str, dict], dict]


class FatalApiError(RuntimeError):
    """A request that retrying will not fix (bad key, bad resource id)."""


# ---------------------------------------------------------------- parsing


def parse_date(value: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _norm(text: object) -> str:
    return " ".join(str(text or "").lower().split())


def match_crop(commodity: str) -> str | None:
    name = _norm(commodity)
    for crop, (include, exclude) in CROPS.items():
        if any(k in name for k in include) and not any(k in name for k in exclude):
            return crop
    return None


def match_district(district: str) -> str | None:
    name = _norm(district)
    for canonical, keys in TARGET_DISTRICTS:
        if any(k in name for k in keys):
            return canonical
    return None


def _price(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def normalize(raw: dict) -> dict | None:
    """Lower-case the API's field names; keep target-district rows only."""
    rec = {str(k).lower(): v for k, v in raw.items()}
    district = match_district(rec.get("district", ""))
    day = parse_date(rec.get("arrival_date", ""))
    if district is None or day is None:
        return None
    return {
        "date": day,
        "district": district,
        "district_raw": str(rec.get("district", "")).strip(),
        "market": str(rec.get("market", "")).strip(),
        "commodity": str(rec.get("commodity", "")).strip(),
        "crop": match_crop(rec.get("commodity", "")),
        "variety": str(rec.get("variety", "")).strip(),
        "grade": str(rec.get("grade", "")).strip(),
        "min_price": _price(rec.get("min_price")),
        "max_price": _price(rec.get("max_price")),
        "modal_price": _price(rec.get("modal_price")),
    }


# ---------------------------------------------------------------- fetching


def fetch_json(url: str, params: dict, *, retries: int = 3, timeout: int = 30) -> dict:
    """GET with backoff on 429/5xx. Errors never include the URL (it holds the key)."""
    query = urllib.parse.urlencode(params)
    last_error = ""
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(f"{url}?{query}", timeout=timeout) as resp:
                data = json.load(resp)
            if isinstance(data, dict) and data.get("status") == "error":
                raise FatalApiError(f"data.gov.in error: {data.get('message', 'unknown')}")
            return data
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise FatalApiError(f"HTTP {exc.code}: check DATA_GOV_IN_KEY") from None
            if exc.code not in (429, 500, 502, 503, 504):
                raise FatalApiError(f"HTTP {exc.code} from data.gov.in") from None
            last_error = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = type(exc).__name__
        if attempt < retries:
            time.sleep(2**attempt)
    raise RuntimeError(f"data.gov.in failed after {retries + 1} tries ({last_error})")


def fetch_day(api_key: str, day: date, get: Getter, pause: float = 0.5) -> list[dict]:
    """All UP rows for one arrival date, following pagination."""
    rows: list[dict] = []
    while True:
        params = {
            "api-key": api_key,
            "format": "json",
            "limit": PAGE_LIMIT,
            "offset": len(rows),
            "filters[State]": STATE,
            "filters[Arrival_Date]": day.strftime(API_DATE_FORMAT),
        }
        page = get(API_URL, params)
        records = page.get("records") or []
        rows.extend(records)
        total = int(page.get("total") or 0)
        if len(records) < PAGE_LIMIT or (total and len(rows) >= total):
            return rows
        time.sleep(pause)


def load_day(
    api_key: str,
    day: date,
    get: Getter,
    *,
    today: date,
    cache_dir: Path | None,
    pause: float,
) -> list[dict]:
    """Fetch one day, reusing a cached copy for past days that had rows."""
    path = cache_dir / f"{day.isoformat()}.json" if cache_dir else None
    if path and path.exists() and day < today:
        return json.loads(path.read_text(encoding="utf-8"))
    rows = fetch_day(api_key, day, get, pause)
    if path and rows and day < today:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


# ---------------------------------------------------------------- analysis


@dataclass
class Coverage:
    days_with_data: int
    latest: date | None
    longest_gap: int


def coverage(dates: set[date], start: date, end: date) -> Coverage:
    """Days in [start, end] with a row, the newest one, and the longest run of
    days without one. A trailing run counts: it is how stale the mandi is."""
    in_window = {d for d in dates if start <= d <= end}
    gap = longest = 0
    day = start
    while day <= end:
        gap = 0 if day in in_window else gap + 1
        longest = max(longest, gap)
        day += timedelta(days=1)
    return Coverage(len(in_window), max(in_window, default=None), longest)


@dataclass
class Market:
    district: str
    name: str
    any_dates: set[date] = field(default_factory=set)
    crop_dates: dict[str, set[date]] = field(default_factory=lambda: defaultdict(set))
    commodities: set[str] = field(default_factory=set)

    @property
    def target_dates(self) -> set[date]:
        return set().union(*self.crop_dates.values())


def build_markets(rows: list[dict]) -> dict[tuple[str, str], Market]:
    markets: dict[tuple[str, str], Market] = {}
    for row in rows:
        key = (row["district"], row["market"])
        market = markets.setdefault(key, Market(*key))
        market.any_dates.add(row["date"])
        if row["crop"]:
            market.crop_dates[row["crop"]].add(row["date"])
            market.commodities.add(row["commodity"])
    return markets


def _sort_key(m: Market) -> tuple:
    return (DISTRICT_RANK[m.district], m.name.lower())


def pick_markets(
    markets: dict[tuple[str, str], Market], n: int = 10, names: list[str] | None = None
) -> list[Market]:
    """Named markets if given; else nearest districts first, preferring
    markets with target-crop prices in the window."""
    if names:
        wanted = {_norm(x) for x in names}
        return sorted((m for m in markets.values() if _norm(m.name) in wanted), key=_sort_key)
    ranked = sorted(
        markets.values(),
        key=lambda m: (not m.target_dates, DISTRICT_RANK[m.district], -len(m.target_dates), m.name.lower()),
    )
    return ranked[:n]


# ---------------------------------------------------------------- output


def _iso(d: date | None) -> str:
    return d.isoformat() if d else "-"


def write_prices(path: Path, rows: list[dict], picked: set[tuple[str, str]]) -> int:
    cols = ["date", "district", "district_raw", "market", "commodity", "crop", "variety",
            "grade", "min_price", "max_price", "modal_price", "picked"]
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (r["date"], r["district"], r["market"], r["commodity"])):
            if not row["crop"]:
                continue
            out = dict(row, date=row["date"].isoformat(),
                       picked=(row["district"], row["market"]) in picked)
            writer.writerow(out)
            count += 1
    return count


def write_summary(path: Path, picked: list[Market], start: date, end: date, today: date) -> None:
    cols = ["district", "market", "days_with_data", "window_days", "latest", "longest_gap",
            "stale", *[f"days_{c}" for c in CROPS], "commodities_matched"]
    window = (end - start).days + 1
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for m in picked:
            cov = coverage(m.target_dates, start, end)
            writer.writerow([
                m.district, m.name, cov.days_with_data, window, _iso(cov.latest), cov.longest_gap,
                is_stale(cov.latest, today),
                *[len(m.crop_dates.get(c, set()) & _window_set(start, end)) for c in CROPS],
                "; ".join(sorted(m.commodities)),
            ])


def _window_set(start: date, end: date) -> set[date]:
    return {start + timedelta(days=i) for i in range((end - start).days + 1)}


def is_stale(latest: date | None, today: date) -> bool:
    return latest is None or (today - latest).days > STALE_AFTER_DAYS


# ---------------------------------------------------------------- main


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--days", type=int, default=14, help="window length ending today")
    p.add_argument("--count", type=int, default=10, help="mandis to pick")
    p.add_argument("--markets", default="", help="comma-separated market names (skips auto-pick)")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--no-cache", action="store_true", help="refetch every day")
    p.add_argument("--pause", type=float, default=0.5, help="seconds between pages")
    return p.parse_args(argv)


def main(argv: list[str] | None = None, get: Getter = fetch_json, today: date | None = None) -> int:
    args = parse_args(argv)
    api_key = os.environ.get("DATA_GOV_IN_KEY", "").strip()
    if not api_key:
        print("DATA_GOV_IN_KEY is not set. Get a key from your data.gov.in account and set it "
              "in the environment (never in a file in this repo).", file=sys.stderr)
        return 2

    today = today or date.today()
    start = today - timedelta(days=args.days - 1)
    cache_dir = None if args.no_cache else args.out_dir / "agmarknet_cache"

    print(f"Agmarknet pull, {STATE}, {start} .. {today}")
    rows: list[dict] = []
    raw_total = 0
    failed: list[date] = []
    for i in range(args.days):
        day = start + timedelta(days=i)
        try:
            raw = load_day(api_key, day, get, today=today, cache_dir=cache_dir, pause=args.pause)
        except FatalApiError as exc:
            print(f"Stopping: {exc}", file=sys.stderr)
            return 1
        except RuntimeError as exc:
            print(f"  {day}: skipped, {exc}", file=sys.stderr)
            failed.append(day)
            continue
        kept = [r for r in map(normalize, raw) if r]
        raw_total += len(raw)
        rows.extend(kept)
        print(f"  {day}: {len(raw):5d} UP rows, {len(kept):4d} in target districts")

    if raw_total == 0:
        print("\nNo rows at all. Check the TODO(verify) notes at the top of this script: "
              "resource id, State spelling, date format.", file=sys.stderr)
        return 1

    markets = build_markets(rows)

    print("\nStep 1: mandis the API has in the target districts")
    for name, _ in TARGET_DISTRICTS:
        in_district = sorted((m for m in markets.values() if m.district == name), key=_sort_key)
        raw_names = sorted({r["district_raw"] for r in rows if r["district"] == name})
        label = f" (API name: {', '.join(raw_names)})" if raw_names else ""
        print(f"  {name}{label}: {len(in_district) or 'none found'}")
        for m in in_district:
            print(f"    {m.name:<28} any-crop days {len(m.any_dates):2d}, "
                  f"wheat/paddy/mustard/potato days {len(m.target_dates):2d}")

    print("\nCommodity names matched to crops (check these):")
    for crop in CROPS:
        names = sorted({r["commodity"] for r in rows if r["crop"] == crop})
        print(f"  {crop:<8} <- {', '.join(names) or 'none'}")

    names = [x.strip() for x in args.markets.split(",") if x.strip()]
    picked = pick_markets(markets, args.count, names or None)
    if names:
        found = {_norm(m.name) for m in picked}
        missing = [x for x in names if _norm(x) not in found]
        if missing:
            print(f"\nNot in the data: {', '.join(missing)}", file=sys.stderr)
    how = "named with --markets" if names else "nearest districts first, crop data preferred"
    print(f"\nStep 2: picked {len(picked)} mandis ({how})")

    print(f"\nStep 3: coverage of wheat/paddy/mustard/potato prices, {args.days}-day window")
    print(f"  {'mandi':<28} {'district':<19} {'days':>6} {'latest':>11} {'gap':>4}  "
          f"{'W':>2} {'Pd':>2} {'M':>2} {'Pt':>2}")
    fresh = 0
    window = _window_set(start, today)
    for m in picked:
        cov = coverage(m.target_dates, start, today)
        stale = is_stale(cov.latest, today)
        fresh += not stale
        per_crop = " ".join(f"{len(m.crop_dates.get(c, set()) & window):>2}" for c in CROPS)
        flag = "  OLD" if stale else ""
        print(f"  {m.name:<28} {m.district:<19} {cov.days_with_data:>3}/{args.days:<2} "
              f"{_iso(cov.latest):>11} {cov.longest_gap:>4}  {per_crop}{flag}")
    print("  days = days with any target-crop price; gap = longest run of days without one "
          f"(trailing days count); OLD = latest price older than {STALE_AFTER_DAYS} days")

    stamp = f"{start.isoformat()}_{today.isoformat()}"
    prices_path = args.out_dir / f"agmarknet_prices_{stamp}.csv"
    summary_path = args.out_dir / f"agmarknet_summary_{stamp}.csv"
    n_prices = write_prices(prices_path, rows, {(m.district, m.name) for m in picked})
    write_summary(summary_path, picked, start, today, today)

    print(f"\n{fresh} of {len(picked)} picked mandis have a price from the last "
          f"{STALE_AFTER_DAYS} days.")
    if failed:
        print(f"Days that failed to download: {', '.join(d.isoformat() for d in failed)}")
    print(f"Saved {n_prices} price rows to {prices_path}")
    print(f"Saved per-mandi summary to {summary_path}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
