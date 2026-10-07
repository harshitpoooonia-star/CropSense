"""Offline tests for scripts/check_agmarknet.py. No network, no API key.

Prices in these rows are synthetic placeholders (1/2/3), not market data.
"""

import csv
from datetime import date, timedelta

import pytest

from scripts import check_agmarknet as ca

TODAY = date(2026, 10, 14)


def _row(district, market, commodity, day, state="Uttar Pradesh"):
    return {
        "State": state,
        "District": district,
        "Market": market,
        "Commodity": commodity,
        "Variety": "Other",
        "Grade": "FAQ",
        "Arrival_Date": day.strftime("%d/%m/%Y"),
        "Min_Price": "1",
        "Max_Price": "3",
        "Modal_Price": "2",
    }


@pytest.mark.parametrize(
    "text, expected",
    [
        ("07/10/2026", date(2026, 10, 7)),
        ("2026-10-07", date(2026, 10, 7)),
        ("07-10-2026", date(2026, 10, 7)),
        ("", None),
        ("not a date", None),
    ],
)
def test_parse_date(text, expected):
    assert ca.parse_date(text) == expected


@pytest.mark.parametrize(
    "commodity, crop",
    [
        ("Wheat", "wheat"),
        ("Paddy(Dhan)(Common)", "paddy"),
        ("Mustard", "mustard"),
        ("Potato", "potato"),
        ("Sweet Potato", None),
        ("Mustard Oil", None),
        ("Wheat Atta", None),
        ("Rice", None),
        ("Coriander(Leaves)", None),
    ],
)
def test_match_crop(commodity, crop):
    assert ca.match_crop(commodity) == crop


@pytest.mark.parametrize(
    "district, canonical",
    [
        ("Gautam Buddh Nagar", "Gautam Buddh Nagar"),
        ("Gautam Budh Nagar", "Gautam Buddh Nagar"),
        ("Noida", "Gautam Buddh Nagar"),
        ("Bulandshahar", "Bulandshahr"),
        ("  hapur ", "Hapur"),
        ("Meerut", None),
    ],
)
def test_match_district(district, canonical):
    assert ca.match_district(district) == canonical


def test_normalize_lowercases_fields_and_drops_other_districts():
    rec = ca.normalize(_row("Ghaziabad", "Ghaziabad", "Wheat", TODAY))
    assert rec["district"] == "Ghaziabad"
    assert rec["crop"] == "wheat"
    assert rec["date"] == TODAY
    assert rec["modal_price"] == 2.0
    assert ca.normalize(_row("Meerut", "Meerut", "Wheat", TODAY)) is None
    assert ca.normalize({**_row("Hapur", "Hapur", "Wheat", TODAY), "Arrival_Date": "?"}) is None


def test_coverage_counts_days_latest_and_trailing_gap():
    start = date(2026, 10, 1)
    end = date(2026, 10, 14)
    dates = {date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5), date(2026, 9, 1)}
    cov = ca.coverage(dates, start, end)
    assert cov.days_with_data == 3  # 1 Sep is outside the window
    assert cov.latest == date(2026, 10, 5)
    assert cov.longest_gap == 9  # 6..14 Oct


def test_coverage_with_no_dates():
    cov = ca.coverage(set(), date(2026, 10, 1), date(2026, 10, 14))
    assert cov == ca.Coverage(0, None, 14)


def test_is_stale_uses_three_day_rule():
    assert not ca.is_stale(TODAY - timedelta(days=3), TODAY)
    assert ca.is_stale(TODAY - timedelta(days=4), TODAY)
    assert ca.is_stale(None, TODAY)


def _markets():
    rows = [
        _row("Aligarh", "Aligarh", "Wheat", TODAY),
        _row("Aligarh", "Khair", "Wheat", TODAY),
        _row("Bulandshahr", "Bulandshahr", "Potato", TODAY),
        _row("Bulandshahr", "Bulandshahr", "Potato", TODAY - timedelta(days=1)),
        _row("Gautam Buddh Nagar", "Dadri", "Onion", TODAY),  # no target crop
        _row("Ghaziabad", "Ghaziabad", "Mustard", TODAY),
    ]
    return ca.build_markets([ca.normalize(r) for r in rows])


def test_pick_prefers_near_districts_with_crop_data():
    picked = ca.pick_markets(_markets(), n=3)
    assert [m.name for m in picked] == ["Ghaziabad", "Bulandshahr", "Aligarh"]


def test_pick_falls_back_to_markets_without_crop_data():
    picked = ca.pick_markets(_markets(), n=5)
    assert picked[-1].name == "Dadri"


def test_pick_by_name_ignores_case_and_spacing():
    picked = ca.pick_markets(_markets(), names=[" khair", "DADRI", "Nowhere"])
    assert [m.name for m in picked] == ["Dadri", "Khair"]


def test_fetch_day_follows_pagination(monkeypatch):
    monkeypatch.setattr(ca, "PAGE_LIMIT", 2)
    pages = [
        {"total": 5, "records": [{"n": 1}, {"n": 2}]},
        {"total": 5, "records": [{"n": 3}, {"n": 4}]},
        {"total": 5, "records": [{"n": 5}]},
    ]
    seen = []

    def get(url, params):
        seen.append(params)
        return pages[len(seen) - 1]

    rows = ca.fetch_day("k", TODAY, get, pause=0)
    assert [r["n"] for r in rows] == [1, 2, 3, 4, 5]
    assert [p["offset"] for p in seen] == [0, 2, 4]
    assert seen[0]["filters[Arrival_Date]"] == "14/10/2026"
    assert seen[0]["filters[State]"] == "Uttar Pradesh"


def _fake_api(rows_by_day):
    def get(url, params):
        day = ca.parse_date(params["filters[Arrival_Date]"])
        records = rows_by_day.get(day, [])
        return {"total": len(records), "records": records}

    return get


def test_main_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATA_GOV_IN_KEY", "test-key")
    old = TODAY - timedelta(days=10)
    rows_by_day = {
        TODAY: [
            _row("Gautam Buddh Nagar", "Dadri", "Wheat", TODAY),
            _row("Gautam Buddh Nagar", "Dadri", "Sweet Potato", TODAY),
            _row("Meerut", "Meerut", "Wheat", TODAY),
        ],
        old: [_row("Bulandshahr", "Khurja", "Potato", old)],
    }

    code = ca.main(["--out-dir", str(tmp_path), "--pause", "0"], get=_fake_api(rows_by_day), today=TODAY)

    assert code == 0
    out = capsys.readouterr().out
    assert "Dadri" in out and "Khurja" in out and "Meerut" not in out
    assert "1 of 2 picked mandis have a price from the last 3 days" in out

    stamp = f"{(TODAY - timedelta(days=13)).isoformat()}_{TODAY.isoformat()}"
    with (tmp_path / f"agmarknet_prices_{stamp}.csv").open(encoding="utf-8") as f:
        prices = list(csv.DictReader(f))
    assert sorted(p["commodity"] for p in prices) == ["Potato", "Wheat"]  # sweet potato dropped

    with (tmp_path / f"agmarknet_summary_{stamp}.csv").open(encoding="utf-8") as f:
        summary = {r["market"]: r for r in csv.DictReader(f)}
    assert summary["Dadri"]["stale"] == "False"
    assert summary["Khurja"]["stale"] == "True"
    assert summary["Khurja"]["longest_gap"] == "10"
    # past days with rows are cached; today is not
    assert (tmp_path / "agmarknet_cache" / f"{old.isoformat()}.json").exists()
    assert not (tmp_path / "agmarknet_cache" / f"{TODAY.isoformat()}.json").exists()


def test_main_without_key_exits_2(monkeypatch):
    monkeypatch.delenv("DATA_GOV_IN_KEY", raising=False)
    assert ca.main([], get=_fake_api({}), today=TODAY) == 2


def test_main_stops_on_auth_error(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_GOV_IN_KEY", "bad")

    def get(url, params):
        raise ca.FatalApiError("HTTP 403: check DATA_GOV_IN_KEY")

    assert ca.main(["--out-dir", str(tmp_path)], get=get, today=TODAY) == 1


def test_main_reports_empty_api(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_GOV_IN_KEY", "test-key")
    assert ca.main(["--out-dir", str(tmp_path), "--pause", "0"], get=_fake_api({}), today=TODAY) == 1
