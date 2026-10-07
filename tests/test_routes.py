import re

import pytest

from agrisense import create_app
from agrisense.extensions import db
from agrisense.models import User

TOOL_ROUTES = ["/plan", "/fertilizer", "/market", "/weather", "/schemes"]
PUBLIC_ROUTES = ["/", "/today", "/field", "/more", "/expert", "/styleguide", *TOOL_ROUTES, "/farm/save", "/login", "/pin/reset", "/api/health"]


@pytest.mark.parametrize("path", PUBLIC_ROUTES)
def test_every_public_route_works_as_guest(client, path):
    assert client.get(path).status_code == 200


def test_health_reports_db(client):
    assert client.get("/api/health").get_json() == {"status": "ok", "db": "ok"}


@pytest.mark.parametrize("old, new", [("/home", "/plan"), ("/history", "/")])
def test_legacy_routes_redirect(client, old, new):
    response = client.get(old)
    assert response.status_code == 302
    assert response.headers["Location"] == new


@pytest.mark.parametrize("path", ["/predict", "/sign_up_submit", "/api/me", "/api/recommendation-history"])
def test_old_endpoints_are_gone(client, path):
    assert client.get(path).status_code == 404
    assert client.post(path).status_code in (404, 405)


def test_default_language_is_hindi(client):
    assert '<html lang="hi">' in client.get("/").get_data(as_text=True)


def test_language_switch_sets_cookie_and_stays_on_page(client):
    response = client.get("/lang/en?next=/market")
    assert response.headers["Location"] == "/market"
    assert "lang=en" in response.headers["Set-Cookie"]
    assert '<html lang="en">' in client.get("/market").get_data(as_text=True)


@pytest.mark.parametrize("target", ["//evil.example", "https://evil.example", "/\\evil.example"])
def test_language_switch_refuses_offsite_redirects(client, target):
    assert client.get(f"/lang/en?next={target}").headers["Location"] == "/"


def test_unknown_language_is_ignored(client):
    assert "Set-Cookie" not in client.get("/lang/fr").headers


def _save(client, phone="9876543210", pin="4826"):
    return client.post(
        "/farm/save", data={"phone": phone, "pin": pin, "pin_confirm": pin, "consent": "yes"}
    )


def test_save_farm_logs_in_and_logout_ends_session(client):
    assert _save(client).status_code == 302
    assert "Log out" in client.get("/more").get_data(as_text=True) or "लॉग आउट" in client.get("/more").get_data(as_text=True)
    client.post("/logout")
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_save_farm_without_consent_is_refused(client):
    response = client.post("/farm/save", data={"phone": "9876543210", "pin": "4826", "pin_confirm": "4826"})
    assert response.status_code == 400
    assert db.session.query(User).count() == 0


def test_login_statuses(client):
    _save(client)
    client.post("/logout")
    assert client.post("/login", data={"phone": "9876543210", "pin": "0000"}).status_code == 401
    assert client.post("/login", data={"phone": "9876543210", "pin": "4826"}).status_code == 302
    client.post("/logout")
    for _ in range(5):
        client.post("/login", data={"phone": "9876543210", "pin": "0000"})
    assert client.post("/login", data={"phone": "9876543210", "pin": "4826"}).status_code == 429


def test_login_rotates_the_session(client):
    with client.session_transaction() as sess:
        sess["planted"] = "attacker-value"
    _save(client)
    with client.session_transaction() as sess:
        assert "planted" not in sess


def test_helper_page_needs_a_helper(client):
    assert client.get("/helper/pin-reset").status_code == 302  # guest -> login
    _save(client)
    assert client.get("/helper/pin-reset").status_code == 403


def test_helper_reset_flow_over_http(client):
    _save(client, phone="9876543210", pin="4826")
    client.post("/logout")
    _save(client, phone="9000000001", pin="5739")
    helper = db.session.query(User).order_by(User.id.desc()).first()
    helper.role = "helper"
    db.session.commit()

    page = client.post("/helper/pin-reset", data={"phone": "9876543210"})
    assert page.headers["Cache-Control"] == "no-store"
    code = re.search(r'id="reset-code">(\d{6})<', page.get_data(as_text=True)).group(1)
    client.post("/logout")

    response = client.post(
        "/pin/reset", data={"phone": "9876543210", "code": code, "pin": "7351", "pin_confirm": "7351"}
    )
    assert response.status_code == 302
    client.post("/logout")
    assert client.post("/login", data={"phone": "9876543210", "pin": "7351"}).status_code == 302


def test_forms_require_csrf_token_when_enabled():
    app = create_app("testing", {"WTF_CSRF_ENABLED": True})
    with app.app_context():
        db.create_all()
        client = app.test_client()
        response = client.post("/login", data={"phone": "9876543210", "pin": "4826"})
        assert response.status_code == 400
        assert 'name="csrf_token"' in client.get("/login").get_data(as_text=True)
        db.drop_all()
