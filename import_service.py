"""Import a saved service-details fixture into SQLite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trackrecord.database import TrackRecordDatabase
from trackrecord.importer import TrainEventImporter
from trackrecord.repository import TrainEventRepository


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("fixtures/service_details_sample.json"),
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("trackrecord.sqlite3"),
    )
    args = parser.parse_args()

    payload = json.loads(args.fixture.read_text(encoding="utf-8"))
    with TrackRecordDatabase(args.database) as database:
        repository = TrainEventRepository(database.connection)
        saved = TrainEventImporter(repository).import_service_details(payload)
        print(f"Saved {saved} new events to {args.database}")


if __name__ == "__main__":
    main()
