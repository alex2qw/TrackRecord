"""Persistence operations for normalized TrackRecord events."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime, timezone

from .filters import EventFilters
from .models import TrainEvent


class TrainEventRepository:
    """Store and retrieve normalized train events."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_events(
        self, events: Sequence[TrainEvent], *, journey_leg: str | None = None
    ) -> int:
        """Insert services, stations, and stops idempotently."""
        inserted_stops = 0
        for event in events:
            self._connection.execute(
                """
                INSERT OR IGNORE INTO services
                    (provider_service_id, operator, scheduled_date, origin_code,
                     destination_code, journey_leg)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.service_id,
                    event.operator,
                    self._service_date(event.service_id),
                    None,
                    None,
                    journey_leg,
                ),
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO stations (crs_code) VALUES (?)",
                (event.station_code,),
            )
            if journey_leg is not None:
                self._connection.execute(
                    """
                    UPDATE services
                    SET journey_leg = ?
                    WHERE provider_service_id = ?
                    """,
                    (journey_leg, event.service_id),
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
        self._update_service_routes(events)
        self._connection.commit()
        return inserted_stops

    def count_events(self) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) AS count FROM service_stops"
        ).fetchone()
        assert row is not None
        return int(row["count"])

    def list_events(self, filters: EventFilters | None = None) -> list[sqlite3.Row]:
        filters = filters or EventFilters()
        conditions: list[str] = []
        parameters: list[object] = []
        if filters.station_code:
            conditions.append("ss.station_code = ?")
            parameters.append(filters.station_code)
        if filters.journey_leg:
            conditions.append("s.journey_leg = ?")
            parameters.append(filters.journey_leg)
        if filters.operator:
            conditions.append("s.operator = ?")
            parameters.append(filters.operator)
        if filters.event_type:
            conditions.append("ss.event_type = ?")
            parameters.append(filters.event_type)
        if filters.from_date:
            conditions.append("s.scheduled_date >= ?")
            parameters.append(filters.from_date.isoformat())
        if filters.to_date:
            conditions.append("s.scheduled_date <= ?")
            parameters.append(filters.to_date.isoformat())
        if filters.weekday:
            conditions.append("strftime('%w', s.scheduled_date) = ?")
            parameters.append(str(_weekday_number(filters.weekday)))
        if filters.hour is not None:
            conditions.append("CAST(substr(ss.scheduled_time, 1, 2) AS INTEGER) = ?")
            parameters.append(filters.hour)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return list(
            self._connection.execute(
                f"""
                SELECT ss.*, s.operator, s.scheduled_date
                FROM service_stops ss
                JOIN services s ON s.provider_service_id = ss.service_id
                {where}
                ORDER BY ss.id
                """,
                parameters,
            ).fetchall()
        )

    def list_stations(self) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                "SELECT crs_code, name FROM stations ORDER BY crs_code"
            ).fetchall()
        )

    def has_station(self, code: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM stations WHERE crs_code = ?", (code,)
        ).fetchone()
        return row is not None

    def has_operator(self, operator: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM services WHERE operator = ?", (operator,)
        ).fetchone()
        return row is not None

    def has_journey_leg(self, journey_leg: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM services WHERE journey_leg = ?", (journey_leg,)
        ).fetchone()
        return row is not None

    def list_journey_legs(self) -> list[str]:
        rows = self._connection.execute(
            """
            SELECT DISTINCT journey_leg
            FROM services
            WHERE journey_leg IS NOT NULL
            ORDER BY journey_leg
            """
        ).fetchall()
        return [str(row["journey_leg"]) for row in rows]

    def list_routes(self) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                """
                SELECT DISTINCT origin_code, destination_code, operator
                    , journey_leg
                FROM services
                WHERE origin_code IS NOT NULL AND destination_code IS NOT NULL
                ORDER BY journey_leg, origin_code, destination_code, operator
                """
            ).fetchall()
        )

    def _update_service_routes(self, events: Sequence[TrainEvent]) -> None:
        grouped: dict[str, list[TrainEvent]] = {}
        for event in events:
            grouped.setdefault(event.service_id, []).append(event)
        for service_id, service_events in grouped.items():
            departures = [e for e in service_events if e.event_type == "departure"]
            arrivals = [e for e in service_events if e.event_type == "arrival"]
            origin = departures[0].station_code if departures else None
            destination = arrivals[-1].station_code if arrivals else None
            self._connection.execute(
                """
                UPDATE services
                SET origin_code = COALESCE(?, origin_code),
                    destination_code = COALESCE(?, destination_code)
                WHERE provider_service_id = ?
                """,
                (origin, destination, service_id),
            )

    def start_collection(
        self,
        source: str,
        started_at: str | None = None,
        journey_leg: str | None = None,
    ) -> int:
        timestamp = started_at or datetime.now(timezone.utc).isoformat()
        cursor = self._connection.execute(
            """
            INSERT INTO collection_runs (source, journey_leg, started_at, status)
            VALUES (?, ?, ?, 'running')
            """,
            (source, journey_leg, timestamp),
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

    def latest_collection_run(
        self, journey_leg: str | None = None
    ) -> sqlite3.Row | None:
        if journey_leg is None:
            return self._connection.execute(
                "SELECT * FROM collection_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return self._connection.execute(
            """
            SELECT * FROM collection_runs
            WHERE journey_leg = ?
            ORDER BY id DESC LIMIT 1
            """,
            (journey_leg,),
        ).fetchone()

    def data_quality(self, filters: EventFilters | None = None) -> dict[str, int]:
        """Return transparent quality counts for a filtered event set."""
        filters = filters or EventFilters()
        rows = self.list_events(filters)
        service_ids = {row["service_id"] for row in rows}
        duplicate_row = self._connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM (
                SELECT service_id, station_code, event_type, scheduled_time
                FROM service_stops
                GROUP BY service_id, station_code, event_type, scheduled_time
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()
        latest = self.latest_collection_run(filters.journey_leg)
        return {
            "events": len(rows),
            "services": len(service_ids),
            "missing_actual_times": sum(row["actual_time"] is None for row in rows),
            "cancelled_events": sum(bool(row["cancelled"]) for row in rows),
            "duplicate_events": int(duplicate_row["count"]) if duplicate_row else 0,
            "rejected_records": int(latest["records_rejected"]) if latest else 0,
        }

    @staticmethod
    def _service_date(service_id: str) -> str | None:
        candidate = service_id[:8]
        if len(candidate) == 8 and candidate.isdigit():
            return f"{candidate[:4]}-{candidate[4:6]}-{candidate[6:]}"
        return None


def _weekday_number(weekday: str) -> int:
    return [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ].index(weekday)
