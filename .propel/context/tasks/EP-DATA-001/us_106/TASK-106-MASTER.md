# TASK-106: Implement Retention and Archive Lifecycle Jobs

**Master Task Breakdown Document**

**Status:** Specification Phase  
**Total Subtasks:** 11 core + 6 QA  
**Total Story Points:** 48  
**Estimated Effort:** 5-7 dev days + compliance validation  
**Created:** 2026-06-22

---

## 1. Executive Summary

TASK-106 implements policy-driven data lifecycle automation for retention, archival, and purging of regulated datasets. The solution enforces immutable retention windows, legal-hold compliance, automated job orchestration with retry/alerting, and provides authorized retrieval paths with comprehensive audit trails.

**Key Challenges:**
- Balancing automation with regulatory compliance
- Handling edge cases (legal holds, timezone boundaries, large datasets)
- Preventing accidental data loss while enabling policy-driven destruction
- Maintaining audit trail integrity throughout lifecycle transitions
- Coordinating across multiple systems and compliance domains

**Success Definition:**
- Records transition to archive/purge states correctly per policy windows
- Immutable retention blocks premature deletion
- Legal-hold records excluded from purge with logged exceptions
- Job failures trigger alerts and retries without data loss
- Archive retrieval path is documented, verified, and access-controlled
- Execution reports available for compliance review with policy versions

---

## 2. Acceptance Criteria Mapping

| AC ID | Criterion | Implementation Tasks | Validation |
|-------|-----------|---|---|
| **AC-1** | Records transition to archive/purge state by policy windows | LIFE-1, LIFE-2, QA-1 | Schedule boundary testing, timezone validation, idempotency |
| **AC-2** | Immutable retention blocks early deletion and emits policy violations | IMM-1, OPS-1, QA-2 | Delete attempt testing, violation event validation, audit logging |
| **AC-3** | Legal-hold records excluded from purge, exceptions logged | HOLD-1, AUDIT-1, QA-3 | Hold marker testing, purge exclusion, exception log validation |
| **AC-4** | Job failures trigger alerts and retries with exponential backoff | OPS-1, OPS-2, QA-4 | Failure injection, retry count validation, alert verification |
| **AC-5** | Authorized archive retrieval path documented and verifiable | RETR-1, DOC-1, QA-5 | Access control testing, audit logging, retrieval success validation |
| **AC-6** | Lifecycle execution reports and policy versions available | REPORT-1, GOV-1, QA-6 | Report generation, version tracking, export format validation |

---

## 3. Subtasks Overview

### Phase 1: Lifecycle Engine Foundation (LIFE-1, LIFE-2) - 9 pts

**Objective:** Build core policy evaluation and job orchestration engine

#### LIFE-1: Policy Model and Schedule Framework (5 pts)
- **Purpose:** Define policy schema by domain, retention window, action type; implement timezone-aware schedule evaluation
- **Key Components:**
  - Policy schema: domain, retention_days, archive_action, purge_action, enabled, effective_date, owner
  - Schedule evaluation: cron-based or date-boundary based evaluation
  - State machines: Operational → Archived → Purged (with Legal-Hold bypass)
  - Timezone-safe date boundary handling (UTC normalization)
  - Replay safety and idempotency guarantees
- **Inputs:** Compliance requirements, data domain definitions, timezone handling strategy
- **Outputs:** 
  - Policy evaluation engine (code)
  - Policy configuration schema (JSON/YAML)
  - Test cases for boundary conditions
- **Success Metrics:** 100% of policies evaluated correctly, replay-safe state transitions, <100ms evaluation per 100 policies

#### LIFE-2: Archive and Purge Job Orchestration (4 pts)
- **Purpose:** Implement archive/purge job execution with dry-run mode and state tracking
- **Key Components:**
  - Archive job: Move data to cold storage (S3 Glacier, Archive Storage) with retention metadata
  - Purge job: Delete data from warm storage after immutable retention expires
  - Dry-run mode: Preview destructive operations without applying changes
  - Job state tracking: pending → running → completed/failed
  - Orchestrator pattern: Handle job dependencies and ordering
  - Compensating transactions for failed operations
- **Inputs:** LIFE-1 policy engine, scheduler/orchestrator infrastructure
- **Outputs:**
  - Archive job implementation
  - Purge job implementation
  - Dry-run validation reports
  - Job state schema
- **Success Metrics:** Archive throughput >10MB/s, purge throughput >1000 records/s, 100% dry-run accuracy

---

### Phase 2: Compliance Controls (IMM-1, HOLD-1, GOV-1) - 10 pts

**Objective:** Enforce immutable retention, legal holds, and policy governance

#### IMM-1: Immutable Retention Enforcement (3 pts)
- **Purpose:** Block delete operations before immutable retention expiry with policy violation events
- **Key Components:**
  - Retention window enforcement: Block deletes where current_date < retention_expiry
  - Policy violation events: Emit structured events for compliance monitoring
  - Audit logging: Record all delete attempts with reason, operator, timestamp
  - Immutable retention marker: Store retention_expiry with data, cannot be modified
  - Compliance reporting: Track and report policy violations
- **Inputs:** LIFE-1 policy model, data schema with retention metadata
- **Outputs:**
  - Enforcement logic (code)
  - Policy violation event schema
  - Audit log schema (retention_enforcement table)
- **Success Metrics:** 100% delete attempts evaluated, <1ms enforcement overhead, 0 unauthorized deletions

#### HOLD-1: Legal-Hold Exclusion Controls (3 pts)
- **Purpose:** Exclude legal-hold records from purge, produce hold exception logs
- **Key Components:**
  - Legal-hold marker: Flag on records indicating active legal hold
  - Hold query integration: Exclude held records from purge job scope
  - Hold exception logging: Record attempted purge of held records
  - Hold metadata: hold_id, hold_reason, hold_placed_by, hold_placed_at, hold_expires_at
  - Hold audit: Track hold lifecycle (placed, maintained, released)
- **Inputs:** HOLD-1 schema, LIFE-2 purge job, compliance control model
- **Outputs:**
  - Hold evaluation logic (code)
  - Hold schema and markers
  - Exception log table
  - Hold audit trail
- **Success Metrics:** 100% of held records excluded, 0 held records purged, all hold exceptions logged

#### GOV-1: Policy Versioning and Change Control (4 pts)
- **Purpose:** Version retention policies with effective dates, ownership, and approval workflow
- **Key Components:**
  - Policy versioning: version_number, effective_date, superseded_date, owner_id, approved_by
  - Backward compatibility: Existing records respect policy version that was active at creation
  - Change approval workflow: Policy changes require approval from compliance officer
  - Policy change audit trail: Track all changes, approvals, effective dates
  - Rollback capability: Revert to previous policy version with recorded rationale
  - Impact analysis: Show which records affected by policy change
- **Inputs:** Policy change workflow requirements, compliance approval model
- **Outputs:**
  - Policy versioning schema
  - Change approval workflow
  - Audit trail table
  - Impact analysis queries
- **Success Metrics:** 100% of policy changes tracked and approved, backward compatibility maintained, 0 unapproved policy changes in production

---

### Phase 3: Operations and Reliability (OPS-1, OPS-2) - 10 pts

**Objective:** Ensure job reliability, observability, and incident response

#### OPS-1: Monitoring, Retries, and Dead-Letter Handling (5 pts)
- **Purpose:** Instrument job success/failure, configure retries with backoff, handle terminal failures
- **Key Components:**
  - Job metrics: success_count, failure_count, duration, throughput, latency_p50/p95/p99
  - Retry strategy: Exponential backoff (1s, 2s, 4s, 8s, 16s), max 5 attempts
  - Dead-letter queue: Failed jobs routed to DLQ for manual investigation
  - Circuit breaker: Stop retrying after N consecutive failures
  - Backoff jitter: Random delay to prevent thundering herd
  - Job state persistence: Track retry attempts and history
  - Monitoring dashboard: Real-time job status, throughput, latency
- **Inputs:** Job execution framework, metrics collection system (CloudWatch, Prometheus, etc.)
- **Outputs:**
  - Retry logic implementation
  - Dead-letter queue schema
  - Metrics schema
  - Monitoring dashboard definition
- **Success Metrics:** <1% permanent failure rate, 95%+ successful first-attempt jobs, <100ms monitoring latency

#### OPS-2: Alerting and Incident Hooks (5 pts)
- **Purpose:** Configure alerts for job failures, backlog growth, and alert integration with runbook links
- **Key Components:**
  - Alert conditions: Job failure (>10 failures in 1 hour), backlog growth (>1M records), repeated failures (>3 consecutive)
  - Alert routing: Route to on-call via PagerDuty, Slack notification with severity levels
  - Runbook attachment: Each alert includes link to DOC-1 runbook and troubleshooting steps
  - Incident auto-filing: Create Jira/GitHub issue automatically for critical failures
  - Alert suppression: Maintenance windows, known issue suppression
  - Alert metrics: Track alert frequency, false positives, mean-time-to-resolution
- **Inputs:** Alerting infrastructure (PagerDuty, Slack, etc.), runbook system, incident management system
- **Outputs:**
  - Alert definitions (Terraform/YAML)
  - Slack integration
  - PagerDuty integration
  - Incident template
- **Success Metrics:** <5 minute alert latency, <10% false positive rate, <30 minute MTTR

---

### Phase 4: Retrieval and Audit (RETR-1, AUDIT-1, REPORT-1, DOC-1) - 12 pts

**Objective:** Enable authorized retrieval, maintain audit trail, generate compliance evidence

#### RETR-1: Authorized Archive Retrieval Path (3 pts)
- **Purpose:** Define and enforce retrieval workflow for authorized roles with access control
- **Key Components:**
  - Retrieval request workflow: Authorized user (Data Officer, Compliance Officer) submits retrieval request
  - Access control checks: Verify requester role, data domain permissions, legal restrictions
  - Retrieval audit logging: Record who requested what data when, purpose, approval, completion
  - Restore workflow: Restore data from cold storage (S3 Glacier, Archive Storage) to warm storage
  - Restore verification: Verify data integrity post-restore (checksums, record counts)
  - Restore performance: <1 hour for typical retrieval requests
  - Data deletion after retrieval: Controlled deletion of restored data after use
- **Inputs:** LIFE-2 archive job, access control system, audit logging system
- **Outputs:**
  - Retrieval request schema
  - Access control policies
  - Restore workflow (code/script)
  - Retrieval audit table
- **Success Metrics:** 100% of retrievals verified and audited, <1 hour retrieval time, 100% access control enforcement

#### AUDIT-1: Lifecycle Audit Trail (3 pts)
- **Purpose:** Record record-count transitions, exclusions, policy ID, execution metadata for compliance review
- **Key Components:**
  - Lifecycle execution log: version, action (archive/purge), record_count, excluded_count (legal holds), policy_id, execution_operator/system_id, start_time, end_time, status, error_message
  - Transition audit: Before/after record counts, storage locations, data checksums
  - Operator tracking: User ID or service account that triggered job
  - Immutable log: Append-only table, no updates or deletes (except retention-expired entries)
  - Compliance retention: 7 years for prod, 1 year for staging, 90 days for dev
  - Log export: Support export to compliance review systems (Splunk, ELK, etc.)
- **Inputs:** LIFE-2 job results, OPS-1 execution metrics, GOV-1 policy versions
- **Outputs:**
  - Lifecycle execution log schema
  - Immutable log implementation
  - Log export scripts
  - Compliance report queries
- **Success Metrics:** 100% of executions logged, 0 log tampering, <1MB/day log growth per environment

#### REPORT-1: Compliance Evidence Reporting (3 pts)
- **Purpose:** Generate per-run reports with action counts, exceptions, policy versions for compliance review
- **Key Components:**
  - Execution report: Generated after each lifecycle job run
  - Report contents: Execution date/time, policy version, job type (archive/purge), record counts, exception counts, success/failure status
  - Exception summary: Legal holds applied, immutable retention violations, failed records
  - Policy version snapshot: Archive policy version active during execution
  - Export formats: CSV, JSON, PDF for compliance submission
  - Scheduled reports: Daily summary, weekly rollup, monthly compliance audit report
  - Report distribution: Email to compliance officer, store in compliance repository
- **Inputs:** AUDIT-1 execution logs, HOLD-1 hold exceptions, GOV-1 policy versions
- **Outputs:**
  - Report schema
  - Report generation queries
  - Report templates (CSV, JSON, PDF)
  - Scheduled job definitions
- **Success Metrics:** 100% execution coverage, <5 minute report generation, 100% report completeness

#### DOC-1: Lifecycle and Recovery Runbook (3 pts)
- **Purpose:** Document job schedules, failure recovery steps, manual override process, legal-hold handling, and retrieval verification
- **Key Components:**
  - Job schedules: Archive jobs every night 11 PM UTC, purge jobs every Sunday 2 AM UTC
  - Normal operations: Step-by-step guide for running jobs, monitoring, success verification
  - Failure recovery: Diagnosis steps for common failures (timeout, DLQ full, data corrupted), manual remediation
  - Manual override: How to manually run a job, skip a job, restart a failed job
  - Legal-hold management: How to place/release holds, verify hold status, exclude from purge
  - Archive retrieval: How to request archive retrieval, approve request, monitor restore, verify restored data
  - Rollback procedure: How to revert failed archive (restore from backup), revert failed purge (restore from archive)
  - Troubleshooting guide: FAQ for common issues
  - Emergency contacts: On-call DBA, compliance officer, data governance lead
- **Inputs:** All prior tasks (LIFE, IMM, HOLD, GOV, OPS, RETR, AUDIT, REPORT)
- **Outputs:**
  - Runbook markdown document
  - Decision tree diagrams
  - Troubleshooting flowcharts
  - Contact list and escalation procedures
- **Success Metrics:** Runbook tested with operators, <30 minute MTTR for common failures, 100% completeness

---

### Phase 5: Testing and Validation (QA-1 through QA-6) - 6 pts

**Objective:** Validate all acceptance criteria through systematic testing

#### QA-1: Policy Window Transition Validation (1 pt)
- **Testing:** Validate archive/purge transitions across boundary dates and timezones
- **Test Cases:**
  - 30-day retention policy: Create record at T, verify archived at T+30d, not before T+30d
  - Timezone boundary crossing: Test with UTC, PST, IST timezones
  - Daylight saving time: Test transitions during DST change
  - Leap seconds: Verify handling of leap second edge case
  - Manual time advancement: Test with artificial time acceleration
- **Success:** 100% of tests pass, all timezone boundaries validated

#### QA-2: Immutable Retention Validation (1 pt)
- **Testing:** Validate deletion is blocked before immutable retention expiry
- **Test Cases:**
  - Delete before expiry: Attempt delete at T+20d for 30d retention, verify blocked with policy violation
  - Delete at expiry: Delete at exactly T+30d, verify allowed
  - Delete after expiry: Delete at T+35d, verify allowed
  - Policy violation event: Verify event emitted and logged
  - Audit trail: Verify all delete attempts logged with reason and operator
- **Success:** 100% of premature deletes blocked, all violations logged

#### QA-3: Legal-Hold Exclusion Validation (1 pt)
- **Testing:** Validate held records excluded from purge and exceptions logged
- **Test Cases:**
  - Hold placement: Place hold on record, verify marked in system
  - Purge with hold: Run purge job, verify held records excluded
  - Hold exception log: Verify exception entries created for held records
  - Hold release: Release hold, verify record becomes eligible for purge
  - Multiple holds: Multiple holds on same record, verify all must be released before purge
- **Success:** 100% held records excluded, all exceptions logged, 0 held records purged

#### QA-4: Failure and Retry Validation (1 pt)
- **Testing:** Validate retries/backoff under forced job failures and alerting
- **Test Cases:**
  - Transient failure: Simulate DB connection timeout, verify retry succeeds on retry 2
  - Backoff timing: Verify exponential backoff intervals (1s, 2s, 4s, 8s, 16s)
  - Max retries: Force failure on all 5 retries, verify job goes to DLQ
  - Alert trigger: Verify alert emitted on failure
  - Alert routing: Verify Slack notification sent, PagerDuty incident created
  - Runbook link: Verify alert includes runbook link
- **Success:** <100ms backoff latency, 100% alert delivery, <5 minute alert latency

#### QA-5: Archive Retrieval Validation (1 pt)
- **Testing:** Validate authorized retrieval flow and access controls
- **Test Cases:**
  - Authorized retrieval: Data Officer requests archived data, verify approved and restored
  - Unauthorized retrieval: User without permission requests data, verify denied
  - Retrieval audit: Verify all retrievals logged with user, timestamp, purpose
  - Restore success: Verify restored data byte-for-byte identical to original
  - Restore performance: Verify restore completes in <1 hour
  - Restore verification: Verify checksums match, record counts match
- **Success:** 100% of authorized retrievals succeed, 100% of unauthorized retrievals blocked, all audited

#### QA-6: Compliance Evidence Validation (1 pt)
- **Testing:** Validate lifecycle reports include policy versions and execution evidence
- **Test Cases:**
  - Report generation: Run job, verify report generated automatically
  - Report completeness: Verify all required fields in report (date, policy version, counts, exceptions)
  - Policy version capture: Verify policy version active during execution captured
  - Exception summary: Verify hold exceptions and retention violations included
  - Export formats: Verify CSV, JSON, PDF exports all valid
  - Report accuracy: Verify report numbers match actual execution counts
- **Success:** 100% execution reports generated, 100% completeness, all formats export correctly

---

## 4. Execution Order and Dependencies

```
Phase 1: Lifecycle Engine Foundation
├── LIFE-1: Policy Model and Schedule Framework (5 pts)
│   └── Dependency: Compliance requirements defined
│
└── LIFE-2: Archive and Purge Job Orchestration (4 pts)
    └── Dependency: LIFE-1 complete

Phase 2: Compliance Controls (parallel after LIFE-2)
├── IMM-1: Immutable Retention Enforcement (3 pts)
│   └── Dependency: LIFE-1 complete
├── HOLD-1: Legal-Hold Exclusion (3 pts)
│   └── Dependency: LIFE-2 complete
└── GOV-1: Policy Versioning (4 pts)
    └── Dependency: IMM-1 complete

Phase 3: Operations (parallel after compliance controls)
├── OPS-1: Monitoring and Retries (5 pts)
│   └── Dependency: LIFE-2 complete
└── OPS-2: Alerting and Incident (5 pts)
    └── Dependency: OPS-1 complete

Phase 4: Retrieval and Audit (parallel after ops)
├── RETR-1: Authorized Retrieval (3 pts)
├── AUDIT-1: Audit Trail (3 pts)
├── REPORT-1: Compliance Reports (3 pts)
└── DOC-1: Runbook (3 pts)
    └── Dependency: All prior tasks complete

Phase 5: Testing and Validation (final)
└── QA-1 through QA-6 (6 pts parallel)
    └── Dependency: All implementation tasks complete

CRITICAL PATH:
LIFE-1 → LIFE-2 → IMM-1 → GOV-1 → OPS-1 → OPS-2 → RETR-1/AUDIT-1/REPORT-1 → DOC-1 → QA
Estimated: 5-7 days sequential + 3-5 days QA/validation
```

---

## 5. Technical Architecture

### Data Model

```
policies:
  - policy_id (PK)
  - domain (VARCHAR) - "patient", "appointment", "document", etc.
  - policy_name (VARCHAR)
  - retention_days (INT)
  - archive_action (ENUM) - "s3_glacier", "azure_archive", "delete_after_retention"
  - purge_action (ENUM) - "delete", "anonymize"
  - enabled (BOOLEAN)
  - version (INT)
  - effective_date (DATE)
  - superseded_date (DATE)
  - owner_id (VARCHAR)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)

lifecycle_executions:
  - execution_id (PK)
  - policy_id (FK)
  - action_type (ENUM) - "archive", "purge"
  - target_table (VARCHAR)
  - scheduled_date (DATE)
  - started_at (TIMESTAMP)
  - completed_at (TIMESTAMP)
  - status (ENUM) - "pending", "running", "success", "failed"
  - total_records (INT)
  - archived_records (INT)
  - purged_records (INT)
  - excluded_records (INT) -- legal holds
  - error_message (TEXT)
  - executed_by (VARCHAR) -- user or service account
  - created_at (TIMESTAMP)

legal_holds:
  - hold_id (PK)
  - record_id (VARCHAR)
  - table_name (VARCHAR)
  - hold_reason (VARCHAR)
  - hold_placed_by (VARCHAR)
  - hold_placed_at (TIMESTAMP)
  - hold_expires_at (TIMESTAMP NULLABLE)
  - hold_status (ENUM) - "active", "released"
  - released_by (VARCHAR NULLABLE)
  - released_at (TIMESTAMP NULLABLE)
  - created_at (TIMESTAMP)

policy_violations:
  - violation_id (PK)
  - record_id (VARCHAR)
  - table_name (VARCHAR)
  - violation_type (ENUM) - "immature_delete_attempt", "hold_excluded"
  - violation_timestamp (TIMESTAMP)
  - attempted_by (VARCHAR)
  - reason (TEXT)
  - created_at (TIMESTAMP)

archive_metadata:
  - metadata_id (PK)
  - record_id (VARCHAR)
  - table_name (VARCHAR)
  - archive_location (VARCHAR) -- "s3://bucket/prefix/file"
  - archived_at (TIMESTAMP)
  - archive_checksum (VARCHAR)
  - restore_requested (BOOLEAN)
  - restore_location (VARCHAR NULLABLE)
  - restored_at (TIMESTAMP NULLABLE)
  - created_at (TIMESTAMP)
```

### Key Features by Phase

| Phase | Feature | Implementation |
|-------|---------|---|
| **1** | Schedule Evaluation | Cron parser + date boundary logic + UTC normalization |
| **1** | Job Orchestration | State machine + idempotency checks + compensating transactions |
| **2** | Immutable Retention | Delete blocker middleware + violation event emitter |
| **2** | Legal Holds | Query filters + exception logging + hold audit trail |
| **2** | Policy Versioning | Schema versioning + backward compatibility + approval workflow |
| **3** | Monitoring | Metrics collection + dashboard + alerting |
| **3** | Retries | Exponential backoff + circuit breaker + DLQ routing |
| **4** | Retrieval | Access control checks + restore workflow + audit logging |
| **4** | Audit Trail | Immutable log + compliance retention + export |
| **4** | Reports | Report generation + versioning + distribution |
| **5** | Runbook | Documentation + troubleshooting + escalation |

---

## 6. Success Metrics & Targets

| Metric | Target | Validation |
|--------|--------|---|
| **Policy Evaluation Accuracy** | 100% | QA-1 |
| **Immutable Retention Block Rate** | 100% | QA-2 |
| **Legal-Hold Exclusion Rate** | 100% | QA-3 |
| **Retry Success Rate** | >95% on first retry | QA-4 |
| **Alert Delivery** | 100% within 5 minutes | QA-4 |
| **Retrieval Authorization** | 100% enforced | QA-5 |
| **Archive Retrieval Time** | <1 hour | QA-5 |
| **Audit Trail Completeness** | 100% of executions | QA-6 |
| **Report Generation** | 100% accuracy | QA-6 |
| **Policy Change Approval** | 100% tracked | QA-6 |

---

## 7. Risk Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|---|---|
| **Accidental data loss in purge** | CRITICAL | LOW | Dry-run validation, immutable retention blocking, audit trail |
| **Legal-hold bypass** | HIGH | LOW | Query filter enforcement, exception logging, compliance audits |
| **Archive restore failure** | HIGH | LOW | Backup strategy, integrity verification, restore test drills |
| **Job timeout on large dataset** | HIGH | MEDIUM | Pagination/batching, timeout configuration, alert on slow jobs |
| **Policy version conflict** | MEDIUM | LOW | Backward compatibility guarantee, change approval workflow |
| **Compliance audit failure** | MEDIUM | LOW | Immutable audit trail, report generation, versioning |
| **Alert fatigue** | LOW | MEDIUM | Alert tuning, suppression rules, runbook quality |

---

## 8. Definition of Done

- [ ] All 11 implementation tasks completed per acceptance criteria
- [ ] All 6 QA tests passing
- [ ] Audit trail immutable and queryable
- [ ] Compliance reports generating correctly
- [ ] Runbook tested with operations team
- [ ] Legal-hold integration validated
- [ ] Archive retrieval path documented and verified
- [ ] Policy versioning backward compatible
- [ ] Monitoring and alerting active
- [ ] Production deployment approved by compliance officer

---

## 9. Next Steps

**Immediate (Days 1-2):**
- Complete LIFE-1 implementation (policy model + schedule framework)
- Create test data with various policies and timezones

**Short-term (Days 2-4):**
- Complete LIFE-2 (archive/purge orchestration)
- Implement IMM-1, HOLD-1, GOV-1 compliance controls
- Add OPS-1 monitoring

**Mid-term (Days 5-6):**
- Add OPS-2 alerting and incident hooks
- Implement RETR-1 retrieval, AUDIT-1 logging, REPORT-1 reporting
- Document DOC-1 runbook

**Final (Days 6-7):**
- Run QA-1 through QA-6 validation tests
- Compliance officer review and sign-off
- Production deployment

---

## 10. Key Documents in This Package

All specifications available in: `.propel/context/tasks/EP-DATA-001/us_106/`

**Start with:** This TASK-106-MASTER.md for complete overview

**Detailed Specs** (to be created):
- LIFE-1.md - Policy model and schedule framework
- LIFE-2.md - Archive and purge orchestration
- IMM-1.md - Immutable retention enforcement
- HOLD-1.md - Legal-hold controls
- GOV-1.md - Policy versioning
- OPS-1.md - Monitoring and retries
- OPS-2.md - Alerting and incidents
- RETR-1.md - Archive retrieval
- AUDIT-1.md - Audit trail logging
- REPORT-1.md - Compliance reporting
- DOC-1.md - Lifecycle runbook
- QA-TESTS.md - Validation procedures

---

## 11. Sign-Off Requirements

Approvals needed from:
- [ ] Data Governance Lead
- [ ] Compliance Officer
- [ ] Database Architect
- [ ] Operations Lead
- [ ] Security Lead (for legal-hold, access control)

---

**Status:** Ready for Phase 1 (LIFE-1, LIFE-2) implementation

**Last Updated:** 2026-06-22  
**Prepared by:** Copilot (GitHub)
