# Data source

TrackRecord currently uses National Rail Historic Service Performance (HSP)
data for historical analysis. The application stores a normalized fixture and
reads it through the importer; it does not scrape National Rail web pages.

## Scope

The initial analysis focuses on the rail legs of the commute:

- Hemel Hempstead (`HML`) to London Euston (`EUS`)
- London King's Cross (`KGX`) or St Pancras (`STP`) to Cambridge (`CBG`)

Cross-London walking and connection reliability are not calculated yet.

## Credentials and requests

Credentials are loaded from environment variables and are not committed,
written to fixtures, or included in logs. Requests use explicit timeouts, and
future collection jobs must respect the provider's current rate limits and
terms. Any production collector should add bounded retries only for temporary
failures.

The exact endpoint, request limits, retention rights, and attribution
requirements must be verified against the current Rail Data Marketplace and
National Rail documentation before deployment. Claims from secondary sources
are not treated as authoritative.

## Data handling

Provider payloads are normalized into TrackRecord events before metrics are
calculated. Missing actual times remain missing, cancellations are represented
explicitly, and the dashboard reports coverage and sample size. Historical HSP
metrics are kept separate from any future Darwin live forecast.

National Rail attribution and any required licence notices must be added to a
deployed dashboard after the current provider requirements have been confirmed.
