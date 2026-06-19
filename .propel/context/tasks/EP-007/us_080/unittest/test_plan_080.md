# UNIT-TEST-PLAN-080: Data Retention and Deletion Policy Documentation

User Story: US-080 (EP-007)
Source File: .propel/context/tasks/EP-007/us_080/us_080.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for policy-document quality controls covering retention period definitions, deletion criteria/approvals, audit-reference readiness, and version-controlled policy updates.

---

## 2. Scope and Assumptions

### In Scope
- Validation of policy structure/content requirements.
- Retention period and deletion criteria rule completeness checks.
- Approval workflow documentation presence checks.
- Audit-reference and version-history verification.

### Out of Scope
- Full implementation testing of archival infrastructure.
- Legal interpretation validation beyond specified checklist rules.

### Assumptions
- Policy artifacts are represented in structured markdown/template fields.
- Validation scripts/checkers are unit-testable as pure functions.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Retention periods for PHI/audit data are clearly documented and compliant | UT-080-001, UT-080-002 |
| AC-2 | Deletion criteria and approval controls are documented | UT-080-003, UT-080-004 |
| AC-3 | Policies are referenceable during audits | UT-080-005, UT-080-006 |
| AC-4 | Policy updates are version-controlled with change history | UT-080-007, UT-080-008 |

---

## 4. Unit Test Areas

### UT-080-001: Policy validator confirms PHI and audit retention sections exist
- Parse policy artifact fixture.
- Assert required sections and headings are present.

### UT-080-002: Retention values satisfy configured compliance minimum thresholds
- Provide threshold boundary fixtures.
- Assert under-threshold values fail validation.

### UT-080-003: Deletion criteria section requires explicit eligibility rules
- Assert criteria define when records may be deleted.

### UT-080-004: Approval workflow section requires reviewer/approver steps
- Assert documented approval controls are present and non-empty.

### UT-080-005: Audit-readiness reference builder links policy to compliance materials
- Assert policy references are included in audit artifact index.

### UT-080-006: Policy references include operational lifecycle mappings
- Assert links to storage/archive/lifecycle process sections exist.

### UT-080-007: Version metadata validator enforces version and revision fields
- Assert document contains version, date, and owner metadata.

### UT-080-008: Change-history validator requires immutable revision entries
- Assert history section appends updates and preserves prior revisions.

### UT-080-009: Missing mandatory sections fail quality gate with actionable messages
- Remove required section in fixture.
- Assert quality gate fails with clear remediation output.

### UT-080-010: Stakeholder review status field validation ensures audit-ready state
- Assert policy includes review approval status markers.

---

## 5. Test Data and Mocking Strategy

- Fixtures: valid policy document, missing-section variants, under-threshold retention variants, no-version-history variants.
- Mocks: compliance threshold provider, audit-reference registry writer.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-080-001 through UT-080-008.

---

## 7. Suggested File Layout

- tests/unit/compliance/RetentionPolicyStructureValidator.test.ts
- tests/unit/compliance/RetentionDeletionCriteriaValidator.test.ts
- tests/unit/compliance/PolicyAuditReferenceValidator.test.ts
- tests/unit/compliance/PolicyVersioningValidator.test.ts
- tests/unit/compliance/__fixtures__/retentionPolicyDocs.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-080-001 through UT-080-010 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
