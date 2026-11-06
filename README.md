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

### Collecting a bounded historical sample

The collector first obtains a `serviceMetrics` summary, extracts unique RIDs,
then fetches service details one at a time with a configurable limit and
pause. This avoids an unbounded request burst while building the local sample.

With credentials in `.env`, collect up to 10 services for a date range:

```bash
python collect_hsp.py \
  --from-date 2026-10-12 \
  --to-date 2026-10-13 \
  --max-services 10
```

Use `--from-loc`, `--to-loc`, and `--journey-leg` to collect another leg,
for example `--from-loc KGX --to-loc CBG --journey-leg KGX-CBG`.

To develop without requesting a new summary, reuse the saved summary fixture:

```bash
python collect_hsp.py \
  --summary-fixture fixtures/hsp_sample.json \
  --max-services 2
```

Both commands still request service details, so credentials and a working
`HSP_SERVICE_DETAILS_URL` (or the documented default) are required. The
collector records each imported service and safely ignores duplicate events.

### Phase 4: historical metrics

Metric definitions and the pure metrics engine are documented in
`docs/metrics.md`. Run the test suite with:

```bash
pytest
```

### Phase 5: read-only API

The historical API reads from SQLite and exposes:

```text
GET /health
GET /api/v1/stations
GET /api/v1/routes
GET /api/v1/journey-legs
GET /api/v1/reliability
GET /api/v1/delays
GET /api/v1/cancellations
GET /api/v1/collections/latest
GET /api/v1/data-quality
GET /api/v1/reliability/by-weekday
GET /api/v1/reliability/by-hour
```

Metrics endpoints accept `station`, `operator`, `event_type`, `from_date`,
`to_date`, `weekday`, and `hour` filters. Historical HSP metrics are kept
separate from future live Darwin forecasts.

The data-quality endpoint reports event and service counts, missing actual
times, cancellations, duplicate groups, and rejected records. Collection
history can be scoped with `?journey_leg=HML-EUS`.

### CI and real-data verification

CI runs the test suite plus Ruff formatting and lint checks. Locally:

```bash
pip install -e ".[dev]"
pytest
ruff format --check .
ruff check .
```

After a bounded live collection, verify the leg and data quality:

```bash
curl "http://127.0.0.1:5000/api/v1/collections/latest?journey_leg=HML-EUS"
curl "http://127.0.0.1:5000/api/v1/data-quality?journey_leg=HML-EUS"
```

### Local demo container

The app can be run as a small container demo with a persistent SQLite volume:

```bash
docker compose up --build
```

Open `http://127.0.0.1:8000/`. The container starts with an empty database;
collect or import data separately, then mount or copy the database into the
volume. This demo does not include credentials or live collection jobs.

### Phase 6: dashboard

Open `http://127.0.0.1:5000/` after starting Flask to view the dashboard.
It provides overview cards, delay distribution, hourly comparisons, filters,
sample-size information, and data-coverage context. This phase uses only the
historical API; live Darwin forecasts and TfL transfer calculations are not
included.

## Roadmap

1. Select and document a permitted data source.
2. Define the data model and reliability calculations.
3. Implement an importer with validation and fixtures.
4. Expose read-only API endpoints.
5. Build the dashboard and deploy a small demo.

## License

MIT. See [LICENSE](LICENSE).
