"""Small, editable vocabulary used to suggest phrase-review categories."""

import re
import tomllib
from pathlib import Path


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", value.casefold()))


def load_vocabulary(path: str | Path) -> list[dict[str, object]]:
    """Load category terms and aliases from a TOML vocabulary file."""
    with Path(path).open("rb") as stream:
        data = tomllib.load(stream)
    terms = data.get("terms", [])
    if not isinstance(terms, list):
        raise ValueError("Vocabulary must contain [[terms]] entries")

    normalized = []
    for index, term in enumerate(terms, start=1):
        if not isinstance(term, dict) or not term.get("category") or not term.get("canonical"):
            raise ValueError(f"Vocabulary term {index} needs category and canonical values")
        aliases = term.get("aliases", [])
        if not isinstance(aliases, list):
            raise ValueError(f"Vocabulary term {index} aliases must be a list")
        phrases = {str(term["canonical"]), *(str(alias) for alias in aliases)}
        normalized.append({
            "category": str(term["category"]).strip(),
            "canonical": str(term["canonical"]).strip(),
            "aliases": tuple(tokens for phrase in phrases if (tokens := _tokens(phrase))),
        })
    return normalized


def suggest_categories(phrase: str, vocabulary: list[dict[str, object]]) -> tuple[str, str]:
    """Return matching seed categories and terms without rejecting unknown phrases."""
    phrase_tokens = _tokens(phrase)
    categories: set[str] = set()
    matched_terms: set[str] = set()
    for term in vocabulary:
        for alias in term["aliases"]:
            size = len(alias)
            if any(phrase_tokens[start:start + size] == alias
                   for start in range(len(phrase_tokens) - size + 1)):
                categories.add(str(term["category"]))
                matched_terms.add(str(term["canonical"]))
                break
    return (
        "; ".join(sorted(categories)) if categories else "no seed term match",
        "; ".join(sorted(matched_terms)),
    )
