# UNIT-TEST-PLAN-095: Auto-Scaling Rules

User Story: US-095 (EP-008)
Source File: .propel/context/tasks/EP-008/us_095/us_095.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for threshold-based auto-scaling policies, scale-up and scale-down behavior, oscillation prevention, and version-controlled policy governance.

---

## 2. Scope and Assumptions

### In Scope
- Scale-up policies and trigger thresholds.
- Scale-down policies with safe cooldowns.
- Oscillation prevention (hysteresis/cooldown).
- Version-controlled auto-scaling policies.

### Out of Scope
- Multi-region scaling strategies.

### Assumptions
- Scaling trigger metrics are injectable.
- Cloud provider autoscaling APIs are mockable.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Auto-scaling scales up before degradation | UT-095-001, UT-095-002 |
| AC-2 | Resources scale down safely with cooldown | UT-095-003, UT-095-004 |
| AC-3 | System stable without oscillation | UT-095-005, UT-095-006 |
| AC-4 | Policies documented and version-controlled | UT-095-007, UT-095-008 |

---

## 4. Unit Test Areas

### UT-095-001: Scale-up triggered when metric exceeds threshold
- Mock high CPU/memory metric.
- Assert scale-up event triggered.

### UT-095-002: Resources scale up before user-facing latency increase
- Simulate high load scenario.
- Assert scaling up occurs proactively.

### UT-095-003: Scale-down triggered when metric drops below threshold
- Mock low utilization metric.
- Assert scale-down event triggered after cooldown.

### UT-095-004: Minimum capacity respected during scale-down
- Attempt scale-down below minimum.
- Assert minimum capacity preserved.

### UT-095-005: Hysteresis prevents oscillation on fluctuating metrics
- Mock fluctuating metric near threshold.
- Assert no rapid scale-up/down cycles.

### UT-095-006: Cooldown period enforced between scaling events
- Trigger multiple scale events rapidly.
- Assert cooldown enforced.

### UT-095-007: Scaling policies stored in version-controlled IaC
- Assert policies retrievable from VCS.

### UT-095-008: Policy changes include rationale documentation
- Assert changes documented with reason/context.

---

## 5. Test Data and Mocking Strategy

- Fixtures: metric values, threshold configs, cooldown periods, scaling policies.
- Mocks: metrics provider, autoscaling executor, VCS adapter.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-095-001 through UT-095-008.

---

## 7. Suggested File Layout

- tests/unit/scaling/ScaleUpPolicies.test.ts
- tests/unit/scaling/ScaleDownPolicies.test.ts
- tests/unit/scaling/OscillationPrevention.test.ts
- tests/unit/scaling/PolicyGovernance.test.ts
- tests/unit/scaling/__fixtures__/autoScaling.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-095-001 through UT-095-008 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
