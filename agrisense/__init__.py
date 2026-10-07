"""AgriSense 2.0 application factory."""

from __future__ import annotations

from flask import Flask, current_app, g, request, session
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import build_config
from .extensions import babel, csrf, db, migrate


def select_locale() -> str:
    """Language cookie, else the browser's preference, else Hindi."""
    languages = current_app.config["LANGUAGES"]
    chosen = request.cookies.get("lang")
    if chosen in languages:
        return chosen
    return request.accept_languages.best_match(languages) or "hi"


def create_app(profile: str | None = None, overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(build_config(profile))
    if overrides:
        app.config.update(overrides)

    if app.config.get("TRUST_PROXY"):
        # Render terminates TLS and appends one X-Forwarded-For hop. Trusting
        # exactly one hop stops clients spoofing their IP to dodge rate limits.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    db.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app, locale_selector=select_locale)
    csrf.init_app(app)

    from . import models  # noqa: F401  (register tables with SQLAlchemy/Alembic)
    from .blueprints import register_blueprints
    from .cli import register_cli

    register_blueprints(app)
    register_cli(app)

    @app.before_request
    def load_user() -> None:
        user_id = session.get("user_id")
        g.user = db.session.get(models.User, user_id) if user_id else None

    @app.context_processor
    def template_globals() -> dict:
        from flask_babel import get_locale

        from .crops import crop_name
        from .navigation import TABS, active_tab
        from .units import AREA_UNITS, WEIGHT_UNITS

        locale = str(get_locale())
        return {
            "current_user": g.get("user"),
            "current_locale": locale,
            "nav_tabs": TABS,
            "nav_active": active_tab(),
            "crop_name": lambda code: crop_name(code, locale),
            "area_units": AREA_UNITS,
            "weight_units": WEIGHT_UNITS,
            # Macros only use env globals (_, url_for), so one shared module works.
            "ui": app.jinja_env.get_template("macros/ui.html").module,
        }

    return app
