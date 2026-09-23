"""SQLite schema and persistence helpers."""

import sqlite3
from pathlib import Path

from fashion_trends.models import NormalizedSignal

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS concepts (
    concept_key TEXT PRIMARY KEY,
    canonical_label TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    concept_key TEXT NOT NULL REFERENCES concepts(concept_key),
    observed_on TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    url TEXT,
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    metadata TEXT,
    UNIQUE(source, source_item_id, concept_key, observed_on)
);
CREATE INDEX IF NOT EXISTS idx_observations_date_concept
    ON observations(observed_on, concept_key);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def save_observations(connection: sqlite3.Connection, items: list[NormalizedSignal]) -> int:
    grouped: dict[tuple[str, str, str], list[NormalizedSignal]] = {}
    for item in items:
        signal = item.signal
        identity = (signal.source, signal.source_item_id, signal.observed_on.isoformat())
        grouped.setdefault(identity, []).append(item)

    inserted_observations = 0
    with connection:
        for (source, source_item_id, observed_on), normalized_items in grouped.items():
            concept_keys = sorted({item.concept_key for item in normalized_items})
            placeholders = ", ".join("?" for _ in concept_keys)
            connection.execute(
                f"DELETE FROM observations WHERE source = ? AND source_item_id = ? "
                f"AND observed_on = ? AND concept_key NOT IN ({placeholders})",
                (source, source_item_id, observed_on, *concept_keys),
            )

            for item in normalized_items:
                signal = item.signal
                observation_date = signal.observed_on.isoformat()
                connection.execute(
                    "INSERT INTO concepts(concept_key, canonical_label) VALUES (?, ?) "
                    "ON CONFLICT(concept_key) DO UPDATE SET canonical_label=excluded.canonical_label",
                    (item.concept_key, item.canonical_label),
                )
                exists = connection.execute(
                    "SELECT 1 FROM observations WHERE source = ? AND source_item_id = ? "
                    "AND concept_key = ? AND observed_on = ?",
                    (signal.source, signal.source_item_id, item.concept_key, observation_date),
                ).fetchone()
                cursor = connection.execute(
                    """INSERT INTO observations
                    (source, source_item_id, concept_key, observed_on, raw_text, url, confidence, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source, source_item_id, concept_key, observed_on) DO UPDATE SET
                        raw_text=excluded.raw_text,
                        url=excluded.url,
                        confidence=excluded.confidence,
                        metadata=excluded.metadata""",
                    (signal.source, signal.source_item_id, item.concept_key,
                     observation_date, signal.text, signal.url,
                     signal.confidence, signal.metadata),
                )
                if not exists:
                    inserted_observations += cursor.rowcount
    return inserted_observations
