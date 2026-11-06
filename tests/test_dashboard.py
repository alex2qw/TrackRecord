from trackrecord.app import create_app


def test_dashboard_page_is_served(tmp_path) -> None:
    app = create_app(tmp_path / "dashboard.sqlite3")
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"TrackRecord" in response.data
    assert b"Choose a journey view" in response.data


def test_dashboard_assets_are_served(tmp_path) -> None:
    app = create_app(tmp_path / "dashboard.sqlite3")
    client = app.test_client()

    css = client.get("/static/dashboard.css")
    javascript = client.get("/static/dashboard.js")

    assert css.status_code == 200
    assert javascript.status_code == 200
