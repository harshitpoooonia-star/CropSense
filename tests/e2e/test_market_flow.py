"""Spec 04 in a real browser at 360x740, in Hindi: a guest checks a trader's
offer for wheat against the nearest mandis (synthetic seeded prices)."""

import os
from pathlib import Path

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL not set; use scripts/run_e2e.py")
ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

SMALL_TARGETS_JS = """
() => [...document.querySelectorAll('main a, main button, main select, main input:not([type=hidden])')]
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


def test_offer_check_in_three_taps(gps_page):
    page = gps_page
    set_up_field_with_gps(page)
    page.goto(BASE_URL + "/market")
    page.wait_for_load_state("networkidle")
    page.select_option('select[name="crop"]', "wheat")      # tap 1
    page.fill('input[name="offer"]', "2000")                # tap 2
    page.locator("main form button[type=submit]").click()   # tap 3
    page.wait_for_selector("#market-board article")
    text = page.inner_text("#market-board")
    assert "मंडी भाव से कम" in text                         # below the mandi price
    assert "Bulandshahr" in text and "Khurja" in text
    assert page.evaluate(SMALL_TARGETS_JS) == 0
    assert page.evaluate("document.documentElement.scrollWidth") <= 360
    assert page.console_errors == []
    ARTIFACTS.mkdir(exist_ok=True)
    page.screenshot(path=str(ARTIFACTS / "market-offer.png"), full_page=True)


def test_transport_rate_is_remembered(gps_page):
    page = gps_page
    set_up_field_with_gps(page)
    page.goto(BASE_URL + "/market")
    page.select_option('select[name="crop"]', "wheat")
    page.fill('input[name="transport_rate"]', "2")
    page.locator("main form button[type=submit]").click()
    page.wait_for_selector("#market-board li")
    assert "ढुलाई" in page.inner_text("#market-board")
    stored = page.evaluate("JSON.parse(localStorage.getItem('agrisense.profile'))")
    assert stored["prefs"]["transport_rate"] == "2"
