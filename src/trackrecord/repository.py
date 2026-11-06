"""Persistence operations for normalized TrackRecord events."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime, timezone

from .models import TrainEvent


class TrainEventRepository:
    """Store and retrieve normalized train events."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_events(self, events: Sequence[TrainEvent]) -> int:
        """Insert services, stations, and stops idempotently."""
        inserted_stops = 0
        for event in events:
            self._connection.execute(
                """
                INSERT OR IGNORE INTO services
                    (provider_service_id, operator, scheduled_date)
                VALUES (?, ?, ?)
                """,
                (event.service_id, event.operator, self._service_date(event.service_id)),
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO stations (crs_code) VALUES (?)",
                (event.station_code,),
            )
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO service_stops (
                    service_id, station_code, event_type, scheduled_time,
                    actual_time, delay_minutes, cancelled, cancel_reason, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.service_id,
                    event.station_code,
                    event.event_type,
                    event.scheduled_time,
                    event.actual_time,
                    event.delay_minutes,
                    int(event.cancelled),
                    event.cancel_reason,
                    event.observed_at,
                ),
            )
            inserted_stops += cursor.rowcount
        self._connection.commit()
        return inserted_stops

    def count_events(self) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) AS count FROM service_stops"
        ).fetchone()
        assert row is not None
        return int(row["count"])

    def list_events(self) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                "SELECT * FROM service_stops ORDER BY id"
            ).fetchall()
        )

    def start_collection(self, source: str, started_at: str | None = None) -> int:
        timestamp = started_at or datetime.now(timezone.utc).isoformat()
        cursor = self._connection.execute(
            """
            INSERT INTO collection_runs (source, started_at, status)
            VALUES (?, ?, 'running')
            """,
            (source, timestamp),
        )
        self._connection.commit()
        return int(cursor.lastrowid)

    def finish_collection(
        self,
        run_id: int,
        *,
        status: str,
        records_received: int,
        records_saved: int,
        records_rejected: int = 0,
        error_message: str | None = None,
        completed_at: str | None = None,
    ) -> None:
        if status not in {"succeeded", "failed"}:
            raise ValueError("collection status must be succeeded or failed")
        timestamp = completed_at or datetime.now(timezone.utc).isoformat()
        self._connection.execute(
            """
            UPDATE collection_runs
            SET completed_at = ?, records_received = ?, records_saved = ?,
                records_rejected = ?, status = ?, error_message = ?
            WHERE id = ?
            """,
            (
                timestamp,
                records_received,
                records_saved,
                records_rejected,
                status,
                error_message,
                run_id,
            ),
        )
        self._connection.commit()

    def list_collection_runs(self) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                "SELECT * FROM collection_runs ORDER BY id"
            ).fetchall()
        )

    @staticmethod
    def _service_date(service_id: str) -> str | None:
        candidate = service_id[:8]
        if len(candidate) == 8 and candidate.isdigit():
            return f"{candidate[:4]}-{candidate[4:6]}-{candidate[6:]}"
        return None
