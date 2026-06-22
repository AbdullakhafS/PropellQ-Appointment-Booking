from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src import db
from src.backup_automation import BackupEngine, BackupPolicy, BackupType, RestoreType
from src.restore_verification import RestoreVerificationEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backup and restore automation")
    parser.add_argument("--db", dest="db_path", default=str(Path(__file__).parent / "db" / "appointments.db"), help="SQLite database path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Backup commands
    backup_parser = subparsers.add_parser("backup", help="Execute a backup")
    backup_parser.add_argument("--policy", required=True, help="Backup policy name")
    backup_parser.add_argument("--operator", default="system", help="Operator identity")

    register_policy_parser = subparsers.add_parser("register-policy", help="Register a backup policy")
    register_policy_parser.add_argument("--policy-name", required=True, help="Policy name")
    register_policy_parser.add_argument("--dataset", required=True, help="Dataset name")
    register_policy_parser.add_argument("--type", choices=["full", "incremental"], required=True, help="Backup type")
    register_policy_parser.add_argument("--cron", default="0 2 * * *", help="Cron schedule")
    register_policy_parser.add_argument("--retention-days", type=int, default=30, help="Retention days")
    register_policy_parser.add_argument("--rpo-minutes", type=int, default=60, help="RPO target in minutes")
    register_policy_parser.add_argument("--rto-minutes", type=int, default=120, help="RTO target in minutes")
    register_policy_parser.add_argument("--owner", required=True, help="Owner team")

    # Restore commands
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("--backup-id", required=True, help="Backup execution ID")
    restore_parser.add_argument("--target-env", required=True, help="Target environment")
    restore_parser.add_argument("--operator", default="system", help="Operator identity")

    verify_parser = subparsers.add_parser("verify", help="Verify restored database")
    verify_parser.add_argument("--restore-id", required=True, help="Restore event ID")
    verify_parser.add_argument("--restored-db", required=True, help="Path to restored database")

    # Drill commands
    drill_parser = subparsers.add_parser("drill", help="Execute a recovery drill")
    drill_parser.add_argument("--drill-id", required=True, help="Drill ID")
    drill_parser.add_argument("--operator", default="system", help="Operator identity")

    # Reporting commands
    report_parser = subparsers.add_parser("report", help="Generate recovery report")
    report_parser.add_argument("--drill-id", help="Drill ID for report")
    report_parser.add_argument("--days", type=int, default=30, help="Days back for report")

    list_parser = subparsers.add_parser("list-executions", help="List recent backups")
    list_parser.add_argument("--dataset", help="Filter by dataset")
    list_parser.add_argument("--limit", type=int, default=10, help="Limit results")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    db_path = Path(args.db_path)
    db.initialize_database(db_path)

    with db.get_connection(db_path) as connection:
        backup_engine = BackupEngine(connection)
        restore_engine = RestoreVerificationEngine(connection)

        if args.command == "register-policy":
            policy = BackupPolicy(
                policy_name=args.policy_name,
                dataset_name=args.dataset,
                backup_type=BackupType(args.type),
                schedule_cron=args.cron,
                retention_days=args.retention_days,
                encryption_algorithm="AES-256-GCM",
                kms_key_id=None,
                compression_enabled=True,
                storage_location=str(Path(__file__).parent / "generated" / "backups"),
                owner_team=args.owner,
                rpo_target_minutes=args.rpo_minutes,
                rto_target_minutes=args.rto_minutes,
            )
            backup_engine.register_policy(policy)
            print(json.dumps({"status": "policy_registered", "policyName": args.policy_name}, indent=2))
            return 0

        if args.command == "backup":
            execution = backup_engine.execute_backup(args.policy, args.operator)
            print(json.dumps({
                "executionId": execution.execution_id,
                "status": execution.status.value,
                "backupLocation": execution.backup_location,
                "backupSize": execution.backup_size_bytes,
                "checksum": execution.backup_checksum,
                "durationMs": execution.duration_ms,
            }, indent=2))
            return 0

        if args.command == "restore":
            execution_row = connection.execute(
                "SELECT * FROM backup_executions WHERE execution_id = ?",
                [args.backup_id],
            ).fetchone()
            if not execution_row:
                print(f"Backup execution not found: {args.backup_id}")
                return 1

            backup_location = execution_row["backup_location"]
            dataset_name = execution_row["dataset_name"]
            event_id = restore_engine.record_restore_event(
                args.backup_id,
                dataset_name,
                "drill",
                args.target_env,
                args.operator,
            )
            restore_engine.update_restore_event_status(event_id, "in_progress")
            print(json.dumps({"restoreEventId": event_id, "backupLocation": backup_location}, indent=2))
            return 0

        if args.command == "verify":
            restored_db = Path(args.restored_db)
            all_passed, results = restore_engine.verify_restore(args.restore_id, restored_db)
            restore_engine.update_restore_event_status(
                args.restore_id,
                "completed" if all_passed else "failed",
            )
            print(json.dumps({
                "restoreEventId": args.restore_id,
                "allPassed": all_passed,
                "verifications": [
                    {
                        "type": r.verification_type.value,
                        "status": r.status.value,
                        "targetTable": r.verification_target_table,
                        "failureReason": r.failure_reason,
                    }
                    for r in results
                ],
            }, indent=2))
            return 0

        if args.command == "list-executions":
            query = "SELECT * FROM backup_executions WHERE status = 'succeeded'"
            params: list = []
            if args.dataset:
                query += " AND dataset_name = ?"
                params.append(args.dataset)
            query += " ORDER BY completed_at DESC LIMIT ?"
            params.append(args.limit)

            rows = connection.execute(query, params).fetchall()
            executions = [
                {
                    "executionId": row["execution_id"],
                    "policyName": row["policy_name"],
                    "datasetName": row["dataset_name"],
                    "status": row["status"],
                    "completedAt": row["completed_at"],
                    "backupSize": row["backup_size_bytes"],
                }
                for row in rows
            ]
            print(json.dumps({"executions": executions}, indent=2))
            return 0

        parser.error("Unknown command")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
