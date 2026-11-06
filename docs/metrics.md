# TrackRecord metrics

TrackRecord calculates descriptive historical metrics from stored
`service_stops`. It does not replace or alter live Darwin forecasts.

## Event scope

Metrics are calculated for one event type at a time (`arrival` or `departure`),
and can be filtered by station, operator, route, or date before calculation.
Cancelled events are included in totals and cancellation counts, but excluded
from delay averages and on-time percentages because they have no completed
journey time.

## Definitions

- **Observed events:** events with an actual time.
- **Coverage:** observed events divided by all events, expressed as a percentage.
- **On-time:** a non-cancelled event with delay at or below 1 minute.
- **Average delay:** arithmetic mean of delays for observed, non-cancelled events.
- **Median delay:** median delay for observed, non-cancelled events.
- **Cancellation rate:** cancelled events divided by all events.
- **Delayed over 5 minutes:** delay greater than 5 minutes.
- **Delayed over 15 minutes:** delay greater than 15 minutes.

Early services are retained as negative delays and count as on time. If there
are no eligible records for a metric, TrackRecord returns `null` rather than
displaying a misleading zero.

## Grouping

Weekday grouping uses the service date encoded in the HSP RID. Hour grouping
uses the local scheduled `HHMM` value. Invalid or unavailable dates and times
are excluded from those groupings.

The HSP provider's definitions and current feed documentation must be checked
before release. These application metrics are descriptive and should not be
presented as guaranteed predictions.
