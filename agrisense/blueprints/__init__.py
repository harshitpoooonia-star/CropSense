from flask import Flask

from . import (
    api,
    fertilizer,
    field,
    internal,
    market,
    more,
    planner,
    profile,
    public,
    pwa,
    schemes,
    styleguide,
    today,
    weather,
)


def register_blueprints(app: Flask) -> None:
    modules = [public, today, planner, fertilizer, field, weather, market, more, schemes, profile, api, internal, pwa]
    if app.config.get("STYLEGUIDE_ENABLED"):
        modules.append(styleguide)
    for module in modules:
        app.register_blueprint(module.bp)
