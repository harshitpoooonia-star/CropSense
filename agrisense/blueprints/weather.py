from flask import Blueprint
from flask_babel import gettext as _

from .tools import placeholder

bp = Blueprint("weather", __name__)


@bp.get("/weather")
def index():
    return placeholder(_("Spray & Irrigation Advisor"), section=8)
