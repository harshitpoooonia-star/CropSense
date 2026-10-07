# AgriSense 2.0 — Redesign Brainstorm, Competitive Brief & Spec

Oct 7, 2026 · @BigDaddy

AgriSense stops being a 7-number crop guesser and becomes a farm decision tool: every screen must change what a farmer plants, spends, sprays or sells — or it doesn't ship.

## Decisions at a glance

Ship a mobile-first, Hindi-first web app built around one farm profile, with six tools that each end in an action: Crop Planner, Fertilizer Calculator, Crop Doctor, Mandi Prices, Spray & Irrigation Advisor, and Scheme Finder.

- **Positioning:** neutral, input-agnostic farm advice that shows its working. We sell nothing to farmers, so every recommendation can be trusted. No incumbent can claim this.
- **The redesign's biggest change:** drop the sign-up wall. Today `/` is a login page. In 2.0 every tool works as a guest; an account only saves your farm.
- **What changes in the ML:** the recommender ranks crops by expected profit and risk for *your season and location*, not "suitable crop" on 7 typed numbers. Accuracy on data.csv is no longer the headline.
- **Phase 1 (6 weeks):** farm profile, Crop Planner v2, Fertilizer Calculator, Mandi Prices + offer checker, Spray & Irrigation Advisor, Scheme Finder, Hindi/English, installable PWA.
- **Phase 2 (semester):** Crop Doctor, ESP32 sensor hub, Sentinel-2 field health, farm diary with season P&L, KVK expert hand-off, voice input.
- **Cut:** carbon credits, digital twin, drones, chatbot-for-its-own-sake, gamification, marketplace. Reasons in the kill list.

One thing to fix before any redesign work: the project copy of `app.py` still stores passwords in plain text and uses `flask_sqlalchemy`. If that is the deployed version rather than the rewritten one, fix it first.

## Brainstorm 1 — Problem framing

The real problem is not "farmers don't know which crop suits their soil". It is that a smallholder makes five money decisions a season with no neutral advice, and the person who advises them usually sells them something.

**Who has the problem.** A 1–5 acre farmer in UP, Haryana or MP. Shared Android phone, patchy 4G, reads Hindi better than English, has a Soil Health Card in a drawer. Second user: the KVK staffer, FPO coordinator or agri student who helps several such farmers.

**What they do today (the real competitor).** Ask the local input dealer, copy the neighbour, call Kisan Call Centre (1800-180-1551), or watch YouTube. The dealer is the default advisor and earns on what he recommends.

**Root cause, not symptom.** Ask "why" three times: wrong crop or overspend → advice came from someone with a stake → no neutral source that knows *this* farm → farm data (soil card, location, prices) is scattered and unreadable.

### Jobs to be done

| When… | I want to… | So I can… | Tool that serves it |
| --- | --- | --- | --- |
| Kharif or rabi sowing is 3–4 weeks away | compare crops on likely profit and risk for my field | not lose a season on the wrong crop | Crop Planner |
| I'm at the dealer's counter | know exactly how many bags of urea/DAP/MOP my field needs | stop overbuying and overapplying | Fertilizer Calculator |
| Leaves show spots or curling | find out what it is and what to spray, with no brand push | act before it spreads | Crop Doctor |
| A trader quotes me a price | check it against today's mandi rates nearby | not get underpaid | Mandi Prices + offer checker |
| I'm planning to spray or irrigate tomorrow | know if rain or wind will waste it | save chemical, diesel and water | Spray & Irrigation Advisor |
| I hear about a sarkari scheme | know if I qualify and which papers I need | claim money I'm owed | Scheme Finder |

### How might we…

1. …give a farmer a crop choice ranked by money, not just agronomy, without asking for 7 lab numbers?
2. …turn a Soil Health Card photo into a shopping list of fertilizer bags?
3. …make advice trustworthy when the farmer can't verify the model?
4. …make the app useful on day one, before any sensor is installed?
5. …let someone who doesn't read English use every tool?
6. …make a dealer's or trader's number checkable in 10 seconds?

**My pushback on the current product:** the 7-number form asks for N, P, K, pH, rainfall and humidity, which no farmer has at hand. The tool only works for someone who already has a soil report, and even then it ignores season, location and price. Fixing the input problem matters more than any new feature.

## Brainstorm 2 — The no-gimmick test

22 ideas scored: 16 pass all four checks, 4 pass with caveats, 2 are cut. A feature ships only if it passes all four checks below.

1. **Decision:** it changes a specific thing the farmer does: plant, buy, spray, irrigate, sell or claim.
2. **Data:** it runs on data we can actually get today, free (Open-Meteo, Agmarknet, Sentinel-2, Soil Health Card values, ICAR guides).
3. **Honesty:** it can show its source and a confidence level, and say "not sure, ask a KVK expert".
4. **Day one:** it works for a farmer with only a phone. Hardware is an optional upgrade, never a requirement.

| Idea | What it changes for the farmer | Passes | Phase |
| --- | --- | --- | --- |
| Farm profile (pin or draw field, area in bigha/acre, irrigation source, soil card values) | Every tool answers for *this* field, nothing typed twice | 4/4 | 1 |
| Crop Planner v2: profit + risk ranking with reasons | Which crop to sow | 4/4 | 1 |
| Fertilizer Calculator from Soil Health Card | How many bags of urea/DAP/MOP to buy, and the ₹ cost | 4/4 | 1 |
| Mandi price board, nearest mandis net of transport | Where and when to sell | 4/4 | 1 |
| Offer checker ("trader offers ₹X/qtl — fair?") | Accept or refuse a price | 4/4 | 1 |
| Spray & irrigation window (rain, wind, humidity next 72 h) | Whether to spray or irrigate tomorrow | 4/4 | 1 |
| Scheme Finder with document checklist | Which schemes to claim, what papers to carry | 4/4 | 1 |
| Hindi/English UI, local units, icons | Lets the actual user use every tool | 4/4 | 1 |
| Installable PWA, works offline for saved advice | Usable with patchy signal | 4/4 | 1 |
| Crop Doctor (leaf photo → likely issue → treatment, incl. non-chemical) | What to spray, or whether to wait | 4/4 if it shows confidence and an "unsure" path | 2 |
| Crop calendar with stage-wise tasks | Nothing missed: sowing, top-dress, irrigation, harvest | 4/4 | 2 |
| Farm diary: expenses, yields, sales → season profit | Knows what actually made money; ready for loan papers | 4/4 | 2 |
| ESP32 soil node (moisture, temp, EC) feeding the farm profile | Irrigates on real moisture, not guesswork | 3/4 — opt-in kit | 2 |
| Sentinel-2 field health (NDVI/NDMI zones) | Which part of the field to walk and check | 4/4 | 2 |
| KVK / expert hand-off (district KVK contacts, Kisan Call Centre) | Gets a human when the AI is unsure | 4/4 | 2 |
| Voice input in Hindi (Bhashini) | Use without typing | 4/4 | 2 |
| Weather-driven pest risk alerts | Scout before damage spreads | 3/4 — needs validated rules per crop | 3 |
| Sell-or-hold price forecast | Timing of sale | 2/4 — forecasts are weak; show range only | 3 |
| Insurance (PMFBY) claim helper: geotagged photos + checklist | Files a claim correctly, on time | 4/4 | 3 |
| Farm report PDF for KCC/loan | Easier credit | 3/4 — depends on diary adoption | 3 |
| Generic AI chatbot "ask anything" | Nothing specific | 1/4 | Cut |
| Carbon/water credit tracker | Nothing today; no buyer for 1-acre farms | 0/4 | Cut |

The chatbot is cut as a *feature*, not as a channel. Phase 2 voice input routes the farmer's question into the six tools above, so every answer comes from a calculation, never from free-form text.

## Brainstorm 3 — Kill list

These were considered and set aside. Each fails the test or costs more than it returns for a 4-person student team.

| Idea | Why it's out | Revisit if… |
| --- | --- | --- |
| Carbon / water credit tracking | No buyer pays for 1–2 acre credits today; promising income we can't deliver breaks trust | A registry accepts aggregated smallholder credits via an FPO |
| Digital farm twin, "what-if" simulator | Needs calibrated crop models per variety; output would be invented precision | Phase 2 sensors + NDVI give a season of real data |
| Drone / rover scouting | Hardware cost and permissions; farmers can't use it from a phone | It's a robotics course demo, kept separate from the product |
| Free-form AI chatbot | Answers without grounding; hallucination risk on pesticide doses | Never as free text — only as a voice router into the tools |
| Input marketplace / buy-now buttons | Destroys the neutrality that is our whole positioning | Never |
| Equipment or labour rental marketplace | Two-sided cold-start problem; needs ops, not code | An FPO partner wants to run it |
| Gamification (badges, streaks, leaderboards) | Farmers open the app when a decision is due, not daily | Never |
| Community feed / farmer social network | Moderation load, misinformation on chemicals | KVK staff agree to moderate |
| 3D hero, parallax, animated globe on the website | Heavy on 2 GB phones, slows first load, says nothing | Never on the app; fine on a jury demo page |
| Blockchain traceability | Solves a buyer's problem, not the farmer's | A buyer partner asks for it |
| Accuracy % as the headline | 96.8% on an augmented Kaggle set says little about real farms | Validated on our own field data |

## Competitive brief — Landscape

Every strong player does one slice well; nobody joins soil, field, weather, price and schemes into one neutral, explained answer for a 1-acre farmer.

| Player | Type | What they do well | Gap we can use |
| --- | --- | --- | --- |
| Input dealer / neighbour | Status quo (the real rival) | Trusted, face to face, gives credit | Advice tied to what he sells; no data |
| Plantix | Direct (diagnosis) | Photo diagnosis; claims 69 crops, 950+ issues, 19 languages | No soil, sensor or price layer; revenue from input-company ads at the moment of diagnosis |
| Fasal | Direct (IoT) | Sensor kits + ML for horticulture | Proprietary, priced for orchards, not field crops |
| DeHaat, AgroStar, BharatAgri | Indirect (commerce + advice) | Full stack, large reach; DeHaat reports ₹3,041 cr FY25 revenue | Advice funds input sales — not neutral |
| Digital Green FarmerChat | Direct (AI advisor) | Voice/image GenAI, 16 languages, 2M+ farmers claimed | Generic to the region, no farm-level data or prices |
| Bharat-VISTAAR, Kisan e-Mitra | Substitute (government) | Free, multilingual voice; national scale; scheme answers | Generic advice; no field-level view |
| Agmarknet, eNAM, myScheme, Soil Health Card portal | Substitute (government data) | The raw data, free | Hard to use; no answer, just tables |
| Cropin | Adjacent (enterprise) | Large-scale B2B agri-intelligence | Sells to agribusiness, not farmers |

Figures are company-reported and come from the AgriSense 2.0 research doc; treat them as indicative.

### Capability matrix

Strong / Adequate / Weak / Absent, judged from public product descriptions, not hands-on testing. The last column is the 2.0 target, not today.

| Capability | Plantix | Fasal | DeHaat / AgroStar | FarmerChat | Govt (VISTAAR, portals) | AgriSense 2.0 target |
| --- | --- | --- | --- | --- | --- | --- |
| Crop choice ranked by profit and risk | Absent | Absent | Adequate | Weak | Weak | Strong |
| Fertilizer bags from soil card | Weak | Adequate | Adequate | Weak | Adequate | Strong |
| Leaf disease diagnosis | Strong | Weak | Adequate | Adequate | Weak | Adequate |
| Mandi prices + offer check | Absent | Absent | Weak | Absent | Adequate (raw) | Strong |
| Spray / irrigation timing | Weak | Strong | Weak | Weak | Weak | Strong |
| Scheme eligibility + papers | Absent | Absent | Weak | Weak | Strong | Strong |
| On-farm sensors | Absent | Strong | Absent | Absent | Absent | Adequate (open kit) |
| Satellite field view | Absent | Adequate | Weak | Absent | Weak | Adequate |
| Shows reasoning and confidence | Weak | Adequate | Weak | Adequate | Weak | Strong |
| Neutral — sells no inputs | Weak | Strong | Absent | Strong | Strong | Strong |
| Hindi + voice | Strong | Adequate | Strong | Strong | Strong | Adequate |
| Useful with only a phone | Strong | Weak | Strong | Strong | Strong | Strong |

## Competitive brief — Positioning and implications

Own "neutral and shows its working". It is the one position no funded player can take, because their revenue depends on selling inputs or ads.

**Positioning statement.** For smallholders in north India who make sowing, buying and selling decisions without neutral advice, AgriSense is a farm decision tool that turns their soil card, field location and today's prices into one explained action. Unlike dealer-backed apps, it sells nothing and shows why it recommends what it does.

**Taglines to test:** "Mitti se Mandi tak" · "Sense. Decide. Earn." · "Advice that sells you nothing."

### Positions in the market

| Position | Who holds it | Our move |
| --- | --- | --- |
| Crowded: "AI-powered", "smart farming" | Everyone | Never lead with "AI" on the site |
| Crowded: disease photo diagnosis | Plantix | Parity only, Phase 2; don't try to beat 150M images |
| Unclaimed: profit-ranked crop choice with reasons | Nobody | Lead feature |
| Unclaimed: offer checker against mandi rates | Nobody | Lead feature — cheapest to build, easiest to demo |
| Unclaimed: open, low-cost sensor kit for field crops | Nobody (Fasal is closed, horticulture) | Differentiator for the IoT/robotics story |
| Vulnerable claim: "free advice" from commerce apps | DeHaat, AgroStar | Contrast quietly: "we don't sell seeds or sprays" |

### Threats

- **Bharat-VISTAAR adds farm-level data.** It already has AgriStack farmer IDs and a free 155261 helpline. If it adds plot-level advice, our core overlaps. Response: build on its rails where possible, and stay the better interface and the better explainer.
- **Plantix adds prices or soil.** It has the distribution. Response: our neutrality and the sensor/satellite layer are hard for an ad-funded app to copy.
- **Our own weak spot: data quality.** The current model trains on 2,683 rows covering 22 crops at about 125 rows each, with no location, season or price. A jury or reviewer who knows the Kaggle crop dataset will spot it. Response: reframe accuracy as one input to a profit ranking, and validate on a small set of real farm records.

### What this means for the build

- **Differentiate on:** Crop Planner v2, offer checker, Fertilizer Calculator, reasoning and confidence on every answer, neutrality.
- **Reach parity on:** Hindi UI, scheme help, weather timing. Wrap the government data rather than compete with it.
- **Deprioritise:** disease detection as a headline. Ship it in Phase 2 with honest confidence, and route unsure cases to KVK.
- **Monitor:** Bharat-VISTAAR third-party APIs, Agmarknet API limits, Plantix feature launches.

## Website redesign

Replace the login wall and single form with a public home page and a five-tab app built on one farm profile.

&#91;embedded content: AgriSense 2.0 sitemap · Today + 4 tabs on one farm profile\]

The five bottom-nav tabs are Today, Plan, Field, Market and More. Each tool reads the farm profile, so a farmer enters location and soil values once.

### Key screens

| Screen | What it shows | Primary action |
| --- | --- | --- |
| Public home | One-line promise, three entry tiles (Plan a crop · Check a price · Find a scheme), language switch, "We don't sell seeds or sprays" | Try a tool — no sign-up |
| Today | Spray/irrigate verdict for 3 days, price change for my crops, tasks due, nearest scheme deadline | Tap a card to open its tool |
| Crop Planner result | 3 crop cards: ₹/acre range, water need, risk, "why" chips | Plan this crop → Fertilizer for it |
| Fertilizer result | Bags per field drawn as bag icons, split by stage, ₹ total | Share to WhatsApp |
| Offer checker | One big ₹/qtl input; verdict in colour, icon and words; 5 nearest mandis | Compare mandis |
| Scheme Finder | "Likely eligible" list, benefit line, papers checklist | Open official portal |

### Design direction

- **Mobile first, 360 px baseline.** Bottom nav with icon + label, one primary action per screen, tap targets ≥ 48 px.
- **Type that renders Hindi as well as English.** Pair such as Mukta or Noto Sans Devanagari with a matching Latin face; body ≥ 16 px; key numbers large.
- **Calm, earthy palette.** Off-white and soil-brown neutrals, one green accent. Good / warning / critical always carry an icon and a word, never colour alone.
- **Every result card ends with** source, date and a confidence badge.
- **No decoration that costs load time:** no hero video, 3D, parallax, carousels or stock photos. Real field photos from the team's visits.
- **Share to WhatsApp on every result** as a clean text + image card — that's how advice travels in a village.
- **Stack for speed:** Flask + Jinja + Tailwind + HTMX + a service worker; under 100 KB of JS. A separate `/about` page carries the architecture and validation results for the jury.

## Spec — Problem, goals, non-goals

**Problem.** Today AgriSense asks a farmer for seven lab values and returns one crop name. It ignores season, location and price, hides everything behind a sign-up page, and works only in English. A smallholder can't use it, and it doesn't help with the decisions that cost them money: what to buy, when to spray, where to sell, what to claim.

### Personas

| Persona | Context | Main jobs | Constraint |
| --- | --- | --- | --- |
| Ramesh, smallholder | 2.5 acres, wheat–paddy, Bulandshahr; tubewell | Plan rabi crop, buy fertilizer, sell wheat | Shared Android, Hindi only, patchy 4G |
| Pooja, KVK / FPO field staff | Helps \~200 farmers in a block | Run the tools on a farmer's behalf, explain results | Needs speed and printable / shareable output |
| Jury / recruiter | Evaluates the project | See a working loop, honest validation | 5 minutes, laptop |

### Goals (Phase 1)

1. A first-time farmer gets a useful answer from any tool in **under 2 minutes, without an account**.
2. **80% task completion** in moderated tests with at least 8 farmers, in Hindi.
3. Every recommendation shows **source, reasoning and a confidence level**.
4. The app loads in **under 3 s on a mid-range Android over a throttled 4G connection** and is installable as a PWA.
5. Crop Planner v2 is validated against **at least 30 real farm records** collected by the team, not only the Kaggle split.

### Non-goals

- **Selling inputs or taking ads.** Neutrality is the product.
- **A native Android app.** A PWA covers install, offline and camera at a fraction of the effort.
- **Languages beyond Hindi and English in Phase 1.** Built for i18n so a third language is a translation file, not a rebuild.
- **Lab-grade soil measurement.** Low-cost probes are estimates and are labelled as such.
- **Price prediction as a promise.** Forecasts, if shown, are ranges with a warning.

## Spec — Requirements

Nine P0 requirements make Phase 1. Each has acceptance criteria the team can test.

### P0 — must ship in Phase 1

1. **Guest-first access and farm profile.** *As Ramesh, I want to try a tool without signing up so that I see value before giving my number.*
   - [ ] `/` is a public home page; all six tools run without login
   - [ ] Farm profile: drop a pin or use GPS, area in acre/bigha/hectare, irrigation source, optional Soil Health Card values
   - [ ] Guest profile lives on the device; "Save my farm" creates an account with phone + 4-digit PIN, and migrates it
   - [ ] Passwords/PINs hashed (werkzeug); no plain-text credentials anywhere
2. **Crop Planner v2.** *As Ramesh, I want crops ranked by likely profit for this season so that I pick one that pays.*
   - [ ] Inputs come from the profile; anything missing is filled from district defaults and marked "estimated"
   - [ ] Season filter (kharif / rabi / zaid) removes out-of-season crops
   - [ ] Top 3 crops show suitability, expected ₹/acre range (yield × recent modal price − input cost), water need and risk level
   - [ ] Each card lists the 2–3 factors that drove the ranking (SHAP or feature importance) in plain Hindi/English
   - [ ] "Why not paddy?" — the user can ask why a crop ranked low
3. **Fertilizer Calculator.** *As Ramesh at the dealer's counter, I want the number of bags so that I don't overbuy.*
   - [ ] Given crop, area and N/P/K values, output bags of urea, DAP and MOP (or SSP option) and ₹ total at current subsidised prices
   - [ ] Split schedule by crop stage (basal, first and second top-dress)
   - [ ] Results match the ICAR / Soil Health Card recommendation within one bag for 10 hand-checked cases
4. **Mandi Prices + offer checker.** *As Ramesh, I want to check a trader's offer so that I'm not underpaid.*
   - [ ] Shows min / modal / max for my crops at the 5 nearest mandis, with date of the price
   - [ ] "Net price" subtracts an editable transport cost per quintal-km
   - [ ] Offer checker: enter ₹/qtl → verdict (below / fair / above modal) with the gap in ₹ and %
   - [ ] If data is older than 3 days, it says so instead of hiding it
5. **Spray & Irrigation Advisor.** *As Ramesh, I want to know if tomorrow is good to spray so that rain doesn't wash it off.*
   - [ ] 72-hour view from Open-Meteo: rain probability, wind, humidity, temperature
   - [ ] Traffic-light verdict per day for spraying and irrigating, with the reason ("rain 70% after 3 pm")
   - [ ] Uses sensor soil moisture when a node is linked (Phase 2), otherwise rainfall + crop stage
6. **Scheme Finder.** *As Ramesh, I want to know which schemes I qualify for so that I claim what I'm owed.*
   - [ ] 5–6 questions (state, land size, ownership, crop, category) → list of likely-eligible central and UP/Haryana schemes
   - [ ] Each scheme: benefit in one line, documents checklist, official link, deadline if known
   - [ ] Labelled "likely eligible — confirm at the official portal or CSC"
7. **Hindi / English and local units.** *As Ramesh, I want everything in Hindi so that I can use it alone.*
   - [ ] Every string in locale files; language switch on every page; Devanagari font loaded
   - [ ] Units switch acre / bigha / hectare and kg / quintal; crops shown by local name
8. **Trust layer on every answer.**
   - [ ] Source line ("Agmarknet, 6 Oct"; "Open-Meteo"; "your soil card")
   - [ ] Confidence badge (high / medium / low) and an "Ask an expert" link to district KVK and Kisan Call Centre
9. **PWA, performance and access.**
   - [ ] Installable; last results of every tool readable offline
   - [ ] First load under 300 KB JS+CSS; LCP under 3 s on throttled 4G
   - [ ] Tap targets ≥ 48 px; WCAG AA contrast; status never shown by colour alone

### P1 — Phase 2 fast follows

- **Crop Doctor:** leaf photo → top-3 likely issues with confidence; below a threshold, show "Not sure — send to expert". Treatments list non-chemical options first and name active ingredients, never brands. Fine-tuned on field images (PlantDoc + own photos), not PlantVillage alone.
- **Sensor Hub:** pair an ESP32 node (moisture, temperature, EC; NPK probe marked "estimate") over MQTT/HTTP; readings feed the farm profile and the irrigation advisor; calibration step against the soil card.
- **Field health:** draw field boundary; Sentinel-2 NDVI/NDMI map every \~5 days with "check this corner" zones.
- **Farm diary:** log costs, yield, sales; season P&L per plot; export PDF.
- **Crop calendar:** stage-wise tasks from sowing date, adjusted by weather.
- **Voice input:** Hindi speech → routed to the right tool (Bhashini).

### P2 — design for, don't build

- Pest risk alerts, PMFBY claim helper, loan-ready farm report, sell-or-hold range, FPO multi-farm view, AgriStack Farmer ID link.
- Architecture implication: the farm profile is the core entity. Every tool reads from it and writes to a per-plot event log, so the diary, reports and FPO views come later without schema changes.

## Spec — Success metrics

Judge Phase 1 on whether farmers finish tasks and act on the answer, not on downloads or model accuracy.

| Metric | Type | Success | Stretch | How measured | When |
| --- | --- | --- | --- | --- | --- |
| Task completion in Hindi, unaided | Leading | 80% | 90% | Moderated tests, ≥ 8 farmers, 6 tasks each | End of week 6 |
| Time to first useful answer, guest | Leading | < 2 min | < 60 s | Stopwatch in tests + analytics event | Week 6 |
| Farmers who say they'd act on the answer | Leading | 60% | 75% | Post-task question in tests | Week 6 |
| Fertilizer output matches ICAR/SHC | Quality | 10/10 within 1 bag | — | Hand-checked cases | Before launch |
| Crop Planner top-3 contains the crop a good local farmer chose | Quality | 70% of 30 records | 80% | Own field records | Week 8 |
| LCP on throttled 4G, mid-range Android | Quality | < 3 s | < 2 s | Lighthouse mobile | Every release |
| Repeat use within a season | Lagging | 40% of pilot farmers return | 60% | Analytics, 20-farmer pilot | End of semester |

Analytics must be privacy-light: no names or phone numbers in events, consent on first save, in line with the DPDP Act 2023.

## Spec — Roadmap

Phase 1 is six weeks of software only, so every farmer with a phone benefits before any hardware is built.

&#91;embedded content: AgriSense 2.0 roadmap · 3 phases, 3 gates\]

Gate 0 comes first: if farmers won't trust a printed crop ranking, rethink Crop Planner before writing code for it.

## Riskiest assumptions and open questions

The riskiest assumption is that farmers will trust a crop ranking from an app over their dealer. Test it with paper before writing code.

| Assumption | Confidence | Cheapest test | By |
| --- | --- | --- | --- |
| Farmers trust an app's profit ranking over the dealer | Low | Show 8 farmers a printed Crop Planner card for their own field; ask what they'd do | Week 1 |
| Farmers can find their Soil Health Card values | Medium | Ask in the same 8 interviews; photograph cards with consent | Week 1 |
| Agmarknet API is fresh enough for nearby mandis | Medium | Get an API key; pull 2 weeks of data for 10 mandis near Greater Noida | Week 1 |
| A guest-first flow converts to saved farms | Medium | Count "Save my farm" taps in the pilot | Week 6 |
| Profit estimates are within a believable range | Low | Compare against 30 real farm records and KVK cost-of-cultivation figures | Week 4 |
| Low-cost NPK probes track soil card values | Low | Calibrate one probe against 5 lab-tested samples | Phase 2 start |

### Open questions

- [ ] **Stack:** stay on Flask + Jinja + HTMX + Tailwind (light, matches the team's skills) or move to React/Next? My recommendation: Flask + HTMX for speed on low-end phones. — *engineering*
- [ ] **Database on Render:** SQLite is wiped on redeploys; move to managed Postgres (Render, Supabase or Neon free tier)? — *engineering*
- [ ] **Which deployed `app.py` is live:** the hashed, sqlite3 rewrite or the project copy with plain-text passwords? — *team*
- [ ] **Target districts for Phase 1:** Gautam Buddh Nagar + Bulandshahr suggested, for field access from campus. — *team*
- [ ] **Farmer access:** can a KVK or the university's rural outreach set up 8–10 interviews? — *team / faculty*
- [ ] **Name:** the folder says AgriSense, the course project says CropSense. Pick one before the redesign. — *team*
- [ ] **Crop list:** data.csv covers 22 crops, including coffee and apple, but not wheat, mustard or sugarcane — the main crops in western UP. Add them with district yield data? — *data*

## Sources

- *AgriSense 2.0: Upgrading a Crop Recommender into a Voice-First Platform…* — the project's research doc. All competitor figures above come from it and were not re-verified for this brief; most are company-reported.
- Project files `app.py`, `data.csv` (profiled: 2,683 rows, 22 crops, 1 duplicate row, no location, season or price columns; no wheat, mustard or sugarcane).
- Capability ratings are our own assessment from public product descriptions, not hands-on testing. Re-check before using them in a jury deck.
