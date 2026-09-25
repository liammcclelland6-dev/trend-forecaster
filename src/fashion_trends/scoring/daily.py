"""Explainable phrase evidence and temporal trend scores."""

import sqlite3
from collections import defaultdict
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
    results.sort(
        key=lambda item: (
            -item["score"],
            -item["recent_articles"],
            -item["source_count"],
            item["canonical_label"],
        )
    )
    return results


def score_semantic_window(
    connection: sqlite3.Connection,
    through_date: date,
    window_days: int = 7,
    source: str = "rss",
    min_mentions: int | None = None,
    similarity_threshold: float = 0.58,
) -> list[dict[str, object]]:
    """Group related phrase mentions, then score distinct article evidence."""
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
        min_mentions = 2 if source == "rss" else 1
    if min_mentions < 1:
        raise ValueError("min_mentions must be at least 1")

    recent_start = through_date - timedelta(days=window_days - 1)
    previous_end = recent_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=window_days - 1)
    rows = connection.execute(
        f"""SELECT o.concept_key, c.canonical_label, o.source, o.source_item_id,
                  o.observed_on, o.confidence
           FROM observations o JOIN concepts c USING (concept_key)
           WHERE o.observed_on >= ? AND o.observed_on <= ? AND {source_filters[source]}
           ORDER BY o.concept_key, o.observed_on""",
        (previous_start.isoformat(), through_date.isoformat()),
    ).fetchall()
    if not rows:
        return []

    from fashion_trends.processing.semantic import cluster_phrases

    clusters = cluster_phrases(
        (row["concept_key"] for row in rows),
        similarity_threshold,
    )
    grouped: dict[str, dict[str, object]] = {}
    recent_start_text = recent_start.isoformat()
    through_date_text = through_date.isoformat()
    for row in rows:
        phrase_key = row["concept_key"]
        members = clusters[phrase_key]
        cluster_id = members[0]
        stats = grouped.setdefault(
            cluster_id,
            {
                "members": set(),
                "labels": {},
                "recent_articles": set(),
                "previous_articles": set(),
                "recent_sources": set(),
                "recent_confidence": {},
                "member_recent_articles": defaultdict(set),
                "member_previous_articles": defaultdict(set),
            },
        )
        stats["members"].add(phrase_key)
        stats["labels"][phrase_key] = row["canonical_label"]
        article_id = (row["source"], row["source_item_id"])
        if recent_start_text <= row["observed_on"] <= through_date_text:
            stats["recent_articles"].add(article_id)
            stats["recent_sources"].add(row["source"])
            stats["recent_confidence"][article_id] = row["confidence"]
            stats["member_recent_articles"][phrase_key].add(article_id)
        else:
            stats["previous_articles"].add(article_id)
            stats["member_previous_articles"][phrase_key].add(article_id)

    results = []
    for stats in grouped.values():
        recent_count = len(stats["recent_articles"])
        previous_count = len(stats["previous_articles"])
        if recent_count < min_mentions:
            continue
        members = sorted(stats["members"])
        labels = stats["labels"]
        display_key = max(
            members,
            key=lambda phrase: (
                len(stats["member_recent_articles"][phrase]),
                len(stats["member_previous_articles"][phrase]),
                labels[phrase].casefold(),
            ),
        )
        source_names = sorted(stats["recent_sources"])
        source_count = len(source_names)
        confidence_values = list(stats["recent_confidence"].values())
        mean_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0
        change_pct = round((recent_count - previous_count) / previous_count * 100, 1) if previous_count else None
        score = round(
            source_count * 3 + recent_count + mean_confidence
            + max(0, recent_count - previous_count) * 0.5,
            2,
        )
        results.append({
            "canonical_label": labels[display_key],
            "members": [labels[phrase] for phrase in members],
            "recent_articles": recent_count,
            "previous_articles": previous_count,
            "source_count": source_count,
            "sources": ",".join(source_names),
            "mean_confidence": mean_confidence,
            "change_pct": change_pct,
            "score": score,
        })

    results.sort(
        key=lambda item: (
            -item["score"],
            -item["recent_articles"],
            -item["source_count"],
            item["canonical_label"].casefold(),
        )
    )
    return results
