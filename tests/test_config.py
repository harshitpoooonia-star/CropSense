import pytest

from agrisense.config import ConfigError, build_config, normalize_database_url

PROD_ENV = {
    "SECRET_KEY": "s" * 64,
    "DATABASE_URL": "postgres://u:p@host/db",
    "PHONE_PEPPER": "pepper-from-env",
}


def test_production_is_the_default_profile():
    assert build_config(environ=PROD_ENV)["AGRISENSE_ENV"] == "production"


@pytest.mark.parametrize("missing", ["SECRET_KEY", "DATABASE_URL", "PHONE_PEPPER"])
def test_production_refuses_to_start_without_required_vars(missing):
    env = {k: v for k, v in PROD_ENV.items() if k != missing}
    with pytest.raises(ConfigError, match=missing):
        build_config("production", env)


def test_production_takes_values_from_env_only():
    config = build_config("production", PROD_ENV)
    assert config["SECRET_KEY"] == PROD_ENV["SECRET_KEY"]
    assert config["PHONE_PEPPER"] == PROD_ENV["PHONE_PEPPER"]
    assert config["SQLALCHEMY_DATABASE_URI"] == "postgresql+psycopg://u:p@host/db"
    assert config["SESSION_COOKIE_SECURE"] is True
    assert config["TRUST_PROXY"] is True


def test_blank_values_count_as_missing():
    with pytest.raises(ConfigError, match="SECRET_KEY"):
        build_config("production", {**PROD_ENV, "SECRET_KEY": "   "})


def test_development_works_with_empty_env():
    config = build_config("development", {})
    assert config["SECRET_KEY"]
    assert config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///")
    assert config["DATA_GOV_IN_KEY"] is None


def test_development_secret_is_not_a_fixed_string():
    assert build_config("development", {})["SECRET_KEY"] != build_config("development", {})["SECRET_KEY"]


def test_unknown_profile_is_rejected():
    with pytest.raises(ConfigError):
        build_config("staging", {})


@pytest.mark.parametrize(
    "url, expected",
    [
        ("postgres://a/b", "postgresql+psycopg://a/b"),
        ("postgresql://a/b", "postgresql+psycopg://a/b"),
        ("postgresql+psycopg://a/b", "postgresql+psycopg://a/b"),
        ("sqlite:///x.db", "sqlite:///x.db"),
    ],
)
def test_normalize_database_url(url, expected):
    assert normalize_database_url(url) == expected


def test_create_app_fails_fast_in_production(monkeypatch):
    from agrisense import create_app

    for name in ("SECRET_KEY", "DATABASE_URL", "PHONE_PEPPER", "AGRISENSE_ENV"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ConfigError):
        create_app()
