from flask import Flask

from . import api, fertilizer, market, planner, profile, public, schemes, weather


def register_blueprints(app: Flask) -> None:
    for module in (public, profile, planner, fertilizer, market, weather, schemes, api):
        app.register_blueprint(module.bp)
