# ADR-003: Data model — farm profile as core entity + per-plot event log

**Status:** Proposed
**Date:** 2026-10-07
**Deciders:** AgriSense team (4) — sign-off below

## Context

Today's schema (`app.py`) is `User` (username, email, hashed password),
`Recommendation` (7 typed numbers + predicted crop), `CropData` (a copy of
`data.csv` loaded into the DB) and `Location` (city weather, never populated).
It has no farm, no location, no season and no history beyond crop guesses.

2.0 requirements that shape the model:

- **P0-1 Guest-first:** every tool works without an account. The guest profile
  lives on the device; "Save my farm" creates an account (phone + 4-digit PIN)
  and migrates it.
- **P0-2…P0-6:** every tool reads the same profile (pin, area + unit,
  irrigation source, optional soil card values); missing values come from
  district defaults and are flagged *estimated*.
- **P0-8 Trust layer:** every result carries reasons, sources with dates,
  confidence and estimated fields.
- **P2 architecture note:** "Every tool reads from [the farm profile] and
  writes to a per-plot event log, so the diary, reports and FPO views come
  later without schema changes."
- **Privacy (spec, DPDP Act 2023):** no names or phone numbers in analytics;
  consent on first save.

## Decision

1. **Core entities:** `user` → `farm` → `plot`, with `soil_card` per plot.
2. **One append-only `event` table per plot** for everything that happens on
   it: tool results, and later expenses, sales, sensor readings, diary notes.
   `kind` + versioned JSON `payload`; new kinds need no migration.
3. **Caches** (`cached_price`, `cached_weather`) are separate, shared,
   non-personal tables, not events.
4. **Guest profile** is a versioned JSON object in `localStorage`, sent with
   each tool request; the server never stores it until "Save my farm".
5. **Phone numbers are not stored in clear.** Login looks up a keyed hash
   (HMAC-SHA256 with a server-side pepper from env) of the normalised number;
   the PIN is hashed with werkzeug.
6. **Legacy tables are not migrated.** `Recommendation`, `CropData` and
   `Location` are dropped in Section 2 (see Consequences).

## Schema (Phase 1)

Types are SQLAlchemy generic (ADR-002). `id` columns are integer PKs; every
table has `created_at` / `updated_at` (UTC). Canonical units are stored;
the unit the farmer typed is kept for display.

```text
app_user                                       -- "user" is reserved in Postgres
  id
  phone_hmac          text, unique, not null   -- HMAC-SHA256(pepper, E.164 number)
  pin_hash            text, not null           -- werkzeug generate_password_hash
  role                text  'farmer' | 'helper'  -- helper = KVK/FPO staff, can start PIN resets
  locale              text  'hi' | 'en'
  consent_at          datetime, not null       -- DPDP consent on first save
  consent_version     text                     -- which consent text they accepted
  pin_reset_required  bool  default false
  pin_reset_code_hash text  nullable           -- one-time 6-digit code, hashed
  pin_reset_expires_at datetime nullable       -- 30 min after the helper starts it
  pin_reset_by_id     fk app_user nullable     -- which helper started it (audit)
  last_login_at       datetime

login_attempt                                  -- for 5 tries / 15 min rate limit
  id, kind ('login'|'register'|'pin_reset'), phone_hmac, ip_hash, attempted_at, success bool
  (rows older than 24 h deleted by the app)

farm
  id
  user_id             fk user, not null
  name                text  nullable           -- farmer's own label, e.g. "nahar wala khet"
  state               text                     -- from district lookup
  district_code       text                     -- key into data/districts.csv
  lat, lon            numeric(8,5)             -- the pin; personal data, never logged

plot
  id
  farm_id             fk farm, not null
  label               text
  area_ha             numeric(10,4), not null  -- canonical
  area_input_value    numeric(10,4)            -- what they typed
  area_input_unit     text  'acre' | 'bigha' | 'hectare' | ...
  irrigation_source   text  'tubewell' | 'canal' | 'rainfed' | 'purchased' | 'other'
  current_crop        text  nullable           -- crop code from data/crops.csv
  season              text  nullable  'kharif' | 'rabi' | 'zaid'
  sowing_date         date  nullable
  boundary_geojson    json  nullable           -- Phase 2 field health

soil_card
  id
  plot_id             fk plot, not null
  sampled_on          date  nullable
  n_kg_ha, p_kg_ha, k_kg_ha, ph, oc_pct, ec_ds_m   numeric, all nullable
  extra               json  nullable           -- S, Zn, Fe, ... as printed on the card
  source              text  'shc' | 'lab' | 'sensor_estimate'
  is_current          bool                     -- one current card per plot

event                                          -- append-only, per plot
  id
  plot_id             fk plot, not null
  kind                text, not null           -- 'planner.result', 'fertilizer.result',
                                               -- 'market.offer_check', 'weather.verdict',
                                               -- 'schemes.result'; Phase 2: 'expense',
                                               -- 'sale', 'yield', 'sensor.reading', 'note'
  occurred_at         datetime, not null       -- when it happened (may differ from created_at)
  payload             json, not null           -- kind-specific body + trust envelope
  payload_version     int, not null
  source              text  'app' | 'user' | 'sensor' | 'import'
  index (plot_id, kind, occurred_at)

cached_price                                   -- shared, no personal data
  id
  source              text  'agmarknet'
  state, district, market, commodity, variety, grade   text
  arrival_date        date
  min_price, max_price, modal_price   numeric  -- Rs per quintal as published
  fetched_at          datetime
  unique (source, market, commodity, variety, grade, arrival_date)

cached_weather                                 -- shared, no personal data
  id
  source              text  'open-meteo'
  lat_r, lon_r        numeric(5,2)             -- rounded to 0.01 deg (~1 km); never the exact pin
  fetched_at          datetime
  valid_until         datetime
  payload             json                     -- hourly series as returned
  unique (source, lat_r, lon_r)
```

### Trust envelope (stored inside every `*.result` event payload)

```json
{
  "value": { "...tool-specific..." },
  "reasons": ["..."],
  "sources": [{ "name": "Agmarknet", "date": "2026-10-06" }],
  "confidence": "high | medium | low",
  "estimated_fields": ["soil.n", "soil.p"],
  "inputs": { "...the profile values used, after defaults..." },
  "model_version": "planner-2026.10.1 | null"
}
```

Same shape the tools return to templates (Section 4), so storing a result is
`json.dumps` of what was rendered.

### Guest profile (localStorage key `agrisense.profile`)

```json
{
  "v": 1,
  "locale": "hi",
  "farm": { "lat": 28.47, "lon": 77.50, "district_code": "UP-GBN" },
  "plots": [{
    "label": "", "area": { "value": 5, "unit": "bigha" },
    "irrigation_source": "tubewell", "current_crop": null, "season": "rabi",
    "soil": { "n": null, "p": null, "k": null, "ph": null, "oc": null }
  }],
  "last_results": { "planner": { "...trust envelope..." } }
}
```

(Values above are illustrative placeholders, not defaults.)

- Sent on each tool request as a hidden form field / `hx-vals` (JSON), added by
  one small script on `htmx:configRequest`. Validated server-side against the
  same schema as the saved model; unknown keys dropped.
- `v` lets us migrate old guest profiles in the browser.
- `last_results` doubles as the offline "last result per tool" (Section 10).
- On "Save my farm": server validates, creates `user` (after consent),
  `farm`, `plot(s)`, `soil_card`, then writes `last_results` as events with
  `source='import'`. The browser keeps a copy for offline use.

## Options Considered

### Option A: Farm/plot core + generic per-plot event log — recommended

| Dimension | Assessment |
|---|---|
| Complexity | Medium: 9 tables, one JSON-payload table. |
| Extensibility | High: diary, calendar, sensors, reports and FPO views read events; no migration per feature. |
| Query cost | JSON payload queries are slower; fine at pilot scale; add typed tables if a kind gets hot. |
| Team familiarity | Medium. |

**Pros:** matches the spec's architecture note; tool results become history for
free; P&L and loan reports are queries over events.
**Cons:** payload schemas live in code, not the DB, so each `kind` needs a
validator and a version; reporting needs care.

### Option B: One table per tool result (planner_run, fertilizer_run, …)

| Dimension | Assessment |
|---|---|
| Complexity | Low per table, but grows with every feature. |
| Extensibility | Low: diary, sensors and reports each need new tables and joins. |
| Query cost | Best: typed columns. |

**Pros:** easy SQL, DB-level constraints.
**Cons:** contradicts "no schema changes" for Phase 2; many migrations.

### Option C: Store the whole profile + results as one JSON document per user

| Dimension | Assessment |
|---|---|
| Complexity | Lowest. |
| Extensibility | Poor for multi-plot, FPO views and per-plot history. |
| Query cost | Poor: no indexes into the document. |

**Pros:** mirrors the localStorage object exactly.
**Cons:** no relational integrity; KVK/FPO multi-farm view (P2) is a rewrite.

## Trade-off Analysis

B optimises for the queries we'll write in weeks 3–5 and makes Phase 2 a
migration per feature. C optimises for week 2 and blocks P2. A keeps a small,
typed core for what every tool reads (farm, plot, soil card) and puts what
*happens* into one append-only table, which is what the diary, calendar,
sensor hub and reports are. The cost is discipline: a validator and version
per event kind, enforced in one module.

Hashing phone numbers instead of storing them trades away the ability to
contact farmers or send an SMS OTP. Phase 1 sends no messages, so the app
doesn't need the clear number, and a leak of the table exposes far less.

## Consequences

- **Easier:** Phase 2 features ship without schema changes; offline last
  results and saved history share one shape; a DB leak exposes no phone
  numbers.
- **Harder:**
  - **Forgotten PIN has no self-service reset** in Phase 1 (no SMS, no stored
    number). **Decided (2026-10-08): staff-assisted reset.** A `helper`
    (KVK/FPO staff, made with `flask agrisense make-helper`) confirms the
    farmer in person and gets a one-time 6-digit code valid for 30 minutes;
    the farmer enters it with a new PIN. Code attempts share the PIN rate
    limit. SMS OTP stays a later option (cost + storing the number).
  - Pepper rotation invalidates all lookups; rotate only with a re-hash plan.
  - 4-digit PIN = 10,000 combinations; rate limiting is mandatory: 5 failures
    / 15 min per phone hash (spec Section 2), plus a looser 30 / 15 min per IP
    hash, because mobile carrier NAT puts many farmers behind one IP.
- **Legacy data:** the live site uses SQLite on an ephemeral Render disk
  (ADR-002), so there is likely no durable legacy data to migrate. Existing
  email/password accounts cannot map to phone + PIN; they are dropped, and the
  old `/home` and `/history` redirect to the new tools (Section 2).
- **Units:** bigha size differs by region. Conversion uses a per-district
  table `data/area_units.csv` with a source column; where no verified figure
  exists the app asks for acre/hectare instead. **TODO:** source bigha sizes
  for Gautam Buddh Nagar and Bulandshahr (state revenue department / KVK).
- **Revisit if:** sensor readings exceed ~100k rows (move to a dedicated
  time-series table), or FPO staff need to manage farms for farmers without
  phones (add an `operator` role).

## Open questions

- [x] Forgotten PIN in Phase 1: **staff-assisted reset** (decided 2026-10-08, see Consequences).
- [ ] Does Pooja (KVK/FPO staff) need her own account that *owns* several farms in Phase 1, or is that P2? The `helper` role only resets PINs today. — *team*

## Action Items

1. [ ] Team sign-off, including the phone-hash decision and the PIN-reset answer.
2. [ ] Section 2: models + initial migration exactly as above; `PHONE_PEPPER` env var added to config and deploy checklist.
3. [ ] Section 2: `event` payload validators module with one schema per `kind` + version.
4. [ ] Section 4: guest-profile JSON schema shared by the browser script and the server validator; migration from guest to saved farm with tests.
5. [ ] Section 4: `data/districts.csv` (centroids, codes) and `data/area_units.csv` with sources.

## Sign-off

| Name | Role | Agree / Disagree | Date |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |
