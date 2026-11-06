"""Import normalized service-details data into SQLite."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
import sqlite3

from .models import TrainEvent
from .normalizer import NormalizationError, TrainEventNormalizer
from .repository import TrainEventRepository


class ImportError(RuntimeError):
    """Raised when an import cannot be completed."""


class TrainEventImporter:
    """Normalize service-details payloads and persist them atomically."""

    def __init__(
        self,
        repository: TrainEventRepository,
        normalizer: TrainEventNormalizer | None = None,
    ) -> None:
        self._repository = repository
        self._normalizer = normalizer or TrainEventNormalizer()

    def import_service_details(
        self,
        payload: Mapping[str, Any],
        *,
        observed_at: str | None = None,
        source: str = "hsp_service_details",
        journey_leg: str | None = None,
    ) -> int:
        """Persist a service-details payload and return inserted-record count."""
        timestamp = observed_at or datetime.now(timezone.utc).isoformat()
        run_id = self._repository.start_collection(source, timestamp)
        try:
            events: list[TrainEvent] = self._normalizer.from_service_details(
                payload, observed_at=timestamp
            )
            saved = self._repository.save_events(events, journey_leg=journey_leg)
            self._repository.finish_collection(
                run_id,
                status="succeeded",
                records_received=len(events),
                records_saved=saved,
            )
            return saved
        except NormalizationError as exc:
            self._repository.finish_collection(
                run_id,
                status="failed",
                records_received=0,
                records_saved=0,
                error_message=str(exc),
            )
            raise ImportError("service-details import failed") from exc
        except sqlite3.Error as exc:
            self._repository.finish_collection(
                run_id,
                status="failed",
                records_received=0,
                records_saved=0,
                error_message=str(exc),
            )
            raise ImportError("database write failed") from exc
