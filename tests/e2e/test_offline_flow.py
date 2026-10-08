"""Section 10 in a real browser at 360x740, in Hindi: the service worker keeps
pages and the last weather answer, and shows them with a note when the phone
loses its connection."""

import os
import time
from pathlib import Path

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL not set; use scripts/run_e2e.py")
ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

SAVED_ANSWER = "यह आपका पिछला जवाब है"      # "This is your last answer"
NO_INTERNET = "इंटरनेट नहीं है"                # "No internet"


def wait_for_worker(page):
    page.wait_for_function("navigator.serviceWorker.controller !== null", timeout=15_000)


def wait_for_saved(page, key, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if page.evaluate(f"caches.open('agrisense-pages').then(c => c.match('{key}')).then(Boolean)"):
            return
        time.sleep(0.2)
    raise AssertionError(f"service worker never saved {key}")


def set_up_field_with_gps(page):
    page.goto(BASE_URL + "/field/setup")
    page.wait_for_load_state("networkidle")
    page.click("[data-gps]")
    page.wait_for_selector("[data-pin-submit]:not([disabled])")
    page.click("[data-pin-submit]")
    page.wait_for_selector('input[name="stage"][value="confirm"]', state="attached")
    page.locator("form button[type=submit]").first.click()
    page.wait_for_selector('input[name="area"]')


def test_worker_installs_and_precaches_the_shell(page):
    page.goto(BASE_URL + "/")
    wait_for_worker(page)
    shell = page.evaluate("""caches.keys().then(names => names.find(n => n.startsWith('agrisense-shell-')))
                             .then(name => caches.open(name)).then(c => c.keys()).then(ks => ks.map(r => r.url))""")
    paths = [u.removeprefix(BASE_URL) for u in shell]
    assert "/offline" in paths and any(p.startswith("/static/css/app.css?v=") for p in paths)
    assert page.console_errors == []


def test_offline_shows_saved_pages_and_the_last_answer(gps_page):
    page = gps_page
    page.goto(BASE_URL + "/")
    wait_for_worker(page)
    set_up_field_with_gps(page)
    page.goto(BASE_URL + "/schemes")
    page.wait_for_load_state("networkidle")
    page.goto(BASE_URL + "/weather")
    page.wait_for_selector("#weather-advice article")
    wait_for_saved(page, "/__last/weather/advice")
    saved = page.evaluate("caches.open('agrisense-pages').then(c => c.match('/__last/weather/advice')).then(r => r.text())")
    assert "data-profile-update" not in saved   # an old copy must never overwrite the farm on this phone
    profile = page.evaluate("localStorage.getItem('agrisense.profile')")

    page.context.set_offline(True)
    try:
        page.reload()
        page.wait_for_selector(f"text={SAVED_ANSWER}")
        note = page.inner_text("#weather-advice [role=status]")
        assert "{time}" not in note and NO_INTERNET in note
        assert page.locator("#weather-advice ol > li").count() == 3   # the saved 3-day advice
        assert page.evaluate("localStorage.getItem('agrisense.profile')") == profile
        assert page.evaluate("document.documentElement.scrollWidth") <= 360
        ARTIFACTS.mkdir(exist_ok=True)
        page.screenshot(path=str(ARTIFACTS / "offline-weather.png"), full_page=True)

        # A page opened before, and a step with no saved answer.
        page.goto(BASE_URL + "/schemes")
        page.click("#schemes-flow button[type=submit]")
        page.wait_for_selector("#schemes-flow [role=alert]")
        assert NO_INTERNET in page.inner_text("#schemes-flow")

        # A page never opened: the bilingual offline page.
        page.goto(BASE_URL + "/fertilizer")
        page.wait_for_selector("text=No internet")
        assert NO_INTERNET in page.inner_text("main")
        page.screenshot(path=str(ARTIFACTS / "offline-page.png"), full_page=True)
    finally:
        page.context.set_offline(False)
