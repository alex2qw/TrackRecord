# TrackRecord

**UK train reliability dashboard**

TrackRecord analyses public transport data to show delays, cancellations, and reliability patterns for train routes and stations. It started with a personal question: how reliable is the journey to university?

## Project status

This repository is at the foundation stage. The first release will focus on one route or operator, a small set of stations, historical data collection, and transparent reliability metrics.

## Planned features

- Scheduled collection from one permitted public data source
- Historical storage in SQLite
- Delay, cancellation, and reliability metrics
- Flask API for route and station data
- Dashboard views for trends and comparisons
- Validation, retries, rate limits, structured logging, and tests
- Docker-based local development and deployment

## Principles

- Use permitted public data and respect provider terms and rate limits.
- Separate observed data from calculated metrics.
- Show data coverage and uncertainty instead of implying false precision.
- Keep personal travel information out of the system.
- Prefer explainable calculations over unsupported predictions.

## Planned stack

Python, Flask, SQLite, Pandas, pytest, Docker, and GitHub Actions. The frontend technology will be selected after the data and API contracts are stable.

## Development

The application scaffold requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
flask --app trackrecord.app run --debug
```

### Phase 2: HSP normalization

The HSP client reads `NRE_USERNAME` and `NRE_PASSWORD` from `.env`. To fetch
the saved sample RID and create a local detail fixture:

```bash
python fetch_service_details.py
```

The client uses `HSP_SERVICE_DETAILS_URL` when set. Otherwise it derives the
service-details URL from `HSP_METRICS_URL`. Credentials are never written to
fixtures or logs.

To import the saved detail fixture into SQLite:

```bash
python import_service.py --database trackrecord.sqlite3
```

The importer is idempotent: importing the same service twice does not create
duplicate stop events. The database file is ignored by Git.

The persistence model keeps `services`, `stations`, `service_stops`, and
`collection_runs` separate. Arrival and departure observations are stored as
different stop events so reliability metrics can distinguish an on-time
departure from an on-time arrival.

## Roadmap

1. Select and document a permitted data source.
2. Define the data model and reliability calculations.
3. Implement an importer with validation and fixtures.
4. Expose read-only API endpoints.
5. Build the dashboard and deploy a small demo.

## License

MIT. See [LICENSE](LICENSE).
