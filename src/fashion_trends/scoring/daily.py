"""Explainable phrase evidence and temporal trend scores."""

import sqlite3
from datetime import date, timedelta


def score_day(
    connection: sqlite3.Connection,
    observed_on: date,
    source: str = "rss",
    min_mentions: int | None = None,
) -> list[dict[str, object]]:
    source_filters = {
        "rss": "o.source != 'sample'",
        "sample": "o.source = 'sample'",
        "all": "1 = 1",
    }
    if source not in source_filters:
        raise ValueError(f"Unsupported report source: {source}")
    if min_mentions is None:
        phrase_min_mentions = 2 if source == "rss" else 1
        single_word_min_mentions = 4 if source == "rss" else 1
    else:
        phrase_min_mentions = min_mentions
        single_word_min_mentions = min_mentions
    if min(phrase_min_mentions, single_word_min_mentions) < 1:
        raise ValueError("min_mentions must be at least 1")

    rows = connection.execute(
        f"""SELECT c.concept_key, c.canonical_label,
                  COUNT(DISTINCT o.source) AS source_count,
                  COUNT(*) AS observation_count,
                  COUNT(DISTINCT o.source || ':' || o.source_item_id) AS article_count,
                  GROUP_CONCAT(DISTINCT o.source) AS sources,
                  AVG(o.confidence) AS mean_confidence
           FROM observations o JOIN concepts c USING (concept_key)
           WHERE o.observed_on = ? AND {source_filters[source]}
           GROUP BY c.concept_key, c.canonical_label
           HAVING (
               (instr(c.concept_key, ' ') = 0 AND
                COUNT(DISTINCT o.source || ':' || o.source_item_id) >= ?)
               OR
               (instr(c.concept_key, ' ') > 0 AND
                COUNT(DISTINCT o.source || ':' || o.source_item_id) >= ?)
           )
           ORDER BY (COUNT(DISTINCT o.source) * 3 + COUNT(*) + AVG(o.confidence)) DESC,
                    c.canonical_label""",
        (observed_on.isoformat(), single_word_min_mentions, phrase_min_mentions),
    ).fetchall()
    results = []
    for row in rows:
        score = round(row["source_count"] * 3 + row["observation_count"] + row["mean_confidence"], 2)
        results.append({**dict(row), "score": score})
    return results


def score_window(
    connection: sqlite3.Connection,
    through_date: date,
    window_days: int = 7,
    source: str = "rss",
    min_mentions: int | None = None,
) -> list[dict[str, object]]:
    """Compare phrase mentions in two equal adjacent publication-date windows."""
    if window_days < 1:
        raise ValueError("window_days must be at least 1")
    source_filters = {
        "rss": "o.source != 'sample'",
        "sample": "o.source = 'sample'",
        "all": "1 = 1",
    }
    if source not in source_filters:
        raise ValueError(f"Unsupported report source: {source}")
    if min_mentions is None:
        phrase_min_mentions = 2 if source == "rss" else 1
        single_word_min_mentions = 4 if source == "rss" else 1
    else:
        phrase_min_mentions = min_mentions
        single_word_min_mentions = min_mentions
    if min(phrase_min_mentions, single_word_min_mentions) < 1:
        raise ValueError("min_mentions must be at least 1")

    recent_start = through_date - timedelta(days=window_days - 1)
    previous_end = recent_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=window_days - 1)
    recent_predicate = "o.observed_on >= :recent_start AND o.observed_on <= :through_date"
    previous_predicate = "o.observed_on >= :previous_start AND o.observed_on <= :previous_end"
    rows = connection.execute(
        f"""SELECT c.concept_key, c.canonical_label,
                  COUNT(DISTINCT CASE WHEN {recent_predicate}
                      THEN o.source || ':' || o.source_item_id END) AS recent_articles,
                  COUNT(DISTINCT CASE WHEN {previous_predicate}
                      THEN o.source || ':' || o.source_item_id END) AS previous_articles,
                  COUNT(DISTINCT CASE WHEN {recent_predicate} THEN o.source END) AS source_count,
                  GROUP_CONCAT(DISTINCT CASE WHEN {recent_predicate} THEN o.source END) AS sources,
                  AVG(CASE WHEN {recent_predicate} THEN o.confidence END) AS mean_confidence
           FROM observations o JOIN concepts c USING (concept_key)
           WHERE o.observed_on >= :previous_start AND o.observed_on <= :through_date
             AND {source_filters[source]}
           GROUP BY c.concept_key, c.canonical_label
           HAVING (
               (instr(c.concept_key, ' ') = 0 AND
                COUNT(DISTINCT CASE WHEN {recent_predicate}
                    THEN o.source || ':' || o.source_item_id END) >= :single_word_min)
               OR
               (instr(c.concept_key, ' ') > 0 AND
                COUNT(DISTINCT CASE WHEN {recent_predicate}
                    THEN o.source || ':' || o.source_item_id END) >= :phrase_min)
           )
           ORDER BY recent_articles DESC, source_count DESC, c.canonical_label""",
        {
            "recent_start": recent_start.isoformat(),
            "through_date": through_date.isoformat(),
            "previous_start": previous_start.isoformat(),
            "previous_end": previous_end.isoformat(),
            "single_word_min": single_word_min_mentions,
            "phrase_min": phrase_min_mentions,
        },
    ).fetchall()

    results = []
    for row in rows:
        recent = row["recent_articles"]
        previous = row["previous_articles"]
        change_pct = round((recent - previous) / previous * 100, 1) if previous else None
        score = round(
            row["source_count"] * 3 + recent + (row["mean_confidence"] or 0)
            + max(0, recent - previous) * 0.5,
            2,
        )
        results.append({**dict(row), "change_pct": change_pct, "score": score})
    return results
