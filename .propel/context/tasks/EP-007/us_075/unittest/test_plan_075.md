# UNIT-TEST-PLAN-075: Log All User Actions (Login, Access, Changes)

User Story: US-075 (EP-007)
Source File: .propel/context/tasks/EP-007/us_075/us_075.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for comprehensive audit event logging across login events, PHI access/modification actions, account/role changes, retrieval completeness, and compliance coverage documentation.

---

## 2. Scope and Assumptions

### In Scope
- Structured audit event schema validation.
- Login success/failure event logging behavior.
- PHI access/modification logging behavior.
- Account/role/configuration change audit logging.
- Audit retrieval payload completeness checks.

### Out of Scope
- Debug/application telemetry unrelated to audit controls.
- Full SIEM query optimization.

### Assumptions
- Audit logger uses a typed event schema builder.
- Retrieval APIs return normalized audit record models.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Login attempts log success/failure with identity and source IP | UT-075-001, UT-075-002 |
| AC-2 | PHI resource access/modification actions are logged with outcome | UT-075-003, UT-075-004 |
| AC-3 | User account/role changes log actor, target, and change details | UT-075-005, UT-075-006 |
| AC-4 | Retrieval includes sufficient metadata for investigation | UT-075-007, UT-075-008 |
| AC-5 | Audit log coverage is complete and documented | UT-075-009, UT-075-010 |

---

## 4. Unit Test Areas

### UT-075-001: Login success event logs required schema fields
- Mock successful authentication flow.
- Assert timestamp, userId, role, ip, action, outcome fields present.

### UT-075-002: Login failure event logs with correct failure outcome and source
- Mock failed authentication.
- Assert failure event emitted without sensitive credential content.

### UT-075-003: PHI read action emits resource-scoped audit event
- Simulate PHI resource access.
- Assert resource identifier, actor, and outcome fields logged.

### UT-075-004: PHI modification action emits change outcome and context
- Simulate update/delete-like PHI change action.
- Assert action type and success/failure outcome captured.

### UT-075-005: Account/profile changes log actor and target-user mapping
- Simulate account attribute update.
- Assert actor and target linkage in event payload.

### UT-075-006: Role change events include before/after role details
- Simulate role update.
- Assert traceable role delta captured with attributable actor.

### UT-075-007: Retrieval query returns events with full investigation metadata
- Mock retrieval response.
- Assert schema completeness and required metadata coverage.

### UT-075-008: Retrieval filters preserve result correctness and ordering
- Apply query constraints (date/action/user).
- Assert expected subset and deterministic sort order.

### UT-075-009: Coverage validator confirms required action categories are instrumented
- Validate mapping across login/access/change categories.
- Assert missing categories fail coverage check.

### UT-075-010: Compliance export summarizes coverage and privacy controls
- Assert report includes coverage matrix and sensitive-data exclusion statement.

### UT-075-011: Audit logger rejects payloads containing prohibited sensitive values
- Inject disallowed secret-like fields.
- Assert sanitization/rejection behavior.

### UT-075-012: Audit logging path remains resilient under sink write failure
- Mock sink failure.
- Assert fail-safe handling and error telemetry without crashing caller flow.

---

## 5. Test Data and Mocking Strategy

- Fixtures: login outcomes, PHI access/change actions, account/role updates, retrieval datasets.
- Mocks: audit event builder, audit sink repository, retrieval adapter, coverage report generator.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-075-001 through UT-075-010.

---

## 7. Suggested File Layout

- tests/unit/audit/AuditEventSchema.test.ts
- tests/unit/audit/LoginAuditLogging.test.ts
- tests/unit/audit/PhiAccessAuditLogging.test.ts
- tests/unit/audit/AccountRoleAuditLogging.test.ts
- tests/unit/audit/AuditRetrievalCoverage.test.ts
- tests/unit/audit/__fixtures__/auditEvents.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-075-001 through UT-075-012 implemented.
- [ ] AC-1 through AC-5 traceability retained.
- [ ] Coverage and CI reliability targets met.
