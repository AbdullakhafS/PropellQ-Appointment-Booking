# UNIT-TEST-PLAN-056: Personal Health Profile

User Story: US-056 (EP-006)
Source File: .propel/context/tasks/EP-006/us_056/us_056.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for the Personal Health Profile section to validate rendering of medications/allergies/diagnoses, correction-report path availability, patient-friendly formatting, and data refresh behavior.

---

## 2. Scope and Assumptions

### In Scope
- Profile section/container rendering logic.
- Data cards for medications, allergies, diagnoses, chronic conditions, care plans, and alerts (where present).
- Correction/report discrepancy call-to-action visibility and trigger behavior.
- Patient-friendly label/terminology rendering and fallback handling.
- Profile refresh behavior when source metadata/version changes.

### Out of Scope
- Clinical data edit workflow execution.
- Backend aggregation correctness across EP-003 sources.
- Full end-to-end routing and API transport concerns.

### Assumptions
- Component receives structured profile payload from a hook/service abstraction that can be mocked.
- Unit tests run with Jest/Vitest and Testing Library-style assertions.
- Correction path is exposed via callback or router intent function.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Medication, allergy, and diagnosis summaries are shown | UT-056-001, UT-056-002, UT-056-003 |
| AC-2 | Clear path exists to report corrections | UT-056-004, UT-056-005 |
| AC-3 | Profile appears in readable, patient-friendly format | UT-056-006, UT-056-007 |
| AC-4 | Profile refreshes when source data updates | UT-056-008, UT-056-009 |

---

## 4. Unit Test Areas

## A. Core Profile Rendering

### UT-056-001: Renders required profile sections with structured data
- Provide fixture containing medications, allergies, diagnoses, and chronic conditions.
- Assert all required section headers and key items are rendered.
- Assert each section displays expected entry count.

### UT-056-002: Renders care plan and alert summaries when available
- Provide fixture with active care plan and clinical alert metadata.
- Assert care plan and alert summary components render.
- Assert status/severity badges (if used) display correctly.

### UT-056-003: Handles missing optional sections gracefully
- Provide fixture with missing care plans or empty chronic conditions.
- Assert required sections still render normally.
- Assert optional empty-state placeholders/messages display without crashes.

## B. Correction Path Behavior

### UT-056-004: Correction/report CTA is visible in profile context
- Render profile with standard data.
- Assert correction/report action is present and accessible.

### UT-056-005: Clicking correction/report CTA triggers expected workflow intent
- Trigger CTA click.
- Assert callback/router intent invoked with expected destination/payload.

## C. Patient-Friendly Formatting and Terminology

### UT-056-006: Patient-friendly labels replace internal clinical jargon
- Provide payload containing internal/technical field names.
- Assert UI label mapping uses patient-friendly terminology.
- Assert unsupported raw labels are not surfaced directly.

### UT-056-007: Readability formatting for clinical values is consistent
- Validate formatted display for dosage/frequency, allergy reaction text, and diagnosis summary fields.
- Assert pending/approximate data includes quality notice text when flagged.

## D. Refresh and Update Behavior

### UT-056-008: Profile updates when version/timestamp changes
- Render with initial profile version/timestamp.
- Simulate refresh with updated payload metadata.
- Assert updated values replace stale values without full remount.

### UT-056-009: Refresh race conditions resolve to latest payload
- Simulate rapid sequential refreshes with different payload versions.
- Assert final rendered state reflects newest successful version.
- Assert no stale overwrite or unhandled promise error occurs.

## E. Robustness States

### UT-056-010: Loading state renders placeholders and prevents misleading interactions
- Mock loading state.
- Assert skeleton/loading indicators appear.
- Assert correction CTA behavior follows intended loading rule (disabled/hidden if applicable).

### UT-056-011: Empty profile state renders supportive messaging
- Mock empty profile payload.
- Assert informative empty-state message is shown.
- Assert correction path remains available when policy requires.

### UT-056-012: Error state remains stable and recoverable
- Mock data fetch error.
- Assert stable fallback/error message renders.
- Assert retry trigger (if present) calls expected handler.

---

## 5. Non-Functional Unit Checks

### UT-056-013: Accessibility checks for profile landmarks and actions
- Assert unique page/section heading structure.
- Assert CTA and key section controls have accessible names.

### UT-056-014: Stable rerender behavior for list sections
- Rerender with updated medications/allergies lists.
- Assert item keying prevents duplication and removes stale items correctly.

---

## 6. Test Data Strategy

- Use deterministic fixtures for: full profile, partial profile, empty profile, and pending-quality flags.
- Include label-mapping fixtures with clinical jargon inputs and expected patient-friendly outputs.
- Include versioned payload fixtures for refresh and race-condition tests.

---

## 7. Mocking Strategy

- Mock profile data hook/service responses (loading/success/error).
- Mock correction CTA workflow callback/router intent.
- Mock refresh trigger or version metadata watcher behavior.
- Mock time/version utilities used by update propagation logic.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-056-001 through UT-056-009 before merge.

---

## 9. Exit Criteria

- All AC-mapped unit tests pass.
- Coverage thresholds are met for health-profile module.
- No flaky behavior across 3 consecutive runs in local/CI.
- Refresh/update and correction-path tests pass consistently.

---

## 10. Suggested File Layout

- tests/unit/profile/HealthProfile.test.tsx
- tests/unit/profile/HealthProfileFormatting.test.tsx
- tests/unit/profile/HealthProfileRefresh.test.tsx
- tests/unit/profile/HealthProfileStates.test.tsx
- tests/unit/profile/__fixtures__/healthProfile.fixtures.ts

---

## 11. Execution Checklist

1. Create deterministic profile fixtures and mock builders.
2. Implement core rendering tests (UT-056-001..003).
3. Implement correction path tests (UT-056-004..005).
4. Implement terminology/formatting tests (UT-056-006..007).
5. Implement refresh/update tests (UT-056-008..009).
6. Implement loading/empty/error robustness tests (UT-056-010..012).
7. Add accessibility and rerender stability tests (UT-056-013..014).
8. Run unit suite and verify coverage thresholds.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-056.
- [ ] Test cases UT-056-001 through UT-056-014 implemented.
- [ ] Acceptance criteria traceability retained in test naming/comments.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes without flaky failures.
