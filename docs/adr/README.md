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

## Decisions the team must make before Section 2

- **Hosting cold start** (ADR-002): Render free spins down after 15 min idle
  (~1 min to wake), which breaks LCP < 3 s. Paid instance for the pilot, or
  demo-only acceptance?
- **Forgotten PIN** (ADR-003): no stored phone number means no SMS reset.
  Staff-assisted reset, or "create a new farm"?
- **FPO/KVK staff accounts** (ADR-003): Phase 1 or P2?
