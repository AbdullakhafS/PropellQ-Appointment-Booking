# TASK-105 Remaining Subtasks: RB, SAFE, VERIFY, GOV, AUDIT, DOC, QA

This file consolidates specifications for the remaining 11 subtasks to complete TASK-105 implementation.

---

## RB-1: Paired Forward/Backward Script Policy

**Task ID:** RB-1 | **Points:** 4 | **Parent:** TASK-105

### Objective
Enforce the requirement that every forward migration (V###) has a corresponding rollback script (U###) with validation that both scripts are syntactically correct and logically complementary.

### Key Deliverables
- [ ] Policy document defining paired script requirements
- [ ] Rollback script templates for common scenarios (CREATE/DROP, ADD/REMOVE, ALTER/REVERT)
- [ ] CI/CD validation rules that block migrations without paired rollback scripts
- [ ] Test cases validating rollback script correctness

### Acceptance Criteria
- Every V### migration has corresponding U### script ✅
- Rollback scripts validated for SQL syntax correctness ✅
- Rollback logic reverses forward migration (idempotent) ✅
- Compensating transaction pattern used when true rollback not possible ✅
- CI/CD blocks missing rollback scripts (hard stop) ✅
- 100% of prod migrations have validated rollback path ✅

### Implementation Pattern

**CI/CD Validation Rule:**
```bash
# .github/workflows/migration-validation.yml
for forward_file in db/migrations/V*.sql; do
  version=$(echo $forward_file | grep -oE 'V[0-9]{3}')
  rollback_file="db/migrations/U${version:1}__*.sql"
  
  if ! ls $rollback_file 2>/dev/null | grep -q .; then
    echo "❌ BLOCKED: No rollback script for $forward_file"
    exit 1  # Hard stop - fail CI/CD
  fi
  
  # Validate syntax
  mysql --syntax-check $rollback_file || exit 1
done
```

---

## RB-2: Non-Prod Rollback Rehearsal Automation

**Task ID:** RB-2 | **Points:** 4 | **Parent:** TASK-105

### Objective
Automate weekly rollback rehearsals in staging/test environments with failure injection, automatic rollback trigger validation, and schema state verification.

### Key Deliverables
- [ ] Rollback rehearsal automation script (weekly schedule)
- [ ] Failure injection mechanisms (4+ scenarios: constraint violation, disk full, timeout, lock contention)
- [ ] Automated rollback trigger and validation
- [ ] Success/failure reporting with schema checksum comparison

### Acceptance Criteria
- Weekly automation runs successfully ✅
- Failures detected and rollback triggered automatically ✅
- Schema checksum before/after rollback matches (validates idempotency) ✅
- Rehearsal completes in <10 minutes ✅
- 0 false positives (false rollbacks) ✅
- Rehearsal report emailed to team weekly ✅

### Failure Scenarios to Simulate
1. **Constraint Violation:** Insert duplicate key → FK violation → trigger rollback
2. **Disk Full:** Fill disk during migration → timeout → automatic rollback
3. **Connection Loss:** Disconnect mid-migration → auto-reconnect with rollback
4. **Lock Timeout:** Long-running query blocking migration → timeout → rollback

---

## RB-3: Emergency Rollback Procedure

**Task ID:** RB-3 | **Points:** 4 | **Parent:** TASK-105

### Objective
Implement operator-initiated emergency rollback with interactive safety prompts, preflight validation, and automatic incident notifications.

### Key Deliverables
- [ ] Emergency rollback CLI script with interactive prompts
- [ ] 3-step confirmation workflow (operator ID, reason, ROLLBACK confirmation)
- [ ] Automatic backup verification before execution
- [ ] Preflight checklist automation
- [ ] Automatic incident ticket creation + Slack notification

### Acceptance Criteria
- Operator can initiate rollback via CLI ✅
- Multi-step confirmation prevents accidental rollback ✅
- Preflight checks validate: backup exists, no locks, disk space ✅
- Rollback completes in <5 minutes ✅
- All actions logged with operator ID ✅
- Incident auto-filed on Slack/PagerDuty ✅

### Interactive Rollback Script
```bash
#!/bin/bash
# ./scripts/emergency-rollback.sh <target-version>

echo "⚠️  EMERGENCY ROLLBACK INITIATED"
read -p "Enter operator ID for audit trail: " operator_id
read -p "Reason for rollback: " reason

# Preflight checks
check_backup_exists
check_no_locks
check_disk_space

# Confirmation
echo "Type 'ROLLBACK-V004' to confirm: "
read confirmation
if [ "$confirmation" != "ROLLBACK-V004" ]; then
  echo "❌ Rollback cancelled"
  exit 1
fi

# Execute rollback
mvn flyway:migrate -Dflyway.target=$target_version

# File incident
INCIDENT=$(curl -X POST https://slack.com/api/chat.postMessage \
  -d "text=🔔 Emergency Rollback: V004 by $operator_id - $reason")

echo "✅ Rollback complete. Incident #$INCIDENT created."
```

---

## SAFE-1: Migration Lint and Policy Checks

**Task ID:** SAFE-1 | **Points:** 5 | **Parent:** TASK-105

### Objective
Implement automated linter with 10+ policy rules to detect unsafe migration patterns, naming violations, and anti-patterns.

### Lint Rules (Enforced)
1. **LNT-001:** Naming Convention - V\d{3}__description.sql pattern (BLOCK)
2. **LNT-002:** No DROP without IF EXISTS (WARN)
3. **LNT-003:** Idempotency hints (IF EXISTS required) (WARN)
4. **LNT-004:** No hardcoded values (BLOCK)
5. **LNT-005:** Migration size limit (<100 statements) (WARN)
6. **LNT-006:** SQL syntax validation (BLOCK)
7. **LNT-007:** Documentation header required (BLOCK)
8. **LNT-008:** Transaction safety (auto-wrap) (INFO)
9. **LNT-009:** Performance impact on large tables (WARN)
10. **LNT-010:** Constraint safety (FK restrictions) (INFO)

### Acceptance Criteria
- All 10+ lint rules implemented and tested ✅
- ERROR rules block CI/CD, WARN rules logged ✅
- Lint execution <5 seconds for 100 migrations ✅
- Exemption mechanism available (propel-lint-disable) ✅
- 0 false positives on validated migrations ✅

---

## SAFE-2: Expand-and-Contract Guardrails

**Task ID:** SAFE-2 | **Points:** 5 | **Parent:** TASK-105

### Objective
Detect breaking change patterns and enforce expand-and-contract migration sequencing with backward-compatible contract windows.

### Breaking Changes Detected
- Direct column removal (BLOCKED unless 2+ versions passed)
- Column type changes (must use expand-and-contract)
- NOT NULL addition without default (BLOCKED)
- Unique constraint addition on nullable column (BLOCKED)
- Foreign key removal (BLOCKED without impact analysis)

### Expand-and-Contract Pattern
```
V001: Add new_column_v2 (parallel to old_column)
V002: Migrate data (old_column → new_column_v2)
V003+: Update services to use new_column_v2
V004+: Remove old_column (after 2-version window)
```

### Acceptance Criteria
- Breaking changes detected and blocked ✅
- 2-version contract window enforced ✅
- Service compatibility validated ✅
- Migration dependency tracking ✅
- 0 direct column removals in prod ✅

---

## VERIFY-1: Post-Deploy Schema Verification

**Task ID:** VERIFY-1 | **Points:** 3 | **Parent:** TASK-105

### Objective
Validate schema integrity, checksum match, and structural completeness after migration deployment.

### Verification Checks
1. Schema checksum matches expected (SHA256)
2. Table count matches baseline (10 tables expected)
3. Column count per table correct
4. Index count correct (13-15 indexes)
5. Constraint count correct (15+ FK constraints)
6. Data integrity checks (no orphaned records)

### Acceptance Criteria
- 100% checksum match post-deployment ✅
- Structural validation 0 mismatches ✅
- Verification <10 seconds ✅
- All checks pass before marking deployment complete ✅

---

## VERIFY-2: Smoke Query Verification

**Task ID:** VERIFY-2 | **Points:** 3 | **Parent:** TASK-105

### Objective
Run 5+ critical smoke queries to validate data integrity and basic read/write functionality post-migration.

### Smoke Query Suite
1. SELECT from patient (validates table access)
2. SELECT with JOIN (validates FK relationships)
3. SELECT with WHERE clause (validates indexes)
4. INSERT + ROLLBACK test (validates transactions)
5. Constraint violation test (validates referential integrity)

### Acceptance Criteria
- All 5+ queries execute successfully ✅
- Write operations and rollback work ✅
- Constraint violations caught correctly ✅
- Total execution <5 seconds ✅
- No data corruption detected ✅

---

## GOV-1: Approval Checkpoint Controls

**Task ID:** GOV-1 | **Points:** 3 | **Parent:** TASK-105

### Objective
Record approver identity, timestamp, and rationale for all production migrations with least-privilege access control.

### Approval Workflow
1. PR created with migration V###
2. Code review required (2 approvals)
3. Approvers leave rationale comments
4. Approval recorded: {approver, timestamp, rationale}
5. Approval valid for 24 hours
6. Deployment authorized only with valid approval

### Acceptance Criteria
- Manual approval required for prod ✅
- Approver identity always captured ✅
- Timestamp in ISO 8601 format ✅
- Approval audit trail immutable ✅
- Approval expires after 24 hours ✅
- Least-privilege: Only DBAs/Platform-Eng approve ✅

---

## AUDIT-1: Execution Logging and Traceability

**Task ID:** AUDIT-1 | **Points:** 3 | **Parent:** TASK-105

### Objective
Persist immutable migration execution logs with compliance retention policies for auditability and troubleshooting.

### Log Schema
```
migration_execution_log (
  log_id, version, type, status, started_at, completed_at,
  duration_seconds, approver_id, approver_timestamp,
  environment, executed_by, script_checksum,
  error_message, rollback_reason, created_at
)
```

### Retention Policy
- Production: 7 years (compliance)
- Staging: 1 year
- Development: 90 days (auto-cleanup)

### Acceptance Criteria
- All migrations logged with execution metadata ✅
- Log entries immutable ✅
- Logs queryable by version/approver/date ✅
- SIEM integration working ✅
- Retention policy automated ✅

---

## DOC-1: Migration and Rollback Runbook

**Task ID:** DOC-1 | **Points:** 2 | **Parent:** TASK-105

### Objective
Document pre-checks, execution steps, rollback decision tree, and troubleshooting procedures for operators.

### Runbook Sections
1. **Pre-Deployment Checks** (15 min: backup, locks, disk space, approval)
2. **Execution Steps** (5 min: run migration, monitor, verify)
3. **Rollback Decision Tree** (success → verify; failure → decide rollback)
4. **Post-Deployment Verification** (checksum, smoke queries, confirmation)
5. **Troubleshooting Guide** (FK violations, disk full, locks, timeouts, etc.)

### Acceptance Criteria
- Pre-checks documented and automated ✅
- Execution steps clear and sequential ✅
- Rollback decision tree covers all scenarios ✅
- Troubleshooting guide covers 8+ common issues ✅
- Runbook tested with operators ✅

---

## QA-1 through QA-6: Testing and Validation

**Task ID:** QA-1 to QA-6 | **Points:** 6 total (1 pt each) | **Parent:** TASK-105

### QA-1: Ordered Execution Validation (1 pt)
**Test:** Deploy 10+ migrations → Verify order → Attempt out-of-order (fail)  
**Success Criteria:** 100% success rate, ordered execution confirmed

### QA-2: Rollback Recovery Validation (1 pt)
**Test:** Apply V005 → Rollback to V004 → Verify schema checksum matches  
**Success Criteria:** Schema returns to previous state, 0 data loss

### QA-3: Safety Gate Validation (1 pt)
**Test:** Create invalid migration (naming error, hardcoded value) → CI/CD blocks  
**Success Criteria:** 100% of unsafe migrations blocked

### QA-4: Post-Deploy Verification Validation (1 pt)
**Test:** Post-deploy checks execute → Checksum validates → Smoke queries pass  
**Success Criteria:** 100% verification pass rate, <10 sec execution

### QA-5: Approval and Audit Validation (1 pt)
**Test:** Deploy without approval → Blocked; Deploy with approval → Logged  
**Success Criteria:** 100% audited, approval records immutable

### QA-6: Runbook Drill Validation (1 pt)
**Test:** Operator follows runbook end-to-end in staging  
**Success Criteria:** All steps executable, clear, documented, successful

---

## Execution Summary

**Recommended Completion Sequence:**
1. PIPE-1 → PIPE-2 (infrastructure foundation)
2. RB-1 → RB-2 → RB-3 (rollback capabilities)
3. SAFE-1 → SAFE-2 (safety guardrails)
4. VERIFY-1 → VERIFY-2 (validation post-deploy)
5. GOV-1 → AUDIT-1 → DOC-1 (governance & documentation)
6. QA-1 through QA-6 (parallel testing)

**Total Effort:** 10-12 dev days for complete implementation  
**Success Metric:** All 6 acceptance criteria met + all QA tests passing
