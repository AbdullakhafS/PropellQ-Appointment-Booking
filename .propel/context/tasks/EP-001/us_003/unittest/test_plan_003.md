# UNIT-TEST-PLAN-003: Select Appointment and Lock Slot During Checkout

User Story: US-003 (EP-001)
Source File: .propel/context/tasks/EP-001/us_003/us_003.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for slot selection and checkout locking behavior to validate selected-slot state transitions, checkout validation rules, reservation conflict handling, and accessible mobile-ready form interactions.

---

## 2. Scope and Assumptions

### In Scope
- Slot selection and sidebar summary state updates.
- Preferred slot swap option input and optionality behavior.
- Confirm action request model construction for lock/booking flow.
- Conflict and validation error handling paths.
- Confirmation summary rendering prior to final submission.

### Out of Scope
- Real distributed lock correctness under production concurrency.
- End-to-end booking API transport/security verification.
- Full mobile visual layout regression.

### Assumptions
- Checkout logic is split across testable component/services.
- Reservation and booking API calls are mockable.
- Conflict outcomes are surfaced via deterministic error payloads.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Slot selection highlights and details sidebar update | UT-003-001, UT-003-002 |
| AC-2 | Preferred slot swap option is optional and captured correctly | UT-003-003 |
| AC-3 | Confirm flow applies lock request with reservation metadata | UT-003-004, UT-003-005 |
| AC-4 | Concurrent conflict displays message and returns to calendar flow | UT-003-006 |
| AC-5 | Checkout required fields validate with inline errors | UT-003-007, UT-003-008 |
| AC-6 | Confirmation summary includes required booking details | UT-003-009 |
| AC-7 | Mobile-specific submission behavior is preserved in logic layer | UT-003-010 |
| AC-8 | Accessibility semantics for labels and errors are present | UT-003-011 |

---

## 4. Unit Test Areas

## A. Selection and Summary State

### UT-003-001: Selecting a slot updates selected state and visual marker
- Trigger slot selection event.
- Assert selected identifier/state updates.
- Assert selected indicator token/class is applied.

### UT-003-002: Sidebar summary reflects selected slot details
- Select slot fixture.
- Assert sidebar shows date, time, provider, and location.

## B. Preferred Slot Swap Input

### UT-003-003: Preferred slot field remains optional and captured only when provided
- Leave preferred slot input empty then submit.
- Assert request model omits preferred slot field.
- Set preferred slot and assert model includes selected value.

## C. Lock and Confirm Flow

### UT-003-004: Confirm action sends booking/lock request with selected slot context
- Click Confirm Booking with valid form.
- Assert booking service invoked with selected slot and required fields.

### UT-003-005: Reservation expiry metadata is tracked in local flow state
- Mock lock response with reservation timeout.
- Assert reservation context stores expiry/lock token fields for next step.

## D. Conflict and Error Handling

### UT-003-006: Conflict response triggers slot-unavailable message and recovery path
- Mock booking response as slot conflict.
- Assert conflict modal/message appears.
- Assert flow returns to slot selection state and clears stale reservation context.

## E. Form Validation and Confirmation Summary

### UT-003-007: Required fields enforce validation before submit
- Submit with missing required inputs.
- Assert form submission blocked.
- Assert inline validation messages appear.

### UT-003-008: Terms checkbox is mandatory for final submission
- Submit with terms unchecked.
- Assert error is shown and API call is not made.

### UT-003-009: Confirmation summary shows required booking details
- Populate checkout with valid data.
- Assert summary includes appointment datetime, provider, location, duration, and cost estimate field.

## F. Mobile and Accessibility Behavior

### UT-003-010: Mobile-mode submit handler remains functional
- Mock mobile breakpoint/state branch.
- Assert submit action still routes through expected POST intent and does not require desktop-only controls.

### UT-003-011: Error announcements and labels are accessibility-safe
- Assert inputs are labeled and errors map via aria-describedby/live region semantics.

---

## 5. Non-Functional Unit Checks

### UT-003-012: Duplicate submit guard prevents double booking request firing
- Trigger rapid double-click on confirm.
- Assert only one booking request is issued while pending.

### UT-003-013: Reservation expiry state cleanup occurs after timeout/cancel
- Simulate expiry or explicit cancellation path.
- Assert lock metadata is cleared deterministically.

---

## 6. Test Data Strategy

- Fixtures for selectable slots, conflict slots, and optional preferred alternatives.
- Form fixtures for complete and incomplete checkout payloads.
- Deterministic reservation timeout values for lock-state assertions.

---

## 7. Mocking Strategy

- Mock booking/lock service responses: success, conflict, validation failure.
- Mock timer utilities for reservation expiry tests.
- Mock breakpoint utility for mobile path coverage.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-003-001 through UT-003-011 before merge.

---

## 9. Exit Criteria

- All AC-linked selection/checkout tests pass.
- Conflict recovery and validation paths verified.
- Coverage thresholds achieved.
- No flaky outcomes across 3 consecutive runs.

---

## 10. Suggested File Layout

- tests/unit/appointments/SlotSelection.test.tsx
- tests/unit/appointments/CheckoutValidation.test.tsx
- tests/unit/appointments/CheckoutConflict.test.tsx
- tests/unit/appointments/CheckoutAccessibility.test.tsx
- tests/unit/appointments/__fixtures__/checkout.fixtures.ts

---

## 11. Execution Checklist

1. Build slot and checkout fixtures.
2. Implement selection/sidebar tests.
3. Implement preferred slot and lock-request tests.
4. Implement conflict and validation tests.
5. Add summary, mobile, and accessibility tests.
6. Add duplicate-submit and timeout cleanup tests.
7. Run suite and confirm coverage targets.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-003.
- [ ] Test cases UT-003-001 through UT-003-013 implemented.
- [ ] AC traceability retained.
- [ ] Coverage thresholds met.
- [ ] CI unit-test stage passes.