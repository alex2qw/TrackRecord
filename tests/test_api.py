import json
from pathlib import Path

from trackrecord.app import create_app
from trackrecord.database import TrackRecordDatabase
from trackrecord.importer import TrainEventImporter
from trackrecord.repository import TrainEventRepository


def client_with_fixture(tmp_path):
    database_path = tmp_path / "api.sqlite3"
    payload = json.loads(
        Path("fixtures/service_details_sample.json").read_text()
    )
    with TrackRecordDatabase(database_path) as database:
        TrainEventImporter(
            TrainEventRepository(database.connection)
        ).import_service_details(
            payload, observed_at="2026-11-06T00:00:00+00:00"
        )
    app = create_app(database_path)
    app.config.update(TESTING=True)
    return app.test_client(), app


def test_reliability_endpoint_returns_metrics_and_filters(tmp_path) -> None:
    client, _ = client_with_fixture(tmp_path)
    response = client.get(
        "/api/v1/reliability?station=EUS&event_type=arrival"
        "&from_date=2026-10-01&to_date=2026-10-31"
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["filters"]["station"] == "EUS"
    assert body["filters"]["from_date"] == "2026-10-01"
    assert body["metrics"]["total_events"] == 1
    assert body["metrics"]["average_delay_minutes"] == 9.0


def test_api_lists_stations_and_routes(tmp_path) -> None:
    client, _ = client_with_fixture(tmp_path)

    stations = client.get("/api/v1/stations").get_json()["stations"]
    routes = client.get("/api/v1/routes").get_json()["routes"]

    assert {"crs_code": "HML", "name": None} in stations
    assert {
        "origin_code": "MKC",
        "destination_code": "EUS",
        "operator": "LM",
    } in routes


def test_invalid_filters_return_bad_request(tmp_path) -> None:
    client, _ = client_with_fixture(tmp_path)

    response = client.get("/api/v1/reliability?event_type=stopped")
    unknown_station = client.get("/api/v1/reliability?station=XYZ")

    assert response.status_code == 400
    assert "event_type" in response.get_json()["error"]
    assert unknown_station.status_code == 400


def test_delay_and_cancellation_endpoints_are_read_only(tmp_path) -> None:
    client, _ = client_with_fixture(tmp_path)

    delays = client.get("/api/v1/delays?event_type=arrival").get_json()
    cancellations = client.get(
        "/api/v1/cancellations?event_type=arrival"
    ).get_json()

    assert sum(delays["bands"].values()) == 12
    assert cancellations["cancelled_events"] == 0


def test_grouping_endpoints_return_json(tmp_path) -> None:
    client, _ = client_with_fixture(tmp_path)

    weekday = client.get("/api/v1/reliability/by-weekday")
    hour = client.get("/api/v1/reliability/by-hour")

    assert weekday.status_code == 200
    assert "Monday" in weekday.get_json()["groups"]
    assert any(group["hour"] == 7 for group in hour.get_json()["groups"])
