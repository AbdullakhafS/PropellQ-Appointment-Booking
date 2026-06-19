# UNIT-TEST-PLAN-030: Build Conflict Resolution UI (Side-by-Side Comparison)

User Story: US-030 (EP-003)
Source File: .propel/context/tasks/EP-003/us_030/us_030.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit tests for conflict-resolution UI logic to validate side-by-side comparison models, field-level conflict highlighting, resolution actions, and final merge payload generation.

## 2. Scope and Assumptions

### In Scope
- Conflict pair selection and comparison-state mapping.
- Field-level difference/highlight model generation.
- Choose-left/choose-right/manual-edit resolution actions.
- Final resolved payload construction and validation.

### Out of Scope
- Full visual diff rendering snapshots.
- End-to-end persistence and approval workflows.

### Assumptions
- Comparison and resolution logic is implemented in testable reducers/helpers.
- Conflict datasets include source metadata for both sides.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 side-by-side mapping | UT-030-001, UT-030-002 |
| AC-4 to AC-6 conflict highlighting and actions | UT-030-003, UT-030-004 |
| AC-7 to AC-9 resolved output validation | UT-030-005, UT-030-006 |

## 4. Unit Test Areas

### UT-030-001: Conflict comparator builds left/right view models with source labels
### UT-030-002: Field-level diff engine marks changed and unchanged fields correctly
### UT-030-003: Resolve-with-left action updates resolution state for selected field
### UT-030-004: Resolve-with-right/manual-edit actions update resolution state correctly
### UT-030-005: Finalize resolution validates all required conflicts resolved
### UT-030-006: Final payload includes chosen values and conflict audit metadata
### UT-030-007: Partial resolution blocks finalize with actionable validation errors
### UT-030-008: Reset/reopen conflict action restores prior unresolved state

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-030-001 through UT-030-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/conflict-ui/ConflictComparisonMapping.test.tsx
- tests/unit/clinical/conflict-ui/ConflictResolutionActions.test.tsx
- tests/unit/clinical/conflict-ui/__fixtures__/conflictResolution.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-030.
- [ ] Test cases UT-030-001 through UT-030-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
