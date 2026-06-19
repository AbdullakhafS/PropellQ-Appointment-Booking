# UNIT-TEST-PLAN-083: Load Balancer Configuration

User Story: US-083 (EP-008)
Source File: .propel/context/tasks/EP-008/us_083/us_083.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for load balancer configuration, health-based routing, stateless traffic handling, multi-instance distribution, and zero-downtime configuration updates.

---

## 2. Scope and Assumptions

### In Scope
- Load balancer listener/backend pool configuration validation.
- Health check integration and unhealthy instance removal.
- Session affinity policy enforcement (disabled for stateless).
- Multi-instance traffic distribution.
- Configuration update rollout safety.

### Out of Scope
- TLS certificate provisioning internals.
- Application-level routing logic.

### Assumptions
- Load balancer configuration is represented in testable abstractions.
- Health check status is available via mocked status provider.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Traffic evenly distributed across instances | UT-083-001, UT-083-002 |
| AC-2 | Unhealthy instances removed from routing | UT-083-003, UT-083-004 |
| AC-3 | Session affinity disabled for stateless traffic | UT-083-005, UT-083-006 |
| AC-4 | Routing across at least three instances | UT-083-007, UT-083-008 |
| AC-5 | Config updates possible without downtime | UT-083-009, UT-083-010 |

---

## 4. Unit Test Areas

### UT-083-001: Distribution algorithm cycles across healthy instances fairly
- Mock 3 healthy backend instances.
- Simulate traffic distribution logic.
- Assert round-robin or similar fair distribution.

### UT-083-002: Uneven instance capacities are respected in distribution
- Mock weighted instance configs.
- Assert distribution respects weight ratios.

### UT-083-003: Unhealthy instance is removed from routing pool
- Mock health check failure for one instance.
- Assert removal from active routing set.

### UT-083-004: Instance removal happens within configured health check window
- Time simulated health failures.
- Assert removal timing meets policy window.

### UT-083-005: Session affinity/sticky session policy is disabled
- Assert cookie-based or LB affinity settings disabled for stateless pools.

### UT-083-006: New request distribution does not favor previous instance
- Simulate multi-request flow.
- Assert no unintended affinity or stickiness.

### UT-083-007: Configuration supports three backend instances minimum
- Create config with 3+ instances.
- Assert routing distributes across all.

### UT-083-008: Capacity validator rejects configs with fewer than 3 instances
- Attempt 2-instance config.
- Assert validation failure.

### UT-083-009: Config update applies without draining existing connections
- Update config (listeners/pool) fixture.
- Assert update succeeds and active traffic flows continue.

### UT-083-010: Configuration changes are version-controlled and rollback-safe
- Apply config update.
- Assert version metadata and rollback path exists.

---

## 5. Test Data and Mocking Strategy

- Fixtures: 3+ instance pools, healthy/unhealthy status sets, weighted configs, update scenarios.
- Mocks: health check provider, instance registry, config persistence layer.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-083-001 through UT-083-008.

---

## 7. Suggested File Layout

- tests/unit/infra/LoadBalancerDistribution.test.ts
- tests/unit/infra/LoadBalancerHealthRouting.test.ts
- tests/unit/infra/LoadBalancerStatelessPolicy.test.ts
- tests/unit/infra/LoadBalancerConfigUpdate.test.ts
- tests/unit/infra/__fixtures__/loadBalancer.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-083-001 through UT-083-010 implemented.
- [ ] AC-1 through AC-5 traceability retained.
- [ ] Coverage and CI reliability targets met.
