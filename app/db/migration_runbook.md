# Migration and Rollback Runbook

**Purpose:** Operational guide for versioned schema migrations, post-deploy verification, and emergency rollback.

## Preflight
- Confirm the migration manifest version order is unchanged.
- Capture a backup of the target database file.
- Record the current SQLite `PRAGMA user_version` value.
- Obtain production approver identity and rationale before execution.

## Execute Forward Migration
1. Run the migration pipeline against the selected environment.
2. Confirm the pipeline passes lint and expand-and-contract guardrails.
3. Apply the versioned migration in manifest order.
4. Record the generated migration audit artifact.

## Post-Deploy Verification
1. Validate the schema version checksum.
2. Confirm required tables exist.
3. Run smoke queries against appointments, patient profiles, and sync queue.
4. Fail the release if any smoke query or checksum check fails.

## Rollback Decision Tree
- If the migration fails before commit, discard the transaction and restore the backup.
- If the migration commits but verification fails, restore the pre-migration backup.
- If the production deployment is partially successful, stop writes, restore backup, and re-run verification.

## Emergency Rollback
1. Stop application traffic.
2. Restore the last known-good backup file.
3. Verify integrity with `PRAGMA integrity_check`.
4. Confirm `PRAGMA user_version` matches the previous known-good state.
5. Re-open traffic only after smoke queries succeed.

## Operator Notes
- Keep approver identity, timestamp, and rationale with the migration artifact.
- Retain migration logs and audit records according to the compliance policy.
- Do not bypass safety gates without a documented emergency authorization.
