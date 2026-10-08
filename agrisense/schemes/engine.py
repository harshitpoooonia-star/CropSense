"""Likely-eligible rule engine (spec 06). Pure functions.

Each rule says "no" when an answer clearly rules the farmer out, "maybe" when
an answer is missing or the data is partial, and nothing otherwise. A scheme
is "likely" only when no rule says no or maybe. Results are never final:
the screen says to confirm at the official portal or a CSC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .catalog import Scheme

QUESTIONS = ("state", "land", "ownership", "crop", "age", "exclusion")


@dataclass(frozen=True)
class Answers:
    state: str | None = None  # UP | HR | other
    land_ha: Decimal | None = None
    ownership: str | None = None  # owner | tenant | sharecropper
    crop: str | None = None
    age: int | None = None
    exclusion: str | None = None  # yes | no: income tax / government job / pension in the family
    irrigation: str | None = None  # from the saved field
    category: str | None = None


@dataclass
class Match:
    scheme: Scheme
    status: str  # likely | maybe | no
    reasons: list[tuple[str, dict]] = field(default_factory=list)  # (code, params) for "no" and "maybe"


def evaluate(scheme: Scheme, a: Answers) -> Match:
    no, maybe = [], []
    r = scheme.rules

    states = r.get("states")
    if states and "any" not in states:
        if a.state is None:
            maybe.append(("state_unknown", {}))
        elif a.state not in states:
            no.append(("state", {"states": states}))

    if "ownership" in r:
        if a.ownership is None:
            maybe.append(("ownership_unknown", {}))
        elif a.ownership not in r["ownership"]:
            no.append(("ownership", {"allowed": r["ownership"]}))

    if "max_land_ha" in r:
        if a.land_ha is None:
            maybe.append(("land_unknown", {}))
        elif a.land_ha > Decimal(str(r["max_land_ha"])):
            no.append(("land", {"max": r["max_land_ha"]}))

    if "age" in r:
        low, high = r["age"].get("min"), r["age"].get("max")
        if a.age is None:
            maybe.append(("age_unknown", {}))
        elif (low is not None and a.age < low) or (high is not None and a.age > high):
            no.append(("age", {"min": low, "max": high}))

    if r.get("no_exclusions"):
        if a.exclusion is None:
            maybe.append(("exclusion_unknown", {}))
        elif a.exclusion == "yes":
            no.append(("excluded", {}))

    if "irrigation" in r:
        if a.irrigation is None:
            maybe.append(("irrigation_unknown", {}))
        elif a.irrigation not in r["irrigation"]:
            no.append(("irrigation", {}))

    if "crops" in r:
        if a.crop is None:
            maybe.append(("crop_unknown", {}))
        elif a.crop not in r["crops"]:
            (maybe if r.get("crops_other") == "maybe" else no).append(("crop_unlisted", {}))

    if "categories" in r:
        if a.category is None:
            maybe.append(("category_unknown", {}))
        elif a.category not in r["categories"]:
            no.append(("category", {}))

    if no:
        return Match(scheme, "no", no)
    if maybe:
        return Match(scheme, "maybe", maybe)
    return Match(scheme, "likely", [])


def find(schemes: list[Scheme], a: Answers) -> dict[str, list[Match]]:
    out: dict[str, list[Match]] = {"likely": [], "maybe": [], "no": []}
    for scheme in schemes:
        match = evaluate(scheme, a)
        out[match.status].append(match)
    return out
