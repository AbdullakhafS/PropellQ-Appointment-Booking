# UNIT-TEST-PLAN-090: Optimize Database Queries with Indexes

User Story: US-090 (EP-008)
Source File: .propel/context/tasks/EP-008/us_090/us_090.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for query optimization through indexing, query plan improvement validation, write-side impact assessment, and latency baseline tracking.

---

## 2. Scope and Assumptions

### In Scope
- High-frequency query pattern identification.
- Index creation and query plan validation.
- Before/after performance comparison.
- Write amplification impact measurement.
- Latency baselines and improvement tracking.

### Out of Scope
- Full database schema redesign.
- Complex query rewriting.

### Assumptions
- Query execution plans are available and testable.
- Database statistics and metrics are available via adapter.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Appropriate indexes created for common queries | UT-090-001, UT-090-002 |
| AC-2 | Query plans improve and performance validated | UT-090-003, UT-090-004 |
| AC-3 | Index selection avoids write amplification | UT-090-005, UT-090-006 |
| AC-4 | Query latency p95 improves toward targets | UT-090-007, UT-090-008 |

---

## 4. Unit Test Areas

### UT-090-001: High-frequency queries are identified
- Analyze mock query workload.
- Assert top queries detected.

### UT-090-002: Indexes are created for identified patterns
- Create indexes from pattern analysis.
- Assert indexes exist and are usable.

### UT-090-003: Query plan uses created index
- Execute query fixture.
- Assert query plan shows index usage.

### UT-090-004: Query execution time improves with index
- Compare performance before/after index.
- Assert latency improvement measured.

### UT-090-005: Index write impact is acceptable
- Measure write-side impact of indexes.
- Assert amplification within acceptable range.

### UT-090-006: Low-value indexes are removed
- Identify unused or expensive indexes.
- Assert removal considered/applied.

### UT-090-007: Latency p95 meets improvement target
- Measure p95 latency pre/post optimization.
- Assert target threshold met.

### UT-090-008: Covering indexes avoid extra lookups
- Validate covering index design.
- Assert single index satisfies query (no key lookup).

---

## 5. Test Data and Mocking Strategy

- Fixtures: high-frequency query sets, execution plans, write workloads, latency measurements.
- Mocks: query executor, plan analyzer, statistics provider.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-090-001 through UT-090-008.

---

## 7. Suggested File Layout

- tests/unit/db/QueryPatternAnalysis.test.ts
- tests/unit/db/IndexCreationAndValidation.test.ts
- tests/unit/db/QueryPlanImprovement.test.ts
- tests/unit/db/WriteAmplificationAssessment.test.ts
- tests/unit/db/__fixtures__/queryOptimization.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-090-001 through UT-090-008 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
