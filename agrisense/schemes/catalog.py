"""Load and check data/schemes.yaml (spec 06, ADR-004).

Unverified entries are shown only when SCHEMES_SHOW_UNVERIFIED is on
(development, tests, the style guide); production shows verified ones only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import yaml

from ..units import DATA

LEVELS = ("central", "UP", "HR")
RULE_KEYS = {"states", "ownership", "max_land_ha", "age", "no_exclusions", "irrigation", "crops", "crops_other",
             "categories"}
REQUIRED = ("id", "level", "name_en", "name_hi", "benefit_en", "benefit_hi", "rules", "documents",
            "official_url", "sources", "verified")


@dataclass(frozen=True)
class Scheme:
    id: str
    level: str
    name_en: str
    name_hi: str
    benefit_en: str
    benefit_hi: str
    rules: dict
    documents: list[dict]
    official_url: str
    sources: list[str]
    verified: bool
    last_checked: str | None = None
    deadline: str | None = None
    deadline_note_en: str | None = None
    deadline_note_hi: str | None = None
    notes: str | None = None
    extra: dict = field(default_factory=dict)

    def name(self, locale: str) -> str:
        return self.name_hi if locale == "hi" else self.name_en

    def benefit(self, locale: str) -> str:
        return self.benefit_hi if locale == "hi" else self.benefit_en

    def deadline_note(self, locale: str) -> str | None:
        return self.deadline_note_hi if locale == "hi" else self.deadline_note_en

    def document_names(self, locale: str) -> list[str]:
        return [d["hi"] if locale == "hi" else d["en"] for d in self.documents]


class CatalogError(ValueError):
    pass


def validate(entry: dict) -> None:
    missing = [k for k in REQUIRED if k not in entry]
    if missing:
        raise CatalogError(f"{entry.get('id', '?')}: missing {missing}")
    if entry["level"] not in LEVELS:
        raise CatalogError(f"{entry['id']}: level must be one of {LEVELS}")
    unknown = set(entry["rules"]) - RULE_KEYS
    if unknown:
        raise CatalogError(f"{entry['id']}: unknown rules {sorted(unknown)}")
    if not entry["official_url"].startswith("https://"):
        raise CatalogError(f"{entry['id']}: official_url must be https")
    if not entry["sources"]:
        raise CatalogError(f"{entry['id']}: needs at least one source")
    if entry["verified"] and not entry.get("last_checked"):
        raise CatalogError(f"{entry['id']}: verified entries need last_checked")
    for doc in entry["documents"]:
        if not (doc.get("en") and doc.get("hi")):
            raise CatalogError(f"{entry['id']}: every document needs en and hi")


@lru_cache(maxsize=1)
def schemes() -> list[Scheme]:
    with (DATA / "schemes.yaml").open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)["schemes"]
    ids = [e.get("id") for e in raw]
    if len(ids) != len(set(ids)):
        raise CatalogError("duplicate scheme ids")
    out = []
    for entry in raw:
        validate(entry)
        known = {k: entry.get(k) for k in Scheme.__dataclass_fields__ if k != "extra" and k in entry}
        out.append(Scheme(**known, extra={k: v for k, v in entry.items() if k not in Scheme.__dataclass_fields__}))
    return out


def visible(show_unverified: bool) -> list[Scheme]:
    return [s for s in schemes() if s.verified or show_unverified]
