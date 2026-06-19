# UNIT-TEST-PLAN-092: Graceful Degradation Pattern

User Story: US-092 (EP-008)
Source File: .propel/context/tasks/EP-008/us_092/us_092.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for graceful degradation of non-essential service failures, core workflow availability during faults, fallback messaging, and degraded-state alerting.

---

## 2. Scope and Assumptions

### In Scope
- Classification of critical vs. optional dependencies.
- Timeout, retry, circuit breaker, and bypass policies.
- Degraded UX messaging without blocking core flows.
- Degraded-state alerting and observability.

### Out of Scope
- Full feature parity during outages.

### Assumptions
- Dependency failure injection is testable via mocks.
- UI/messaging layer is injectable.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Core booking available during optional service failure | UT-092-001, UT-092-002 |
| AC-2 | System shows appropriate user messaging without full failure | UT-092-003, UT-092-004 |
| AC-3 | Optional service calls do not block core workflows | UT-092-005, UT-092-006 |
| AC-4 | Degraded operation generates alerts for affected service | UT-092-007, UT-092-008 |

---

## 4. Unit Test Areas

### UT-092-001: Core booking remains available during analytics service outage
- Mock analytics service failure.
- Assert booking flow succeeds without failure.

### UT-092-002: Core booking available during non-essential notification service down
- Mock notification service failure.
- Assert booking proceeds without blocking.

### UT-092-003: Degraded messaging shown to user on optional service failure
- Trigger optional service failure.
- Assert user sees appropriate fallback message (e.g., "Some features temporarily unavailable").

### UT-092-004: User experience remains consistent in degraded mode
- Compare booking experience with/without optional service.
- Assert core UX unchanged.

### UT-092-005: Optional service calls timeout and bypass without blocking
- Set short timeout on optional service.
- Assert booking continues on timeout without wait.

### UT-092-006: Circuit breaker opens after repeated failures
- Trigger multiple failures.
- Assert circuit breaker opens and requests fail fast.

### UT-092-007: Degraded state alert emitted on service degradation
- Trigger degraded mode.
- Assert alert/event generated.

### UT-092-008: Alert includes service name and degradation context
- Assert alert payload includes affected service and reason.

---

## 5. Test Data and Mocking Strategy

- Fixtures: service failure scenarios, timeout configs, circuit breaker states, degraded messages.
- Mocks: dependency injectors, circuit breaker, timeout handler, alert emitter.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-092-001 through UT-092-008.

---

## 7. Suggested File Layout

- tests/unit/reliability/CoreWorkflowFaultTolerance.test.ts
- tests/unit/reliability/DegradedModeFallback.test.ts
- tests/unit/reliability/CircuitBreakerBehavior.test.ts
- tests/unit/reliability/DegradedAlerts.test.ts
- tests/unit/reliability/__fixtures__/degradation.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-092-001 through UT-092-008 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
