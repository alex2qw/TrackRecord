"""HTTP application entry point for TrackRecord."""

from datetime import date
from pathlib import Path

from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

from .database import TrackRecordDatabase
from .filters import EventFilters, VALID_WEEKDAYS
from .metrics import MetricsCalculator, delay_bands
from .repository import TrainEventRepository
from .serialization import filters_to_dict, metrics_to_dict, row_to_event


def create_app(database_path: str | Path = "trackrecord.sqlite3") -> Flask:
    """Create the TrackRecord Flask application."""
    app = Flask(__name__)
    database = TrackRecordDatabase(database_path)
    repository = TrainEventRepository(database.connection)
    calculator = MetricsCalculator()
    allowed_query = {
        "journey_leg", "station", "operator", "event_type", "from_date", "to_date",
        "weekday", "hour",
    }

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    @app.get("/")
    def dashboard():
        return render_template("index.html")

    @app.errorhandler(Exception)
    def handle_error(error: Exception):
        if isinstance(error, HTTPException):
            return {"error": error.description}, error.code
        app.logger.exception("Unhandled API error")
        return {"error": "Internal server error"}, 500

    def parse_filters() -> EventFilters:
        unknown = set(request.args) - allowed_query
        if unknown:
            raise ValueError(f"Unknown query parameter: {sorted(unknown)[0]}")
        def optional_date(name: str) -> date | None:
            value = request.args.get(name)
            if value is None:
                return None
            try:
                return date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(f"{name} must use YYYY-MM-DD format") from exc
        from_date = optional_date("from_date")
        to_date = optional_date("to_date")
        if from_date and to_date and from_date > to_date:
            raise ValueError("from_date must not be after to_date")
        event_type = request.args.get("event_type")
        if event_type and event_type not in {"arrival", "departure"}:
            raise ValueError("event_type must be arrival or departure")
        weekday = request.args.get("weekday")
        if weekday and weekday not in VALID_WEEKDAYS:
            raise ValueError("weekday is invalid")
        hour_value = request.args.get("hour")
        hour = None
        if hour_value is not None:
            try:
                hour = int(hour_value)
            except ValueError as exc:
                raise ValueError("hour must be an integer from 0 to 23") from exc
            if not 0 <= hour <= 23:
                raise ValueError("hour must be an integer from 0 to 23")
        return EventFilters(
            journey_leg=request.args.get("journey_leg"),
            station_code=request.args.get("station"),
            operator=request.args.get("operator"),
            event_type=event_type,
            from_date=from_date,
            to_date=to_date,
            weekday=weekday,
            hour=hour,
        )

    def events_for_request():
        try:
            filters = parse_filters()
        except ValueError as exc:
            return {"error": str(exc)}, 400
        if filters.station_code and not repository.has_station(filters.station_code):
            return {"error": f"Unknown station code: {filters.station_code}"}, 400
        if filters.journey_leg and not repository.has_journey_leg(filters.journey_leg):
            return {"error": f"Unknown journey leg: {filters.journey_leg}"}, 400
        if filters.operator and not repository.has_operator(filters.operator):
            return {"error": f"Unknown operator: {filters.operator}"}, 400
        rows = repository.list_events(filters)
        return filters, [row_to_event(row) for row in rows]

    @app.get("/api/v1/stations")
    def stations():
        return {"stations": [dict(row) for row in repository.list_stations()]}

    @app.get("/api/v1/routes")
    def routes():
        return {"routes": [dict(row) for row in repository.list_routes()]}

    @app.get("/api/v1/journey-legs")
    def journey_legs():
        return {"journey_legs": repository.list_journey_legs()}

    @app.get("/api/v1/collections/latest")
    def latest_collection():
        run = repository.latest_collection_run()
        return {"collection": dict(run) if run is not None else None}

    @app.get("/api/v1/reliability")
    def reliability():
        result = events_for_request()
        if isinstance(result[0], dict):
            return result
        filters, events = result
        metrics = calculator.reliability(events)
        rows = repository.list_events(filters)
        dates = [row["scheduled_date"] for row in rows if row["scheduled_date"]]
        latest_collection = repository.latest_collection_run()
        return {
            "filters": filters_to_dict(filters),
            "metrics": metrics_to_dict(metrics),
            "metadata": {
                "data_source": "National Rail HSP",
                "sample_size": len(events),
                "last_observed_at": max(
                    (event.observed_at for event in events), default=None
                ),
                "data_period": {
                    "from": min(dates) if dates else None,
                    "to": max(dates) if dates else None,
                },
                "latest_collection": (
                    dict(latest_collection) if latest_collection else None
                ),
            },
        }

    @app.get("/api/v1/delays")
    def delays():
        result = events_for_request()
        if isinstance(result[0], dict):
            return result
        filters, events = result
        return {
            "filters": filters_to_dict(filters),
            "bands": delay_bands(events),
            "total_observed_events": sum(
                event.delay_minutes is not None and not event.cancelled
                for event in events
            ),
        }

    @app.get("/api/v1/cancellations")
    def cancellations():
        result = events_for_request()
        if isinstance(result[0], dict):
            return result
        filters, events = result
        metrics = calculator.reliability(events)
        reasons: dict[str, int] = {}
        for event in events:
            if event.cancelled:
                reason = event.cancel_reason or "Unknown"
                reasons[reason] = reasons.get(reason, 0) + 1
        return {
            "filters": filters_to_dict(filters),
            "total_events": metrics.total_events,
            "cancelled_events": metrics.cancelled_events,
            "cancellation_percentage": metrics.cancellation_percentage,
            "reasons": [
                {"reason": reason, "count": count}
                for reason, count in sorted(reasons.items())
            ],
        }

    @app.get("/api/v1/reliability/by-weekday")
    def reliability_by_weekday():
        result = events_for_request()
        if isinstance(result[0], dict):
            return result
        _, events = result
        return {
            "groups": {
                day: metrics_to_dict(metrics)
                for day, metrics in calculator.group_by_weekday(events).items()
            }
        }

    @app.get("/api/v1/reliability/by-hour")
    def reliability_by_hour():
        result = events_for_request()
        if isinstance(result[0], dict):
            return result
        _, events = result
        return {
            "groups": [
                {"hour": hour, "metrics": metrics_to_dict(metrics)}
                for hour, metrics in calculator.group_by_hour(events).items()
            ]
        }

    @app.get("/api/v1/reliability/by-date")
    def reliability_by_date():
        result = events_for_request()
        if isinstance(result[0], dict):
            return result
        _, events = result
        return {
            "groups": [
                {"date": service_date, "metrics": metrics_to_dict(metrics)}
                for service_date, metrics in calculator.group_by_date(events).items()
            ]
        }

    return app
