"""District KVK contacts (data/kvk_contacts.csv), each row with its source.

A phone number shows only when the row has one; until it's verified the
expert page shows the address and the Kisan Call Centre.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache

from .units import DATA


@dataclass(frozen=True)
class Kvk:
    district_code: str
    name_en: str
    name_hi: str
    address_en: str
    phone: str
    source: str
    as_of: str

    def name(self, locale: str) -> str:
        return self.name_hi if locale == "hi" else self.name_en


@lru_cache(maxsize=1)
def contacts() -> dict[str, Kvk]:
    with (DATA / "kvk_contacts.csv").open(encoding="utf-8") as f:
        rows = {}
        for row in csv.DictReader(f):
            if not row["source"].strip():
                continue
            rows[row["district_code"]] = Kvk(**{k: row[k].strip() for k in Kvk.__dataclass_fields__})
        return rows


def for_district(code: str | None) -> Kvk | None:
    return contacts().get(code or "")
