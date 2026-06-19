# UNIT-TEST-PLAN-022: Build 360 Patient Profile UI

User Story: US-022 (EP-003)
Source File: .propel/context/tasks/EP-003/us_022/us_022.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit tests for patient-profile UI state logic covering tab navigation, section rendering, cross-tab data synchronization, and loading/error states.

## 2. Scope and Assumptions

### In Scope
- Tab model and active-tab transitions.
- Overview, medications, allergies, and diagnoses section mappers.
- Shared patient-state synchronization across tabs.
- Loading, empty, and error states.

### Out of Scope
- Visual pixel-level layout checks.
- End-to-end routing behavior.

### Assumptions
- UI components use selector/state hooks that are mockable.
- Data adapters provide deterministic section models.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 tab and section behavior | UT-022-001, UT-022-002 |
| AC-4 to AC-6 state sync and updates | UT-022-003, UT-022-004 |
| AC-7 to AC-9 UX robustness | UT-022-005, UT-022-006 |

## 4. Unit Test Areas

### UT-022-001: Default tab selection opens expected overview state
### UT-022-002: Tab switching updates active section without stale state bleed
### UT-022-003: Medications/allergies/diagnoses mappers render normalized rows
### UT-022-004: Profile updates in one tab propagate to shared profile state
### UT-022-005: Loading and empty states show correct section-level placeholders
### UT-022-006: Error state shows recoverable fallback and retry intent
### UT-022-007: Keyboard tab navigation updates active tab index
### UT-022-008: Section reorder or missing fields do not crash container

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-022-001 through UT-022-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/profile/ProfileTabsState.test.tsx
- tests/unit/clinical/profile/ProfileSectionMapping.test.tsx
- tests/unit/clinical/profile/__fixtures__/profileUi.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-022.
- [ ] Test cases UT-022-001 through UT-022-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
