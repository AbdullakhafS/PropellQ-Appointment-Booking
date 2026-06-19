# UNIT-TEST-PLAN-016: Flag Unverified Insurance for Staff Review

User Story: US-016 (EP-002)
Source File: .propel/context/tasks/EP-002/us_016/us_016.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for staff insurance-review workspace logic, including table composition, sort/filter behavior, status color semantics, manual verification actions, batch updates, and export-state handling.

---

## 2. Scope and Assumptions

### In Scope
- Pending verification dataset transformation for table view.
- Sorting and filtering state logic.
- Status-to-color mapping semantics.
- Manual verification action model and payload construction.
- Batch action and CSV-export payload generation.

### Out of Scope
- Full UI rendering layout pixel verification.
- End-to-end CSV file download mechanics in browser.
- Authentication/authorization enforcement tests.

### Assumptions
- Staff dashboard logic layer exposes table/query-state reducers/selectors.
- Verification action service is mockable.
- Export builder is deterministic and testable.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Dashboard route/state target for pending verifications | UT-016-001 |
| AC-2 | Table model includes required columns | UT-016-002 |
| AC-3 | Default and custom sorting behavior | UT-016-003 |
| AC-4 | Status/plan/date filtering behavior | UT-016-004, UT-016-005 |
| AC-5 | Status color-coding semantics | UT-016-006 |
| AC-6 | Patient details panel payload mapping | UT-016-007 |
| AC-7 | Manual verification action payload contract | UT-016-008, UT-016-009 |
| AC-8 | Confidence score formatting indicator logic | UT-016-010 |
| AC-9 | Verification attempt history display model | UT-016-011 |
| AC-10 | Batch verification action behavior | UT-016-012 |
| AC-11 | CSV export row model generation | UT-016-013 |
| AC-12 | Empty-state behavior for no pending records | UT-016-014 |

---

## 4. Unit Test Areas

## A. Dataset and Table State

### UT-016-001: Pending verification view selector returns correct dataset scope
- Provide mixed status records.
- Assert selector returns expected pending/unverified cohort.

### UT-016-002: Table-row mapper exposes required columns and action metadata
- Map record fixture to row model.
- Assert patient, insurance, member id, confidence, status, appointment date, and action fields.

### UT-016-003: Sorting reducer applies default earliest-appointment ordering and user-selected sort
- Initialize table state.
- Assert default sort and override sort behavior.

### UT-016-004: Status and insurance-plan filters reduce dataset correctly
- Apply status and plan filters.
- Assert filtered row set.

### UT-016-005: Date-range quick filters apply expected appointment windows
- Apply 7/14/30-day filters.
- Assert date-bound results.

## B. Display Semantics and Detail Mapping

### UT-016-006: Status-to-color mapper returns expected semantic color tokens
- Test verified/unverified/manual-review statuses.
- Assert token mapping (green/amber/etc.).

### UT-016-007: Patient details panel model includes contact, appointment, and insurance data
- Build side-panel model from selected row.
- Assert expected detail fields.

### UT-016-010: Confidence score formatter returns percentage/indicator label model
- Provide confidence values.
- Assert formatted indicator text or bucket classification.

### UT-016-011: Verification history mapper returns ordered attempt timeline entries
- Provide audit history fixture.
- Assert timeline model ordering and content.

## C. Actions, Batch, and Export

### UT-016-008: Manual verify action builder composes required payload fields
- Provide verification form input.
- Assert method, notes, staff name/date payload fields.

### UT-016-009: Manual verify action updates status and emits update event contract
- Mock successful verification action.
- Assert status transition and event dispatch payload.

### UT-016-012: Batch verification action applies to selected record set
- Select multiple rows and trigger batch action.
- Assert action payload includes all selected identifiers.

### UT-016-013: CSV export builder outputs expected columns and values
- Build export from filtered dataset.
- Assert CSV row model content/ordering.

### UT-016-014: Empty-state model renders positive completion message when no pending items
- Provide empty pending dataset.
- Assert expected empty-state text model.

---

## 5. Test Data Strategy

- Mixed-status insurance verification fixtures with varied dates/scores.
- Verification history fixtures for timeline assertions.
- Batch-selection fixtures with partial filter overlap.

---

## 6. Mocking Strategy

- Mock repository selectors and verification action service.
- Mock date utility for filter windows.
- Mock export serializer for deterministic row assertions.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-016-001 through UT-016-012 before merge.

---

## 8. Exit Criteria

- AC-mapped dashboard logic tests pass.
- Filtering, action, and export behavior verified.
- Status semantics and history models validated.
- Coverage thresholds achieved.

---

## 9. Suggested File Layout

- tests/unit/intake/insurance-review/ReviewTableFiltersSort.test.ts
- tests/unit/intake/insurance-review/ReviewActionsBatch.test.ts
- tests/unit/intake/insurance-review/ReviewDisplayExport.test.ts
- tests/unit/intake/insurance-review/__fixtures__/insuranceReview.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-016.
- [ ] Test cases UT-016-001 through UT-016-014 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
