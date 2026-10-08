"""Spray and irrigation verdicts per day (spec 05). Pure functions, no I/O.

Every number comes from data/weather_thresholds.csv (cited or proposed);
rules return reason codes with parameters, and the view words them in the
farmer's language.

Spray, per day: try each hour in the morning and evening spray windows. An
hour is usable when its wind is in the cited band and neither it nor the
next `spray_rain_free_hours` hours look rainy.
    any usable hour            -> good  (best window named)
    only calm-air hours        -> warning
    otherwise                  -> critical (rain or wind named)
Irrigation, per day: rain forecast for that day and the next, and rain in
the two days before it.
    forecast >= hold, or recent >= recent  -> critical (hold)
    forecast >= check                      -> warning (check soil first)
    otherwise                              -> good (no rain expected)
Phase 2 hook: `soil_moisture` from a field sensor will refine irrigation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class Hour:
    time: datetime  # local time, start of the hour the values describe
    rain_prob: float | None
    rain_mm: float | None
    wind_kmh: float | None
    humidity: float | None
    temp_c: float | None


@dataclass(frozen=True)
class Reason:
    code: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Verdict:
    status: str  # good | warning | critical | past
    reason: Reason
    window: tuple[int, int] | None = None  # (start hour, end hour) of the best spray window


@dataclass(frozen=True)
class DayVerdict:
    day: date
    spray: Verdict
    irrigate: Verdict
    rain_mm: float
    max_rain_prob: float | None
    max_wind: float | None
    temp_min: float | None
    temp_max: float | None


def is_rainy(h: Hour, t: dict) -> bool:
    return ((h.rain_prob or 0) >= t["spray_rain_prob_pct"]) or ((h.rain_mm or 0) >= t["spray_rain_mm"])


def _window_hours(day: date, t: dict) -> list[int]:
    morning = range(int(t["spray_morning_start"]), int(t["spray_morning_end"]))
    evening = range(int(t["spray_evening_start"]), int(t["spray_evening_end"]))
    return [*morning, *evening]


def spray_day(day: date, by_time: dict[datetime, Hour], t: dict, now: datetime) -> Verdict:
    free = int(t["spray_rain_free_hours"])
    good, calm, rain_hits, wind_hits = [], [], [], []
    seen = False
    for hour in _window_hours(day, t):
        start = datetime.combine(day, datetime.min.time()) + timedelta(hours=hour)
        if start < now.replace(minute=0, second=0, microsecond=0):
            continue  # already past
        span = [by_time.get(start + timedelta(hours=k)) for k in range(free + 1)]
        if any(h is None for h in span):
            continue  # beyond the forecast: can't confirm a rain-free spell
        seen = True
        rainy = [h for h in span if is_rainy(h, t)]
        wind = span[0].wind_kmh
        if rainy:
            rain_hits.append(rainy[0])
        elif wind is not None and wind > t["spray_wind_max_kmh"]:
            wind_hits.append(wind)
        elif wind is not None and wind < t["spray_wind_min_kmh"]:
            calm.append(hour)
        else:
            good.append(hour)
    if not seen:
        return Verdict("past", Reason("window_passed"))
    if good:
        block = _first_block(good)
        winds = [by_time[datetime.combine(day, datetime.min.time()) + timedelta(hours=h)].wind_kmh for h in block]
        return Verdict("good", Reason("good_window", {"start": block[0], "end": block[-1] + 1,
                                                       "wind": round(max(w for w in winds if w is not None))}),
                       window=(block[0], block[-1] + 1))
    if calm:
        block = _first_block(calm)
        return Verdict("warning", Reason("calm", {"start": block[0], "end": block[-1] + 1}))
    if rain_hits:
        first = min(rain_hits, key=lambda h: h.time)
        return Verdict("critical", Reason("rain", {"prob": round(first.rain_prob or 0), "hour": first.time.hour}))
    return Verdict("critical", Reason("wind", {"wind": round(max(wind_hits))}))


def _first_block(hours: list[int]) -> list[int]:
    block = [hours[0]]
    for h in hours[1:]:
        if h == block[-1] + 1:
            block.append(h)
        else:
            break
    return block


def _rain_between(by_time: dict[datetime, Hour], start: datetime, end: datetime) -> float:
    return sum((h.rain_mm or 0) for time, h in by_time.items() if start <= time < end)


def irrigate_day(day: date, by_time: dict[datetime, Hour], t: dict, soil_moisture: float | None = None) -> Verdict:
    midnight = datetime.combine(day, datetime.min.time())
    coming = _rain_between(by_time, midnight, midnight + timedelta(days=2))
    recent = _rain_between(by_time, midnight - timedelta(days=2), midnight)
    # Phase 2: with `soil_moisture` from a sensor, this rule will use it first.
    if recent >= t["irrigate_recent_rain_mm"]:
        return Verdict("critical", Reason("recent_rain", {"mm": round(recent)}))
    if coming >= t["irrigate_hold_rain_mm"]:
        return Verdict("critical", Reason("rain_coming", {"mm": round(coming)}))
    if coming >= t["irrigate_check_rain_mm"]:
        return Verdict("warning", Reason("some_rain", {"mm": round(coming)}))
    return Verdict("good", Reason("no_rain", {"mm": round(coming, 1)}))


def days(hours: list[Hour], t: dict, now: datetime, count: int = 3) -> list[DayVerdict]:
    by_time = {h.time: h for h in hours}
    out = []
    for offset in range(count):
        day = now.date() + timedelta(days=offset)
        today_hours = [h for h in hours if h.time.date() == day]
        if not today_hours:
            break
        probs = [h.rain_prob for h in today_hours if h.rain_prob is not None]
        winds = [h.wind_kmh for h in today_hours if h.wind_kmh is not None]
        temps = [h.temp_c for h in today_hours if h.temp_c is not None]
        out.append(DayVerdict(
            day=day, spray=spray_day(day, by_time, t, now), irrigate=irrigate_day(day, by_time, t),
            rain_mm=round(sum((h.rain_mm or 0) for h in today_hours), 1),
            max_rain_prob=max(probs) if probs else None, max_wind=max(winds) if winds else None,
            temp_min=min(temps) if temps else None, temp_max=max(temps) if temps else None,
        ))
    return out
