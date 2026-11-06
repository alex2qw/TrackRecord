from trackrecord.metrics import MetricsCalculator, delay_bands
from trackrecord.models import TrainEvent


def event(
    service_id: str,
    delay: int | None,
    *,
    actual: str | None = "0700",
    cancelled: bool = False,
    scheduled: str = "0700",
) -> TrainEvent:
    return TrainEvent(
        service_id=service_id,
        operator="LM",
        station_code="HML",
        event_type="departure",
        scheduled_time=scheduled,
        actual_time=actual,
        delay_minutes=delay,
        cancelled=cancelled,
        cancel_reason="engineering works" if cancelled else None,
        observed_at="2026-11-06T00:00:00+00:00",
    )


def test_reliability_metrics_handle_cancellations_and_missing_data() -> None:
    events = [
        event("202610126717911", -1),
        event("202610136717911", 4),
        event("202610146717911", 16),
        event("202610156717911", None, actual=None, cancelled=True),
        event("202610166717911", None, actual=None),
    ]

    metrics = MetricsCalculator().reliability(events)

    assert metrics.total_events == 5
    assert metrics.observed_events == 3
    assert metrics.cancelled_events == 1
    assert metrics.on_time_events == 1
    assert metrics.delayed_over_5_events == 1
    assert metrics.delayed_over_15_events == 1
    assert metrics.average_delay_minutes == 19 / 3
    assert metrics.median_delay_minutes == 4
    assert metrics.on_time_percentage == 33.33
    assert metrics.cancellation_percentage == 20.0
    assert metrics.coverage_percentage == 60.0


def test_delay_bands_are_explicit_and_exclude_cancellations() -> None:
    events = [
        event("202610126717911", -1),
        event("202610136717911", 3),
        event("202610146717911", 10),
        event("202610156717911", 20),
        event("202610166717911", 20, cancelled=True),
    ]

    assert delay_bands(events) == {
        "early_or_on_time": 1,
        "1_to_5_minutes": 1,
        "6_to_15_minutes": 1,
        "over_15_minutes": 1,
    }


def test_grouping_uses_service_date_and_scheduled_hour() -> None:
    events = [
        event("202610126717911", 0, scheduled="0703"),
        event("202610136717911", 10, scheduled="0815"),
    ]
    calculator = MetricsCalculator()

    assert set(calculator.group_by_weekday(events)) == {"Monday", "Tuesday"}
    assert set(calculator.group_by_hour(events)) == {7, 8}


def test_empty_metrics_are_explicitly_unavailable() -> None:
    metrics = MetricsCalculator().reliability([])

    assert metrics.total_events == 0
    assert metrics.on_time_percentage is None
    assert metrics.average_delay_minutes is None
