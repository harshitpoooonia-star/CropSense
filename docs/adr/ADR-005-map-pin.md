# ADR-005: Map for the farm pin — Leaflet + OpenStreetMap tiles

**Status:** Proposed
**Date:** 2026-10-08
**Deciders:** AgriSense team (4) — sign-off below

## Context

The profile wizard (spec 01, R1) needs the farmer to mark where the field is.
CLAUDE.md says no new JS library without an ADR, and ADR-001 keeps JS small
and loads heavy assets only where needed. The roadmap's Section 4 names
Leaflet + OSM tiles. This ADR records that choice and its limits.

Constraints: 2 GB Android phones, patchy 4G, no paid map API, free and
neutral (no tracking SDKs), works in Hindi, and the pin is personal data.

## Decision

**Leaflet 1.9.4, vendored and integrity-checked like HTMX, loaded only on
wizard step 1. Tiles from `tile.openstreetmap.org` with OSM attribution.**
GPS and "choose district" stay available, so the map is never required.

## Options considered

| | Leaflet + OSM tiles (recommended) | Google Maps JS | No map: GPS + district list only |
|---|---|---|---|
| Size | ~40 KB gz JS + 4 KB CSS, one page only | Large SDK plus tracking | 0 |
| Cost | Free | API key, billing account | Free |
| Privacy | Tile requests show OSM the rough area being viewed | Location and usage sent to Google | Nothing leaves the device except to us |
| Usability | Drag a pin on a real map | Same | No way to correct a bad GPS fix on the field |
| Neutrality / lock-in | Open data, swap tile server by config | Vendor lock-in | — |

## Trade-offs and consequences

- **OSM tile usage policy:** the public tile servers are for light use, need
  visible attribution, and forbid heavy or bulk use. A pilot of tens of
  farmers is light. If usage grows, switch the tile URL (config) to a
  provider with a plan, or self-host. **Revisit before any public launch.**
- **Privacy:** the browser fetches tiles around the pin from OSM. We say so
  in the consent text. We never send the pin itself to OSM, and we use no
  geocoding service.
- **Offline:** tiles aren't cached for offline use (Section 10 decides).
  GPS and the district list work offline once the page is cached.
- **Budget:** Leaflet loads only on `/field/setup` step 1, so other pages'
  first-load budget is unchanged.

## Action items

1. [ ] Team sign-off.
2. [ ] Section 4: vendor Leaflet via `scripts/get_assets.py leaflet` with npm integrity; no CDN at runtime.
3. [ ] Tile URL and attribution in config (`MAP_TILE_URL`, `MAP_ATTRIBUTION`) so the server can change without code.
4. [ ] Before public launch: re-read the OSM tile usage policy against expected traffic.

## Sign-off

| Name | Role | Agree / Disagree | Date |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |
