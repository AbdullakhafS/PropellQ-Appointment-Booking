# UNIT-TEST-PLAN-054: Upcoming Appointments with Actions

User Story: US-054 (EP-006)
Source File: .propel/context/tasks/EP-006/us_054/us_054.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for the Upcoming Appointments section to validate rendering of appointment details, policy-driven action visibility, past-appointment filtering behavior, and action workflow initiation.

---

## 2. Scope and Assumptions

### In Scope
- Upcoming appointments list/container rendering logic.
- Appointment card details (provider, date/time, location, status).
- Action button visibility based on eligibility flags and policy.
- Client-side action trigger callbacks for reschedule/cancel/view details.
- UI behavior for loading, empty, and error states.

### Out of Scope
- Full reschedule or cancel workflow execution.
- Backend policy engine correctness (covered by backend tests).
- End-to-end routing and API transport behavior.

### Assumptions
- UI component uses service hooks or props for appointment data and eligibility flags.
- Unit test framework is Jest/Vitest with Testing Library style assertions.
- Navigation/workflow actions are exposed as callbacks or router intent helpers that can be mocked.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Upcoming appointments display clear key details | UT-054-001, UT-054-002 |
| AC-2 | Eligible appointments show reschedule/cancel actions | UT-054-003, UT-054-004 |
| AC-3 | Past appointments are excluded from upcoming list | UT-054-005, UT-054-006 |
| AC-4 | Clicking action initiates appropriate workflow | UT-054-007, UT-054-008, UT-054-009 |

---

## 4. Unit Test Areas

## A. List and Detail Rendering

### UT-054-001: Renders upcoming appointment cards with required fields
- Provide fixture with two future appointments.
- Assert provider name, date/time, location, and status badge render for each item.
- Assert card count matches input appointments.

### UT-054-002: Handles compact display formatting consistently
- Provide fixture with varied date/time/location values.
- Assert formatting function output appears in expected compact patient-friendly format.
- Assert fallback placeholder behavior for optional missing location subfields.

## B. Eligibility and Action Button Visibility

### UT-054-003: Shows reschedule/cancel buttons when appointment is eligible
- Provide fixture with eligibility flags true.
- Assert reschedule and cancel actions are visible and enabled.

### UT-054-004: Disables or hides actions when policy disallows changes
- Provide fixture with eligibility flags false.
- Assert reschedule/cancel controls are hidden or disabled per component rule.
- Assert tooltip/helper text (if defined) appears for disallowed actions.

## C. Upcoming Filter Behavior

### UT-054-005: Excludes appointments in the past from rendered upcoming list
- Provide mixed fixture with past and future appointments.
- Assert only future appointments render.

### UT-054-006: Boundary-time handling for appointment filtering
- Freeze clock and provide appointment at boundary conditions.
- Assert exactly-on-threshold behavior follows product rule.
- Assert no flaky behavior due to local timezone conversion in unit logic.

## D. Action Workflow Initiation

### UT-054-007: Reschedule action invokes correct workflow intent
- Click reschedule button on eligible appointment.
- Assert callback/router intent called with appointment identifier and expected action type.

### UT-054-008: Cancel action invokes correct workflow intent
- Click cancel button on eligible appointment.
- Assert callback/router intent called with appointment identifier and expected action type.

### UT-054-009: View details action invokes details workflow intent
- Click view details action.
- Assert callback/router intent called with details destination payload.

## E. Robustness States

### UT-054-010: Loading state renders skeleton or placeholder list
- Mock loading state from data hook.
- Assert loading UI appears and actions are not interactive.

### UT-054-011: Empty state renders when no upcoming appointments exist
- Mock no future appointments.
- Assert empty-state message and optional CTA are rendered.

### UT-054-012: Partial error state does not crash component
- Mock error response for appointment fetch.
- Assert stable fallback message renders and component remains mounted.

---

## 5. Non-Functional Unit Checks

### UT-054-013: Accessibility naming for action controls
- Assert reschedule/cancel/details controls have accessible names.
- Assert status badges have readable text content.

### UT-054-014: Stable keying and rerender behavior
- Rerender with updated appointment list.
- Assert no duplicate row rendering and removed items disappear correctly.

---

## 6. Test Data Strategy

- Maintain deterministic fixtures for future, past, mixed, and boundary-time appointments.
- Include eligibility combinations: fully allowed, partially allowed, fully disallowed.
- Use fixed timestamps with timezone-explicit values to avoid flaky tests.

---

## 7. Mocking Strategy

- Mock appointment data source (hook/service) with controllable states.
- Mock clock/time utilities for boundary filtering tests.
- Mock router/navigation or workflow dispatch callbacks.
- Mock policy/eligibility fields directly from fixture payloads.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-054-001 through UT-054-009 before merge.

---

## 9. Exit Criteria

- All AC-mapped test cases pass.
- Coverage thresholds met for appointments dashboard module.
- No flaky behavior in 3 consecutive local/CI runs.
- Action trigger tests prove correct workflow initiation payloads.

---

## 10. Suggested File Layout

- tests/unit/dashboard/UpcomingAppointments.test.tsx
- tests/unit/dashboard/UpcomingAppointmentsActions.test.tsx
- tests/unit/dashboard/UpcomingAppointmentsFilter.test.tsx
- tests/unit/dashboard/UpcomingAppointmentsStates.test.tsx
- tests/unit/dashboard/__fixtures__/upcomingAppointments.fixtures.ts

---

## 11. Execution Checklist

1. Create deterministic appointment fixtures and mock builders.
2. Implement rendering/detail tests (UT-054-001..002).
3. Implement eligibility/action visibility tests (UT-054-003..004).
4. Implement upcoming filter tests (UT-054-005..006).
5. Implement action initiation tests (UT-054-007..009).
6. Implement loading/empty/error robustness tests (UT-054-010..012).
7. Add accessibility and rerender stability checks (UT-054-013..014).
8. Run full unit suite and verify thresholds.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-054.
- [ ] Test cases UT-054-001 through UT-054-014 implemented.
- [ ] Acceptance criteria traceability retained in test naming/comments.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes without flaky failures.
