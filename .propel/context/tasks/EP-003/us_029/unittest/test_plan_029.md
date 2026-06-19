# UNIT-TEST-PLAN-029: Implement Confidence Score Thresholds

User Story: US-029 (EP-003)
Source File: .propel/context/tasks/EP-003/us_029/us_029.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for confidence-threshold policy logic that routes suggestions into auto-accept, review, or manual-only paths based on configurable score thresholds.

## 2. Scope and Assumptions

### In Scope
- Threshold policy evaluation.
- Bucket assignment by score range.
- Config-driven threshold updates.
- Routing output contracts for downstream workflows.

### Out of Scope
- End-to-end human-review UX flows.
- Real-time model score generation.

### Assumptions
- Threshold policy is centralized and deterministic.
- Runtime config can be mocked in unit tests.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 score bucketing | UT-029-001, UT-029-002 |
| AC-4 to AC-6 routing behavior | UT-029-003, UT-029-004 |
| AC-7 to AC-9 config and edge boundaries | UT-029-005, UT-029-006 |

## 4. Unit Test Areas

### UT-029-001: Score classifier assigns high/medium/low buckets correctly
### UT-029-002: Boundary values map to expected inclusive/exclusive ranges
### UT-029-003: High-confidence bucket routes to auto-accept candidate path
### UT-029-004: Medium and low buckets route to review/manual paths
### UT-029-005: Threshold config update changes routing behavior without code change
### UT-029-006: Invalid threshold config falls back to safe defaults
### UT-029-007: Routing payload includes score, bucket, and threshold version
### UT-029-008: Null/NaN score values route to manual-review fallback

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-029-001 through UT-029-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/confidence/ThresholdClassification.test.ts
- tests/unit/clinical/confidence/ThresholdRoutingConfig.test.ts
- tests/unit/clinical/confidence/__fixtures__/thresholds.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-029.
- [ ] Test cases UT-029-001 through UT-029-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
