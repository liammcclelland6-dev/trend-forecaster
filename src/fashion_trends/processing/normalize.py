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
_FALLBACK_NOISE = {
    "a", "an", "and", "are", "as", "at", "be", "became", "by", "can", "copy",
    "director", "every", "everything", "fashion", "from", "how", "in", "is", "its",
    "know", "made", "me", "new", "of", "on", "our", "own", "season", "the", "their",
    "this", "to", "today", "up", "what", "when", "why", "with", "you", "your",
    "chic", "essential", "outfit", "outfits", "pair", "pairs", "proof", "style",
    "takes", "timeless", "need", "needs", "everyone", "obsessed",
}


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", normalized)


def normalize(signal: Signal) -> list[NormalizedSignal]:
    """Map a phrase to known concepts, falling back to its normalized phrase."""
    ordered_tokens = _tokens(signal.text)
    tokens = set(ordered_tokens)
    matched = [key for key, aliases in _ALIASES.items() if tokens.intersection(aliases)]
    if not matched:
        useful_tokens = list(
            dict.fromkeys(
                token for token in ordered_tokens
                if not token.isdigit() and token not in _FALLBACK_NOISE
            )
        )[:4]
        # Keep the stable key scheme so re-collecting the same signal remains
        # idempotent even as its display label gets cleaner.
        key = " ".join(sorted(tokens)) or "unknown"
        label = " ".join(token.title() for token in useful_tokens) or "Unknown"
        return [NormalizedSignal(signal, key, label)]
    return [NormalizedSignal(signal, key, _LABELS[key]) for key in matched]
