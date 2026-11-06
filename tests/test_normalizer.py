import json
from pathlib import Path

from trackrecord.normalizer import TrainEventNormalizer


def test_summary_payload_normalizes_each_rid_at_both_endpoints() -> None:
    payload = json.loads(Path("fixtures/hsp_sample.json").read_text())

    events = TrainEventNormalizer().from_summary(
        payload, observed_at="2026-11-05T23:00:00+00:00"
    )

    assert len(events) == 48
    assert events[0].service_id == "202610126717911"
    assert events[0].station_code == "MKC"
    assert events[1].station_code == "EUS"
    assert events[0].operator == "LM"
