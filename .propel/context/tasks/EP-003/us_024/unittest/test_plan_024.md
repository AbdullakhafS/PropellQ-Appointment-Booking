# UNIT-TEST-PLAN-024: Implement Medication Conflict Detection

User Story: US-024 (EP-003)
Source File: .propel/context/tasks/EP-003/us_024/us_024.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for medication-conflict detection logic including interaction-rule evaluation, severity scoring, duplicate normalization, and alert generation behavior.

## 2. Scope and Assumptions

### In Scope
- Medication normalization and code mapping.
- Pairwise interaction-rule evaluation.
- Severity and risk categorization.
- Alert payload and conflict context generation.

### Out of Scope
- Clinical knowledge-base correctness beyond test fixtures.
- End-to-end provider notification delivery.

### Assumptions
- Interaction engine and rule repository are mockable.
- Severity policy is deterministic and versioned.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 normalization/rules | UT-024-001, UT-024-002 |
| AC-4 to AC-6 severity/alerts | UT-024-003, UT-024-004 |
| AC-7 to AC-9 edge and dedupe handling | UT-024-005, UT-024-006 |

## 4. Unit Test Areas

### UT-024-001: Medication names normalize to canonical identifiers
### UT-024-002: Interaction engine detects configured conflicting medication pairs
### UT-024-003: Severity scorer assigns expected risk bucket
### UT-024-004: Conflict alert payload includes med pair, severity, rationale
### UT-024-005: Duplicate meds do not produce duplicate conflict alerts
### UT-024-006: Unknown medication codes produce review-needed marker
### UT-024-007: No-conflict medication list returns empty alert set
### UT-024-008: Rule-version metadata is included for traceability

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-024-001 through UT-024-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/conflicts/MedicationNormalizationRules.test.ts
- tests/unit/clinical/conflicts/MedicationConflictSeverityAlerts.test.ts
- tests/unit/clinical/conflicts/__fixtures__/medicationConflicts.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-024.
- [ ] Test cases UT-024-001 through UT-024-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
