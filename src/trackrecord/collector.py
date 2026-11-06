"""Bounded HSP summary-to-details collection workflow."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from time import sleep
from typing import Any

from .hsp_client import HspClient, HspClientError
from .importer import ImportError, TrainEventImporter
from .normalizer import TrainEventNormalizer


class HspCollector:
    """Fetch a summary, then import a bounded number of service details."""

    def __init__(
        self,
        client: HspClient,
        importer: TrainEventImporter,
        *,
        pause_seconds: float = 0.0,
        journey_leg: str | None = None,
    ) -> None:
        if pause_seconds < 0:
            raise ValueError("pause_seconds must not be negative")
        self._client = client
        self._importer = importer
        self._normalizer = TrainEventNormalizer()
        self._pause_seconds = pause_seconds
        self._journey_leg = journey_leg

    def collect_summary(
        self,
        summary: Mapping[str, Any],
        *,
        max_services: int,
        observed_at: str | None = None,
    ) -> dict[str, int]:
        """Import up to ``max_services`` unique RIDs from a summary."""
        if max_services < 1:
            raise ValueError("max_services must be positive")
        timestamp = observed_at or datetime.now(timezone.utc).isoformat()
        summary_events = self._normalizer.from_summary(
            summary, observed_at=timestamp
        )
        rids = list(dict.fromkeys(event.service_id for event in summary_events))
        selected = rids[:max_services]
        saved = 0
        failed = 0
        for rid in selected:
            try:
                details = self._client.get_service_details(rid)
                saved += self._importer.import_service_details(
                    details, observed_at=timestamp, journey_leg=self._journey_leg
                )
            except (HspClientError, ImportError):
                failed += 1
            if self._pause_seconds:
                sleep(self._pause_seconds)
        return {
            "summary_services": len(rids),
            "services_requested": len(selected),
            "services_failed": failed,
            "events_saved": saved,
        }
