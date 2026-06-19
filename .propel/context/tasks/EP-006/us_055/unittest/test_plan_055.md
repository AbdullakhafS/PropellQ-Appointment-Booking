# UNIT-TEST-PLAN-055: Past Appointments with Clinical Notes

User Story: US-055 (EP-006)
Source File: .propel/context/tasks/EP-006/us_055/us_055.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for past appointment history and released clinical notes behavior, including secure note access visibility, unavailable-note messaging, and stable detail loading.

---

## 2. Scope and Assumptions

### In Scope
- Past appointment list rendering (date, provider, status).
- Released notes/summary link visibility and action triggers.
- Unavailable-note messaging for visits without released content.
- Past-appointment detail panel loading and error handling.
- List states: loading, empty, and partial error.

### Out of Scope
- Full EHR access and unrestricted clinical content policies.
- Backend release-policy correctness across EP-003 sources.
- End-to-end file download transport behavior.

### Assumptions
- Component receives appointment history and release flags via service hook/props.
- Secure note/document access is represented via masked link metadata or action callback.
- Unit tests use Jest/Vitest and Testing Library style assertions.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Past visits appear in historical list | UT-055-001, UT-055-002 |
| AC-2 | Released notes can be viewed/downloaded | UT-055-003, UT-055-004 |
| AC-3 | Clear message shown when notes unavailable | UT-055-005, UT-055-006 |
| AC-4 | Selecting past appointment loads details without errors | UT-055-007, UT-055-008 |

---

## 4. Unit Test Areas

## A. Historical List Rendering

### UT-055-001: Renders past appointment list with required metadata
- Provide fixture with multiple historical visits.
- Assert date, provider, and status are rendered for each row.
- Assert list count matches expected historical items.

### UT-055-002: Supports empty history state gracefully
- Provide fixture with no past visits.
- Assert empty-state message appears.
- Assert component remains stable and interactive controls are appropriate.

## B. Released Notes Access Behavior

### UT-055-003: Shows view/download actions when notes are released
- Provide appointment fixture with releasedNote flag and link metadata.
- Assert view and/or download action is visible and enabled.

### UT-055-004: Note action trigger emits expected workflow intent
- Trigger note view/download action.
- Assert callback/router intent receives expected appointment/note payload.
- Assert no unintended action is fired for unrelated row elements.

## C. Unavailable Notes Handling

### UT-055-005: Unreleased notes show clear unavailable message
- Provide fixture where visit has no released notes.
- Assert unavailable-note message renders in the visit context.
- Assert restricted actions are hidden or disabled.

### UT-055-006: Mixed released/unreleased visits render per-row correctly
- Provide fixture with both released and unreleased visits.
- Assert each row shows correct action/message state independently.

## D. Past Appointment Detail Loading

### UT-055-007: Selecting a past visit loads detail panel data
- Click/select a past appointment row.
- Assert detail panel renders expected visit details.
- Assert detail fetch callback (if used) is called once with selected visit id.

### UT-055-008: Detail load failure shows safe fallback without crash
- Mock detail-load error.
- Assert error/fallback message is displayed.
- Assert user can still select another visit afterward.

## E. Robustness and UX States

### UT-055-009: Loading state behavior for history list
- Mock loading state for history query.
- Assert placeholders/skeleton are shown.
- Assert row actions are not active during loading.

### UT-055-010: Sorting or grouping consistency by recency
- Provide unsorted historical fixture.
- Assert rendered order follows recency rule (most recent first, if expected).

### UT-055-011: Secure link presence/absence handling
- Provide malformed/expired link metadata fixture.
- Assert secure link action is safely suppressed and message is shown.

---

## 5. Non-Functional Unit Checks

### UT-055-012: Accessibility checks for history list and note actions
- Assert row labels and action buttons have accessible names.
- Assert status and unavailable-note messages are readable to assistive tech.

### UT-055-013: Stable rerender behavior on updated history payload
- Rerender with updated visit set.
- Assert removed rows disappear and updated rows re-render without duplicates.

---

## 6. Test Data Strategy

- Maintain deterministic fixtures for: all-released, none-released, mixed-release, empty-history, and detail-error scenarios.
- Use fixed timestamps to avoid locale/timezone flakiness in historical ordering.
- Include secure-link metadata variants for valid, missing, and invalid link states.

---

## 7. Mocking Strategy

- Mock history list data hook/service with loading/success/error states.
- Mock detail panel data fetch callback or service.
- Mock note action workflow callback/router intent.
- Mock time formatting or sorting helpers where behavior is date-sensitive.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-055-001 through UT-055-008 before merge.

---

## 9. Exit Criteria

- All AC-mapped test cases pass.
- Coverage thresholds met for past-appointments/profile-history module.
- No flaky behavior in 3 consecutive local or CI runs.
- Notes-access and detail-loading scenarios pass consistently.

---

## 10. Suggested File Layout

- tests/unit/history/PastAppointmentsList.test.tsx
- tests/unit/history/PastAppointmentsNotes.test.tsx
- tests/unit/history/PastAppointmentsDetail.test.tsx
- tests/unit/history/PastAppointmentsStates.test.tsx
- tests/unit/history/__fixtures__/pastAppointments.fixtures.ts

---

## 11. Execution Checklist

1. Create deterministic history and notes fixtures.
2. Implement list rendering tests (UT-055-001..002).
3. Implement released-notes access tests (UT-055-003..004).
4. Implement unavailable-notes tests (UT-055-005..006).
5. Implement detail loading tests (UT-055-007..008).
6. Implement robustness tests (UT-055-009..011).
7. Add accessibility and rerender stability tests (UT-055-012..013).
8. Run full unit suite and verify coverage thresholds.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-055.
- [ ] Test cases UT-055-001 through UT-055-013 implemented.
- [ ] Acceptance criteria traceability preserved in test naming/comments.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes without flaky failures.
