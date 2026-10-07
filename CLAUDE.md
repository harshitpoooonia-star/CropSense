# AgriSense 2.0 — rules for Claude
- Source of truth: docs/AgriSense-2.0-spec.md, docs/adr/, docs/specs/. Read the relevant ones first.
- Stack: Flask + Jinja + HTMX + Tailwind (standalone CLI). No React, no new JS libraries without an ADR.
- Budgets: first load < 300 KB JS+CSS, LCP < 3 s on throttled 4G, 360 px baseline, tap targets >= 48 px.
- Every user-facing string goes through Flask-Babel (hi + en). No raw text in templates.
- Every tool result goes through the trust layer: reasons, sources with dates, confidence, estimated fields.
- Never invent agronomic numbers, prices, scheme rules or thresholds. Leave a TODO with the source to check.
- No plain-text secrets or credentials. Config from env only.
- Neutral: no brands, ads or buy buttons. Treatments name active ingredients only.
- Tests with every change; Playwright for user flows (webapp-testing skill).
