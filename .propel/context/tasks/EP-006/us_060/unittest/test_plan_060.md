# UNIT-TEST-PLAN-060: Admin Operational Dashboard UI

User Story: US-060 (EP-006)
Source File: .propel/context/tasks/EP-006/us_060/us_060.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for the admin operational dashboard to validate secure admin access, KPI/chart rendering, filter-driven metric updates, and refresh freshness behavior.

---

## 2. Scope and Assumptions

### In Scope
- Admin-only route and role-guard behavior.
- KPI card and chart component rendering from metrics payload.
- Date/provider/location filter interactions.
- Refresh action and last-updated metadata display.

### Out of Scope
- End-to-end authorization across external identity systems.
- Full BI-grade analytics validation beyond dashboard-level KPIs.
- Cross-service load/performance benchmarking.

### Assumptions
- Dashboard data is loaded through service hooks with mockable responses.
- Route authorization guard is unit-testable in isolation.
- Test stack is Jest/Vitest with Testing Library.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Admin can navigate to operational dashboard | UT-060-001, UT-060-002 |
| AC-2 | KPI cards and charts are visible on load | UT-060-003, UT-060-004 |
| AC-3 | Metrics update when filters are applied | UT-060-005, UT-060-006 |
| AC-4 | Refresh shows latest available data | UT-060-007, UT-060-008 |

---

## 4. Unit Test Areas

## A. Access and Route Gating

### UT-060-001: Admin role is allowed to access dashboard route
- Mock authorized admin context.
- Assert route renders dashboard shell and navigation entry.

### UT-060-002: Non-admin role is denied dashboard access
- Mock non-admin context.
- Assert redirect/forbidden behavior and no metrics request dispatch.

## B. KPI and Chart Rendering

### UT-060-003: KPI cards render utilization, wait-time, and no-show values
- Mock successful metrics payload.
- Assert each KPI card displays expected values and labels.

### UT-060-004: Chart components render expected series and legends
- Mock chart dataset.
- Assert chart receives normalized series data and renders legend labels.

## C. Filter-Driven Updates

### UT-060-005: Date/provider/location filter changes trigger metric reload
- Simulate filter control updates.
- Assert query call includes selected filter params.

### UT-060-006: Filtered response updates KPI and chart content deterministically
- Return filtered payload.
- Assert previous values are replaced and no stale values remain.

## D. Refresh and Freshness

### UT-060-007: Refresh action requests latest metrics and updates timestamp
- Trigger refresh control.
- Assert reload call fired and last-updated metadata changes.

### UT-060-008: Failed refresh shows recoverable error without clearing current metrics
- Mock refresh failure.
- Assert user-visible error and retention of prior dashboard values.

## E. Robustness and Accessibility

### UT-060-009: Loading and empty states are handled safely
- Mock loading and empty payload variants.
- Assert placeholders and empty-state messaging render correctly.

### UT-060-010: Partial API payload does not crash dashboard rendering
- Omit optional fields from payload.
- Assert component applies defaults and remains interactive.

### UT-060-011: Keyboard and accessible labels exist for filters/refresh controls
- Assert filter controls and refresh action have accessible names/roles.

### UT-060-012: Rapid filter changes preserve latest request outcome
- Simulate quick successive filter changes.
- Assert latest response wins and UI reflects newest scope.

---

## 5. Test Data and Mocking Strategy

- Metrics fixtures: baseline, filtered, empty, partial, and error states.
- Role fixtures: admin and non-admin auth contexts.
- Time fixtures: deterministic last-updated timestamps.
- Mock route guard, metrics API hooks, and chart adapters.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-060-001 through UT-060-008.

---

## 7. Suggested File Layout

- tests/unit/admin/AdminDashboardAccess.test.tsx
- tests/unit/admin/AdminDashboardKpiChart.test.tsx
- tests/unit/admin/AdminDashboardFilters.test.tsx
- tests/unit/admin/AdminDashboardRefresh.test.tsx
- tests/unit/admin/__fixtures__/adminDashboard.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-060-001 through UT-060-012 implemented.
- [ ] AC-1 through AC-4 traceability preserved.
- [ ] Coverage thresholds met.
- [ ] CI unit tests pass without flaky failures.
