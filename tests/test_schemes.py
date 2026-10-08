"""Scheme Finder (spec 06): one rule-engine test per scheme, catalogue checks, HTTP."""

import json
from decimal import Decimal

import pytest
import yaml
from werkzeug.datastructures import MultiDict

from agrisense import create_app
from agrisense import farm_profile as fp
from agrisense.schemes import catalog, engine
from agrisense.schemes.engine import Answers

HX = {"HX-Request": "true"}
UP_SMALL_OWNER = Answers(state="UP", land_ha=Decimal("1.0"), ownership="owner", crop="wheat", age=30,
                         exclusion="no", irrigation="tubewell")


def scheme(sid):
    return next(s for s in catalog.schemes() if s.id == sid)


def status(sid, **changes):
    return engine.evaluate(scheme(sid), Answers(**{**UP_SMALL_OWNER.__dict__, **changes})).status


# ---------------------------------------------------------------- catalogue


def test_catalogue_loads_and_every_entry_is_unverified_with_sources():
    entries = catalog.schemes()
    assert {s.id for s in entries} >= {"pm-kisan", "pmfby", "kcc", "pm-kmy", "up-kdky", "up-tubewell-power",
                                       "hr-mfmb", "hr-bby"}
    for s in entries:
        assert s.sources and s.official_url.startswith("https://") and s.name_hi and s.benefit_hi
        assert s.verified is False  # a person flips this after checking the official page


@pytest.mark.parametrize("bad, message", [
    ({"level": "MP"}, "level"), ({"rules": {"colour": "red"}}, "unknown rules"),
    ({"official_url": "http://x"}, "https"), ({"sources": []}, "source"),
    ({"verified": True}, "last_checked"), ({"documents": [{"en": "only english"}]}, "en and hi"),
])
def test_catalogue_validation(bad, message):
    entry = {"id": "x", "level": "central", "name_en": "x", "name_hi": "x", "benefit_en": "x", "benefit_hi": "x",
             "rules": {}, "documents": [], "official_url": "https://x", "sources": ["s"], "verified": False, **bad}
    with pytest.raises(catalog.CatalogError, match=message):
        catalog.validate(entry)


def test_yaml_rules_use_known_keys_only():
    raw = yaml.safe_load((catalog.DATA / "schemes.yaml").read_text(encoding="utf-8"))["schemes"]
    assert all(set(e["rules"]) <= catalog.RULE_KEYS for e in raw)


def test_production_hides_unverified_schemes(monkeypatch):
    for name, val in (("SECRET_KEY", "x" * 32), ("DATABASE_URL", "sqlite://"), ("PHONE_PEPPER", "p")):
        monkeypatch.setenv(name, val)
    monkeypatch.delenv("SCHEMES_SHOW_UNVERIFIED", raising=False)
    app = create_app("production")
    assert app.config["SCHEMES_SHOW_UNVERIFIED"] is False
    assert catalog.visible(False) == []  # nothing verified yet


# ---------------------------------------------------------------- one test per scheme


def test_pm_kisan():
    assert status("pm-kisan") == "likely"
    assert status("pm-kisan", ownership="tenant") == "no"
    assert status("pm-kisan", exclusion="yes") == "no"
    assert status("pm-kisan", exclusion=None) == "maybe"


def test_pmfby():
    assert status("pmfby") == "likely"
    assert status("pmfby", ownership="sharecropper") == "likely"
    assert status("pmfby", state="other") == "likely"
    assert status("pmfby", ownership=None) == "maybe"


def test_kcc():
    assert status("kcc", ownership="tenant") == "likely"
    assert status("kcc", ownership=None) == "maybe"


def test_pm_kmy():
    assert status("pm-kmy") == "likely"
    assert status("pm-kmy", age=41) == "no"
    assert status("pm-kmy", age=17) == "no"
    assert status("pm-kmy", land_ha=Decimal("2.01")) == "no"
    assert status("pm-kmy", land_ha=Decimal("2")) == "likely"
    assert status("pm-kmy", age=None) == "maybe"


def test_up_kdky():
    assert status("up-kdky", ownership="sharecropper", age=70) == "likely"
    assert status("up-kdky", age=71) == "no"
    assert status("up-kdky", state="HR") == "no"
    assert status("up-kdky", state=None) == "maybe"


def test_up_tubewell_power():
    assert status("up-tubewell-power") == "likely"
    assert status("up-tubewell-power", irrigation="canal") == "no"
    assert status("up-tubewell-power", irrigation=None) == "maybe"


def test_hr_mfmb():
    assert status("hr-mfmb", state="HR") == "likely"
    assert status("hr-mfmb") == "no"  # UP farmer


def test_hr_bby():
    assert status("hr-bby", state="HR", crop="potato") == "likely"
    assert status("hr-bby", state="HR", crop="wheat") == "maybe"  # list is partial in our data
    assert status("hr-bby", state="HR", crop=None) == "maybe"


def test_every_scheme_has_a_test():
    tested = {"pm-kisan", "pmfby", "kcc", "pm-kmy", "up-kdky", "up-tubewell-power", "hr-mfmb", "hr-bby"}
    assert {s.id for s in catalog.schemes()} == tested


# ---------------------------------------------------------------- HTTP


def profile():
    p = fp.empty()
    fp.apply_where(p, MultiDict({"location_source": "district", "district_code": "UP-bulandshahr"}))
    fp.apply_area(p, MultiDict({"area": "2.5", "area_unit": "acre"}))
    fp.apply_water(p, MultiDict({"irrigation_source": "tubewell"}))
    return p


@pytest.fixture
def en(client):
    client.set_cookie("lang", "en")


def answer(client, step, answers, **form):
    r = client.post(f"/schemes/answer/{step}", headers=HX,
                    data={"answers": json.dumps(answers), "profile": json.dumps(profile()), **form})
    return r.get_data(as_text=True)


def answers_in(html):
    import html as htmllib
    raw = html.split('name="answers" value="')[1].split('"')[0]
    return json.loads(htmllib.unescape(raw))


def test_state_and_land_are_prefilled_from_the_field(client, en):
    html = client.post("/schemes/step", headers=HX, data={"step": "state", "profile": json.dumps(profile())}).get_data(as_text=True)
    assert 'value="UP" class="size-6 accent-accent" checked' in html
    assert answers_in(html) == {"state": "UP", "land": "1.0117"}


def test_full_flow_shows_likely_schemes(client, en):
    a = {}
    for step, value in (("state", "UP"), ("land", None), ("ownership", "owner"), ("crop", "wheat"), ("age", "30")):
        html = answer(client, step, a, value=value or "") if value else answer(client, step, a, value="2.5", value_unit="acre")
        a = answers_in(html)
    html = answer(client, "exclusion", a, value="no")
    assert "Likely eligible: confirm at the official portal or a CSC" in html
    for name in ("PM-KISAN", "Fasal Bima", "Kisan Credit Card", "Maandhan", "Durghatna", "tubewell"):
        assert name in html
    assert "Not for you, and why" in html and "Only for farmers in Haryana" in html
    assert "Not yet checked against the official page" in html and "Low confidence" in html
    saved = json.loads(html.split("data-profile-update>")[1].split("</script>")[0])
    assert "pm-kisan" in saved["last_results"]["schemes"]["value"]["likely"]


def test_skip_makes_results_maybe(client, en):
    html = answer(client, "exclusion", {"state": "UP", "ownership": "owner", "age": "30", "land": "1"}, skip="1")
    assert "Depends on income tax" in html


@pytest.mark.parametrize("step, form", [("age", {"value": "abc"}), ("land", {"value": "x", "value_unit": "acre"}),
                                        ("ownership", {"value": "landlord"})])
def test_bad_answers(client, en, step, form):
    html = answer(client, step, {}, **form)
    assert 'role="alert"' in html


def test_scheme_finder_in_hindi(client):
    client.set_cookie("lang", "hi")
    html = answer(client, "exclusion", {"state": "UP", "ownership": "owner", "age": "30", "land": "1", "crop": "wheat"},
                  value="no")
    assert "प्रधानमंत्री किसान सम्मान निधि" in html and "साथ ले जाने वाले कागज़" in html


def test_production_shows_the_myscheme_pointer(monkeypatch):
    for name, val in (("SECRET_KEY", "x" * 32), ("DATABASE_URL", "sqlite://"), ("PHONE_PEPPER", "p")):
        monkeypatch.setenv(name, val)
    app = create_app("production", {"WTF_CSRF_ENABLED": False})
    from agrisense.extensions import db
    with app.app_context():
        db.create_all()
        c = app.test_client()
        c.set_cookie("lang", "en")
        html = c.post("/schemes/answer/exclusion", headers=HX, data={"answers": "{}", "profile": "", "value": "no"}).get_data(as_text=True)
    assert "myscheme.gov.in" in html and "still checking our scheme list" in html
