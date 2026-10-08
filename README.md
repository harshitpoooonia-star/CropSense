# AgriSense 2.0

A farm decision tool for smallholders in north India: crop planning, fertilizer
bags, mandi prices, spray and irrigation timing, and scheme eligibility, in
Hindi and English. It sells nothing and shows why it recommends what it does.

**Status:** Phase 1 rebuild in progress. Section 2 (foundation and security)
is in place; the tools are placeholders until Sections 5–9.

- Spec: [docs/AgriSense-2.0-spec.md](docs/AgriSense-2.0-spec.md)
- Roadmap: [docs/AgriSense-2.0-roadmap.md](docs/AgriSense-2.0-roadmap.md)
- Architecture decisions: [docs/adr/](docs/adr/)
- Deploy checklist: [docs/deploy-checklist.md](docs/deploy-checklist.md)
- Rules for contributors and Claude: [CLAUDE.md](CLAUDE.md)

## Stack

Flask + Jinja + HTMX + Tailwind (ADR-001), SQLAlchemy + Flask-Migrate,
Postgres on Neon in production and SQLite locally (ADR-002), Flask-Babel for
Hindi/English.

## Run it locally

Python 3.14 (see `.python-version`).

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python -m playwright install chromium

set AGRISENSE_ENV=development     # PowerShell: $env:AGRISENSE_ENV="development"
flask --app wsgi db upgrade       # creates agrisense-dev.db (SQLite)
flask --app wsgi run              # http://127.0.0.1:5000
```

`AGRISENSE_ENV` defaults to `production`, which refuses to start without its
environment variables, so local runs must set `development`.

## Configuration (environment only)

| Variable | Needed in | What |
|---|---|---|
| `AGRISENSE_ENV` | all | `production` (default), `development`, `testing` |
| `SECRET_KEY` | production | Flask session signing; long random string |
| `DATABASE_URL` | production | Neon Postgres URL (`postgres://` is fine) |
| `PHONE_PEPPER` | production | Key for hashing phone numbers. **Never change it** without a re-hash plan: every saved farm's login depends on it |
| `DATA_GOV_IN_KEY` | optional | Agmarknet API key (Section 7, Gate 0 script) |
| `REFRESH_TOKEN` | optional | Protects the price warm-up endpoint (Section 7) |

Never put real values in a file in this repo.

## Styles, fonts and translations

The built CSS, HTMX, the Mukta fonts and the compiled `.mo` catalogues are
committed, so Render needs no Node or build tools.

```bash
python scripts/build_css.py        # after changing templates or static/src/app.css
pybabel extract -F babel.cfg -k _l -k lazy_gettext --no-location --sort-output -o agrisense/translations/messages.pot .
pybabel update -i agrisense/translations/messages.pot -d agrisense/translations --no-fuzzy-matching
pybabel compile -d agrisense/translations   # after editing hi/LC_MESSAGES/messages.po
python scripts/get_assets.py htmx fonts     # only when bumping a pinned version
python scripts/build_icons.py               # after editing static/icons/icon.svg
```

## Offline and performance

The app installs to the home screen and keeps pages and each tool's last
answer for offline use ([ADR-006](docs/adr/ADR-006-offline.md)). Static URLs
carry a content hash (`?v=`) and are cached for a year; responses are
compressed (Flask-Compress).

```bash
python scripts/perf_budget.py   # JS+CSS < 300 KB and LCP < 3 s at 360 px, slow 4G, 4x CPU
```

`/styleguide` shows every UI macro in Hindi and English (on in development;
set `STYLEGUIDE=1` to show it in production). Design tokens and rules:
[docs/design-system.md](docs/design-system.md).

## Crop Planner data

Every figure the planner shows comes from a cited row in `data/`; rows stay
`verified=false` until a team member checks them against the source.

```bash
python scripts/build_crop_data.py --download   # DES yields (APY/UPAG) + UP cost of cultivation -> economics, seasons
python scripts/build_climate.py                # Open-Meteo history -> district season climate
python scripts/train_suitability.py            # legacy suitability model, no PCA, calibrated
python scripts/validate_planner.py             # top-3 hit rate on data/farm_records.csv
```

MSPs live in `data/msp.csv` and are updated by hand when the Cabinet announces them.
Spec: [docs/specs/02-crop-planner.md](docs/specs/02-crop-planner.md).

## Mandi prices

Prices come from Agmarknet (data.gov.in) into a cache table; pages read the
cache and label anything older than 3 days.

```bash
flask --app wsgi agrisense refresh-prices --days 3   # needs DATA_GOV_IN_KEY
python scripts/build_mandis.py                       # mandi towns + coordinates (Wikidata)
```

In production a scheduled GitHub Actions workflow (`refresh-prices.yml`) calls
`POST /internal/refresh/prices` daily. Set the repository secrets
`REFRESH_URL` (the Render URL) and `REFRESH_TOKEN` (same value as the app's
`REFRESH_TOKEN` env var); without them the workflow skips. The "fair offer"
band is `FAIR_BAND_PCT` (default 5, for team review).
Spec: [docs/specs/04-mandi.md](docs/specs/04-mandi.md).

## Tests

```bash
pytest                            # unit tests; network is blocked
python scripts/run_e2e.py         # Playwright guest smoke test at 360 px
```

CI (GitHub Actions) runs the unit tests on SQLite and Postgres, applies and
checks the migrations on Postgres, and runs the browser smoke test.

## Admin

```bash
flask --app wsgi agrisense make-helper   # make a KVK/FPO helper who can reset PINs
```

A farmer who forgets their PIN asks a helper. The helper confirms the farmer
in person, gets a one-time code at `/helper/pin-reset`, and the farmer sets a
new PIN at `/pin/reset`.

## Deploy (Render)

- Build: `pip install -r requirements.txt && flask --app wsgi db upgrade`
  (free tier; Render's separate pre-deploy command is paid)
- Start: `gunicorn wsgi:app`
- Follow [docs/deploy-checklist.md](docs/deploy-checklist.md) every time.

## Team

Built as a Design Thinking & Innovation (DTI) project at **Bennett University**:
Harshit Poonia, Shivansh Gupta, Anaya Bakshi, Tushita, Anant Vaibhav.

## License

[MIT](LICENSE)
