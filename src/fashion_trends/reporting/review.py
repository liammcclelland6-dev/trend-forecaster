"""CSV export for human review of collected phrase candidates."""

import csv
import json
import sqlite3
from pathlib import Path

from fashion_trends.processing.vocabulary import load_vocabulary, suggest_categories


def export_phrase_review(
    connection: sqlite3.Connection,
    output_path: str | Path,
    vocabulary_path: str | Path,
    source: str = "rss",
    limit: int = 200,
) -> int:
    """Export frequent phrase/source pairs with evidence and blank review columns."""
    if source not in {"rss", "sample", "all"}:
        raise ValueError(f"Unsupported review source: {source}")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    source_filter = {
        "rss": "o.source != 'sample'",
        "sample": "o.source = 'sample'",
        "all": "1 = 1",
    }[source]
    rows = connection.execute(
        f"""WITH counts AS (
                SELECT o.concept_key, o.source,
                       COUNT(DISTINCT o.source_item_id) AS article_count,
                       MAX(o.observed_on) AS latest_date
                FROM observations o
                WHERE {source_filter}
                GROUP BY o.concept_key, o.source
            ), ranked AS (
                SELECT o.concept_key, o.source, o.source_item_id, o.observed_on,
                       o.raw_text, o.url, o.metadata,
                       ROW_NUMBER() OVER (
                           PARTITION BY o.concept_key, o.source
                           ORDER BY o.observed_on DESC, o.source_item_id
                       ) AS row_number
                FROM observations o
                WHERE {source_filter}
            )
            SELECT c.concept_key, c.canonical_label, counts.source,
                   counts.article_count, counts.latest_date,
                   ranked.raw_text, ranked.url, ranked.metadata
            FROM counts
            JOIN concepts c USING (concept_key)
            JOIN ranked ON ranked.concept_key = counts.concept_key
                        AND ranked.source = counts.source
                        AND ranked.row_number = 1
            ORDER BY counts.article_count DESC, counts.latest_date DESC,
                     c.canonical_label COLLATE NOCASE, counts.source
            LIMIT ?""",
        (limit,),
    ).fetchall()
    vocabulary = load_vocabulary(vocabulary_path)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "phrase", "suggested_category", "matched_seed_terms", "source",
        "article_count", "latest_date", "title", "summary_excerpt", "url",
        "review_category", "reviewed_name", "related_terms", "review_notes",
    ]
    with destination.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            suggested_category, matched_terms = suggest_categories(row["canonical_label"], vocabulary)
            try:
                metadata = json.loads(row["metadata"] or "{}")
            except (TypeError, json.JSONDecodeError):
                metadata = {}
            writer.writerow({
                "phrase": row["canonical_label"],
                "suggested_category": suggested_category,
                "matched_seed_terms": matched_terms,
                "source": row["source"],
                "article_count": row["article_count"],
                "latest_date": row["latest_date"],
                "title": metadata.get("title") or row["raw_text"],
                "summary_excerpt": str(metadata.get("summary") or "")[:500],
                "url": row["url"] or "",
                "review_category": "",
                "reviewed_name": "",
                "related_terms": "",
                "review_notes": "",
            })
    return len(rows)
