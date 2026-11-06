# Architecture

TrackRecord is a small, read-only historical analysis application:

```text
National Rail HSP
       |
       v
HSP client / saved fixture
       |
       v
Normalizer -> TrainEvent
       |
       v
Importer -> SQLite
       |
       v
Metrics calculator
       |
       v
Flask JSON API
       |
       v
HTML/CSS/JavaScript dashboard
```

## Boundaries

- **Client and importer:** obtain or load provider data and record collection
  outcomes.
- **Normalizer:** converts provider-specific payloads into immutable
  `TrainEvent` values.
- **Repository:** owns parameterized SQLite reads and writes.
- **Metrics calculator:** contains pure historical calculations and is
  independent of Flask and SQLite.
- **API:** validates filters and serializes data for read-only consumers.
- **Dashboard:** requests API data and renders it; it does not calculate the
  project's core metrics.

Arrival and departure observations are stored as separate stop events. This
keeps their reliability measurements distinct and avoids hiding a late
departure behind an on-time arrival.

## Deliberate constraints

SQLite is appropriate for the single-user MVP and keeps local development and
deployment simple. A database server can be considered if concurrent writers,
multiple users, or collection volume make it necessary.

The MVP does not include React, user accounts, live Darwin forecasts, TfL
transfer calculations, notifications, or machine-learning predictions. These
would add complexity before the historical data contract is proven.
