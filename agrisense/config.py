"""Configuration, read from the environment only (CLAUDE.md, ADR-002).

AGRISENSE_ENV picks the profile: production (default), development, testing.
Production refuses to start without its required variables, so a missing
secret fails the deploy instead of silently using a fallback.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Mapping

REQUIRED_IN_PRODUCTION = ("SECRET_KEY", "DATABASE_URL", "PHONE_PEPPER")
OPTIONAL = ("DATA_GOV_IN_KEY", "REFRESH_TOKEN")
PROFILES = ("production", "development", "testing")

# Not a secret: only ever used when AGRISENSE_ENV is development/testing, so
# saved dev farms keep working across restarts. Production must set its own.
_DEV_PEPPER = "insecure-dev-only-pepper"


class ConfigError(RuntimeError):
    pass


def normalize_database_url(url: str) -> str:
    """Render and Neon hand out postgres:// URLs; we use the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def build_config(profile: str | None = None, environ: Mapping[str, str] | None = None) -> dict:
    env = os.environ if environ is None else environ
    profile = profile or env.get("AGRISENSE_ENV", "production")
    if profile not in PROFILES:
        raise ConfigError(f"AGRISENSE_ENV must be one of {', '.join(PROFILES)}, got {profile!r}")

    def get(name: str) -> str:
        return env.get(name, "").strip()

    config: dict = {
        "AGRISENSE_ENV": profile,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
        "LANGUAGES": ("hi", "en"),
        "BABEL_DEFAULT_LOCALE": "hi",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        # spec Section 2: 5 PIN attempts per 15 minutes per phone number
        "LOGIN_MAX_ATTEMPTS": 5,
        "LOGIN_WINDOW_SECONDS": 15 * 60,
        # Looser cap per IP: Indian mobile networks put whole villages behind
        # one carrier-NAT address, so a tight per-IP limit would lock them out.
        "LOGIN_IP_MAX_ATTEMPTS": 30,
        "PIN_RESET_CODE_TTL_SECONDS": 30 * 60,
        # ADR-005: OSM's public tiles are for light use; switch the URL by env if usage grows.
        "MAP_TILE_URL": get("MAP_TILE_URL") or "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "MAP_ATTRIBUTION": get("MAP_ATTRIBUTION")
        or '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        # Spec 04. FAIR_BAND_PCT is a product choice, proposed for team review:
        # an offer within this % of the modal price counts as fair.
        "FAIR_BAND_PCT": get("FAIR_BAND_PCT") or "5",
        "PRICE_STALE_DAYS": 3,  # spec P0-4: say so when the price is older than 3 days
        "PRICE_WINDOW_DAYS": 30,
        "NEAREST_MANDIS": 5,
        # ADR-004: production shows only schemes a person has checked (verified: true).
        "SCHEMES_SHOW_UNVERIFIED": profile != "production" or get("SCHEMES_SHOW_UNVERIFIED") == "1",
        # /styleguide shows unverified samples; off in production unless asked.
        "STYLEGUIDE_ENABLED": profile != "production" or get("STYLEGUIDE") == "1",
        **{name: get(name) or None for name in OPTIONAL},
    }

    if profile == "production":
        missing = [name for name in REQUIRED_IN_PRODUCTION if not get(name)]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")
        config.update(
            SECRET_KEY=get("SECRET_KEY"),
            SQLALCHEMY_DATABASE_URI=normalize_database_url(get("DATABASE_URL")),
            PHONE_PEPPER=get("PHONE_PEPPER"),
            SESSION_COOKIE_SECURE=True,
            PREFERRED_URL_SCHEME="https",
            TRUST_PROXY=True,
        )
    elif profile == "development":
        config.update(
            SECRET_KEY=get("SECRET_KEY") or secrets.token_hex(32),
            SQLALCHEMY_DATABASE_URI=normalize_database_url(
                get("DATABASE_URL") or "sqlite:///agrisense-dev.db"
            ),
            PHONE_PEPPER=get("PHONE_PEPPER") or _DEV_PEPPER,
        )
    else:  # testing
        config.update(
            TESTING=True,
            SECRET_KEY=secrets.token_hex(32),
            SQLALCHEMY_DATABASE_URI=normalize_database_url(
                get("TEST_DATABASE_URL") or "sqlite:///:memory:"
            ),
            PHONE_PEPPER=_DEV_PEPPER,
            WTF_CSRF_ENABLED=False,
        )
    return config
