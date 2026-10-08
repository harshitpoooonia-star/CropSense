"""Spec 01 in a real browser at 360x740, in Hindi: the field wizard as a
guest, the profile kept on the phone, then "Save my farm" and logout."""

import json
import os
from pathlib import Path

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")

pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL not set; use scripts/run_e2e.py")
ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"


def stored(page):
    raw = page.evaluate("localStorage.getItem('agrisense.profile')")
    return json.loads(raw) if raw else None


def shot(page, name):
    ARTIFACTS.mkdir(exist_ok=True)
    page.screenshot(path=str(ARTIFACTS / f"wizard-{name}.png"), full_page=True)


def run_wizard(page):
    page.goto(BASE_URL + "/field/setup")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector(".leaflet-container")  # map step loads Leaflet
    shot(page, "1-where")

    page.click("[data-gps]")
    page.wait_for_selector("[data-pin-submit]:not([disabled])")
    page.click("[data-pin-submit]")
    page.wait_for_selector('input[name="stage"][value="confirm"]', state="attached")
    assert page.input_value('select[name="district_code"]') == "UP-bulandshahr"
    shot(page, "1b-confirm")
    page.locator("form button[type=submit]").first.click()

    page.wait_for_selector('input[name="area"]')
    page.fill('input[name="area"]', "2.5")
    page.select_option('select[name="area_unit"]', "acre")
    shot(page, "2-area")
    page.locator("form button[type=submit]").first.click()

    page.wait_for_selector('input[value="tubewell"]', state="attached")
    page.click('label:has(input[value="tubewell"])')
    page.locator("form button[type=submit]").first.click()

    page.wait_for_selector('button[name="skip"]')
    shot(page, "4-soil")
    page.click('button[name="skip"]')
    page.wait_for_selector("text=आपका खेत जुड़ गया")
    shot(page, "5-done")


def test_guest_sets_up_a_field_with_gps(gps_page):
    page = gps_page
    page.goto(BASE_URL + "/")
    page.wait_for_load_state("networkidle")
    assert not any("leaflet" in url for url in page.requested), "Leaflet must load only on the map step"

    run_wizard(page)
    profile = stored(page)
    assert profile["farm"]["district_code"] == "UP-bulandshahr"
    assert profile["farm"]["location_source"] == "gps"
    assert profile["plots"][0]["area_ha"] == "1.0117"
    assert profile["plots"][0]["soil_skipped"] is True
    assert page.console_errors == []

    # Another tab of the app reads the same profile from the phone.
    page.goto(BASE_URL + "/field")
    page.wait_for_selector("text=बुलन्दशहर")
    assert page.locator("text=भरोसा कम").count() == 1  # soil unknown -> low confidence


def test_profile_survives_a_reload_and_back_keeps_values(gps_page):
    run_wizard(gps_page)
    page = gps_page
    page.goto(BASE_URL + "/field/setup?step=area")
    page.wait_for_function("document.querySelector('input[name=area]').value === '2.5'")
    page.locator("form").last.locator("button").click()  # Back
    page.wait_for_selector('input[name="stage"][value="pin"]', state="attached")


def test_choose_district_without_gps(page):
    page.goto(BASE_URL + "/field/setup")
    page.wait_for_load_state("networkidle")
    page.select_option('form:has(input[value="district"]) select[name="district_code"]', "UP-gautam-buddh-nagar")
    page.locator('form:has(input[value="district"]) button[type=submit]').click()
    page.wait_for_selector('input[name="area"]')
    assert stored(page)["farm"]["location_source"] == "district"


def test_save_my_farm_then_logout_clears_the_phone(gps_page):
    page = gps_page
    run_wizard(page)
    page.wait_for_function("navigator.serviceWorker.controller !== null")  # so /field gets saved offline
    page.goto(BASE_URL + "/farm/save")
    page.fill('input[name="phone"]', "9876500011")
    page.fill('input[name="pin"]', "4826")
    page.fill('input[name="pin_confirm"]', "4826")
    page.click('label:has(input[name="consent"])')
    page.locator("main form button[type=submit]").click()
    page.wait_for_url(BASE_URL + "/field")
    page.wait_for_selector("text=बुलन्दशहर")
    assert stored(page)["farm"]["district_code"] == "UP-bulandshahr"
    saved = page.evaluate("fetch('/api/profile').then(r => r.json())")
    assert saved["plots"][0]["irrigation_source"] == "tubewell"

    page.goto(BASE_URL + "/more")
    page.locator("form[action='/logout'] button").click()
    page.wait_for_load_state("networkidle")
    assert stored(page) is None
    # The logged-in farm's pages, saved for offline use, are gone too (shared phones).
    assert page.evaluate("caches.match('/field').then(Boolean)") is False
