"""The six moderated-test tasks (spec success metrics, roadmap Section 11),
run by a guest on one 360x740 phone in Hindi, in the order the farmers do
them. Each task starts from a screen and moves only by tapping what is on it,
the way a farmer would, never by typing a URL. A screenshot per step goes to
tests/artifacts/tasks/, and each task's time to answer to
tests/artifacts/tasks/timings.json.

This is the automated rehearsal of the kit in docs/research/moderated-test-kit.md;
it checks the app, not the farmers.
"""

import json
import os
import time
from pathlib import Path

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL not set; use scripts/run_e2e.py")
SHOTS = Path(__file__).resolve().parent.parent / "artifacts" / "tasks"
FIRST_ANSWER_BUDGET_S = 120  # spec goal 1: a guest gets a useful answer in under 2 minutes
TIMINGS: dict[str, float] = {}


@pytest.fixture(scope="module")
def phone(browser):
    """One phone for all six tasks, like one farmer's session: the field set up
    in task 1 is what tasks 2-6 use."""
    context = browser.new_context(viewport={"width": 360, "height": 740}, locale="hi-IN",
                                  geolocation={"latitude": 28.40, "longitude": 77.85}, permissions=["geolocation"])
    context.route("https://tile.openstreetmap.org/**", lambda route: route.fulfill(status=200, body=b""))
    page = context.new_page()
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.console_errors = errors
    SHOTS.mkdir(parents=True, exist_ok=True)
    for old in SHOTS.glob("*.png"):  # a renamed step mustn't leave last run's picture behind
        old.unlink()
    yield page
    context.close()
    (SHOTS / "timings.json").write_text(json.dumps(TIMINGS, indent=2), encoding="utf-8")


class Task:
    def __init__(self, page, number, name):
        self.page, self.prefix, self.name, self.step = page, f"{number}-{name}", name, 0
        self.started = time.monotonic()

    def shot(self, label):
        self.step += 1
        self.page.screenshot(path=str(SHOTS / f"{self.prefix}-{self.step:02d}-{label}.png"), full_page=True)

    def tap(self, selector):
        self.page.locator(selector).first.click()

    def answered(self):
        seconds = round(time.monotonic() - self.started, 1)
        TIMINGS[self.name] = seconds
        assert seconds < FIRST_ANSWER_BUDGET_S
        assert self.page.evaluate("document.documentElement.scrollWidth") <= 360
        assert self.page.console_errors == []


def test_1_plan_a_crop(phone):
    """"Which crop should you sow this rabi?" From the home page, with no field set up yet."""
    t = Task(phone, 1, "plan-a-crop")
    phone.goto(BASE_URL + "/")
    phone.wait_for_load_state("networkidle")
    t.shot("home")
    t.tap("main a[href='/plan']")                                      # "Plan a crop" tile
    phone.wait_for_selector('button[name="season"][value="rabi"]')
    t.shot("plan")
    t.tap('button[name="season"][value="rabi"]')
    phone.wait_for_selector("text=पहले अपने खेत के बारे में बताएँ")     # "First, tell us about your field"
    t.shot("needs-field")
    t.tap("#plan-results a[href='/field/setup']")
    phone.wait_for_selector("[data-gps]")
    t.shot("where")
    t.tap("[data-gps]")
    phone.wait_for_selector("[data-pin-submit]:not([disabled])")
    t.tap("[data-pin-submit]")
    phone.wait_for_selector('input[name="stage"][value="confirm"]', state="attached")
    t.shot("confirm-district")
    t.tap("form button[type=submit]")
    phone.wait_for_selector('input[name="area"]')
    phone.fill('input[name="area"]', "2.5")
    phone.select_option('select[name="area_unit"]', "acre")
    t.shot("area")
    t.tap("form button[type=submit]")
    phone.wait_for_selector('input[value="tubewell"]', state="attached")
    phone.click('label:has(input[value="tubewell"])')
    t.shot("water")
    t.tap("form button[type=submit]")
    phone.wait_for_selector('button[name="skip"]')
    t.shot("soil-card")
    t.tap('button[name="skip"]')
    phone.wait_for_selector("text=आपका खेत जुड़ गया")
    t.shot("field-done")
    t.tap("main a[href='/plan']")                                      # "What next? Plan a crop"
    phone.wait_for_selector('button[name="season"][value="rabi"]')
    t.tap('button[name="season"][value="rabi"]')
    phone.wait_for_selector("#plan-results article")
    assert phone.locator("#plan-results article").count() == 3
    assert "स्रोत:" in phone.inner_text("#plan-results")               # every card cites its source
    t.shot("answer")
    t.answered()


def test_2_fertilizer_bags(phone):
    """"You will sow wheat. How many bags of fertilizer for your field?" From the Field tab."""
    t = Task(phone, 2, "fertilizer-bags")
    t.tap("nav a[href='/field']")
    phone.wait_for_selector("main a[href='/fertilizer']")
    t.shot("field")
    t.tap("main a[href='/fertilizer']")                                # "Fertilizer for this field"
    phone.wait_for_selector('select[name="crop"]')
    phone.select_option('select[name="crop"]', "wheat")
    phone.click('label:has(input[name="mode"][value="standard"])')
    t.shot("fertilizer")
    t.tap("main form button[type=submit] >> nth=-1")
    phone.wait_for_selector("#fert-result article")
    result = phone.inner_text("#fert-result")
    assert phone.locator('#fert-result [role="img"]').count() >= 1    # bags drawn, not only numbers
    assert "कुल: ₹" in result
    t.shot("answer")
    t.answered()


def test_3_check_a_traders_offer(phone):
    """"A trader offers ₹2,000 a quintal for your wheat. Is that fair?" From the home page."""
    t = Task(phone, 3, "trader-offer")
    phone.goto(BASE_URL + "/")
    phone.wait_for_load_state("networkidle")
    t.tap("main a[href='/market']")                                    # "Check a price" tile
    phone.wait_for_selector('select[name="crop"]')
    t.shot("market")
    phone.select_option('select[name="crop"]', "wheat")
    phone.fill('input[name="offer"]', "2000")
    t.shot("offer")
    t.tap("main form button[type=submit]")
    phone.wait_for_selector("#market-board article")
    assert "मंडी भाव से कम" in phone.inner_text("#market-board")      # below the mandi price
    t.shot("answer")
    t.answered()


def test_4_should_i_spray_tomorrow(phone):
    """"Can you spray tomorrow?" From the Today tab."""
    t = Task(phone, 4, "spray-tomorrow")
    t.tap("nav a[href='/today']")
    phone.wait_for_selector("main a[href='/weather']")
    t.shot("today")
    t.tap("main a[href='/weather']")
    phone.wait_for_selector("#weather-advice ol > li")
    tomorrow = phone.locator("#weather-advice ol > li").nth(1)
    text = tomorrow.inner_text()
    assert "कल" in text and "छिड़काव" in text                          # tomorrow's spray verdict
    t.shot("answer")
    t.answered()


def test_5_find_a_scheme(phone):
    """"Which government schemes could you get?" From the More tab."""
    t = Task(phone, 5, "find-a-scheme")
    t.tap("nav a[href='/more']")
    phone.wait_for_selector("main a[href='/schemes']")
    t.shot("more")
    t.tap("main a[href='/schemes']")
    phone.wait_for_selector("#schemes-flow button[type=submit]")
    t.tap("#schemes-flow button[type=submit]")
    answers = [("radio", "UP"), ("keep", None), ("radio", "owner"), ("select", "wheat"), ("fill", "35"), ("radio", "no")]
    for n, (kind, value) in enumerate(answers, start=1):
        phone.wait_for_selector(f"text=सवाल {n} / 6")
        if kind == "radio":
            phone.click(f'label:has(input[value="{value}"])')
        elif kind == "select":
            phone.select_option('select[name="value"]', value)
        elif kind == "fill":
            phone.fill('input[name="value"]', value)
        t.shot(f"question-{n}")                                         # land (question 2) comes from the field
        t.tap("#schemes-flow form button[type=submit]")
    phone.wait_for_selector("text=साथ ले जाने वाले कागज़")              # papers to carry
    assert "आधिकारिक पोर्टल या CSC पर पक्का करें" in phone.inner_text("#schemes-flow")
    t.shot("answer")
    t.answered()


def test_6_save_my_farm(phone):
    """"Save your farm so it's there next time." From the More tab."""
    t = Task(phone, 6, "save-my-farm")
    t.tap("nav a[href='/more']")
    phone.wait_for_selector("main a[href='/farm/save']")
    t.shot("more")
    t.tap("main a[href='/farm/save']")
    phone.wait_for_selector('input[name="phone"]')
    phone.fill('input[name="phone"]', "9876500022")                   # test number, throwaway e2e database
    phone.fill('input[name="pin"]', "5937")
    phone.fill('input[name="pin_confirm"]', "5937")
    phone.click('label:has(input[name="consent"])')
    t.shot("form")
    t.tap("main form button[type=submit]")
    phone.wait_for_url(BASE_URL + "/field")
    phone.wait_for_selector("text=बुलन्दशहर")
    saved = phone.evaluate("fetch('/api/profile').then(r => r.json())")
    assert saved["plots"][0]["irrigation_source"] == "tubewell"       # the guest's field is now in the account
    t.shot("answer")
    t.answered()
