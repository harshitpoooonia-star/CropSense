# ADR-006: Offline — what the service worker keeps on the phone

**Status:** Proposed
**Date:** 2026-10-08
**Deciders:** AgriSense team (4) — sign-off below

## Context

Section 10 makes AgriSense installable and readable offline: the spec's
farmers are on patchy 4G, and a plan or a spray verdict they got at home
should still read in the field. Constraints: no new JS library without an ADR
(CLAUDE.md), phones are often shared (ADR-003), the guest profile lives in
localStorage and the server sends it back in `data-profile-update` blocks,
and every answer must show its sources and date (trust layer).

## Decision

**A hand-written service worker (`/sw.js`, rendered by Flask), no Workbox.**

| What | Strategy | Kept where |
|---|---|---|
| Static files (CSS, JS, fonts, icons) | Cache first. URLs carry a content hash (`?v=`), so a changed file is a new URL. App shell precached on install | `agrisense-shell-<version>`; old versions deleted on activate |
| Pages (GET navigations) | Network first; offline → the copy from the last visit, else the bilingual `/offline` page | `agrisense-pages` |
| Tool answers (HTMX POSTs) | Network first. Saved only when the server marks the response `X-Offline-Keep: 1` (a real answer, not a form error or empty state). Offline → that saved answer with a note "no internet, your last answer from <time>"; no saved answer → a "connect and try again" message | `agrisense-pages`, key `/__last/<path>` |
| Login, logout, PIN, farm account, `/lang`, `/api`, `/internal`, other sites (map tiles) | Not touched | — |

- **Saved copies have their `data-profile-update` block removed**, so
  replaying an old answer can never overwrite the farm on the phone.
- **Logout and "Delete my farm" delete `agrisense-pages`** (profile.js, on the
  `null` profile), so the next person on a shared phone doesn't see them.
- **Version:** a hash of the precached URLs (which carry content hashes), the
  worker and offline-page templates, and `RENDER_GIT_COMMIT`. Nothing to bump
  by hand.
- **Only GET pages and HTMX POSTs are handled.** Plain form posts go straight
  to the network.

## Options considered

| | Hand-written worker (recommended) | Workbox | No worker (manifest only) |
|---|---|---|---|
| Size | ~5 KB unminified, ours to read | Library from a CDN or a JS build step | 0 |
| Fits the stack | Yes: Jinja renders the precache list | Needs Node or `importScripts` from Google's CDN | Yes |
| Control over what's kept | Exact: server marks answers, profile blocks stripped | Possible, with plugins | — |
| Offline answers | Yes | Yes | No |

## Trade-offs and consequences

- **One saved answer per tool path.** A rabi plan replaces a kharif plan;
  offline shows whichever came last, with its own season, sources and date.
- **Stale is labelled, never hidden:** a replayed answer always carries the
  saved-at note on top of its own source dates.
- **Pages are keyed by URL, not language.** Offline, a page shows in the
  language it was last opened in.
- **Map tiles aren't cached** (OSM's tile policy forbids bulk prefetching), so
  the map step needs a connection; GPS and the district list remain.
- **Safari** may evict caches after weeks without use; the app then simply
  needs a connection again.
- **Compression** (Flask-Compress) puts CSRF tokens next to reflected input on
  some pages (the BREACH pattern). The session cookie is SameSite=Lax, which
  makes that attack slow and visible; revisit if that changes.

## Action items

1. [ ] Team sign-off.
2. [ ] Pilot: test install and offline on the team's own low-end Android phones and one iPhone.
3. [ ] Deploy checklist §4: confirm `/sw.js`'s version changes on each release.

## Sign-off

| Name | Role | Agree / Disagree | Date |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |
