# UNIT-TEST-PLAN-017: Store Intake Data in Structured Format

User Story: US-017 (EP-002)
Source File: .propel/context/tasks/EP-002/us_017/us_017.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for structured intake persistence layer logic, including schema mapping, relational integrity checks, confidence-score persistence, audit logging, validation guards, index-aware query predicates, and soft-delete behavior.

---

## 2. Scope and Assumptions

### In Scope
- Intake aggregate mapping across master/detail tables.
- Insert/update validation and referential integrity safeguards.
- Confidence-score storage rules for extracted entities.
- Audit-log payload generation for mutations.
- Soft-delete status transitions and query exclusion behavior.

### Out of Scope
- Physical database migration execution.
- Actual index performance benchmarking.
- Full integration transaction behavior across live DB engines.

### Assumptions
- Repository/service layer encapsulates table writes in testable methods.
- Schema validators are deterministic and independent of DB runtime.
- Soft-delete behavior implemented via status flags and filtered query scopes.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | IntakeResponses master record mapping | UT-017-001 |
| AC-2 | Chief complaint persistence mapping | UT-017-002 |
| AC-3 | Medical history one-to-many mapping | UT-017-003 |
| AC-4 | Medications one-to-many mapping | UT-017-004 |
| AC-5 | Allergies one-to-many mapping with reaction typing | UT-017-005 |
| AC-6 | Insurance detail linkage mapping | UT-017-006 |
| AC-7 | Confidence score persistence fields | UT-017-007 |
| AC-8 | Audit log mutation recording | UT-017-008 |
| AC-9 | Query predicate support for common indexed filters | UT-017-009 |
| AC-10 | Insert/update validation and referential integrity | UT-017-010, UT-017-011 |
| AC-11 | Soft-delete behavior without hard deletion | UT-017-012 |

---

## 4. Unit Test Areas

## A. Aggregate Mapping

### UT-017-001: Intake aggregate writer creates master IntakeResponses record with required fields
- Build intake aggregate fixture.
- Assert master record payload includes appointment_id, patient_id, mode, timestamps.

### UT-017-002: Chief complaint mapper stores complaint text linked to intake id
- Persist aggregate.
- Assert complaint field mapping in target payload.

### UT-017-003: Medical history mapper emits expected rows with condition metadata
- Provide multiple condition entries.
- Assert row count and field-level mapping.

### UT-017-004: Medication mapper emits dosage/frequency/route rows
- Provide multi-medication fixture.
- Assert one-to-many row mapping correctness.

### UT-017-005: Allergy mapper persists allergen and reaction fields with typing
- Provide allergy + side-effect entries.
- Assert reaction_type/severity mapping.

### UT-017-006: Insurance mapper links insurance details to intake aggregate
- Assert insurance payload includes name, member_id, group_number, plan_name, verification_status.

## B. Confidence, Audit, and Validation

### UT-017-007: Confidence score fields persist per detail row where applicable
- Include AI-extracted confidence metadata.
- Assert confidence_score stored on mapped records.

### UT-017-008: Mutation audit logger captures changed field/value metadata
- Simulate update mutation.
- Assert audit entry contains changed_field, old/new values, actor, timestamp.

### UT-017-010: Validation layer rejects missing required fields before persistence
- Provide invalid aggregate fixture.
- Assert validation failure and no repository write.

### UT-017-011: Referential integrity checks reject orphan detail rows
- Provide detail record with missing intake reference.
- Assert integrity validation failure.

## C. Query and Soft Delete Behavior

### UT-017-009: Query builder composes predicates for patient_id, appointment_id, and created_at
- Build query requests with common filters.
- Assert predicate model includes indexed fields.

### UT-017-012: Soft-delete operation marks status as voided and excludes from default queries
- Execute soft-delete path.
- Assert status transition to voided and default query scope exclusion.

---

## 5. Test Data Strategy

- Aggregate fixtures with full and partial intake details.
- Invalid fixtures for required-field and reference-integrity checks.
- Update fixtures to drive audit trail assertions.

---

## 6. Mocking Strategy

- Mock repositories for intake master/detail tables.
- Mock validation and audit services.
- Mock query builder outputs without DB execution.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-017-001 through UT-017-010 before merge.

---

## 8. Exit Criteria

- AC-mapped persistence logic tests pass.
- Mapping, validation, and audit behaviors are verified.
- Soft-delete and query-scope logic covered.
- Coverage thresholds achieved.

---

## 9. Suggested File Layout

- tests/unit/intake/persistence/IntakeAggregateMapping.test.ts
- tests/unit/intake/persistence/IntakeValidationAudit.test.ts
- tests/unit/intake/persistence/IntakeQuerySoftDelete.test.ts
- tests/unit/intake/persistence/__fixtures__/intakePersistence.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-017.
- [ ] Test cases UT-017-001 through UT-017-012 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
