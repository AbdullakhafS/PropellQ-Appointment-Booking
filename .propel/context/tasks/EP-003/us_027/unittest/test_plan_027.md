# UNIT-TEST-PLAN-027: Implement CPT Code Suggestion Engine

User Story: US-027 (EP-003)
Source File: .propel/context/tasks/EP-003/us_027/us_027.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit tests for CPT suggestion logic to validate procedure-feature mapping, candidate ranking, modifier rules, confidence scoring, and deterministic output.

## 2. Scope and Assumptions

### In Scope
- Procedure/context feature extraction.
- CPT candidate retrieval and ranking.
- Modifier suggestion logic.
- Confidence and threshold categorization.

### Out of Scope
- Payer-specific reimbursement behavior.
- End-to-end billing submission flow.

### Assumptions
- CPT rule repository is versioned and mockable.
- Ranking and modifier rules are deterministic.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 candidate mapping | UT-027-001, UT-027-002 |
| AC-4 to AC-6 ranking/modifier | UT-027-003, UT-027-004 |
| AC-7 to AC-9 confidence/fallback | UT-027-005, UT-027-006 |

## 4. Unit Test Areas

### UT-027-001: Extracted procedure context maps to CPT search features
### UT-027-002: Candidate retrieval returns expected CPT code set
### UT-027-003: Ranking orders CPT suggestions by relevance and rule weight
### UT-027-004: Modifier rules append valid modifiers when conditions met
### UT-027-005: Confidence threshold labels suggestions as high/medium/low
### UT-027-006: Low-confidence path marks suggestion for verification review
### UT-027-007: Deterministic ordering maintained across identical scores
### UT-027-008: Missing procedure data returns safe empty suggestion result

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-027-001 through UT-027-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/coding/cpt/CptCandidateRanking.test.ts
- tests/unit/clinical/coding/cpt/CptModifiersConfidence.test.ts
- tests/unit/clinical/coding/cpt/__fixtures__/cptSuggestions.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-027.
- [ ] Test cases UT-027-001 through UT-027-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
