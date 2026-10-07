from flask import Blueprint
from flask_babel import gettext as _

from .tools import placeholder

bp = Blueprint("schemes", __name__)


@bp.get("/schemes")
def index():
    return placeholder(_("Scheme Finder"), section=9)
