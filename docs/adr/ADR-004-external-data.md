# ADR-004: External data — adapters, caching, staleness, failure

**Status:** Proposed
**Date:** 2026-10-07
**Deciders:** AgriSense team (4) — sign-off below

## Context

Phase 1 tools depend on three outside sources and several static datasets:

| Source | Used by | Nature |
|---|---|---|
| Agmarknet via data.gov.in API | Mandi Prices, offer checker, Crop Planner profit, Today | Daily, published with a lag; API key; limits not documented to us yet |
| Open-Meteo forecast API | Spray & Irrigation Advisor, Today | Hourly; no key; free tier is **non-commercial**, < 10,000 calls/day, < 5,000/hour, < 600/min, CC-BY 4.0 attribution ([terms](https://open-meteo.com/en/terms)) |
| Scheme rules (`data/schemes.yaml`) | Scheme Finder | Curated by the team from official pages; changes yearly |
| Static tables in `data/` | All tools | District centroids, mandi coordinates, KVK contacts, crop names, area units, fertilizer RDF/prices, district crop economics |

Requirements: P0-4 ("if data is older than 3 days, say so"), P0-5 (72-hour
forecast), P0-8 (source + date on every answer), CLAUDE.md (never invent
numbers; config from env), tests run offline, and Render's free web service
has no background worker or free cron (ADR-002).

The Gate 0 script (`scripts/check_agmarknet.py`) is the first real contact
with the Agmarknet API; its findings (freshness, gaps, field names, date
format) feed this ADR's open items.

## Decision

**One adapter module per external source behind a common interface;
read-through DB caches with per-source TTL; a daily GitHub Actions warm-up for
prices; staleness computed and shown, never hidden; static data as versioned
files with `source` and `as_of`; recorded fixtures and no network in tests.**

### Adapter contract

```python
# agrisense/data/base.py (Section 2 creates it; shape fixed here)
@dataclass
class SourceInfo:
    name: str             # "Agmarknet", "Open-Meteo", "your soil card"
    as_of: date | datetime  # the data's own date, not fetch time
    fetched_at: datetime | None
    stale: bool
    note: str | None      # e.g. "couldn't refresh, showing 5 Oct"

@dataclass
class Result[T]:
    data: T | None        # None = no data at all
    source: SourceInfo
```

Every adapter exposes typed read functions (e.g. `prices_for(markets, crops,
since)`, `forecast(lat, lon)`) that return `Result`. Tools turn `SourceInfo`
into the trust layer's `sources[]` and lower `confidence` when `stale`.

### Per-source policy

| | Agmarknet | Open-Meteo | Schemes YAML | Static `data/*.csv` |
|---|---|---|---|---|
| Module | `market/agmarknet.py` | `weather/openmeteo.py` | `schemes/catalog.py` | `agrisense/data/static.py` |
| Cache | `cached_price` rows | `cached_weather` per 0.01° cell | loaded at startup | loaded at startup |
| Refresh | Daily warm-up + on-read if today's rows missing | On read when `valid_until` passed (TTL 1 h, spec) | On deploy | On deploy |
| Request timeout on read path | 4 s, then serve cache | 4 s, then serve cache | n/a | n/a |
| Stale when | price date > 3 days old (P0-4) | **TODO** threshold for review; propose: fetched > 3 h ago | `last_checked` > 12 months, or `verified: false` | `as_of` shown; no auto-stale |
| Retries | 3, backoff on 429/5xx | 2, backoff on 429/5xx | — | — |
| Secrets | `DATA_GOV_IN_KEY` env | none | none | none |

**Price warm-up:** a scheduled GitHub Actions workflow calls
`POST /internal/refresh/prices` once a day with a bearer token
(`REFRESH_TOKEN`, env + Actions secret). It also wakes the free Render service
and Neon compute ahead of morning use. Render cron jobs are not free, so this
avoids a paid service. **TODO:** set the time once Gate 0 shows when
Agmarknet rows for the target mandis usually appear.

**Weather cache key** is the pin rounded to 0.01° so nearby farms share one
call and no exact location is stored with weather data. At pilot scale this
stays far under Open-Meteo's daily limit.

### When a source is down or empty

1. Cached data exists → show it with its date and a plain note ("आज का भाव नहीं
   मिला, 5 अक्टूबर का दिखा रहे हैं / couldn't get today's price, showing 5 Oct"),
   `stale=True`, confidence capped at *medium* (*low* if older than the stale
   threshold).
2. No cached data → the tool shows an empty state that says what's missing,
   links to the official source (Agmarknet, IMD/Meghdoot) and the Ask-an-expert
   card. **Never** a fabricated or interpolated number.
3. Partial data (e.g. 3 of 5 mandis) → show what exists, list the missing ones.
4. Crop Planner without prices → rank on suitability and water/risk only, hide
   the ₹/acre range, and say why.

### Static data conventions

- One CSV/YAML per dataset in `data/`, with `source` and `as_of` columns (or
  per-file header for YAML). Missing verified values are blank + `TODO` in a
  `notes` column, never guessed (CLAUDE.md).
- A test loads every file, checks required columns and fails on unknown
  district/crop codes.
- `data/schemes.yaml` entries carry `verified` and `last_checked`. **In
  production, only `verified: true` schemes are shown**; unverified ones show
  in dev and on `/styleguide` so the team can review them.

### Tests

- `tests/fixtures/agmarknet/*.json` and `tests/fixtures/openmeteo/*.json`
  recorded from real responses (Gate 0 run), trimmed, with keys/IPs removed.
- `scripts/record_fixtures.py` refreshes them on purpose, never in CI.
- Network is blocked in the test suite (a fixture that patches socket
  connect); adapters take an injectable HTTP getter, as the Gate 0 script does.
- Each policy above has a test: TTL hit/miss, stale flag at the boundary,
  timeout falls back to cache, empty cache gives the empty state.

## Options Considered

### Option A: Adapters + read-through DB cache + scheduled warm-up — recommended

| Dimension | Assessment |
|---|---|
| Complexity | Medium: one module per source, shared contract. |
| Cost | Free (GitHub Actions schedule; DB tables already exist). |
| Resilience | Good: cache survives source outages and app restarts. |
| Freshness | Daily prices are as fresh as Agmarknet publishes. |

**Pros:** works on free hosting; uniform trust/staleness handling; offline tests.
**Cons:** first request after a long idle may pay a fetch (bounded by 4 s
timeout); warm-up depends on GitHub Actions schedule reliability.

### Option B: Call sources live on every request, no cache

| Dimension | Assessment |
|---|---|
| Complexity | Low. |
| Resilience | Poor: any outage breaks the tool; slow on 4G. |
| Limits | Burns API quota; Open-Meteo may block us. |

**Pros:** always newest data. **Cons:** fails P0-4/P0-9 on bad days; no history.

### Option C: Nightly batch ETL into the DB only (no on-read fetch)

| Dimension | Assessment |
|---|---|
| Complexity | Medium–high: needs a reliable scheduler and backfill logic. |
| Freshness | Fine for prices; wrong for weather (needs hourly). |
| Cost | Render cron is paid; GitHub Actions can do it but runs long jobs on CI minutes. |

**Pros:** request path never touches the network. **Cons:** weather doesn't fit;
one missed run means a day of stale prices with no self-healing.

## Trade-off Analysis

B fails the honesty and performance requirements the first time a source is
slow. C suits prices but not hourly weather. A takes C's daily pull for prices
(as a warm-up, not the only path) and adds on-read refresh with a strict
timeout, so every tool degrades to "cached + labelled" instead of "broken".
The common `SourceInfo` contract is what makes the trust layer (P0-8)
uniform across tools rather than re-implemented in each.

## Consequences

- **Easier:** every tool gets source/date/staleness for free; outages are a
  label, not an error page; tests are fast and offline.
- **Harder:** two cache tables to prune; fixtures must be refreshed when an
  API changes shape; a `/internal/refresh/*` endpoint to protect.
- **Licensing:** Open-Meteo free use is non-commercial with CC-BY 4.0
  attribution: add attribution on result cards' source line and on `/about`.
  If AgriSense ever becomes commercial, move to their paid API.
- **Revisit if:** data.gov.in rate limits or freshness from Gate 0 are poor
  (consider eNAM or state mandi board feeds), Bhashini/Sentinel-2 arrive in
  Phase 2 (each gets its own adapter + ADR), or the pilot outgrows free limits.

## Implementation notes

- **Section 7 (2026-10-08):** the Agmarknet adapter, cache upsert, the
  `/internal/refresh/prices` warm-up (bearer token; 404 when no token is set)
  and `flask agrisense refresh-prices` are built. **On-read refresh is
  deferred:** a full Uttar Pradesh pull is several pages per day, too slow to
  run inside a farmer's request even with a 4 s timeout. Pages read the cache
  and label old prices; the daily warm-up fills it. Revisit after the Gate 0
  run shows the real data volume.

## Open items (filled from the Gate 0 Agmarknet run)

- [ ] Confirm resource id, field names, `Arrival_Date` format, max page size.
- [ ] data.gov.in rate limit per key (not documented to us yet).
- [ ] Typical publish lag for the target mandis → warm-up time.
- [ ] Which mandis have usable data (feeds `data/mandis.csv`).
- [ ] Weather stale threshold (proposed 3 h) and spray/irrigation thresholds: for review in Section 8, with sources.

## Action Items

1. [ ] Team sign-off.
2. [ ] Section 2: `agrisense/data/base.py` with `SourceInfo`/`Result`, the socket-blocking test fixture, `REFRESH_TOKEN` and `DATA_GOV_IN_KEY` in config + deploy checklist.
3. [ ] Section 7: Agmarknet adapter on this contract, reusing Gate 0 parsing; GitHub Actions daily warm-up.
4. [ ] Section 8: Open-Meteo adapter; attribution on the source line.
5. [ ] Section 9: schemes YAML loader with `verified` filter in production.

## Sign-off

| Name | Role | Agree / Disagree | Date |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |
