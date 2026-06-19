# UNIT-TEST-PLAN-076: Audit Log Retention (7 Years)

User Story: US-076 (EP-007)
Source File: .propel/context/tasks/EP-007/us_076/us_076.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for 7-year audit retention controls, archival/retrieval behavior, deletion eligibility enforcement, compliance evidence output, and approval-controlled deletion logging.

---

## 2. Scope and Assumptions

### In Scope
- Retention-period policy validation and enforcement logic.
- Archival tier placement and retrieval routing behavior.
- Expiration-based deletion eligibility checks.
- Deletion approval workflow and deletion audit logging.
- Compliance evidence/report generation.

### Out of Scope
- Historical analytics over retained logs.
- Storage cost optimization benchmarking.

### Assumptions
- Retention and archival are managed by policy services/lifecycle adapters.
- Deletion operation requires explicit approval metadata in workflow model.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Audit entries retained minimum 7 years before deletion | UT-076-001, UT-076-002 |
| AC-2 | Logs outside active window remain retrievable via archive | UT-076-003, UT-076-004 |
| AC-3 | Only expired records are deletion-eligible | UT-076-005, UT-076-006 |
| AC-4 | Retention policy and enforcement evidence documented | UT-076-007, UT-076-008 |
| AC-5 | Any deletion is logged and approval-controlled | UT-076-009, UT-076-010 |

---

## 4. Unit Test Areas

### UT-076-001: Retention policy validator enforces minimum 7-year threshold
- Provide policy fixtures below and above seven-year minimum.
- Assert below-minimum config rejected.

### UT-076-002: Lifecycle evaluator blocks deletion before retention maturity
- Evaluate records younger than 7 years.
- Assert deletion eligibility returns false.

### UT-076-003: Archival routing moves eligible old records to archive tier
- Mock records crossing active-window boundary.
- Assert archive-tier assignment behavior.

### UT-076-004: Retrieval service resolves active + archived records transparently
- Query records across tiers.
- Assert retrieval results include archived entries as expected.

### UT-076-005: Deletion selector includes only truly expired records
- Provide mixed-age record fixtures.
- Assert candidate set includes only expired subset.

### UT-076-006: Early-deletion attempt path is denied and audited as violation
- Attempt deletion on non-expired record.
- Assert denial and policy-violation log output.

### UT-076-007: Compliance evidence builder includes retention policy settings and enforcement proofs
- Assert report includes policy version, thresholds, and enforcement checks.

### UT-076-008: Evidence output includes archival retrieval verification records
- Assert report includes retrieval-test outcomes and timestamps.

### UT-076-009: Deletion workflow requires approval metadata before execution
- Execute deletion without approval.
- Assert operation blocked.
- Execute with approval fixture and assert allowed path.

### UT-076-010: Approved deletion emits immutable deletion-audit event
- Assert deletion audit record contains actor, approver, target scope, reason, timestamp.

### UT-076-011: Retention enforcement handles clock drift boundary safely
- Simulate boundary timestamps with slight skew.
- Assert deterministic eligibility around cutoff.

### UT-076-012: Archival/retrieval error handling preserves traceability
- Mock archive service failure.
- Assert retryable failure status and incident telemetry.

---

## 5. Test Data and Mocking Strategy

- Fixtures: retention-window boundaries, archived/active record sets, approved/unapproved deletion requests.
- Mocks: lifecycle policy engine, archive store adapter, retrieval gateway, approval service, deletion audit emitter.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-076-001 through UT-076-010.

---

## 7. Suggested File Layout

- tests/unit/audit/RetentionPolicyValidator.test.ts
- tests/unit/audit/RetentionLifecycleEnforcement.test.ts
- tests/unit/audit/ArchiveRetrievalBehavior.test.ts
- tests/unit/audit/DeletionApprovalControls.test.ts
- tests/unit/audit/RetentionComplianceEvidence.test.ts
- tests/unit/audit/__fixtures__/retention.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-076-001 through UT-076-012 implemented.
- [ ] AC-1 through AC-5 traceability retained.
- [ ] Coverage and CI reliability targets met.
