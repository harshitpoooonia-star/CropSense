# Spec 06: Scheme Finder

**Status:** Draft for Section 9 · **Date:** 2026-10-08
**From:** [AgriSense 2.0 spec](../AgriSense-2.0-spec.md) P0-6. **Builds on:** ADR-004 (schemes YAML, verified filter), spec 01 (profile prefill, trust layer).

## Problem statement

Ramesh hears about a scheme at the chaupal but doesn't know if he qualifies,
what it pays, or which papers to take to the CSC. Official portals list
schemes one at a time, in English, with long eligibility text. Money he is
owed goes unclaimed.

## Goals

1. Six short questions, one per screen, in Hindi, with Skip on each; state and land prefilled from the saved field.
2. A list of **likely** schemes, then **might fit** (missing answers or partial data), then **not for you, and why**.
3. Each scheme: the benefit in one line, papers to carry, official link, deadline or deadline note, and its source.
4. Every result labelled "likely eligible: confirm at the official portal or a CSC".
5. **Only schemes a person has checked appear in production** (ADR-004).

## Non-goals

- **Applying for the scheme.** We link to the official portal; we don't collect applications.
- **Deciding eligibility.** Results are "likely", never final.
- **District-specific notifications** (PMFBY notified crops and dates). We point to the portal for these.

## Requirements (P0)

**R1. Data** (`data/schemes.yaml`): id, Hindi and English name and benefit, level (central / UP / HR), rules, documents (Hindi and English), official URL (https), deadline or deadline note, sources, `verified`, `last_checked`. Checked by `agrisense/schemes/catalog.py` at load.

Seeded (all `verified: false`): PM-KISAN, PMFBY, KCC, PM-KMY (central); Mukhyamantri Krishak Durghatna Kalyan Yojana, free power for private tubewells (UP); Meri Fasal Mera Byora, Bhavantar Bharpai Yojana (Haryana).

**R2. Rule engine** (`agrisense/schemes/engine.py`): per rule, "no" when an answer rules the farmer out, "maybe" when an answer is missing or the data is partial. Rules: states, ownership, max land, age, exclusions (income tax / government job / large pension), irrigation (from the saved field), crops, categories.

**R3. Questions**: state, land, whose land (own / rent / batai), main crop, age, and the exclusions question. **Category isn't asked**: no seeded scheme depends on it; the engine supports it for when one does.

**R4. Results** with the trust layer: confidence low while any shown scheme is unverified. In production, with nothing verified, the page points to myScheme and CSCs instead.

## Open questions

- **Blocking for launch:** a person checks each scheme against its official page and sets `verified: true` with `last_checked`. Specific TODOs in the YAML: KCC's ₹3 lakh vs ₹5 lakh subsidised limit; KDKY's document list and claim window; whether UP free tubewell power is still running and how to register; the MFMB document list. *Team*
- **Not blocking:** more UP schemes (e.g. farm-machinery subsidy, PM-KUSUM solar pumps) once their current terms are sourced. *Team*
- **Not blocking:** a grievance/helpline number per scheme. *Team*
