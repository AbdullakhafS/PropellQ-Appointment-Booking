# UNIT-TEST-PLAN-082: Vendor BAA Process

User Story: US-082 (EP-007)
Source File: .propel/context/tasks/EP-007/us_082/us_082.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for vendor BAA process governance, including due diligence/risk checks, template approval workflow, periodic compliance review triggers, and vendor-scope change updates.

---

## 2. Scope and Assumptions

### In Scope
- Due diligence checklist and risk assessment step validation.
- BAA template availability and legal/compliance approval workflow checks.
- Periodic vendor compliance review trigger logic.
- Vendor-scope change handling and BAA status update requirements.

### Out of Scope
- Negotiation of custom vendor legal clauses.
- Technical onboarding of vendor integrations.

### Assumptions
- BAA process artifacts are represented in structured process docs/workflow schemas.
- Vendor compliance review schedule/triggers are codified in policy objects.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | BAA process includes due diligence and risk assessment | UT-082-001, UT-082-002 |
| AC-2 | BAA template exists and legal/compliance review is defined | UT-082-003, UT-082-004 |
| AC-3 | Signed vendor contracts trigger periodic compliance review | UT-082-005, UT-082-006 |
| AC-4 | Vendor scope changes update BAA status and documentation | UT-082-007, UT-082-008 |

---

## 4. Unit Test Areas

### UT-082-001: Due diligence checklist validator enforces required vendor risk fields
- Assert checklist includes data access, encryption, breach notice, audit rights items.

### UT-082-002: Risk assessment workflow requires completion before PHI-access approval
- Simulate incomplete risk review.
- Assert process state blocks progression.

### UT-082-003: BAA template registry returns approved template artifact
- Assert template exists and is retrievable by process workflow.

### UT-082-004: Approval workflow requires legal and compliance sign-off states
- Assert both approval checkpoints are mandatory.

### UT-082-005: Signed-contract event schedules periodic compliance review trigger
- Simulate contract-sign event.
- Assert review cadence schedule created.

### UT-082-006: Missed review window triggers compliance-alert status
- Simulate overdue review.
- Assert escalation/alert status output.

### UT-082-007: Vendor scope-change event requires BAA status update
- Simulate scope-change input.
- Assert status transitions to update-required/review state.

### UT-082-008: Scope-change path appends documentation revision entry
- Assert change log captures reason, actor, timestamp.

### UT-082-009: Process coverage report includes due diligence, template, review, and update controls
- Assert compliance report completeness across all process stages.

### UT-082-010: Invalid process states fail validation with actionable remediation
- Inject missing-template/no-review-cadence fixtures.
- Assert validator errors are explicit.

---

## 5. Test Data and Mocking Strategy

- Fixtures: vendor due diligence records, template approval states, signed/unsigned contract states, scope-change events.
- Mocks: workflow engine/state machine, approval registry, compliance scheduler, process-report builder.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-082-001 through UT-082-008.

---

## 7. Suggested File Layout

- tests/unit/compliance/VendorDueDiligenceProcess.test.ts
- tests/unit/compliance/BaaTemplateApprovalWorkflow.test.ts
- tests/unit/compliance/VendorComplianceReviewTrigger.test.ts
- tests/unit/compliance/VendorBaaScopeChangeUpdates.test.ts
- tests/unit/compliance/__fixtures__/vendorBaa.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-082-001 through UT-082-010 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
