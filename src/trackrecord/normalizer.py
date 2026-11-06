"""Convert National Rail HSP payloads into TrackRecord domain events."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .models import TrainEvent


class NormalizationError(ValueError):
    """Raised when a provider payload cannot be normalized."""


class TrainEventNormalizer:
    """Normalize HSP summary and service-details payloads."""

    def from_summary(
        self,
        payload: Mapping[str, Any],
        *,
        observed_at: str,
    ) -> list[TrainEvent]:
        """Create endpoint events from the serviceMetrics summary payload."""
        services = payload.get("Services")
        if not isinstance(services, Sequence) or isinstance(services, (str, bytes)):
            raise NormalizationError("summary payload has no Services list")

        events: list[TrainEvent] = []
        for service in services:
            if not isinstance(service, Mapping):
                raise NormalizationError("summary service must be an object")
            attributes = service.get("serviceAttributesMetrics")
            if not isinstance(attributes, Mapping):
                raise NormalizationError("summary service has no attributes")

            rids = attributes.get("rids")
            if not isinstance(rids, Sequence) or isinstance(rids, (str, bytes)):
                raise NormalizationError("summary service has no rids list")

            operator = self._required_text(attributes, "toc_code")
            origin = self._required_text(attributes, "origin_location")
            destination = self._required_text(attributes, "destination_location")
            scheduled_departure = self._time_text(attributes, "gbtt_ptd")
            scheduled_arrival = self._time_text(attributes, "gbtt_pta")

            for rid in rids:
                service_id = str(rid).strip()
                if not service_id:
                    raise NormalizationError("summary contains an empty RID")
                events.extend(
                    (
                        TrainEvent(
                            service_id=service_id,
                            operator=operator,
                            station_code=origin,
                            event_type="departure",
                            scheduled_time=scheduled_departure,
                            actual_time=None,
                            delay_minutes=None,
                            cancelled=False,
                            cancel_reason=None,
                            observed_at=observed_at,
                        ),
                        TrainEvent(
                            service_id=service_id,
                            operator=operator,
                            station_code=destination,
                            event_type="arrival",
                            scheduled_time=scheduled_arrival,
                            actual_time=None,
                            delay_minutes=None,
                            cancelled=False,
                            cancel_reason=None,
                            observed_at=observed_at,
                        ),
                    )
                )
        return events

    def from_service_details(
        self,
        payload: Mapping[str, Any],
        *,
        observed_at: str,
    ) -> list[TrainEvent]:
        """Create events from a serviceDetails payload.

        HSP has changed wrapper names between feed versions. This method accepts
        the common ``service``/``locations`` shapes and fails explicitly when
        the actual response is not one of them.
        """
        service = self._first_mapping(
            payload,
            ("service", "Service", "serviceDetails", "serviceAttributesDetails"),
        )
        locations = self._first_sequence(
            service or payload,
            ("locations", "Locations", "serviceLocations", "ServiceLocations"),
        )
        if locations is None:
            raise NormalizationError(
                "serviceDetails payload has no supported locations list"
            )

        service_id = self._first_text(
            service or payload, ("rid", "RID", "service_id", "serviceId")
        )
        operator = (
            self._first_text(
                service or payload, ("toc_code", "tocCode", "operator", "operatorCode")
            )
            or ""
        )
        if not service_id:
            raise NormalizationError("serviceDetails payload has no service ID")

        events: list[TrainEvent] = []
        for location in locations:
            if not isinstance(location, Mapping):
                raise NormalizationError("service location must be an object")
            station_code = self._first_text(
                location,
                ("location", "location_code", "locationCode", "crs", "crsCode"),
            )
            cancelled = self._optional_bool(
                location, ("cancelled", "canceled", "isCancelled")
            )
            cancel_reason = self._first_text(
                location,
                ("cancel_reason", "cancelReason", "reason", "late_canc_reason"),
            )
            # HSP uses late_canc_reason for both late-running and cancelled
            # services. A reason alone does not mean cancellation: this sample
            # contains operated services with a reason code. Treat it as a
            # cancellation reason only when no actual time was reported.
            cancelled = cancelled or (
                not self._first_text(location, ("actual_ta", "actual_td"))
                and cancel_reason is not None
            )
            if not cancelled:
                cancel_reason = None
            if not station_code:
                raise NormalizationError("service location lacks station code")

            for event_type, scheduled_key, actual_key in (
                ("arrival", "gbtt_pta", "actual_ta"),
                ("departure", "gbtt_ptd", "actual_td"),
            ):
                scheduled = self._first_text(location, (scheduled_key,))
                if scheduled is None:
                    continue
                actual = self._first_text(location, (actual_key,))
                delay = self._optional_int(
                    location,
                    (f"{event_type}_delay_minutes", "delay_minutes", "delay"),
                )
                if delay is None and actual is not None:
                    delay = self._calculate_delay(scheduled, actual)
                events.append(
                    TrainEvent(
                        service_id=service_id,
                        operator=operator,
                        station_code=station_code,
                        event_type=event_type,
                        scheduled_time=scheduled,
                        actual_time=actual,
                        delay_minutes=delay,
                        cancelled=cancelled,
                        cancel_reason=cancel_reason,
                        observed_at=observed_at,
                    )
                )
        return events

    @staticmethod
    def _required_text(mapping: Mapping[str, Any], key: str) -> str:
        value = mapping.get(key)
        if value is None or not str(value).strip():
            raise NormalizationError(f"summary field {key!r} is missing")
        return str(value).strip()

    @staticmethod
    def _time_text(mapping: Mapping[str, Any], key: str) -> str:
        return TrainEventNormalizer._required_text(mapping, key)

    @staticmethod
    def _first_text(mapping: Mapping[str, Any], keys: Sequence[str]) -> str | None:
        for key in keys:
            value = mapping.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    @staticmethod
    def _first_mapping(
        mapping: Mapping[str, Any], keys: Sequence[str]
    ) -> Mapping[str, Any] | None:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, Mapping):
                return value
        return None

    @staticmethod
    def _first_sequence(
        mapping: Mapping[str, Any], keys: Sequence[str]
    ) -> Sequence[Any] | None:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                return value
        return None

    @staticmethod
    def _optional_int(mapping: Mapping[str, Any], keys: Sequence[str]) -> int | None:
        value = TrainEventNormalizer._first_text(mapping, keys)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError as exc:
            raise NormalizationError("delay value is not an integer") from exc

    @staticmethod
    def _optional_bool(mapping: Mapping[str, Any], keys: Sequence[str]) -> bool:
        value = TrainEventNormalizer._first_text(mapping, keys)
        if value is None:
            return False
        if value.lower() in {"true", "1", "yes"}:
            return True
        if value.lower() in {"false", "0", "no"}:
            return False
        raise NormalizationError("cancelled value is not a boolean")

    @staticmethod
    def _calculate_delay(scheduled: str, actual: str) -> int | None:
        """Calculate minutes late for HSP's HHMM time values."""
        try:
            scheduled_minutes = TrainEventNormalizer._hhmm_to_minutes(scheduled)
            actual_minutes = TrainEventNormalizer._hhmm_to_minutes(actual)
        except ValueError:
            return None

        delay = actual_minutes - scheduled_minutes
        if delay < -12 * 60:
            delay += 24 * 60
        return delay

    @staticmethod
    def _hhmm_to_minutes(value: str) -> int:
        if len(value) != 4 or not value.isdigit():
            raise ValueError("expected HHMM")
        hours, minutes = int(value[:2]), int(value[2:])
        if hours > 23 or minutes > 59:
            raise ValueError("invalid HHMM")
        return hours * 60 + minutes
