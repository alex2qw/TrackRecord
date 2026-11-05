"""HTTP application entry point for TrackRecord."""

from flask import Flask


def create_app() -> Flask:
    """Create the TrackRecord Flask application."""
    app = Flask(__name__)

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    return app
