# TASK-106 Remaining Subtasks - Consolidated Specifications

**Compliance Controls, Operations, Retrieval, Audit, and Documentation**

**Reference Document** - For detailed individual task specs, see individual task files (IMM-1.md, HOLD-1.md, etc.)

---

## 1. Compliance Controls (10 pts total)

### IMM-1: Immutable Retention Enforcement (3 pts)

**Objective:** Block delete operations before retention expiry, emit policy violation events

**Acceptance Criteria:**
- [ ] Delete operations blocked where current_date < retention_expiry
- [ ] Policy violation events emitted as structured log entries
- [ ] Audit log records all delete attempts with operator/timestamp
- [ ] <1ms enforcement overhead per check

**Implementation Approach:**
- Create delete middleware interceptor to check retention_expiry
- Emit violation event to compliance monitoring system
- Log to immutable audit table (never deleted/modified)
- Query interface: `SELECT * FROM policy_violations WHERE violation_type = 'immature_delete_attempt'`

**Key Outputs:**
- Delete blocker middleware
- Policy violation event schema
- Audit logging implementation
- Query interface for compliance review

**Success Metrics:**
- 100% of delete attempts evaluated
- 0 authorized deletions before expiry
- <1ms latency per enforcement check

**Dependencies:** LIFE-1 complete

---

### HOLD-1: Legal-Hold Exclusion Controls (3 pts)

**Objective:** Exclude legal-hold records from purge, produce exception logs

**Acceptance Criteria:**
- [ ] Legal-hold marker prevents purge operations
- [ ] Held records excluded from purge job scope
- [ ] Exception log captures attempted purges of held records
- [ ] Hold metadata tracked (hold_id, hold_reason, held_by, held_at)

**Implementation Approach:**
- Add legal_holds table with record references
- Modify purge job to query for holds before purging
- Create hold_exclusion_log table
- Implement hold lifecycle (place → maintain → release)

**Key Outputs:**
- Legal-hold schema and tables
- Hold marker logic
- Purge job integration
- Exception logging

**Success Metrics:**
- 100% held records excluded from purge
- 0 held records accidentally purged
- All exclusions logged

**Dependencies:** LIFE-2 complete

---

### GOV-1: Policy Versioning and Change Control (4 pts)

**Objective:** Version policies with effective dates, approval workflow, backward compatibility

**Acceptance Criteria:**
- [ ] Policies versioned with version_number, effective_date, superseded_date
- [ ] Policy changes require approval (compliance officer + DBA)
- [ ] Records respect policy active at creation time (backward compatible)
- [ ] Rollback capability with audit trail
- [ ] Impact analysis showing affected records per policy change

**Implementation Approach:**
- Add versioning fields to retention_policies table
- Implement policy_change_log table
- Create approval workflow (requires 2 approvals)
- Query for policy active at record creation time
- Build impact analysis queries

**Key Outputs:**
- Policy versioning schema
- Change approval workflow
- Backward compatibility logic
- Impact analysis queries
- Rollback procedures

**Success Metrics:**
- 100% of policy changes tracked
- 100% of changes approved
- 0 unapproved policies in production
- Backward compatibility maintained

**Dependencies:** IMM-1 complete

---

## 2. Operations and Reliability (10 pts total)

### OPS-1: Monitoring, Retries, and Dead-Letter Handling (5 pts)

**Objective:** Monitor jobs, configure exponential backoff retries, handle terminal failures

**Acceptance Criteria:**
- [ ] Job metrics collected (success/failure counts, duration, throughput)
- [ ] Exponential backoff retry: 1s, 2s, 4s, 8s, 16s (max 5 attempts)
- [ ] Failed jobs routed to dead-letter queue (DLQ)
- [ ] Circuit breaker stops retries after N consecutive failures
- [ ] Monitoring dashboard with real-time job status

**Implementation Approach:**
- Instrument jobs with metrics collection
- Implement retry logic with exponential backoff
- Create DLQ for failed jobs
- Build monitoring dashboard (Prometheus, CloudWatch, Datadog)
- Configure circuit breaker (e.g., 5+ failures trigger circuit open)

**Key Outputs:**
- Retry logic implementation
- Dead-letter queue schema/topic
- Metrics schema
- Monitoring dashboard definition
- Runbook for DLQ handling

**Success Metrics:**
- <1% permanent failure rate
- 95%+ successful first-attempt jobs
- <100ms monitoring latency
- 0 lost jobs (all tracked in DLQ)

**Dependencies:** LIFE-2 complete

---

### OPS-2: Alerting and Incident Hooks (5 pts)

**Objective:** Configure alerts for failures, backlog, escalation with runbook links

**Acceptance Criteria:**
- [ ] Alerts for: job failures (>10/hr), backlog growth (>1M records), repeated failures (>3x)
- [ ] Alert routing to PagerDuty/Slack with severity levels
- [ ] Runbook link attached to each alert (from DOC-1)
- [ ] Incident auto-filed in Jira/GitHub for critical failures
- [ ] <5 minute alert latency

**Implementation Approach:**
- Define alert conditions in monitoring system (Prometheus rules, CloudWatch alarms)
- Configure Slack webhooks and PagerDuty integrations
- Build incident template for auto-filing
- Link runbook URLs to alert definitions
- Implement alert suppression for maintenance windows

**Key Outputs:**
- Alert definitions (Terraform/YAML)
- Slack integration
- PagerDuty integration
- Incident template
- Maintenance window config

**Success Metrics:**
- <5 minute alert latency
- <10% false positive rate
- <30 minute MTTR (mean time to resolution)
- 100% critical failure incident coverage

**Dependencies:** OPS-1 complete

---

## 3. Retrieval and Audit (12 pts total)

### RETR-1: Authorized Archive Retrieval Path (3 pts)

**Objective:** Enable authorized retrieval of archived data with access control and audit logging

**Acceptance Criteria:**
- [ ] Retrieval request workflow (Data Officer/Compliance Officer only)
- [ ] Access control enforces requester role and data domain permissions
- [ ] Retrieval audit log records: who, what, when, why, approval, status
- [ ] Restore from cold storage to warm storage (<1 hour)
- [ ] Data integrity verification (checksums, record counts)

**Implementation Approach:**
- Create retrieval_requests table
- Implement role-based access control checks
- Build restore workflow from S3 Glacier/Azure Archive
- Create retrieval_audit_log table
- Implement checksum verification post-restore

**Key Outputs:**
- Retrieval request schema
- Access control policies
- Restore workflow code
- Retrieval audit schema
- Integrity verification logic

**Success Metrics:**
- 100% of retrievals verified
- <1 hour retrieval time
- 100% access control enforcement
- 0 unauthorized retrievals

**Dependencies:** LIFE-2 complete

---

### AUDIT-1: Lifecycle Audit Trail (3 pts)

**Objective:** Maintain immutable audit log of all lifecycle transitions with compliance retention

**Acceptance Criteria:**
- [ ] Execution log captures: version, action, counts, policy_id, operator, timestamps
- [ ] Transition audit: before/after counts, storage locations, checksums
- [ ] Immutable log (append-only, no deletes)
- [ ] Compliance retention: 7yr (prod), 1yr (staging), 90d (dev)
- [ ] Export for compliance review (Splunk, ELK, S3)

**Implementation Approach:**
- Create lifecycle_execution_log table (immutable)
- Implement append-only log pattern
- Build retention policy enforcement
- Create export queries and scripts
- Configure log rotation and archival

**Key Outputs:**
- Execution log schema
- Immutable log implementation
- Log export scripts
- Compliance query interface
- Retention enforcement

**Success Metrics:**
- 100% execution coverage
- 0 log tampering
- <1MB/day log growth per environment
- Full compliance audit trail

**Dependencies:** LIFE-2, OPS-1 complete

---

### REPORT-1: Compliance Evidence Reporting (3 pts)

**Objective:** Generate per-run reports with execution evidence for compliance review

**Acceptance Criteria:**
- [ ] Report auto-generated after each job run
- [ ] Contains: execution date, policy version, counts, exceptions, status
- [ ] Exception summary: holds applied, retention violations, failures
- [ ] Export formats: CSV, JSON, PDF
- [ ] Scheduled reports: daily, weekly, monthly
- [ ] Distribution: email to compliance officer, store in compliance repo

**Implementation Approach:**
- Create report_execution table
- Build report generation queries
- Implement report templates (CSV, JSON, PDF)
- Configure scheduled report jobs
- Set up email distribution

**Key Outputs:**
- Report schema
- Report generation queries
- Report templates
- Scheduled job definitions
- Email distribution config

**Success Metrics:**
- 100% execution coverage
- <5 minute report generation
- 100% accuracy (counts match actual execution)
- All formats export correctly

**Dependencies:** AUDIT-1, IMM-1, HOLD-1, GOV-1 complete

---

### DOC-1: Lifecycle and Recovery Runbook (3 pts)

**Objective:** Document procedures, recovery steps, emergency processes for operations team

**Acceptance Criteria:**
- [ ] Job schedules documented (archive nightly, purge Sunday 2 AM)
- [ ] Normal operations guide with step-by-step procedures
- [ ] Failure recovery: diagnosis, common issues, remediation steps
- [ ] Manual override procedures
- [ ] Legal-hold management and verification
- [ ] Archive retrieval procedures with examples
- [ ] Rollback procedures with examples
- [ ] Troubleshooting FAQ and escalation

**Implementation Approach:**
- Write comprehensive markdown runbook
- Create decision trees for common issues
- Build troubleshooting flowcharts
- Document contact list and escalation
- Include real examples and templates

**Key Outputs:**
- Runbook markdown document (5-10 pages)
- Decision tree diagrams
- Troubleshooting flowcharts
- Contact escalation list
- Procedure templates

**Success Metrics:**
- Runbook tested with operations team
- <30 minute MTTR for common failures
- 100% procedure coverage
- Clear and actionable guidance

**Dependencies:** All other tasks complete

---

## 4. Testing and Validation (6 pts total)

### QA-1: Policy Window Transition Validation (1 pt)

**Testing:** Validate archive/purge transitions at boundary dates and timezones

**Test Cases:**
- Retention boundary crossing (record at T, archive at T+30d, not before)
- Timezone boundary crossing (UTC, PST, IST, etc.)
- DST transitions during policy evaluation
- Leap second handling
- Manual time acceleration validation

**Success Criteria:** 100% tests pass, all timezone boundaries correct

---

### QA-2: Immutable Retention Validation (1 pt)

**Testing:** Validate deletion blocked before immutable retention expiry

**Test Cases:**
- Delete before expiry (T+20d for 30d retention): blocked
- Delete at expiry (T+30d): allowed
- Delete after expiry (T+35d): allowed
- Policy violation event: emitted and logged
- Audit trail: all attempts logged with reason/operator

**Success Criteria:** 100% premature deletes blocked, all violations logged

---

### QA-3: Legal-Hold Exclusion Validation (1 pt)

**Testing:** Validate held records excluded from purge

**Test Cases:**
- Hold placement: record marked in system
- Purge with hold: held records excluded from purge job
- Hold exception log: entries created for held records
- Hold release: record becomes purgeable
- Multiple holds: all must be released before purge

**Success Criteria:** 100% held records excluded, all exceptions logged, 0 held records purged

---

### QA-4: Failure and Retry Validation (1 pt)

**Testing:** Validate retries/backoff and alerting under job failures

**Test Cases:**
- Transient failure: DB timeout, retry succeeds on attempt 2
- Backoff timing: verify intervals (1s, 2s, 4s, 8s, 16s)
- Max retries: fail all 5 attempts, goes to DLQ
- Alert trigger: alert emitted on failure
- Alert routing: Slack notification sent, PagerDuty incident created
- Runbook link: alert includes runbook link

**Success Criteria:** <100ms backoff latency, 100% alert delivery, <5 min alert latency

---

### QA-5: Archive Retrieval Validation (1 pt)

**Testing:** Validate authorized retrieval with access controls

**Test Cases:**
- Authorized retrieval: Data Officer requests archived data, approved and restored
- Unauthorized retrieval: user without permission denied
- Retrieval audit: all retrievals logged (user, timestamp, purpose)
- Restore success: restored data byte-for-byte identical
- Restore performance: completes in <1 hour
- Restore verification: checksums and counts match

**Success Criteria:** 100% authorized retrievals succeed, 100% unauthorized denied, all audited

---

### QA-6: Compliance Evidence Validation (1 pt)

**Testing:** Validate lifecycle reports with policy versions and execution evidence

**Test Cases:**
- Report generation: auto-generated after job run
- Report completeness: all required fields present
- Policy version capture: active policy version captured
- Exception summary: holds and violations included
- Export formats: CSV, JSON, PDF all valid
- Report accuracy: counts match actual execution

**Success Criteria:** 100% execution reports generated, 100% complete, all formats export

---

## 5. Execution Dependencies

```
LIFE-1 ✅
  ↓
LIFE-2 ✅
  ├→ IMM-1 (parallel)
  ├→ HOLD-1 (parallel)
  └→ OPS-1 (parallel)
       ↓
      IMM-1, HOLD-1, OPS-1 complete
       ↓
      GOV-1 (after IMM-1)
       ↓
      OPS-2 (after OPS-1)
       ↓
      RETR-1, AUDIT-1, REPORT-1 (parallel)
       ↓
      DOC-1 (after all others)
       ↓
      QA-1 through QA-6 (parallel)
       ↓
    TASK-106 COMPLETE ✅
```

---

## 6. Success Metrics Summary

| Task | Metric | Target |
|------|--------|--------|
| IMM-1 | Delete block rate | 100% |
| HOLD-1 | Hold exclusion rate | 100% |
| GOV-1 | Policy change approval | 100% |
| OPS-1 | First-attempt success | >95% |
| OPS-2 | Alert latency | <5 min |
| RETR-1 | Retrieval time | <1 hour |
| AUDIT-1 | Log coverage | 100% |
| REPORT-1 | Report accuracy | 100% |
| DOC-1 | MTTR improvement | <30 min |
| QA-1-6 | Test pass rate | 100% |

---

## 7. Quick Reference - Task Points

- **IMM-1:** 3 pts (Immutable retention enforcement)
- **HOLD-1:** 3 pts (Legal-hold controls)
- **GOV-1:** 4 pts (Policy versioning)
- **OPS-1:** 5 pts (Monitoring and retries)
- **OPS-2:** 5 pts (Alerting and incidents)
- **RETR-1:** 3 pts (Archive retrieval)
- **AUDIT-1:** 3 pts (Audit trail)
- **REPORT-1:** 3 pts (Compliance reporting)
- **DOC-1:** 3 pts (Runbook)
- **QA-1 to QA-6:** 6 pts (Validation)

**Total:** 42 pts (+ 9 pts for LIFE-1/LIFE-2 = 51 pts for TASK-106)

---

For detailed specifications of each task, refer to individual task files:
- IMM-1.md, HOLD-1.md, GOV-1.md, OPS-1.md, OPS-2.md
- RETR-1.md, AUDIT-1.md, REPORT-1.md, DOC-1.md
- QA-TESTS.md

For master overview and execution plan, see: **TASK-106-MASTER.md**
