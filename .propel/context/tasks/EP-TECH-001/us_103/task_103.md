# TASK-103: Standardize Environment Configuration and Secret Loading

User Story: US-103 (EP-TECH-001)
Source File: .propel/context/tasks/EP-TECH-001/us_103/us_103.md
Priority: CRITICAL
Estimated Effort: 3-5 dev days + rotation drill
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Standardize environment configuration and secure secret loading across environments so deployments are deterministic, auditable, and resilient to configuration drift and secret-handling risks.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Missing required config causes fail-fast startup diagnostics | CFG-1, VALID-1, QA-1 |
| AC-2 | Secrets load from approved manager, not source-controlled files | SEC-1, SEC-2, QA-2 |
| AC-3 | Config precedence rules are deterministic and documented | CFG-2, DOC-1, QA-3 |
| AC-4 | Rotated secrets are consumed without code changes | ROT-1, QA-4 |
| AC-5 | Invalid/unsafe config blocks release in pipeline checks | VALID-2, CI-1, QA-5 |
| AC-6 | Audit evidence includes schema, change history, and access logs | GOV-1, AUDIT-1, QA-6 |

---

## 3. Layered Implementation Tasks

## Configuration Standard Tasks

### CFG-1: Configuration Schema and Catalog
- Define required key catalog by service and environment.
- Publish non-secret template format for local/dev bootstrap.

### CFG-2: Precedence and Resolution Rules
- Define deterministic config precedence (defaults, env overrides, runtime sources).
- Document conflict resolution and prohibited patterns.

## Secret Management Tasks

### SEC-1: Secret Manager Integration Pattern
- Define standard secret loading path from approved secret manager.
- Remove plaintext secret loading patterns from service bootstrap paths.

### SEC-2: Least-Privilege Secret Access Controls
- Define scoped access roles and policy boundaries by service/environment.
- Validate no broad wildcard secret access in service identities.

### ROT-1: Secret Rotation and Revocation Procedure
- Implement blue-green rotation flow and rollback fallback.
- Validate service runtime reload/refresh behavior for rotated secrets.

## Validation and Governance Tasks

### VALID-1: Startup Validation Gate
- Implement fail-fast checks for missing required config/secret keys.
- Provide clear startup diagnostics and actionable messages.

### VALID-2: CI Configuration Safety Checks
- Add pipeline checks for invalid, unsafe, or missing configuration.
- Block release when policy violations are detected.

### GOV-1: Configuration Change Governance
- Define ownership, review requirements, and approval flow for config schema changes.
- Track schema version and compatibility notes.

### AUDIT-1: Access and Change Audit Trail
- Capture secret access logs and configuration change history.
- Ensure evidence retrieval path for audit/compliance review.

### DOC-1: Runbook and Onboarding Documentation
- Document configuration schema, precedence model, and rotation workflow.
- Include troubleshooting guide for startup validation failures.

## Testing Tasks

### QA-1: Fail-Fast Startup Validation
- Validate startup fails with clear diagnostics when required keys are missing.

### QA-2: Secret Source Validation
- Validate secrets are loaded only from approved manager paths.

### QA-3: Precedence Rule Validation
- Validate deterministic precedence outcomes across environments.

### QA-4: Rotation Drill Validation
- Validate rotation/revocation can be consumed without code change.

### QA-5: CI Config Gate Validation
- Validate invalid/unsafe config blocks release pipeline.

### QA-6: Audit Evidence Validation
- Validate retrievability of schema history and secret access logs.

---

## 4. Dependencies

- CI quality gate foundation from US-101.
- Security policy and access model approvals from compliance stakeholders.

---

## 5. Definition of Done

- [ ] Standard config schema and environment catalog are published.
- [ ] Secret manager integration pattern is adopted by core services.
- [ ] Startup fail-fast and CI config checks are active.
- [ ] Rotation and revocation drill is successfully executed.
- [ ] Least-privilege access controls are validated.
- [ ] Audit trails for config/secret access are retrievable.
- [ ] Runbook and onboarding docs are updated.
- [ ] Acceptance criteria AC-1 through AC-6 are validated and signed off.

---

## 6. Suggested Execution Order

1. CFG-1, CFG-2
2. SEC-1, SEC-2
3. VALID-1, VALID-2
4. ROT-1
5. GOV-1, AUDIT-1
6. DOC-1
7. QA-1 through QA-6
