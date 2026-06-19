# TASK-102: Implement Resiliency Defaults (Timeouts, Retries, Circuit Breakers)

User Story: US-102 (EP-TECH-001)
Source File: .propel/context/tasks/EP-TECH-001/us_102/us_102.md
Priority: CRITICAL
Estimated Effort: 5-7 dev days + chaos validation
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Implement shared, safe-by-default resiliency controls for service communication so transient failures are contained, cascading outages are reduced, and critical workflows degrade gracefully.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Safe default timeout values apply by call type when unspecified | RES-1, QA-1 |
| AC-2 | Retries use exponential backoff with jitter and retry budget | RES-2, QA-2 |
| AC-3 | Circuit breaker opens after repeated downstream failures | RES-3, QA-3 |
| AC-4 | Half-open probes validate recovery before close | RES-4, QA-4 |
| AC-5 | Core booking remains available with non-critical outage fallback | FALL-1, QA-5 |
| AC-6 | Chaos tests keep error/latency within guardrails | TEST-1, OBS-1, QA-6 |

---

## 3. Layered Implementation Tasks

## Shared Resiliency Library Tasks

### RES-1: Timeout Default Matrix
- Define timeout defaults by call type (sync, async, external dependency).
- Provide override policy and safe upper/lower bounds.

### RES-2: Retry Strategy with Budget Controls
- Implement exponential backoff with jitter and bounded retry budgets.
- Add per-endpoint allowlist to prevent retry amplification on unsafe paths.

### RES-3: Circuit Breaker Open-State Policy
- Define breaker thresholds for failure count/rate and open duration.
- Enforce pressure relief behavior for failing dependencies.

### RES-4: Half-Open Recovery Policy
- Configure half-open probe cadence and success criteria for reclosing.
- Emit breaker transition events for operations visibility.

## Fallback and Journey Continuity Tasks

### FALL-1: Non-Critical Dependency Fallback Guidelines
- Define fallback patterns for non-critical features during dependency outages.
- Validate core booking path remains available under partial degradation.

### FALL-2: Override Governance
- Define approval process for service-level override of defaults.
- Track override decisions and expiry in governance records.

## Observability and Operations Tasks

### OBS-1: Resiliency Telemetry and Alerting
- Emit timeout, retry, and breaker state metrics.
- Add alerts for retry storms, prolonged open breakers, and fallback activations.

### OPS-1: Breaker and Recovery Runbook
- Document breaker state interpretation and recovery actions.
- Include triage steps for retry amplification and fallback failures.

## Test and Validation Tasks

### TEST-1: Fault Injection and Chaos Suite
- Simulate timeout, error, and outage scenarios for key dependencies.
- Validate system behavior against error-rate and latency guardrails.

### QA-1: Timeout Default Validation
- Validate default timeout application for unconfigured outbound calls.

### QA-2: Retry Policy Validation
- Validate jittered retries and retry budget enforcement.

### QA-3: Breaker Open-State Validation
- Validate breaker opens when thresholds are exceeded.

### QA-4: Half-Open Recovery Validation
- Validate probe-based recovery before breaker closure.

### QA-5: Fallback Continuity Validation
- Validate booking continuity with non-critical dependency outages.

### QA-6: Guardrail Validation Under Chaos
- Validate latency/error guardrails across injected failure scenarios.

---

## 4. Dependencies

- Shared API/middleware baseline from US-098.
- Observability dashboards and alerting baseline from US-100.

---

## 5. Definition of Done

- [ ] Shared resiliency library is integrated in core services.
- [ ] Timeout/retry/circuit-breaker defaults are documented and enforced.
- [ ] Fallback behavior for critical journeys is implemented and validated.
- [ ] Telemetry and alerting for resiliency events are operational.
- [ ] Chaos/fault tests validate no cascading failure behavior.
- [ ] Operational runbook for breaker states and recovery is published.
- [ ] Acceptance criteria AC-1 through AC-6 are validated and signed off.

---

## 6. Suggested Execution Order

1. RES-1, RES-2
2. RES-3, RES-4
3. FALL-1, FALL-2
4. OBS-1
5. OPS-1
6. TEST-1
7. QA-1 through QA-6
