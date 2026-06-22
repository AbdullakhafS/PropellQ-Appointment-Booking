from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src import db
from src.lifecycle_jobs import LifecycleJobEngine


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lifecycle retention and archive jobs")
    parser.add_argument("--db", dest="db_path", default=str(db.DEFAULT_DB_PATH), help="SQLite database path")
    parser.add_argument("--report-dir", default=None, help="Directory for compliance evidence reports")

    subparsers = parser.add_subparsers(dest="command", required=True)

    archive_parser = subparsers.add_parser("archive", help="Run archive job")
    archive_parser.add_argument("--dataset", default=None, help="Limit to a dataset")
    archive_parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    archive_parser.add_argument("--operator", default="system", help="Operator identity")
    archive_parser.add_argument("--at", dest="reference_time", default=None, help="ISO-8601 reference time")

    purge_parser = subparsers.add_parser("purge", help="Run purge job")
    purge_parser.add_argument("--dataset", default=None, help="Limit to a dataset")
    purge_parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    purge_parser.add_argument("--operator", default="system", help="Operator identity")
    purge_parser.add_argument("--at", dest="reference_time", default=None, help="ISO-8601 reference time")

    retrieve_parser = subparsers.add_parser("retrieve", help="Retrieve an archived record")
    retrieve_parser.add_argument("--dataset", required=True, help="Dataset name")
    retrieve_parser.add_argument("--record-key", required=True, help="Record key")
    retrieve_parser.add_argument("--role", required=True, help="Requester role")
    retrieve_parser.add_argument("--requester", default="system", help="Requester identity")

    report_parser = subparsers.add_parser("report", help="Print a compliance evidence report")
    report_parser.add_argument("--run-id", required=True, help="Lifecycle run identifier")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    db.initialize_database(Path(args.db_path))
    with db.get_connection(Path(args.db_path)) as connection:
        engine = LifecycleJobEngine(connection, report_dir=Path(args.report_dir) if args.report_dir else None)
        reference_time = _parse_iso(getattr(args, "reference_time", None))

        if args.command == "archive":
            report = engine.run_archive(args.dataset, reference_time, args.dry_run, args.operator)
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
            return 0

        if args.command == "purge":
            report = engine.run_purge(args.dataset, reference_time, args.dry_run, args.operator)
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
            return 0

        if args.command == "retrieve":
            payload = engine.retrieve_archived_record(args.dataset, args.record_key, args.role, args.requester)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        if args.command == "report":
            report = engine.latest_report(args.run_id)
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
            return 0

        parser.error("Unknown command")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
