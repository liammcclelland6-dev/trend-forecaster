"""Source-neutral candidate phrase extraction from article evidence."""

import json
import re
import unicodedata
from collections import Counter

from fashion_trends.models import PhraseMention, Signal

_STOPWORDS = {
    "a", "about", "after", "all", "also", "am", "an", "and", "any", "are", "as",
    "at", "be", "because", "been", "before", "being", "between", "but", "by", "can",
    "could", "did", "do", "does", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "he", "her", "here", "hers", "him", "his", "how",
    "i", "if", "in", "into", "is", "it", "its", "just", "may", "me", "might", "more",
    "most", "my", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "our", "out", "over", "own", "same", "she", "should", "so", "some", "such", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "this", "those",
    "through", "to", "too", "under", "until", "up", "us", "very", "was", "we", "were",
    "what", "when", "where", "which", "while", "who", "why", "will", "with", "would",
    "you", "your", "yours", "s", "t", "re", "ve", "ll", "d", "m",
    "fashion", "clothes", "clothing", "collection", "collections", "designer", "designers",
    "dress", "dresses", "fashionable", "get", "gets", "getting", "look", "looks", "new",
    "outfit", "outfits", "season", "seasons", "style", "styles", "trend", "trends", "wear",
    "wearing", "way", "ways", "everything", "essential", "essentials", "must", "need", "needs",
    "know", "everyone", "people", "proof", "copy", "guide", "launch", "today", "why",
    "consider", "one", "work", "everything", "incredible", "moments", "became", "takes",
    "brand", "brands", "fall", "week", "weeks", "best", "house", "september",
    "continue", "reading",
}
_MAX_PHRASES_PER_ARTICLE = 80


def _words(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return [
        word for word in re.findall(r"[a-z0-9]+", normalized)
        if not word.isdigit() and word not in _STOPWORDS and len(word) > 2
    ]


def _ngrams(words: list[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for size in (1, 2, 3):
        for index in range(len(words) - size + 1):
            counts[" ".join(words[index:index + size])] += 1
    return counts


def _article_text(signal: Signal) -> tuple[str, str]:
    try:
        metadata = json.loads(signal.metadata or "{}")
    except (TypeError, json.JSONDecodeError):
        metadata = {}
    title = str(metadata.get("title") or signal.text)
    summary = str(metadata.get("summary") or "")
    return title, summary


def extract_phrases(signal: Signal) -> list[PhraseMention]:
    """Return article phrases as independent mentions, preserving the source evidence."""
    title, summary = _article_text(signal)
    title_words = _words(title)
    summary_words = _words(summary[:4000])
    title_counts = _ngrams(title_words)
    all_counts = title_counts + _ngrams(summary_words)
    if not all_counts:
        return []

    ranked = sorted(
        all_counts,
        key=lambda phrase: (
            phrase in title_counts,
            all_counts[phrase],
            len(phrase.split()),
            phrase,
        ),
        reverse=True,
    )[:_MAX_PHRASES_PER_ARTICLE]
    return [PhraseMention(signal, phrase) for phrase in ranked]
