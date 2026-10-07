# Gate 0 kit: 8 farmer interviews (Gautam Buddh Nagar + Bulandshahr)

Week 1, before any Crop Planner code. Source: "Riskiest assumptions" in
[docs/AgriSense-2.0-spec.md](../AgriSense-2.0-spec.md).

**Decision rule:** if **fewer than 5 of 8** farmers say they would act on the
Crop Planner card, flag Crop Planner for a rethink before Section 5.

Contents

1. [Research plan](#1-research-plan)
2. [Consent script](#2-consent-script--सहमति)
3. [Interview guide (20 min)](#3-interview-guide-20-min--बातचीत-की-गाइड)
4. [Crop Planner card (print)](#4-crop-planner-card-print)
5. [Results sheet (print)](#5-results-sheet-print)
6. [After the 8 interviews](#6-after-the-8-interviews)

---

## 1. Research plan

### What we need to learn

| # | Assumption (from the spec) | Confidence now | What answers it |
| --- | --- | --- | --- |
| A1 | Farmers trust an app's profit ranking over the dealer | Low | Section F of the guide + the card |
| A2 | Farmers can find their Soil Health Card values | Medium | Section C; photo of the results table, with consent |
| A3 | Farmers check a trader's price against something | Unknown | Section D |
| A4 | Schemes are claimed, and papers are the pain point | Unknown | Section E |

A1 decides the gate. A2–A4 feed Sections 4, 6, 7 and 9.

### Participants

- 8 farmers: 4 in Gautam Buddh Nagar, 4 in Bulandshahr.
- Own or lease and work 1–5 acres; make the sowing decision themselves.
- Mix: at least 2 who say they have a Soil Health Card, at least 2 who say they don't; at least 1 woman farmer if possible; at least 1 tenant/lessee.
- Not: input dealers, FPO staff, family of team members.
- Recruit through the district KVK or the university's rural outreach (open question in the spec; settle this first).

### Roles and kit

| Role | Job |
| --- | --- |
| Interviewer (Hindi speaker) | Asks the questions, shows the card. Doesn't explain or defend the card. |
| Note-taker | Fills the results sheet live, writes quotes word for word, times the session |

Bring: printed consent script, 2 printed cards per farmer (district version, see §4), 8 results sheets, pen, phone for photos (only with consent), a cover sheet (blank paper) to mask personal fields on the soil card.

### Rules for the interviewer

- Ask about **what they did last season**, not what they would do in general.
- Don't sell the app. Don't say "AI". Don't say the card is right.
- Silence is fine. Wait 5 seconds before the next question.
- If they ask for advice, say: "हम सीख रहे हैं, सलाह नहीं दे सकते। KVK या किसान कॉल सेंटर 1800-180-1551 पर पूछें।" (We are learning and can't advise; ask KVK or Kisan Call Centre.)
- Don't record names or phone numbers anywhere. Each farmer gets a code: GBN-1…GBN-4, BSR-1…BSR-4.

---

## 2. Consent script / सहमति

Read aloud before any question. Tick the boxes on the results sheet. If the
answer to the first question is no, thank them and stop.

> Written to follow the purpose-limitation, consent and erasure principles of
> India's Digital Personal Data Protection Act, 2023. Have a faculty
> supervisor check it against the university's research-ethics rules before
> the first interview.

| हिंदी (पढ़कर सुनाएँ) | English |
| --- | --- |
| नमस्ते, हम [विश्वविद्यालय का नाम] के छात्र हैं। हम किसानों के लिए एक मुफ़्त मोबाइल टूल पर काम कर रहे हैं, जो कोई बीज, खाद या दवा नहीं बेचता। | Hello, we are students from [university]. We are working on a free phone tool for farmers that sells no seeds, fertilizer or sprays. |
| हम 20 मिनट आपसे खेती के फ़ैसलों के बारे में बात करना चाहते हैं। सही या गलत जवाब कुछ नहीं है। | We'd like 20 minutes to talk about your farming decisions. There are no right or wrong answers. |
| हम आपका नाम, फ़ोन नंबर या पता नहीं लिखेंगे। आपकी बातें सिर्फ़ इस प्रोजेक्ट के लिए इस्तेमाल होंगी और किसी को बेची या दी नहीं जाएँगी। | We won't write down your name, phone number or address. What you say is used only for this project and is not sold or given to anyone. |
| आप कभी भी रुक सकते हैं या किसी सवाल का जवाब न देने को कह सकते हैं। | You can stop at any time or skip any question. |
| **क्या हम बात शुरू करें?** ☐ हाँ ☐ नहीं | **May we start?** ☐ Yes ☐ No |

**Soil Health Card photo (ask only in Section C, only if they have the card):**

| हिंदी | English |
| --- | --- |
| क्या हम आपके मृदा स्वास्थ्य कार्ड की सिर्फ़ जाँच वाली तालिका (N, P, K, pH वाली) की फ़ोटो ले सकते हैं? नाम, पता, मोबाइल और आधार वाला हिस्सा हम कागज़ से ढक देंगे। | May we photograph only the test-results table (N, P, K, pH) on your Soil Health Card? We'll cover the name, address, mobile and Aadhaar part with paper. |
| यह फ़ोटो सिर्फ़ यह समझने के लिए है कि ऐप में ये नंबर कैसे भरे जाएँ। प्रोजेक्ट खत्म होने पर हम इसे मिटा देंगे। आप कहें तो आज ही मिटा देंगे। | The photo is only to understand how the app should read these numbers. We delete it when the project ends, or today if you ask. |
| **क्या हम फ़ोटो ले सकते हैं?** ☐ हाँ ☐ नहीं | **May we take the photo?** ☐ Yes ☐ No |

Photo handling: store on the team's shared drive only, file name = farmer code
(e.g. `BSR-2_shc.jpg`), never in this git repo. Delete the copy on the phone the
same day. Delete all photos at project end.

---

## 3. Interview guide (20 min) / बातचीत की गाइड

Times are targets. If short of time, protect **F (card)** and cut E.

### A. Warm-up — 2 min

| हिंदी | English |
| --- | --- |
| आप कितने साल से खेती कर रहे हैं? कितनी ज़मीन पर? अपनी है या ठेके/बटाई पर? | How long have you farmed? How much land? Own, leased or sharecropped? |
| पिछली रबी और खरीफ़ में क्या-क्या बोया था? | What did you sow last rabi and last kharif? |
| सिंचाई कैसे होती है? (ट्यूबवेल / नहर / बारिश / दूसरे से पानी) | How do you irrigate? (tubewell / canal / rain-fed / buy water) |

Note-taker: area **in the unit they use** (bigha, acre, killa) and the crops.

### B. Choosing a crop, and who advises — 5 min

| हिंदी | English | Probe / जाँच |
| --- | --- | --- |
| पिछली रबी में [फसल] बोने का फ़ैसला कैसे किया? शुरू से बताइए। | How did you decide to sow [crop] last rabi? Walk me through it. | कब सोचना शुरू किया? किससे बात की? / When did you start thinking? Whom did you talk to? |
| इस फ़ैसले में सबसे ज़्यादा किसकी बात मानते हैं? | Whose word counts most in that decision? | दुकानदार, पड़ोसी, परिवार, KVK, यूट्यूब, कोई ऐप? / Dealer, neighbour, family, KVK, YouTube, an app? |
| क्या कभी किसी की सलाह से नुकसान हुआ? क्या हुआ था? | Has anyone's advice ever cost you money? What happened? | |
| पिछले साल कोई और फसल बोने का सोचा था पर नहीं बोई? क्यों? | Did you consider a different crop last year but not sow it? Why not? | पैसा, पानी, बाज़ार, जोखिम? / Money, water, market, risk? |

### C. Soil Health Card — 3 min

| हिंदी | English | Probe |
| --- | --- | --- |
| क्या आपके पास मृदा स्वास्थ्य कार्ड है? | Do you have a Soil Health Card? | कब बना था? / When was it issued? |
| क्या आप अभी उसे ला सकते हैं? | Could you fetch it now? | Note: found in < 5 min? yes/no |
| (कार्ड हो तो) इसमें नाइट्रोजन कहाँ लिखा है, दिखाइए। | (If they have it) Show me where nitrogen is written. | Don't help. Note if they find N, P, K without help. |
| खाद खरीदते समय क्या इस कार्ड को देखते हैं? | Do you look at this card when buying fertilizer? | नहीं तो क्यों? / If not, why? |

Then the photo consent (§2) if they have the card.

### D. Selling and checking a price — 3 min

| हिंदी | English | Probe |
| --- | --- | --- |
| पिछली बार गेहूँ/धान कहाँ और किसे बेचा? | Where and to whom did you last sell wheat/paddy? | मंडी, आढ़ती, गाँव का व्यापारी, सरकारी खरीद? / Mandi, commission agent, village trader, govt procurement? |
| जो भाव मिला, वह ठीक है या नहीं — यह कैसे पता किया? | How did you know whether the price offered was fair? | किसी से पूछा? फ़ोन पर देखा? / Asked someone? Checked a phone? |
| किसी और मंडी में बेचने के बारे में सोचा? क्यों/क्यों नहीं? | Did you consider another mandi? Why or why not? | भाड़ा, दूरी, उधार? / Transport, distance, credit? |

### E. Schemes — 2 min

| हिंदी | English | Probe |
| --- | --- | --- |
| कौन-सी सरकारी योजनाओं का पैसा या फ़ायदा मिलता है? | Which government schemes do you get money or benefits from? | Don't name schemes first. Note what they name. |
| किसी योजना में आवेदन करने में दिक्कत आई? क्या? | Any trouble applying for a scheme? What? | कागज़, CSC, ऑनलाइन, समय-सीमा? / Papers, CSC, online, deadline? |

### F. Crop Planner card — 4 min (the gate question)

Hand over the card for **their district** (§4). Fill in their area in their unit
before handing it over. Then say only:

| हिंदी | English |
| --- | --- |
| यह कार्ड एक मोबाइल टूल का नमूना है। कृपया इसे पढ़िए, जितना समय चाहिए लीजिए। | This card is a sample from a phone tool. Please read it, take your time. |

Wait. Don't explain. Then:

| # | हिंदी | English | Note-taker codes |
| --- | --- | --- | --- |
| F1 | इसमें आपको क्या समझ आया? अपने शब्दों में बताइए। | What did you understand from it? In your own words. | Understood ranking? yes / partly / no |
| F2 | अगर यह कार्ड इसी रबी में आपके खेत के लिए होता, तो क्या आप इसकी वजह से कुछ अलग करते? क्या? | If this card were for your field this rabi, would you do anything differently because of it? What? | **Would act: yes / no / maybe** + what |
| F3 | किस बात पर भरोसा हुआ और किस पर नहीं? | What did you trust on it, and what not? | Quote |
| F4 | इस कार्ड को किससे दिखाकर पक्का करेंगे? | Who would you show this to before deciding? | Dealer / family / KVK / no one |
| F5 | आपके दुकानदार की सलाह और यह कार्ड अलग बात कहें, तो किसकी मानेंगे? क्यों? | If your dealer and this card disagreed, whom would you follow? Why? | Card / dealer / depends + why |

**Coding F2 for the decision rule** (note-taker decides after the session, then
the interviewer checks):

- **Yes** = names a concrete change because of the card: would sow or try a
  crop from the card, change the area under a crop, or take the card to a KVK
  before sowing.
- **Maybe** = "सोचेंगे" / "will think about it" with no concrete change.
- **No** = would do the same as planned, or doesn't trust it.
- For the gate, **only Yes counts**. Maybe counts as No.

### G. Wrap-up — 1 min

| हिंदी | English |
| --- | --- |
| आपके फ़ोन पर इंटरनेट चलता है? फ़ोन आपका है या घर में साझा? | Does your phone have internet? Is it yours or shared at home? |
| कोई बात जो हमने नहीं पूछी पर पूछनी चाहिए थी? | Anything we didn't ask that we should have? |
| धन्यवाद। यह कार्ड सिर्फ़ नमूना था, असली सलाह नहीं। फ़सल का फ़ैसला KVK या किसान कॉल सेंटर 1800-180-1551 से पूछकर करें। | Thank you. The card was only a sample, not real advice. For crop decisions, ask the KVK or Kisan Call Centre 1800-180-1551. |

The last line is a required debrief: never leave a farmer thinking a prototype
card is advice.

---

## 4. Crop Planner card (print)

One card per **district and season** (rabi 2026–27), prepared before the
visits, so the same card is shown to the 4 farmers in that district. Only the
area line is filled in per farmer on the spot.

**Filling rules (CLAUDE.md: never invent agronomic numbers or prices):**

- Pick the 3 crops with the district KVK or from the district's
  package-of-practice; write the source on the card.
- ₹/acre range = (yield range × recent modal price) − cost of cultivation.
  Yield and cost from a citable source (KVK, state agriculture department,
  CACP cost-of-cultivation reports); modal price from the Agmarknet pull
  (`scripts/check_agmarknet.py`). Write each source and its date in the
  source line.
- If a number has no source, write **"पता नहीं / not known"** in that box.
  Don't estimate.
- Water need and risk: low / medium / high, with the reason in the "why" lines.
- Confidence: tick one. Use **low** unless every number on the card has a source.

Print on A5 or half an A4 sheet, 2 copies per farmer.

```text
┌──────────────────────────────────────────────────────────────────┐
│  AgriSense · फसल योजना / Crop Planner              नमूना / SAMPLE │
│  रबी / Rabi 2026–27 · ज़िला / District: ____________________     │
│  आपका खेत / Your field: ______ बीघा / एकड़ / bigha / acre          │
│  सिंचाई / Irrigation: ट्यूबवेल / नहर / बारिश  (tubewell/canal/rain) │
├──────────────────────────────────────────────────────────────────┤
│  1. फसल / Crop: ____________________                              │
│     अनुमानित मुनाफ़ा / Likely profit: ₹ ______ – ₹ ______ प्रति एकड़ │
│     पानी / Water:  ☐ कम low  ☐ मध्यम medium  ☐ ज़्यादा high         │
│     जोखिम / Risk:  ☐ कम low  ☐ मध्यम medium  ☐ ज़्यादा high         │
│     क्यों / Why:  • ________________________________________     │
│                   • ________________________________________     │
│                   • ________________________________________     │
├──────────────────────────────────────────────────────────────────┤
│  2. फसल / Crop: ____________________                              │
│     अनुमानित मुनाफ़ा / Likely profit: ₹ ______ – ₹ ______ प्रति एकड़ │
│     पानी / Water:  ☐ कम low  ☐ मध्यम medium  ☐ ज़्यादा high         │
│     जोखिम / Risk:  ☐ कम low  ☐ मध्यम medium  ☐ ज़्यादा high         │
│     क्यों / Why:  • ________________________________________     │
│                   • ________________________________________     │
├──────────────────────────────────────────────────────────────────┤
│  3. फसल / Crop: ____________________                              │
│     अनुमानित मुनाफ़ा / Likely profit: ₹ ______ – ₹ ______ प्रति एकड़ │
│     पानी / Water:  ☐ कम low  ☐ मध्यम medium  ☐ ज़्यादा high         │
│     जोखिम / Risk:  ☐ कम low  ☐ मध्यम medium  ☐ ज़्यादा high         │
│     क्यों / Why:  • ________________________________________     │
│                   • ________________________________________     │
├──────────────────────────────────────────────────────────────────┤
│  स्रोत / Sources:                                                 │
│   भाव / Price: Agmarknet, ______ मंडी, तारीख / date ______         │
│   उपज और लागत / Yield & cost: ______________, ______ (date)       │
│  भरोसा / Confidence:  ☐ ज़्यादा high  ☐ मध्यम medium  ☐ कम low      │
│  पक्का नहीं? / Not sure? KVK ______________ · किसान कॉल सेंटर      │
│  1800-180-1551                                                   │
│  हम बीज, खाद या दवा नहीं बेचते। / We don't sell seeds or sprays.   │
└──────────────────────────────────────────────────────────────────┘
```

Why lines: plain words, one factor each, e.g. the shape "पिछले 2 हफ़्ते में
[मंडी] में भाव ___ रहा" (price at [mandi] was ___ in the last 2 weeks) or
"आपकी सिंचाई [स्रोत] से है, इसलिए पानी की ज़रूरत वाली फ़सल ठीक है" (your
irrigation is [source], so a water-hungry crop is workable). Fill the blanks
from the same sources as the numbers.

---

## 5. Results sheet (print)

One per farmer. No names, phone numbers or addresses.

```text
Farmer code: ______ (GBN-1..4 / BSR-1..4)   Date: ________   Village/block: ____________
Interviewer: ________   Note-taker: ________   Start ____ End ____ (min: ____)

Consent to talk:  ☐ yes          Consent to SHC photo:  ☐ yes  ☐ no  ☐ no card

A. Land: ____ (unit: bigha/acre/killa)  ☐ own ☐ lease ☐ share   Irrigation: ____________
   Last rabi: ____________   Last kharif: ____________

B. Main advisor:  ☐ input dealer ☐ neighbour ☐ family ☐ KVK ☐ YouTube ☐ app ☐ other ____
   Lost money on advice?  ☐ yes ☐ no   What: ________________________________
   Quote: "____________________________________________________________"

C. Has Soil Health Card:  ☐ yes ☐ no ☐ lost/not sure     Year issued: ____
   Found it within 5 min:  ☐ yes ☐ no
   Found N, P, K values without help:  ☐ yes ☐ partly ☐ no
   Uses it when buying fertilizer:  ☐ yes ☐ no   Why not: _____________________

D. Sold last crop at:  ☐ mandi ☐ commission agent ☐ village trader ☐ govt procurement
   Checks price against:  ☐ nothing ☐ asks others ☐ phone/app ☐ mandi board ☐ other ____
   Quote: "____________________________________________________________"

E. Schemes named (their words): ______________________________________________
   Trouble applying:  ☐ yes ☐ no   What: ________________________________

F. Card
   F1 Understood ranking:  ☐ yes ☐ partly ☐ no
   F2 WOULD ACT:  ☐ YES  ☐ MAYBE  ☐ NO      What would change: ________________
   F3 Trusted: ______________________   Didn't trust: ______________________
   F4 Would show it to:  ☐ dealer ☐ family ☐ KVK ☐ no one ☐ other ____
   F5 Dealer vs card:  ☐ card ☐ dealer ☐ depends   Why: ______________________
   Quote: "____________________________________________________________"

G. Phone:  ☐ own smartphone ☐ shared smartphone ☐ keypad phone ☐ none   Internet: ☐ yes ☐ no
   Anything we missed: __________________________________________________

Debrief line read ("sample, not advice; ask KVK / 1800-180-1551"):  ☐ yes
```

### Tally (fill after all 8)

| Code | Would act (F2) | Has SHC | Found N/P/K | Main advisor | Checks price against | Phone |
| --- | --- | --- | --- | --- | --- | --- |
| GBN-1 | | | | | | |
| GBN-2 | | | | | | |
| GBN-3 | | | | | | |
| GBN-4 | | | | | | |
| BSR-1 | | | | | | |
| BSR-2 | | | | | | |
| BSR-3 | | | | | | |
| BSR-4 | | | | | | |
| **Total** | **Yes: __ / 8** | __ / 8 | __ / 8 | | | |

**Gate 0 verdict:** Yes ≥ 5 → Crop Planner goes ahead as specced.
Yes ≤ 4 → **flag Crop Planner for rethink before Section 5**, and write down
what F3 and F5 say people didn't trust.

---

## 6. After the 8 interviews

1. Same day: note-taker types the sheet into `docs/research/gate-0-results.md`
   (codes only), and deletes SHC photos from phones.
2. Fill the tally. Apply the decision rule as written; don't round Maybe up.
3. Affinity-map the quotes into themes on: who advises, why trust/distrust the
   card, how prices are checked, scheme pain points.
4. Update the spec's "Riskiest assumptions" table with the new confidence for
   A1–A4, and note anything that changes Sections 4–9 (e.g. if few farmers can
   find N/P/K, the profile wizard needs a photo or district-default path first).
5. Together with the Agmarknet pull result, record the Gate 0 decision in the
   roadmap checklist.
