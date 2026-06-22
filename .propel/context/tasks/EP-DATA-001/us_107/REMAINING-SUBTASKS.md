# TASK-107 Remaining Subtasks - Consolidated Specifications

**Duplicate Detection, Consistency Checks, Pipeline Integration, Governance, Observability, Reporting, and QA**

---

## 1. Rule Engineering - Phase 1 (RULE-2, RULE-3)

### RULE-2: Duplicate Detection Rules (4 pts)

**Objective:** Identify exact and fuzzy duplicates with confidence scoring

**Acceptance Criteria:**
- [ ] Exact duplicates detected using business keys (>98% accuracy)
- [ ] Fuzzy duplicates detected (Levenshtein, Soundex) with confidence 0-100
- [ ] <500ms fuzzy check per batch of 100 records
- [ ] <10% false positive rate on fuzzy matches

**Implementation Approach:**
- Business key definition: (patient_id, appointment_status, scheduled_start) or (first_name + last_name + dob)
- Exact matching: SQL GROUP BY with HAVING COUNT(*) > 1
- Fuzzy matching: Levenshtein distance (max distance 2), Soundex for phonetic matching
- Confidence scoring: distance_score (0-100) with weights for field importance
- Deduplication suggestion: Flag duplicate sets, suggest primary record

**Key Outputs:**
- Duplicate detection engine (SQL + Python)
- Business key registry
- Fuzzy matching algorithms
- Duplicate scoring system

**Success Metrics:** 95%+ precision on exact, <500ms fuzzy check, <10% false positive rate

---

### RULE-3: Consistency and Referential Rule Set (4 pts)

**Objective:** Implement cross-table consistency and semantic validation

**Acceptance Criteria:**
- [ ] Referential integrity: 100% FK validation coverage
- [ ] Cardinality constraints enforced (e.g., max 3 concurrent appointments/patient)
- [ ] Temporal consistency: start < end, dates in valid ranges
- [ ] Status flow validation: Only valid state transitions allowed
- [ ] Clinical logic: Allergy interactions, medication contraindications
- [ ] <1s cross-table checks per 1000 records

**Implementation Approach:**
- FK constraints: Verify appointment.provider_id exists in provider table
- Cardinality checks: SELECT COUNT(*) ... GROUP BY patient_id HAVING COUNT(*) > max
- Temporal checks: WHERE scheduled_start >= scheduled_end triggers violation
- State machine: Define valid transitions (pending→confirmed→completed, not pending→completed)
- Clinical rules: Query allergy_interactions, medication_contraindications tables

**Key Outputs:**
- Cross-table constraint registry
- Cardinality validation queries
- Status transition rules engine
- Clinical logic validator

**Success Metrics:** 100% FK coverage, <1s cross-table checks, 0 orphaned records

---

## 2. Pipeline and Enforcement - Phase 2 (PIPE-1, PIPE-2, GOV-1)

### PIPE-1: Scheduled and In-Pipeline Execution (4 pts)

**Objective:** Integrate validation into real-time and batch processing

**Acceptance Criteria:**
- [ ] In-pipeline: Validate on INSERT/UPDATE, <100ms latency
- [ ] Scheduled: Nightly batch validation, <5s per 1000 records
- [ ] Async mode: Non-blocking validation for non-critical domains
- [ ] Dry-run: Preview violations without applying consequences
- [ ] Performance: 0 validation timeouts, >99% coverage

**Implementation Approach:**
- In-pipeline: Middleware/trigger on INSERT, async event emitter
- Scheduled: Cron job running daily 11 PM, query all tables
- Async queue: Message broker (RabbitMQ, Kafka) for async validation
- Dry-run mode: Set flag, validate without logging violations
- Performance optimization: Batch queries, parallel execution, caching

**Key Outputs:**
- Validation middleware/trigger
- Scheduled job orchestration (Airflow/Kubernetes)
- Async validation queue setup
- Performance monitoring

**Success Metrics:** <100ms in-pipeline, <5s batch, >99% coverage, 0 timeouts

---

### PIPE-2: Publish Gate and Quarantine Flow (4 pts)

**Objective:** Block downstream publish for critical violations, route to quarantine/triage

**Acceptance Criteria:**
- [ ] CRITICAL violations block publish (0 allowed)
- [ ] HIGH violations trigger warning/block if >3
- [ ] Quarantine: Records marked "needs_review" for triage
- [ ] Approval flow: Data governance can approve/correct and re-publish
- [ ] Metrics: Track quarantine rate, review time, correction rate

**Implementation Approach:**
- Severity threshold checks before publish
- Quarantine queue: Mark records with CRITICAL violations
- Approval workflow: API endpoint for review, approve, and retry
- Correction engine: Auto-fix known issues (optional)
- Tracking: Log quarantine → approval → retry cycle

**Key Outputs:**
- Publish gate middleware
- Quarantine state management
- Approval workflow API
- Correction rule engine

**Success Metrics:** 100% CRITICAL blocks, <1% false positive blocks, <4hr avg review time

---

### GOV-1: Enforcement Policy Configuration (3 pts)

**Objective:** Define staged enforcement (observe→warn→block) with exceptions

**Acceptance Criteria:**
- [ ] Policy schema: domain, rule_id, enforcement_level, effective_date
- [ ] Staged rollout: observe (log only) → warn (alert) → block (enforce)
- [ ] Exception registry: Bypass rules for test/migration data
- [ ] Policy audit: Track all changes, versions
- [ ] Override capability: Temporary overrides by governance officer

**Implementation Approach:**
- Policy config table: domain, rule_id, enforcement_level (observe/warn/block)
- Rollout management: Schedule gradual escalation (e.g., 1 week per stage)
- Exception handling: Regex patterns for test data, exemption categories
- Policy changes: Require approval, audit trail
- Manual override: Admin flag to temporarily disable enforcement

**Key Outputs:**
- Policy configuration schema
- Rollout scheduler
- Exception registry
- Policy audit system

**Success Metrics:** 0 unapproved policies, <5% false positive rate in observe phase

---

## 3. Observability and Reporting - Phase 3 (OBS-1, OBS-2, REPORT-1)

### OBS-1: Violation Metrics and Alerting (3 pts)

**Objective:** Emit metrics, detect thresholds, fire alerts

**Acceptance Criteria:**
- [ ] Metrics: violation_count_by_rule, _by_domain, _by_severity
- [ ] Alert conditions: Daily threshold (>10 violations), spike detection (3x baseline)
- [ ] Sustained degradation: >5 violations on same rule for 2+ hours
- [ ] Alert latency: <5 minutes from violation to alert fire
- [ ] <10% false positive alerts

**Implementation Approach:**
- Prometheus/CloudWatch metrics emitter
- Threshold monitoring: Query metrics every 5 minutes
- Spike detection: Compare current hour to 24-hour average
- Alerting: Prometheus AlertManager or CloudWatch Alarms
- Alert rules: Define conditions, severity, routing

**Key Outputs:**
- Metrics emission code
- Threshold configuration
- Alert rule definitions
- Monitoring dashboard

**Success Metrics:** <5 min alert latency, <10% false positives, 100% critical detection

---

### OBS-2: Ownership Routing (3 pts)

**Objective:** Route alerts to domain teams with context and runbooks

**Acceptance Criteria:**
- [ ] Ownership mapping: Rule → Team (Clinical Ops, Compliance, etc.)
- [ ] Alert routing: Slack, email, PagerDuty with full context
- [ ] Context: Rule details, affected domain, violation count, trend
- [ ] Runbook link: Each alert includes troubleshooting link
- [ ] SLA tracking: Time to acknowledgement, resolution

**Implementation Approach:**
- Ownership registry: rule_id → team → slack_channel/email
- Alert formatter: Include rule name, severity, affected records, trend
- Integration: Slack API, SendGrid, PagerDuty APIs
- Runbook linking: Generated from DOC-1 runbook
- SLA tracking: Track alert → ack → resolution timestamps

**Key Outputs:**
- Ownership mapping registry
- Alert routing engine
- Slack/Email/PagerDuty integrations
- SLA tracking system

**Success Metrics:** <5 min to team notification, 100% routing accuracy, <60 min avg SLA

---

### REPORT-1: Quality Trend Dashboard and Exports (4 pts)

**Objective:** Dashboard with trends, scheduled reports, exports

**Acceptance Criteria:**
- [ ] Dashboard: Real-time metrics (violation count, trend, top rules)
- [ ] 30-day trend per rule/domain
- [ ] Quality score: 100% - (violations / total_records)
- [ ] Scheduled reports: Daily email to governance lead, weekly to executives
- [ ] Exports: CSV, PDF for presentations
- [ ] Dashboard loads <2s, reports generate <5 min

**Implementation Approach:**
- Metrics aggregation queries (daily, hourly, real-time)
- Dashboard: Grafana or Tableau with real-time data
- Reports: Scheduled email with charts, quality scores
- Export format: CSV with detailed data, PDF with executive summary
- Drill-down: Navigate from dashboard to rule details, affected records

**Key Outputs:**
- Aggregation queries
- Dashboard definition (Grafana/Tableau)
- Report generation script
- Email scheduling
- Export utilities

**Success Metrics:** Dashboard <2s load, reports <5 min generation, <1% metric discrepancy

---

## 4. Testing and Validation (QA-1 through QA-6)

### QA-1: Completeness/Validity Validation (1 pt)

**Test Cases:**
- Missing required field → triggers COMP rule ✓
- Invalid datatype → triggers TYPE rule ✓
- Value outside range → triggers RANGE rule ✓
- Domain value invalid → triggers DOMAIN rule ✓
- Valid record → no violations ✓

### QA-2: Duplicate Detection Validation (1 pt)

**Test Cases:**
- Exact duplicate → detected, confidence 100% ✓
- Fuzzy duplicate (1 char diff) → detected, confidence >90% ✓
- Similar but distinct records → low confidence (<20%) ✓
- Performance: 100K records checked in <10s ✓

### QA-3: Consistency Validation (1 pt)

**Test Cases:**
- FK violation (invalid provider_id) → rule triggers ✓
- Cardinality violation (4 concurrent appointments, max 3) → rule triggers ✓
- Temporal violation (start > end) → rule triggers ✓
- Status transition invalid → rule triggers ✓

### QA-4: Severity Alert Validation (1 pt)

**Test Cases:**
- CRITICAL violations → publish blocked ✓
- HIGH violations (>3) → alert sent ✓
- Alert routing → correct team notified in <5 min ✓
- Runbook link → present in alert ✓

### QA-5: Trend Metrics Validation (1 pt)

**Test Cases:**
- Dashboard violation counts match database ✓
- 30-day trend shows correct progression ✓
- Quality score calculated correctly ✓
- Reports include all required metrics ✓

### QA-6: Publish Block Validation (1 pt)

**Test Cases:**
- Publish blocked on CRITICAL violations ✓
- Publish allowed on LOW violations only ✓
- Quarantine flow: Records moved to quarantine state ✓
- Manual approval: Corrected record re-validated and published ✓

---

## 5. Success Metrics Summary

| Task | Metric | Target |
|------|--------|--------|
| RULE-1 | Evaluation time per rule | <5ms |
| RULE-2 | Duplicate precision | 95%+ |
| RULE-3 | Cross-table coverage | 100% |
| PIPE-1 | In-pipeline latency | <100ms |
| PIPE-2 | CRITICAL block rate | 100% |
| GOV-1 | False positive rate (observe) | <5% |
| OBS-1 | Alert latency | <5 min |
| OBS-2 | Team notification latency | <5 min |
| REPORT-1 | Dashboard load time | <2s |
| QA-1 to QA-6 | Test pass rate | 100% |

---

## 6. Execution Dependencies

```
RULE-1, RULE-2, RULE-3 (parallel - 4 pts each)
    ↓
PIPE-1 (depends on RULE-1/2/3)
    ↓
PIPE-2 (depends on PIPE-1)
    ↓
GOV-1 (depends on PIPE-2)
    ↓
OBS-1 (depends on PIPE-2)
    ↓
OBS-2 (depends on OBS-1)
    ↓
REPORT-1 (depends on OBS-1, OBS-2)
    ↓
QA-1 through QA-6 (parallel - depends on all above)
```

---

## 7. Quick Reference - Task Points

- **RULE-1:** 4 pts (Completeness & Validity)
- **RULE-2:** 4 pts (Duplicate Detection)
- **RULE-3:** 4 pts (Consistency & Referential)
- **PIPE-1:** 4 pts (Scheduled & In-Pipeline)
- **PIPE-2:** 4 pts (Publish Gate & Quarantine)
- **GOV-1:** 3 pts (Policy Configuration)
- **OBS-1:** 3 pts (Metrics & Alerting)
- **OBS-2:** 3 pts (Ownership Routing)
- **REPORT-1:** 4 pts (Dashboard & Reports)
- **QA-1 to QA-6:** 6 pts (Validation)

**Total:** 38 pts

---

For detailed specifications of individual tasks, refer to:
- TASK-107-MASTER.md - Master overview
- RULE-1.md - Detailed completeness/validity rules
- Individual task files (RULE-2.md, PIPE-1.md, etc.) as needed during implementation
