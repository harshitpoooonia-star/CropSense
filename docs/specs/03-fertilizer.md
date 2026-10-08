# Spec 03: Fertilizer Calculator

**Status:** Draft for Section 6 · **Date:** 2026-10-08
**From:** [AgriSense 2.0 spec](../AgriSense-2.0-spec.md) P0-3. **Builds on:** spec 01 (profile, trust layer), spec 02 (planner's "Fertilizer for this crop").

## Problem statement

At the dealer's counter Ramesh is told how many bags to buy by the person
selling them. His Soil Health Card already prints a dose for his field, but
in kg of nutrient or product per hectare, which he can't turn into bags for
his 2.5 acres. He needs the number of bags of urea, DAP (or SSP) and MOP, the
cost, and when to apply them, from a source that sells nothing.

## Goals

1. Bags per product, kg, and ₹ total for the farmer's field area, in under 2 minutes, as a guest, in Hindi.
2. **The farmer's own card dose comes first**; a cited state dose is the fallback; otherwise "ask your KVK", never a guess.
3. All 10 worked cases in `data/fert_cases.csv` within 1 bag (spec P0-3), and within 0.02 bag of exact arithmetic.
4. Every result shows the dose source, product prices with their dates, and a confidence badge.

## Non-goals

- **Inventing doses.** Crops without a cited dose say so and point to the KVK.
- **Adjusting the standard dose for soil-test ratings** (low +25% / high −25%). Sources disagree on the cut-offs and one calls the rule arbitrary; off until a UP source is cited. The card's own dose already reflects the soil test.
- **Brands.** Products are named by type (urea, DAP, MOP, SSP) only.
- **Micronutrients and organic manure doses.** Phase 2 with sourced data.

## User stories

- As Ramesh with a soil card, I want to copy its dose and get bags for my field so that I buy exactly that.
- As Ramesh without a card, I want the standard dose for my crop turned into bags, clearly marked as not adjusted for my soil.
- As Ramesh, I want the choice of SSP instead of DAP so that I can buy what the dealer has.
- As Ramesh, I want to know which bags go in at sowing and which later, where a source says so.
- As Ramesh, I want to share the list on WhatsApp to take to the shop.

## Requirements (P0)

**R1. Data, cited per row** (`verified=false` until a person checks)
- [ ] `data/fert_rdf.csv`: crop, condition, N/P₂O₅/K₂O kg/ha (low–high where a source gives a range), split schedule where cited, source.
- [ ] `data/fert_products.csv`: nutrient content (Fertiliser (Control) Order), bag size, price per bag with its date and source.
- [ ] `data/soil_rating_adjust.csv`: the adjustment table, inactive, with the reason.

**R2. Calculator** (`agrisense/fertilizer/calc.py`, pure functions, no Flask)
- [ ] Standard dose: P from DAP first and subtract its N; K from MOP; the rest of N from urea. SSP option instead of DAP.
- [ ] Card dose: product kg per hectare or per acre, scaled to the field.
- [ ] Bags (to 0.1), kg, bags to buy (whole bags), ₹ total for the bags to buy.
- [ ] Split by stage only where the source gives one; otherwise say "no cited split".

**R3. Screen** (`/fertilizer`, prefilled from the planner's link and the profile's area)
- [ ] Crop, condition (where the source has several), area with unit, card-or-standard, DAP-or-SSP.
- [ ] Result: `bag_icons` per product, ₹ total, split, trust layer, Share to WhatsApp.

**R4. Tests**: the 10 cases, product maths, card scaling, uncited-crop path, HTTP and a Playwright flow at 360 px in Hindi.

## Open questions

- **Blocking for launch:** a person checks each dose row and price against its source; wheat's UP page is cited from a search excerpt because its TLS certificate had expired. *Team*
- **Not blocking:** cited doses for mustard and maize in western UP (SVPUAT package of practices). *Team / KVK*
- **Not blocking:** MOP and SSP MRPs are open; the table uses the 2023-24 official averages. Show the bag's printed MRP? *Team*
