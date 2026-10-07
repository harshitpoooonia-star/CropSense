from datetime import timedelta

import pytest
from sqlalchemy import select

from agrisense import auth
from agrisense.auth import AuthError, AuthSettings
from agrisense.models import LoginAttempt, User, utcnow

PHONE = "98765 43210"
E164 = "+919876543210"


@pytest.fixture
def settings(app):
    return AuthSettings.from_config(app.config)


def make_user(session, settings, phone=PHONE, pin="4826", ip="10.0.0.1"):
    return auth.register(
        session, settings, raw_phone=phone, pin=pin, pin_confirm=pin, consent=True, locale="hi", ip=ip
    )


# ---------------------------------------------------------------- helpers


@pytest.mark.parametrize(
    "raw",
    ["9876543210", "98765 43210", "+91 98765-43210", "+919876543210", "919876543210", "09876543210", "0091 9876543210"],
)
def test_normalize_phone_accepts_common_forms(raw):
    assert auth.normalize_phone(raw) == E164


@pytest.mark.parametrize("raw", ["", None, "12345", "5876543210", "98765432101", "abcdefghij", "+1 9876543210"])
def test_normalize_phone_rejects_invalid(raw):
    assert auth.normalize_phone(raw) is None


def test_phone_hash_is_keyed_and_stable():
    a = auth.phone_hash(E164, "pepper-a")
    assert a == auth.phone_hash(E164, "pepper-a")
    assert a != auth.phone_hash(E164, "pepper-b")
    assert a != auth.ip_hash(E164, "pepper-a")  # separate domains
    assert "9876543210" not in a


@pytest.mark.parametrize(
    "pin, problem",
    [("4826", None), ("0912", None), ("123", "pin_format"), ("12345", "pin_format"), ("12a4", "pin_format"),
     (None, "pin_format"), ("1111", "pin_simple"), ("1234", "pin_simple"), ("9876", "pin_simple"),
     ("0123", "pin_simple")],
)
def test_pin_problem(pin, problem):
    assert auth.pin_problem(pin) == problem


# ---------------------------------------------------------------- register / login


def test_register_stores_no_plain_phone_or_pin(session, settings):
    user = make_user(session, settings)
    row = session.get(User, user.id)
    stored = " ".join(str(v) for v in vars(row).values())
    assert "9876543210" not in stored
    assert "4826" not in stored
    assert row.phone_hmac == auth.phone_hash(E164, settings.pepper)
    assert row.consent_version == auth.CONSENT_VERSION
    assert row.role == "farmer"


@pytest.mark.parametrize(
    "kwargs, code",
    [
        ({"raw_phone": "123"}, "phone_invalid"),
        ({"consent": False}, "consent_required"),
        ({"pin": "1111", "pin_confirm": "1111"}, "pin_simple"),
        ({"pin": "4826", "pin_confirm": "4827"}, "pin_mismatch"),
    ],
)
def test_register_validation(session, settings, kwargs, code):
    args = {"raw_phone": PHONE, "pin": "4826", "pin_confirm": "4826", "consent": True, "locale": "hi", "ip": "1.1.1.1"}
    with pytest.raises(AuthError) as exc:
        auth.register(session, settings, **{**args, **kwargs})
    assert exc.value.code == code


def test_register_twice_is_refused(session, settings):
    make_user(session, settings)
    with pytest.raises(AuthError) as exc:
        make_user(session, settings, phone="+91 9876543210")
    assert exc.value.code == "phone_taken"


def test_login_round_trip(session, settings):
    user = make_user(session, settings)
    assert auth.authenticate(session, settings, raw_phone="09876543210", pin="4826", ip="1.1.1.1").id == user.id


@pytest.mark.parametrize("phone, pin", [(PHONE, "0000"), ("9123456789", "4826"), ("junk", "4826")])
def test_login_failures_look_the_same(session, settings, phone, pin):
    make_user(session, settings)
    with pytest.raises(AuthError) as exc:
        auth.authenticate(session, settings, raw_phone=phone, pin=pin, ip="1.1.1.1")
    assert exc.value.code == "invalid"


# ---------------------------------------------------------------- rate limiting


def _fail_login(session, settings, times, phone=PHONE, ip="1.1.1.1"):
    for _ in range(times):
        with pytest.raises(AuthError):
            auth.authenticate(session, settings, raw_phone=phone, pin="0000", ip=ip)


def test_five_failures_lock_the_number_even_for_the_right_pin(session, settings):
    make_user(session, settings)
    _fail_login(session, settings, 4)
    assert auth.authenticate(session, settings, raw_phone=PHONE, pin="4826", ip="1.1.1.1")  # 5th try ok
    _fail_login(session, settings, 5)
    with pytest.raises(AuthError) as exc:
        auth.authenticate(session, settings, raw_phone=PHONE, pin="4826", ip="2.2.2.2")
    assert exc.value.code == "locked"


def test_lock_is_per_number(session, settings):
    make_user(session, settings)
    make_user(session, settings, phone="9123456789")
    _fail_login(session, settings, 5)
    assert auth.authenticate(session, settings, raw_phone="9123456789", pin="4826", ip="1.1.1.1")


def test_lock_expires_after_the_window(session, settings):
    make_user(session, settings)
    _fail_login(session, settings, 5)
    old = utcnow() - settings.window - timedelta(seconds=1)
    for attempt in session.scalars(select(LoginAttempt)):
        attempt.attempted_at = old
    session.commit()
    assert auth.authenticate(session, settings, raw_phone=PHONE, pin="4826", ip="1.1.1.1")


def test_ip_cap_stops_spraying_many_numbers(session, settings):
    for i in range(settings.ip_max_attempts):
        _fail_login(session, settings, 1, phone=f"98000000{i:02d}", ip="9.9.9.9")
    make_user(session, settings, ip="8.8.8.8")
    with pytest.raises(AuthError) as exc:
        auth.authenticate(session, settings, raw_phone=PHONE, pin="4826", ip="9.9.9.9")
    assert exc.value.code == "locked"


def test_ip_is_stored_hashed(session, settings):
    _fail_login(session, settings, 1, ip="203.0.113.7")
    attempt = session.scalars(select(LoginAttempt)).one()
    assert "203.0.113.7" not in attempt.ip_hash


# ---------------------------------------------------------------- staff-assisted PIN reset


@pytest.fixture
def helper(session, settings):
    user = make_user(session, settings, phone="9000000001", pin="5739")
    user.role = "helper"
    session.commit()
    return user


def test_pin_reset_happy_path(session, settings, helper):
    farmer = make_user(session, settings)
    code = auth.start_pin_reset(session, settings, helper=helper, raw_farmer_phone=PHONE)
    assert len(code) == 6 and code.isdigit()
    assert code not in (farmer.pin_reset_code_hash or "")
    assert farmer.pin_reset_by_id == helper.id

    auth.complete_pin_reset(session, settings, raw_phone=PHONE, code=code, new_pin="7351", pin_confirm="7351", ip="1.1.1.1")
    with pytest.raises(AuthError):
        auth.authenticate(session, settings, raw_phone=PHONE, pin="4826", ip="1.1.1.1")
    assert auth.authenticate(session, settings, raw_phone=PHONE, pin="7351", ip="1.1.1.1").id == farmer.id
    assert not session.get(User, farmer.id).pin_reset_required


def test_reset_code_works_once(session, settings, helper):
    make_user(session, settings)
    code = auth.start_pin_reset(session, settings, helper=helper, raw_farmer_phone=PHONE)
    auth.complete_pin_reset(session, settings, raw_phone=PHONE, code=code, new_pin="7351", pin_confirm="7351", ip="1.1.1.1")
    with pytest.raises(AuthError) as exc:
        auth.complete_pin_reset(session, settings, raw_phone=PHONE, code=code, new_pin="2580", pin_confirm="2580", ip="1.1.1.1")
    assert exc.value.code == "reset_invalid"


def test_reset_code_expires(session, settings, helper):
    farmer = make_user(session, settings)
    code = auth.start_pin_reset(session, settings, helper=helper, raw_farmer_phone=PHONE)
    farmer.pin_reset_expires_at = utcnow() - timedelta(seconds=1)
    session.commit()
    with pytest.raises(AuthError) as exc:
        auth.complete_pin_reset(session, settings, raw_phone=PHONE, code=code, new_pin="7351", pin_confirm="7351", ip="1.1.1.1")
    assert exc.value.code == "reset_invalid"


def test_wrong_reset_codes_are_rate_limited(session, settings, helper):
    make_user(session, settings)
    code = auth.start_pin_reset(session, settings, helper=helper, raw_farmer_phone=PHONE)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(settings.max_attempts):
        with pytest.raises(AuthError):
            auth.complete_pin_reset(session, settings, raw_phone=PHONE, code=wrong, new_pin="7351", pin_confirm="7351", ip="1.1.1.1")
    with pytest.raises(AuthError) as exc:
        auth.complete_pin_reset(session, settings, raw_phone=PHONE, code=code, new_pin="7351", pin_confirm="7351", ip="1.1.1.1")
    assert exc.value.code == "locked"


def test_only_helpers_start_resets(session, settings):
    farmer = make_user(session, settings)
    other = make_user(session, settings, phone="9123456789")
    with pytest.raises(AuthError) as exc:
        auth.start_pin_reset(session, settings, helper=other, raw_farmer_phone=PHONE)
    assert exc.value.code == "not_helper"
    assert not session.get(User, farmer.id).pin_reset_required


def test_helper_cannot_reset_unknown_number_or_self(session, settings, helper):
    with pytest.raises(AuthError) as exc:
        auth.start_pin_reset(session, settings, helper=helper, raw_farmer_phone="9111111111")
    assert exc.value.code == "no_such_farmer"
    with pytest.raises(AuthError) as exc:
        auth.start_pin_reset(session, settings, helper=helper, raw_farmer_phone="9000000001")
    assert exc.value.code == "not_self"


def test_remembering_the_old_pin_cancels_a_pending_reset(session, settings, helper):
    make_user(session, settings)
    code = auth.start_pin_reset(session, settings, helper=helper, raw_farmer_phone=PHONE)
    auth.authenticate(session, settings, raw_phone=PHONE, pin="4826", ip="1.1.1.1")
    with pytest.raises(AuthError):
        auth.complete_pin_reset(session, settings, raw_phone=PHONE, code=code, new_pin="7351", pin_confirm="7351", ip="1.1.1.1")
