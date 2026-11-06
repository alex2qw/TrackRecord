"""Collect a bounded set of HSP services into SQLite."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from trackrecord.collector import HspCollector
from trackrecord.database import TrackRecordDatabase
from trackrecord.hsp_client import HspClient
from trackrecord.importer import TrainEventImporter
from trackrecord.repository import TrainEventRepository


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary-fixture", type=Path)
    parser.add_argument("--database", type=Path, default=Path("trackrecord.sqlite3"))
    parser.add_argument("--max-services", type=int, default=10)
    parser.add_argument("--pause-seconds", type=float, default=0.25)
    parser.add_argument("--from-date")
    parser.add_argument("--to-date")
    parser.add_argument("--from-loc", default="HML")
    parser.add_argument("--to-loc", default="EUS")
    parser.add_argument("--journey-leg", default="HML-EUS")
    args = parser.parse_args()
    load_dotenv()

    username = os.environ.get("NRE_USERNAME")
    password = os.environ.get("NRE_PASSWORD")
    metrics_url = os.environ.get("HSP_METRICS_URL")
    if not username or not password:
        raise SystemExit("Collection requires NRE_USERNAME and NRE_PASSWORD")

    with TrackRecordDatabase(args.database) as database:
        repository = TrainEventRepository(database.connection)
        importer = TrainEventImporter(repository)
        service_details_url = os.environ.get("HSP_SERVICE_DETAILS_URL")
        client = HspClient(
            username,
            password,
            metrics_url=metrics_url,
            service_details_url=service_details_url,
        )
        if args.summary_fixture:
            summary = json.loads(args.summary_fixture.read_text(encoding="utf-8"))
        else:
            if not metrics_url or not args.from_date or not args.to_date:
                raise SystemExit(
                    "Live summary collection requires HSP_METRICS_URL, "
                    "--from-date, and --to-date"
                )
            summary = client.get_service_metrics(
                {
                    "from_loc": args.from_loc,
                    "to_loc": args.to_loc,
                    "from_time": "0700",
                    "to_time": "0900",
                    "from_date": args.from_date,
                    "to_date": args.to_date,
                    "days": "WEEKDAY",
                }
            )

        result = HspCollector(
            client,
            importer,
            pause_seconds=args.pause_seconds,
            journey_leg=args.journey_leg,
        ).collect_summary(summary, max_services=args.max_services)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
