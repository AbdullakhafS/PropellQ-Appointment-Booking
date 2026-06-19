# UNIT-TEST-PLAN-026: Implement ICD-10 Code Suggestion Engine

User Story: US-026 (EP-003)
Source File: .propel/context/tasks/EP-003/us_026/us_026.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit tests for ICD-10 suggestion engine logic, including symptom-to-code mapping, ranking, confidence scoring, exclusions, and suggestion traceability.

## 2. Scope and Assumptions

### In Scope
- Input feature extraction for coding context.
- ICD candidate retrieval and ranking.
- Confidence score computation.
- Rule-based exclusions and tie-breakers.

### Out of Scope
- Live coding-guideline updates from external services.
- End-to-end coder workflow UI.

### Assumptions
- Suggestion engine uses deterministic ranking functions.
- ICD reference dataset is mockable.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 candidate generation | UT-026-001, UT-026-002 |
| AC-4 to AC-6 ranking/confidence | UT-026-003, UT-026-004 |
| AC-7 to AC-9 exclusions/traceability | UT-026-005, UT-026-006 |

## 4. Unit Test Areas

### UT-026-001: Feature extractor produces expected coding signals from input profile
### UT-026-002: Candidate retriever returns plausible ICD code set
### UT-026-003: Ranking function orders suggestions by relevance score
### UT-026-004: Confidence scorer maps score to expected threshold bucket
### UT-026-005: Exclusion rules remove contraindicated or incompatible codes
### UT-026-006: Suggestion payload includes evidence/trace metadata
### UT-026-007: Tie-breaking applies deterministic secondary ordering
### UT-026-008: Empty-input fallback returns no-suggestion with reason

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-026-001 through UT-026-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/coding/icd/IcdCandidateRanking.test.ts
- tests/unit/clinical/coding/icd/IcdConfidenceExclusions.test.ts
- tests/unit/clinical/coding/icd/__fixtures__/icdSuggestions.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-026.
- [ ] Test cases UT-026-001 through UT-026-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
