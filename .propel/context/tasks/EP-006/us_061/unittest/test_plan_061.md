# UNIT-TEST-PLAN-061: No-Show Rate and Trends

User Story: US-061 (EP-006)
Source File: .propel/context/tasks/EP-006/us_061/us_061.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for no-show analytics, including KPI display, trend chart behavior across date ranges, and prior-period comparison clarity.

---

## 2. Scope and Assumptions

### In Scope
- No-show KPI card rendering and delta indicator logic.
- Trend visualization for no-show percentage over time.
- Date range filtering for no-show metrics.
- Prior-period comparison values and labeling.

### Out of Scope
- Predictive no-show models.
- Deep causal analysis of no-show drivers.

### Assumptions
- No-show rate is computed as missed appointments divided by scheduled appointments.
- Frontend consumes normalized metrics from API and renders via reusable chart components.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | No-show rate card is visible | UT-061-001, UT-061-002 |
| AC-2 | Trend chart shows no-show % over time | UT-061-003, UT-061-004 |
| AC-3 | Date range filter updates trends | UT-061-005, UT-061-006 |
| AC-4 | Prior-period comparison is displayed clearly | UT-061-007, UT-061-008 |

---

## 4. Unit Test Areas

### UT-061-001: KPI card renders current no-show rate value
- Mock current no-show metrics payload.
- Assert card label and percentage value render.

### UT-061-002: Change indicator shows direction and magnitude
- Provide positive/negative delta fixtures.
- Assert up/down indicator and delta formatting are correct.

### UT-061-003: Trend chart receives no-show percentage series
- Mock time-series payload.
- Assert chart adapter receives normalized points in order.

### UT-061-004: Trend chart handles missing intervals gracefully
- Provide sparse series fixture.
- Assert chart still renders with gap-safe behavior.

### UT-061-005: Date range change triggers no-show query with selected period
- Simulate date range control update.
- Assert request called with expected date params.

### UT-061-006: Filtered trend output replaces previous series cleanly
- Return second dataset after filter change.
- Assert stale series points are not displayed.

### UT-061-007: Prior-period value and delta text are rendered clearly
- Mock comparison payload.
- Assert baseline label and delta wording match UX contract.

### UT-061-008: Comparison fallback state appears when baseline unavailable
- Mock missing prior-period data.
- Assert fallback label/message without component failure.

### UT-061-009: Loading and error states are handled for KPI/trend sections
- Mock loading and API error variants.
- Assert spinner/placeholder and recoverable error message.

### UT-061-010: Formatting consistency for percentages and date labels
- Assert percent precision and date tick formatting are deterministic.

---

## 5. Test Data and Mocking Strategy

- Fixtures: current KPI, trend series, sparse trend, prior-period comparison, no-baseline.
- Mock services: no-show metrics API, filter state hook, formatting utilities.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-061-001 through UT-061-008.

---

## 7. Suggested File Layout

- tests/unit/admin/NoShowKpiCard.test.tsx
- tests/unit/admin/NoShowTrendChart.test.tsx
- tests/unit/admin/NoShowFilterBehavior.test.tsx
- tests/unit/admin/NoShowComparison.test.tsx
- tests/unit/admin/__fixtures__/noShow.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-061-001 through UT-061-010 implemented.
- [ ] AC mapping retained in tests/docs.
- [ ] Coverage targets met and CI stable.
