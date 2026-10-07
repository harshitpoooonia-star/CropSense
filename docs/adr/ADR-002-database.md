# ADR-002: Database and migrations

**Status:** Proposed
**Date:** 2026-10-07
**Deciders:** AgriSense team (4) — sign-off below

## Context

The current app uses Flask-SQLAlchemy with `sqlite:///cropsense.db` and runs on
Render's free web service. Render's free web services have an **ephemeral
filesystem**: a local SQLite file is lost on every redeploy, restart or
spin-down ([Render docs](https://render.com/docs/free)). So today's sign-ups
and saved recommendations on the live site are very likely already gone after
each deploy or idle period.

2.0 needs durable storage for saved farms, plots, soil cards, the per-plot
event log, the mandi price cache and the weather cache (ADR-003). Constraints:

- Free or near-free for a student team; data volume is small (a 20-farmer
  pilot, a few thousand cached price rows a week).
- **"Migration run on a copy first, DB backup before migration"** is part of
  the deploy checklist (roadmap, Section 2).
- Personal data (phone-derived identifiers, farm location) under the DPDP Act
  2023: keep it minimal and in one place.
- Tests and local dev must run with no network and no paid services.

Free-tier facts as of Oct 2026 (re-check before signing):

| Provider | Free limit that matters |
|---|---|
| Render Postgres | Expires **30 days** after creation; 14-day grace, then deleted. 1 GB. ([docs](https://render.com/docs/free)) |
| Supabase | 500 MB DB; **project pauses after 1 week of inactivity**. ([pricing](https://supabase.com/pricing)) |
| Neon | 0.5 GB storage, 100 CU-hours/month per project, compute **scales to zero after 5 min** idle; branching. ([plans](https://neon.com/docs/introduction/plans)) |

## Decision

**Neon Postgres (free tier) in production; SQLite for local dev and unit
tests; SQLAlchemy 2.x models with Flask-Migrate (Alembic) migrations.**
Use a **Neon branch** as the "copy" for every migration rehearsal and as the
pre-migration backup. Pick the Neon and Render regions closest to each other
(both offer Singapore; verify at setup).

## Options Considered

### Option A: SQLite on Render (status quo)

| Dimension | Assessment |
|---|---|
| Complexity | Lowest. |
| Cost | Free. |
| Durability | **None on free tier**: wiped on redeploy/restart/spin-down. Render disks are paid only. |
| Team familiarity | High. |

**Pros:** zero setup; same engine locally and in prod.
**Cons:** loses every saved farm. Disqualified for production; kept for dev/tests.

### Option B: Render Postgres

| Dimension | Assessment |
|---|---|
| Complexity | Low; same dashboard as the web service. |
| Cost | Free DB **expires after 30 days**; a 6-week phase plus a semester pilot needs a paid plan. |
| Durability | Good while paid. |
| Team familiarity | Medium. |

**Pros:** same provider and region as the app, internal networking.
**Cons:** free tier doesn't outlive Phase 1; recreating monthly means data loss.

### Option C: Supabase (Postgres)

| Dimension | Assessment |
|---|---|
| Complexity | Medium; a whole platform (auth, storage, REST) of which we'd use only Postgres. |
| Cost | Free, 500 MB. |
| Durability | Good, but **pauses after 7 days idle**; must be restored by hand. |
| Team familiarity | Low–medium (MCP is configured in `.mcp.json`). |

**Pros:** generous free tier; storage bucket could hold Phase 2 photos.
**Cons:** a pause between field visits takes the app down until someone
restores it; temptation to adopt Supabase auth/REST, which conflicts with
Flask-owned auth and the server-rendered stack (ADR-001).

### Option D: Neon (Postgres) — recommended

| Dimension | Assessment |
|---|---|
| Complexity | Low; plain Postgres connection string. |
| Cost | Free: 0.5 GB, 100 CU-hours/month. Enough for Phase 1 volumes. |
| Durability | Good; no expiry; scale-to-zero instead of pausing the project. |
| Team familiarity | Low, but it is just Postgres + a dashboard. |

**Pros**
- Doesn't expire or pause the project; idle compute wakes on connect.
- **Branching** gives a copy-on-write clone in seconds: rehearse each migration
  on a branch, keep the pre-migration branch as the backup.
- Plain Postgres: leaving later is a `pg_dump`.

**Cons**
- Cold start after 5 min idle adds latency to the first query.
- 0.5 GB cap: Phase 2 sensor readings would need pruning or a paid plan.
- Separate provider from Render: cross-provider latency; pick the same region.

## Trade-off Analysis

Durability rules out A; the 30-day expiry rules out B on the free tier. C and
D are both free Postgres; the deciding difference is idle behaviour. A field
pilot is bursty (busy on visit days, quiet for a week), which is exactly what
Supabase's 7-day pause punishes and Neon's scale-to-zero tolerates. Neon's
branching also turns the deploy-checklist steps ("migrate a copy first",
"backup before migration") into one command each.

**Related hosting risk (not a DB decision, recorded here):** Render's free web
service spins down after 15 min without traffic and takes about a minute to
come back. A farmer's first visit after idle would blow the LCP < 3 s budget by
a wide margin. Neon cold start stacks on top. This needs a decision before the
pilot: a paid Render instance for the pilot weeks, or accepting the cold start
for demos only.

## Consequences

- **Easier:** durable saved farms; safe migrations; local dev unchanged (SQLite).
- **Harder:** two engines. SQLite and Postgres differ (types, JSON, case
  sensitivity, concurrent writes), so:
  - Models use SQLAlchemy generic types only (`JSON`, `DateTime(timezone=True)`, `Numeric`); no raw SQL in app code.
  - Store all timestamps in UTC.
  - CI runs the test suite and `flask db upgrade` against a Postgres service container as well as SQLite.
- **Config:** `DATABASE_URL` from env only (CLAUDE.md); SQLite default only when `FLASK_ENV=development` or under tests.
- **Revisit if:** storage passes 0.4 GB, Phase 2 sensors arrive (time-series volume), or the pilot needs guaranteed warm latency.

## Action Items

1. [ ] Team sign-off; confirm free-tier limits on the provider pages on the day.
2. [ ] Create a Neon project (Singapore or nearest to the Render region); store the connection string only in Render env vars and GitHub Actions secrets.
3. [ ] Section 2: Flask-Migrate initial migration from the ADR-003 models; Postgres service container in CI.
4. [ ] Section 2 deploy checklist: `neon branch create` before migrate, run migration on the branch, then on main; delete branches older than the last 2 releases.
5. [ ] Decide before the pilot: paid Render instance vs accepting cold starts (owner: team; input: Gate 0 farmer phone/network answers).

## Sign-off

| Name | Role | Agree / Disagree | Date |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |
