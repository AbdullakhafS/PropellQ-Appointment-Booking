# TASK-105: Implement Migration and Rollback Pipeline - Master Task Breakdown

**Task ID:** TASK-105  
**Parent:** US-105 (EP-DATA-001)  
**Priority:** CRITICAL  
**Status:** Ready for Implementation  
**Total Points:** 56 (estimated)  
**Created:** 2026-06-22

---

## 1. Task Objective

Implement an automated, versioned migration and rollback pipeline that applies schema changes safely across all environments with approval gates, comprehensive auditability, and tested recovery paths for production deployments.

---

## 2. Scope Summary

| Acceptance Criterion | Implementation Task | Status |
|---|---|---|
| AC-1: Versioned migrations execute in order via CI/CD | PIPE-1, PIPE-2, QA-1 | Planned |
| AC-2: Rollback restores previous known-good version in non-prod | RB-1, RB-2, QA-2 | Planned |
| AC-3: Lint and safety checks block unsafe operations per policy | SAFE-1, SAFE-2, QA-3 | Planned |
| AC-4: Post-migration verification validates checksum/version and smoke queries | VERIFY-1, VERIFY-2, QA-4 | Planned |
| AC-5: Production migration logs and operator approvals are recorded | GOV-1, AUDIT-1, QA-5 | Planned |
| AC-6: Emergency rollback runbook is actionable and tested | RB-3, DOC-1, QA-6 | Planned |

---

## 3. Subtask Breakdown by Category

### CATEGORY A: Pipeline Infrastructure Tasks (14 pts)

#### PIPE-1: Migration Framework Integration (7 pts)
**Objective:** Select and integrate migration tool with strict versioning, deterministic ordering, and environment awareness

**Inputs:**
- Database standards (from TASK-104)
- CI/CD pipeline specification
- Migration directory structure requirements

**Outputs:**
- [ ] Migration tool selected and integrated (Flyway/Liquibase)
- [ ] Migration directory structure defined (migrations/, rollback/)
- [ ] Version naming convention enforced (V001__..., R001__...)
- [ ] One-way ordering validation implemented
- [ ] Deterministic execution guarantees documented

**Acceptance Criteria:**
- [ ] Migrations execute in strict numerical order (V001 → V002 → V003)
- [ ] No out-of-order execution possible
- [ ] Version metadata persisted (timestamp, checksum, duration, status)
- [ ] Dry-run capability implemented and tested
- [ ] Rollback script association validated per migration

**Key Implementation Details:**
- Tool: Flyway (open-source) or Liquibase with versioning
- Directory structure: `db/migrations/V###__description.sql`, `db/migrations/U###__description.sql`
- Checksum validation: SHA256 hash of migration content
- Status table: `flyway_schema_history` or equivalent

**Success Metrics:**
- [ ] 100% migration success rate in test environment
- [ ] Deterministic ordering verified in 10+ test runs
- [ ] <100ms per migration version lookup
- [ ] All migrations idempotent (can retry safely)

**Definition of Done:**
- [ ] Framework integrated into project
- [ ] Migration directory structure created
- [ ] Naming conventions documented
- [ ] Peer-reviewed and approved
- [ ] Ready for PIPE-2

---

#### PIPE-2: Environment Promotion Workflow (7 pts)
**Objective:** Configure migration stages across dev/test/staging/production with approval gates and artifact immutability

**Inputs:**
- PIPE-1 framework integration
- Environment definitions (dev, test, staging, prod)
- CI/CD pipeline infrastructure

**Outputs:**
- [ ] Environment promotion workflow defined (dev → test → staging → prod)
- [ ] Migration artifact immutability enforced
- [ ] Approval gates configured for production
- [ ] Rollback path pre-validated before promotion
- [ ] Environment-specific migration parameters (if needed)

**Acceptance Criteria:**
- [ ] Dev environment: Auto-apply migrations on commit
- [ ] Test/Staging: Auto-apply with approval notification
- [ ] Production: Manual approval required + pre-deployment validation
- [ ] Migration artifact versioning immutable (cannot be modified after creation)
- [ ] Rollback script present and validated before prod promotion

**Environment Promotion Pipeline:**
```
DEV (auto) → TEST (auto) → STAGING (manual approval) → PROD (manual approval + preflight checks)
```

**Key Implementation Details:**
- Immutability: Migrations stored in version control as read-only in prod
- Approval workflow: GitHub/Azure DevOps approval gates
- Pre-deployment validation: Schema checksum, constraint count, index count
- Estimated runtime: 2-5 minutes per environment

**Success Metrics:**
- [ ] All promotions logged with approval records
- [ ] 0 manual SQL execution bypasses migration pipeline
- [ ] Artifact version matches across all environments
- [ ] Rollback path validated in 100% of prod migrations

**Definition of Done:**
- [ ] Promotion workflow implemented
- [ ] Approval gates functional
- [ ] Immutability enforced
- [ ] Tested end-to-end across all environments
- [ ] Ready for SAFE-1 safety checks

---

### CATEGORY B: Rollback and Recovery Tasks (12 pts)

#### RB-1: Paired Forward/Backward Script Policy (4 pts)
**Objective:** Require and validate rollback scripts paired with every forward migration

**Inputs:**
- PIPE-1 framework
- Rollback script templates
- CI validation rules

**Outputs:**
- [ ] Policy document: Paired migration requirements
- [ ] Rollback script templates for common scenarios
- [ ] CI/CD validation: Paired script detection
- [ ] Test cases for rollback execution

**Acceptance Criteria:**
- [ ] Every V### migration has corresponding U### (undo) script
- [ ] U### scripts validated for syntactic correctness
- [ ] Rollback script content reverses forward migration
- [ ] Compensating transaction logic used when true rollback not possible
- [ ] CI/CD blocks migration without paired rollback script

**Paired Script Examples:**
```
V001__create_patient_table.sql
U001__drop_patient_table.sql

V002__add_mrn_unique_constraint.sql
U002__drop_mrn_unique_constraint.sql

V003__add_appointment_indexes.sql
U003__drop_appointment_indexes.sql
```

**Compensating Transaction Pattern:**
```sql
-- V004__add_non_nullable_column.sql
ALTER TABLE patient ADD phone_secondary VARCHAR(20);

-- U004__drop_non_nullable_column.sql (can't truly undo - data might be lost)
-- Instead, use compensating transaction:
ALTER TABLE patient DROP COLUMN phone_secondary;
-- OR if preserving data:
ALTER TABLE patient MODIFY phone_secondary VARCHAR(20) NULL;
```

**Success Metrics:**
- [ ] 100% of migrations have paired rollback scripts
- [ ] CI/CD validation catches missing rollback scripts
- [ ] Rollback scripts tested in staging
- [ ] Compensating logic documented when applicable

**Definition of Done:**
- [ ] Policy documented
- [ ] CI/CD validation rules implemented
- [ ] Test cases passing
- [ ] Ready for RB-2

---

#### RB-2: Non-Prod Rollback Rehearsal Automation (4 pts)
**Objective:** Automate failure simulation and rollback trigger validation in non-production environments

**Inputs:**
- RB-1 paired scripts
- Test/staging environments
- Failure injection mechanisms

**Outputs:**
- [ ] Rollback rehearsal automation script
- [ ] Failure injection scenarios (constraint violation, disk full, timeout)
- [ ] Automated rollback trigger and validation
- [ ] Success/failure report generation

**Acceptance Criteria:**
- [ ] Weekly rollback rehearsal executed automatically
- [ ] Failure scenarios simulated (4+ different failure types)
- [ ] Rollback triggered and schema version verified to revert
- [ ] Automated verification: Schema checksum before/after rollback
- [ ] 0 false positives or script failures in rehearsal

**Rollback Rehearsal Workflow:**
```
1. Apply V### migration to staging
2. Verify new schema state (checksum, version)
3. Simulate failure (inject error, trigger rollback condition)
4. Execute rollback (U### script)
5. Verify schema returned to previous state (checksum matches)
6. Report success/failure
7. Restore to latest migration for next rehearsal
```

**Failure Simulation Scenarios:**
- Constraint violation on forward migration (force rollback)
- Disk full during migration (timeout + rollback)
- Connection loss mid-migration (rollback on reconnect)
- Timeout after 30-second threshold (automatic rollback)

**Success Metrics:**
- [ ] Weekly automation schedule configured
- [ ] All 4+ failure scenarios tested successfully
- [ ] Rollback success rate > 99%
- [ ] Schema checksum match validated pre/post rollback

**Definition of Done:**
- [ ] Rehearsal automation script created and tested
- [ ] Failure injection scenarios implemented
- [ ] Weekly schedule configured
- [ ] 3+ successful rehearsals completed
- [ ] Ready for RB-3

---

#### RB-3: Emergency Rollback Procedure (4 pts)
**Objective:** Implement operator-initiated emergency rollback workflow with safety prompts and preflight validation

**Inputs:**
- RB-1 and RB-2 rollback infrastructure
- Production environment access controls
- Operator runbook template

**Outputs:**
- [ ] Emergency rollback script with interactive prompts
- [ ] Preflight validation checklist (backups, audit trail)
- [ ] Rollback authorization workflow
- [ ] Automatic incident notification (Slack, email, PagerDuty)

**Acceptance Criteria:**
- [ ] Operator can initiate rollback via CLI with clear prompts
- [ ] Multi-step confirmation required (3-step verification)
- [ ] Automatic backup verification before rollback
- [ ] Rollback duration monitored (failure if exceeds 5 minutes)
- [ ] Incident notification sent to on-call team
- [ ] All rollback actions logged with operator ID

**Emergency Rollback Workflow:**
```
Step 1: Operator runs: ./scripts/emergency-rollback.sh <migration-version>
Step 2: Script validates:
  - Backup exists and is recent (< 1 hour old)
  - Current version matches expected version
  - No locks on database
Step 3: Confirmation prompts:
  - "Are you sure you want to rollback? Current version: V005"
  - "Operator ID (for audit trail):"
  - "Reason for rollback (for incident log):"
Step 4: Final approval: "Type 'ROLLBACK' to confirm: "
Step 5: Execute rollback and monitor
Step 6: Verify schema matches previous version
Step 7: Send incident notification
Step 8: Generate rollback report
```

**Preflight Validation Checklist:**
- [ ] Backup file exists and is readable
- [ ] Current database version matches migration metadata
- [ ] No active locks on database tables
- [ ] Disk space sufficient for rollback operation
- [ ] Network connection stable to database

**Safety Prompts & Confirmations:**
```
⚠️  EMERGENCY ROLLBACK INITIATED
────────────────────────────────────
Current Version: V005 (add_indexes_migration)
Target Version: V004 (create_appointment_table)
Estimated Duration: 45 seconds

Preflight Checks:
✅ Backup verified (2026-06-22 14:30:00)
✅ No active locks
✅ Disk space: 500GB available

[3-Step Confirmation Required]
Step 1/3: Enter operator ID [████████]: alice-smith
Step 2/3: Reason for rollback: [Index performance issue discovered]
Step 3/3: Type 'ROLLBACK-V004' to confirm: [████████]

Executing rollback... [████████████████] 100% (45/45s)
✅ Rollback successful
✅ Schema matches V004 checksum
📊 Incident #INC-0042 created
🔔 Notification sent to #on-call
```

**Success Metrics:**
- [ ] Interactive prompts clear and actionable
- [ ] Preflight validation 100% success rate
- [ ] Rollback execution <5 minutes
- [ ] Zero accidental rollbacks (all require multi-step confirmation)
- [ ] All rollback actions audited

**Definition of Done:**
- [ ] Emergency rollback script implemented
- [ ] Interactive prompts and confirmations working
- [ ] Preflight validation validated
- [ ] Tested with manual simulations
- [ ] Operator runbook documented
- [ ] Ready for DOC-1

---

### CATEGORY C: Safety and Validation Tasks (16 pts)

#### SAFE-1: Migration Lint and Policy Checks (5 pts)
**Objective:** Add automated lint checks to detect unsafe migration patterns and block risky operations

**Inputs:**
- Migration SQL files
- Policy rules (naming, structure, anti-patterns)
- CI/CD pipeline

**Outputs:**
- [ ] Migration linter implementation
- [ ] Policy rules documentation (10+ rules)
- [ ] CI/CD integration for lint blocking
- [ ] False-positive tuning and exemptions

**Acceptance Criteria:**
- [ ] Naming convention validation (V###, U###, description)
- [ ] Anti-pattern detection: DROP without warning, ALTER without rollback
- [ ] Idempotency hints detection (IF EXISTS, IF NOT EXISTS)
- [ ] No hardcoded values (magic numbers, fixed timestamps)
- [ ] Migration size limit (< 100 SQL statements per migration)
- [ ] Syntax validation (SQL parsing for errors)
- [ ] Documentation requirement (header comments with purpose)

**Lint Rules (Enforced):**

| Rule ID | Rule Name | Pattern | Severity | Action |
|---------|-----------|---------|----------|--------|
| LNT-001 | Naming Convention | `V\d{3}__.*\.sql` | ERROR | Block migration |
| LNT-002 | No DROP without warning | `DROP TABLE` without comment | WARN | Log warning |
| LNT-003 | Idempotency | `IF (NOT) EXISTS` present | WARN | Log suggestion |
| LNT-004 | No hardcoded values | Literal dates, IDs, strings | ERROR | Require parameter |
| LNT-005 | Migration size | >100 SQL statements | WARN | Suggest split |
| LNT-006 | Syntax validation | Parse SQL for errors | ERROR | Block migration |
| LNT-007 | Documentation header | `-- Description:` required | ERROR | Require header |
| LNT-008 | Transaction safety | Auto-wrap in transaction | INFO | Apply by default |
| LNT-009 | Performance impact | ALTER on large table without online | WARN | Log consideration |
| LNT-010 | Constraint safety | FK constraint with RESTRICT | INFO | Verify intended |

**Lint Exemption Policy:**
```
-- propel-lint-disable LNT-002
DROP TABLE temp_table; -- Temporary table cleanup (exempted)
-- propel-lint-enable LNT-002
```

**Success Metrics:**
- [ ] All 10+ lint rules implemented
- [ ] CI/CD integration working (blocks on errors)
- [ ] 0 false positives on validated migrations
- [ ] Lint execution <5 seconds for 100 migrations

**Definition of Done:**
- [ ] Linter implementation complete
- [ ] All rules tested and validated
- [ ] CI/CD integration functional
- [ ] Documentation with exemption policy published
- [ ] Ready for SAFE-2

---

#### SAFE-2: Expand-and-Contract Guardrails (5 pts)
**Objective:** Detect breaking change patterns and enforce expand-and-contract migration sequencing

**Inputs:**
- SAFE-1 linter
- Schema version tracking
- Migration dependency analysis

**Outputs:**
- [ ] Breaking change detector
- [ ] Expand-and-contract validation rules
- [ ] Backward-compatible contract window enforcement
- [ ] Migration sequencing guidance

**Acceptance Criteria:**
- [ ] Breaking changes detected (column removal, type change, NOT NULL without default)
- [ ] Expand-and-contract pattern required (add → data migration → remove)
- [ ] Backward-compatible contract window: 2+ migration versions
- [ ] Service compatibility validated before promoting
- [ ] Migration sequencing enforces contract window

**Expand-and-Contract Pattern:**

Breaking Change Example: Remove column from in-use service
```sql
-- ❌ BLOCKED: Direct column removal (breaking change)
ALTER TABLE patient DROP COLUMN phone_secondary;

-- ✅ ALLOWED: Expand-and-contract pattern
-- V001: Add new column alongside old
ALTER TABLE patient ADD COLUMN phone_secondary_v2 VARCHAR(20);

-- V002: Migrate data (separate migration)
UPDATE patient SET phone_secondary_v2 = phone_secondary;

-- V003: Contract - remove old column (only after 2+ migrations)
ALTER TABLE patient DROP COLUMN phone_secondary;
```

Type Change Example: Change column type
```sql
-- ❌ BLOCKED: Direct type change
ALTER TABLE appointment MODIFY scheduled_start_time TIME;

-- ✅ ALLOWED: Expand-and-contract
-- V001: Add new column with new type
ALTER TABLE appointment ADD COLUMN scheduled_start_time_new DATETIME;

-- V002: Migrate data
UPDATE appointment SET scheduled_start_time_new = scheduled_start_time;

-- V003: Contract - switch and drop
ALTER TABLE appointment DROP COLUMN scheduled_start_time;
ALTER TABLE appointment RENAME COLUMN scheduled_start_time_new TO scheduled_start_time;
```

NOT NULL Addition Example:
```sql
-- ❌ BLOCKED: NOT NULL without default on existing data
ALTER TABLE patient ADD COLUMN status VARCHAR(50) NOT NULL;

-- ✅ ALLOWED: Add with default, then require
-- V001: Add with safe default
ALTER TABLE patient ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'active';

-- V002: Services can now rely on NOT NULL constraint
```

**Contract Window Validation:**
```
Migration V001 (add column) → Safe for 2 versions (V002, V003)
                              ↓
Migration V004 (can remove) → After 2-version contract window
```

**Success Metrics:**
- [ ] All breaking change patterns detected
- [ ] Expand-and-contract pattern enforced
- [ ] 0 direct column removals in production
- [ ] Contract window tracked and validated
- [ ] Service compatibility confirmed before promotion

**Definition of Done:**
- [ ] Breaking change detector implemented
- [ ] Expand-and-contract validation rules coded
- [ ] Contract window enforced in promotion workflow
- [ ] Tested with 5+ breaking change scenarios
- [ ] Ready for VERIFY-1

---

#### VERIFY-1: Post-Deploy Schema Verification (3 pts)
**Objective:** Validate schema checksum, version, and structural integrity after migration

**Inputs:**
- PIPE-2 migration framework
- Schema baseline from TASK-104
- Expected table/column/constraint counts

**Outputs:**
- [ ] Schema checksum calculation (SHA256 of DDL)
- [ ] Post-migration verification script
- [ ] Structural validation queries
- [ ] Checksum mismatch alert mechanism

**Acceptance Criteria:**
- [ ] Schema checksum matches expected value
- [ ] All expected tables present (count matches)
- [ ] All expected columns present with correct types
- [ ] All expected indexes present
- [ ] All expected constraints present
- [ ] Verification completes in <10 seconds

**Post-Deploy Verification Queries:**
```sql
-- Verify all expected tables
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_schema = 'appointment_db';
-- Expected: 10 tables

-- Verify specific table structure
SELECT COUNT(*) FROM information_schema.columns 
WHERE table_schema = 'appointment_db' AND table_name = 'patient';
-- Expected: 12 columns

-- Verify all indexes exist
SELECT COUNT(*) FROM information_schema.statistics 
WHERE table_schema = 'appointment_db' AND index_name != 'PRIMARY';
-- Expected: 13-15 indexes

-- Verify constraints
SELECT COUNT(*) FROM information_schema.key_column_usage 
WHERE constraint_schema = 'appointment_db' AND constraint_type = 'FOREIGN KEY';
-- Expected: 15+ FK constraints

-- Calculate schema checksum
SELECT SHA2(GROUP_CONCAT(SQL_MODE), 256) FROM information_schema.tables ...
```

**Success Metrics:**
- [ ] 100% checksum match after migration
- [ ] Structural validation 0 mismatches
- [ ] Verification <10 seconds
- [ ] Alert mechanism working for any discrepancy

**Definition of Done:**
- [ ] Verification script implemented
- [ ] All validation queries tested
- [ ] Checksum calculation reproducible
- [ ] Integrated into post-deploy workflow
- [ ] Ready for VERIFY-2

---

#### VERIFY-2: Smoke Query Verification (3 pts)
**Objective:** Run critical smoke queries to verify data integrity and basic read/write functionality

**Inputs:**
- VERIFY-1 schema verification
- Production query patterns
- Hot-path queries from TASK-104

**Outputs:**
- [ ] Smoke query test suite (5-10 critical queries)
- [ ] Read/write transaction validation
- [ ] Failure detection and alerting
- [ ] Smoke query report

**Acceptance Criteria:**
- [ ] 5+ hot-path queries execute successfully
- [ ] Basic INSERT, UPDATE, SELECT operations work
- [ ] Transaction rollback works (no orphaned records)
- [ ] Query returns expected row counts or results
- [ ] All smoke queries complete in <5 seconds total

**Smoke Query Suite:**
```sql
-- Q1: Patient lookup
SELECT COUNT(*) FROM patient WHERE patient_id > 0;
-- Expected: >0 rows

-- Q2: Appointment query with JOIN
SELECT COUNT(*) FROM appointment a 
JOIN patient p ON a.patient_id = p.patient_id;
-- Expected: consistent row count

-- Q3: Provider schedule
SELECT COUNT(*) FROM appointment WHERE provider_id IS NOT NULL;
-- Expected: >0 rows

-- Q4: Write operation (INSERT + rollback)
BEGIN;
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary) 
VALUES ('SMOKE-TEST-001', 'Test', 'User', '2000-01-01', 'M', '555-0000');
SELECT COUNT(*) FROM patient WHERE mrn = 'SMOKE-TEST-001';
-- Expected: 1 row inserted
ROLLBACK;
SELECT COUNT(*) FROM patient WHERE mrn = 'SMOKE-TEST-001';
-- Expected: 0 rows after rollback

-- Q5: Constraint validation
INSERT INTO appointment (patient_id, provider_id, clinic_id, appointment_type_id, 
  scheduled_start_time, scheduled_end_time, appointment_status)
VALUES (99999, 1, 1, 1, NOW(), NOW(), 'scheduled');
-- Expected: FK constraint error (patient_id 99999 doesn't exist)
```

**Success Metrics:**
- [ ] All 5+ smoke queries pass
- [ ] Write operation and rollback working
- [ ] Constraint violations detected correctly
- [ ] Total execution <5 seconds
- [ ] 0 false alarms

**Definition of Done:**
- [ ] Smoke query suite implemented
- [ ] All queries tested and passing
- [ ] Integrated into post-deploy workflow
- [ ] Alerts configured for failures
- [ ] Ready for GOV-1

---

### CATEGORY D: Governance and Audit Tasks (8 pts)

#### GOV-1: Approval Checkpoint Controls (3 pts)
**Objective:** Record approver identity, time, and rationale before production migration execution

**Inputs:**
- PIPE-2 production promotion workflow
- GitHub/Azure DevOps approval infrastructure
- Audit logging system

**Outputs:**
- [ ] Approval gate implementation in CI/CD
- [ ] Approval data schema (approver, timestamp, rationale)
- [ ] Approval audit trail
- [ ] Least-privilege execution verification

**Acceptance Criteria:**
- [ ] Manual approval required for production migrations
- [ ] Approver identity and timestamp recorded
- [ ] Approval rationale/comments captured
- [ ] Approval valid only for 24 hours (expires)
- [ ] Least-privilege: Only DBAs/platform-eng can approve

**Approval Workflow:**
```
1. Pull request created: Migration V005 (add_new_index)
2. CI/CD runs: Linting, validation checks (PASS)
3. PR review required: 2 approvals from [dba-team, platform-eng]
4. Approval gates:
   - GitHub: At least 1 approval from codeowners
   - Azure DevOps: Manual approval from platform-eng
5. Post-approval:
   - Record: {approver: alice-smith, timestamp: 2026-06-22T15:30:00Z, rationale: "Index needed for Q2 reports"}
   - Approval expires after 24 hours
6. Deployment authorized only with valid approval

Step 1: PR opened → Awaiting approval
Step 2: Approver reviews → Checks for safety gate violations
Step 3: If SAFE → Approver comments "Approved for deployment" + reasons
Step 4: Post-deployment verification confirms migration applied
Step 5: Approval record archived in audit log
```

**Least-Privilege Enforcement:**
```
Approval Permissions:
- Developer: Create PR ✅, Approve own PR ❌
- Platform-Eng: Approve prod migrations ✅, Execute migrations ✅
- DBA: Execute migrations ✅, Approve prod migrations ✅
- On-Call: Emergency rollback only ⚠️ (limited approval)
```

**Success Metrics:**
- [ ] All production migrations have approval record
- [ ] Approver identity always captured
- [ ] Approval timestamps in ISO 8601 format
- [ ] 0 migrations deployed without approval
- [ ] Approval audit trail immutable

**Definition of Done:**
- [ ] Approval gates configured
- [ ] Audit schema designed and implemented
- [ ] Least-privilege roles enforced
- [ ] Tested with sample migration
- [ ] Ready for AUDIT-1

---

#### AUDIT-1: Execution Logging and Traceability (3 pts)
**Objective:** Persist migration execution logs with versions, duration, status, and compliance retention

**Inputs:**
- GOV-1 approval infrastructure
- Migration framework metadata
- SIEM/logging infrastructure

**Outputs:**
- [ ] Migration execution log schema
- [ ] Structured logging implementation
- [ ] Log retention policy (7-year production, 90-day dev)
- [ ] SIEM integration (Splunk, ELK, CloudWatch)

**Acceptance Criteria:**
- [ ] All migrations logged with: version, timestamp, duration, status, approver
- [ ] Log entries immutable (cannot be modified after creation)
- [ ] Logs retained per compliance policy (7 years prod, 90 days dev)
- [ ] Query-able audit trail (search by version, approver, date range)
- [ ] Integration with SIEM for alerting

**Migration Execution Log Schema:**
```sql
CREATE TABLE migration_execution_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  migration_version VARCHAR(50) NOT NULL,        -- V001__create_tables
  migration_type ENUM('forward', 'rollback'),
  execution_status ENUM('success', 'failure', 'rollback'),
  started_at DATETIME NOT NULL,
  completed_at DATETIME,
  duration_seconds INT,
  approver_id VARCHAR(100),                      -- alice-smith
  approval_timestamp DATETIME,
  deployment_environment VARCHAR(50),            -- dev, staging, prod
  executed_by VARCHAR(100),                      -- operator/ci-service
  script_checksum VARCHAR(64),                   -- SHA256 hash
  error_message TEXT,                            -- if failure
  rollback_reason TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE INDEX idx_version_env (migration_version, deployment_environment),
  INDEX idx_approver (approver_id),
  INDEX idx_executed_at (executed_at)
) ENGINE=InnoDB;
```

**Structured Log Example:**
```json
{
  "log_id": 1001,
  "migration_version": "V005__add_patient_indexes",
  "migration_type": "forward",
  "execution_status": "success",
  "started_at": "2026-06-22T14:30:00Z",
  "completed_at": "2026-06-22T14:30:45Z",
  "duration_seconds": 45,
  "approver_id": "alice-smith",
  "approval_timestamp": "2026-06-22T14:25:00Z",
  "deployment_environment": "prod",
  "executed_by": "ci-service-account",
  "script_checksum": "abc123def456...",
  "error_message": null,
  "created_at": "2026-06-22T14:30:00Z"
}
```

**SIEM Integration (Splunk Example):**
```
sourcetype=migration_log 
| stats count by execution_status
| timechart count by deployment_environment

Alert: If any migration fails in production
  sourcetype=migration_log deployment_environment=prod execution_status=failure
  | alert("Production Migration Failure", on_call)
```

**Log Retention Policy:**
- Production: 7 years (compliance requirement)
- Staging: 1 year
- Development: 90 days (automatic cleanup)

**Success Metrics:**
- [ ] All migrations have execution log entries
- [ ] Logs queryable and immutable
- [ ] SIEM integration working
- [ ] 0 orphaned log entries
- [ ] Retention policy automated

**Definition of Done:**
- [ ] Log schema implemented
- [ ] Structured logging integrated
- [ ] SIEM integration configured
- [ ] Retention policy automated
- [ ] Tested with sample migrations
- [ ] Ready for DOC-1

---

#### DOC-1: Migration and Rollback Runbook (2 pts)
**Objective:** Document pre-checks, execution steps, rollback path, and verification procedures

**Inputs:**
- All SAFE, VERIFY, GOV, AUDIT components
- Emergency rollback procedures from RB-3
- Operational runbook template

**Outputs:**
- [ ] Pre-flight checks documented (5+ items)
- [ ] Step-by-step execution procedure
- [ ] Rollback decision tree
- [ ] Verification checklist
- [ ] Troubleshooting guide

**Acceptance Criteria:**
- [ ] Pre-deployment checklist (backup verified, locks released, etc.)
- [ ] Execution steps clear and sequential
- [ ] Rollback decision tree for various failure scenarios
- [ ] Post-deployment verification steps
- [ ] Troubleshooting guide for 8+ common issues

**Migration Runbook Structure:**

```markdown
## 1. Pre-Deployment Checks (15 minutes)
- [ ] Backup verified and recent (< 1 hour old)
- [ ] No active locks on database tables (SHOW OPEN TABLES WHERE ...)
- [ ] Sufficient disk space (>500GB free)
- [ ] Network connectivity to database stable
- [ ] Approval obtained and valid (< 24 hours old)
- [ ] Dry-run migration completed successfully on staging
- [ ] Rollback script exists and tested
- [ ] On-call team notified

## 2. Execution Steps (5 minutes)
1. Connect to production database
2. Run migration: ./scripts/migrate.sh --environment prod --version V005
3. Monitor: Watch migration logs in real-time
4. Verification: Run smoke query suite
5. Confirm: Schema checksum matches expected

## 3. Rollback Decision Tree
If migration succeeds:
  → Go to "Post-Deployment Verification"
  
If migration fails but rollback executed:
  → Verify schema returned to previous version
  → Verify smoke queries pass
  → File incident and notify on-call
  
If migration fails and rollback fails:
  → CRITICAL: Database may be in inconsistent state
  → Execute emergency procedures (call DBA)
  → Consider point-in-time recovery

## 4. Post-Deployment Verification
- [ ] Schema version matches V005
- [ ] All expected tables, columns, indexes present
- [ ] Smoke queries all pass (5/5)
- [ ] No errors in migration logs
- [ ] Approver notified: Migration successful

## 5. Troubleshooting

| Error | Cause | Resolution |
|-------|-------|-----------|
| FK constraint violation | Foreign key references invalid | Check dependent records exist |
| Disk full mid-migration | Insufficient space | Free disk space and retry |
| Lock timeout | Table locked by other query | Identify long-running query, kill if needed |
| Connection lost | Network interruption | Retry migration (idempotent) |
| Checksum mismatch | Migration didn't apply correctly | Manual inspection + rollback + retry |
| Rollback failed | Undo script has errors | Execute rollback manually, file bug |
| Smoke query fails | Data integrity issue | Investigate data, possible rollback |
| Approval expired | >24 hours since approval | Get new approval, retry migration |
```

**Success Metrics:**
- [ ] Runbook clear and actionable for operators
- [ ] All steps tested and validated
- [ ] Troubleshooting guide covers 8+ scenarios
- [ ] Pre-checks reduce deployment failures by >80%

**Definition of Done:**
- [ ] Runbook documented
- [ ] Decision trees reviewed
- [ ] Troubleshooting guide complete
- [ ] Tested with operational team
- [ ] Ready for QA-1 through QA-6

---

### CATEGORY E: Testing and Validation Tasks (6 pts)

#### QA-1: Ordered Execution Validation (1 pt)
**Objective:** Validate versioned scripts execute in strict numerical order via CI/CD

**Test Procedures:**
- [ ] Deploy 10+ migrations in sequence, verify order
- [ ] Attempt out-of-order deployment (should fail)
- [ ] Verify metadata table shows correct execution order
- [ ] Test dry-run mode shows correct order

---

#### QA-2: Rollback Recovery Validation (1 pt)
**Objective:** Validate rollback returns schema to previous known-good state

**Test Procedures:**
- [ ] Apply migration V005 (schema changes)
- [ ] Execute rollback to V004
- [ ] Verify schema checksum matches V004 baseline
- [ ] Verify no residual data from V005
- [ ] Test with 5+ different rollback scenarios

---

#### QA-3: Safety Gate Validation (1 pt)
**Objective:** Validate unsafe migrations are blocked according to policy

**Test Procedures:**
- [ ] Create migration that violates LNT-001 (naming) → Should block
- [ ] Create migration with DROP without IF EXISTS → Should warn
- [ ] Create migration with hardcoded value → Should block
- [ ] Verify SAFE-2 expand-and-contract enforced
- [ ] Test exemption policy works correctly

---

#### QA-4: Post-Deploy Verification Validation (1 pt)
**Objective:** Validate checksum/version and smoke query checks execute and gate release

**Test Procedures:**
- [ ] After migration, checksum validation passes
- [ ] Introduce checksum mismatch → Verification fails
- [ ] Run smoke query suite → All 5+ queries pass
- [ ] Corrupt data → Smoke query fails, blocks release
- [ ] Verify verification <10 seconds

---

#### QA-5: Approval and Audit Validation (1 pt)
**Objective:** Validate production approvals and logs captured end-to-end

**Test Procedures:**
- [ ] Deploy migration without approval → Blocked
- [ ] Deploy with approval → Succeeds and logged
- [ ] Verify audit log contains: approver, timestamp, rationale
- [ ] Query audit trail → All records immutable
- [ ] Verify SIEM integration receives log entries

---

#### QA-6: Runbook Drill Validation (1 pt)
**Objective:** Execute runbook drill and verify operator actions are actionable

**Test Procedures:**
- [ ] Operator follows runbook from start to finish
- [ ] All pre-checks executable and clear
- [ ] Migration executes per runbook steps
- [ ] Rollback decision tree understood
- [ ] Post-deployment verification completed
- [ ] Troubleshooting guide helpful for actual issue

---

## 4. Execution Order (Suggested)

```
Phase 1: Pipeline Infrastructure (Days 1-2)
  1. PIPE-1: Framework integration
  2. PIPE-2: Environment promotion workflow

Phase 2: Rollback Infrastructure (Days 3-4)
  3. RB-1: Paired forward/backward scripts
  4. RB-2: Non-prod rollback automation
  5. RB-3: Emergency rollback procedure

Phase 3: Safety & Validation (Days 5-7)
  6. SAFE-1: Migration lint checks
  7. SAFE-2: Expand-and-contract guardrails
  8. VERIFY-1: Post-deploy schema verification
  9. VERIFY-2: Smoke query verification

Phase 4: Governance & Audit (Days 8-9)
  10. GOV-1: Approval checkpoints
  11. AUDIT-1: Execution logging
  12. DOC-1: Migration runbook

Phase 5: Testing & Validation (Days 10-11)
  13. QA-1 through QA-6: All validation tests (run in parallel)
```

---

## 5. Definition of Done

### Must-Have (Blocking)
- [ ] Versioned migrations execute in strict order (PIPE-1, PIPE-2)
- [ ] Rollback restores previous version (RB-1, RB-2, RB-3)
- [ ] Safety checks block unsafe operations (SAFE-1, SAFE-2)
- [ ] Post-deploy verification validates integrity (VERIFY-1, VERIFY-2)
- [ ] Production approvals recorded (GOV-1)
- [ ] Execution logs persisted and auditable (AUDIT-1)
- [ ] Runbook documented and tested (DOC-1)
- [ ] All QA tests passing (QA-1 through QA-6)

### Should-Have (High Priority)
- [ ] Emergency rollback procedure tested with operator
- [ ] Rehearsal automation running weekly
- [ ] SIEM integration functional
- [ ] Checksum validation <10 seconds
- [ ] All pre-checks automated

### Nice-to-Have
- [ ] Rollback approval workflow (separate from promotion)
- [ ] Canary deployment strategy (deploy to 1 replica first)
- [ ] Automated rollback on smoke query failure
- [ ] Cost tracking per migration
- [ ] Migration execution dashboard

---

## 6. Success Criteria

| Metric | Target | Measurement |
|---|---|---|
| **Ordered Execution** | 100% success rate | QA-1 test results |
| **Rollback Success** | >99% success rate | RB-2 rehearsal logs |
| **Safety Gate Coverage** | 100% policy compliance | SAFE-1 lint results |
| **Approval Rate** | 100% for prod | GOV-1 audit log |
| **Audit Trail** | 100% traceability | AUDIT-1 log completeness |
| **Smoke Query Pass** | 100% success | VERIFY-2 test results |
| **Verification Speed** | <10 seconds | VERIFY-1 execution time |

---

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Migration blocks table locks | HIGH | Add timeout logic, test with concurrent load |
| Rollback takes too long (>5min) | HIGH | Optimize rollback scripts, test duration |
| Checksum mismatch false positive | MEDIUM | Capture baseline before first migration |
| Approval workflow blocks emergency | HIGH | Emergency rollback path bypasses approval |
| Audit logs become too large | MEDIUM | Implement log archival and cleanup |
| Safety checks cause false negatives | MEDIUM | Tune lint rules, track exemptions |

---

## 8. Related Documents

**Parent User Story:**
- [US-105: Migration and Rollback Pipeline](us_105.md)

**Dependent Tasks:**
- TASK-104: Production Schema and Index Strategy (baseline schema)

**Reference Standards:**
- CI/CD Pipeline Standards: `.github/instructions/cicd-pipeline-standards.instructions.md`
- Database Standards: `.github/instructions/database-standards.instructions.md`
- Security Standards: `.github/instructions/security-standards-owasp.instructions.md`

---

## 9. Task Status Dashboard

| Subtask | Points | Owner | Status | % Complete |
|---|---|---|---|---|
| PIPE-1 | 7 | TBD | Planned | 0% |
| PIPE-2 | 7 | TBD | Planned | 0% |
| RB-1 | 4 | TBD | Planned | 0% |
| RB-2 | 4 | TBD | Planned | 0% |
| RB-3 | 4 | TBD | Planned | 0% |
| SAFE-1 | 5 | TBD | Planned | 0% |
| SAFE-2 | 5 | TBD | Planned | 0% |
| VERIFY-1 | 3 | TBD | Planned | 0% |
| VERIFY-2 | 3 | TBD | Planned | 0% |
| GOV-1 | 3 | TBD | Planned | 0% |
| AUDIT-1 | 3 | TBD | Planned | 0% |
| DOC-1 | 2 | TBD | Planned | 0% |
| QA-1 thru QA-6 | 6 | TBD | Planned | 0% |
| **TOTAL** | **56** | | **READY** | **0%** |

---

**Next:** Begin PIPE-1 task (Migration Framework Integration)
