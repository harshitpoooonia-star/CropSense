from flask import Blueprint, render_template

bp = Blueprint("today", __name__)


@bp.get("/today")
def index():
    return render_template("today.html")
