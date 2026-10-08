# Architecture decision records

One file per decision. Status moves Proposed → Accepted once all four team
members sign the table at the bottom of the ADR. Change an accepted decision
with a new ADR that supersedes it; don't edit the old one.

| ADR | Decision (recommended) | Status |
|---|---|---|
| [001](ADR-001-frontend.md) | Frontend: Flask + Jinja + HTMX + Tailwind v4 standalone CLI | Proposed |
| [002](ADR-002-database.md) | Database: Neon Postgres in prod, SQLite locally, Flask-Migrate; Neon branches for migration rehearsal/backup | Proposed |
| [003](ADR-003-data-model.md) | Data model: user → farm → plot (+ soil_card), append-only per-plot `event` log, shared caches; guest profile in localStorage; phone stored only as keyed hash | Proposed |
| [004](ADR-004-external-data.md) | External data: adapter per source, read-through DB cache, daily price warm-up via GitHub Actions, staleness always shown, offline fixtures | Proposed |
| [005](ADR-005-map-pin.md) | Farm pin: Leaflet 1.9.4 vendored, OSM tiles, loaded only on the wizard's map step; GPS and district list as fallbacks | Proposed |
| [006](ADR-006-offline.md) | Offline: hand-written service worker; pages and server-marked tool answers kept on the phone, profile blocks stripped, cleared on logout/delete | Proposed |

## Decisions the team must make before Section 2

- **Hosting cold start** (ADR-002): Render free spins down after 15 min idle
  (~1 min to wake), which breaks LCP < 3 s. Paid instance for the pilot, or
  demo-only acceptance?
- ~~**Forgotten PIN** (ADR-003)~~: decided 2026-10-08, staff-assisted reset
  by a `helper` with a one-time code.
- **FPO/KVK staff accounts that own several farms** (ADR-003): Phase 1 or P2?
