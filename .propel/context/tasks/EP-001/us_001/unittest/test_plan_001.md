# UNIT-TEST-PLAN-001: Search Appointments with Filters

User Story: US-001 (EP-001)
Source File: .propel/context/tasks/EP-001/us_001/us_001.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for appointment search filtering to validate cumulative filter behavior, result rendering, empty-state handling, pagination/sorting logic, and accessibility-safe form interactions.

---

## 2. Scope and Assumptions

### In Scope
- Filter form state management (date range, time-of-day, provider name, specialty).
- Query payload construction for search requests.
- Cumulative filtering behavior and reactive updates.
- Search result rendering with required slot/provider fields.
- Empty-state and pagination/sorting client logic.

### Out of Scope
- Database query performance verification and true backend latency SLAs.
- End-to-end provider detail navigation and booking checkout flow.
- Browser/device visual regression testing.

### Assumptions
- Search UI is implemented with React and tested via Jest/Vitest + Testing Library.
- API/data hook for search results is mockable.
- Accessibility checks at unit level cover semantic/label assertions, not full audits.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Four filter categories are displayed and usable | UT-001-001, UT-001-002 |
| AC-2 | Availability request executes and displays returned slots | UT-001-003, UT-001-004 |
| AC-3 | Results include required appointment/provider fields | UT-001-005 |
| AC-4 | Filters are cumulative and update results without reload | UT-001-006, UT-001-007 |
| AC-5 | Helpful message shown when no slots match | UT-001-008 |
| AC-6 | Responsive behavior is controlled correctly by UI state/hooks | UT-001-009 |
| AC-7 | Labels, keyboard behavior, and accessibility semantics are present | UT-001-010, UT-001-011 |

---

## 4. Unit Test Areas

## A. Filter Controls and State

### UT-001-001: Renders all required filter controls
- Render search module.
- Assert date range, time-of-day, provider autocomplete, and specialty dropdown are present.
- Assert each control has an associated label.

### UT-001-002: Filter state updates with user input
- Simulate selecting date range/time window and entering provider/specialty.
- Assert internal state/query model reflects selected values.

## B. Search Request and Result Rendering

### UT-001-003: Submits search with expected normalized query payload
- Apply filter selections.
- Trigger search/refetch action.
- Assert data service is called with expected request payload.

### UT-001-004: Displays returned appointment slots from mock service
- Mock successful search response.
- Assert list/grid renders matching item count.

### UT-001-005: Result card renders required fields and primary action
- Provide one slot fixture.
- Assert provider name, specialty, date/time, location, and Book Now action are rendered.

## C. Cumulative Filtering Behavior

### UT-001-006: Multiple filters are applied cumulatively
- Mock result subsets for single vs combined filters.
- Assert combined filter returns stricter result set.

### UT-001-007: Results update reactively without full remount
- Change one filter after initial render.
- Assert updated data appears.
- Assert top-level container remains mounted.

## D. Empty State, Pagination, and Sorting

### UT-001-008: Displays helpful no-results guidance
- Mock empty search response.
- Assert no-results message and suggestion text are rendered.

### UT-001-009: Pagination and sorting handlers update query model
- Trigger page change/sort selection.
- Assert updated request model contains page/sort values.

## E. Accessibility and Keyboard Safety

### UT-001-010: Labels and input associations are valid
- Assert inputs are queryable by accessible label.
- Assert no unlabeled required control.

### UT-001-011: Keyboard interaction triggers expected search behavior
- Simulate keyboard navigation and submit key path.
- Assert focusable controls are reachable and search trigger executes.

---

## 5. Non-Functional Unit Checks

### UT-001-012: Debounced provider autocomplete avoids duplicate calls
- Simulate rapid input changes.
- Assert debounced service calls remain within expected count.

### UT-001-013: Error fallback for search request failure is stable
- Mock service failure.
- Assert error state renders and component does not crash.

---

## 6. Test Data Strategy

- Maintain fixtures for broad result set, narrowed result set, and empty result set.
- Include provider names/specialties with mixed casing for normalization checks.
- Freeze date/time where filtering depends on relative boundaries.

---

## 7. Mocking Strategy

- Mock search API hook/service with loading/success/error variants.
- Mock pagination/sorting callbacks and router intent for result actions.
- Mock viewport utility where responsive branch logic is component-driven.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-001-001 through UT-001-011 before merge.

---

## 9. Exit Criteria

- All AC-mapped tests pass.
- Search filter logic reaches coverage thresholds.
- No flaky behavior across 3 consecutive runs.
- Error and empty states are verified stable.

---

## 10. Suggested File Layout

- tests/unit/appointments/SearchFilters.test.tsx
- tests/unit/appointments/SearchResults.test.tsx
- tests/unit/appointments/SearchBehavior.test.tsx
- tests/unit/appointments/SearchAccessibility.test.tsx
- tests/unit/appointments/__fixtures__/search.fixtures.ts

---

## 11. Execution Checklist

1. Build deterministic search fixtures.
2. Implement filter state and request payload tests.
3. Implement result rendering and cumulative filter tests.
4. Implement empty/pagination/sort behavior tests.
5. Add keyboard/accessibility assertions.
6. Add debounce and error-state robustness checks.
7. Run unit suite and confirm thresholds.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-001.
- [ ] Test cases UT-001-001 through UT-001-013 implemented.
- [ ] Acceptance criteria traceability preserved.
- [ ] Coverage thresholds met.
- [ ] CI unit-test stage passes.