# UNIT-TEST-PLAN-025: Implement Allergy-Drug Interaction Check

User Story: US-025 (EP-003)
Source File: .propel/context/tasks/EP-003/us_025/us_025.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for allergy-drug interaction checking, including allergen normalization, cross-reactivity rules, severity classification, and safe alert output.

## 2. Scope and Assumptions

### In Scope
- Allergy normalization and synonym matching.
- Drug class mapping and cross-reactivity checks.
- Severity/urgency classification.
- Interaction alert generation with rationale.

### Out of Scope
- External allergy ontology quality validation.
- End-to-end physician notification workflows.

### Assumptions
- Interaction engine has deterministic rule evaluation.
- Allergy and medication fixtures include coded and free-text variants.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 normalization/matching | UT-025-001, UT-025-002 |
| AC-4 to AC-6 interaction/severity | UT-025-003, UT-025-004 |
| AC-7 to AC-9 edge handling | UT-025-005, UT-025-006 |

## 4. Unit Test Areas

### UT-025-001: Allergy names normalize to canonical allergen identifiers
### UT-025-002: Drug classes resolve correctly for interaction checks
### UT-025-003: Interaction checker detects direct and class-based cross-reactivity
### UT-025-004: Severity classifier returns expected high/medium/low risk buckets
### UT-025-005: Unknown allergy terms produce manual-review marker
### UT-025-006: Non-conflicting combinations return empty interaction set
### UT-025-007: Alert payload includes allergy, drug, severity, and guidance fields
### UT-025-008: Duplicate allergy entries do not duplicate generated alerts

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-025-001 through UT-025-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/interactions/AllergyDrugNormalization.test.ts
- tests/unit/clinical/interactions/AllergyDrugRiskAlerts.test.ts
- tests/unit/clinical/interactions/__fixtures__/allergyDrug.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-025.
- [ ] Test cases UT-025-001 through UT-025-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
