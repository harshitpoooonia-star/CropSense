from flask import Blueprint, current_app, redirect, render_template, request, url_for

bp = Blueprint("public", __name__)

ONE_YEAR = 365 * 24 * 3600


def safe_next(target: str | None) -> str:
    """Only same-site paths, so ?next= can't send people to another site."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("public.home")


@bp.get("/")
def home():
    return render_template("home.html")


# Old 1.x routes stay reachable until their replacements ship (Section 2).
@bp.get("/home")
def legacy_home():
    return redirect(url_for("planner.index"))


@bp.get("/history")
def legacy_history():
    return redirect(url_for("public.home"))


@bp.get("/lang/<code>")
def set_language(code: str):
    response = redirect(safe_next(request.args.get("next")))
    if code in current_app.config["LANGUAGES"]:
        response.set_cookie("lang", code, max_age=ONE_YEAR, samesite="Lax", httponly=True)
    return response
