"""Crop names in the farmer's language (data/crops.csv).

`dataset_label` maps the legacy Kaggle classifier labels (dataset/data.csv)
to our crop codes; crops without one (wheat, mustard, potato, sugarcane) come
in through the district tables in Section 5.
"""

from __future__ import annotations

import csv
from functools import lru_cache

from .units import DATA


@lru_cache(maxsize=1)
def crops() -> dict[str, dict[str, str]]:
    with (DATA / "crops.csv").open(encoding="utf-8") as f:
        return {row["code"]: row for row in csv.DictReader(f)}


def crop_name(code: str, locale: str) -> str:
    row = crops().get(code)
    if row is None:
        return code
    return row["name_hi"] if locale == "hi" else row["name_en"]
