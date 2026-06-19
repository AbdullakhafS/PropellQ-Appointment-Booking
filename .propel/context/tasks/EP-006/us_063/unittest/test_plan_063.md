# UNIT-TEST-PLAN-063: Appointment Utilization Analytics

User Story: US-063 (EP-006)
Source File: .propel/context/tasks/EP-006/us_063/us_063.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for appointment utilization analytics including KPI visibility, booked-vs-available visualization, filter responsiveness, and scope-specific rendering.

---

## 2. Scope and Assumptions

### In Scope
- Utilization KPI card and summary counts.
- Booked vs available slot chart rendering.
- Provider/specialty/location filter handling.
- Scope indicator behavior for selected provider/location.

### Out of Scope
- Room occupancy integrations.
- Workforce time tracking outside appointment data.

### Assumptions
- Utilization is computed as booked slots / available slots.
- API returns aggregated metrics by selected dimensions.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Utilization metrics are visible | UT-063-001, UT-063-002 |
| AC-2 | Utilization data updates with filters | UT-063-003, UT-063-004 |
| AC-3 | Booked vs available comparisons are shown | UT-063-005, UT-063-006 |
| AC-4 | Utilization scopes by provider/location selection | UT-063-007, UT-063-008 |

---

## 4. Unit Test Areas

### UT-063-001: Utilization KPI renders percentage and counts
- Mock utilization summary payload.
- Assert percentage plus booked/available counts are displayed.

### UT-063-002: KPI handles zero-availability edge case safely
- Mock available slots = 0.
- Assert fallback value/state without divide-by-zero display errors.

### UT-063-003: Filter selection triggers scoped utilization query
- Simulate provider/specialty/location filter changes.
- Assert query parameters reflect selected dimensions.

### UT-063-004: Filtered response updates utilization values deterministically
- Return updated filtered payload.
- Assert KPI and chart refresh with no stale scope values.

### UT-063-005: Booked vs available chart renders comparative series correctly
- Mock chart dataset.
- Assert both booked and available series are present with expected labels.

### UT-063-006: Comparative chart supports sparse or partial data windows
- Provide partial-series fixture.
- Assert chart remains renderable and legends remain accurate.

### UT-063-007: Scope indicator reflects currently selected provider/location
- Select provider/location.
- Assert header/scope badge text matches active selection.

### UT-063-008: Clearing scope filters resets indicator and aggregation level
- Clear selection.
- Assert scope indicator resets to default global/all state.

### UT-063-009: Loading/error states remain recoverable for utilization block
- Mock loading and failed query states.
- Assert placeholders and error messaging without full dashboard failure.

### UT-063-010: Utilization formatting remains consistent across percentages
- Assert precision and formatting rules for low/high utilization values.

---

## 5. Test Data and Mocking Strategy

- Fixtures: global utilization, scoped provider/location slices, zero-availability, sparse trend.
- Mock services: utilization API, filter state hook, chart transformation helper.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-063-001 through UT-063-008.

---

## 7. Suggested File Layout

- tests/unit/admin/UtilizationKpiCard.test.tsx
- tests/unit/admin/UtilizationComparisonChart.test.tsx
- tests/unit/admin/UtilizationFilters.test.tsx
- tests/unit/admin/UtilizationScopeIndicator.test.tsx
- tests/unit/admin/__fixtures__/utilization.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-063-001 through UT-063-010 implemented.
- [ ] AC traceability retained.
- [ ] Coverage and CI stability targets met.
