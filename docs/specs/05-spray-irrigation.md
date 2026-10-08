# Spec 05: Spray & Irrigation Advisor

**Status:** Draft for Section 8 · **Date:** 2026-10-08
**From:** [AgriSense 2.0 spec](../AgriSense-2.0-spec.md) P0-5. **Builds on:** ADR-004 (adapters, cache), spec 01 (profile, trust layer).

## Problem statement

Ramesh sprays in the morning and a shower at noon washes it off, or the wind
carries it to the neighbour's field. He irrigates, and it rains that night.
Each mistake costs chemical, diesel and water. He needs a plain yes / careful /
no for the next three days, with the reason, for his own field.

## Goals

1. For a set-up field: 3 days, each with a spray verdict and an irrigation verdict, icon + word + colour, and a one-line reason ("Rain 70% likely around 3 pm").
2. **Every threshold is data**, with its source or marked as a proposal for review (`data/weather_thresholds.csv`).
3. The Today tab's lead card shows today's verdicts.
4. The 10 written cases in `data/weather_cases.json` give the expected verdicts.

## Non-goals

- **Which chemical to spray, or doses.** That's the label and the KVK; Crop Doctor (Phase 2) names active ingredients only.
- **Crop-stage-based irrigation schedules.** Not collected yet, and they need cited stage tables. Irrigation advice uses rain only and says so.
- **Soil-moisture sensing.** Phase 2: `rules.irrigate_day` takes `soil_moisture` as the hook.

## Requirements (P0)

**R1. Open-Meteo adapter** (`agrisense/weather/openmeteo.py`): hourly rain probability, rain, wind at 10 m, humidity, temperature; 3 forecast days + 2 past days; Asia/Kolkata time; cached per 0.01° cell for 1 hour; on failure, the cache labelled old, or a clear "couldn't get the forecast" with the IMD Meghdoot pointer. Credit "Open-Meteo.com (CC BY 4.0)".

**R2. Rules** (`agrisense/weather/rules.py`, pure functions)
- Spray: each hour in the morning and evening windows is usable when the wind is inside the band and neither it nor the next N hours look rainy. Any usable hour → good (best window named); only still-air hours → careful; otherwise → don't (rain or wind named). Past hours are skipped.
- Irrigation: rain forecast for the day and the next ≥ hold → hold; ≥ check → check the soil first; rain in the 2 days before ≥ recent → hold; otherwise "irrigate if your crop needs it".

**R3. Screens**: `/weather` (3 days) and the Today lead card, both with the trust layer; confidence at most medium while any threshold is a proposal; low if the forecast is old.

## Thresholds (for your review)

| Key | Value | Status | Source / note |
|---|---|---|---|
| Spray wind band | 6–19 km/h | **cited** | Victoria Dept of Health, Beaufort scale for pesticide spraying (via search excerpt) |
| Rain-free hours after spraying | 3 h | **cited** | KIRAN agromet advisory, Manipur 2013: "sky clear for at least 2–3 hours" |
| Spray windows | 6–9 am, 3–6 pm | **cited** (start/end of evening proposed) | KAU agromet bulletins: before 9 am or after 3 pm |
| Rainy hour | ≥ 50% chance or ≥ 0.5 mm | **proposed** | No Indian figure found; bulletins say "when rain is expected" |
| Irrigation hold | ≥ 10 mm today + tomorrow | **proposed** | IMD/ICAR-CRIDA bulletins advise postponing irrigation when rain is forecast, without a mm figure |
| Irrigation check | ≥ 2 mm | **proposed** | as above |
| Recent rain hold | ≥ 10 mm in the 2 days before | **proposed** | as above |
| Forecast counts as old | > 3 h | **proposed** | ADR-004 |

Change a value in the CSV; no code changes are needed.

## Open questions

- **Blocking before the pilot:** review the proposed cut-offs with the KVK; ideally replace them with cited district advisory figures. *Team / KVK*
- **Not blocking:** add crop and sowing date to the profile so irrigation can use critical stages (needs a cited stage table). *Team*
