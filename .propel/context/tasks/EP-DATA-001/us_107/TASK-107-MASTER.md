# TASK-107: Implement Data Quality Validation Checks

**Master Task Breakdown Document**

**Status:** Specification Phase  
**Total Subtasks:** 9 core + 6 QA  
**Total Story Points:** 38  
**Estimated Effort:** 3-5 dev days + rule tuning  
**Created:** 2026-06-22

---

## 1. Executive Summary

TASK-107 implements automated data quality validations for critical clinical domains with severity-based enforcement and comprehensive reporting. The solution detects completeness issues, duplicates, and consistency mismatches while providing severity-routed alerting, trend analytics, and publish-blocking for severe failures.

**Key Challenges:**
- Balancing detection sensitivity with false positive rates
- Handling domain-specific validation rules across multiple tables
- Real-time validation without blocking ingestion performance
- Distinguishing recoverable issues from critical failures
- Routing alerts to appropriate teams with actionable context

**Success Definition:**
- Completeness/type checks enforced for critical domains
- Uniqueness checks identify and flag duplicates
- Cross-table consistency mismatches reported
- Threshold breaches trigger severity-based alerts
- Trend metrics available in quality reports
- Severe failures block downstream publish with quarantine flow

---

## 2. Acceptance Criteria Mapping

| AC ID | Criterion | Implementation Tasks | Validation |
|-------|-----------|---|---|
| **AC-1** | Completeness and type checks enforced | RULE-1, PIPE-1, QA-1 | Rule deployment, pipeline integration |
| **AC-2** | Uniqueness checks identify duplicates | RULE-2, QA-2 | Duplicate detection accuracy, confidence scoring |
| **AC-3** | Cross-table consistency mismatches reported | RULE-3, QA-3 | Referential integrity, semantic checks |
| **AC-4** | Threshold breaches trigger severity-based alerts | OBS-1, OBS-2, QA-4 | Alert routing, severity enforcement |
| **AC-5** | Trend metrics available in quality reports | REPORT-1, QA-5 | Dashboard accuracy, metric continuity |
| **AC-6** | Severe failures block publish, quarantine flow | PIPE-2, GOV-1, QA-6 | Publish gate, quarantine validation |

---

## 3. Subtasks Overview

### Phase 1: Rule Engineering Foundation (RULE-1, RULE-2, RULE-3) - 12 pts

**Objective:** Design and implement rule sets for completeness, uniqueness, and consistency validation

#### RULE-1: Completeness and Validity Rule Set (4 pts)
- **Purpose:** Define required-field, datatype, range, and domain value validations
- **Key Components:**
  - Rule schema: rule_id, domain, rule_type, expression, severity, owner
  - Completeness rules: non-null constraints per field
  - Datatype rules: string/int/date/decimal validation
  - Range rules: min/max bounds, acceptable value lists
  - Domain rules: clinic_id, provider_id, appointment_status valid values
  - Rule versioning: Version rules with effective dates and deprecation
  - Rule packs: Group rules by domain (appointments, medications, allergies, coding)
- **Implementation:**
  - Rule DSL or JSON schema for rule definition
  - Rule evaluator engine (SQL, Python, or Java)
  - Rule registry and metadata management
  - Version control for rule changes
- **Success Metrics:** 100+ rules defined and versioned, <5ms per rule evaluation, 0 rule parsing errors

#### RULE-2: Duplicate Detection Rules (4 pts)
- **Purpose:** Implement uniqueness checks using business keys and fuzzy indicators
- **Key Components:**
  - Business key detection: (patient, appointment_status, scheduled_start) as key
  - Exact match duplicates: Query for identical records
  - Fuzzy duplicates: Levenshtein distance for name matching, soundex for phonetic matching
  - Duplicate confidence scoring: 0-100 confidence percentile
  - Metadata: duplicate_id, records_involved, confidence, rule_version
  - Handling: Log duplicates without blocking (for review/merge workflow)
- **Implementation:**
  - Business key definition system
  - Fuzzy matching algorithms (Levenshtein, Soundex, etc.)
  - Duplicate scoring engine
  - Deduplication suggestion system
- **Success Metrics:** 95%+ precision on exact duplicates, <500ms fuzzy check per batch, <10% false positive rate on fuzzy matches

#### RULE-3: Consistency and Referential Rule Set (4 pts)
- **Purpose:** Implement cross-table consistency checks and semantic mismatches
- **Key Components:**
  - Referential integrity: appointment.provider_id must exist in provider table
  - Cardinality constraints: Patient can have max 3 concurrent active appointments
  - Semantic consistency: appointment.duration must be between appointment_type.min_duration and max_duration
  - Temporal consistency: appointment.scheduled_start < appointment.scheduled_end
  - Status flow rules: Appointment can only transition certain state paths (pending → confirmed → completed, not pending → completed directly)
  - Clinical rules: Allergy interactions, medication contraindications, dosage limits
- **Implementation:**
  - Cross-table query engine
  - Constraint violation detection
  - State machine validation for status transitions
  - Business logic validator
- **Success Metrics:** 100% referential integrity coverage, <1s cross-table checks, 0 undetected orphaned records

---

### Phase 2: Pipeline and Enforcement (PIPE-1, PIPE-2, GOV-1) - 11 pts

**Objective:** Integrate validation into ingestion/publish pipeline with enforcement gates

#### PIPE-1: Scheduled and In-Pipeline Execution (4 pts)
- **Purpose:** Run validations both in real-time pipeline and scheduled batches
- **Key Components:**
  - In-pipeline: Validate on ingestion (after INSERT/UPDATE), fail fast on critical issues
  - Scheduled: Nightly batch validation of all tables (detect slow-forming issues)
  - Async validation: Non-blocking validation for non-critical domains
  - Pipeline integration points: Pre-insert, post-insert, pre-publish hooks
  - Performance: <100ms per record validation, <5s batch validation per 1000 records
  - Dry-run mode: Validate without applying consequences
- **Implementation:**
  - Validation middleware/interceptor
  - Scheduled job orchestration
  - Async validation queue (message broker pattern)
  - Performance optimization (batch validation, caching, parallel execution)
- **Success Metrics:** <100ms validation latency, >99% validation coverage, 0 validation timeouts

#### PIPE-2: Publish Gate and Quarantine Flow (4 pts)
- **Purpose:** Block downstream publish for severe violations, route to quarantine/triage
- **Key Components:**
  - Severity thresholds: CRITICAL (0 allowed), HIGH (>3 triggers block), MEDIUM (log only)
  - Publish gate: Check violation count/types before allowing downstream publish
  - Quarantine state: Mark records as "needs_review" when CRITICAL violations detected
  - Triage workflow: Data governance team reviews and approves/corrects quarantined records
  - Approval mechanism: Manual approval or auto-correction rules for known issues
  - Metrics: Track quarantine rate, review time, correction rate
- **Implementation:**
  - Publish gate middleware
  - Quarantine queue/state machine
  - Approval workflow API
  - Correction rule engine
- **Success Metrics:** 100% CRITICAL violations blocked, <1% false positive blocks, <4hr avg triage time

#### GOV-1: Enforcement Policy Configuration (3 pts)
- **Purpose:** Define staged enforcement (observe, warn, block) by domain/severity
- **Key Components:**
  - Policy schema: domain, rule_id, enforcement_level (observe/warn/block), effective_date, owner
  - Staged rollout: Start with "observe" mode to tune false positives, then escalate to "warn", then "block"
  - Exception handling: Rules can have exemption categories (e.g., test data, migration data)
  - Policy versioning: Track policy changes over time
  - Override capability: Data governance officer can temporarily override enforcement for emergency data loads
- **Implementation:**
  - Policy configuration system
  - Rollout management (gradual escalation)
  - Exception registry
  - Policy audit trail
- **Success Metrics:** 0 untracked policy changes, <5% false positive rate at "observe" level

---

### Phase 3: Observability and Reporting (OBS-1, OBS-2, REPORT-1) - 10 pts

**Objective:** Monitor validations, alert domain teams, report trends

#### OBS-1: Violation Metrics and Alerting (3 pts)
- **Purpose:** Emit metrics, detect threshold breaches, configure alerts
- **Key Components:**
  - Metrics: violation_count_by_rule, violation_count_by_domain, violation_count_by_severity
  - Threshold monitoring: Alert if violation_count > daily_threshold (configurable per domain)
  - Alert conditions: Sustained degradation (>5 violations on same rule for 2+ hours), spike detection (3x baseline)
  - Metrics persistence: Prometheus, CloudWatch, or Datadog
  - Alert delay: <5 minutes from violation to alert firing
- **Implementation:**
  - Metrics emitter
  - Threshold monitoring engine
  - Alert rule configuration
- **Success Metrics:** <5 min alert latency, <10% false positive alerts, 100% critical violation detection

#### OBS-2: Ownership Routing (3 pts)
- **Purpose:** Route alerts to domain owning teams with context and runbook links
- **Key Components:**
  - Ownership mapping: Rule → Team (e.g., appointment validation → Clinical Operations, coding validation → Compliance)
  - Alert routing: Send to Slack, email, PagerDuty with team assignment
  - Context inclusion: Rule details, affected domain, violation count, recent trend
  - Runbook links: Each alert includes link to troubleshooting runbook (see DOC-1)
  - SLA timers: Track time from alert to resolution
  - Escalation: Auto-escalate unacknowledged alerts after 30 minutes
- **Implementation:**
  - Ownership registry
  - Alert routing engine (Slack, email, PagerDuty integrations)
  - Context formatter
  - SLA tracking
- **Success Metrics:** <5 min to team notification, 100% ownership assignment, <60 min avg SLA

#### REPORT-1: Quality Trend Dashboard and Exports (4 pts)
- **Purpose:** Produce dashboards and periodic reports for stakeholders
- **Key Components:**
  - Dashboard: Real-time quality metrics (violation count, trend, affected domains)
  - Metrics displayed: Daily violation counts, trend (↑/↓/→), top 5 failing rules, top 5 affected domains
  - Historical view: 30-day trend graph per rule and domain
  - Quality score: Calculate overall data quality percentage (100% - violation_rate)
  - Periodic reports: Daily email to Data Governance Lead (morning briefing), weekly to executives
  - Export format: CSV, PDF for stakeholder presentations
  - Drill-down: Navigate from dashboard to rule details, affected records, remediation actions
- **Implementation:**
  - Metrics aggregation queries
  - Dashboard (Grafana, Tableau, or custom)
  - Report generation and email scheduling
  - Export utilities
- **Success Metrics:** Dashboard loads <2s, reports generate <5 min, accuracy within 1% of actual metrics

---

### Phase 4: Testing and Validation (QA-1 through QA-6) - 6 pts

**Objective:** Validate all acceptance criteria through systematic testing

#### QA-1: Completeness/Validity Validation (1 pt)
**Testing:** Validate completeness/type rules with seeded invalid records

**Test Cases:**
- Missing required field: Insert record without patient_id, verify rule triggers
- Invalid datatype: Insert appointment with invalid ISO date, verify rule triggers
- Range violation: Insert appointment with duration > 480 minutes, verify rule triggers
- Domain value invalid: Insert appointment_status = 'unknown', verify rule triggers
- Valid record: Insert valid record, verify no violations

**Success:** 100% of seeded violations detected, 0 false positives on valid records

#### QA-2: Duplicate Detection Validation (1 pt)
**Testing:** Validate duplicate rule performance and accuracy

**Test Cases:**
- Exact duplicate: Insert same record twice, verify detected with 100% confidence
- Fuzzy duplicate: Insert record with 1 character difference in name, verify detected with confidence >90%
- False positive: Insert very similar but distinct records (different patients), verify confidence <20%
- Performance: Detect duplicates for 100K records in <10 seconds

**Success:** 95%+ precision on exact duplicates, <500ms fuzzy check per batch

#### QA-3: Consistency Validation (1 pt)
**Testing:** Validate cross-table mismatch reporting

**Test Cases:**
- FK violation: Insert appointment.provider_id = invalid_id, verify rule triggers
- Cardinality violation: Assign 4 concurrent appointments to patient (max 3), verify rule triggers
- Temporal violation: appointment.start > appointment.end, verify rule triggers
- Status transition violation: Transition appointment from pending → completed directly (invalid path), verify rule triggers

**Success:** 100% violation detection, 0 missed orphaned records

#### QA-4: Severity Alert Validation (1 pt)
**Testing:** Validate severity thresholds and routing

**Test Cases:**
- CRITICAL severity: Trigger >3 CRITICAL violations, verify publish blocked
- HIGH severity: Trigger 5 HIGH violations, verify alert sent to team
- Alert routing: Verify Slack notification sent to Clinical Operations for appointment rule violations
- Runbook link: Verify runbook URL present in alert

**Success:** 100% CRITICAL violations blocked, <5 min alert latency, 0 routing failures

#### QA-5: Trend Metrics Validation (1 pt)
**Testing:** Validate dashboard/report metrics correctness

**Test Cases:**
- Metric accuracy: Violation counts in dashboard match actual violation count in database
- Trend tracking: 30-day trend graph shows correct progression
- Quality score: Quality % = (total_records - total_violations) / total_records, verified
- Report completeness: Daily report includes all required metrics and charts

**Success:** <1% metric discrepancy, all trend lines tracking correctly

#### QA-6: Publish Block Validation (1 pt)
**Testing:** Validate publish blocking and quarantine behavior

**Test Cases:**
- Block on CRITICAL: Attempt publish with CRITICAL violations, verify blocked
- Allow on LOW: Attempt publish with only LOW violations, verify allowed
- Quarantine flow: Blocked records moved to quarantine state, can be reviewed and approved
- Manual correction: Data governance corrects record in quarantine, re-runs validation, publish succeeds

**Success:** 100% CRITICAL blocks, 0 false positive blocks, quarantine/approval flow working

---

## 4. Execution Order and Dependencies

```
Phase 1: Rule Engineering (parallel)
├── RULE-1: Completeness & Validity (4 pts)
├── RULE-2: Duplicate Detection (4 pts)
└── RULE-3: Consistency & Referential (4 pts)
    └── All complete

Phase 2: Pipeline & Enforcement (after Phase 1)
├── PIPE-1: Scheduled & In-Pipeline Execution (4 pts)
├── PIPE-2: Publish Gate & Quarantine (4 pts)
└── GOV-1: Enforcement Policy Config (3 pts)

Phase 3: Observability (after Phase 2)
├── OBS-1: Metrics & Alerting (3 pts)
├── OBS-2: Ownership Routing (3 pts)
└── REPORT-1: Quality Dashboard & Reports (4 pts)

Phase 4: Testing (final)
└── QA-1 through QA-6 (6 pts parallel)

CRITICAL PATH:
RULE-1/2/3 → PIPE-1 → PIPE-2 → GOV-1 → OBS-1 → OBS-2 → REPORT-1 → QA
Estimated: 3-5 days sequential + 1 day QA
```

---

## 5. Technical Architecture

### Data Model

```
validation_rules:
  - rule_id (PK)
  - domain (VARCHAR) - "patient", "appointment", "coding", etc.
  - rule_type (ENUM) - "completeness", "type", "range", "uniqueness", "referential", "semantic"
  - rule_name (VARCHAR)
  - rule_expression (TEXT) - SQL or rule DSL
  - severity (ENUM) - "critical", "high", "medium", "low"
  - enabled (BOOLEAN)
  - version (INT)
  - effective_date (DATE)
  - owner_id (VARCHAR)
  - created_at (TIMESTAMP)

validation_violations:
  - violation_id (PK)
  - rule_id (FK)
  - domain (VARCHAR)
  - record_id (VARCHAR)
  - violation_message (TEXT)
  - severity (ENUM)
  - violation_timestamp (TIMESTAMP)
  - violation_status (ENUM) - "detected", "acknowledged", "resolved"
  - created_at (TIMESTAMP)

duplicate_flags:
  - duplicate_id (PK)
  - primary_record_id (VARCHAR)
  - duplicate_record_id (VARCHAR)
  - table_name (VARCHAR)
  - confidence (INT 0-100)
  - match_type (ENUM) - "exact", "fuzzy"
  - flagged_at (TIMESTAMP)

quarantine_records:
  - quarantine_id (PK)
  - record_id (VARCHAR)
  - table_name (VARCHAR)
  - violation_ids (TEXT) - comma-separated
  - status (ENUM) - "pending_review", "approved", "rejected"
  - reviewed_by (VARCHAR)
  - reviewed_at (TIMESTAMP)
  - created_at (TIMESTAMP)

validation_policies:
  - policy_id (PK)
  - rule_id (FK)
  - domain (VARCHAR)
  - enforcement_level (ENUM) - "observe", "warn", "block"
  - effective_date (DATE)
  - owner_id (VARCHAR)
  - version (INT)
  - created_at (TIMESTAMP)
```

### Key Features by Phase

| Phase | Feature | Implementation |
|-------|---------|---|
| **1** | Completeness Validation | NOT NULL checks, datatype validation, range checks |
| **1** | Duplicate Detection | Business key matching, fuzzy algorithms, confidence scoring |
| **1** | Consistency Checks | FK validation, cardinality checks, temporal checks, state machines |
| **2** | Pipeline Integration | Pre/post-insert hooks, async validation, batch processing |
| **2** | Publish Gate | Severity threshold checks, record quarantine, approval workflow |
| **2** | Policy Enforcement | Staged rollout (observe→warn→block), exception handling |
| **3** | Metrics & Alerts | Prometheus/CloudWatch integration, threshold monitoring, alert firing |
| **3** | Team Routing | Ownership mapping, Slack/PagerDuty integration, runbook links |
| **3** | Reporting | Dashboard, trend metrics, PDF export, email distribution |

---

## 6. Success Metrics & Targets

| Metric | Target | Validation |
|--------|--------|---|
| **Completeness Detection** | 100% | QA-1 |
| **Duplicate Precision** | 95%+ | QA-2 |
| **Consistency Coverage** | 100% | QA-3 |
| **Alert Latency** | <5 minutes | QA-4 |
| **Metric Accuracy** | <1% discrepancy | QA-5 |
| **Publish Block Accuracy** | 100% CRITICAL, <1% false positive | QA-6 |
| **Rule Evaluation Time** | <5ms per rule | Performance benchmark |
| **Batch Validation Time** | <5s per 1000 records | Performance benchmark |
| **Alert Delivery** | 100% within 5 min | OBS-1 |
| **Team Notification** | 100% within 5 min | OBS-2 |

---

## 7. Risk Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|---|---|
| **False positive rate too high** | HIGH | MEDIUM | Staged rollout (observe first), rule tuning, exemption handling |
| **Validation latency impacting ingestion** | HIGH | MEDIUM | Async validation, batch optimization, performance benchmarking |
| **Duplicate detection too slow** | MEDIUM | LOW | Indexed queries, caching, parallel execution |
| **Publish gate blocks legitimate data** | MEDIUM | LOW | Careful severity calibration, manual override capability |
| **Alerts trigger alert fatigue** | LOW | MEDIUM | Alert tuning, suppression rules, SLA tracking |
| **Incomplete cross-table coverage** | HIGH | LOW | Comprehensive rule definition, peer review of rules |

---

## 8. Definition of Done

- [ ] All 9 implementation tasks completed per acceptance criteria
- [ ] All 6 QA tests passing (100% coverage)
- [ ] Rule set tuned to <10% false positive rate
- [ ] Publish gate tested and validated
- [ ] Quarantine workflow end-to-end tested
- [ ] Alerting and routing working for all domains
- [ ] Dashboard deployed and accessible
- [ ] Documentation and runbooks published
- [ ] Team trained on validation system
- [ ] Production deployment approved by Data Governance Lead

---

## 9. Next Steps

**Immediate (Days 1-2):**
- Complete RULE-1, RULE-2, RULE-3 implementation
- Create rule registry with 50+ initial rules
- Set up test data with seeded violations

**Short-term (Days 2-3):**
- Integrate PIPE-1 into ingestion pipeline
- Implement PIPE-2 publish gate and quarantine
- Deploy GOV-1 policy configuration

**Mid-term (Days 4):**
- Implement OBS-1 metrics and alerting
- Configure OBS-2 team routing
- Deploy REPORT-1 dashboard

**Final (Days 5):**
- Execute QA-1 through QA-6 validation tests
- Fine-tune rules based on QA results
- Data Governance Lead approval and production deployment

---

## 10. Key Documents in This Package

All specifications in: `.propel/context/tasks/EP-DATA-001/us_107/`

**Start with:** 
- [TASK-107-MASTER.md](./TASK-107-MASTER.md) - This document (complete overview)
- [RULE-1.md](./RULE-1.md) - Completeness & validity rules (detailed implementation)
- [RULE-2.md](./RULE-2.md) - Duplicate detection (detailed implementation)
- [REMAINING-SUBTASKS.md](./REMAINING-SUBTASKS.md) - Quick reference for RULE-3, PIPE-1/2, GOV-1, OBS-1/2, REPORT-1, QA-1-6

---

## 11. Sign-Off Requirements

Approvals needed from:
- [ ] Data Governance Lead
- [ ] Clinical Operations Lead
- [ ] Database Architect
- [ ] Platform Engineering Lead
- [ ] Compliance Officer (for data quality compliance)

---

**Status:** Ready for Phase 1 (RULE-1, RULE-2, RULE-3) implementation

**Last Updated:** 2026-06-22  
**Prepared by:** Copilot (GitHub)
