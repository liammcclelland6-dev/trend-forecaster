"""Explainable daily heuristic scores."""

import sqlite3
from datetime import date


def score_day(connection: sqlite3.Connection, observed_on: date) -> list[dict[str, object]]:
    rows = connection.execute(
        """SELECT c.concept_key, c.canonical_label,
                  COUNT(DISTINCT o.source) AS source_count,
                  COUNT(*) AS observation_count,
                  GROUP_CONCAT(DISTINCT o.source) AS sources,
                  AVG(o.confidence) AS mean_confidence
           FROM observations o JOIN concepts c USING (concept_key)
           WHERE o.observed_on = ?
           GROUP BY c.concept_key, c.canonical_label
           ORDER BY (COUNT(DISTINCT o.source) * 3 + COUNT(*) + AVG(o.confidence)) DESC,
                    c.canonical_label""",
        (observed_on.isoformat(),),
    ).fetchall()
    results = []
    for row in rows:
        score = round(row["source_count"] * 3 + row["observation_count"] + row["mean_confidence"], 2)
        results.append({**dict(row), "score": score})
    return results
