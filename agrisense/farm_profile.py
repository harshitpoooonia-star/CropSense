"""The guest farm profile (ADR-003, spec 01): validation and wizard steps.

The browser keeps the profile in localStorage and sends it as the `profile`
form field. The server never stores a guest profile: it validates it,
applies a wizard step, and hands the result back. Shape, version 1:

    {"v": 1,
     "farm": {"lat": 28.41, "lon": 77.83, "district_code": "UP-bulandshahr",
              "location_source": "map" | "gps" | "district"},
     "plots": [{"area": {"value": "2.5", "unit": "acre"}, "area_ha": "1.0117",
                "irrigation_source": "tubewell",
                "soil": {"n": null, "p": null, "k": null, "ph": null, "oc": null,
                         "sampled_on": null},
                "soil_skipped": false}],
     "last_results": {"planner": {...trust envelope...}}}

(Values above show the shape only.) Phase 1 uses one plot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from . import districts, units
from .trust import TrustResult

VERSION = 1
STEPS = ("where", "area", "water", "soil")
LOCATION_SOURCES = ("map", "gps", "district")
IRRIGATION_SOURCES = ("tubewell", "canal", "rainfed", "purchased", "other")
TOOLS = ("planner", "fertilizer", "market", "weather", "schemes")
SOIL_KEYS = ("n", "p", "k", "ph", "oc")
# Physical limits only (pH scale, a percentage, no negative amounts). These
# catch typos; they are not agronomic thresholds.
SOIL_LIMITS = {"n": (0, None), "p": (0, None), "k": (0, None), "ph": (0, 14), "oc": (0, 100)}
INDIA_BOUNDS = ((6.0, 37.5), (68.0, 97.5))  # lat, lon box around India


@dataclass(frozen=True)
class FieldError:
    field: str
    code: str  # mapped to a translated message by the view


def empty() -> dict:
    return {
        "v": VERSION,
        "farm": {"lat": None, "lon": None, "district_code": None, "location_source": None},
        "plots": [_empty_plot()],
        "last_results": {},
        "prefs": {"transport_rate": None},  # Rs per quintal per km, the farmer's own figure
    }


def _empty_plot() -> dict:
    return {
        "area": {"value": None, "unit": None},
        "area_ha": None,
        "irrigation_source": None,
        "soil": {**{k: None for k in SOIL_KEYS}, "sampled_on": None},
        "soil_skipped": False,
    }


def plot(profile: dict) -> dict:
    return profile["plots"][0]


def is_complete(profile: dict) -> bool:
    p = plot(profile)
    return bool(profile["farm"]["district_code"] and p["area_ha"] and p["irrigation_source"])


def next_step(profile: dict) -> str | None:
    """First step still missing, or None when the field is set up."""
    p = plot(profile)
    if not profile["farm"]["district_code"]:
        return "where"
    if not p["area_ha"]:
        return "area"
    if not p["irrigation_source"]:
        return "water"
    if not p["soil_skipped"] and all(p["soil"][k] is None for k in SOIL_KEYS):
        return "soil"
    return None


# ---------------------------------------------------------------- parsing incoming JSON


def parse(raw: str | None) -> dict:
    """Whatever the browser sent -> a clean profile. Bad parts are dropped, not trusted."""
    try:
        data = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        data = {}
    if not isinstance(data, dict) or data.get("v") != VERSION:
        return empty()
    profile = empty()

    farm = data.get("farm") if isinstance(data.get("farm"), dict) else {}
    lat, lon = _float(farm.get("lat")), _float(farm.get("lon"))
    if lat is not None and lon is not None and _in_india(lat, lon):
        profile["farm"]["lat"], profile["farm"]["lon"] = round(lat, 5), round(lon, 5)
    if districts.get(farm.get("district_code")):
        profile["farm"]["district_code"] = farm["district_code"]
    if farm.get("location_source") in LOCATION_SOURCES:
        profile["farm"]["location_source"] = farm["location_source"]

    plots = data.get("plots") if isinstance(data.get("plots"), list) else []
    if plots and isinstance(plots[0], dict):
        _parse_plot(plots[0], profile)

    prefs = data.get("prefs") if isinstance(data.get("prefs"), dict) else {}
    profile["prefs"]["transport_rate"] = transport_rate(prefs.get("transport_rate"))

    results = data.get("last_results") if isinstance(data.get("last_results"), dict) else {}
    for tool, envelope in results.items():
        if tool in TOOLS and isinstance(envelope, dict):
            try:
                profile["last_results"][tool] = TrustResult.from_dict(envelope).to_dict()
            except (ValueError, TypeError, AttributeError):
                continue
    return profile


def _parse_plot(raw: dict, profile: dict) -> None:
    p = plot(profile)
    area = raw.get("area") if isinstance(raw.get("area"), dict) else {}
    try:
        p["area"], p["area_ha"] = _area(area.get("value"), area.get("unit"), profile["farm"]["district_code"])
    except (ValueError, units.UnitUnavailable):
        pass
    if raw.get("irrigation_source") in IRRIGATION_SOURCES:
        p["irrigation_source"] = raw["irrigation_source"]
    soil = raw.get("soil") if isinstance(raw.get("soil"), dict) else {}
    for key in SOIL_KEYS:
        try:
            p["soil"][key] = _soil_value(key, soil.get(key))
        except ValueError:
            p["soil"][key] = None
    p["soil"]["sampled_on"] = _past_date(soil.get("sampled_on"))
    p["soil_skipped"] = bool(raw.get("soil_skipped"))


def dumps(profile: dict) -> str:
    return json.dumps(profile, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------- wizard steps


def apply_where(profile: dict, form) -> list[FieldError]:
    """Pin (map/GPS) or a chosen district. With a pin, the nearest district is
    suggested; the farmer confirms it by submitting `district_code`."""
    farm = profile["farm"]
    source = form.get("location_source")
    code = form.get("district_code") or None
    if source in ("map", "gps"):
        lat, lon = _float(form.get("lat")), _float(form.get("lon"))
        if lat is None or lon is None or not _in_india(lat, lon):
            return [FieldError("lat", "location_invalid")]
        farm.update(lat=round(lat, 5), lon=round(lon, 5), location_source=source)
        if code is None:
            suggestion = districts.nearest(lat, lon)
            farm["district_code"] = suggestion.code if suggestion else None
            return [] if suggestion else [FieldError("district_code", "district_needed")]
    elif source == "district":
        district = districts.get(code)
        if district is None:
            return [FieldError("district_code", "district_needed")]
        farm.update(lat=district.lat, lon=district.lon, location_source="district")
    else:
        return [FieldError("lat", "location_invalid")]
    if code is not None:
        if districts.get(code) is None:
            return [FieldError("district_code", "district_needed")]
        farm["district_code"] = code
    return []


def apply_area(profile: dict, form) -> list[FieldError]:
    p = plot(profile)
    try:
        p["area"], p["area_ha"] = _area(form.get("area"), form.get("area_unit"), profile["farm"]["district_code"])
    except units.UnitUnavailable:
        return [FieldError("area", "bigha_unknown")]
    except ValueError:
        return [FieldError("area", "area_invalid")]
    return []


def apply_water(profile: dict, form) -> list[FieldError]:
    source = form.get("irrigation_source")
    if source not in IRRIGATION_SOURCES:
        return [FieldError("irrigation_source", "choose_one")]
    plot(profile)["irrigation_source"] = source
    return []


def apply_soil(profile: dict, form) -> list[FieldError]:
    p = plot(profile)
    if form.get("skip"):
        p["soil"] = {**{k: None for k in SOIL_KEYS}, "sampled_on": None}
        p["soil_skipped"] = True
        return []
    errors, values = [], {}
    for key in SOIL_KEYS:
        try:
            values[key] = _soil_value(key, form.get(f"soil_{key}"))
        except ValueError:
            errors.append(FieldError(f"soil_{key}", "number_invalid"))
    sampled = form.get("soil_sampled_on") or None
    if sampled and _past_date(sampled) is None:
        errors.append(FieldError("soil_sampled_on", "date_invalid"))
    if errors:
        return errors
    p["soil"] = {**values, "sampled_on": _past_date(sampled)}
    p["soil_skipped"] = all(v is None for v in values.values())
    return []


APPLY = {"where": apply_where, "area": apply_area, "water": apply_water, "soil": apply_soil}


# ---------------------------------------------------------------- helpers


def _float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None  # drop NaN


def _in_india(lat: float, lon: float) -> bool:
    (lat_lo, lat_hi), (lon_lo, lon_hi) = INDIA_BOUNDS
    return lat_lo <= lat <= lat_hi and lon_lo <= lon <= lon_hi


def _area(value, unit, district_code) -> tuple[dict, str]:
    if unit not in ("acre", "bigha", "hectare"):
        raise ValueError("unit")
    amount = units.parse_decimal(value)
    if amount <= 0:
        raise ValueError("area must be positive")
    hectares = units.to_hectares(amount, unit, district_code)
    return {"value": _dec(amount), "unit": unit}, _dec(hectares.quantize(Decimal("0.0001")))


def _soil_value(key: str, raw) -> str | None:
    if raw is None or str(raw).strip() == "":
        return None
    number = units.parse_decimal(raw)
    low, high = SOIL_LIMITS[key]
    if number < low or (high is not None and number > high):
        raise ValueError(key)
    return _dec(number)


def transport_rate(raw) -> str | None:
    """The farmer's transport cost, Rs per quintal per km; None if blank or not a number."""
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return _dec(units.parse_decimal(raw))
    except ValueError:
        return None


def _past_date(raw) -> str | None:
    try:
        day = date.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None
    return day.isoformat() if day <= date.today() else None


def _dec(number: Decimal) -> str:
    text = format(number.normalize(), "f")
    return text
