"""Spec 02 in a real browser at 360x740, in Hindi: field set up, rabi plan,
three cards with the trust layer, Why not, and on to fertilizer."""

import os
from pathlib import Path

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL not set; use scripts/run_e2e.py")
ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

TAP_TARGETS_JS = """
() => [...document.querySelectorAll('#plan-results a, #plan-results button, #plan-results select')]
  .map(el => el.getBoundingClientRect()).filter(r => r.width > 1 && (r.width < 48 || r.height < 48)).length
"""


def set_up_field(page):
    page.goto(BASE_URL + "/field/setup")
    page.wait_for_load_state("networkidle")
    page.select_option('form:has(input[value="district"]) select[name="district_code"]', "UP-bulandshahr")
    page.locator('form:has(input[value="district"]) button[type=submit]').click()
    page.wait_for_selector('input[name="area"]')
    page.fill('input[name="area"]', "2")
    page.locator("form button[type=submit]").first.click()
    page.wait_for_selector('input[value="tubewell"]', state="attached")
    page.click('label:has(input[value="tubewell"])')
    page.locator("form button[type=submit]").first.click()
    page.wait_for_selector('button[name="skip"]')
    page.click('button[name="skip"]')
    page.wait_for_selector("text=आपका खेत जुड़ गया")


def test_plan_without_a_field_asks_for_one(page):
    page.goto(BASE_URL + "/plan")
    page.click('button[name="season"][value="rabi"]')
    page.wait_for_selector("text=पहले अपने खेत के बारे में बताएँ")


def test_rabi_plan_with_reasons_and_why_not(page):
    set_up_field(page)
    page.goto(BASE_URL + "/plan")
    page.wait_for_load_state("networkidle")
    page.click('button[name="season"][value="rabi"]')
    page.wait_for_selector("#plan-results article")

    cards = page.locator("#plan-results article")
    assert cards.count() == 3
    first = cards.first
    assert first.locator("text=स्रोत:").count() == 1
    assert first.locator("text=भरोसा मध्यम").count() + first.locator("text=भरोसा कम").count() == 1
    # Only crops with a cited fertilizer dose link on; the others say to ask the KVK.
    fert_links = page.locator("#plan-results article a[href*='/fertilizer?crop=']")
    assert fert_links.count() >= 1
    assert fert_links.count() + page.locator("text=इसकी बोरियाँ नहीं गिन सकते").count() == 3
    assert page.evaluate(TAP_TARGETS_JS) == 0
    assert page.evaluate("document.documentElement.scrollWidth") <= 360
    ARTIFACTS.mkdir(exist_ok=True)
    page.screenshot(path=str(ARTIFACTS / "planner-rabi.png"), full_page=True)

    page.select_option('select[name="crop"]', "paddy")
    page.locator('#plan-results form:has(select[name="crop"]) button').click()
    page.wait_for_selector("#why-answer li")
    assert "नहीं दिखती" in page.inner_text("#why-answer")

    href = fert_links.first.get_attribute("href")
    page.goto(BASE_URL + href)
    assert page.url.startswith(BASE_URL + "/fertilizer?crop=")
    assert page.console_errors == []

    stored = page.evaluate("JSON.parse(localStorage.getItem('agrisense.profile'))")
    assert len(stored["last_results"]["planner"]["value"]["top"]) == 3
