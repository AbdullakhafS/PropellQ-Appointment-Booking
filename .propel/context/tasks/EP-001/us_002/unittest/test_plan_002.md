# UNIT-TEST-PLAN-002: Display Appointment Slots with Calendar

User Story: US-002 (EP-001)
Source File: .propel/context/tasks/EP-001/us_002/us_002.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for calendar slot presentation to validate month/week switching, slot interaction behavior, navigation controls, timezone-safe display formatting, and responsive calendar rendering logic.

---

## 2. Scope and Assumptions

### In Scope
- Calendar default month rendering and week toggle behavior.
- Slot color/status mapping logic.
- Slot click behavior and details panel rendering.
- Calendar navigation controls (previous/next/jump date intent).
- Timezone display formatting and footer metadata.

### Out of Scope
- Backend slot generation/search endpoint correctness.
- Browser-specific gesture/pinch implementation details.
- End-to-end performance instrumentation.

### Assumptions
- Calendar UI exposes view mode and navigation state via component state/store.
- Slot data is supplied from mockable service/hook.
- Unit tests verify logic and semantics, not pixel-perfect layout.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Month view with color-coded slot states renders by default | UT-002-001, UT-002-002 |
| AC-2 | Week view toggle works | UT-002-003 |
| AC-3 | Slot click opens details with select action | UT-002-004, UT-002-005 |
| AC-4 | Provider hover preview logic is wired | UT-002-006 |
| AC-5 | Calendar navigation controls update period correctly | UT-002-007, UT-002-008 |
| AC-6 | Responsive branches are handled by viewport-aware logic | UT-002-009 |
| AC-7 | Times display in patient timezone with offset context | UT-002-010 |
| AC-8 | Rendering and large-slot handling remain stable | UT-002-011 |

---

## 4. Unit Test Areas

## A. Calendar View and Slot Status

### UT-002-001: Month view is default on initial render
- Render calendar without explicit view override.
- Assert month view marker/state is active.

### UT-002-002: Slot status mapping applies expected visual state identifiers
- Provide available/booked/preferred slot fixtures.
- Assert each slot receives expected status label/class/token mapping.

## B. View Switching and Slot Detail Interaction

### UT-002-003: Week view toggle updates view state and slot layout mode
- Trigger Week View action.
- Assert component switches to week mode and renders time-slot structure.

### UT-002-004: Clicking slot opens detail panel with required fields
- Click a slot entry.
- Assert provider, specialty, duration, location, and Select action are displayed.

### UT-002-005: Slot details update when a different slot is selected
- Select slot A then slot B.
- Assert details panel reflects slot B and does not retain stale values.

## C. Provider Preview and Navigation

### UT-002-006: Provider preview trigger emits expected data payload
- Trigger hover/focus preview action on provider element.
- Assert preview model contains photo, credentials, and review count fields.

### UT-002-007: Previous/Next controls update visible period
- Trigger previous and next controls.
- Assert displayed date range changes as expected.

### UT-002-008: Jump-to-date action resolves target month correctly
- Trigger date jump action.
- Assert rendered month/year state matches selected date.

## D. Responsive and Timezone Logic

### UT-002-009: Viewport branch logic selects mobile vs tablet/desktop layout mode
- Mock mobile and desktop breakpoint utilities.
- Assert layout mode state changes according to breakpoint.

### UT-002-010: Slot times format to patient timezone and include offset label
- Provide UTC fixture and patient timezone context.
- Assert displayed local time and timezone indicator are correct.

## E. Robustness with Higher Slot Volume

### UT-002-011: Calendar rendering remains stable with 30+ slot fixtures
- Render month view with high slot count fixture.
- Assert all expected slots are represented and no duplicate key/error warnings surface.

---

## 5. Non-Functional Unit Checks

### UT-002-012: Keyboard accessibility for calendar navigation controls
- Assert controls are focusable and expose accessible names.
- Assert Enter/Space triggers intended navigation intent.

### UT-002-013: Loading and error state handling for calendar data fetch
- Mock loading then error states.
- Assert placeholder/fallback views render without component crash.

---

## 6. Test Data Strategy

- Provide fixtures for month and week views with mixed slot statuses.
- Include timezone-sensitive date/time fixtures around day boundaries.
- Add large dataset fixture (30+ slots) to validate rendering stability.

---

## 7. Mocking Strategy

- Mock calendar data source hook/service and provider preview source.
- Mock viewport and timezone utilities.
- Mock navigation callbacks instead of full router integration.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-002-001 through UT-002-011 before merge.

---

## 9. Exit Criteria

- AC-mapped calendar tests pass.
- Timezone and navigation logic validated.
- Coverage thresholds reached for calendar module.
- No flaky outcomes in 3 consecutive runs.

---

## 10. Suggested File Layout

- tests/unit/appointments/CalendarView.test.tsx
- tests/unit/appointments/CalendarInteraction.test.tsx
- tests/unit/appointments/CalendarTimezone.test.tsx
- tests/unit/appointments/CalendarAccessibility.test.tsx
- tests/unit/appointments/__fixtures__/calendar.fixtures.ts

---

## 11. Execution Checklist

1. Create calendar fixtures for month/week and status variants.
2. Implement default view and status mapping tests.
3. Implement slot interaction/detail tests.
4. Implement navigation and date jump tests.
5. Implement responsive/timezone assertions.
6. Add high-volume, loading/error robustness checks.
7. Run suite and verify coverage thresholds.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-002.
- [ ] Test cases UT-002-001 through UT-002-013 implemented.
- [ ] AC traceability retained.
- [ ] Coverage thresholds met.
- [ ] CI unit-test stage passes.