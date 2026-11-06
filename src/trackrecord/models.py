"""Domain models used by TrackRecord."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class TrainEvent:
    """A normalized observation of a train at one station."""

    service_id: str
    operator: str
    station_code: str
    event_type: Literal["arrival", "departure"]
    scheduled_time: str
    actual_time: str | None
    delay_minutes: int | None
    cancelled: bool
    cancel_reason: str | None
    observed_at: str
