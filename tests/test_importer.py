import json
from pathlib import Path

from trackrecord.database import TrackRecordDatabase
from trackrecord.importer import TrainEventImporter
from trackrecord.repository import TrainEventRepository


def test_importer_saves_service_details_fixture(tmp_path) -> None:
    payload = json.loads(
        Path("fixtures/service_details_sample.json").read_text()
    )
    with TrackRecordDatabase(tmp_path / "test.sqlite3") as database:
        repository = TrainEventRepository(database.connection)
        importer = TrainEventImporter(repository)

        assert importer.import_service_details(
            payload, observed_at="2026-11-06T00:00:00+00:00"
        ) == 24
        assert repository.count_events() == 24
        run = repository.list_collection_runs()[0]
        assert run["status"] == "succeeded"
        assert run["records_received"] == 24
        assert run["records_saved"] == 24

        assert importer.import_service_details(
            payload, observed_at="2026-11-06T00:00:00+00:00"
        ) == 0
