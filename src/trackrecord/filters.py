"""Validated filters for historical event queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

VALID_WEEKDAYS = {
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
}


@dataclass(frozen=True, slots=True)
class EventFilters:
    journey_leg: str | None = None
    station_code: str | None = None
    operator: str | None = None
    event_type: str | None = None
    from_date: date | None = None
    to_date: date | None = None
    weekday: str | None = None
    hour: int | None = None
