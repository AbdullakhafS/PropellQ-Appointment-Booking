# TASK-099: Implement Centralized Logging with Correlation IDs

User Story: US-099 (EP-TECH-001)
Source File: .propel/context/tasks/EP-TECH-001/us_099/us_099.md
Priority: CRITICAL
Estimated Effort: 3-5 dev days + staging validation
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Implement centralized structured logging with end-to-end correlation IDs and redaction controls so incidents can be traced quickly and securely across service boundaries.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Missing inbound correlation ID is generated and propagated | LOG-1, LOG-2, QA-1 |
| AC-2 | Cross-service events are discoverable by correlation ID timeline | PIPE-1, SEARCH-1, QA-2 |
| AC-3 | PHI/secret masking prevents leakage in emitted logs | SEC-1, SEC-2, QA-3 |
| AC-4 | Production log delivery success >= 99.9% with retry | PIPE-1, PIPE-2, QA-4 |
| AC-5 | Incident search supports service/env/severity/correlation filters | SEARCH-1, DOC-1, QA-5 |
| AC-6 | Environment-specific retention policy is enforced | GOV-1, PIPE-2, QA-6 |

---

## 3. Layered Implementation Tasks

## Logging Standard Tasks

### LOG-1: Structured Log Schema Standard
- Define required JSON fields and severity model.
- Standardize route, actor, status, and environment attributes.

### LOG-2: Correlation Propagation Pattern
- Define correlation ID generation on ingress if missing.
- Propagate correlation across sync calls and async workers.

## Pipeline and Platform Tasks

### PIPE-1: Centralized Log Shipping Pipeline
- Configure service log forwarding to centralized index.
- Add retry/resilience behavior for transient sink failures.

### PIPE-2: Retention and Delivery Reliability Controls
- Configure retention by environment and log class.
- Track delivery success and pipeline backpressure metrics.

## Security and Compliance Tasks

### SEC-1: Redaction and Masking Rules
- Define and implement masking for PHI/PII/secret-bearing fields.
- Validate allowlist/denylist behavior on structured payloads.

### SEC-2: Logging Boundary Controls
- Enforce immutable audit boundary alignment where required.
- Prevent sensitive payload dumps in error serialization paths.

## Search and Operations Tasks

### SEARCH-1: Query and Timeline Experience
- Define standard queries for service/env/severity/correlation filters.
- Provide timeline views for correlation-driven incident debugging.

### GOV-1: Logging Policy Governance
- Publish retention and access policy for each environment.
- Define exception process for temporary debug-level increases.

### DOC-1: Incident Investigation Runbook
- Document investigation flow using correlation IDs and filters.
- Include common query patterns and escalation references.

## Testing Tasks

### QA-1: Correlation Injection Validation
- Validate ID generation when missing and propagation across boundaries.

### QA-2: Cross-Service Discoverability Validation
- Validate related events can be reconstructed by correlation ID.

### QA-3: Redaction Validation
- Seed sensitive fields and validate masking in stored logs.

### QA-4: Delivery Reliability Validation
- Validate delivery success target and retry behavior under transient failures.

### QA-5: Searchability Validation
- Validate filter combinations support incident triage workflows.

### QA-6: Retention Policy Validation
- Validate retention/expiry behavior by environment policy.

---

## 4. Dependencies

- API middleware correlation injection baseline from US-098.
- Aggregation sink/index availability and access controls.

---

## 5. Definition of Done

- [ ] Structured logging schema is adopted in pilot/core services.
- [ ] Correlation IDs propagate end-to-end in staging scenarios.
- [ ] Centralized log pipeline is operational with retry controls.
- [ ] Redaction rules are security-validated.
- [ ] Investigation runbook and search patterns are documented.
- [ ] Retention policy is configured and verified.
- [ ] Acceptance criteria AC-1 through AC-6 are validated and signed off.

---

## 6. Suggested Execution Order

1. LOG-1, LOG-2
2. PIPE-1, PIPE-2
3. SEC-1, SEC-2
4. SEARCH-1, GOV-1
5. DOC-1
6. QA-1 through QA-6
