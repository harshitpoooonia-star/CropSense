"""HTTP flows for spec 01: guest wizard, guest -> saved, sync, delete."""

import json
import re

import pytest
from sqlalchemy import select

from agrisense import farm_profile as fp
from agrisense.extensions import db
from agrisense.models import Event, Farm, Plot, SoilCard, User

BULANDSHAHR = "UP-bulandshahr"
HX = {"HX-Request": "true"}


@pytest.fixture(autouse=True)
def english(client):
    client.set_cookie("lang", "en")


def stored_profile(html: str):
    """The profile the server asked the browser to save, or None."""
    match = re.search(r'<script type="application/json" data-profile-update>(.*?)</script>', html, re.S)
    return json.loads(match.group(1)) if match else "absent"


def step(client, name, profile, **fields):
    return client.post(f"/field/setup/{name}", data={"profile": json.dumps(profile), **fields}, headers=HX)


def guest_wizard(client, soil=None):
    profile = fp.empty()
    r = step(client, "where", profile, stage="district", location_source="district", district_code=BULANDSHAHR)
    profile = stored_profile(r.get_data(as_text=True))
    assert "data-profile-update" in r.get_data(as_text=True)
    r = step(client, "area", profile, area="2.5", area_unit="acre")
    profile = stored_profile(r.get_data(as_text=True))
    r = step(client, "water", profile, irrigation_source="tubewell")
    profile = stored_profile(r.get_data(as_text=True))
    r = step(client, "soil", profile, **(soil or {"skip": "1"}))
    html = r.get_data(as_text=True)
    return stored_profile(html), html


def test_guest_wizard_end_to_end(client):
    profile, html = guest_wizard(client)
    assert fp.is_complete(profile) and fp.next_step(profile) is None
    assert "Your field is set up" in html
    assert "Estimated, not measured: field location" in html  # chose district, no pin
    assert "Low confidence" in html  # soil unknown -> at most low
    assert db.session.scalar(select(Farm)) is None  # guests never stored server-side


def test_htmx_steps_are_partials_and_full_posts_are_pages(client):
    r = step(client, "area", fp.empty(), area="x", area_unit="acre")
    assert "<html" not in r.get_data(as_text=True)
    assert "Enter the field size as a number" in r.get_data(as_text=True)
    full = client.post("/field/setup/area", data={"profile": "", "area": "x", "area_unit": "acre"})
    assert "<html" in full.get_data(as_text=True) and "Step 2 of 4" in full.get_data(as_text=True)


def test_pin_is_confirmed_before_moving_on(client):
    r = step(client, "where", fp.empty(), stage="pin", location_source="gps", lat="28.40", lon="77.85")
    html = r.get_data(as_text=True)
    assert 'name="stage" value="confirm"' in html
    assert f'<option value="{BULANDSHAHR}" selected>' in html
    assert "Bulandshahr district" in html


def test_first_page_load_never_overwrites_the_phones_profile(client):
    # A guest's GET has no profile yet; it must not tell the browser to save an empty one.
    html = client.get("/field/setup").get_data(as_text=True)
    assert stored_profile(html) == "absent"
    assert 'hx-post="/field/setup/show"' in html


def test_show_prefills_a_step_from_the_profile(client):
    profile, _ = guest_wizard(client)
    r = client.post("/field/setup/show", data={"profile": json.dumps(profile), "step": "area"}, headers=HX)
    assert 'value="2.5"' in r.get_data(as_text=True)


def test_summary_for_guest_with_and_without_profile(client):
    empty = client.post("/field/summary", data={"profile": ""}, headers=HX).get_data(as_text=True)
    assert "Set up your field" in empty
    profile, _ = guest_wizard(client, soil={"soil_n": "180"})
    html = client.post("/field/summary", data={"profile": json.dumps(profile)}, headers=HX).get_data(as_text=True)
    assert "Bulandshahr" in html and "your soil card" in html and "Not known" in html


def test_expert_shows_the_district_kvk(client):
    profile, _ = guest_wizard(client)
    html = client.post("/expert/kvk", data={"profile": json.dumps(profile)}, headers=HX).get_data(as_text=True)
    assert "D.M. Road, Bulandshahr" in html
    assert "still checking this KVK" in html  # no unverified phone shown
    assert 'href="tel:' not in html


# ---------------------------------------------------------------- saving the farm


def save(client, profile, phone="9876543210", pin="4826"):
    return client.post("/farm/save", data={
        "phone": phone, "pin": pin, "pin_confirm": pin, "consent": "yes", "profile": json.dumps(profile),
    })


def test_save_my_farm_migrates_the_guest_profile(client):
    profile, _ = guest_wizard(client, soil={"soil_n": "180", "soil_ph": "7.2"})
    profile["last_results"]["planner"] = {"value": {"top": []}, "confidence": "low",
                                         "sources": [{"name": "x", "date": None}]}
    r = save(client, profile)
    assert r.status_code == 302 and r.headers["Location"] == "/field"

    user = db.session.scalar(select(User))
    plot = db.session.scalar(select(Plot))
    assert plot.farm.user_id == user.id and plot.farm.district_code == BULANDSHAHR
    assert plot.farm.location_source == "district"
    assert str(plot.area_ha) == "1.0117" and plot.area_input_unit == "acre"
    card = db.session.scalar(select(SoilCard))
    assert str(card.n_kg_ha) == "180.00" and card.is_current
    event = db.session.scalar(select(Event))
    assert event.kind == "planner.result" and event.source == "import"

    # The next full page hands the saved profile to the browser.
    synced = stored_profile(client.get("/field").get_data(as_text=True))
    assert synced["farm"]["district_code"] == BULANDSHAHR and synced["plots"][0]["soil"]["n"] == "180"
    assert stored_profile(client.get("/field").get_data(as_text=True)) == "absent"  # only once


def test_save_without_a_profile_creates_the_account_then_asks_for_the_field(client):
    r = save(client, fp.empty())
    assert r.headers["Location"] == "/field/setup"
    assert db.session.scalar(select(Farm)) is None


def test_failed_save_creates_nothing(client):
    profile, _ = guest_wizard(client)
    client.post("/farm/save", data={"phone": "9876543210", "pin": "1111", "pin_confirm": "1111",
                                    "consent": "yes", "profile": json.dumps(profile)})
    assert db.session.scalar(select(User)) is None and db.session.scalar(select(Farm)) is None


def test_logged_in_wizard_updates_the_db_and_keeps_old_soil_cards(client):
    profile, _ = guest_wizard(client, soil={"soil_n": "180"})
    save(client, profile)
    step(client, "water", {}, irrigation_source="canal")  # browser profile ignored: DB is the truth
    step(client, "soil", {}, soil_n="200")
    plot = db.session.scalar(select(Plot))
    assert plot.irrigation_source == "canal"
    cards = db.session.scalars(select(SoilCard).order_by(SoilCard.id)).all()
    assert [(str(c.n_kg_ha), c.is_current) for c in cards] == [("180.00", False), ("200.00", True)]


def test_api_profile(client):
    assert client.get("/api/profile").status_code == 401
    profile, _ = guest_wizard(client)
    save(client, profile)
    response = client.get("/api/profile")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.get_json()["plots"][0]["irrigation_source"] == "tubewell"


def test_logout_clears_the_phone(client):
    save(client, fp.empty())
    client.post("/logout")
    assert stored_profile(client.get("/").get_data(as_text=True)) is None


def test_delete_my_farm(client):
    profile, _ = guest_wizard(client, soil={"soil_n": "180"})
    save(client, profile)
    assert client.get("/farm/delete").status_code == 200
    assert client.post("/farm/delete", data={"pin": "0000"}).status_code == 401
    assert db.session.scalar(select(User)) is not None

    r = client.post("/farm/delete", data={"pin": "4826"})
    assert r.status_code == 302
    for model in (User, Farm, Plot, SoilCard, Event):
        assert db.session.scalar(select(model)) is None
    assert stored_profile(client.get("/").get_data(as_text=True)) is None


def test_delete_needs_login(client):
    assert client.get("/farm/delete").headers["Location"] == "/login"


@pytest.mark.parametrize("path", ["/field/setup?step=area", "/field/setup?step=soil"])
def test_each_step_renders_as_a_page(client, path):
    assert client.get(path).status_code == 200


def test_unknown_step_is_404(client):
    assert client.get("/field/setup?step=nope").status_code == 404
    assert client.post("/field/setup/nope").status_code == 404
