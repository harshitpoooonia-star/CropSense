"""Guest smoke test in a real browser (Playwright, webapp-testing skill).

Run with `python scripts/run_e2e.py`, which starts Flask through the skill's
with_server.py and sets E2E_BASE_URL. Skipped in the plain unit-test run.
Screenshots go to tests/artifacts/ (gitignored).
"""

import os
from pathlib import Path

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL not set; use scripts/run_e2e.py")

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"
GUEST_ROUTES = [
    "/", "/today", "/plan", "/fertilizer", "/field", "/weather", "/market", "/more",
    "/schemes", "/expert", "/farm/save", "/login", "/pin/reset", "/styleguide",
]

# Every visible control, measured at 360 px. The checkbox itself is small on
# purpose: its whole label row is the 48 px target.
TAP_TARGETS_JS = """
() => [...document.querySelectorAll('a, button, select, input:not([type=hidden]):not([type=checkbox]), label:has(input[type=checkbox])')]
  .filter(el => { const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1; })
  .map(el => { const r = el.getBoundingClientRect();
               return {tag: el.tagName, text: (el.innerText || el.name || '').trim().slice(0, 30),
                       w: Math.round(r.width), h: Math.round(r.height)}; })
  .filter(t => t.w < 48 || t.h < 48)
"""


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    # 360x740 is the spec's baseline phone.
    context = browser.new_context(viewport={"width": 360, "height": 740}, locale="hi-IN")
    page = context.new_page()
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.console_errors = errors
    yield page
    context.close()


@pytest.mark.parametrize("path", GUEST_ROUTES)
def test_guest_page_works_on_a_360px_phone(page, path):
    response = page.goto(BASE_URL + path)
    page.wait_for_load_state("networkidle")
    assert response.status == 200
    assert page.console_errors == []
    assert page.locator("html").get_attribute("lang") == "hi"
    assert page.evaluate("document.documentElement.scrollWidth") <= 360, "horizontal scroll"
    assert page.evaluate(TAP_TARGETS_JS) == [], "tap targets under 48 px"


def test_fonts_and_styles_load(page):
    page.goto(BASE_URL + "/")
    page.wait_for_load_state("networkidle")
    family = page.evaluate("getComputedStyle(document.body).fontFamily")
    assert family.startswith("Mukta")
    assert page.evaluate("document.fonts.check('16px Mukta', 'खेत')")


def test_language_switch_round_trip(page):
    page.goto(BASE_URL + "/market")
    page.get_by_role("link", name="English").click()
    page.wait_for_load_state("networkidle")
    assert page.url == BASE_URL + "/market"
    assert page.locator("html").get_attribute("lang") == "en"
    page.get_by_role("link", name="हिंदी").click()
    assert page.locator("html").get_attribute("lang") == "hi"


def test_old_home_redirects_to_planner(page):
    page.goto(BASE_URL + "/home")
    assert page.url == BASE_URL + "/plan"


def test_home_tiles_reach_each_tool(page):
    page.goto(BASE_URL + "/")
    for href in ("/plan", "/market", "/schemes"):
        assert page.locator(f"main a[href='{href}']").count() == 1


@pytest.mark.parametrize("path", ["/", "/styleguide", "/farm/save"])
def test_screenshots(page, path):
    ARTIFACTS.mkdir(exist_ok=True)
    page.goto(BASE_URL + path)
    page.wait_for_load_state("networkidle")
    name = path.strip("/") or "home"
    page.screenshot(path=str(ARTIFACTS / f"{name}-360.png"), full_page=True)
