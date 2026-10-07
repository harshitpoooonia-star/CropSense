# ADR-001: Frontend stack

**Status:** Proposed
**Date:** 2026-10-07
**Deciders:** AgriSense team (4) — sign-off below

## Context

AgriSense 2.0 replaces a login-walled single form with a public home page and
five-tab app (Today, Plan, Field, Market, More) built on one farm profile.
See [spec](../AgriSense-2.0-spec.md), "Website redesign" and P0-7/P0-9.

Forces:

- **Users:** smallholders on shared 2 GB Android phones, patchy 4G, Hindi first.
- **Budgets (P0-9, CLAUDE.md):** first load < 300 KB JS+CSS, LCP < 3 s on
  throttled 4G, 360 px baseline, tap targets ≥ 48 px. Design doc goal: under
  100 KB of JS.
- **Offline:** installable PWA, last result of every tool readable offline.
- **Team:** 4 students, 6 weeks. The current app is Flask + Jinja; the ML
  (scikit-learn) is Python and must run server-side.
- **Hosting:** Render free tier (see ADR-002 for its limits).
- **i18n:** every string in hi + en catalogues, switchable on every page.

Today's app (`app.py`, `templates/index.html` at 65 KB of inline markup) loads
Tailwind via CDN, Bootstrap and Lottie animations, and has no i18n.

## Decision

**Flask + Jinja templates + HTMX + Tailwind v4 built with the standalone CLI**
(no Node in the build). Server renders every page and every partial. Client JS
is HTMX plus a few small vanilla modules (guest profile in localStorage, unit
switch, share, service worker). Any further JS library needs its own ADR.

## Options Considered

### Option A: Flask + Jinja + HTMX + Tailwind (standalone CLI) — recommended

| Dimension | Assessment |
|---|---|
| Complexity | Low. One Python app, one deploy, templates the team already writes. |
| Cost | Free. One Render web service. |
| Performance | Best of the three. HTMX is ~16 KB min+gzip (check when pinning); pages are HTML from the server, so LCP doesn't wait for JS. |
| Offline / PWA | Service worker caches HTML pages and HTMX partials like any other response (Section 10). |
| i18n | Flask-Babel in templates and Python, one catalogue system. |
| Team familiarity | High: the current app is Flask + Jinja. |

**Pros**
- Smallest JS payload; the 300 KB budget is mostly fonts and CSS.
- ML, data adapters and templates in one process; no API layer to design first.
- Tailwind standalone CLI is a single binary: no `node_modules`, no npm audit churn.
- Easy to make every result a shareable, printable HTML page (Pooja persona).

**Cons**
- Rich client interactions (map pin, drag-to-draw boundary) need hand-written JS;
  Leaflet is loaded only on the map step.
- Guest-first means some state lives in the browser (localStorage) and must be
  sent with each request (see ADR-003), which plain SSR doesn't do by default.
- Fewer ready-made component libraries; macros are built by us (Section 3).

### Option B: React / Next.js

| Dimension | Assessment |
|---|---|
| Complexity | High. Second codebase and deploy, plus an API contract to Flask for ML. |
| Cost | Second service (Vercel or Render). Free tiers exist but add another limit set. |
| Performance | Worst of the three. Framework runtime is commonly 80–100 KB gzip before app code (measure if reconsidered); hydration on a 2 GB phone adds input delay. |
| Offline / PWA | Good tooling, but more moving parts. |
| i18n | next-intl or similar, separate from Python messages: two catalogues. |
| Team familiarity | Mixed; the skills pack's react-best-practices exists, but nobody has shipped Next here. |

**Pros**
- Huge ecosystem; easy rich interactions.
- Strong hiring/portfolio signal.

**Cons**
- Spends much of the JS budget before any feature.
- Splits a 4-person team across two stacks in a 6-week phase.
- Two translation systems for a Hindi-first product.

### Option C: Flask + Jinja + Alpine.js (with or without HTMX)

| Dimension | Assessment |
|---|---|
| Complexity | Low–medium. |
| Cost | Free, same as A. |
| Performance | Good. Alpine is a similar size to HTMX; both together roughly double it. |
| Team familiarity | Low for Alpine. |

**Pros**
- Declarative client state (tabs, toggles, unit switch) without writing listeners.

**Cons**
- A second client paradigm next to HTMX; server-driven partials already cover
  most of what Alpine would do.
- The client-side state we need (guest profile, unit, language) is small enough
  for ~100 lines of vanilla JS.

## Trade-off Analysis

The binding constraints are the phone and the network, not developer comfort.
A wins on payload and LCP because content arrives as HTML. B buys interaction
richness that the six tools don't need (they are forms that return a result
card) at the cost of the JS budget, a second deploy and a second i18n system.
C is close to A; it loses only because it adds a library for a problem
vanilla JS already solves at this size. If the profile wizard or Field tab
outgrows vanilla JS, adding Alpine later is a small, reversible ADR.

## Consequences

- **Easier:** budgets, server-side ML and trust layer in one place, one
  translation catalogue, printable/shareable result pages, simple deploys.
- **Harder:** map drawing (Phase 2 field boundary) and any offline *editing*
  need custom JS; we must design how localStorage state reaches the server.
- **Rules this sets:**
  - Every HTMX endpoint returns HTML; a full-page GET of the same URL must
    also work (progressive enhancement, deep links, offline cache keys).
  - No CDN Tailwind in production; the CLI builds a minified CSS file.
  - Leaflet and any other heavy asset loads only on the screen that needs it.
  - Lottie, Bootstrap and the `static/*.jpg` hero images are retired in Section 3.
- **Revisit if:** Phase 2 needs offline data entry (farm diary) beyond what a
  service worker + small JS can do, or the team adds a native app.

## Action Items

1. [ ] Team sign-off on this ADR.
2. [ ] Section 2: app factory + blueprints on Flask; pin HTMX version and vendor it into `static/` (no CDN at runtime).
3. [ ] Section 3: add the Tailwind v4 standalone CLI binary to the build (download script + checksum, not committed), `@theme` tokens, minified output.
4. [ ] Section 3: retire Bootstrap, Lottie JSON and hero images; record before/after page weight.
5. [ ] Section 10: Lighthouse budget check in CI on `/`, `/plan`, `/market`, `/schemes`.

## Sign-off

| Name | Role | Agree / Disagree | Date |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |
