# Deploy checklist: AgriSense on Render + Neon

Run this for **every** deploy, not only releases. Copy the block below into
the release's PR or notes and tick it there.

Setup this assumes (ADR-001, ADR-002):

- Render web service, start command `gunicorn wsgi:app`.
- Neon Postgres: the `main` branch is production.
- Flask-Migrate migrations in `migrations/`.
- Migrations run in the **build command** on the free tier:
  `pip install -r requirements.txt && flask --app wsgi db upgrade`.
  Render's separate pre-deploy command is a paid feature (verify on the
  Render dashboard). Move the upgrade there if the service is upgraded.

Verify Neon CLI command names against the Neon docs the first time you use
them; the dashboard can do every Neon step below too.

---

## Deploy checklist: `<version or commit>`

**Date:** ____ · **Deployer:** ____ · **Second pair of eyes:** ____
**Commit:** `____` · **Previous live commit (rollback target):** `____`

### 1. Before you start

- [ ] CI is green on the commit being deployed: unit tests on SQLite and on
      Postgres, migrations on Postgres, browser smoke test.
- [ ] The diff has been read by someone other than the author and merged to `main`.
- [ ] No known bug that breaks a tool for guests.
- [ ] You know the previous live commit (write it above). That is the rollback target.
- [ ] Teammates know a deploy is happening. Don't deploy during a field visit or demo.

### 2. Environment variables (Render → Environment)

Check names only. **Never paste values into chat, PRs or this file.**

- [ ] `AGRISENSE_ENV` = `production`
- [ ] `SECRET_KEY` set (long random string)
- [ ] `DATABASE_URL` set to the Neon **main** branch, pooled connection string
- [ ] `PHONE_PEPPER` set and **unchanged** since the last deploy. Changing it
      locks every saved farm out of login.
- [ ] `PYTHON_VERSION` matches `.python-version` (3.14), or Render reads
      `.python-version`. Verify that Render supports this version.
- [ ] Optional, when the feature is live: `DATA_GOV_IN_KEY` (Section 7),
      `REFRESH_TOKEN` (Section 7 warm-up; must match the GitHub Actions secret)
- [ ] Any new variable this release needs is in the README table and here.

The app refuses to start in production if `SECRET_KEY`, `DATABASE_URL` or
`PHONE_PEPPER` is missing, so a missing variable shows up as a failed deploy,
not as silent insecure behaviour.

### 3. Database: only if `migrations/versions/` changed

- [ ] **Backup:** create a Neon branch from `main` named
      `pre-deploy-<short-sha>` (e.g. `neonctl branches create --name pre-deploy-abc1234`).
      This copy-on-write branch is the backup.
- [ ] **Rehearse:** create a second branch `rehearse-<short-sha>` from `main`
      and run the migration against it from your machine:
      `AGRISENSE_ENV=development DATABASE_URL=<rehearse branch URL> flask --app wsgi db upgrade`
- [ ] `flask --app wsgi db check` against the rehearse branch reports no differences.
- [ ] Spot-check row counts on the rehearse branch: `app_user`, `farm`, `plot`, `event`.
- [ ] The migration is **additive**, or this checklist notes why not. During the
      build, the old code still serves traffic against the migrated database.
- [ ] Delete the rehearse branch. Keep `pre-deploy-<sha>` until the next
      successful deploy, and delete branches older than the last 2 releases.

### 4. Service worker (from Section 10 on)

- [ ] `CACHE_VERSION` in `sw.js` changes for this build (injected from the git
      SHA at build time). Without it, phones keep showing the old app shell.

### 5. Deploy

- [ ] Trigger the deploy on Render for the exact commit above.
- [ ] Build log shows `flask db upgrade` finished, if there was a migration.
- [ ] Service status is "Live" and the log shows no traceback in the first minute.

### 6. Smoke test against the live URL

The free service may take about a minute to wake up. Wait, then:

- [ ] `GET /api/health` returns `{"status": "ok", "db": "ok"}`
- [ ] As a guest, in a private window on a phone or at 360 px width, each of
      these loads with status 200 and no console errors: `/`, `/plan`,
      `/fertilizer`, `/market`, `/weather`, `/schemes`, `/farm/save`, `/login`
- [ ] `/home` redirects to `/plan` and `/history` redirects to `/`
- [ ] Language switch: हिंदी ↔ English works and sticks after reload
- [ ] With a test account the team keeps for this purpose: log in, log out.
      Never use a real farmer's account.
- [ ] From Section 3 on, Lighthouse mobile (throttled 4G) on `/`: LCP under 3 s,
      JS+CSS under 300 KB. Measure it after the service is warm and note the
      numbers here: LCP ____ s, JS+CSS ____ KB

### 7. Watch (15 minutes)

- [ ] Render logs: no 5xx, no repeating tracebacks
- [ ] Neon dashboard: no connection errors or exhausted connections

### 8. After

- [ ] Release notes: what changed, migration yes/no, new env vars
- [ ] Tag releases (`v2.0.0`, ...) on the deployed commit
- [ ] Note the Neon backup branch name in the release notes

---

## Rollback

**Roll back immediately, without debugging first, if any of these happen:**

- Any 5xx on `/` or on a tool route (`/plan`, `/fertilizer`, `/market`, `/weather`, `/schemes`)
- Any tool fails for a guest (error page, empty page, console error that breaks it)
- `/api/health` is not `ok` for more than 2 minutes after the service is warm
- Login works for nobody (a wrong `PHONE_PEPPER` looks exactly like this)
- LCP over 3 s on the Lighthouse mobile run (Section 3 on) and the cause isn't
  the free-tier cold start

**How:**

1. Render → Deploys → redeploy the **previous live commit**, the rollback target noted above.
2. If this deploy ran a migration and the old code can't work with the new
   schema, restore the database from `pre-deploy-<sha>` (Neon "restore"/reset
   the `main` branch from it, or point `DATABASE_URL` at it). Writes made since
   the deploy are lost; note how long the window was.
3. Re-run section 6 against the rolled-back service.
4. Write down what happened and fix it on a branch. Don't hot-fix on `main`.
