"""Guest smoke test in a real browser (Playwright, webapp-testing skill).

Run with `python scripts/run_e2e.py`, which starts Flask through the skill's
with_server.py and sets E2E_BASE_URL. Skipped in the plain unit-test run.
"""

import os

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL not set; use scripts/run_e2e.py")

GUEST_ROUTES = ["/", "/plan", "/fertilizer", "/market", "/weather", "/schemes", "/farm/save", "/login"]


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    # 360 px is the spec's baseline phone width.
    context = browser.new_context(viewport={"width": 360, "height": 740}, locale="hi-IN")
    page = context.new_page()
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.console_errors = errors
    yield page
    context.close()


@pytest.mark.parametrize("path", GUEST_ROUTES)
def test_guest_can_open(page, path):
    response = page.goto(BASE_URL + path)
    page.wait_for_load_state("networkidle")
    assert response.status == 200
    assert page.console_errors == []
    assert page.locator("html").get_attribute("lang") == "hi"


def test_old_home_redirects_to_planner(page):
    page.goto(BASE_URL + "/home")
    assert page.url == BASE_URL + "/plan"


def test_home_links_reach_each_tool(page):
    page.goto(BASE_URL + "/")
    for href in ("/plan", "/market", "/schemes"):
        assert page.locator(f"main a[href='{href}']").count() == 1
