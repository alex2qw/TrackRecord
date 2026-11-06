"""SQLite database setup for TrackRecord."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS stations (
    crs_code TEXT PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS services (
    provider_service_id TEXT PRIMARY KEY,
    operator TEXT NOT NULL,
    scheduled_date TEXT,
    origin_code TEXT,
    destination_code TEXT,
    journey_leg TEXT
);

CREATE TABLE IF NOT EXISTS service_stops (
    id INTEGER PRIMARY KEY,
    service_id TEXT NOT NULL REFERENCES services(provider_service_id),
    station_code TEXT NOT NULL REFERENCES stations(crs_code),
    event_type TEXT NOT NULL CHECK (event_type IN ('arrival', 'departure')),
    scheduled_time TEXT NOT NULL,
    actual_time TEXT,
    delay_minutes INTEGER,
    cancelled INTEGER NOT NULL CHECK (cancelled IN (0, 1)),
    cancel_reason TEXT,
    observed_at TEXT NOT NULL,
    UNIQUE (service_id, station_code, event_type, scheduled_time)
);

CREATE TABLE IF NOT EXISTS collection_runs (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    journey_leg TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    records_received INTEGER NOT NULL DEFAULT 0,
    records_saved INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    error_message TEXT
);
"""


class TrackRecordDatabase:
    """Own a SQLite connection and initialize the TrackRecord schema."""

    def __init__(self, path: str | Path = "trackrecord.sqlite3") -> None:
        self.path = Path(path)
        # Flask may serve requests on a different worker thread from the one
        # that created the application and its SQLite connection.
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(SCHEMA)
        self._add_column_if_missing("services", "origin_code", "TEXT")
        self._add_column_if_missing("services", "destination_code", "TEXT")
        self._add_column_if_missing("services", "journey_leg", "TEXT")
        self._add_column_if_missing("collection_runs", "journey_leg", "TEXT")
        self._connection.commit()

    def _add_column_if_missing(self, table: str, column: str, column_type: str) -> None:
        columns = {
            row["name"]
            for row in self._connection.execute(f"PRAGMA table_info({table})")
        }
        if column not in columns:
            self._connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"
            )

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> TrackRecordDatabase:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
