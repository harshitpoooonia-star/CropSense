## What and why

<!-- One or two sentences. Link the spec section or ADR it follows. -->

## Checklist

- [ ] Tests added or updated (`pytest`; Playwright via `python scripts/run_e2e.py` for user flows)
- [ ] Every new user-facing string goes through Flask-Babel, with Hindi in `hi/LC_MESSAGES/messages.po`, and catalogues recompiled
- [ ] Results go through the trust layer (reasons, sources with dates, confidence)
- [ ] No invented agronomic numbers, prices, thresholds or scheme rules; new figures cite a source in `data/`
- [ ] `python scripts/build_css.py --check` and `python scripts/perf_budget.py` pass
- [ ] No secrets, brands or buy buttons
