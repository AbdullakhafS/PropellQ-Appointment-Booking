# UNIT-TEST-PLAN-066: AI-Human Agreement Rate Metrics

User Story: US-066 (EP-006)
Source File: .propel/context/tasks/EP-006/us_066/us_066.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for AI-human agreement analytics, including KPI visibility, trend behavior, filter updates, and category breakdown rendering.

---

## 2. Scope and Assumptions

### In Scope
- Agreement KPI card and directional change indicator.
- Trend chart for agreement percentage over time.
- Filter controls affecting agreement analytics.
- Category breakdown by document type or workflow.

### Out of Scope
- AI model diagnostics and retraining workflows.
- Real-time streaming analytics behavior.

### Assumptions
- Agreement is computed from reviewed AI suggestions against human-confirmed outcomes.
- API provides aggregate totals plus category-sliced breakdowns.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Agreement card is visible | UT-066-001, UT-066-002 |
| AC-2 | Trend chart shows agreement % over time | UT-066-003, UT-066-004 |
| AC-3 | Filters update agreement metrics | UT-066-005, UT-066-006 |
| AC-4 | Category breakdown selection updates display | UT-066-007, UT-066-008 |

---

## 4. Unit Test Areas

### UT-066-001: Agreement KPI card renders current percentage
- Mock aggregate agreement payload.
- Assert card label and percentage value display.

### UT-066-002: KPI directional change indicator renders correctly
- Provide positive and negative delta fixtures.
- Assert indicator direction and delta format.

### UT-066-003: Trend chart receives normalized agreement time series
- Mock trend dataset.
- Assert chart adapter input ordering and value mapping.

### UT-066-004: Trend handles sparse data and missing intervals safely
- Provide sparse series fixture.
- Assert graceful rendering without runtime errors.

### UT-066-005: Filter changes trigger agreement re-query
- Simulate date/provider/workflow filter updates.
- Assert request params reflect selected filters.

### UT-066-006: Filtered response replaces prior KPI/trend state
- Return second filtered dataset.
- Assert stale values are removed.

### UT-066-007: Category breakdown selection updates chart/table segment
- Select document type/workflow category.
- Assert displayed breakdown matches selected dimension.

### UT-066-008: Invalid or empty category breakdown returns fallback state
- Mock empty category response.
- Assert fallback messaging with stable UI.

### UT-066-009: Loading and error states are recoverable
- Mock loading and API error variants.
- Assert skeleton/error states without full dashboard failure.

### UT-066-010: Metric definition helper text is present and consistent
- Assert explanatory metric text/rules render for interpretability.

---

## 5. Test Data and Mocking Strategy

- Fixtures: baseline agreement, filtered datasets, category breakdowns, sparse trend, empty/error.
- Mock services: agreement API, breakdown API, filter state hook, formatting helpers.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-066-001 through UT-066-008.

---

## 7. Suggested File Layout

- tests/unit/admin/AiHumanAgreementKpi.test.tsx
- tests/unit/admin/AiHumanAgreementTrend.test.tsx
- tests/unit/admin/AiHumanAgreementFilters.test.tsx
- tests/unit/admin/AiHumanAgreementBreakdown.test.tsx
- tests/unit/admin/__fixtures__/aiHumanAgreement.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-066-001 through UT-066-010 implemented.
- [ ] AC traceability retained.
- [ ] Coverage targets met and CI stable.
