# UNIT-TEST-PLAN-023: Display Document Sources with Traceability

User Story: US-023 (EP-003)
Source File: .propel/context/tasks/EP-003/us_023/us_023.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for traceability presentation logic so extracted clinical fields can be linked back to source documents and offsets with reliable provenance metadata.

## 2. Scope and Assumptions

### In Scope
- Provenance metadata model generation.
- Source-link rendering model and field-level references.
- Missing-source and stale-reference handling.
- Sorting/filtering by source type/time.

### Out of Scope
- Full document viewer integration.
- End-to-end OCR coordinate validation.

### Assumptions
- Extraction pipeline stores source references/offsets.
- Traceability mapper is deterministic and testable.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 source linkage | UT-023-001, UT-023-002 |
| AC-4 to AC-6 provenance metadata | UT-023-003, UT-023-004 |
| AC-7 to AC-9 missing/invalid references | UT-023-005, UT-023-006 |

## 4. Unit Test Areas

### UT-023-001: Field traceability mapper includes source document id and section
### UT-023-002: Source links include expected anchor metadata (page/offset)
### UT-023-003: Provenance timestamp and extraction version are preserved
### UT-023-004: Sorting by latest source update returns expected order
### UT-023-005: Missing source reference renders unavailable-state marker
### UT-023-006: Stale reference mismatch triggers review-required flag
### UT-023-007: Duplicate references collapse into single provenance entry
### UT-023-008: Filter by source type (intake/pdf/docx) returns correct subset

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-023-001 through UT-023-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/traceability/TraceabilityMapping.test.ts
- tests/unit/clinical/traceability/TraceabilityStatesFilters.test.ts
- tests/unit/clinical/traceability/__fixtures__/traceability.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-023.
- [ ] Test cases UT-023-001 through UT-023-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
