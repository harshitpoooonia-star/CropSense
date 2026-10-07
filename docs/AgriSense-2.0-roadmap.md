# AgriSense 2.0 — Skills Map, Build Roadmap & Prompt Pack

Oct 7, 2026 · @BigDaddy

## How to use this doc

Only 5 of the 12 imported skills do real work for AgriSense 2.0. ui-ux-pro-max, tailwind-patterns, progressive-web-app, scikit-learn and webapp-testing carry it. i18n-localization and frontend-design help with caveats. The three senior-\* skills turned out to be boilerplate templates, and react-best-practices targets a stack the spec rejects.

The build is split into Gate 0 plus 11 sections over 6 weeks. Each section has one prompt you paste into Claude Code, opened in `C:\Users\harsh\Desktop\AgriSense`, and each prompt names the skills it should load. Run Gate 0, then Sections 1 → 4 in order, then 5–9 in any order, then 10 and 11. Sections 5–9 are the five Phase 1 tools; Crop Doctor waits for Phase 2. They only depend on the farm profile and the trust layer.

The three skills you asked about each have a fixed job. `/product-management:write-spec` turns each tool into a mini-PRD before any code. `/engineering:architecture` writes the 4 ADRs in Section 1. `/engineering:deploy-checklist` runs before every deploy to Render, starting in Section 2.

## Skills analysis

The spec picks Flask + Jinja + Tailwind + HTMX with under 100 KB of JS. Each skill below was judged against that stack and the 9 P0 requirements. I read every SKILL.md, and I ran the scripts where it was cheap to do so.

| Skill | Verdict | What it gives AgriSense 2.0 | Where it is wrong for us | Sections |
| --- | --- | --- | --- | --- |
| **ui-ux-pro-max** | Core, override its picks | 99 UX rules, an html-tailwind stack guide, chart guidance, pre-delivery checklist | Run for AgriSense, `--design-system` returned an *App Store landing* pattern, a blue `#3B82F6` primary and Lexend/Source Sans. That means app-store buttons we don't have, a palette that breaks the spec's soil-brown + one green, and fonts with no Devanagari. Use its rules and checklist; take palette and fonts from the spec. | 3, 4–9, 11 |
| **tailwind-patterns** | Core | `@theme` tokens, mobile-first breakpoints, container queries, anti-patterns | Written for Tailwind v4 with a build step. Using the Play CDN in production would blow the 300 KB budget, so add the standalone Tailwind CLI (no Node) to the build. | 3, 10 |
| **progressive-web-app** | Core | manifest, service worker, cache strategies, offline page, iOS notes | Its example routes assume `/api/*`; our HTMX partials return HTML. Needs a rule for those, plus offline storage of "last result per tool". | 10 |
| **scikit-learn** | Core | Pipelines, CV, model evaluation, feature importance, regression | Nothing wrong. The current `train.py` puts PCA before the random forest, so the "why" chips (SHAP or feature importance) would explain PCA components, not soil or rain. Drop the PCA. | 5 |
| **webapp-testing** | Core | Playwright scripts, `with_server.py` to start Flask during tests | Python Playwright must be installed on your machine. Use it for the 6 guest tasks + offline check. | 2, 11 |
| **i18n-localization** | Use with caveats | Locale file layout, fallbacks, "no concatenated strings" rules | Its `i18n_checker.py` scans `.py .js .jsx .ts .tsx .vue` only, not Jinja `.html` templates, so it misses most of our UI text. Use Flask-Babel and add a template check. | 3 |
| **frontend-design** | Use with caveats | Pushes a distinctive, non-template look; good for the public home and `/about` jury page | Leans toward bold aesthetic risk; the spec wants calm, fast, no decoration. Use only for the home page, under the spec's limits. | 3 |
| **react-best-practices** | Skip for Phase 1 | 40+ React/Next perf rules | The spec chose Flask + HTMX. Relevant only if ADR-001 picks React. | — |
| **senior-fullstack** | Skip | — | Its references are \~1.6 KB generic text and its 3 scripts are empty class templates that print "Completed". No AgriSense value. | — |
| **senior-ml-engineer** | Skip | — | Same template: \~1.4 KB references, stub scripts. Its RAG/LLM focus conflicts with the "no chatbot" rule. | — |
| **senior-data-scientist** | Skip | — | Same template. For experiment design, use write-spec metrics + scikit-learn instead. | — |
| **/product-management:write-spec** | Core (process) | Turns each tool into a PRD: problem, goals, non-goals, stories, P0/P1/P2 with acceptance criteria | The master spec already exists. Use it per tool, fed with that tool's section of the spec, so each build starts from testable criteria. | 4–9, Phase 2 |
| **/engineering:architecture** | Core (process) | ADR format with options, trade-offs and consequences | — | 1 |
| **/engineering:deploy-checklist** | Core (process) | Pre-deploy, deploy, post-deploy, rollback triggers | Customise it once for Render + Postgres + the service-worker cache version, then reuse every release. | 2, 11 |

None of the 12 skills cover ESP32 firmware, MQTT, Sentinel-2 or speech input. Those Phase 2 parts run on plain, detailed prompts (see Phase 2 prompts).

## Coverage gaps

Six P0 needs have no skill behind them. They are domain logic and data plumbing, so the prompts carry the detail and each gap gets a test the team checks by hand.

| Gap | Spec requirement | How the prompt handles it | Proof it works |
| --- | --- | --- | --- |
| Agmarknet / data.gov.in mandi API | P0-4 Mandi Prices | Adapter module with a daily cache table, staleness flag at 3 days, and a fixture file so tests run offline | Week 1 pull: 2 weeks of data for 10 mandis near Greater Noida |
| Open-Meteo forecast | P0-5 Spray & Irrigation | Adapter + 1-hour cache; verdict rules in a pure function with unit tests | 10 hand-written weather cases with expected verdicts |
| Fertilizer maths (ICAR / Soil Health Card) | P0-3 | Pure-Python calculator: nutrient need → urea/DAP/MOP (or SSP) bags → ₹ at subsidised price, split by stage | 10 hand-checked cases within 1 bag |
| Profit model (yield × modal price − input cost) | P0-2 Crop Planner | District yield + cost-of-cultivation tables as CSV; suitability model × profit × risk ranking | 30 real farm records, top-3 hit ≥ 70% |
| Scheme eligibility rules | P0-6 | Rules in a YAML file (one entry per scheme), not code | Each scheme checked against its official page |
| Missing crops | P0-2 | data.csv has no wheat, mustard or sugarcane, the main western-UP crops; they come in through the district yield tables, not the Kaggle classifier | Crop list review with a KVK or local farmer |

There is also a pre-existing security gap. `app.py` stores passwords in plain text (`user.password == password`) and hard-codes two different secret keys. Section 2 fixes this before anything else ships.

## Roadmap

Phase 1 runs 6 weeks, with Gate 0 at the end of week 1 and Gate 1 at the end of week 6.

&#91;embedded content: Phase 1 roadmap · Gate 0 + 11 sections over 6 weeks\]

Sections 1–4 build the base every tool reads. Sections 5–9 are the tools and can run in parallel across team members. Crop Planner's real-farm validation (30 records, 70% top-3) lands in week 8 per the spec, so collect records from week 1.

## Prompt pack

Paste each prompt into Claude Code, opened in the AgriSense folder, unless it says otherwise. Each one starts with its skill names, so Claude loads them before working. Before Section 1, copy the spec into the repo as `docs/AgriSense-2.0-spec.md`. All the prompts refer to it.

### Gate 0 — Prove farmers would act on it (week 1, no app code)

**Skills:** /design:user-research · **Done when:** 8 interviews logged and the Agmarknet pull shows usable data.

Run this one in a Claude chat in this Project:

```text
/design:user-research
Read "AgriSense 2.0 — Redesign Brainstorm, Competitive Brief & Spec", especially "Riskiest assumptions". Build the Gate 0 kit for 8 farmer interviews in Gautam Buddh Nagar and Bulandshahr, in Hindi with English beside it:
1. A 20-minute interview guide: how they choose a crop, who advises them, whether they have a Soil Health Card and can find N/P/K on it, how they check a trader's price, which schemes they claim.
2. A one-page printable Crop Planner card for one farmer's own field: 3 crops, ₹/acre range, water need, risk, 2–3 "why" reasons, source line and confidence badge. Leave blanks for numbers we fill per farmer; invent none.
3. A consent script for photographing soil cards (purpose, no names stored, DPDP Act 2023).
4. A results sheet: per farmer — would act on the card (yes/no/why), has SHC values, current advisor, phone type.
Decision rule: if fewer than 5 of 8 say they would act on the card, flag Crop Planner for rethink before Section 5.
```

Run this one in Claude Code:

```text
Write scripts/check_agmarknet.py. Pull the last 14 days of mandi prices from the data.gov.in Agmarknet API (key from env DATA_GOV_IN_KEY) for wheat, paddy, mustard and potato at the 10 mandis nearest Greater Noida. First list the mandi names the API actually has for Gautam Buddh Nagar, Bulandshahr, Ghaziabad, Hapur and Aligarh, then pick the 10. Save a CSV and print per mandi: days with data, latest price date, longest gap. No app features yet.
```

### Section 1 — Architecture decisions (week 1)

**Skills:** /engineering:architecture · **Done when:** 4 ADRs in `docs/adr/`, each with one recommended option and the team's sign-off.

```text
/engineering:architecture
Read README.md, app.py, train.py, predict.py, requirements.txt and docs/AgriSense-2.0-spec.md.
Constraints: 4-person student team, 6-week Phase 1, Render free tier, users on 2 GB Android phones over patchy 4G, first load under 300 KB JS+CSS, LCP under 3 s, Hindi-first, guest-first, neutral (no ads, no input sales).
Write four ADRs in docs/adr/ in your ADR format (context, options table, trade-offs, consequences, action items), status Proposed:
ADR-001 Frontend: Flask + Jinja + HTMX + Tailwind (standalone CLI) vs React/Next.js vs Flask + Alpine.js.
ADR-002 Database: SQLite on Render (wiped on redeploy) vs Render Postgres vs Supabase vs Neon free tier, plus migrations with Flask-Migrate.
ADR-003 Data model: farm profile as the core entity plus a per-plot event log, so a diary, reports and FPO views can come later without schema changes. Tables at least: user, farm, plot, soil_card, event, cached_price, cached_weather. Guest profile in localStorage, migrated on "Save my farm".
ADR-004 External data: adapters for Agmarknet, Open-Meteo and a schemes YAML; caching, staleness flags, offline fixtures for tests, rate limits, what the UI shows when a source is down.
Recommend one option per ADR. Write no app code.
```

### Section 2 — Foundation and security (weeks 1–2)

**Skills:** webapp-testing, /engineering:deploy-checklist · **Done when:** no plain-text credentials, tests green in CI, first deploy passes the checklist.

```text
Use the webapp-testing skill. Read docs/adr/ first and follow ADR-001 to ADR-003.
1. Restructure into an app factory with blueprints: public, profile, planner, fertilizer, market, weather, schemes, api.
2. Config from env only: SECRET_KEY, DATABASE_URL, DATA_GOV_IN_KEY. Remove both hard-coded secret keys in app.py.
3. Replace email + plain-text password login with phone + 4-digit PIN hashed with werkzeug.security. Rate-limit PIN attempts to 5 per 15 minutes. Existing users get a forced reset; keep no plain-text values anywhere.
4. Flask-Migrate with the ADR-003 models: Postgres in production, SQLite locally.
5. "/" becomes a public placeholder home. Every tool route works without login; the old /home and /history stay behind a redirect until replaced.
6. pytest suite plus a GitHub Actions workflow that runs it on every push.
7. A Playwright smoke test using the skill's scripts/with_server.py to start Flask: load "/", open each tool route as a guest, assert 200 and no console errors.
Don't style anything yet.
```

Then, once:

```text
/engineering:deploy-checklist
Customise it for AgriSense on Render with managed Postgres and Flask-Migrate. Include: env vars present, migration run on a copy first, DB backup before migration, service-worker CACHE_VERSION bumped (from Section 10 on), smoke test against the live URL, rollback = redeploy the previous commit and restore the backup. Rollback triggers: any 5xx on "/" or a tool route, any tool failing as guest, LCP over 3 s on the Lighthouse mobile run. Save it as docs/deploy-checklist.md.
```

### Section 3 — Design system, app shell, Hindi/English (week 2)

**Skills:** ui-ux-pro-max, tailwind-patterns, i18n-localization, frontend-design (home page only) · **Done when:** /styleguide renders every component in Hindi and English and passes the pre-delivery checklist.

```text
Use ui-ux-pro-max, tailwind-patterns and i18n-localization; use frontend-design only for the public home page.
Run ui-ux-pro-max searches for UX rules (--domain ux "accessibility touch loading") and the html-tailwind stack guide. Do NOT use its palette, fonts or landing pattern. These spec constraints win:
- mobile-first, 360 px baseline; bottom nav with icon + label; one primary action per screen; tap targets 48 px or more
- off-white and soil-brown neutrals, one green accent; good/warning/critical always icon + word + colour, never colour alone; WCAG AA
- Mukta or Noto Sans Devanagari with a matching Latin face; body 16 px or more; key numbers large
- no hero video, 3D, parallax, carousels or stock photos; HTMX is the only JS dependency
Build:
1. Tailwind v4 through the standalone CLI (no Node), semantic tokens in @theme, minified CSS output in static/.
2. Jinja base layout: top bar with language switch; bottom nav Today, Plan, Field, Market, More.
3. Jinja macros: result_card (title, body, source line + date, confidence badge high/medium/low, "Ask an expert" link, Share to WhatsApp), verdict_pill, number_input with unit switch, bag_icons.
4. Flask-Babel with hi and en catalogues, locale cookie, Devanagari font with font-display: swap, unit helpers (acre/bigha/hectare, kg/quintal), a crop local-name table. The skill's i18n_checker.py doesn't scan .html, so add tests/test_i18n_templates.py that fails on raw text in templates outside _().
5. Public home: one-line promise, three tiles (Plan a crop, Check a price, Find a scheme), "We don't sell seeds or sprays".
6. /styleguide showing every macro in both languages.
Finish by running ui-ux-pro-max's Pre-Delivery Checklist and report each item pass/fail.
```

### Section 4 — Farm profile and trust layer (week 2)

**Skills:** /product-management:write-spec, ui-ux-pro-max · **Done when:** a guest can set up a farm in Hindi at 360 px and every tool can read it.

```text
/product-management:write-spec
Write the spec for "Guest-first farm profile + trust layer" from requirements P0-1 and P0-8 in docs/AgriSense-2.0-spec.md. Save it as docs/specs/01-farm-profile.md. Don't ask questions the spec already answers.
Then implement it, using ui-ux-pro-max for the screens:
- Profile wizard, 4 steps at most: pin on a map (Leaflet + OSM tiles, loaded only on that step) or GPS; area + unit; irrigation source; optional Soil Health Card N, P, K, pH, OC.
- Guest profile in localStorage, sent with each tool request. "Save my farm" = phone + PIN, creates farm/plot rows, migrates local data, shows DPDP consent text.
- District lookup from lat/lon (offline table of UP and Haryana district centroids). District defaults fill missing soil values, flagged estimated.
- Trust layer: every tool returns {value, reasons[], sources[{name, date}], confidence, estimated_fields[]}, and result_card renders it. KVK contacts for the target districts + Kisan Call Centre 1800-180-1551.
Tests: guest → saved round trip, estimated flag shown, Playwright run of the wizard at 360x740 in Hindi.
```

### Section 5 — Crop Planner v2 (weeks 3–4)

**Skills:** /product-management:write-spec, scikit-learn, ui-ux-pro-max · **Done when:** top-3 contains the farmer's chosen crop in 70% of 30 real records (spec target, checked week 8).

```text
/product-management:write-spec
Spec "Crop Planner v2" from P0-2 in docs/AgriSense-2.0-spec.md; save docs/specs/02-crop-planner.md.
Then build it with the scikit-learn and ui-ux-pro-max skills:
1. Data: data/district_crop_economics.csv with columns district, crop, season, yield_qtl_per_acre, cost_per_acre_inr, water_need, source, as_of. Cover Gautam Buddh Nagar and Bulandshahr, including wheat, mustard, sugarcane, paddy, potato, maize. Where you have no verified figure leave the cell blank with TODO. Do not invent agronomic or price numbers.
2. Model: retrain the suitability classifier WITHOUT PCA (current train.py puts PCA before the forest, which makes explanations meaningless). Pipeline StandardScaler -> RandomForest or GradientBoosting, stratified 5-fold CV, CalibratedClassifierCV for honest probabilities, saved with joblib plus a version string.
3. Ranking: expected profit = yield x recent modal price (from the mandi cache) - cost; risk from price spread + water need vs irrigation source; score combines suitability, profit and risk. Season filter kharif/rabi/zaid removes out-of-season crops.
4. Top 3 cards: Rs/acre range, water need, risk level, 2-3 plain-language reasons from per-prediction contributions (SHAP TreeExplainer if installed, otherwise permutation importance), confidence badge, sources. Add "Why not <crop>?" for any crop.
5. scripts/validate_planner.py reads data/farm_records.csv (inputs + the crop a good local farmer chose) and prints top-3 hit rate. Report the Kaggle test accuracy only as a secondary number.
6. Card CTA "Fertilizer for this crop" opens Section 6's tool prefilled.
```

### Section 6 — Fertilizer Calculator (week 3)

**Skills:** /product-management:write-spec, ui-ux-pro-max · **Done when:** all 10 hand-checked cases land within 1 bag.

```text
/product-management:write-spec
Spec "Fertilizer Calculator" from P0-3; save docs/specs/03-fertilizer.md. Then build it:
- fertilizer/calc.py, pure functions, no Flask imports. Inputs: crop, area in any unit, soil N/P/K from the profile or district default.
- data/fert_rdf.csv: crop, state, N, P2O5, K2O (kg/ha), split schedule, source. Fill from ICAR / state package-of-practice tables you can cite; blank + TODO otherwise.
- Soil Health Card low/medium/high adjustment as data, not code.
- Products: DAP (18-46-0) for P first and subtract its N, MOP (0-0-60) for K, urea (46% N) for the rest; SSP option instead of DAP. Bag sizes and subsidised prices from data/fert_prices.csv with a date (verify current bag sizes).
- Output: bags per product drawn with bag_icons, Rs total, split by basal / first / second top-dress, Share to WhatsApp text, trust layer.
- tests/test_fertilizer.py runs the 10 cases in data/fert_cases.csv (each with its source); each must be within 1 bag.
```

### Section 7 — Mandi Prices + offer checker (weeks 3–4)

**Skills:** /product-management:write-spec, ui-ux-pro-max · **Done when:** a guest gets an offer verdict in 3 taps, and stale data is labelled.

```text
/product-management:write-spec
Spec "Mandi Prices + offer checker" from P0-4; save docs/specs/04-mandi.md. Then build it per ADR-004:
- market/agmarknet.py adapter: daily fetch into cached_price, retries, a fixture file for tests.
- 5 nearest mandis by haversine from the farm pin (data/mandis.csv with coordinates).
- Show min/modal/max per crop with the price date. Older than 3 days: say so plainly, never hide it.
- Net price = modal - (transport Rs per quintal-km x distance); the rate is editable and remembered.
- Offer checker: one big Rs/qtl input -> below / fair / above modal, gap in Rs and %, verdict_pill (icon + word + colour). The "fair" band is a config value, shown in the reason text.
- Market tab lists the farmer's crops; Today tab shows the price change.
Tests: adapter with fixtures, verdict boundaries, Playwright guest flow at 360x740.
```

### Section 8 — Spray & Irrigation Advisor (week 4)

**Skills:** /product-management:write-spec, ui-ux-pro-max · **Done when:** 10 written weather cases give the expected verdicts.

```text
/product-management:write-spec
Spec "Spray & Irrigation Advisor" from P0-5; save docs/specs/05-spray-irrigation.md. Then build it:
- weather/openmeteo.py: 72-hour hourly forecast (precipitation_probability, precipitation, wind_speed_10m, relative_humidity_2m, temperature_2m) for the farm pin, cached 1 hour.
- weather/rules.py: pure functions for spray and irrigate verdicts per day. Put every threshold in config with a cited source note (KVK or pesticide-label guidance). Propose values but list them for my review; don't treat them as final.
- Irrigation uses recent + forecast rain and crop stage; leave a hook to use sensor soil moisture when a plot has a node (Phase 2).
- Traffic light per day with a localised reason string, e.g. "rain 70% after 3 pm".
- The Today tab's lead card uses this.
Tests: data/weather_cases.json with 10 cases and expected verdicts.
```

### Section 9 — Scheme Finder (week 5)

**Skills:** /product-management:write-spec, ui-ux-pro-max · **Done when:** every listed scheme is checked against its official page by a person.

```text
/product-management:write-spec
Spec "Scheme Finder" from P0-6; save docs/specs/06-schemes.md. Then build it:
- data/schemes.yaml: id, name_hi, name_en, level (central/UP/Haryana), eligibility rules (state, land size, ownership, crop, category), one-line benefit, documents[], official_url, deadline (nullable), last_checked, verified (bool).
- Seed with major central schemes (e.g. PM-KISAN, PMFBY, KCC) and the main UP and Haryana farmer schemes. Mark every entry verified: false; a person flips it after checking the official page.
- 5-6 questions, one per screen with HTMX -> likely-eligible list with benefit, document checklist, official link, deadline.
- Label every result "likely eligible - confirm at the official portal or CSC".
Tests: one rule-engine test per scheme.
```

### Section 10 — PWA and performance (week 5)

**Skills:** progressive-web-app, tailwind-patterns, ui-ux-pro-max · **Done when:** installable, last results readable offline, under 300 KB first load, LCP under 3 s.

```text
Use the progressive-web-app, tailwind-patterns and ui-ux-pro-max skills.
- manifest.json: AgriSense, Hindi and English short names, theme colour from the tokens, 192 and 512 maskable icons.
- sw.js: precache app shell, offline.html and fonts; network-first for HTML pages AND HTMX partials (requests with the HX-Request header) with cache fallback; keep the last result of each tool under its own cache key so it reads offline; CACHE_VERSION injected from the git SHA at build.
- Install button for Android; an "Add to Home Screen" hint for iOS Safari.
- Performance: Lighthouse mobile with throttled 4G on /, /plan, /market, /schemes. Budget: under 300 KB JS+CSS, LCP under 3 s. Fix with font subsetting (Devanagari + Latin), lazy Leaflet, image sizes, cache headers.
Report a table: page, transfer size, LCP, pass/fail.
```

### Section 11 — Test and launch (week 6)

**Skills:** webapp-testing, /design:accessibility-review, ui-ux-pro-max, /engineering:deploy-checklist · **Done when:** 80% unaided task completion in Hindi with 8 or more farmers, and v2.0.0 deployed through the checklist.

```text
Use the webapp-testing skill.
1. Playwright suite for the 6 moderated-test tasks as a guest at 360x740 in Hindi: plan a crop, get fertilizer bags, check a trader's offer, should I spray tomorrow, find a scheme, save my farm. Save a screenshot per step to tests/artifacts/.
2. Run /design:accessibility-review on every screen: contrast, 48 px tap targets, focus order, status never colour-only.
3. Run ui-ux-pro-max's Pre-Delivery Checklist.
4. Privacy check: analytics events carry no names or phone numbers; consent asked on first save (DPDP Act 2023).
5. Moderated test kit in Hindi: task script, stopwatch sheet, "would you act on this?" question after each task.
6. Run docs/deploy-checklist.md for the release and tag v2.0.0.
```

## Phase 2 prompts

Phase 2 starts only after Gate 1 passes, meaning the 80% task completion in Section 11. Every Phase 2 feature starts with `/product-management:write-spec` on its P1 bullet, plus an ADR wherever it adds hardware or a new data source.

**Crop Doctor:** scikit-learn won't do here; this needs a small CNN. The prompt carries the detail.

```text
/product-management:write-spec
Spec "Crop Doctor" from the P1 list in docs/AgriSense-2.0-spec.md; save docs/specs/07-crop-doctor.md.
Then: fine-tune a small image model (MobileNetV3 or EfficientNet-B0) on PlantDoc + our own field photos (not PlantVillage alone) for the target crops. Report per-class precision/recall on a held-out set of field photos only. Serve top-3 likely issues with confidence; below a threshold set on the validation set, show "Not sure - send to expert" with the KVK hand-off. Treatments list non-chemical options first and name active ingredients, never brands. Photos are resized on the phone before upload.
```

**Sensor Hub (ESP32):**

```text
/engineering:architecture
Write ADR-005: ESP32 soil node (moisture, temperature, EC; NPK probe labelled "estimate") to AgriSense. Options: MQTT broker vs plain HTTPS POST to a Flask endpoint, with device keys, power budget on battery + solar, and offline buffering. Then implement the chosen endpoint, a pairing flow on the Field tab, readings stored as plot events, a calibration step against the soil card, and the irrigation advisor's sensor hook from Section 8. Include the ESP32 Arduino sketch in firmware/.
```

**Field health (Sentinel-2):**

```text
/product-management:write-spec for "Field health" from P1, then build: draw the field boundary on the Leaflet map; fetch Sentinel-2 L2A NDVI and NDMI for that polygon every ~5 days (pick the provider in an ADR: Copernicus Data Space, Sentinel Hub, or Google Earth Engine); mask clouds; show a zone map and up to 3 "check this corner" zones with the image date and cloud cover as the trust line.
```

**Farm diary + crop calendar:**

```text
/product-management:write-spec for "Farm diary" and "Crop calendar" from P1. Build both on the ADR-003 event log with no schema changes: log costs, yield and sales per plot; season P&L; PDF export. The calendar generates stage-wise tasks from the sowing date and shifts them using the Section 8 weather rules.
```

**Voice input (Hindi):**

```text
/product-management:write-spec for "Voice input" from P1. Hindi speech -> text via Bhashini -> an intent router that maps to one of the six tools and fills its inputs, then shows that tool's normal result card. No free-text answers ever: if no tool matches, say so and show the six tiles.
```

## Working rules

Run one section per Claude Code session, on its own branch, and merge only after you've read the diff. Give every session the same ground rules by saving this as `CLAUDE.md` in the AgriSense root before Section 1:

```markdown
# AgriSense 2.0 — rules for Claude
- Source of truth: docs/AgriSense-2.0-spec.md, docs/adr/, docs/specs/. Read the relevant ones first.
- Stack: Flask + Jinja + HTMX + Tailwind (standalone CLI). No React, no new JS libraries without an ADR.
- Budgets: first load < 300 KB JS+CSS, LCP < 3 s on throttled 4G, 360 px baseline, tap targets >= 48 px.
- Every user-facing string goes through Flask-Babel (hi + en). No raw text in templates.
- Every tool result goes through the trust layer: reasons, sources with dates, confidence, estimated fields.
- Never invent agronomic numbers, prices, scheme rules or thresholds. Leave a TODO with the source to check.
- No plain-text secrets or credentials. Config from env only.
- Neutral: no brands, ads or buy buttons. Treatments name active ingredients only.
- Tests with every change; Playwright for user flows (webapp-testing skill).
```

- [ ] Save the spec as `docs/AgriSense-2.0-spec.md` and add `CLAUDE.md`
- [ ] Settle the open questions first: which `app.py` is live, final name (AgriSense or CropSense), target districts, KVK contact for interviews
- [ ] Start each section with: "Read CLAUDE.md and docs/ first, then: \<prompt>"
- [ ] Ask Claude to show a plan before it edits, for Sections 2, 5 and 10
- [ ] After each section: run tests, read the diff, tick the section's "Done when", commit
- [ ] Run `docs/deploy-checklist.md` before every deploy, not only the launch
