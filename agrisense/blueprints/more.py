from flask import Blueprint, render_template

from .. import districts, kvk
from ..profile_io import current_profile

bp = Blueprint("more", __name__)

# Spec P0-8: the national helpline on every "Ask an expert".
KISAN_CALL_CENTRE = "1800-180-1551"


@bp.get("/more")
def index():
    return render_template("more.html")


@bp.get("/expert")
def expert():
    return render_template("expert.html", kcc=KISAN_CALL_CENTRE)


@bp.post("/expert/kvk")
def expert_kvk():
    """The farmer's district KVK, from the profile their phone sends."""
    code = current_profile()["farm"]["district_code"]
    return render_template(
        "_kvk.html",
        district=districts.get(code),
        entry=kvk.for_district(code),
        known=list(kvk.contacts().values()),
    )
