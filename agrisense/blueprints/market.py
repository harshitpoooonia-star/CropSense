from flask import Blueprint
from flask_babel import gettext as _

from .tools import placeholder

bp = Blueprint("market", __name__)


@bp.get("/market")
def index():
    return placeholder(_("Mandi Prices"), section=7)
