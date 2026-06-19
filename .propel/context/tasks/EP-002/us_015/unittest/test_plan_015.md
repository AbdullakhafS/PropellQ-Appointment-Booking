# UNIT-TEST-PLAN-015: Implement Insurance Pre-Check Logic

User Story: US-015 (EP-002)
Source File: .propel/context/tasks/EP-002/us_015/us_015.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for insurance pre-check logic to validate insurer matching, ID/group format validation, confidence scoring, verification-flag assignment, patient notification, staff queue signaling, and audit logging.

---

## 2. Scope and Assumptions

### In Scope
- Insurance-plan catalog lookup and name matching rules.
- Member ID and optional group-number format validation.
- Confidence score calculation rules.
- Verification status decision thresholds.
- Notification and downstream review-queue event generation.

### Out of Scope
- Real insurer API verification integrations.
- Staff UI rendering behavior for pending queue.
- End-to-end persistence performance testing.

### Assumptions
- Pre-check service is invoked after intake submission.
- Scoring and validation policies are centralized in deterministic functions.
- Audit log repository is mockable.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Insurance-plan catalog source available for matching | UT-015-001 |
| AC-2 | Input data contract includes required insurance fields | UT-015-002 |
| AC-3 | Pre-check auto-triggers on intake submission event | UT-015-003 |
| AC-4 | Name matching (case-insensitive + partial) behavior | UT-015-004 |
| AC-5 | Member ID format validation by insurer rules | UT-015-005 |
| AC-6 | Optional group-number validation when provided | UT-015-006 |
| AC-7 | Confidence score rule matrix | UT-015-007, UT-015-008 |
| AC-8 | Verification-status flagging threshold behavior | UT-015-009 |
| AC-9 | Patient warning notification for unverified outcome | UT-015-010 |
| AC-10 | Staff pending-review signal for low-confidence cases | UT-015-011 |
| AC-11 | Audit logging captures full check metadata | UT-015-012 |

---

## 4. Unit Test Areas

## A. Catalog and Trigger

### UT-015-001: Plan matcher loads and searches insurer catalog entries
- Load catalog fixture with common insurers.
- Assert lookup returns expected matches.

### UT-015-002: Intake insurance payload validator enforces required fields
- Provide valid/invalid payloads.
- Assert required-field validation outcomes.

### UT-015-003: Intake-submit event triggers insurance pre-check service call
- Simulate intake completion event.
- Assert pre-check invocation without extra user action.

## B. Matching and Validation

### UT-015-004: Name matcher handles exact, case-insensitive, and partial matches
- Test insurer name variants.
- Assert matching score/source insurer id.

### UT-015-005: Member ID validator applies insurer-specific format rules
- Provide insurer-specific member id fixtures.
- Assert valid/invalid outcomes.

### UT-015-006: Group number validation runs only when optional value provided
- Test missing vs provided group numbers.
- Assert optional behavior and validation results.

## C. Scoring, Status, and Notifications

### UT-015-007: Confidence scorer computes expected score for exact/partial/no-id scenarios
- Provide scoring matrix fixtures.
- Assert score values align with policy tiers.

### UT-015-008: Unknown insurer path yields zero-confidence outcome
- Provide non-matching insurer input.
- Assert score 0 and unknown-plan classification.

### UT-015-009: Verification status sets verified or unverified based on threshold
- Test scores around threshold boundary.
- Assert status assignment logic.

### UT-015-010: Unverified status emits patient-facing warning payload
- Simulate low-confidence outcome.
- Assert warning message contract generated.

### UT-015-011: Low-confidence case emits pending-staff-review event
- Assert review-queue signal/event payload includes patient and appointment context.

## D. Audit Logging

### UT-015-012: Audit log writer records required fields for each pre-check run
- Assert log payload includes patient_id, insurance_name, member_id, confidence_score, status, timestamp, checked_by.

---

## 5. Test Data Strategy

- Insurer catalog fixtures including aliases and partial-match candidates.
- ID/group format fixtures by insurer rule.
- Score-boundary fixtures near verification threshold.

---

## 6. Mocking Strategy

- Mock catalog repository and scoring policy helper.
- Mock intake submission event bus and review-queue publisher.
- Mock audit log repository.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-015-003 through UT-015-011 before merge.

---

## 8. Exit Criteria

- AC-mapped pre-check logic tests pass.
- Scoring and status threshold behavior validated.
- Notification, queue, and audit side effects verified.
- Coverage thresholds achieved.

---

## 9. Suggested File Layout

- tests/unit/intake/insurance/InsuranceMatcherValidation.test.ts
- tests/unit/intake/insurance/InsuranceScoringStatus.test.ts
- tests/unit/intake/insurance/InsurancePrecheckEventsAudit.test.ts
- tests/unit/intake/insurance/__fixtures__/insurancePrecheck.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-015.
- [ ] Test cases UT-015-001 through UT-015-012 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
