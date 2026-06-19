# UNIT-TEST-PLAN-087: Make API Stateless (No Local Storage)

User Story: US-087 (EP-008)
Source File: .propel/context/tasks/EP-008/us_087/us_087.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for statelessness enforcement, audit of local session removal, cross-instance auth consistency, external state externalization, and session persistence across failover.

---

## 2. Scope and Assumptions

### In Scope
- Local session/workflow state audit and removal.
- Cross-instance authentication and authorization validation.
- External state storage for required stateful data.
- Session continuity across scaling and failover.

### Out of Scope
- Full session store implementation details beyond externalization.
- Complex distributed transaction state management.

### Assumptions
- Application request handling is unit-testable in isolation.
- Session validation logic is injectable/mockable.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | No user session state stored locally | UT-087-001, UT-087-002 |
| AC-2 | Auth/session validation consistent across instances | UT-087-003, UT-087-004 |
| AC-3 | Stateful data stored in external services | UT-087-005, UT-087-006 |
| AC-4 | Sessions persist through failover/scaling | UT-087-007, UT-087-008 |

---

## 4. Unit Test Areas

### UT-087-001: Local disk/memory session persistence is absent
- Audit code paths for file writes or local cache.
- Assert no session state persisted locally.

### UT-087-002: Session state audit test on startup
- Run static/lint checkers or audit patterns.
- Assert no prohibited local-state patterns detected.

### UT-087-003: Auth validation succeeds on any instance
- Route same request to different mock instances.
- Assert auth result consistent.

### UT-087-004: Token verification works identically across instances
- Mock token verification from different instances.
- Assert same token produces same auth result.

### UT-087-005: Required stateful data is stored in external store
- Mock workflow with required state.
- Assert state persisted in external service (Redis/DB).

### UT-087-006: State retrieval uses external service only
- Simulate external service access.
- Assert no fallback to local storage.

### UT-087-007: Session survives instance replacement during request
- Simulate failover during in-flight request.
- Assert session accessible on new instance.

### UT-087-008: Scaling operations do not break session continuity
- Simulate scale-up/scale-down.
- Assert existing sessions remain accessible.

---

## 5. Test Data and Mocking Strategy

- Fixtures: request payloads with session data, auth tokens, external store states.
- Mocks: session validator, external store adapter, instance router.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-087-001 through UT-087-008.

---

## 7. Suggested File Layout

- tests/unit/api/StatelessnessAudit.test.ts
- tests/unit/api/CrossInstanceAuth.test.ts
- tests/unit/api/ExternalStatePersistence.test.ts
- tests/unit/api/FailoverSessionContinuity.test.ts
- tests/unit/api/__fixtures__/statelessness.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-087-001 through UT-087-008 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
