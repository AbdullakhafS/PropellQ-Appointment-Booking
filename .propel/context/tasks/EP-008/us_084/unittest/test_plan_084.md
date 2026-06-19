# UNIT-TEST-PLAN-084: Database Replication (Primary + Standby)

User Story: US-084 (EP-008)
Source File: .propel/context/tasks/EP-008/us_084/us_084.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for primary-standby database replication, failover timing/procedures, replication lag monitoring, application failover, and operational documentation.

---

## 2. Scope and Assumptions

### In Scope
- Replication topology setup and sync validation.
- Failover promotion procedures and timing.
- Lag monitoring and alerting logic.
- Application connection string failover.
- Runbook/documentation completeness checks.

### Out of Scope
- Live database platform deployment internals.
- Multi-region or advanced replication topologies.

### Assumptions
- Replication status is available via testable adapters.
- Connection string failover is managed by an injectable config provider.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Standby replica maintains sync with primary | UT-084-001, UT-084-002 |
| AC-2 | Standby promoted within target failover time | UT-084-003, UT-084-004 |
| AC-3 | Replication lag monitored with alerting | UT-084-005, UT-084-006 |
| AC-4 | App connectivity updated to new primary | UT-084-007, UT-084-008 |
| AC-5 | Failover procedures and roles documented | UT-084-009, UT-084-010 |

---

## 4. Unit Test Areas

### UT-084-001: Standby replication state reflects primary changes
- Mock primary update event.
- Assert standby state synchronized.

### UT-084-002: Backup and restore compatible with replication
- Simulate backup during replication.
- Assert backup validity and restore compatibility.

### UT-084-003: Promotion procedure transitions standby to writable primary
- Trigger promotion workflow.
- Assert standby becomes writable primary.

### UT-084-004: Promotion timing meets target failover window
- Measure promotion latency.
- Assert within configured target (e.g., < 30 seconds).

### UT-084-005: Replication lag monitor calculates and tracks lag
- Mock replication event delay.
- Assert lag metric calculated correctly.

### UT-084-006: Alert generated when lag exceeds threshold
- Inject lag above threshold.
- Assert alert event emitted.

### UT-084-007: Connection string failover logic switches to new primary
- Mock promotion event.
- Assert app connection config updated to new endpoint.

### UT-084-008: App reconnection succeeds after failover
- Simulate failover and reconnect.
- Assert query execution on promoted primary succeeds.

### UT-084-009: Operational runbook includes all required procedures
- Assert document includes roles, steps, timing, recovery checks.

### UT-084-010: Runbook is stakeholder-usable
- Assert clarity and completeness for ops team.

---

## 5. Test Data and Mocking Strategy

- Fixtures: sync/lag states, promotion workflows, connection configs, lag thresholds.
- Mocks: replication monitor, promotion executor, connection manager, alert emitter.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-084-001 through UT-084-008.

---

## 7. Suggested File Layout

- tests/unit/db/ReplicationTopologySync.test.ts
- tests/unit/db/FailoverPromotion.test.ts
- tests/unit/db/ReplicationLagMonitoring.test.ts
- tests/unit/db/FailoverConnectivity.test.ts
- tests/unit/db/__fixtures__/replication.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-084-001 through UT-084-010 implemented.
- [ ] AC-1 through AC-5 traceability retained.
- [ ] Coverage and CI reliability targets met.
