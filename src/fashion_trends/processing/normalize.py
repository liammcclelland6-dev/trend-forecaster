"""Deterministic starter normalizer; replaceable by semantic clustering later."""

import re
import unicodedata

from fashion_trends.models import NormalizedSignal, Signal

_ALIASES = {
    "western": ("western", "cowboy", "rodeo"),
    "belt": ("belt", "belts", "buckle", "buckles"),
    "rhinestone": ("rhinestone", "rhinestones", "bedazzled"),
}
_LABELS = {"western": "Western style", "belt": "Belts", "rhinestone": "Rhinestone details"}


def _tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return set(re.findall(r"[a-z0-9]+", normalized))


def normalize(signal: Signal) -> list[NormalizedSignal]:
    """Map a phrase to known concepts, falling back to its normalized phrase."""
    tokens = _tokens(signal.text)
    matched = [key for key, aliases in _ALIASES.items() if tokens.intersection(aliases)]
    if not matched:
        key = " ".join(sorted(tokens)) or "unknown"
        return [NormalizedSignal(signal, key, signal.text.strip().title() or "Unknown")]
    return [NormalizedSignal(signal, key, _LABELS[key]) for key in matched]
