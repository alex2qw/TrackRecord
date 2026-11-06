"""Explicit JSON serialization for API responses."""

from .metrics import ReliabilityMetrics
from .filters import EventFilters


def metrics_to_dict(metrics: ReliabilityMetrics) -> dict[str, object]:
    return {
        "total_events": metrics.total_events,
        "observed_events": metrics.observed_events,
        "cancelled_events": metrics.cancelled_events,
        "on_time_events": metrics.on_time_events,
        "delayed_over_5_events": metrics.delayed_over_5_events,
        "delayed_over_15_events": metrics.delayed_over_15_events,
        "average_delay_minutes": metrics.average_delay_minutes,
        "median_delay_minutes": metrics.median_delay_minutes,
        "on_time_percentage": metrics.on_time_percentage,
        "cancellation_percentage": metrics.cancellation_percentage,
        "coverage_percentage": metrics.coverage_percentage,
    }


def filters_to_dict(filters: EventFilters) -> dict[str, object]:
    result = {
        "station": filters.station_code,
        "operator": filters.operator,
        "event_type": filters.event_type,
        "from_date": filters.from_date.isoformat() if filters.from_date else None,
        "to_date": filters.to_date.isoformat() if filters.to_date else None,
        "weekday": filters.weekday,
        "hour": filters.hour,
    }
    return result


def row_to_event(row: object):
    from .models import TrainEvent

    return TrainEvent(
        service_id=row["service_id"],
        operator=row["operator"],
        station_code=row["station_code"],
        event_type=row["event_type"],
        scheduled_time=row["scheduled_time"],
        actual_time=row["actual_time"],
        delay_minutes=row["delay_minutes"],
        cancelled=bool(row["cancelled"]),
        cancel_reason=row["cancel_reason"],
        observed_at=row["observed_at"],
    )
