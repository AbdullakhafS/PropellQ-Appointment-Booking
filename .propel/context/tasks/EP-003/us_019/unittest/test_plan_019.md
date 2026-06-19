# UNIT-TEST-PLAN-019: Aggregate Patient Data from Intake and Documents

User Story: US-019 (EP-003)
Source File: .propel/context/tasks/EP-003/us_019/us_019.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for patient-data aggregation logic to validate source ingestion, normalization, merge precedence, deduplication, and aggregate output integrity.

## 2. Scope and Assumptions

### In Scope
- Intake and document-source data adapters.
- Canonical patient-profile mapping.
- Merge precedence and conflict markers.
- Required field completeness checks.

### Out of Scope
- End-to-end OCR/document extraction quality.
- Production database performance behavior.

### Assumptions
- Aggregation service has deterministic merge helpers.
- Source payloads are mockable fixtures.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 source ingestion/mapping | UT-019-001, UT-019-002 |
| AC-4 to AC-6 merge precedence/conflicts | UT-019-003, UT-019-004 |
| AC-7 to AC-9 dedupe and integrity | UT-019-005, UT-019-006 |

## 4. Unit Test Areas

### UT-019-001: Intake payload maps to canonical profile fields
### UT-019-002: Document payload maps to canonical profile fields
### UT-019-003: Merge precedence keeps latest/highest-trust value
### UT-019-004: Conflicting values produce conflict marker metadata
### UT-019-005: Duplicate meds/allergies are deduplicated by key rules
### UT-019-006: Missing required fields trigger validation output
### UT-019-007: Aggregated profile serializer preserves section ordering
### UT-019-008: Error in one source does not corrupt other source data

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-019-001 through UT-019-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/aggregation/PatientAggregateMapping.test.ts
- tests/unit/clinical/aggregation/PatientAggregateMerge.test.ts
- tests/unit/clinical/aggregation/__fixtures__/patientAggregate.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-019.
- [ ] Test cases UT-019-001 through UT-019-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
