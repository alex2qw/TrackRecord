import json
from pathlib import Path

from trackrecord.collector import HspCollector
from trackrecord.database import TrackRecordDatabase
from trackrecord.importer import TrainEventImporter
from trackrecord.repository import TrainEventRepository


class FakeClient:
    def __init__(self, detail_payload: dict) -> None:
        self.detail_payload = detail_payload
        self.requested: list[str] = []

    def get_service_details(self, rid: str) -> dict:
        self.requested.append(rid)
        payload = dict(self.detail_payload)
        payload["serviceAttributesDetails"] = dict(
            payload["serviceAttributesDetails"], rid=rid
        )
        return payload


def test_collector_fetches_bounded_unique_services(tmp_path) -> None:
    summary = json.loads(Path("fixtures/hsp_sample.json").read_text())
    detail = json.loads(
        Path("fixtures/service_details_sample.json").read_text()
    )
    client = FakeClient(detail)
    with TrackRecordDatabase(tmp_path / "collector.sqlite3") as database:
        repository = TrainEventRepository(database.connection)
        result = HspCollector(
            client, TrainEventImporter(repository), journey_leg="HML-EUS"
        ).collect_summary(summary, max_services=2, observed_at="now")

        assert result == {
            "summary_services": 24,
            "services_requested": 2,
            "services_failed": 0,
            "events_saved": 48,
        }
        assert len(client.requested) == 2
        assert repository.count_events() == 48
        assert repository.list_journey_legs() == ["HML-EUS"]
