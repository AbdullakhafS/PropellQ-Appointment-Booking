# UNIT-TEST-PLAN-068: Date/Provider/Location Filters

User Story: US-068 (EP-006)
Source File: .propel/context/tasks/EP-006/us_068/us_068.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for dashboard date/provider/location filters including availability, data refresh behavior, reset behavior, and invalid selection fallback handling.

---

## 2. Scope and Assumptions

### In Scope
- Date range, provider, and location filter controls.
- Dashboard re-query and render updates after filter changes.
- Clear/reset filters returning to default scope.
- Invalid selection fallback/error behavior.
- Filter state persistence on navigation-away and return.

### Out of Scope
- Saved custom filter views.
- Cross-dashboard blended filtering.

### Assumptions
- Server-side filtering is enforced through API query params.
- Filter state is managed via testable state store/hook.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Date/provider/location filters are available | UT-068-001, UT-068-002 |
| AC-2 | Dashboard data updates when filters change | UT-068-003, UT-068-004 |
| AC-3 | Clearing filters returns default scope | UT-068-005, UT-068-006 |
| AC-4 | Invalid selection shows helpful fallback/error | UT-068-007, UT-068-008 |

---

## 4. Unit Test Areas

### UT-068-001: All three filters render with expected defaults
- Render dashboard filter bar.
- Assert presence of date, provider, location controls and default values.

### UT-068-002: Controls are keyboard accessible with clear labels
- Assert tab navigation, roles, labels, and interaction semantics.

### UT-068-003: Changing each filter issues server-side query with params
- Update one filter at a time.
- Assert request payload reflects selected filter value.

### UT-068-004: Combined filter updates produce scoped KPI/chart refresh
- Apply multiple filters together.
- Assert refreshed data corresponds to combined scope.

### UT-068-005: Clear filters action resets UI control values
- Apply non-default selections then clear.
- Assert controls reset to baseline defaults.

### UT-068-006: Clear filters reloads unfiltered dashboard dataset
- After clear action, assert unfiltered API call and baseline metrics.

### UT-068-007: Invalid filter combination triggers fallback behavior
- Mock backend invalid combination response.
- Assert helpful message and safe fallback scope.

### UT-068-008: Invalid provider/location value resolves to safe default
- Inject invalid selected value.
- Assert control and query logic normalize to default/allowed value.

### UT-068-009: Filter state persistence survives navigation away/return
- Simulate unmount/remount with state cache.
- Assert previous valid filter state is restored.

### UT-068-010: Rapid filter changes settle on latest intended query state
- Simulate quick successive changes.
- Assert only final selection state is reflected in UI.

---

## 5. Test Data and Mocking Strategy

- Fixtures: default scope dataset, provider/location/date subsets, invalid-combination responses.
- Mock services: filter-aware API, validation/fallback mapper, persisted filter state store.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-068-001 through UT-068-008.

---

## 7. Suggested File Layout

- tests/unit/dashboard/DashboardFilterControls.test.tsx
- tests/unit/dashboard/DashboardFilterUpdateBehavior.test.tsx
- tests/unit/dashboard/DashboardFilterReset.test.tsx
- tests/unit/dashboard/DashboardFilterFallbacks.test.tsx
- tests/unit/dashboard/__fixtures__/dashboardFilters.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-068-001 through UT-068-010 implemented.
- [ ] AC traceability retained.
- [ ] Coverage and CI reliability targets met.
