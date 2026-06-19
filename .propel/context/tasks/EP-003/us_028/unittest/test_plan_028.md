# UNIT-TEST-PLAN-028: Build Code Verification UI (Accept, Reject, Override)

User Story: US-028 (EP-003)
Source File: .propel/context/tasks/EP-003/us_028/us_028.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for code-verification workflow state logic, including accept/reject/override actions, reason capture requirements, and audit-ready decision payloads.

## 2. Scope and Assumptions

### In Scope
- Verification queue row state.
- Accept, reject, and override actions.
- Mandatory reason capture for reject/override paths.
- Decision payload generation and local state updates.

### Out of Scope
- Full backend persistence integration.
- Visual styling and interaction animation checks.

### Assumptions
- Verification UI uses state reducers/selectors with mockable actions.
- Decision actions return deterministic payload contracts.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 queue and action state | UT-028-001, UT-028-002 |
| AC-4 to AC-6 reject/override validation | UT-028-003, UT-028-004 |
| AC-7 to AC-9 audit and status updates | UT-028-005, UT-028-006 |

## 4. Unit Test Areas

### UT-028-001: Verification list renders actionable items with decision state
### UT-028-002: Accept action updates item status and emits decision payload
### UT-028-003: Reject action requires reason before submission
### UT-028-004: Override action requires replacement code and rationale
### UT-028-005: Decision payload includes user, timestamp, and previous suggestion
### UT-028-006: Post-decision item is removed or marked finalized in queue state
### UT-028-007: Validation errors are surfaced for incomplete decision forms
### UT-028-008: Keyboard-triggered action events dispatch expected handlers

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-028-001 through UT-028-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/verification/CodeVerificationActions.test.tsx
- tests/unit/clinical/verification/CodeVerificationValidation.test.tsx
- tests/unit/clinical/verification/__fixtures__/verification.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-028.
- [ ] Test cases UT-028-001 through UT-028-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
