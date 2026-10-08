"""Spec 05 in a real browser at 360x740, in Hindi, on a seeded synthetic
forecast: the advisor's 3 days and Today's lead card."""

import os
from pathlib import Path

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL not set; use scripts/run_e2e.py")
ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

SMALL_TARGETS_JS = """
() => [...document.querySelectorAll('main a, main button')]
  .map(el => el.getBoundingClientRect()).filter(r => r.width > 1 && (r.width < 48 || r.height < 48)).length
"""


def set_up_field_with_gps(page):
    page.goto(BASE_URL + "/field/setup")
    page.wait_for_load_state("networkidle")
    page.click("[data-gps]")
    page.wait_for_selector("[data-pin-submit]:not([disabled])")
    page.click("[data-pin-submit]")
    page.wait_for_selector('input[name="stage"][value="confirm"]', state="attached")
    page.locator("form button[type=submit]").first.click()
    page.wait_for_selector('input[name="area"]')


def test_three_day_advice(gps_page):
    page = gps_page
    set_up_field_with_gps(page)
    page.goto(BASE_URL + "/weather")
    page.wait_for_selector("#weather-advice article")
    days = page.locator("#weather-advice ol > li")
    assert days.count() == 3
    text = page.inner_text("#weather-advice")
    assert "कल" in text                                   # "Tomorrow"
    assert "सिंचाई रोकें" in text                          # rain tomorrow -> hold irrigation
    assert "Open-Meteo.com (CC BY 4.0)" in text
    assert page.evaluate(SMALL_TARGETS_JS) == 0
    assert page.evaluate("document.documentElement.scrollWidth") <= 360
    assert page.console_errors == []
    ARTIFACTS.mkdir(exist_ok=True)
    page.screenshot(path=str(ARTIFACTS / "weather-advice.png"), full_page=True)


def test_today_lead_card(gps_page):
    page = gps_page
    set_up_field_with_gps(page)
    page.goto(BASE_URL + "/today")
    page.wait_for_selector("text=आज छिड़काव या सिंचाई?")
    assert page.locator("a[href='/weather']").count() >= 1
