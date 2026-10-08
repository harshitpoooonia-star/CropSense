# Launch review: v2.0.0 (Section 11)

**Date:** 2026-10-08 · **Commit:** the `section-11/test-launch` merge
**Done when (roadmap):** 80% unaided task completion in Hindi with 8+ farmers,
and v2.0.0 deployed through [deploy-checklist.md](deploy-checklist.md).
**Status: not done.** The software checks below pass; the farmer sessions,
the first deploy and the release tag are still to do (see "Before the tag").

---

## 1. Six-task rehearsal (Playwright)

[tests/e2e/test_moderated_tasks.py](../tests/e2e/test_moderated_tasks.py): one
guest phone, 360×740, Hindi, the six tasks of the
[moderated test kit](research/moderated-test-kit.md), moving only by tapping.
Screenshots per step: `tests/artifacts/tasks/` (30 images). All six pass.

| # | Task | Path tapped | Time to answer* |
| --- | --- | --- | --- |
| 1 | Plan a crop | Home tile → rabi → set up field (GPS, 2.5 acre, tubewell, skip card) → plan | 2.7 s |
| 2 | Fertilizer bags (wheat) | Field tab → Fertilizer for this field → standard dose | 0.8 s |
| 3 | Trader's offer | Home tile → wheat, ₹2,000 → verdict | 1.1 s |
| 4 | Spray tomorrow | Today tab → weather card → tomorrow | 0.4 s |
| 5 | Find a scheme | More tab → schemes → 6 questions | 1.4 s |
| 6 | Save my farm | More tab → save my farm → phone, PIN, consent | 0.8 s |

\*Machine time on a local server: it shows each task has a short, working
path. It says nothing about how long a farmer takes; the sessions measure that.

**Found and fixed:** mustard topped the rabi plan, but fertilizer has no cited
dose for mustard, so the card's "Fertilizer for this crop" button led to a page
that couldn't count bags. Cards now show the button only for crops with a cited
dose and otherwise say "ask your KVK". The fertilizer page's message for such a
crop no longer suggests the Soil Health Card path, which can't be chosen for it.

## 2. Accessibility review (WCAG 2.2 AA)

The `/design:accessibility-review` skill isn't installed in this workspace, so
the review is automated in [tests/e2e/a11y.py](../tests/e2e/a11y.py) and
[test_accessibility.py](../tests/e2e/test_accessibility.py) (no axe-core:
no new JS library without an ADR). It runs on all 15 screens in Hindi and
English, every tool's answer in both languages, and keyboard focus on 6 pages.

| Check | Result |
| --- | --- |
| Text contrast 4.5:1 (3:1 large), on the real background | Pass (after fix 2) |
| 48 px tap targets | Pass |
| Focus visible, ring 3:1 against its surroundings | Pass (after fix 1) |
| Focus order: no positive tabindex, follows the page | Pass |
| Status never colour alone: every good/warn/critical box has an icon and words | Pass |
| Every control named; images labelled | Pass |
| One h1, no skipped heading levels, `lang` set | Pass (after fixes 3, 4) |
| No sideways scroll at 360, 768, 1024, 1440 px | Pass |

**Fixed:**

1. **Focus ring invisible on primary buttons and the top bar.** `transition-colors`
   faded the ring in from the text colour (white on green buttons, so a white ring
   on the off-white page), and the green ring on the brown top bar was 1.6:1. The
   ring now appears at once, and is white inside the top bar.
2. The map step's disabled "Use this spot" button: white on grey was 4.1:1; now dark on light grey.
3. The wizard's "field is set up" screen had no h1 after the HTMX swap.
4. The offline page had two h1s (one per language).

**Still for a person to check:** TalkBack in Hindi on a real Android phone
(reading order, that Hindi is read in Hindi), and the app at 200% system font size.

## 3. ui-ux-pro-max pre-delivery checklist

| Item | Result |
| --- | --- |
| No emojis as icons | Pass: one SVG sprite (`_icons.html`) |
| Consistent icon set | Pass: same stroke style throughout |
| Brand logos correct | N/A: no brands, by design (neutral) |
| Hover causes no layout shift | Pass: hover changes colour/border colour only |
| Theme colours used directly | Pass: Tailwind tokens (`bg-accent`), no ad-hoc colours |
| `cursor-pointer` on clickable elements | Pass: buttons and choice rows |
| Hover feedback | Pass |
| Transitions 150–300 ms | Pass: 150 ms colour transitions |
| Focus states visible | Pass after the fix above (was failing) |
| Light mode contrast 4.5:1 | Pass (audit) |
| Glass/transparent elements | N/A: none |
| Borders visible | Pass: inputs 3.8:1; soft lines are decorative only |
| Dark mode | N/A: the spec's palette is light only |
| Floating elements spaced from edges; nothing hidden behind fixed bars | Pass: bottom nav has safe-area padding; pages pad 7 rem above it |
| Responsive 375/768/1024/1440 | Pass (test) |
| No horizontal scroll on mobile | Pass (every test at 360 px) |
| Images have alt text | Pass: no `<img>`; drawn bags have `role=img` + label |
| Form inputs have labels | Pass (audit) |
| Colour not the only indicator | Pass (audit) |
| `prefers-reduced-motion` respected | Pass: CSS turns animations and transitions off |

## 4. Privacy check (DPDP Act 2023, spec, ADR-003)

[tests/test_privacy.py](../tests/test_privacy.py) and the smoke test.

| Check | Result |
| --- | --- |
| Phone number stored nowhere: only its keyed hash; not in any table or event after using every tool | Pass |
| No column for a person's name; `farm.name` is the farm's own label and nothing fills it yet | Pass |
| Event log payloads: tool results, sources, confidence; no phone or name | Pass |
| Consent asked and recorded (time + version) before a farm is saved | Pass |
| Guests: nothing written to the server; the profile stays on the phone | Pass |
| No third-party requests on any page (no analytics, ads, CDNs, web fonts); only the map step loads OSM tiles | Pass |
| No personal data in logs: the app logs nothing of its own; PINs and phones are POST bodies, never in URLs | Pass |
| Shared phones: logout and "Delete my farm" clear the phone's profile and offline copies | Pass (e2e) |

**Gap:** there are **no analytics** yet. The spec's "time to first useful answer"
and "repeat use" metrics assume privacy-light analytics events. Until the team
decides how (and records it in an ADR), those two metrics come from the
moderated sessions only.

## 5. Performance (unchanged from Section 10)

`python scripts/perf_budget.py`, 360 px, slow 4G, 4× CPU, cold first load:
JS+CSS 26.8 KB on every page (budget 300 KB), LCP 0.74–0.92 s (budget 3 s). All pass.

## 6. Before the tag

The tag goes on the commit that is actually deployed (deploy checklist §8), so
v2.0.0 is **not** tagged yet. In order:

1. [ ] Push the repo to GitHub and see CI pass there (it has only run locally).
2. [ ] Team items still open from earlier sections: `DATA_GOV_IN_KEY`; verify the
       cited data rows (`verified=false`); KVK phone numbers; bigha sizes; district
       soil defaults; the consent text's grievance contact; review the proposed
       weather thresholds and `FAIR_BAND_PCT`; check schemes and set `verified: true`;
       sign ADR-001 to ADR-006.
3. [ ] First deploy to Render + Neon through [deploy-checklist.md](deploy-checklist.md).
4. [ ] Moderated sessions with 8+ farmers on the deployed app
       ([kit](research/moderated-test-kit.md)); fix must-fix problems; re-test.
5. [ ] Pass on completion (≥ 80%), task 1 time (< 2 min) and would-act (≥ 60%):
       tag `v2.0.0` on the deployed commit and write the release notes.
