# AgriSense design system (Section 3)

Source: [`agrisense/static/src/app.css`](../agrisense/static/src/app.css) tokens,
[`agrisense/templates/macros/ui.html`](../agrisense/templates/macros/ui.html) macros,
live at `/styleguide` in Hindi and English.

The spec's constraints win over ui-ux-pro-max's generated picks. Its
`--design-system` run suggested a blue primary, Lexend/Source Sans (no
Devanagari) and an app-store landing page; none of those are used. Its UX
rules and html-tailwind guidance are applied, with 48 px targets (spec) instead
of its 44 px.

## Tokens

| Token | Hex | Use | Contrast |
|---|---|---|---|
| `bg` | `#faf7f2` | page | — |
| `surface` / `surface-2` | `#ffffff` / `#f1ebe1` | cards / muted panels | — |
| `ink` | `#2b2118` | body text | 14.7:1 on bg |
| `ink-muted` | `#5c4b3b` | secondary text | 7.8:1 on bg |
| `soil` / `soil-soft` | `#5a3b22` / `#7a5230` | top bar, bag icons, soil band | white on soil 10.1:1 |
| `accent` | `#2f6b3a` | the one green: buttons, links, focus, active tab | white on it 6.4:1 |
| `good` / `good-bg` | `#1e5a2a` / `#e3f1e3` | good verdicts, high confidence | 7.0:1 |
| `warn` / `warn-bg` | `#7a4a00` / `#fdf0d2` | caution, medium confidence | 6.6:1 |
| `crit` / `crit-bg` | `#9b1c1c` / `#fbe5e3` | don't, errors | 6.8:1 |
| `line` / `line-soft` | `#8c7b68` / `#d9cfc1` | input borders (3.8:1) / dividers | — |

`tests/test_design_tokens.py` re-checks every pair. Tailwind's default palette
is switched off (`--color-*: initial`), so only these colours exist.

Type: **Mukta** (Ek Type, SIL OFL), one family for Devanagari and Latin,
weights 400 and 700, self-hosted, `font-display: swap`, the first-paint face
preloaded per language. Body 18 px (`text-body`); key numbers 40 px
(`text-figure`).

## Rules

- One primary action per screen; bottom nav Today / Plan / Field / Market / More.
- Every tap target ≥ 48 px (`min-h-tap`); checked on every guest page by the e2e test.
- Status is icon + word + colour, never colour alone (`verdict_pill`, `confidence_badge`).
- Every result ends with source + date, confidence, Ask an expert, and Share on WhatsApp (`result_card`).
- No hero video, 3D, parallax, carousels, stock photos or emoji icons. Icons are one inline SVG sprite (`templates/_icons.html`).
- HTMX is the only JS library. Everything works without JS.
- No raw text in templates (`tests/test_i18n_templates.py`).

## Pre-delivery checklist (ui-ux-pro-max), 2026-10-08

| Item | Result |
|---|---|
| No emoji icons; one consistent icon set | Pass: own SVG sprite, 24 px grid |
| Brand logos correct | N/A: none used ("WhatsApp" is text only) |
| Hover states don't shift layout | Pass: colour/border changes only |
| Theme colours used directly | Pass: `bg-accent`, not `var()` wrappers |
| `cursor-pointer` on clickables | Pass: buttons, selects, checkbox rows; links by default |
| Hover feedback | Pass on buttons, home rows, list rows; bottom-nav tabs rely on the active state only |
| Transitions 150–300 ms | Pass: 150 ms colour transitions |
| Visible keyboard focus | Pass: 3 px green outline on `:focus-visible` everywhere |
| Light-mode contrast ≥ 4.5:1 | Pass: lowest text pair 5.98:1 |
| Dark mode | N/A: not in the spec; one light theme for outdoor reading |
| Nothing hidden behind fixed bars | Pass: sticky header; main has bottom padding for the nav |
| Responsive 375/768/1024/1440 | Pass at 360 px (e2e). Wider screens use a centred 36 rem column, not yet screenshot-tested |
| No horizontal scroll on mobile | Pass: checked on every guest page at 360 px |
| Images have alt text | N/A: no content images |
| Form inputs have labels | Pass: every input has a `<label for>` |
| Colour not the only indicator | Pass: tested in `tests/test_ui_macros.py` |
| `prefers-reduced-motion` respected | Pass: base layer disables transitions/animations |

## Known follow-ups

- Fonts are ~240 KB in total (Devanagari faces ~100 KB each). Section 10 subsets them.
- District KVK contacts on `/expert` arrive with the district table (Section 4).
- Bigha conversion is disabled until `data/area_units.csv` has a sourced size per district.
