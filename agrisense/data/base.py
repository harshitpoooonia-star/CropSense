"""Contract every external-data adapter returns (ADR-004).

Tools turn `SourceInfo` into the trust layer's `sources[]` line and lower
their confidence when `stale` is true. `data is None` means "no data at all":
the tool shows an empty state, never a made-up number.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class SourceInfo:
    name: str  # "Agmarknet", "Open-Meteo", "your soil card"
    as_of: date | datetime | None  # the data's own date, not when we fetched it
    fetched_at: datetime | None = None
    stale: bool = False
    note: str | None = None  # e.g. "couldn't refresh, showing 5 Oct"


@dataclass(frozen=True)
class Result(Generic[T]):
    data: T | None
    source: SourceInfo
