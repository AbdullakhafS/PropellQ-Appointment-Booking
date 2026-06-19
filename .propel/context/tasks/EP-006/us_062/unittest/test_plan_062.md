# UNIT-TEST-PLAN-062: Average Wait Time Metrics

User Story: US-062 (EP-006)
Source File: .propel/context/tasks/EP-006/us_062/us_062.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for average wait-time analytics, including KPI/trend rendering, filter responsiveness, and threshold-based warning behavior.

---

## 2. Scope and Assumptions

### In Scope
- Wait-time KPI card rendering (average and percentile if present).
- Trend chart rendering across selected date windows.
- Date/provider/location filter binding.
- High wait-time threshold warning state display.

### Out of Scope
- Real-time queue prediction.
- Infrastructure-level performance/load testing.

### Assumptions
- Wait-time data is sourced from aggregated event timestamps.
- Threshold evaluation metadata is returned or computed by testable logic.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Average wait-time KPI is visible | UT-062-001, UT-062-002 |
| AC-2 | Wait-time metrics and trends display | UT-062-003, UT-062-004 |
| AC-3 | Filter updates wait-time data | UT-062-005, UT-062-006 |
| AC-4 | High threshold shows warning state | UT-062-007, UT-062-008 |

---

## 4. Unit Test Areas

### UT-062-001: Wait-time KPI card renders average value
- Mock aggregate wait metrics response.
- Assert KPI value and unit labels render correctly.

### UT-062-002: Percentile values render when provided
- Include percentile fixture (for example p90).
- Assert percentile badge/value display and formatting.

### UT-062-003: Trend chart renders wait-time series points
- Mock time-series dataset.
- Assert chart receives ordered data and axis labels.

### UT-062-004: Trend handles empty or low-sample datasets safely
- Mock empty/minimal series.
- Assert no crash and informative empty-state output.

### UT-062-005: Filter changes trigger wait-time query updates
- Simulate filter selection changes.
- Assert API calls include selected scope parameters.

### UT-062-006: Filtered payload updates KPI and trend in sync
- Return filtered response.
- Assert KPI and chart refresh consistently from same payload.

### UT-062-007: Threshold breach sets warning visual state
- Mock threshold-exceeded flag.
- Assert warning style/indicator and message appear.

### UT-062-008: Non-breach condition clears warning state
- Mock normal threshold state after prior breach.
- Assert warning indicator is removed deterministically.

### UT-062-009: API error state for wait-time block is recoverable
- Mock failed fetch.
- Assert error messaging and retry affordance behavior.

### UT-062-010: Value formatting consistency for minutes and ranges
- Assert rounding/precision rules are stable across fixtures.

---

## 5. Test Data and Mocking Strategy

- Fixtures: normal wait-time, threshold-breach, empty trend, filtered variants.
- Mock services: wait-time metrics API, threshold evaluator, filter state hooks.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-062-001 through UT-062-008.

---

## 7. Suggested File Layout

- tests/unit/admin/WaitTimeKpiCard.test.tsx
- tests/unit/admin/WaitTimeTrendChart.test.tsx
- tests/unit/admin/WaitTimeFilters.test.tsx
- tests/unit/admin/WaitTimeThresholdWarning.test.tsx
- tests/unit/admin/__fixtures__/waitTime.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-062-001 through UT-062-010 implemented.
- [ ] AC traceability retained.
- [ ] Coverage thresholds achieved and CI stable.
