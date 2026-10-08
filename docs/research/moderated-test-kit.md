# Moderated test kit: 6 tasks, 8+ farmers, in Hindi

Week 6, on the release candidate. Source: "Success metrics" in
[docs/AgriSense-2.0-spec.md](../AgriSense-2.0-spec.md) and roadmap Section 11.
The same six tasks run automatically in
[tests/e2e/test_moderated_tasks.py](../../tests/e2e/test_moderated_tasks.py):
that rehearsal checks the app works. This kit checks whether farmers can use it.

**Pass (spec):**

| Metric | Success | Stretch |
| --- | --- | --- |
| Tasks completed unaided, in Hindi (8+ farmers × 6 tasks) | 80% | 90% |
| Time to first useful answer as a guest (task 1) | under 2 min | under 60 s |
| "Would you act on this?" = yes | 60% | 75% |

Contents

1. [Before the sessions](#1-before-the-sessions)
2. [Consent script](#2-consent-script--सहमति)
3. [Session script (30 min)](#3-session-script-30-min)
4. [Stopwatch sheet (print, one per farmer)](#4-stopwatch-sheet-print-one-per-farmer)
5. [Scoring](#5-scoring)
6. [After the sessions](#6-after-the-sessions)

---

## 1. Before the sessions

### Participants

- At least 8 farmers who did **not** take part in the Gate 0 interviews (they've seen the card).
- Same profile as Gate 0: work 1–5 acres, make the sowing decision, a mix of Soil Health Card / no card, at least 1 tenant, at least 1 woman farmer if possible.
- From the five districts the planner has data for: Gautam Buddh Nagar, Bulandshahr, Ghaziabad, Hapur, Aligarh. A farmer from elsewhere uses the scenario field below.
- Not: input dealers, FPO/KVK staff, team members' families.
- Each farmer gets a code (P01, P02, …). **No names or phone numbers on any sheet.**

### The app must be ready (team checks the day before)

- [ ] The release candidate is deployed and warm (open `/api/health` 2 minutes before each session: the free tier sleeps).
- [ ] Live mandi prices: `DATA_GOV_IN_KEY` is set and `/market` shows prices from the last 3 days for wheat. **Without it task 3 can't be tested.**
- [ ] Schemes: at least the schemes a person has checked show in production (ADR-004). If none are verified yet, task 5 only reaches the "check at myScheme or a CSC" page: score it, but note it.
- [ ] Weather loads on `/weather` for the test village.

### Test phone

- A mid-range Android (2–4 GB RAM) with Chrome, in Hindi, mobile data only (no Wi-Fi), location on.
- Before **each** farmer: Chrome → Settings → Site settings → the AgriSense site → **Clear & reset**. The farmer starts as a new guest with nothing saved.
- Screen recording **only** if the farmer agrees in the consent step, and with the camera off.

### Scenario field (only for a farmer outside the five districts, or who doesn't want to use their own)

Bulandshahr, 2.5 acres, tubewell, no Soil Health Card, plans wheat for rabi.

### Roles

| Role | Job |
| --- | --- |
| Moderator (Hindi speaker) | Reads each task, then stays quiet. Never points at the screen. |
| Note-taker | Stopwatch sheet, where the farmer got stuck, quotes word for word |

### Rules for the moderator

- Read the task exactly as written. Repeat it once if asked. Don't explain buttons.
- If the farmer asks "what do I press?": "आपको जो ठीक लगे, वही दबाइए।" (Press whatever seems right to you.)
- Help only after **2 minutes stuck** or if the farmer asks to stop. Then the task is **assisted**, not unaided.
- If the farmer asks for advice: "हम ऐप जाँच रहे हैं, सलाह नहीं दे सकते। KVK या किसान कॉल सेंटर 1800-180-1551 पर पूछें।"
- Don't say the app's answer is right. Don't say "AI".

---

## 2. Consent script / सहमति

Read aloud. Continue only after a clear "हाँ".

> नमस्ते। हम एक विश्वविद्यालय की टीम हैं और खेती के लिए एक फ़ोन ऐप बना रहे हैं। आज हम ऐप की जाँच कर रहे हैं, आपकी नहीं। कोई जवाब गलत नहीं है: अगर कुछ समझ न आए, तो कमी ऐप की है।
>
> हम आपको फ़ोन पर छह छोटे काम देंगे, लगभग आधा घंटा लगेगा। हम आपका नाम या फ़ोन नंबर नहीं लिखेंगे। हम सिर्फ़ यह लिखेंगे कि काम में कितना समय लगा और कहाँ दिक्कत आई।
>
> आखिरी काम में ऐप आपका फ़ोन नंबर माँगेगा। आप चाहें तो अपना नंबर डाल सकते हैं, या हमारा दिया हुआ जाँच वाला नंबर। जाँच के बाद हम वह खेत ऐप से मिटा देंगे, जब तक आप उसे रखना न चाहें।
>
> क्या हम फ़ोन की स्क्रीन रिकॉर्ड कर सकते हैं? सिर्फ़ स्क्रीन, आपका चेहरा या आवाज़ नहीं। (हाँ / नहीं)
>
> आप कभी भी रुक सकते हैं। क्या हम शुरू करें?

Note-taker ticks: ☐ consent yes ☐ screen recording yes ☐ screen recording no

---

## 3. Session script (30 min)

Hand over the phone on the AgriSense home page. Start the stopwatch when you finish reading each task; stop it when the farmer **sees the answer** (the success screen below). After each task ask the follow-up question.

### Task 1: plan a crop

> "मान लीजिए रबी की बुआई आने वाली है। यह ऐप आपके खेत के लिए कौन-सी फसलें सुझाता है, यह पता कीजिए।"
> (Rabi sowing is coming. Find out which crops this app suggests for your field.)

**Success:** three crop cards for rabi, after the farmer set up their field (where, size, water).
**Watch for:** finding "अपना खेत जोड़ें" (Set up your field) first; the map step; the area unit (bigha/acre).

### Task 2: fertilizer bags

> "आप गेहूँ बोने वाले हैं। अपने खेत के लिए खाद की कितनी बोरियाँ लगेंगी, यह पता कीजिए।"
> (You'll sow wheat. Find out how many bags of fertilizer your field needs.)

**Success:** the bags for urea / DAP (or SSP) / potash on screen, with the total cost.
**Watch for:** the Soil Health Card vs standard dose choice.

### Task 3: check a trader's offer

> "एक व्यापारी आपके गेहूँ के लिए ₹2,000 प्रति क्विंटल दे रहा है। क्या यह भाव ठीक है?"
> (A trader offers ₹2,000 a quintal for your wheat. Is that a fair price?)

**Success:** the verdict (below / fair / above the mandi price) with the nearby mandis.
**Watch for:** typing the offer; reading the verdict, not just the list.

### Task 4: spray tomorrow

> "आपको कल फसल पर दवा छिड़कनी है। क्या कल छिड़काव ठीक रहेगा?"
> (You need to spray your crop tomorrow. Is tomorrow a good day to spray?)

**Success:** tomorrow's spray verdict and the good time window.
**Watch for:** finding it from "आज"; reading "कल" (tomorrow) and not today.

### Task 5: find a scheme

> "पता कीजिए कि आपको कौन-सी सरकारी योजनाओं का फ़ायदा मिल सकता है, और साथ क्या कागज़ ले जाने होंगे।"
> (Find out which government schemes you may get, and which papers to take.)

**Success:** the list of likely schemes with the papers to carry.
**Watch for:** the age and income-tax questions; using "छोड़ें" (Skip).

### Task 6: save my farm

> "आप चाहते हैं कि अगली बार यह ऐप आपका खेत याद रखे। ऐसा कीजिए।"
> (You want the app to remember your farm next time. Do that.)

**Success:** the farm is saved (the field page opens after saving).
**Watch for:** the PIN; reading the consent text.

### After each task / हर काम के बाद

> "अगर यह आपके असली खेत की बात होती, तो क्या आप इस जवाब के हिसाब से कुछ करते?"
> (If this were about your real field, would you act on this answer?) **हाँ / शायद / नहीं** — "क्यों?" (Why?)

(Task 6 has no answer to act on: skip the question.)

### At the end (2 min)

> "सबसे मुश्किल क्या लगा?" (What was hardest?)
> "क्या आप यह ऐप किसी और किसान को बताएँगे? क्यों?" (Would you tell another farmer about it? Why?)

Then, unless the farmer wants to keep it: **और → मेरा खेत मिटाएँ** (More → Delete my farm), and clear the site data.

---

## 4. Stopwatch sheet (print, one per farmer)

Farmer code: ____  District: ____  Own field / scenario field  Date: ____
Phone/network: ____  Moderator: ____  Note-taker: ____

| # | Task | Time (m:ss) | Result (U / A / F) | Stuck where? | Act on it? (Y / M / N) | Why / quote |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Plan a crop | | | | | |
| 2 | Fertilizer bags | | | | | |
| 3 | Trader's offer | | | | | |
| 4 | Spray tomorrow | | | | | |
| 5 | Find a scheme | | | | | |
| 6 | Save my farm | | | | — | |

U = unaided, A = assisted (moderator helped or 2 min stuck), F = failed or stopped.
Y = yes, M = maybe, N = no.

Hardest part (quote): ________________________________
Would tell another farmer? Y / N, why: ________________________________

---

## 5. Scoring

- **Completion** = U ÷ (farmers × 6). Assisted counts as **not** completed.
- **Time to first useful answer** = task 1 time, per farmer; report the median and the slowest.
- **Would act** = Y ÷ answers to the follow-up (tasks 1–5). Maybe is not yes.
- Count the same problem once per farmer. A problem 3 or more farmers hit is a **must-fix** before the release; fewer than 3 goes to the backlog with its quotes.

---

## 6. After the sessions

1. Fill the totals and send them to the team the same day:

   | Metric | Result | Pass? |
   | --- | --- | --- |
   | Completion (U ÷ all tasks) | ___ % | ≥ 80% |
   | Task 1 median time | ___ | < 2 min |
   | Would act (Y ÷ answers) | ___ % | ≥ 60% |

2. List must-fix problems with the task, the screen and the quotes. Fix, re-run
   `python scripts/run_e2e.py`, and re-test those tasks with 2 new farmers.
3. Destroy the paper sheets' rough notes after typing them up; keep only the coded table.
   Delete any screen recordings once the problems are written down.
4. Delete every farm saved during the sessions that the farmer didn't ask to keep.
