from flask import Blueprint
from flask_babel import gettext as _

from .tools import placeholder

bp = Blueprint("fertilizer", __name__)


@bp.get("/fertilizer")
def index():
    return placeholder(_("Fertilizer Calculator"), section=6)
