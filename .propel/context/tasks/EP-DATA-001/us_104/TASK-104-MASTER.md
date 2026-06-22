# TASK-104: Finalize Production Schema and Index Strategy - Master Task Breakdown

**Task ID:** TASK-104  
**Parent:** US-104 (EP-DATA-001)  
**Priority:** CRITICAL  
**Status:** Ready for Implementation  
**Total Points:** 52 (estimated)  
**Created:** 2026-06-22

---

## 1. Task Objective

Deliver a production-ready relational schema and index strategy for operational workloads (appointments, patient profiles, intake, documents, clinical coding) so that data integrity is enforced, uniqueness constraints prevent duplicates, and critical booking/profile/queue queries meet performance targets at scale.

---

## 2. Scope Summary

| Acceptance Criterion | Implementation Task | Status |
|---|---|---|
| AC-1: PK/FK constraints & cardinality documented | SCHEMA-1, SCHEMA-2, DOC-1, QA-1 | Planned |
| AC-2: Critical queries meet p95 latency budget | PERF-1, PERF-2, QA-2 | Planned |
| AC-3: Uniqueness constraints prevent duplicates | SCHEMA-3, QA-3 | Planned |
| AC-4: Naming conventions & semantics documented | GOV-1, DOC-1, QA-4 | Planned |
| AC-5: Hot-path indexes retained; unused removed | INDEX-1, INDEX-2, PERF-2, QA-5 | Planned |
| AC-6: Schema changes pass architecture review | GOV-2, DOC-2 | Planned |

---

## 3. Subtask Breakdown by Category

### CATEGORY A: Data Modeling Tasks (12 pts)

#### SCHEMA-1: Canonical Entity Model Finalization (4 pts)
**Objective:** Define core entities with normalized boundaries  
**Inputs:** US-104 user story, existing database patterns  
**Outputs:**
- Entity definitions (patient, appointment, provider, intake, document, coding, audit_log)
- Normalized schema with ownership per domain
- Entity relationship diagram (draft)
- Cardinality documentation

**Acceptance Criteria:**
- [ ] All 8 core entities defined with clear business purpose
- [ ] Cardinality documented (1:N, N:1, 0:N relationships)
- [ ] No denormalization without explicit rationale
- [ ] ERD diagram showing all relationships

**Dependencies:** None (can start immediately)

---

#### SCHEMA-2: Constraint Strategy (PK/FK/Check) (4 pts)
**Objective:** Add explicit constraints for data integrity  
**Inputs:** SCHEMA-1 entity definitions  
**Outputs:**
- DDL with PRIMARY KEY on all tables
- FOREIGN KEY constraints with cascading rules
- CHECK constraints for domain-valid states
- Cascade/restrict behavior documented

**Acceptance Criteria:**
- [ ] All tables have explicit single-column PK (BIGINT AUTO_INCREMENT)
- [ ] 15+ FK relationships defined with ON DELETE behavior (RESTRICT/CASCADE/SET NULL)
- [ ] CHECK constraints for status enums, timing constraints, bounded fields
- [ ] Test cases for FK violations pass/fail correctly

**Dependencies:** SCHEMA-1

---

#### SCHEMA-3: Uniqueness and Duplicate Prevention (4 pts)
**Objective:** Prevent duplicate records via unique constraints  
**Inputs:** SCHEMA-2 DDL, duplicate-risk entity analysis  
**Outputs:**
- UNIQUE constraints for identity fields (MRN, email, NPI)
- Composite unique keys where business uniqueness spans columns
- Insert/update conflict test cases
- Service-layer error handling guidance

**Acceptance Criteria:**
- [ ] MRN uniqueness enforced per organization
- [ ] Email uniqueness prevents duplicate accounts
- [ ] NPI uniqueness enforces national standard
- [ ] Coding (appointment_id, code_system, code_value, coding_type) prevents duplicate
- [ ] Test case: duplicate insert fails with ERROR 1062

**Dependencies:** SCHEMA-2

---

### CATEGORY B: Indexing and Query Tasks (20 pts)

#### INDEX-1: Hot-Path Index Candidate Design (5 pts)
**Objective:** Identify indexes needed for operational workloads  
**Inputs:** SCHEMA-2 DDL, query patterns from booking, queue, profile, intake flows  
**Outputs:**
- Read/write path matrix (10+ operational queries)
- Index candidates with predicate/join/orderby patterns
- Classification: mandatory (hot path), optional, deferred
- Rationale for each index

**Acceptance Criteria:**
- [ ] 4+ hot path queries identified (booking, schedule, queue, profile)
- [ ] Compound index design using leftmost prefix principle
- [ ] Estimated impact on p95 latency documented
- [ ] Write-path impact (insert/update cost) assessed

**Dependencies:** SCHEMA-1, SCHEMA-2

---

#### INDEX-2: Index Rationalization and Cleanup (3 pts)
**Objective:** Remove redundant/unused indexes  
**Inputs:** INDEX-1 candidates, production query stats (if available)  
**Outputs:**
- Final approved index list
- Overlapping indexes identified and removed
- PERFORMANCE_SCHEMA monitoring strategy
- Unused index detection procedure

**Acceptance Criteria:**
- [ ] Mandatory hot-path indexes retained
- [ ] Overlapping single-column indexes removed if compound exists
- [ ] Unused index monitoring query provided
- [ ] 13-15 final indexes approved

**Dependencies:** INDEX-1

---

#### PERF-1: Representative Dataset and Benchmark Harness (6 pts)
**Objective:** Generate realistic data volumes for performance testing  
**Inputs:** SCHEMA-3 DDL, cardinality estimates  
**Outputs:**
- SQL scripts to generate test data (100K patients, 500K appointments, etc.)
- Benchmark query suite (5-10 critical queries)
- Baseline measurements (p50/p95/p99 latencies)
- Row scan and index usage metrics

**Acceptance Criteria:**
- [ ] Test data generated with realistic distributions
- [ ] Benchmark script runs 4 hot queries 100+ times each
- [ ] Baseline latencies recorded before tuning
- [ ] Mixed workload baseline (read + write concurrent)

**Dependencies:** SCHEMA-3, INDEX-1

---

#### PERF-2: Query Plan and Latency Tuning (6 pts)
**Objective:** Iterate schema/index changes to meet latency targets  
**Inputs:** PERF-1 benchmark results, latency targets (5-50ms p95)  
**Outputs:**
- Query plan snapshots (EXPLAIN output before/after tuning)
- Index modifications applied
- Mixed workload validation (no write regression)
- Final latency report with p50/p95/p99

**Acceptance Criteria:**
- [ ] Hot Query 1 (patient lookup): p95 < 5ms
- [ ] Hot Query 2 (provider schedule): p95 < 10ms
- [ ] Hot Query 3 (clinic queue): p95 < 15ms
- [ ] Medium Query 4 (patient profile): p95 < 50ms
- [ ] No write-path regressions from indexing

**Dependencies:** PERF-1, INDEX-2

---

### CATEGORY C: Governance and Documentation Tasks (12 pts)

#### GOV-1: Naming and Semantic Standardization (3 pts)
**Objective:** Enforce consistent naming conventions  
**Inputs:** SCHEMA-3 DDL, project SQL standards  
**Outputs:**
- Table naming rules (singular, lowercase, snake_case)
- Column naming patterns (FK, boolean, timestamp, status)
- Index naming conventions
- Semantic consistency checks

**Acceptance Criteria:**
- [ ] All tables singular: `patient`, `appointment`, not `patients`
- [ ] All FKs follow `{table}_id` pattern
- [ ] All timestamps end in `_at`: created_at, updated_at, submitted_at
- [ ] All booleans use `is_*` or `has_*` prefix
- [ ] Index names follow `idx_{table}_{columns}` pattern

**Dependencies:** SCHEMA-3

---

#### GOV-2: Architecture Review and Compatibility Notes (3 pts)
**Objective:** Prepare schema for architecture review and approval  
**Inputs:** PERF-2 final DDL, governance documentation  
**Outputs:**
- Schema review package with change rationale
- Compatibility assessment (backward/forward compatibility)
- Migration impact analysis
- Architecture approval sign-off template

**Acceptance Criteria:**
- [ ] Change rationale documented for each major design decision
- [ ] Breaking changes vs. compatible changes identified
- [ ] Rollback strategy included
- [ ] Approval sign-off from Database Architect, Backend Lead, Security Lead

**Dependencies:** PERF-2, GOV-1

---

#### DOC-1: Data Model Glossary and ERD Updates (4 pts)
**Objective:** Document all entities and column semantics  
**Inputs:** SCHEMA-3 DDL, entity definitions, PERF-2 query analysis  
**Outputs:**
- Data model glossary (100+ column definitions)
- Entity-relationship diagram with cardinality
- Business meaning for every column
- Validation rules and constraints

**Acceptance Criteria:**
- [ ] All 8 entities documented with purpose and relationships
- [ ] 100+ columns with business meaning, type, constraints
- [ ] Status enum values explained
- [ ] Foreign key relationships with cardinality
- [ ] Service-facing contract links where applicable

**Dependencies:** SCHEMA-3

---

#### DOC-2: DDL and Migration Documentation (2 pts)
**Objective:** Document final DDL and deployment procedures  
**Inputs:** PERF-2 final DDL, GOV-2 approval notes  
**Outputs:**
- Approved DDL committed to version control
- Migration scripts (forward + rollback)
- Operational deployment notes
- Partitioning triggers based on growth thresholds

**Acceptance Criteria:**
- [ ] Final DDL artifact saved and version tracked
- [ ] Migration script tested on staging
- [ ] Rollback procedure documented and tested
- [ ] Deployment checklist created
- [ ] Growth thresholds and partitioning strategy documented

**Dependencies:** GOV-2

---

### CATEGORY D: Testing and Validation Tasks (8 pts)

#### QA-1: Integrity Constraint Validation (2 pts)
**Objective:** Validate PK/FK/check constraints work correctly  
**Inputs:** SCHEMA-2 and SCHEMA-3 DDL  
**Outputs:**
- Positive test cases (valid inserts/updates succeed)
- Negative test cases (constraint violations fail correctly)
- Test case execution results

**Acceptance Criteria:**
- [ ] PK constraints: Duplicate PK rejected
- [ ] FK constraints: Orphaned records rejected or cascaded
- [ ] CHECK constraints: Invalid enum/timing rejected
- [ ] NULL handling: Nullable constraints allow NULL

**Dependencies:** SCHEMA-2, SCHEMA-3

---

#### QA-2: Latency Budget Validation (2 pts)
**Objective:** Confirm all queries meet p95 latency targets under load  
**Inputs:** PERF-2 benchmark results  
**Outputs:**
- Benchmark report with p50/p95/p99 latencies
- Pass/fail verdict for each query target
- Load test results (1000 concurrent users)

**Acceptance Criteria:**
- [ ] All 4 hot queries pass their p95 targets
- [ ] No timeout failures under 1000 concurrent connections
- [ ] Mixed read/write workload tested
- [ ] Query plan stability confirmed over multiple runs

**Dependencies:** PERF-2

---

#### QA-3: Duplicate Prevention Validation (1 pt)
**Objective:** Validate uniqueness constraints prevent duplicates  
**Inputs:** SCHEMA-3 unique constraints  
**Outputs:**
- Test cases for each unique constraint
- ERROR 1062 (duplicate entry) verification

**Acceptance Criteria:**
- [ ] Duplicate MRN insert fails
- [ ] Duplicate email insert fails
- [ ] Duplicate NPI insert fails
- [ ] Duplicate appointment type code fails
- [ ] Duplicate coding (same appointment + code) fails

**Dependencies:** SCHEMA-3, QA-1

---

#### QA-4: Naming/Semantics Review Validation (1 pt)
**Objective:** Validate naming conventions applied consistently  
**Inputs:** GOV-1 rules, DOC-1 glossary, DDL artifacts  
**Outputs:**
- Naming consistency audit
- Glossary alignment verification

**Acceptance Criteria:**
- [ ] All tables singular and lowercase
- [ ] All FKs follow pattern
- [ ] All timestamps consistent
- [ ] Glossary matches DDL definitions

**Dependencies:** GOV-1, DOC-1

---

#### QA-5: Index Effectiveness Validation (2 pts)
**Objective:** Verify retained indexes are used and removed indexes don't regress  
**Inputs:** INDEX-2 final index list, PERF-2 query plans  
**Outputs:**
- Query plan analysis showing index usage
- PERFORMANCE_SCHEMA stats
- Regression test results

**Acceptance Criteria:**
- [ ] All hot queries use intended indexes (EXPLAIN shows index_range_scan)
- [ ] Removed indexes don't cause query regressions
- [ ] Index statistics up-to-date (ANALYZE TABLE run)
- [ ] Unused index monitoring working

**Dependencies:** INDEX-2, PERF-2, QA-2

---

## 4. Execution Order (Suggested)

```
Phase 1: Data Modeling (Days 1-3)
  1. SCHEMA-1: Entity definitions
  2. SCHEMA-2: Constraints (PK/FK/Check)
  3. SCHEMA-3: Uniqueness constraints

Phase 2: Indexing & Query (Days 4-10)
  4. INDEX-1: Hot-path index design
  5. GOV-1: Naming standardization (parallel)
  6. PERF-1: Test data generation
  7. INDEX-2: Index rationalization
  8. PERF-2: Latency tuning

Phase 3: Documentation & Governance (Days 11-14)
  9. DOC-1: Data model glossary
  10. DOC-2: DDL & migration docs
  11. GOV-2: Architecture review & approval

Phase 4: Testing & Validation (Days 15-18)
  12. QA-1, QA-2, QA-3, QA-4, QA-5: All validation tests
```

---

## 5. Definition of Done

### Must-Have (Blocking)
- [ ] All 8 entities defined with explicit PKs and documented cardinality
- [ ] 15+ FK relationships with referential integrity
- [ ] 4+ hot path queries meet p95 targets (5-50ms)
- [ ] 6 uniqueness constraints prevent duplicates
- [ ] 13-15 production indexes designed and validated
- [ ] Architecture review approval obtained
- [ ] Final DDL committed with version number

### Should-Have (High Priority)
- [ ] Data model glossary published (100+ columns documented)
- [ ] Query plans captured before/after tuning
- [ ] Load test results (1000 concurrent users) validated
- [ ] Deployment runbook documented
- [ ] Naming conventions enforced consistently

### Nice-to-Have
- [ ] Partitioning strategy documented for growth thresholds
- [ ] PERFORMANCE_SCHEMA monitoring alerts configured
- [ ] Migration tool integrated (Flyway/Liquibase)
- [ ] Team trained on schema governance process

---

## 6. Success Criteria

| Metric | Target | Measurement |
|---|---|---|
| **Query Performance** | p95 latency 5-50ms | PERF-2 benchmark report |
| **Data Integrity** | 0 duplicate violations | QA-3 test results |
| **Index Coverage** | All hot paths indexed | EXPLAIN ANALYZE verification |
| **Documentation** | 100% of columns documented | DOC-1 glossary completeness |
| **Constraint Coverage** | All entities have constraints | QA-1 test results |
| **Architecture Approval** | Sign-off obtained | GOV-2 approval record |

---

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Over-indexing degrades writes | HIGH | Validate mixed workload; monitor write latency |
| Query plan instability | HIGH | Capture plans before/after; regression test |
| Cardinality estimation wrong | MEDIUM | Load test with realistic data volumes |
| Schema changes break services | MEDIUM | Compatibility assessment in GOV-2 |
| Performance targets not met | HIGH | Iterate tuning in PERF-2 before approval |

---

## 8. Related Documents

**Parent User Story:**
- [US-104: Production Schema and Index Strategy](us_104.md)

**Reference Standards:**
- Database Standards: `.github/instructions/database-standards.instructions.md`
- Performance Best Practices: `.github/instructions/performance-best-practices.instructions.md`
- Backend Development: `.github/instructions/backend-development-standards.instructions.md`

---

## 9. Task Status Dashboard

| Subtask | Points | Owner | Status | % Complete |
|---|---|---|---|---|
| SCHEMA-1 | 4 | TBD | Planned | 0% |
| SCHEMA-2 | 4 | TBD | Planned | 0% |
| SCHEMA-3 | 4 | TBD | Planned | 0% |
| INDEX-1 | 5 | TBD | Planned | 0% |
| INDEX-2 | 3 | TBD | Planned | 0% |
| PERF-1 | 6 | TBD | Planned | 0% |
| PERF-2 | 6 | TBD | Planned | 0% |
| GOV-1 | 3 | TBD | Planned | 0% |
| GOV-2 | 3 | TBD | Planned | 0% |
| DOC-1 | 4 | TBD | Planned | 0% |
| DOC-2 | 2 | TBD | Planned | 0% |
| QA-1 thru QA-5 | 8 | TBD | Planned | 0% |
| **TOTAL** | **52** | | **READY** | **0%** |

---

**Next:** Begin SCHEMA-1 task (Entity Model Finalization)
