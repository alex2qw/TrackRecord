"""Authenticated client for National Rail HSP feeds."""

from __future__ import annotations

from typing import Any

import requests


class HspClientError(RuntimeError):
    """Raised when an HSP request cannot be completed or decoded."""


class HspClient:
    """Small, reusable client for the HSP service endpoints."""

    def __init__(
        self,
        username: str,
        password: str,
        *,
        base_url: str = "https://hspfeeds.nationalrail.co.uk",
        service_details_url: str | None = None,
        metrics_url: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not username or not password:
            raise ValueError("username and password are required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self._metrics_url = metrics_url
        self._service_details_url = service_details_url or (
            f"{base_url.rstrip('/')}/serviceDetails"
        )
        self._timeout_seconds = timeout_seconds
        self._session = requests.Session()
        self._session.auth = (username, password)
        self._session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "TrackRecord/0.1",
            }
        )

    def get_service_metrics(self, query: dict[str, Any]) -> dict[str, Any]:
        """Fetch a serviceMetrics summary for a bounded date/time query."""
        if not self._metrics_url:
            raise ValueError("metrics_url is required for serviceMetrics")
        if not query:
            raise ValueError("serviceMetrics query must not be empty")
        return self._post_json(self._metrics_url, query, "serviceMetrics")

    def get_service_details(self, rid: str) -> dict[str, Any]:
        """Fetch stop-level details for one HSP RID."""
        if not rid.strip():
            raise ValueError("rid must not be empty")

        return self._post_json(
            self._service_details_url, {"rid": rid}, "serviceDetails"
        )

    def _post_json(
        self, url: str, payload: dict[str, Any], endpoint: str
    ) -> dict[str, Any]:
        try:
            response = self._session.post(
                url, json=payload, timeout=self._timeout_seconds
            )
            response.raise_for_status()
            result = response.json()
        except requests.RequestException as exc:
            raise HspClientError(f"{endpoint} request failed") from exc
        except ValueError as exc:
            raise HspClientError(f"{endpoint} returned invalid JSON") from exc

        if not isinstance(result, dict):
            raise HspClientError(f"{endpoint} returned an unexpected payload")
        return result
