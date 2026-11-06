"""Fetch one HSP service-details fixture using credentials from .env."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from trackrecord.hsp_client import HspClient


def main() -> None:
    load_dotenv()
    username = os.environ.get("NRE_USERNAME")
    password = os.environ.get("NRE_PASSWORD")
    if not username or not password:
        raise SystemExit("NRE_USERNAME and NRE_PASSWORD are required")

    service_details_url = os.environ.get("HSP_SERVICE_DETAILS_URL")
    if not service_details_url:
        metrics_url = os.environ.get("HSP_METRICS_URL")
        if metrics_url:
            service_details_url = metrics_url.rsplit("/", 1)[0] + "/serviceDetails"
        else:
            service_details_url = "https://hspfeeds.nationalrail.co.uk/serviceDetails"
    client = HspClient(
        username,
        password,
        service_details_url=service_details_url,
    )
    payload = client.get_service_details("202610126717911")
    output = Path("fixtures/service_details_sample.json")
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
