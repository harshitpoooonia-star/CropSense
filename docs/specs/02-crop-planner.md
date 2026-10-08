# Spec 02: Crop Planner v2

**Status:** Draft for Section 5 · **Date:** 2026-10-08
**From:** [AgriSense 2.0 spec](../AgriSense-2.0-spec.md) P0-2. **Builds on:** spec 01 (farm profile, trust layer), ADR-004 (external data).

## Problem statement

Ramesh has to choose what to sow 3–4 weeks before the season, mostly on the
input dealer's word. The 1.x tool asked for 7 lab numbers and returned one
crop name from a Kaggle classifier that knows no wheat, mustard, potato or
sugarcane, which are the main crops around Bulandshahr. He needs crops
ranked by what they are likely to earn on *his* field this season, with the
reasons and sources shown, and a plain "we don't know" where data is
missing.

## Goals

1. For a farmer with a set-up field, show the **top 3 crops for the chosen season** in under 2 seconds, in Hindi, as a guest.
2. Every card shows a **₹/acre range** when prices exist, **water need**, **risk**, 2–3 **reasons**, sources with dates and a confidence badge.
3. **Top-3 contains the crop a good local farmer chose in ≥ 70% of 30 real records** (spec target, checked in week 8).
4. **No unsourced number** appears on a card: every yield, cost, price and water figure traces to a cited row.

## Non-goals

- **Price forecasting.** Profit uses recent prices, or MSP clearly labelled, not predictions.
- **Variety and sowing-date advice.** That's the crop calendar (Phase 2).
- **Accuracy on the Kaggle split as the headline.** It's a secondary number only.
- **Crops outside the district's own record.** If the district's statistics don't show a crop in that season, it isn't offered (it can still be asked about with "Why not?").

## User stories

- As Ramesh, I want to pick kharif, rabi or zaid and see three crops for my field so that I can compare before I talk to the dealer.
- As Ramesh, I want to see the likely earnings per acre as a range so that I don't mistake an estimate for a promise.
- As Ramesh with a rain-fed field, I want thirsty crops marked as risky for me so that I don't sow something I can't water.
- As Ramesh, I want to ask "why not paddy?" so that I understand what the app thinks of the crop I had in mind.
- As Ramesh, I want to go from a crop to its fertilizer bags in one tap.
- As Pooja, I want the reasons in plain words so that I can explain them to a farmer.

## Requirements

### P0

**R1. Data, cited per row**
- [ ] `data/crop_seasons.csv`: crops each district grows per season (DES APY area, ≥ 100 ha on average over the last 3 years, series running to 2018-19 or later).
- [ ] `data/district_crop_economics.csv`: yield range per acre over the last 5 years (DES APY / UPAG), cost per acre (DES Cost of Cultivation, Uttar Pradesh, A2+FL, latest year), water need (FAO, MAUSAM), all with sources. Every row `verified=false` until a person checks it.
- [ ] `data/msp.csv`: MSPs for the current marketing seasons, with source.
- [ ] `data/district_climate.csv`: season climate normals from Open-Meteo history (inputs to the legacy model).
- [ ] Built by `scripts/build_crop_data.py` and `scripts/build_climate.py`, so anyone can rebuild them.

**R2. Suitability model, honestly scoped**
- [ ] Retrained without PCA: StandardScaler → RandomForest, stratified 5-fold CV, calibrated probabilities (`CalibratedClassifierCV`), saved with a version string.
- [ ] Used only when N, P, K and pH are known and every input is inside the training range; otherwise the card says it wasn't used.
- [ ] Low weight in the score, and labelled "public dataset, not local farms".

**R3. Ranking**
- [ ] Profit per acre = yield range × price − cost. Price: recent mandi modal prices when the cache has them (Section 7), otherwise MSP (labelled "MSP, not a mandi price"), otherwise unknown.
- [ ] Water fit: the crop's water need against the field's irrigation source.
- [ ] Score combines profit, water fit and suitability; a missing factor drops out and lowers confidence. With no price at all, crops aren't ranked by profit and the page says so.

**R4. Cards**
- [ ] Top 3: ₹/acre range (or "not known"), water need, risk, 2–3 reasons, sources with dates, confidence, Ask an expert, Share on WhatsApp, "Fertilizer for this crop".
- [ ] Confidence: at most *medium* while any figure is unverified or estimated, or the cost data is older than 2 years; *low* without a price.

**R5. Why not <crop>?**
- [ ] Any crop in our list: says if it isn't grown in that district and season, or which factors put it below the top 3.

**R6. Validation**
- [ ] `scripts/validate_planner.py` reads `data/farm_records.csv` and prints the top-3 hit rate; the Kaggle test accuracy is printed second.

### P1

- Per-mandi price history for a price-risk measure (needs Section 7 data).
- Cost of cultivation per district (only state averages exist today).
- Intercropping and ratoon sugarcane.

### P2

- Sell-or-hold price range (spec Phase 3).
- Retrain suitability on our own farm records once there are enough.

## Success metrics

| Metric | Target | How |
|---|---|---|
| Top-3 hit rate on real records | ≥ 70% of 30 | `validate_planner.py`, week 8 |
| Cards with every trust field | 100% | contract test |
| Farmers who'd act on the card (Gate 0) | ≥ 5 of 8 | interview kit |
| Time to result, guest | < 2 s server time | test timing |

## Open questions

- **Blocking for launch:** a person checks each `verified=false` row (yields, costs, water, MSP) against its source. *Team*
- **Not blocking:** cost data is 2021-22 (latest in the DES series). Should cards show it as-is (current choice) or adjust with an index? Adjusting would add our own estimate. *Team*
- **Not blocking:** the season months used for climate normals are an assumption (kharif Jun–Oct, rabi Nov–Mar, zaid Mar–Jun). *Data*
