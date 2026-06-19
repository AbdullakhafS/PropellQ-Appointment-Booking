# UNIT-TEST-PLAN-085: Automated Health Checks

User Story: US-085 (EP-008)
Source File: .propel/context/tasks/EP-008/us_085/us_085.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for liveness and readiness health probes, load balancer/orchestrator integration, persistent failure alerting, and safe endpoint behavior.

---

## 2. Scope and Assumptions

### In Scope
- Liveness and readiness endpoint implementations.
- Health check probe integration and routing removal.
- Startup readiness gate enforcement.
- Persistent failure alerting.
- Endpoint documentation and behavior.

### Out of Scope
- Deep application diagnostics beyond health signals.
- Orchestration platform health probe internals.

### Assumptions
- Health endpoints are injectable/mockable service methods.
- Load balancer/orchestrator integration is abstracted via test doubles.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Readiness and liveness endpoints available | UT-085-001, UT-085-002 |
| AC-2 | Unhealthy instances detected and removed | UT-085-003, UT-085-004 |
| AC-3 | Readiness prevents traffic until ready | UT-085-005, UT-085-006 |
| AC-4 | Repeated failures generate alerts | UT-085-007, UT-085-008 |
| AC-5 | Endpoint behavior documented clearly | UT-085-009, UT-085-010 |

---

## 4. Unit Test Areas

### UT-085-001: Liveness endpoint responds with health status
- Call liveness endpoint.
- Assert expected response format and status codes.

### UT-085-002: Readiness endpoint checks dependencies
- Mock dependent service states.
- Assert readiness reflects actual state.

### UT-085-003: Failed health check is detected by probe
- Simulate unhealthy state.
- Assert probe detects failure.

### UT-085-004: Load balancer removes unhealthy instance from traffic
- Trigger health check failure.
- Assert instance removed from routing set.

### UT-085-005: Readiness gate prevents routing before startup complete
- Mock startup state.
- Assert readiness fails and traffic blocked.

### UT-085-006: Readiness gate passes after dependencies available
- Complete startup sequence.
- Assert readiness passes and traffic allowed.

### UT-085-007: Persistent health check failures trigger alert
- Simulate repeated failures.
- Assert alert generated on threshold.

### UT-085-008: Single transient failure does not alert
- Simulate one failure then recovery.
- Assert no alert emitted.

### UT-085-009: Endpoint semantics are documented
- Assert docs include expected failure modes and meanings.

### UT-085-010: Health checks do not leak sensitive information
- Assert responses exclude internal secrets or PHI.

---

## 5. Test Data and Mocking Strategy

- Fixtures: healthy/unhealthy states, startup phases, dependency status sets, failure counts.
- Mocks: dependency checker, probe integrator, alert emitter.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-085-001 through UT-085-008.

---

## 7. Suggested File Layout

- tests/unit/health/LivenessProbe.test.ts
- tests/unit/health/ReadinessProbe.test.ts
- tests/unit/health/HealthCheckRouting.test.ts
- tests/unit/health/HealthCheckAlerts.test.ts
- tests/unit/health/__fixtures__/health.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-085-001 through UT-085-010 implemented.
- [ ] AC-1 through AC-5 traceability retained.
- [ ] Coverage and CI reliability targets met.
