# UNIT-TEST-PLAN-065: Insurance Verification Status Metrics

User Story: US-065 (EP-006)
Source File: .propel/context/tasks/EP-006/us_065/us_065.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for insurance verification analytics, including status KPI visibility, filter-driven updates, issue highlighting, and status-specific filtering behavior.

---

## 2. Scope and Assumptions

### In Scope
- KPI card for verified, pending, and failed counts.
- Trend/summary view updates by date/provider/status filters.
- Highlighting for pending/failed issue counts.
- Status filter controls that constrain visible records.

### Out of Scope
- Eligibility adjudication internals.
- Claims workflow processing.

### Assumptions
- Verification statuses are normalized to verified, pending, failed.
- API provides both aggregate counts and issue emphasis metadata.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Insurance verification metrics are visible | UT-065-001, UT-065-002 |
| AC-2 | Filters update verification data | UT-065-003, UT-065-004 |
| AC-3 | Verification issues are highlighted | UT-065-005, UT-065-006 |
| AC-4 | Status filter shows only matching records | UT-065-007, UT-065-008 |

---

## 4. Unit Test Areas

### UT-065-001: KPI card renders verified/pending/failed counts
- Mock status-count payload.
- Assert each bucket count and label render correctly.

### UT-065-002: Trend section renders verification performance over time
- Mock trend dataset.
- Assert trend visualization receives normalized status series.

### UT-065-003: Date/provider filters trigger verification metrics reload
- Simulate date/provider updates.
- Assert query includes selected filter values.

### UT-065-004: Filtered results replace prior status totals without stale data
- Return filtered payload.
- Assert KPI and trend reflect latest filtered counts only.

### UT-065-005: Pending/failed issue highlight appears when issue flag set
- Mock issue emphasis metadata true.
- Assert visual emphasis on pending/failed segments.

### UT-065-006: Highlight clears when issues are resolved/absent
- Transition to no-issue fixture.
- Assert emphasis styling and alerts are removed.

### UT-065-007: Status filter limits rendered records to selected status
- Select pending or failed status filter.
- Assert only matching status records/segments appear.

### UT-065-008: Clearing status filter restores full status set
- Clear status filter.
- Assert verified/pending/failed records return.

### UT-065-009: Unknown status values are handled via safe fallback mapping
- Provide unexpected status code fixture.
- Assert fallback bucket/label behavior without crashes.

### UT-065-010: Loading/error states are recoverable for verification block
- Mock loading and API failure variants.
- Assert placeholder plus recoverable error messaging.

---

## 5. Test Data and Mocking Strategy

- Fixtures: balanced status counts, issue-heavy dataset, filtered subsets, unknown statuses.
- Mock services: verification metrics API, status filter state, emphasis metadata mapper.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-065-001 through UT-065-008.

---

## 7. Suggested File Layout

- tests/unit/admin/InsuranceVerificationKpi.test.tsx
- tests/unit/admin/InsuranceVerificationTrend.test.tsx
- tests/unit/admin/InsuranceVerificationFilters.test.tsx
- tests/unit/admin/InsuranceVerificationHighlight.test.tsx
- tests/unit/admin/__fixtures__/insuranceVerification.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-065-001 through UT-065-010 implemented.
- [ ] AC traceability retained.
- [ ] Coverage thresholds and CI stability met.
