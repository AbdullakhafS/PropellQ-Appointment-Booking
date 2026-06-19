# UNIT-TEST-PLAN-086: Automatic Instance Removal on Failure

User Story: US-086 (EP-008)
Source File: .propel/context/tasks/EP-008/us_086/us_086.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for automatic instance removal after health failures, operational event visibility, retry thresholds, flapping protection, and safe instance recovery.

---

## 2. Scope and Assumptions

### In Scope
- Automatic instance deregistration on health failure.
- Retry threshold and graceful drain logic.
- Operational event/alert emission on removal.
- Flapping protection and transient failure filtering.
- Healthy instance rejoin conditions.

### Out of Scope
- Self-healing instance replacement logic.
- Deep orchestration platform behaviors.

### Assumptions
- Instance lifecycle management is abstracted via injectable adapters.
- Health check failure/recovery state is available to test.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Failed instances removed from traffic automatically | UT-086-001, UT-086-002 |
| AC-2 | Removal events generate alerts | UT-086-003, UT-086-004 |
| AC-3 | Transient failures do not trigger premature removal | UT-086-005, UT-086-006 |
| AC-4 | Restored instances can rejoin safely | UT-086-007, UT-086-008 |

---

## 4. Unit Test Areas

### UT-086-001: Unhealthy instance is deregistered from LB/scheduler
- Trigger failure condition.
- Assert instance removed from active pool.

### UT-086-002: Graceful drain occurs before removal
- Simulate removal with active connections.
- Assert drain completes before instance removed.

### UT-086-003: Removal event is emitted for operational visibility
- Trigger removal flow.
- Assert event/alert generated.

### UT-086-004: Removal event includes sufficient context (instance ID, reason, timestamp)
- Assert event payload includes required fields.

### UT-086-005: Single transient failure does not trigger removal
- Mock one failed check then recovery.
- Assert instance not removed.

### UT-086-006: Consecutive failures trigger removal after threshold
- Mock repeated failures at/above threshold.
- Assert removal after threshold breached.

### UT-086-007: Healthy instance can re-register after recovery
- Simulate recovery and healthy status.
- Assert instance rejoins active pool.

### UT-086-008: Flapping protection prevents unstable cycles
- Mock failure/recovery cycles.
- Assert stabilization wait prevents churn.

---

## 5. Test Data and Mocking Strategy

- Fixtures: failure sequences, threshold configs, recovery states, drain scenarios.
- Mocks: health monitor, lifecycle manager, event emitter, drain handler.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-086-001 through UT-086-008.

---

## 7. Suggested File Layout

- tests/unit/infra/InstanceDeregistration.test.ts
- tests/unit/infra/RemovalEventEmission.test.ts
- tests/unit/infra/FlappingProtection.test.ts
- tests/unit/infra/InstanceRejoin.test.ts
- tests/unit/infra/__fixtures__/instanceRemoval.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-086-001 through UT-086-008 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
