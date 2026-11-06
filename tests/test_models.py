from trackrecord.models import TrainEvent


def test_train_event_is_immutable_and_typed() -> None:
    event = TrainEvent(
        service_id="202610126717911",
        operator="LM",
        station_code="EUS",
        event_type="arrival",
        scheduled_time="2026-10-12T07:37:00+01:00",
        actual_time=None,
        delay_minutes=None,
        cancelled=False,
        cancel_reason=None,
        observed_at="2026-11-05T23:00:00+00:00",
    )

    assert event.service_id == "202610126717911"
    assert event.cancelled is False
