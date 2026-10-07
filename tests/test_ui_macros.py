"""Section 3 macros render the trust layer and never show status by colour alone."""

import re
from datetime import date

import pytest
from flask import render_template_string
from flask_babel import force_locale


def render(app, source, locale="en", **context):
    with app.test_request_context("/"), force_locale(locale):
        app.preprocess_request()
        return render_template_string(source, **context)


@pytest.mark.parametrize(
    "status, icon, word",
    [("good", "i-check", "Good"), ("warning", "i-alert", "Careful"), ("critical", "i-stop", "Don't")],
)
def test_verdict_pill_has_icon_and_word(app, status, icon, word):
    html = render(app, "{{ ui.verdict_pill(s) }}", s=status)
    assert f'href="#{icon}"' in html
    assert word in html.replace("&#39;", "'")


@pytest.mark.parametrize("level, word", [("high", "High confidence"), ("medium", "Medium confidence"), ("low", "Low confidence")])
def test_confidence_badge(app, level, word):
    html = render(app, "{{ ui.confidence_badge(l) }}", l=level)
    assert word in html and "<svg" in html


TRUST = {
    "reasons": ["Reason one"],
    "sources": [{"name": "Agmarknet", "date": date(2026, 10, 6)}, {"name": "your soil card", "date": None}],
    "confidence": "low",
    "estimated_fields": ["soil nitrogen"],
}
CARD = '{% call ui.result_card("Title", trust, share_text=share) %}<p id="body">value</p>{% endcall %}'


def test_result_card_carries_the_trust_layer(app):
    html = render(app, CARD, trust=TRUST, share="Wheat & mustard: 3 bags")
    assert '<p id="body">value</p>' in html
    assert "Reason one" in html
    assert "Estimated, not measured: soil nitrogen" in html
    assert "Agmarknet (Oct 6, 2026)" in html and "your soil card" in html
    assert "Low confidence" in html
    assert 'href="/expert"' in html
    assert "https://wa.me/?text=Wheat%20%26%20mustard%3A%203%20bags" in html


def test_result_card_in_hindi(app):
    html = render(app, CARD, locale="hi", trust=TRUST, share=None)
    assert "स्रोत:" in html and "विशेषज्ञ से पूछें" in html and "भरोसा कम" in html
    assert "wa.me" not in html


@pytest.mark.parametrize("count, whole, part", [(3, 3, False), (3.5, 3, True), (0.25, 0, True), (15, 12, False)])
def test_bag_icons(app, count, whole, part):
    html = render(app, "{{ ui.bag_icons(n, 'Urea') }}", n=count)
    full_icons = len(re.findall(r'class="size-9 shrink-0"', html))
    assert full_icons == whole + (1 if part else 0)  # the part bag's fill layer is a full icon, clipped
    assert ("width:" in html) == part
    if count == 15:
        assert "+3" in html
    assert 'role="img"' in html and "bags of Urea" in html


def test_number_input_selects_unit_and_shows_error(app):
    html = render(
        app,
        "{{ ui.number_input('area', 'Area', area_units, 'area_unit', value='2', unit_value='hectare', error='Bad') }}",
    )
    assert '<option value="hectare" selected>' in html
    assert 'inputmode="decimal"' in html
    assert 'aria-invalid="true"' in html and 'aria-describedby=" area-error"' in html


def test_units_are_translated(app):
    html = render(app, "{% for c, l in area_units %}{{ l }} {% endfor %}", locale="hi")
    assert html.split() == ["एकड़", "बीघा", "हेक्टेयर"]


def test_bottom_nav_marks_the_active_tab(client):
    html = client.get("/market").get_data(as_text=True)
    active = re.findall(r'<a href="([^"]+)" aria-current="page"', html)
    assert active == ["/market"]
    for href in ("/today", "/plan", "/field", "/market", "/more"):
        assert f'href="{href}"' in html


def test_fertilizer_lights_the_plan_tab(client):
    html = client.get("/fertilizer").get_data(as_text=True)
    assert re.findall(r'<a href="([^"]+)" aria-current="page"', html) == ["/plan"]


def test_pages_render_in_hindi(client):
    client.set_cookie("lang", "hi")
    html = client.get("/").get_data(as_text=True)
    assert "बुआई से बिक्री तक" in html and "हम बीज या दवा नहीं बेचते।" in html
    assert 'href="/static/fonts/mukta-400-devanagari.woff2"' in html


def test_styleguide_shows_both_languages(client):
    html = client.get("/styleguide").get_data(as_text=True)
    assert '<section lang="hi"' in html and '<section lang="en"' in html
    assert "भरोसा मध्यम" in html and "Medium confidence" in html


def test_styleguide_is_off_in_production(monkeypatch):
    from agrisense import create_app

    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("PHONE_PEPPER", "p")
    monkeypatch.delenv("STYLEGUIDE", raising=False)
    assert create_app("production").test_client().get("/styleguide").status_code == 404
