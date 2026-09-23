"""Protocol for source adapters."""

from datetime import date
from typing import Protocol

from fashion_trends.models import Signal


class SignalSource(Protocol):
    name: str

    def fetch(self, observed_on: date) -> list[Signal]:
        """Return signals observed for the given date."""
