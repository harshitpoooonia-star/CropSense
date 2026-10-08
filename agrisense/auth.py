"""Phone + 4-digit PIN accounts (spec P0-1, ADR-003). No Flask routes here.

- The phone number is stored only as HMAC-SHA256(PHONE_PEPPER, E.164 number).
- PINs and reset codes are hashed with werkzeug.
- Every PIN or code check is rate-limited: LOGIN_MAX_ATTEMPTS failures per
  phone, LOGIN_IP_MAX_ATTEMPTS per IP, within LOGIN_WINDOW_SECONDS.
- Forgotten PIN: a helper confirms the farmer in person and gets a one-time
  6-digit code; the farmer enters it with a new PIN.

Service functions commit their own writes so a failed attempt is recorded
even when they raise AuthError.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from .models import LoginAttempt, User, aware, utcnow

CONSENT_VERSION = "2026-10-v2"  # bump when the consent text changes

_INDIAN_MOBILE = re.compile(r"[6-9]\d{9}")
_PIN = re.compile(r"\d{4}")
# Compared against when the phone is unknown, so a miss costs as much as a hit.
_DUMMY_HASH = generate_password_hash("not-a-real-pin")


class AuthError(Exception):
    """`code` is stable and mapped to a translated message by the views."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AuthSettings:
    pepper: str
    max_attempts: int
    ip_max_attempts: int
    window: timedelta
    reset_ttl: timedelta

    @classmethod
    def from_config(cls, config) -> AuthSettings:
        return cls(
            pepper=config["PHONE_PEPPER"],
            max_attempts=config["LOGIN_MAX_ATTEMPTS"],
            ip_max_attempts=config["LOGIN_IP_MAX_ATTEMPTS"],
            window=timedelta(seconds=config["LOGIN_WINDOW_SECONDS"]),
            reset_ttl=timedelta(seconds=config["PIN_RESET_CODE_TTL_SECONDS"]),
        )


# ---------------------------------------------------------------- pure helpers


def normalize_phone(raw: str | None) -> str | None:
    """Indian mobile number in any common form -> '+91XXXXXXXXXX', else None."""
    digits = re.sub(r"[\s\-().]", "", raw or "")
    if digits.startswith("+91"):
        digits = digits[3:]
    elif digits.startswith("0091"):
        digits = digits[4:]
    elif len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return "+91" + digits if _INDIAN_MOBILE.fullmatch(digits) else None


def _keyed_hash(value: str, pepper: str, domain: str) -> str:
    return hmac.new(pepper.encode(), f"{domain}:{value}".encode(), hashlib.sha256).hexdigest()


def phone_hash(phone: str, pepper: str) -> str:
    return _keyed_hash(phone, pepper, "phone")


def ip_hash(ip: str | None, pepper: str) -> str:
    return _keyed_hash(ip or "unknown", pepper, "ip")


def pin_problem(pin: str | None) -> str | None:
    """None if the PIN is acceptable, else 'pin_format' or 'pin_simple'."""
    if not pin or not _PIN.fullmatch(pin):
        return "pin_format"
    steps = {int(b) - int(a) for a, b in zip(pin, pin[1:])}
    if len(set(pin)) == 1 or steps in ({1}, {-1}):
        return "pin_simple"  # 1111, 1234, 9876 ...
    return None


# ---------------------------------------------------------------- rate limiting


def _failures(session: Session, column, value: str, since: datetime) -> int:
    stmt = select(func.count(LoginAttempt.id)).where(
        column == value, LoginAttempt.success.is_(False), LoginAttempt.attempted_at >= since
    )
    return session.scalar(stmt) or 0


def is_locked(session: Session, s: AuthSettings, phone_h: str | None, ip_h: str) -> bool:
    since = utcnow() - s.window
    if phone_h and _failures(session, LoginAttempt.phone_hmac, phone_h, since) >= s.max_attempts:
        return True
    return _failures(session, LoginAttempt.ip_hash, ip_h, since) >= s.ip_max_attempts


def _record(session: Session, kind: str, phone_h: str | None, ip_h: str, success: bool) -> None:
    now = utcnow()
    session.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < now - timedelta(hours=24)))
    session.add(LoginAttempt(kind=kind, phone_hmac=phone_h, ip_hash=ip_h, attempted_at=now, success=success))


def _fail(session: Session, kind: str, phone_h: str | None, ip_h: str, code: str) -> AuthError:
    _record(session, kind, phone_h, ip_h, success=False)
    session.commit()
    return AuthError(code)


def _check_pin_pair(pin: str, confirm: str) -> None:
    problem = pin_problem(pin)
    if problem:
        raise AuthError(problem)
    if pin != confirm:
        raise AuthError("pin_mismatch")


# ---------------------------------------------------------------- services


def register(
    session: Session,
    s: AuthSettings,
    *,
    raw_phone: str,
    pin: str,
    pin_confirm: str,
    consent: bool,
    locale: str,
    ip: str | None,
    before_commit: Callable[[Session, User], None] | None = None,
) -> User:
    """Create the account. `before_commit` adds rows (the farm) in the same transaction."""
    phone = normalize_phone(raw_phone)
    if phone is None:
        raise AuthError("phone_invalid")
    if not consent:
        raise AuthError("consent_required")
    _check_pin_pair(pin, pin_confirm)

    phone_h, ip_h = phone_hash(phone, s.pepper), ip_hash(ip, s.pepper)
    if is_locked(session, s, None, ip_h):
        raise AuthError("locked")
    if session.scalar(select(User.id).where(User.phone_hmac == phone_h)) is not None:
        # Counts against the IP cap, which slows anyone probing for numbers.
        raise _fail(session, "register", None, ip_h, "phone_taken")

    now = utcnow()
    user = User(
        phone_hmac=phone_h,
        pin_hash=generate_password_hash(pin),
        locale=locale,
        consent_at=now,
        consent_version=CONSENT_VERSION,
        last_login_at=now,
    )
    session.add(user)
    session.flush()
    if before_commit is not None:
        before_commit(session, user)
    _record(session, "register", phone_h, ip_h, success=True)
    session.commit()
    return user


def authenticate(session: Session, s: AuthSettings, *, raw_phone: str, pin: str, ip: str | None) -> User:
    phone = normalize_phone(raw_phone)
    ip_h = ip_hash(ip, s.pepper)
    phone_h = phone_hash(phone, s.pepper) if phone else None
    if is_locked(session, s, phone_h, ip_h):
        raise AuthError("locked")

    user = session.scalar(select(User).where(User.phone_hmac == phone_h)) if phone_h else None
    if user is None:
        check_password_hash(_DUMMY_HASH, pin or "")
        raise _fail(session, "login", phone_h, ip_h, "invalid")
    if not check_password_hash(user.pin_hash, pin or ""):
        raise _fail(session, "login", phone_h, ip_h, "invalid")

    # They remembered after all: a pending reset is no longer needed.
    _clear_reset(user)
    user.last_login_at = utcnow()
    _record(session, "login", phone_h, ip_h, success=True)
    session.commit()
    return user


def verify_pin(session: Session, s: AuthSettings, *, user: User, pin: str, ip: str | None) -> None:
    """Re-check a logged-in user's PIN before a destructive action. Rate-limited."""
    ip_h = ip_hash(ip, s.pepper)
    if is_locked(session, s, user.phone_hmac, ip_h):
        raise AuthError("locked")
    if not check_password_hash(user.pin_hash, pin or ""):
        raise _fail(session, "confirm", user.phone_hmac, ip_h, "invalid")


def start_pin_reset(session: Session, s: AuthSettings, *, helper: User, raw_farmer_phone: str) -> str:
    """Return a one-time 6-digit code for the helper to hand to the farmer.

    The helper must have confirmed the farmer in person first. The code is
    shown once and only its hash is stored.
    """
    if not helper.is_helper:
        raise AuthError("not_helper")
    phone = normalize_phone(raw_farmer_phone)
    farmer = (
        session.scalar(select(User).where(User.phone_hmac == phone_hash(phone, s.pepper)))
        if phone
        else None
    )
    if farmer is None:
        raise AuthError("no_such_farmer")
    if farmer.id == helper.id:
        raise AuthError("not_self")

    code = f"{secrets.randbelow(10**6):06d}"
    farmer.pin_reset_required = True
    farmer.pin_reset_code_hash = generate_password_hash(code)
    farmer.pin_reset_expires_at = utcnow() + s.reset_ttl
    farmer.pin_reset_by_id = helper.id
    session.commit()
    return code


def complete_pin_reset(
    session: Session,
    s: AuthSettings,
    *,
    raw_phone: str,
    code: str,
    new_pin: str,
    pin_confirm: str,
    ip: str | None,
) -> User:
    _check_pin_pair(new_pin, pin_confirm)
    phone = normalize_phone(raw_phone)
    ip_h = ip_hash(ip, s.pepper)
    phone_h = phone_hash(phone, s.pepper) if phone else None
    if is_locked(session, s, phone_h, ip_h):
        raise AuthError("locked")

    user = session.scalar(select(User).where(User.phone_hmac == phone_h)) if phone_h else None
    valid = (
        user is not None
        and user.pin_reset_required
        and user.pin_reset_code_hash is not None
        and aware(user.pin_reset_expires_at) > utcnow()
        and check_password_hash(user.pin_reset_code_hash, (code or "").strip())
    )
    if not valid:
        raise _fail(session, "pin_reset", phone_h, ip_h, "reset_invalid")

    user.pin_hash = generate_password_hash(new_pin)
    _clear_reset(user)
    user.last_login_at = utcnow()
    _record(session, "pin_reset", phone_h, ip_h, success=True)
    session.commit()
    return user


def _clear_reset(user: User) -> None:
    user.pin_reset_required = False
    user.pin_reset_code_hash = None
    user.pin_reset_expires_at = None
