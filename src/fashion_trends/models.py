"""Shared data contracts for source signals and normalized observations."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Signal:
    source: str
    source_item_id: str
    observed_on: date
    text: str
    url: str | None = None
    confidence: float = 0.5
    metadata: str | None = None


@dataclass(frozen=True, slots=True)
class NormalizedSignal:
    signal: Signal
    concept_key: str
    canonical_label: str
