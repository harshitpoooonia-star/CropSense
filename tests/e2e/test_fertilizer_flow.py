"""Spec 03 in a real browser at 360x740, in Hindi: from the planner's link to
bags for the saved field, then the Soil Health Card path."""

import os
from pathlib import Path

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL not set; use scripts/run_e2e.py")
ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

SMALL_TARGETS_JS = """
() => [...document.querySelectorAll('main a, main button, main select, main input:not([type=hidden]):not([type=radio]), main label:has(input[type=radio])')]
  .map(el => el.getBoundingClientRect()).filter(r => r.width > 1 && (r.width < 48 || r.height < 48)).length
"""


def set_up_field(page):
    page.goto(BASE_URL + "/field/setup")
    page.wait_for_load_state("networkidle")
    page.select_option('form:has(input[value="district"]) select[name="district_code"]', "UP-bulandshahr")
    page.locator('form:has(input[value="district"]) button[type=submit]').click()
    page.wait_for_selector('input[name="area"]')
    page.fill('input[name="area"]', "2.5")
    page.locator("form button[type=submit]").first.click()
    page.wait_for_selector('input[value="tubewell"]', state="attached")
    page.click('label:has(input[value="tubewell"])')
    page.locator("form button[type=submit]").first.click()
    page.wait_for_selector('button[name="skip"]')
    page.click('button[name="skip"]')
    page.wait_for_selector("text=आपका खेत जुड़ गया")


def test_standard_dose_for_saved_field(page):
    set_up_field(page)
    page.goto(BASE_URL + "/fertilizer?crop=wheat&season=rabi")
    page.wait_for_load_state("networkidle")
    assert page.input_value('select[name="crop"]') == "wheat"
    assert page.evaluate(SMALL_TARGETS_JS) == 0
    page.click('label:has(input[name="mode"][value="standard"])')
    page.locator("main form button[type=submit]").last.click()
    page.wait_for_selector("#fert-result article")
    result = page.locator("#fert-result")
    assert result.locator('[role="img"]').count() == 3  # urea, DAP, MOP drawn as bags
    assert "कुल: ₹" in result.inner_text()
    assert "आपकी मिट्टी की जाँच के हिसाब से बदली नहीं गई" in result.inner_text()
    assert page.evaluate("document.documentElement.scrollWidth") <= 360
    ARTIFACTS.mkdir(exist_ok=True)
    page.screenshot(path=str(ARTIFACTS / "fertilizer-wheat.png"), full_page=True)
    stored = page.evaluate("JSON.parse(localStorage.getItem('agrisense.profile'))")
    assert stored["last_results"]["fertilizer"]["value"]["crop"] == "wheat"
    assert page.console_errors == []


def test_soil_health_card_dose(page):
    set_up_field(page)
    page.goto(BASE_URL + "/fertilizer")
    page.click('label:has(input[name="mode"][value="card"])')
    page.fill('input[name="card_urea"]', "260")
    page.fill('input[name="card_dap"]', "130")
    page.locator("main form button[type=submit]").last.click()
    page.wait_for_selector("#fert-result article")
    text = page.inner_text("#fert-result")
    assert "आपके मृदा स्वास्थ्य कार्ड से" in text and "आपका मृदा स्वास्थ्य कार्ड" in text
