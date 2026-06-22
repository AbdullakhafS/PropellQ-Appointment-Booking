from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.migration_pipeline import (
    MIGRATION_MANIFEST_PATH,
    MigrationExecutionContext,
    MigrationPipeline,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Versioned migration and rollback pipeline")
    parser.add_argument("--db", default=str(Path(__file__).resolve().parent / "appointments.db"), help="Target SQLite database")
    parser.add_argument("--environment", choices=["development", "staging", "production"], default="development")
    parser.add_argument("--approver", help="Approver identity for production migrations")
    parser.add_argument("--rationale", help="Approval rationale")
    parser.add_argument("--dry-run", action="store_true", help="Validate without applying SQL")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("lint", help="Run migration lint and safety checks")
    subparsers.add_parser("migrate", help="Apply migrations in manifest order")
    verify_parser = subparsers.add_parser("verify", help="Run post-deploy verification")
    verify_parser.add_argument("--version", default="1.0.0", help="Expected schema version")
    rollback_parser = subparsers.add_parser("rollback", help="Restore a previous database backup")
    rollback_parser.add_argument("--backup", required=True, help="Backup file path to restore")
    subparsers.add_parser("manifest", help="Print manifest contents")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    pipeline = MigrationPipeline(Path(args.db))

    if args.command == "manifest":
        print(json.dumps(json.loads(MIGRATION_MANIFEST_PATH.read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "lint":
        issues = []
        for migration in pipeline.manifest:
            issues.extend(pipeline.lint_migration(migration))
            issues.extend(pipeline.check_expand_contract_guardrails(migration))
        print(json.dumps({"issues": issues}, indent=2))
        return 1 if issues else 0

    context = MigrationExecutionContext(
        environment=args.environment,
        approver=args.approver,
        rationale=args.rationale,
        dry_run=args.dry_run,
    )

    if args.command == "migrate":
        records = pipeline.migrate(context)
        print(json.dumps([record.__dict__ for record in records], indent=2, default=str))
        return 0

    if args.command == "verify":
        result = pipeline.verify_post_deploy(args.version)
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "rollback":
        record = pipeline.rollback_last(context, Path(args.backup))
        print(json.dumps(record.__dict__, indent=2, default=str))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
