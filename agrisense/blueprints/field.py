from flask import Blueprint, render_template

bp = Blueprint("field", __name__)


@bp.get("/field")
def index():
    return render_template("field.html")
