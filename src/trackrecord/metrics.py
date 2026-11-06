"""Historical reliability metrics for normalized train events."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from statistics import median

from .models import TrainEvent


@dataclass(frozen=True, slots=True)
class ReliabilityMetrics:
    """Descriptive metrics for one filtered set of train events."""

    total_events: int
    observed_events: int
    cancelled_events: int
    on_time_events: int
    delayed_over_5_events: int
    delayed_over_15_events: int
    average_delay_minutes: float | None
    median_delay_minutes: float | None
    on_time_percentage: float | None
    cancellation_percentage: float | None
    coverage_percentage: float | None


class MetricsCalculator:
    """Calculate historical metrics without accessing a database or API."""

    def __init__(self, *, on_time_threshold_minutes: int = 1) -> None:
        if on_time_threshold_minutes < 0:
            raise ValueError("on_time_threshold_minutes must not be negative")
        self._on_time_threshold = on_time_threshold_minutes

    def reliability(self, events: Iterable[TrainEvent]) -> ReliabilityMetrics:
        """Calculate metrics for events, excluding unavailable delays."""
        values = list(events)
        observed = [event for event in values if event.actual_time is not None]
        delays = [
            event.delay_minutes
            for event in observed
            if event.delay_minutes is not None and not event.cancelled
        ]
        cancelled = [event for event in values if event.cancelled]
        on_time = [
            delay for delay in delays if delay <= self._on_time_threshold
        ]
        delayed_over_5 = [delay for delay in delays if delay > 5]
        delayed_over_15 = [delay for delay in delays if delay > 15]
        total = len(values)

        return ReliabilityMetrics(
            total_events=total,
            observed_events=len(observed),
            cancelled_events=len(cancelled),
            on_time_events=len(on_time),
            delayed_over_5_events=len(delayed_over_5),
            delayed_over_15_events=len(delayed_over_15),
            average_delay_minutes=(
                sum(delays) / len(delays) if delays else None
            ),
            median_delay_minutes=median(delays) if delays else None,
            on_time_percentage=_percentage(len(on_time), len(delays)),
            cancellation_percentage=_percentage(len(cancelled), total),
            coverage_percentage=_percentage(len(observed), total),
        )

    def group_by_weekday(
        self, events: Iterable[TrainEvent]
    ) -> dict[str, ReliabilityMetrics]:
        """Calculate metrics grouped by the service date's weekday."""
        groups: defaultdict[str, list[TrainEvent]] = defaultdict(list)
        for event in events:
            service_date = _service_date(event.service_id)
            if service_date is not None:
                groups[service_date.strftime("%A")].append(event)
        return {
            weekday: self.reliability(group)
            for weekday, group in sorted(groups.items())
        }

    def group_by_hour(
        self, events: Iterable[TrainEvent]
    ) -> dict[int, ReliabilityMetrics]:
        """Calculate metrics grouped by scheduled local hour."""
        groups: defaultdict[int, list[TrainEvent]] = defaultdict(list)
        for event in events:
            hour = _scheduled_hour(event.scheduled_time)
            if hour is not None:
                groups[hour].append(event)
        return {
            hour: self.reliability(groups[hour])
            for hour in sorted(groups)
        }


def delay_bands(
    events: Iterable[TrainEvent],
) -> dict[str, int]:
    """Count observed, non-cancelled events in useful delay bands."""
    bands = Counter(
        _delay_band(event.delay_minutes)
        for event in events
        if event.delay_minutes is not None and not event.cancelled
    )
    return {
        "early_or_on_time": bands["early_or_on_time"],
        "1_to_5_minutes": bands["1_to_5_minutes"],
        "6_to_15_minutes": bands["6_to_15_minutes"],
        "over_15_minutes": bands["over_15_minutes"],
    }


def _percentage(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator * 100 / denominator, 2)


def _delay_band(delay: int) -> str:
    if delay <= 0:
        return "early_or_on_time"
    if delay <= 5:
        return "1_to_5_minutes"
    if delay <= 15:
        return "6_to_15_minutes"
    return "over_15_minutes"


def _service_date(service_id: str) -> date | None:
    value = service_id[:8]
    if len(value) != 8 or not value.isdigit():
        return None
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:]))
    except ValueError:
        return None


def _scheduled_hour(scheduled_time: str) -> int | None:
    if len(scheduled_time) != 4 or not scheduled_time.isdigit():
        return None
    hour = int(scheduled_time[:2])
    minute = int(scheduled_time[2:])
    if hour > 23 or minute > 59:
        return None
    return hour
