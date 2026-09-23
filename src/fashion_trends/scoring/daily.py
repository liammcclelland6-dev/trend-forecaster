"""Explainable daily heuristic scores."""

import sqlite3
from datetime import date


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
