# Spec 01: Guest-first farm profile + trust layer

**Status:** Draft for Section 4 · **Date:** 2026-10-08
**From:** [AgriSense 2.0 spec](../AgriSense-2.0-spec.md) P0-1 (guest-first access and farm profile) and P0-8 (trust layer on every answer).
**Builds on:** ADR-003 (data model, guest profile JSON), ADR-002 (DB), Section 2 (phone + PIN, staff-assisted reset), Section 3 (`result_card` and other macros).

## Problem statement

Every Phase 1 tool needs the same few facts about a field: where it is, how
big, how it's watered, and what the soil card says. Today the farmer has to
type seven lab numbers before getting anything. Ramesh doesn't have them to
hand, won't sign up before seeing value, and won't trust an answer that
doesn't say where it came from. Without one shared profile, every tool asks
again. Without a trust layer, every tool invents its own way of showing (or
hiding) how sure it is.

## Goals

1. A first-time guest sets up a field in **under 2 minutes** in Hindi on a 360 px phone, with no account (spec Phase 1 goal 1).
2. **Every tool reads the same profile.** Nothing is typed twice across the five tools.
3. Every tool result carries **reasons, sources with dates, confidence and estimated fields**, rendered the same way (P0-8).
4. Missing soil values never block an answer and are never shown as measured. They are filled from a sourced district default, or the answer says it isn't known.
5. "Save my farm" moves the guest's field and last results to an account with **no retyping**.

## Non-goals

- **Several plots per farm.** Phase 1 has one plot. The schema already supports many (ADR-003), so this is a UI change later (P1).
- **Drawing the field boundary.** Phase 2 field health. Only a pin now.
- **Reading a Soil Health Card photo (OCR).** Typing 5 numbers is enough to test the flow; OCR is a separate bet.
- **Making up district soil defaults.** If no sourced default exists, the value is "not known". We don't estimate it ourselves (CLAUDE.md).
- **SMS login or OTP.** Phone + PIN only, as decided in ADR-003.

## User stories

**Ramesh (guest farmer)**
- As Ramesh, I want to mark my field by dropping a pin or pressing "use my location" so that I don't have to know coordinates.
- As Ramesh without GPS or a map signal, I want to pick my district from a list so that I can still use the tools.
- As Ramesh, I want to enter my field size in the unit I use so that I don't convert anything myself.
- As Ramesh without a soil card, I want to skip the soil step so that I still get an answer, clearly marked as using estimates.
- As Ramesh, I want my field remembered on my phone without an account so that the next tool already knows it.
- As Ramesh, I want to see why the app says something and where the numbers come from so that I can judge it against my dealer's word.
- As Ramesh, when the app isn't sure, I want a person to call so that I'm not left with a guess.

**Ramesh (saving his farm)**
- As Ramesh, I want "Save my farm" to keep everything I already entered so that I don't start again.
- As Ramesh, I want to know what is kept about me before I save, and to delete it all later, so that I stay in control (DPDP Act 2023).

**Pooja (KVK/FPO staff)**
- As Pooja, I want to set up a field for a farmer on my phone quickly so that I can show them a result on the spot.

## Requirements

### P0: must ship

**R1. Profile wizard, 4 steps at most** (`/field/setup`)
- [ ] Step 1, *Where*: a map with a draggable pin (Leaflet + OpenStreetMap tiles, **loaded only on this step**, ADR-005), a "Use my location" button (browser GPS), and a "Choose district instead" list.
- [ ] Step 2, *Area*: number + unit (acre / bigha / hectare). Bigha is accepted only where `data/area_units.csv` has a sourced size for the district; otherwise the step says so and asks for acre or hectare.
- [ ] Step 3, *Water*: tubewell / canal / rain-fed / bought water / other, as big tappable choices.
- [ ] Step 4, *Soil card (optional)*: N, P, K (kg/ha), pH, organic carbon (%), and the card date. "Skip" is as prominent as "Save".
- [ ] Every step works at 360 px in Hindi with 48 px targets. Back keeps what was entered.
- [ ] Inputs are validated on the server; errors show next to the field in the user's language.

**R2. Guest profile on the device**
- [ ] Stored in `localStorage` under `agrisense.profile`, schema `v: 1` (ADR-003).
- [ ] One small script sends it with every HTMX request and every form post (`profile` field), and saves the updated profile the server returns.
- [ ] The server never stores a guest profile. It validates, normalises and returns it.
- [ ] If storage is unavailable (private mode), the wizard still works for the current visit and says the field won't be remembered.

**R3. District from location**
- [ ] Offline table of UP and Haryana districts with coordinates, Hindi and English names, and a source per row (`data/districts.csv`, built from Wikidata).
- [ ] The nearest district within 100 km of the pin is suggested and shown for confirmation ("Looks like Bulandshahr. Change?"). Further than that: ask the farmer to choose.
- [ ] Picking a district without a pin uses its listed coordinates, and the location is marked *estimated*.

**R4. District defaults and estimated fields**
- [ ] `data/district_soil_defaults.csv` holds per-district N, P, K, pH, OC with a source and date per row. A value is used only if its row has a source.
- [ ] A missing soil value is filled from the district default when one exists, and listed in `estimated_fields`. Otherwise it stays unknown and is listed as *not known*.
- [ ] No default values ship without a cited source. (Today the file has the target districts with blanks and TODOs.)

**R5. Trust layer contract**
- [ ] Every tool returns a `TrustResult`: `value`, `reasons[]`, `sources[{name, date}]`, `confidence` (high / medium / low), `estimated_fields[]`.
- [ ] Rule: if any input the result depends on is estimated, confidence is at most *medium*. If a required input is unknown, at most *low*.
- [ ] `result_card` renders every `TrustResult`. The "Ask an expert" link goes to `/expert`.
- [ ] `/expert` shows the Kisan Call Centre (1800-180-1551) with tap-to-call, and the farmer's district KVK where we have a sourced entry. Address only until phone numbers are verified.

**R6. Save my farm (account) migrates the guest profile**
- [ ] `/farm/save` posts the guest profile along with phone, PIN and consent.
- [ ] One transaction creates `app_user`, `farm`, `plot` and `soil_card` (if any), and imports `last_results` as `event` rows with `source='import'`.
- [ ] Consent text is final, versioned (`consent_version`), and shown before saving: what is kept, why, who sees it, how to delete.
- [ ] After saving, the browser keeps its copy for offline use.

**R7. Saved farms stay in sync**
- [ ] A logged-in user editing the wizard updates their DB rows. A new soil card becomes the current one; the old one is kept.
- [ ] `GET /api/profile` returns the saved profile in the guest-profile shape, so the browser copy can be refreshed after login.

**R8. Delete my farm**
- [ ] A logged-in user can delete their account and all farm data after re-entering their PIN. Events, soil cards, plots, farm and user rows are removed, and the session ends.

### P1: fast follows

- More than one plot per farm, with a plot switcher.
- Edit a saved farm offline and sync later.
- Photo of the soil card stored with the profile (with consent) for a helper to read.
- Hindi voice prompts on each wizard step.

### P2: design for, don't build

- Field boundary polygon (`plot.boundary_geojson`) for Sentinel-2.
- Sensor node linked to a plot.
- FPO/KVK operator who owns several farmers' farms (ADR-003 open question).
- AgriStack Farmer ID link.

## Success metrics

| Metric | Type | Target | Stretch | How |
|---|---|---|---|---|
| Time from opening `/field/setup` to a finished profile, guest, Hindi | Leading | < 2 min | < 60 s | Stopwatch in the 8 moderated tests; Playwright timing as a floor |
| Guests who finish the wizard after starting it | Leading | 70% | 85% | Privacy-light count of step-reached events (no location, no phone) |
| Results shown with every trust field present | Quality | 100% | — | Contract test on every tool |
| Farmers who say they understand why a result was given | Leading | 60% | 75% | Post-task question in moderated tests |
| Guests who later "Save my farm" | Lagging | Measured, no target yet | — | Pilot count (spec's riskiest-assumptions table) |

## Open questions

- **Blocking for real defaults:** the source for district soil defaults. Candidates are the Soil Health Card portal's district summaries, or KVK/state soil-testing lab reports. *Data / team*
- **Not blocking:** KVK phone numbers for Gautam Buddh Nagar and Bulandshahr. Addresses are from ICAR records; phones need a call or the ICAR KVK portal. *Team*
- **Not blocking:** bigha size per target district. *Team, via the revenue office or KVK*
- **Not blocking:** whether to send step-reached counts at all in Phase 1, or only use the moderated tests. *Team (privacy)*
- **Blocking for the pilot:** a contact for data questions in the consent text (DPDP Act 2023 grievance contact), and faculty review of that text. *Team / faculty*
- **Not blocking:** Wikidata lists 76 UP and 21 Haryana districts against the official 75 and 22; reconcile with the LGD directory before relying on the list for anything beyond suggestions. *Data*

## Implementation notes (Section 4)

- District suggestions come from Wikidata's single point per district, often the headquarters. Near a district border the suggestion can be wrong, which is why the farmer always confirms it.
- In Hindi, the map marker is "निशान", not "पिन", so it isn't confused with the login PIN.
- Logging out removes the farm from the phone's storage, because phones are often shared.

## Timeline

- Week 2 of Phase 1 (roadmap Section 4). Depends on Sections 2 and 3; Sections 5–9 depend on this.
- Data gaps don't block the build: code paths for "default missing" and "phone unknown" ship and are tested now, and the data fills in later.
