# ADR 001: Keep the MVP historical and server-rendered

- **Status:** Accepted
- **Date:** 2026-11-06

## Decision

TrackRecord will begin with National Rail HSP historical data, SQLite,
server-side metrics, a Flask API, and a lightweight HTML/CSS/JavaScript
dashboard. The two rail legs will be analysed independently.

## Reasons

This is the smallest architecture that demonstrates data access,
normalization, persistence, metrics, API design, testing, and responsible
communication. It also lets the project use a real commuter problem without
pretending to solve cross-London connection reliability.

## Alternatives deferred

Live Darwin data, TfL transfer logic, React, PostgreSQL, accounts,
notifications, and prediction models remain future work. They may become
appropriate after the historical data contract, collection process, and
coverage are reliable.
