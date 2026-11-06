from dataclasses import replace

from trackrecord.database import TrackRecordDatabase
from trackrecord.models import TrainEvent
from trackrecord.repository import TrainEventRepository


def make_event() -> TrainEvent:
    return TrainEvent(
        service_id="rid-1",
        operator="LM",
        station_code="HML",
        event_type="departure",
        scheduled_time="0703",
        actual_time="0707",
        delay_minutes=4,
        cancelled=False,
        cancel_reason=None,
        observed_at="2026-11-06T00:00:00+00:00",
    )


def test_save_events_is_idempotent(tmp_path) -> None:
    with TrackRecordDatabase(tmp_path / "test.sqlite3") as database:
        repository = TrainEventRepository(database.connection)

        assert repository.save_events([make_event()]) == 1
        assert repository.save_events([make_event()]) == 0
        assert repository.count_events() == 1


def test_save_events_persists_nullable_values(tmp_path) -> None:
    event = replace(make_event(), actual_time=None, delay_minutes=None)
    with TrackRecordDatabase(tmp_path / "test.sqlite3") as database:
        repository = TrainEventRepository(database.connection)
        repository.save_events([event])
        row = repository.list_events()[0]

    assert row["actual_time"] is None
    assert row["delay_minutes"] is None
