# Spec 04: Mandi Prices + offer checker

**Status:** Draft for Section 7 · **Date:** 2026-10-08
**From:** [AgriSense 2.0 spec](../AgriSense-2.0-spec.md) P0-4. **Builds on:** ADR-004 (adapters, caching, staleness), spec 01 (profile), spec 02 (planner reads the same cache).

## Problem statement

A trader quotes Ramesh a price at the farm gate or the mandi. He has no quick
way to check it against what the nearby mandis paid that week, or to see how
much carrying the crop to a farther mandi would cost him. Agmarknet publishes
the prices, but as tables nobody reads on a phone.

## Goals

1. A guest gets an offer verdict (below / fair / above the modal price, with the gap in ₹ and %) in **3 taps**: crop, offer, check.
2. Prices at the **5 nearest mandis**: min, modal and max per quintal, with the date. Anything **older than 3 days says so** (P0-4).
3. **Net price** after the farmer's own transport rate, remembered on the phone.
4. Prices never block the page: no data shows a clear empty state, never a made-up number.

## Non-goals

- **Price forecasts** or sell-or-hold advice (Phase 3).
- **A default transport rate.** We don't know the farmer's tractor or trolley cost; they enter it, or net price isn't shown.
- **Road distances.** Straight-line distance from the farm pin to the mandi town, labelled as such.
- **Brokers' commission and mandi fees.** Not in Agmarknet; P1 if a source is found.

## Requirements (P0)

**R1. Agmarknet adapter** (`agrisense/market/agmarknet.py`)
- [ ] Daily fetch of Uttar Pradesh prices from data.gov.in into `cached_price`, keeping the 5 target districts; upsert by market, commodity, variety, grade and date.
- [ ] Retries on 429/5xx; a bad key stops the run; the key never appears in errors or logs.
- [ ] Warm-up: `POST /internal/refresh/prices` with a bearer token (GitHub Actions schedule), and `flask agrisense refresh-prices` locally.
- [ ] Tests use a fixture shaped like the API response; the network is blocked.

**R2. Mandis** (`data/mandis.csv`, `scripts/build_mandis.py`)
- [ ] Mandi towns per district with coordinates and sources; matched to Agmarknet market names by name and aliases.

**R3. Board**: 5 nearest mandis by straight-line distance; for each, the latest day in the last 30 with a price: median modal across varieties, widest min–max, date, "N days old" when older than 3 days; net price when a transport rate is set.

**R4. Offer checker**
- [ ] One big ₹/quintal input. Reference price: the nearest mandi with a fresh price, else the nearest with any price.
- [ ] Verdict: below / fair / above, with icon + word + colour, the gap in ₹ and %. **Fair = within `FAIR_BAND_PCT` of the modal price** (config; proposed 5%, for team review). The band is stated in the reasons.
- [ ] Confidence high for a fresh price, low for an old one; source line names the mandi and date.

**R5. Today tab**: price change for the farmer's top planned crop at the nearest mandi with two recent price days.

## Decisions for review

- **`FAIR_BAND_PCT = 5`** is a product choice, not market data. Set it in env; it's shown to the farmer in every verdict.
- **On-read refresh (ADR-004) is not built yet.** A full-state pull is several pages, too slow to do inside a farmer's request. The daily warm-up fills the cache; revisit once the Gate 0 run shows how much data arrives per day.

## Open questions

- **Blocking for real data:** `DATA_GOV_IN_KEY`, and the first live run to confirm the API's field names and date format (Gate 0 script). *Team*
- **Not blocking:** the mandi list comes from a 1996 Lok Sabha table; confirm it against the market names Agmarknet reports. Shikarpur and Chharra have no coordinates yet. *Team*
- **Not blocking:** the warm-up time of day depends on Agmarknet's publishing lag (Gate 0). *Team*
