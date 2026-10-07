"""Save my farm (account), log in/out, and the staff-assisted PIN reset.

Section 4 adds the farm wizard and migrates the guest profile on save; here
"Save my farm" only creates the account.
"""

from __future__ import annotations

from functools import wraps

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session
from flask import url_for
from flask_babel import get_locale
from flask_babel import lazy_gettext as _l

from .. import auth
from ..auth import AuthError, AuthSettings
from ..extensions import db

bp = Blueprint("profile", __name__)

ERRORS = {
    "phone_invalid": _l("Enter a 10-digit mobile number."),
    "consent_required": _l("Please read and accept the consent text to save your farm."),
    "pin_format": _l("The PIN must be exactly 4 digits."),
    "pin_simple": _l("This PIN is too easy to guess. Avoid PINs like 1111 or 1234."),
    "pin_mismatch": _l("The two PINs don't match."),
    "phone_taken": _l("This number already has a saved farm. Log in instead."),
    "invalid": _l("Wrong mobile number or PIN."),
    "locked": _l("Too many tries. Wait 15 minutes and try again."),
    "reset_invalid": _l("The code is wrong or has expired. Ask your helper for a new one."),
    "no_such_farmer": _l("There is no saved farm for this number."),
    "not_self": _l("You can't reset your own PIN here."),
    "not_helper": _l("Only a helper can do this."),
}
STATUS = {"invalid": 401, "reset_invalid": 401, "locked": 429}


def _settings() -> AuthSettings:
    return AuthSettings.from_config(current_app.config)


def _error_page(template: str, err: AuthError, **context):
    return render_template(template, error=ERRORS[err.code], **context), STATUS.get(err.code, 400)


def _log_in(user) -> None:
    session.clear()  # new session id on every login: no session fixation
    session["user_id"] = user.id


def helper_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            return redirect(url_for("profile.login"))
        if not g.user.is_helper:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@bp.route("/farm/save", methods=["GET", "POST"])
def save_farm():
    if request.method == "GET":
        return render_template("profile/save.html")
    form = request.form
    try:
        user = auth.register(
            db.session,
            _settings(),
            raw_phone=form.get("phone", ""),
            pin=form.get("pin", ""),
            pin_confirm=form.get("pin_confirm", ""),
            consent=form.get("consent") == "yes",
            locale=str(get_locale()),
            ip=request.remote_addr,
        )
    except AuthError as err:
        return _error_page("profile/save.html", err)
    _log_in(user)
    flash(_l("Your farm is saved."))
    return redirect(url_for("public.home"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("profile/login.html")
    try:
        user = auth.authenticate(
            db.session,
            _settings(),
            raw_phone=request.form.get("phone", ""),
            pin=request.form.get("pin", ""),
            ip=request.remote_addr,
        )
    except AuthError as err:
        return _error_page("profile/login.html", err)
    _log_in(user)
    return redirect(url_for("public.home"))


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("public.home"))


@bp.route("/pin/reset", methods=["GET", "POST"])
def pin_reset():
    if request.method == "GET":
        return render_template("profile/pin_reset.html")
    form = request.form
    try:
        user = auth.complete_pin_reset(
            db.session,
            _settings(),
            raw_phone=form.get("phone", ""),
            code=form.get("code", ""),
            new_pin=form.get("pin", ""),
            pin_confirm=form.get("pin_confirm", ""),
            ip=request.remote_addr,
        )
    except AuthError as err:
        return _error_page("profile/pin_reset.html", err)
    _log_in(user)
    flash(_l("Your new PIN is set."))
    return redirect(url_for("public.home"))


@bp.route("/helper/pin-reset", methods=["GET", "POST"])
@helper_required
def helper_pin_reset():
    if request.method == "GET":
        return render_template("profile/helper_pin_reset.html")
    try:
        code = auth.start_pin_reset(
            db.session, _settings(), helper=g.user, raw_farmer_phone=request.form.get("phone", "")
        )
    except AuthError as err:
        return _error_page("profile/helper_pin_reset.html", err)
    minutes = current_app.config["PIN_RESET_CODE_TTL_SECONDS"] // 60
    response = render_template("profile/helper_pin_reset.html", code=code, minutes=minutes)
    return response, 200, {"Cache-Control": "no-store"}
