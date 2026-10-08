"""Shared Playwright fixtures for the e2e tests (webapp-testing skill)."""

import base64
import os

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
# 1x1 transparent PNG: stands in for OpenStreetMap tiles so tests never leave the machine.
BLANK_TILE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


def _new_page(browser, **context_args):
    # 360x740 is the spec's baseline phone; Hindi is the default language.
    context = browser.new_context(viewport={"width": 360, "height": 740}, locale="hi-IN", **context_args)
    context.route("https://tile.openstreetmap.org/**",
                  lambda route: route.fulfill(status=200, content_type="image/png", body=BLANK_TILE))
    page = context.new_page()
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.console_errors = errors
    requests: list[str] = []
    page.on("request", lambda req: requests.append(req.url))
    page.requested = requests
    return context, page


@pytest.fixture
def page(browser):
    context, page = _new_page(browser)
    yield page
    context.close()


@pytest.fixture
def gps_page(browser):
    """A phone whose GPS says it's in a Bulandshahr field."""
    context, page = _new_page(browser, geolocation={"latitude": 28.40, "longitude": 77.85}, permissions=["geolocation"])
    yield page
    context.close()
