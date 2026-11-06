import json
from pathlib import Path

from trackrecord.normalizer import TrainEventNormalizer


def test_service_details_payload_normalizes_stop_times() -> None:
    payload = json.loads(Path("fixtures/service_details_sample.json").read_text())

    events = TrainEventNormalizer().from_service_details(
        payload, observed_at="2026-11-05T23:00:00+00:00"
    )

    assert len(events) == 24
    assert events[0].service_id == "202610126717911"
    assert events[0].operator == "LM"
    assert events[0].station_code == "MKC"
    assert events[0].event_type == "departure"
    assert events[0].scheduled_time == "0630"
    assert events[0].actual_time == "0629"
    assert events[0].delay_minutes == -1
    assert events[0].cancelled is False

    final_stop = events[-1]
    assert final_stop.station_code == "EUS"
    assert final_stop.event_type == "arrival"
    assert final_stop.scheduled_time == "0737"
    assert final_stop.actual_time == "0746"
    assert final_stop.delay_minutes == 9


def test_service_details_uses_departure_when_arrival_is_missing() -> None:
    payload = {
        "serviceAttributesDetails": {
            "rid": "rid-1",
            "toc_code": "LM",
            "locations": [
                {
                    "location": "HML",
                    "gbtt_ptd": "0703",
                    "gbtt_pta": "",
                    "actual_td": "0707",
                    "actual_ta": "",
                    "late_canc_reason": "",
                }
            ],
        }
    }

    event = TrainEventNormalizer().from_service_details(
        payload, observed_at="now"
    )[0]

    assert event.scheduled_time == "0703"
    assert event.actual_time == "0707"
    assert event.delay_minutes == 4
    assert event.event_type == "departure"
