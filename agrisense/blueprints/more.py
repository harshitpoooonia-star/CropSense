from flask import Blueprint, render_template

bp = Blueprint("more", __name__)

# Spec P0-8. District KVK contacts arrive with the district table (Section 4).
KISAN_CALL_CENTRE = "1800-180-1551"


@bp.get("/more")
def index():
    return render_template("more.html")


@bp.get("/expert")
def expert():
    return render_template("expert.html", kcc=KISAN_CALL_CENTRE)
