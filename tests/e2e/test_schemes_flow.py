"""Spec 06 in a real browser at 360x740, in Hindi: six questions as a guest,
then likely-eligible schemes with papers and the confirm-at-portal label."""

import os
from pathlib import Path

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL not set; use scripts/run_e2e.py")
ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

SMALL_TARGETS_JS = """
() => [...document.querySelectorAll('main a, main button, main select, main input:not([type=hidden]):not([type=radio]), main label:has(input[type=radio]), main summary')]
  .map(el => el.getBoundingClientRect()).filter(r => r.width > 1 && (r.width < 48 || r.height < 48)).length
"""


def next_question(page, n):
    page.wait_for_selector(f"text=सवाल {n} / 6")


def test_six_questions_to_schemes(page):
    page.goto(BASE_URL + "/schemes")
    page.wait_for_load_state("networkidle")
    page.click("#schemes-flow button[type=submit]")                      # Start

    next_question(page, 1)
    assert page.evaluate(SMALL_TARGETS_JS) == 0
    page.click('label:has(input[value="UP"])')
    page.locator("#schemes-flow form button[type=submit]").first.click()
    next_question(page, 2)
    page.fill('input[name="value"]', "2")
    page.locator("#schemes-flow form button[type=submit]").first.click()
    next_question(page, 3)
    page.click('label:has(input[value="owner"])')
    page.locator("#schemes-flow form button[type=submit]").first.click()
    next_question(page, 4)
    page.select_option('select[name="value"]', "wheat")
    page.locator("#schemes-flow form button[type=submit]").first.click()
    next_question(page, 5)
    page.fill('input[name="value"]', "30")
    page.locator("#schemes-flow form button[type=submit]").first.click()
    next_question(page, 6)
    page.click('label:has(input[value="no"])')
    page.locator("#schemes-flow form button[type=submit]").first.click()

    page.wait_for_selector("text=साथ ले जाने वाले कागज़")
    text = page.inner_text("#schemes-flow")
    assert "आधिकारिक पोर्टल या CSC पर पक्का करें" in text
    assert "प्रधानमंत्री किसान सम्मान निधि" in text
    assert page.evaluate(SMALL_TARGETS_JS) == 0
    assert page.evaluate("document.documentElement.scrollWidth") <= 360
    assert page.console_errors == []
    ARTIFACTS.mkdir(exist_ok=True)
    page.screenshot(path=str(ARTIFACTS / "schemes-results.png"), full_page=True)


def test_skip_answers(page):
    page.goto(BASE_URL + "/schemes")
    page.wait_for_load_state("networkidle")
    page.click("#schemes-flow button[type=submit]")
    for n in range(1, 7):
        next_question(page, n)
        page.click('#schemes-flow button[name="skip"]')
    page.wait_for_selector("text=साथ ले जाने वाले कागज़")
