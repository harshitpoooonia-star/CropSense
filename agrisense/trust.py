"""The trust layer every tool returns (spec P0-8, spec 01 R5).

    TrustResult(value, reasons, sources, confidence, estimated_fields)

`result_card` renders it. `to_dict()` is the JSON stored in the guest
profile's `last_results` and in `event.payload` (ADR-003).

Confidence rule: an answer built on an estimated input is at most *medium*;
one missing a required input is at most *low*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

LEVELS = ("low", "medium", "high")


@dataclass(frozen=True)
class Source:
    name: str
    date: date | None = None

    def to_dict(self) -> dict:
        return {"name": self.name, "date": self.date.isoformat() if self.date else None}

    @classmethod
    def from_dict(cls, data: dict) -> Source:
        raw = data.get("date")
        return cls(name=str(data.get("name", "")), date=date.fromisoformat(raw) if raw else None)


@dataclass(frozen=True)
class TrustResult:
    value: Any
    confidence: str
    reasons: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    estimated_fields: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.confidence not in LEVELS:
            raise ValueError(f"confidence must be one of {LEVELS}")
        if not self.sources:
            raise ValueError("every result needs at least one source")

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "reasons": list(self.reasons),
            "sources": [s.to_dict() for s in self.sources],
            "confidence": self.confidence,
            "estimated_fields": list(self.estimated_fields),
        }

    @classmethod
    def from_dict(cls, data: dict) -> TrustResult:
        return cls(
            value=data.get("value"),
            confidence=data.get("confidence", "low"),
            reasons=[str(r) for r in data.get("reasons", [])],
            sources=[Source.from_dict(s) for s in data.get("sources", [])],
            estimated_fields=[str(f) for f in data.get("estimated_fields", [])],
        )


def cap(confidence: str, ceiling: str) -> str:
    return LEVELS[min(LEVELS.index(confidence), LEVELS.index(ceiling))]


def apply_input_rule(confidence: str, *, any_estimated: bool, any_unknown: bool) -> str:
    if any_unknown:
        return cap(confidence, "low")
    if any_estimated:
        return cap(confidence, "medium")
    return confidence
