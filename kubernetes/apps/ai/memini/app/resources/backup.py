"""Hourly consistent SQLite snapshots to the backed-up APPS NFS mount."""

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import logging
import os
import sqlite3
import time


def snapshot(source: Path, directory: Path) -> Path:
    # Opening read-only fails if Memini has not created the store yet. Never
    # create an empty source database and mistake it for a successful backup.
    destination = directory / f"memini-{datetime.now(timezone.utc):%Y-%m-%d}.db"
    temporary = directory / ".memini-backup.tmp"
    try:
        # The backup API includes committed WAL transactions without copying a
        # live database file. It does not need sqlite-vec to interpret the data.
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as database:
            with closing(sqlite3.connect(temporary)) as backup:
                database.backup(backup, pages=256, sleep=0.1)
        with temporary.open("rb") as completed:
            os.fsync(completed.fileno())
        os.replace(temporary, destination)
        # Retain one snapshot per UTC day for the seven most recent days.
        # Only rotate after a successful replacement, preserving older copies
        # if the database or NFS mount is unavailable.
        for expired in sorted(directory.glob("memini-????-??-??.db"), reverse=True)[7:]:
            expired.unlink()
        return destination
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    while True:
        try:
            result = snapshot(Path("/data/memini.db"), Path("/backups"))
            logging.info("SQLite snapshot completed: %s", result.name)
            time.sleep(3600)
        except (OSError, sqlite3.Error):
            logging.exception("SQLite snapshot failed; retrying in 60 seconds")
            time.sleep(60)


if __name__ == "__main__":
    main()
