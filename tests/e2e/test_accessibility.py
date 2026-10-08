"""Accessibility review (Section 11) in a real browser at 360x740: every
screen, and every tool's answer, in Hindi and English. Checks are in a11y.py."""

import os

import pytest

from a11y import AUDIT_JS, FOCUS_JS

BASE_URL = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL not set; use scripts/run_e2e.py")

SCREENS = [
    "/", "/today", "/plan", "/fertilizer", "/field", "/field/setup", "/weather", "/market", "/more",
    "/schemes", "/expert", "/farm/save", "/login", "/pin/reset", "/offline",
]


def use_language(page, lang):
    page.context.add_cookies([{"name": "lang", "value": lang, "url": BASE_URL}])


def audit(page):
    page.wait_for_load_state("networkidle")
    return page.evaluate(AUDIT_JS)


def focus_problems(page, presses=60):
    problems = []
    page.locator("body").click(position={"x": 1, "y": 1})
    for _ in range(presses):
        page.keyboard.press("Tab")
        problem = page.evaluate(FOCUS_JS)
        if problem and problem not in problems:
            problems.append(problem)
    return problems


@pytest.mark.parametrize("lang", ["hi", "en"])
@pytest.mark.parametrize("path", SCREENS)
def test_screen(page, path, lang):
    use_language(page, lang)
    page.goto(BASE_URL + path)
    problems = audit(page)
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("path", ["/", "/plan", "/field/setup", "/market", "/schemes", "/farm/save"])
def test_keyboard_focus_is_always_visible(page, path):
    page.goto(BASE_URL + path)
    page.wait_for_load_state("networkidle")
    problems = focus_problems(page)
    assert not problems, "\n".join(problems)


def set_up_field_with_gps(page):
    page.goto(BASE_URL + "/field/setup")
    page.wait_for_load_state("networkidle")
    page.click("[data-gps]")
    page.wait_for_selector("[data-pin-submit]:not([disabled])")
    page.click("[data-pin-submit]")
    page.wait_for_selector('input[name="stage"][value="confirm"]', state="attached")
    page.locator("form button[type=submit]").first.click()
    page.wait_for_selector('input[name="area"]')
    page.fill('input[name="area"]', "2.5")
    page.locator("form button[type=submit]").first.click()
    page.wait_for_selector('input[value="tubewell"]', state="attached")
    page.click('label:has(input[value="tubewell"])')
    page.locator("form button[type=submit]").first.click()
    page.wait_for_selector('button[name="skip"]')
    page.click('button[name="skip"]')
    page.wait_for_selector("[role=status]")


@pytest.mark.parametrize("lang", ["hi", "en"])
def test_every_answer(gps_page, lang):
    page = gps_page
    use_language(page, lang)
    set_up_field_with_gps(page)
    found = {"field done": audit(page)}

    page.goto(BASE_URL + "/plan")
    page.click('button[name="season"][value="rabi"]')
    page.wait_for_selector("#plan-results article")
    found["plan"] = audit(page)

    page.goto(BASE_URL + "/fertilizer?crop=wheat&season=rabi")
    page.click('label:has(input[name="mode"][value="standard"])')
    page.locator("main form button[type=submit]").last.click()
    page.wait_for_selector("#fert-result article")
    found["fertilizer"] = audit(page)

    page.goto(BASE_URL + "/market")
    page.select_option('select[name="crop"]', "wheat")
    page.fill('input[name="offer"]', "2000")
    page.locator("main form button[type=submit]").click()
    page.wait_for_selector("#market-board article")
    found["market"] = audit(page)

    page.goto(BASE_URL + "/weather")
    page.wait_for_selector("#weather-advice article")
    found["weather"] = audit(page)

    page.goto(BASE_URL + "/today")
    page.wait_for_selector("main a[href='/weather']")
    found["today"] = audit(page)

    page.goto(BASE_URL + "/field")
    page.wait_for_selector("main article")
    found["field"] = audit(page)

    page.goto(BASE_URL + "/schemes")
    page.wait_for_load_state("networkidle")
    page.click("#schemes-flow button[type=submit]")
    for _ in range(6):
        page.wait_for_selector('#schemes-flow button[name="skip"]')
        found.setdefault("scheme question", audit(page))
        page.click('#schemes-flow button[name="skip"]')
        page.wait_for_load_state("networkidle")
    page.wait_for_selector("#schemes-flow article")
    found["schemes"] = audit(page)

    bad = {k: v for k, v in found.items() if v}
    assert not bad, "\n".join(f"{k}: {p}" for k, v in bad.items() for p in v)
