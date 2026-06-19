# UNIT-TEST-PLAN-064: Intake Completion Rates

User Story: US-064 (EP-006)
Source File: .propel/context/tasks/EP-006/us_064/us_064.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for intake completion analytics, including KPI/trend visibility, filter-driven updates, and low-completion highlighting.

---

## 2. Scope and Assumptions

### In Scope
- Intake completion KPI rendering.
- Date/provider filter integration.
- Low-completion threshold highlighting behavior.
- Trend/summary refresh under filter changes.

### Out of Scope
- Field-level intake form analytics.
- Real-time patient reminder interventions.

### Assumptions
- Completion rate is completed intake forms / scheduled visits.
- Threshold flag is returned by API or derived by deterministic helper logic.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Intake completion metrics are visible | UT-064-001, UT-064-002 |
| AC-2 | Date range filter updates completion data | UT-064-003, UT-064-004 |
| AC-3 | Low completion is highlighted for review | UT-064-005, UT-064-006 |
| AC-4 | KPI reflects changed filter subset | UT-064-007, UT-064-008 |

---

## 4. Unit Test Areas

### UT-064-001: Completion KPI card renders rate and count summary
- Mock completion payload.
- Assert percentage and numerator/denominator values render.

### UT-064-002: Trend series renders completion trajectory over period
- Mock trend data points.
- Assert chart gets ordered series and labels.

### UT-064-003: Date filter change triggers completion query update
- Simulate date range selection.
- Assert API request includes updated date scope.

### UT-064-004: Provider filter change updates completion metrics subset
- Simulate provider selection.
- Assert returned KPI reflects provider-scoped subset.

### UT-064-005: Low-completion threshold displays highlighted warning state
- Mock low-completion flag true.
- Assert warning style/indicator and review cue text.

### UT-064-006: Normal completion state clears highlight
- Transition from low to normal fixture.
- Assert highlight is removed and neutral style restored.

### UT-064-007: Combined filter changes produce deterministic KPI output
- Apply date + provider filters together.
- Assert final KPI equals expected combined subset output.

### UT-064-008: Filter reset restores global completion values
- Reset active filters.
- Assert KPI/trend return to unfiltered baseline values.

### UT-064-009: Empty or missing metrics payload handled safely
- Mock empty dataset.
- Assert fallback messaging and non-crashing render path.

### UT-064-010: Formatting consistency for completion percentages and labels
- Assert precision and label consistency across values.

---

## 5. Test Data and Mocking Strategy

- Fixtures: baseline completion, low-completion threshold, provider/date subsets, empty state.
- Mock services: completion metrics API, threshold helper, filter-state hook.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-064-001 through UT-064-008.

---

## 7. Suggested File Layout

- tests/unit/admin/IntakeCompletionKpi.test.tsx
- tests/unit/admin/IntakeCompletionTrend.test.tsx
- tests/unit/admin/IntakeCompletionFilters.test.tsx
- tests/unit/admin/IntakeCompletionHighlight.test.tsx
- tests/unit/admin/__fixtures__/intakeCompletion.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-064-001 through UT-064-010 implemented.
- [ ] AC traceability retained.
- [ ] Coverage and CI reliability criteria met.
