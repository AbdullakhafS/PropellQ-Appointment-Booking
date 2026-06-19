# TASK-104: Finalize Production Schema and Index Strategy

User Story: US-104 (EP-DATA-001)
Source File: .propel/context/tasks/EP-DATA-001/us_104/us_104.md
Priority: CRITICAL
Estimated Effort: 5-7 dev days + benchmark validation
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Deliver a production-ready relational schema and index strategy for operational workloads so that data integrity is enforced and critical booking, profile, intake, and clinical queries meet performance targets at scale.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Core entities include explicit PK/FK constraints and documented cardinality | SCHEMA-1, SCHEMA-2, DOC-1, QA-1 |
| AC-2 | Critical operational queries meet p95 latency budget on representative volume | PERF-1, PERF-2, QA-2 |
| AC-3 | Uniqueness constraints prevent duplicate appointments/patient identifiers | SCHEMA-3, QA-3 |
| AC-4 | Naming conventions and column semantics are consistent and documented | GOV-1, DOC-1, QA-4 |
| AC-5 | Redundant indexes removed and hot-path indexes retained based on plans | INDEX-1, INDEX-2, PERF-2, QA-5 |
| AC-6 | Schema changes pass architecture review with compatibility notes | GOV-2, DOC-2 |

---

## 3. Layered Implementation Tasks

## Data Modeling Tasks

### SCHEMA-1: Canonical Entity Model Finalization
- Finalize canonical entities for appointments, patient profile, intake, documents, coding, and audit references.
- Define normalized boundaries and ownership per domain aggregate.
- Publish entity relationship draft with explicit cardinality.

### SCHEMA-2: Constraint Strategy (PK/FK/Check)
- Add explicit primary and foreign keys for all core entities.
- Add check constraints for domain-valid states (status, lifecycle phase, bounded numeric fields).
- Validate cascade/restrict behavior to avoid orphan or destructive deletes.

### SCHEMA-3: Uniqueness and Duplicate Prevention
- Define unique constraints for duplicate-risk entities (appointment identity, patient identifier scopes).
- Add composite unique keys where business uniqueness spans multiple columns.
- Validate insert/update conflict behavior for service-layer error handling.

## Indexing and Query Tasks

### INDEX-1: Hot-Path Index Candidate Design
- Build read/write path matrix for booking lookup, queue processing, profile timeline, intake fetch, and dashboard reads.
- Propose index candidates from predicate, join, and order-by patterns.
- Classify indexes as mandatory, optional, or deferred.

### INDEX-2: Index Rationalization and Cleanup
- Analyze query plans and runtime stats to identify redundant/unused indexes.
- Remove overlapping indexes that do not improve targeted plans.
- Keep hot-path indexes that show measurable p95 benefit.

### PERF-1: Representative Dataset and Benchmark Harness
- Generate representative data volumes for realistic cardinality/skew.
- Create benchmark script set for critical operational queries.
- Capture baseline p50/p95/p99 latencies and row scan metrics.

### PERF-2: Query Plan and Latency Tuning
- Iterate schema/index changes against benchmark suite.
- Capture query plan snapshots before and after tuning.
- Validate mixed workload impact to prevent write-path regressions.

## Governance and Documentation Tasks

### GOV-1: Naming and Semantic Standardization
- Apply consistent naming conventions for tables, columns, constraints, and indexes.
- Standardize semantic patterns (timestamps, soft-delete markers, source provenance fields).
- Validate conformance with project SQL standards.

### GOV-2: Architecture Review and Compatibility Notes
- Prepare schema review package with change rationale and migration impact.
- Include compatibility notes for backward/forward deployment sequencing.
- Obtain architecture approval sign-off.

### DOC-1: Data Model Glossary and ERD Updates
- Update glossary definitions for core entities and column semantics.
- Publish ERD with cardinality and relationship notes.
- Link glossary terms to service-facing contracts where applicable.

### DOC-2: DDL and Migration Documentation
- Commit approved DDL artifacts and migration scripts.
- Document rollback strategy and operational deployment notes.
- Add guidance for partitioning triggers based on growth thresholds.

## Testing and Validation Tasks

### QA-1: Integrity Constraint Validation
- Validate PK/FK/check constraints using positive and negative test cases.

### QA-2: Latency Budget Validation
- Run benchmark suite and verify p95 latency meets agreed budgets.

### QA-3: Duplicate Prevention Validation
- Validate uniqueness constraint behavior under concurrent insert/update attempts.

### QA-4: Naming/Semantics Review Validation
- Validate artifact consistency (naming, semantics, glossary alignment).

### QA-5: Index Effectiveness Validation
- Verify retained indexes are used by hot queries and removed indexes show no regression.

---

## 4. Dependencies

- API access pattern standards and query conventions from EP-TECH-001.
- Hot query path inputs from EP-001, EP-003, and EP-006.
- Representative data generation capability for benchmark workloads.
- Architecture review forum and approval workflow.

---

## 5. Definition of Done

- [ ] Approved production schema and DDL artifacts are committed.
- [ ] PK/FK/check/unique constraints are implemented and validated.
- [ ] Index strategy is documented with benchmark and query-plan evidence.
- [ ] Redundant/unused indexes are removed and hot-path indexes retained.
- [ ] Query plan snapshots are stored for critical endpoints.
- [ ] Data model glossary and ERD are updated and reviewed.
- [ ] Architecture review approval and compatibility notes are recorded.
- [ ] Acceptance criteria AC-1 through AC-6 are validated and signed off.

---

## 6. Suggested Execution Order

1. SCHEMA-1
2. SCHEMA-2, SCHEMA-3
3. INDEX-1, GOV-1
4. PERF-1
5. INDEX-2, PERF-2
6. DOC-1, DOC-2
7. GOV-2
8. QA-1 through QA-5
