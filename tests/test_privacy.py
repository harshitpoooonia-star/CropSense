"""Section 11 privacy check (spec: privacy-light, DPDP Act 2023, ADR-003):
no phone numbers or names stored or put in events, nothing kept on the server
for guests, consent recorded before a farm is saved."""

import json

from sqlalchemy import select, text

from agrisense import farm_profile as fp
from agrisense.extensions import db
from agrisense.models import Event, User
from werkzeug.datastructures import MultiDict

HX = {"HX-Request": "true"}
PHONE = "9876543210"


def ready_profile():
    p = fp.empty()
    fp.apply_where(p, MultiDict({"location_source": "district", "district_code": "UP-bulandshahr"}))
    fp.apply_area(p, MultiDict({"area": "2.5", "area_unit": "acre"}))
    fp.apply_water(p, MultiDict({"irrigation_source": "tubewell"}))
    return p


def use_every_tool(client, profile):
    body = {"profile": json.dumps(profile)}
    client.post("/plan/results", headers=HX, data={**body, "season": "rabi"})
    client.post("/fertilizer/result", headers=HX, data={**body, "crop": "wheat", "mode": "standard"})
    client.post("/market/board", headers=HX, data={**body, "crop": "wheat", "offer": "2000", "transport_rate": "2"})
    client.post("/schemes/answer/exclusion", headers=HX, data={**body, "answers": json.dumps({"state": "UP"}), "value": "no"})
    client.post("/field/summary", headers=HX, data=body)


def every_stored_value():
    """Every cell of every table, as text."""
    cells = []
    for table in db.metadata.sorted_tables:
        for row in db.session.execute(text(f"SELECT * FROM {table.name}")):
            cells.extend(str(v) for v in row)
    return " ".join(cells)


# farm.name is a label for the farm ("canal field"), from ADR-003. Nothing fills it
# yet; if a form ever does, its hint must say not to type a person's name.
NAME_COLUMNS_ALLOWED = {("farm", "name")}


def test_no_table_has_a_column_for_a_person_s_name_or_a_raw_phone_number():
    for table in db.metadata.sorted_tables:
        for column in table.columns:
            if "name" in column.name:
                assert (table.name, column.name) in NAME_COLUMNS_ALLOWED, (table.name, column.name)
            assert "phone" not in column.name or column.name == "phone_hmac", (table.name, column.name)


def test_a_saved_farmer_s_phone_number_is_stored_nowhere(client):
    r = client.post("/farm/save", data={"phone": PHONE, "pin": "4826", "pin_confirm": "4826", "consent": "yes",
                                        "profile": json.dumps(ready_profile())})
    assert r.status_code == 302
    use_every_tool(client, ready_profile())
    assert db.session.scalar(select(db.func.count()).select_from(Event)) >= 3  # the tools did log events
    stored = every_stored_value()
    assert PHONE not in stored and PHONE[-6:] not in stored
    for event in db.session.scalars(select(Event)):
        payload = json.dumps(event.payload)
        assert PHONE not in payload and "phone" not in payload.lower()


def test_consent_is_recorded_before_a_farm_is_saved(client):
    r = client.post("/farm/save", data={"phone": PHONE, "pin": "4826", "pin_confirm": "4826",
                                        "profile": json.dumps(ready_profile())})
    assert r.status_code != 302 and db.session.scalar(select(User)) is None
    client.post("/farm/save", data={"phone": PHONE, "pin": "4826", "pin_confirm": "4826", "consent": "yes",
                                    "profile": json.dumps(ready_profile())})
    user = db.session.scalar(select(User))
    assert user.consent_at is not None and user.consent_version


def test_guests_leave_nothing_on_the_server(client):
    use_every_tool(client, ready_profile())
    for table in ("app_user", "farm", "plot", "soil_card", "event", "login_attempt"):
        assert db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() == 0, table
