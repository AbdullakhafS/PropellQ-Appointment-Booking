# UNIT-TEST-PLAN-069: CSV Export for Reports

User Story: US-069 (EP-006)
Source File: .propel/context/tasks/EP-006/us_069/us_069.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for filter-aware CSV export behavior, including successful download, data parity with dashboard scope, formatting correctness, and large-dataset handling.

---

## 2. Scope and Assumptions

### In Scope
- Export action trigger and feedback states.
- Server-side CSV generation aligned to active filters.
- Header and row formatting rules for dates/numbers/labels.
- Large export handling (streaming/chunked behavior abstractions).

### Out of Scope
- Scheduled/automated exports.
- Data warehouse bulk export workflows.

### Assumptions
- Export endpoint returns file payload and metadata using active dashboard filter params.
- CSV formatting helper(s) are unit-testable.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | CSV downloads successfully on export action | UT-069-001, UT-069-002 |
| AC-2 | CSV matches currently displayed filtered data | UT-069-003, UT-069-004 |
| AC-3 | CSV includes headers and formatted rows | UT-069-005, UT-069-006 |
| AC-4 | Large dataset export remains performant/stable | UT-069-007, UT-069-008 |

---

## 4. Unit Test Areas

### UT-069-001: Export action invokes CSV endpoint with current scope
- Simulate export button click.
- Assert request includes active dashboard filters.

### UT-069-002: Successful export triggers file download workflow
- Mock successful file payload response.
- Assert download helper invoked with expected filename/mime.

### UT-069-003: Exported dataset reflects active date/provider/location filters
- Provide filtered dashboard state fixture.
- Assert exported rows align with filtered subset identifiers.

### UT-069-004: Export with default scope matches unfiltered dashboard dataset
- Clear filters and export.
- Assert output aligns with baseline displayed metrics.

### UT-069-005: CSV includes expected column headers and order
- Parse generated CSV output.
- Assert header names and ordering match contract.

### UT-069-006: Date/numeric/label formatting is consistent across rows
- Validate date format, decimal precision, and label normalization.

### UT-069-007: Large dataset path uses chunked/stream-safe processing abstraction
- Mock large-row response path.
- Assert chunk/stream handler invoked and no memory-heavy sync path.

### UT-069-008: Large export completion feedback and stability behavior
- Simulate extended export duration.
- Assert in-progress indicator and completion state transitions.

### UT-069-009: Export failure shows recoverable error and allows retry
- Mock endpoint failure.
- Assert error toast/message and retry-capable UI state.

### UT-069-010: Concurrency guard prevents duplicate export submissions
- Simulate repeated clicks during in-flight export.
- Assert single request in progress policy.

---

## 5. Test Data and Mocking Strategy

- Fixtures: filtered/unfiltered datasets, small CSV payloads, large export response.
- Mock services: export API, file download helper, CSV formatter, in-progress state manager.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-069-001 through UT-069-008.

---

## 7. Suggested File Layout

- tests/unit/admin/CsvExportAction.test.tsx
- tests/unit/admin/CsvExportFilterParity.test.ts
- tests/unit/admin/CsvExportFormatting.test.ts
- tests/unit/admin/CsvExportLargeDataset.test.ts
- tests/unit/admin/__fixtures__/csvExport.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-069-001 through UT-069-010 implemented.
- [ ] AC traceability retained.
- [ ] Coverage and CI reliability targets met.
