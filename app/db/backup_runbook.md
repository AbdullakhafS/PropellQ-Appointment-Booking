# Backup and Restore Automation Runbook

**Status:** Production  
**Version:** 1.0  
**Last Updated:** 2024  
**Owner:** Database and Reliability Engineering Team  

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Backup Policies and Scheduling](#backup-policies-and-scheduling)
4. [Executing Backups](#executing-backups)
5. [Restore Procedures](#restore-procedures)
6. [Monthly Recovery Drills](#monthly-recovery-drills)
7. [Verification and Validation](#verification-and-validation)
8. [Monitoring and Alerting](#monitoring-and-alerting)
9. [Incident Response](#incident-response)
10. [Emergency Procedures](#emergency-procedures)
11. [Troubleshooting](#troubleshooting)

---

## Overview

This document describes the operational procedures for backup, restore, and recovery drill automation for the PropellQ Appointment Booking platform. The system provides:

- **Full and Incremental Backups:** Automated scheduled backups with configurable retention
- **Encryption at Rest:** AES-256-GCM with HSM-backed key management
- **Automated Restore Verification:** Integrity checks, referential validation, and critical query testing
- **Monthly Recovery Drills:** Isolated environment restore exercises to validate RTO/RPO targets
- **Compliance Evidence:** Immutable audit trail for all backup, restore, and drill operations
- **Incident Tracking:** Alert escalation and runbook integration for backup/restore failures

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Backup Automation                       │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Backup Policy Registration & Scheduling       │   │
│  │  - Full/Incremental backup schedule via cron  │   │
│  │  - Retention tier policy (hot/warm/cold)      │   │
│  │  - RPO/RTO targets and SLA thresholds         │   │
│  └─────────────────────────────────────────────────┘   │
│                        ↓                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Backup Execution Engine                       │   │
│  │  - Copy database to backup location            │   │
│  │  - Compute checksums and compression ratios    │   │
│  │  - Encrypt with KMS key management             │   │
│  │  - Audit trail and metadata persistence        │   │
│  └─────────────────────────────────────────────────┘   │
│                        ↓                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Restore Verification Engine                   │   │
│  │  - Restore to isolated environment             │   │
│  │  - Verify schema integrity                     │   │
│  │  - Check row counts and checksums              │   │
│  │  - Validate referential integrity              │   │
│  │  - Execute critical business queries           │   │
│  └─────────────────────────────────────────────────┘   │
│                        ↓                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Recovery Drill Automation                      │   │
│  │  - Monthly scheduled restore exercise          │   │
│  │  - Metrics: RTO/RPO achievement vs targets     │   │
│  │  - Evidence capture and compliance reporting   │   │
│  │  - Blocker identification and remediation      │   │
│  └─────────────────────────────────────────────────┘   │
│                        ↓                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Alerting and Incident Management              │   │
│  │  - Backup failures trigger CRITICAL alerts     │   │
│  │  - RPO/RTO SLA misses escalate to on-call      │   │
│  │  - Drill failures block production deployments │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Policy Registration Phase**
   - DBA registers backup policy (dataset, schedule, retention, encryption)
   - System seeds `backup_policies` table
   - Policy includes RPO/RTO targets for compliance measurement

2. **Backup Execution Phase**
   - Scheduler triggers backup engine at cron time
   - Engine copies database to encrypted storage location
   - Backup execution record inserted to `backup_executions` table
   - Metadata: size, checksum, row count, compression ratio, encryption status

3. **Restore Verification Phase**
   - Restore engine copies backup to isolated environment
   - Schema integrity verified (all tables present)
   - Row counts compared against baseline
   - Referential integrity checks run (FK constraints)
   - Critical business queries executed and validated
   - Verification results persisted to `restore_verification` table

4. **Drill Execution Phase**
   - Monthly drill scheduled via `restore_drills` table
   - Isolation ensures no production impact
   - Measured metrics: RTO (restore completion time), RPO (data currency point accuracy)
   - Report generated and stored in `drill_reports` table
   - Approval/sign-off by compliance officer

---

## Backup Policies and Scheduling

### Register a Backup Policy

```bash
python app/db/backup.py register-policy \
  --db app/db/appointments.db \
  --policy-name "production_full_backup" \
  --dataset "appointments" \
  --type "full" \
  --cron "0 2 * * *" \
  --retention-days 30 \
  --rpo-minutes 60 \
  --rto-minutes 120 \
  --owner "platform-team"
```

**Parameters:**
- `--policy-name`: Unique identifier for this backup policy
- `--dataset`: Name of the dataset (appointments, patient_profiles, etc.)
- `--type`: `full` or `incremental`
- `--cron`: POSIX cron format for schedule (default: `0 2 * * *` = 2 AM daily)
- `--retention-days`: How long to keep backups before purge (default: 30)
- `--rpo-minutes`: Recovery Point Objective target in minutes (default: 60)
- `--rto-minutes`: Recovery Time Objective target in minutes (default: 120)
- `--owner`: Team responsible for this policy

**Encryption Defaults:**
- Algorithm: AES-256-GCM
- Key management: HSM-backed (KMS key ID optional; if omitted, use default key)
- Compression: Enabled (zstd algorithm)

### Typical Policy Schedule

```
# Production: Daily full backup at 2 AM, monthly incremental backups
production_full_backup:
  - type: full
  - cron: "0 2 * * *"     # Every day at 2 AM UTC
  - retention_days: 30    # Keep 30 days of backups
  - rpo_target: 60 minutes
  - rto_target: 120 minutes

# Staging: Weekly full backups
staging_backup:
  - type: full
  - cron: "0 3 ? * SUN"   # Sundays at 3 AM UTC
  - retention_days: 14    # 2 weeks retention
  - rpo_target: 240 minutes
  - rto_target: 240 minutes
```

---

## Executing Backups

### Manual Backup Execution

```bash
python app/db/backup.py backup \
  --db app/db/appointments.db \
  --policy "production_full_backup" \
  --operator "dba-oncall"
```

**Output:**
```json
{
  "executionId": "a1b2c3d4e5f6...",
  "status": "succeeded",
  "backupLocation": "/mnt/backups/appointments.backup.full.20240115T020000Z.db",
  "backupSize": 524288000,
  "checksum": "sha256:abc123...",
  "durationMs": 45000
}
```

### Automated Backup via Cron

Add to system crontab (Linux/macOS) or Task Scheduler (Windows):

```bash
# Execute daily full backup at 2 AM UTC
0 2 * * * cd /opt/propellq && python app/db/backup.py backup --policy production_full_backup --operator system
```

### Monitoring Backup Execution

List recent backups:

```bash
python app/db/backup.py list-executions \
  --db app/db/appointments.db \
  --dataset "appointments" \
  --limit 10
```

**Output:**
```json
{
  "executions": [
    {
      "executionId": "a1b2c3d4e5f6...",
      "policyName": "production_full_backup",
      "datasetName": "appointments",
      "status": "succeeded",
      "completedAt": "2024-01-15T02:45:30Z",
      "backupSize": 524288000
    },
    ...
  ]
}
```

### Backup Failure Handling

If a backup fails, the system:

1. **Marks status as `failed`** in `backup_executions` table
2. **Records error message** with diagnostic context
3. **Emits CRITICAL alert** to incident management system
4. **Triggers automated runbook** for on-call response
5. **Logs audit trail entry** with operator identity and timestamp

See [Incident Response](#incident-response) for troubleshooting.

---

## Restore Procedures

### Pre-Restore Verification Checklist

Before initiating any restore operation:

- [ ] Isolated restore environment is available (no production data)
- [ ] Target environment database is accessible and empty
- [ ] KMS key is available and not rotated recently
- [ ] Operator identity and approval chain established
- [ ] Restore rationale documented (drill, emergency, PITR)
- [ ] RPO/RTO targets captured for measurement

### Execute Restore Operation

```bash
# 1. Identify the backup execution to restore from
BACKUP_ID=$(python app/db/backup.py list-executions \
  --limit 1 | grep executionId | head -1 | cut -d'"' -f4)

# 2. Initiate restore to isolated environment
python app/db/backup.py restore \
  --db app/db/appointments.db \
  --backup-id "$BACKUP_ID" \
  --target-env "dev-restore-box" \
  --operator "dba-oncall"
```

**Output:**
```json
{
  "restoreEventId": "evt-xyz789...",
  "backupLocation": "/mnt/backups/appointments.backup.full.20240115T020000Z.db"
}
```

### Restore Point Selection

The system supports three restore point types:

| Type | Use Case | Selection |
|------|----------|-----------|
| **Full** | Complete database snapshot | Latest successful full backup |
| **Point-in-Time (PITR)** | Restore to specific timestamp | Query backup metadata for timestamp |
| **Snapshot** | Most recent backup (full or incremental) | Latest by `completed_at` timestamp |

### Post-Restore Verification

After restore completes, verify integrity:

```bash
RESTORE_ID="evt-xyz789..."
RESTORED_DB="/path/to/restored/appointments.db"

python app/db/backup.py verify \
  --db app/db/appointments.db \
  --restore-id "$RESTORE_ID" \
  --restored-db "$RESTORED_DB"
```

**Output:**
```json
{
  "restoreEventId": "evt-xyz789...",
  "allPassed": true,
  "verifications": [
    {
      "type": "schema",
      "status": "passed",
      "targetTable": null,
      "failureReason": null
    },
    {
      "type": "row_count",
      "status": "passed",
      "targetTable": "appointments",
      "failureReason": null
    },
    ...
  ]
}
```

### Restore Failure Scenarios

| Scenario | Root Cause | Resolution |
|----------|-----------|------------|
| Corrupt backup file | Disk corruption during backup | Use prior backup; check storage health |
| Missing schema tables | Backup predates table creation | Identify correct backup with required tables |
| Referential integrity violations | Data inconsistency in backup | Review source data cleanup; restore to earlier backup |
| Encryption key unavailable | KMS key deleted or rotated | Verify key policy; restore with available key version |
| Restore timeout | Large database or slow storage | Increase timeout; check resource availability |

---

## Monthly Recovery Drills

### Drill Scheduling

Recovery drills are scheduled monthly and executed on a fixed date:

```bash
# Schedule a monthly drill
python app/db/backup.py drill \
  --drill-id "drill-monthly-production" \
  --operator "qa-lead"
```

### Drill Execution Workflow

1. **Prepare Isolated Environment**
   - Provision isolated restore target (separate database server, VPC, or container)
   - Ensure no network connectivity to production
   - Capture baseline resource metrics (CPU, memory, I/O)

2. **Initiate Restore**
   - Retrieve latest successful backup
   - Initiate restore operation in isolated environment
   - Record start time (`initiated_at`) for RTO measurement

3. **Perform Verification**
   - Run schema integrity checks
   - Validate row counts against baseline
   - Execute critical business queries
   - Measure end time (`completed_at`)

4. **Calculate Metrics**
   - **RTO Achieved:** `completed_at - initiated_at` (in minutes)
   - **RPO Achieved:** Difference between current time and `data_currency_point` from backup
   - **Target Met:** Compare achieved vs target (e.g., RTO 45 min vs target 120 min ✓)

5. **Generate Report**
   ```json
   {
     "reportId": "report-drill-monthly-20240115",
     "drillId": "drill-monthly-production",
     "drillDate": "2024-01-15",
     "drillOutcome": "success",
     "drillDurationMinutes": 42,
     "rpoAchievedMinutes": 90,
     "rtoAchievedMinutes": 42,
     "rpoTargetMinutes": 60,
     "rtoTargetMinutes": 120,
     "rpoTargetMet": true,
     "rtoTargetMet": true,
     "integrityChecksPassed": true,
     "criticalQueriesValidated": true,
     "blockers": null,
     "remediationActions": null,
     "executedBy": "qa-lead",
     "approvedBy": "dba-manager",
     "approvedAt": "2024-01-15T12:00:00Z"
   }
   ```

6. **Compliance Approval**
   - Compliance officer reviews report
   - Signs off on drill success/remediation items
   - Report archived for audit trail

### Drill Failure Handling

If drill fails to meet SLA targets:

1. **Capture Blocker Details**
   - Infrastructure issue (storage, network, compute)?
   - Data integrity problem?
   - Encryption key access delay?

2. **Log Remediation Action**
   - Assign to engineering team
   - Set target resolution date
   - Escalate if drill blockage affects production readiness

3. **Re-run Drill**
   - After remediation is complete
   - Document improvement metrics
   - Re-submit for compliance approval

---

## Verification and Validation

### Verification Types

| Type | Scope | Failure Impact |
|------|-------|-----------------|
| **Schema** | All tables present with expected columns | Blocks drill pass |
| **Row Count** | Verify count in each table matches source | Warning; investigate data loss |
| **Referential** | Foreign key constraint validation | Blocks drill pass |
| **Critical Query** | Execute business-critical SQL queries | Blocks drill pass |
| **Checksum** | Verify data integrity via checksums | Warning if drift detected |

### Expected Verification Results

```
✓ schema:     PASSED  - All expected tables present
✓ row_count:  PASSED  - appointments (1000 rows)
✓ row_count:  PASSED  - patient_profiles (500 rows)
✓ row_count:  PASSED  - providers (50 rows)
✓ referential: PASSED  - No FK constraint violations
✓ critical_query: PASSED  - Available appointments query executed
✓ critical_query: PASSED  - Patient count query executed
✓ critical_query: PASSED  - Active providers query executed
✓ critical_query: PASSED  - Reservation queue query executed

OVERALL: PASSED (8/8 checks)
```

### Manual Verification (If Automated Checks Insufficient)

Connect to restored database and execute queries:

```sql
-- 1. Verify tables exist
SELECT name FROM sqlite_master WHERE type='table' 
  ORDER BY name;

-- 2. Count rows in each table
SELECT 'appointments' as table_name, COUNT(*) as row_count 
  FROM appointments
UNION ALL
SELECT 'patient_profiles', COUNT(*) FROM patient_profiles
UNION ALL
SELECT 'providers', COUNT(*) FROM providers;

-- 3. Check for NULL values in critical columns
SELECT COUNT(*) FROM appointments 
  WHERE appointment_date IS NULL 
     OR start_time IS NULL 
     OR provider_id IS NULL;

-- 4. Verify referential integrity
PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;

-- 5. Validate business logic
SELECT COUNT(*) as available_slots 
  FROM appointments 
  WHERE status = 'available' 
    AND appointment_date >= DATE('now');
```

---

## Monitoring and Alerting

### SLA Thresholds

| Alert Type | Severity | Threshold | Response Time |
|------------|----------|-----------|-----------------|
| Backup missed | CRITICAL | No backup in 25 hours | 15 minutes |
| Backup failed | CRITICAL | Execution status = failed | 15 minutes |
| RPO exceeded | WARNING | Data currency > RPO target + 30% | 60 minutes |
| RTO exceeded | WARNING | Restore duration > RTO target + 30% | 60 minutes |
| Drill failed | WARNING | Drill outcome != success | 60 minutes |
| Encryption key expiring | INFO | KMS key expires in < 30 days | 240 minutes |

### Alerting Configuration

Alerts are sent to:
- **CRITICAL:** PagerDuty on-call, Slack #ops-incidents
- **WARNING:** Slack #ops-warnings, email ops-team@propellq.com
- **INFO:** Slack #ops-info

Example alert payload:

```json
{
  "alertId": "alert-backup-failed-20240115",
  "alertType": "backup_failed",
  "severity": "critical",
  "message": "Backup failed for dataset 'appointments' (execution: a1b2c3d4e5f6)",
  "affectedDataset": "appointments",
  "incidentTarget": "#ops-incidents",
  "runbookLink": "https://wiki.propellq.com/runbooks/backup-failure",
  "retryBackoffSeconds": 300,
  "createdAt": "2024-01-15T03:00:00Z"
}
```

### Dashboard Metrics

Monitor the following KPIs:

- Backup success rate (target: 99.9%)
- Average backup duration (trend baseline: 45 minutes)
- Data loss (target: 0 files)
- Restore verification pass rate (target: 100%)
- Drill RTO achievement (target: ≤ 120 minutes)
- Drill RPO achievement (target: ≤ 60 minutes)

---

## Incident Response

### Backup Failure Incident

**Trigger:** Alert "backup_failed" with CRITICAL severity

**Immediate Actions (0-5 min):**
1. Acknowledge alert in PagerDuty
2. Check if previous backup succeeded (within 24 hours)
3. Verify backup storage location is accessible
4. Confirm database is responsive and not locked

**Investigation (5-15 min):**
```bash
# Check backup execution log
python app/db/backup.py list-executions --limit 5

# Query error message in database
sqlite3 app/db/appointments.db \
  "SELECT error_message, started_at FROM backup_executions 
   WHERE status = 'failed' 
   ORDER BY started_at DESC LIMIT 1"

# Check disk space on backup storage
df -h /mnt/backups

# Verify KMS key accessibility
aws kms describe-key --key-id arn:aws:kms:...
```

**Remediation:**
- If storage full: Archive old backups to cold storage; retry backup
- If KMS key unavailable: Restore key access; retry with backup key version
- If database locked: Check active connections; commit pending transactions
- If disk corruption: Restore from prior backup; check storage health

**Post-Incident:**
- File incident report with root cause
- Implement preventive controls (disk quota alert, KMS key monitoring)
- Update runbook with new learnings

### Restore Verification Failure

**Trigger:** Verification returns status = failed for row_count, referential, or critical_query

**Immediate Actions:**
1. Compare expected vs actual results in verification report
2. Check if source database had recent data changes (expected drift)
3. Verify no data loss occurred (row count matches or increases expected)

**Investigation:**
```bash
# Query restore event details
sqlite3 app/db/appointments.db \
  "SELECT * FROM restore_events WHERE event_id = 'evt-xyz789' LIMIT 1"

# Get all verification results
sqlite3 app/db/appointments.db \
  "SELECT verification_type, verification_target_table, status, failure_reason 
   FROM restore_verification 
   WHERE restore_event_id = 'evt-xyz789' 
   ORDER BY verification_type"

# Manual verification in restored database
sqlite3 /path/to/restored/appointments.db \
  "PRAGMA integrity_check; PRAGMA foreign_key_check;"
```

**Remediation:**
- If referential violation: Review data cleanup; restore from earlier backup
- If row count mismatch: Expected if database was active during backup; document drift
- If critical query fails: Check query syntax; verify required tables restored
- If schema incomplete: Restore from backup predating missing tables

**Post-Incident:**
- Update verification thresholds if expected drift is acceptable
- Add data cleanup steps to backup procedure if violations detected
- Schedule maintenance to address schema evolution

### RPO/RTO SLA Miss

**Trigger:** Alert "rpo_exceeded" or "rto_exceeded" with WARNING severity

**Immediate Actions:**
1. Review drill report to identify bottleneck
2. Check if infrastructure resources were constrained (CPU, I/O, network)
3. Determine if issue is reproducible or transient

**Investigation:**
```bash
# Get latest drill report
sqlite3 app/db/appointments.db \
  "SELECT * FROM drill_reports 
   ORDER BY drill_date DESC LIMIT 1"

# Check resource utilization during drill
grep "drill_date = '2024-01-15'" /var/log/resource-metrics.log

# Identify blocker from remediation notes
sqlite3 app/db/appointments.db \
  "SELECT blockers, remediation_actions FROM drill_reports 
   WHERE report_id = 'report-drill-monthly-20240115'"
```

**Remediation Options:**
- **RTO exceeded:** Upgrade restore environment resources (faster storage, more CPU)
- **RPO exceeded:** Increase backup frequency (e.g., hourly vs daily)
- **Both:** Review backup compression; optimize restore query performance

**Post-Incident:**
- Update SLA targets if current infrastructure cannot support (with business approval)
- Implement recommended remediation
- Re-run drill after fix to validate improvement

---

## Emergency Procedures

### Emergency Restore (Production Outage)

If production database is corrupted or offline:

```bash
# 1. Provision emergency restore environment
# (Use same infrastructure as production for accuracy)

# 2. Identify latest good backup
BACKUP_ID=$(python app/db/backup.py list-executions --limit 1 | jq '.executions[0].executionId')

# 3. Initiate emergency restore
python app/db/backup.py restore \
  --backup-id "$BACKUP_ID" \
  --target-env "prod-emergency-restore" \
  --operator "on-call-dba" \
  --rationale "EMERGENCY: Production database corrupted"

# 4. Run full verification suite
python app/db/backup.py verify \
  --restore-id "$RESTORE_ID" \
  --restored-db "/path/to/emergency/appointments.db"

# 5. If verification passes, switch traffic to restored database
# (Coordinate with application team; update DNS/connection strings)

# 6. Document timeline and actions taken
# (File incident report with root cause analysis)
```

**Success Criteria:**
- Restored database passes all verification checks
- Critical business queries execute successfully
- Data currency acceptable (within RTO/RPO targets if possible)
- No data loss in critical tables

### Emergency Key Recovery

If KMS key is unavailable:

```bash
# 1. Check key status
aws kms describe-key --key-id arn:aws:kms:us-east-1:123456789012:key/12345678-...

# 2. If key disabled, enable it
aws kms enable-key --key-id arn:aws:kms:...

# 3. If key scheduled for deletion, cancel deletion
aws kms cancel-key-deletion --key-id arn:aws:kms:...

# 4. If key unavailable, use backup key version
# (Requires AWS KMS administrator or emergency access)
aws kms describe-key --key-id arn:aws:kms:... --key-spec

# 5. After key recovery, verify backup accessibility
python app/db/backup.py restore \
  --backup-id "$BACKUP_ID" \
  --target-env "key-recovery-test" \
  --operator "kms-admin"
```

---

## Troubleshooting

### Issue: Backup times out

**Symptoms:** Backup execution hangs; doesn't complete in expected time

**Diagnosis:**
```bash
# Check if backup process is still running
ps aux | grep backup

# Monitor disk I/O
iotop -b | head -20

# Check database file size
ls -lh app/db/appointments.db

# Verify backup storage has space
df -h /mnt/backups
```

**Solutions:**
- Increase backup timeout threshold (default: 60 min)
- Upgrade backup storage to faster SSD
- Enable compression to reduce I/O
- Run backup during lower-traffic window

### Issue: Restore verification fails on row count

**Symptoms:** Verification reports "Expected 1000, got 999"

**Diagnosis:**
```bash
# Check if data was deleted after backup started
sqlite3 app/db/appointments.db \
  "SELECT COUNT(*) FROM appointments WHERE status = 'cancelled'"

# Compare timestamps of backup execution and deletion
sqlite3 app/db/appointments.db \
  "SELECT data_currency_point FROM backup_executions 
   WHERE status = 'succeeded' ORDER BY completed_at DESC LIMIT 1"
```

**Solutions:**
- Expected drift if database active during backup (document as acceptable)
- If unexpected data loss: investigate deletion causes; restore from earlier backup
- Update verification thresholds to tolerate expected drift

### Issue: Critical query fails during verification

**Symptoms:** Verification reports FAILED for critical_query

**Diagnosis:**
```bash
# Run query manually in restored database
sqlite3 /path/to/restored/appointments.db \
  "SELECT COUNT(*) FROM appointments WHERE status = 'available'"

# Check if table exists
sqlite3 /path/to/restored/appointments.db \
  ".schema appointments"

# Verify column names
sqlite3 /path/to/restored/appointments.db \
  "PRAGMA table_info(appointments)"
```

**Solutions:**
- If query syntax error: update query in verification suite
- If table missing: restore from backup predating table creation
- If column missing: verify backup schema compatibility with query

### Issue: Drill report shows RPO/RTO miss

**Symptoms:** "RTO achieved: 180 min > target 120 min"

**Diagnosis:**
```bash
# Check restore environment resource utilization
cat drill_report.json | grep -A5 "durationMinutes"

# Verify backup size didn't exceed expectations
python app/db/backup.py list-executions --limit 1

# Check for network latency during drill
# (Compare restore duration on prod vs restore environment)
```

**Solutions:**
- Upgrade restore environment resources (faster storage, more CPU)
- Pre-warm restore environment cache before drill
- Reduce data size if possible (archive old records)
- Increase RTO target if infrastructure constraints are acceptable (with business approval)

---

## Compliance and Audit

### Evidence Artifacts

All backup, restore, and drill operations generate immutable evidence:

- **Backup Execution Log:** `app/generated/backups/backup_{execution_id}.json`
- **Restore Event Log:** `app/generated/restores/restore_{event_id}.json`
- **Verification Report:** `app/generated/verifications/verify_{restore_id}.json`
- **Drill Report:** `app/generated/drills/drill_{drill_id}_{date}.json`
- **Audit Trail:** SQLite table `backup_audit_trail` (append-only)

### Audit Trail Query

```sql
SELECT audit_id, action_type, resource_id, actor_identity, 
       actor_role, action_details, created_at
FROM backup_audit_trail
WHERE created_at >= DATE('now', '-90 days')
ORDER BY created_at DESC;
```

### Compliance Reporting

Monthly compliance report includes:
- Total backups executed (success/failure count)
- Data retention policy adherence
- Drill outcomes (passed/failed, RTO/RPO achievement)
- Security incidents (unauthorized access attempts)
- Evidence integrity (checksum validation)

---

## References

- **Database Schema:** `app/db/backup_schema.sql`
- **Backup Engine:** `app/src/backup_automation.py`
- **Restore Verification:** `app/src/restore_verification.py`
- **CLI Tool:** `app/db/backup.py`
- **Test Suites:** `app/tests/test_backup_automation.py`, `app/tests/test_restore_verification.py`
- **AWS KMS Documentation:** https://docs.aws.amazon.com/kms/
- **SQLite Backup:** https://www.sqlite.org/backup.html
