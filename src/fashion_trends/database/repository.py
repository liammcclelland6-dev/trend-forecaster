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
    before = connection.total_changes
    with connection:
        for item in items:
            signal = item.signal
            connection.execute(
                "INSERT INTO concepts(concept_key, canonical_label) VALUES (?, ?) "
                "ON CONFLICT(concept_key) DO UPDATE SET canonical_label=excluded.canonical_label",
                (item.concept_key, item.canonical_label),
            )
            connection.execute(
                """INSERT OR IGNORE INTO observations
                (source, source_item_id, concept_key, observed_on, raw_text, url, confidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (signal.source, signal.source_item_id, item.concept_key,
                 signal.observed_on.isoformat(), signal.text, signal.url,
                 signal.confidence, signal.metadata),
            )
    return connection.total_changes - before
