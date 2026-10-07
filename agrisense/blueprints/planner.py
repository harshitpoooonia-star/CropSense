from flask import Blueprint
from flask_babel import gettext as _

from .tools import placeholder

bp = Blueprint("planner", __name__)


@bp.get("/plan")
def index():
    return placeholder(_("Crop Planner"), section=5)
