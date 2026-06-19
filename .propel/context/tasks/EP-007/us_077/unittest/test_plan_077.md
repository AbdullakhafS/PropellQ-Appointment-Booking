# UNIT-TEST-PLAN-077: Log Integrity Checking (HMAC)

User Story: US-077 (EP-007)
Source File: .propel/context/tasks/EP-007/us_077/us_077.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for HMAC-based audit log integrity controls, including hash generation, tamper detection, periodic validation jobs, and compliance documentation outputs.

---

## 2. Scope and Assumptions

### In Scope
- Integrity hash generation for each audit record.
- Hash storage and metadata safety checks.
- Tamper-detection validation logic.
- Periodic integrity validation job behavior.
- Integrity evidence/documentation generation.

### Out of Scope
- Blockchain audit storage.
- Hardware security module internals.

### Assumptions
- HMAC key access is mediated by a key service adapter.
- Integrity checker and scheduled job runner are unit-testable via mocks.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Audit entry stores integrity hash | UT-077-001, UT-077-002 |
| AC-2 | Validation detects tampering on hash mismatch | UT-077-003, UT-077-004 |
| AC-3 | Periodic checks confirm integrity of stored entries | UT-077-005, UT-077-006 |
| AC-4 | Integrity design and validation results are documented | UT-077-007, UT-077-008 |

---

## 4. Unit Test Areas

### UT-077-001: New audit entry receives deterministic HMAC value
- Mock audit payload and key source.
- Assert generated integrity value exists and uses expected algorithm profile.

### UT-077-002: Integrity metadata is persisted in safe storage fields
- Assert hash metadata persistence excludes sensitive key material.

### UT-077-003: Integrity checker flags modified payload with stored hash mismatch
- Mutate stored log content fixture.
- Assert mismatch detection and failure status.

### UT-077-004: Integrity checker passes unchanged payload/hash pairs
- Provide valid entry/hash pair.
- Assert verification success.

### UT-077-005: Periodic validation job scans entries on configured cadence
- Mock scheduler trigger.
- Assert checker invoked across target record set.

### UT-077-006: Validation failures are logged and surfaced for review
- Inject mismatched entry in periodic run.
- Assert failure event is captured and logged.

### UT-077-007: Compliance report includes integrity method and key-handling description references
- Assert report output contains method identifiers and control references.

### UT-077-008: Compliance report includes validation run outcomes
- Assert report includes run timestamp, pass/fail totals, and anomaly references.

### UT-077-009: Optional chained-hash sequence validator detects broken chain
- Provide sequence with broken link.
- Assert chain validation fails.

### UT-077-010: Integrity checker error paths return safe diagnostics
- Mock key service/checker error.
- Assert non-sensitive error output with actionable status.

---

## 5. Test Data and Mocking Strategy

- Fixtures: valid entries, tampered entries, chained sequence sets, periodic-run snapshots.
- Mocks: key service adapter, audit store adapter, scheduler trigger, compliance report builder.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-077-001 through UT-077-008.

---

## 7. Suggested File Layout

- tests/unit/audit/AuditHmacGenerator.test.ts
- tests/unit/audit/AuditIntegrityChecker.test.ts
- tests/unit/audit/AuditIntegrityValidationJob.test.ts
- tests/unit/audit/AuditIntegrityComplianceReport.test.ts
- tests/unit/audit/__fixtures__/auditIntegrity.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-077-001 through UT-077-010 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
