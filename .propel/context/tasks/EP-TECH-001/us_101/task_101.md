# TASK-101: Add CI Quality Gates (Lint, Test, SAST/SCA)

User Story: US-101 (EP-TECH-001)
Source File: .propel/context/tasks/EP-TECH-001/us_101/us_101.md
Priority: CRITICAL
Estimated Effort: 3-5 dev days + policy validation
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Implement required CI quality gates for linting, test execution, and security scanning so merge/release quality and vulnerability policies are automatically enforced.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | PR merges are blocked when lint/tests fail | CI-1, BRANCH-1, QA-1 |
| AC-2 | High/critical SAST/SCA findings block merge | SEC-1, SEC-2, QA-2 |
| AC-3 | PR checks provide actionable annotations | CI-2, QA-3 |
| AC-4 | Flaky retry policy only applies to configured tests | TEST-1, QA-4 |
| AC-5 | Missing required checks prevent PR merge | BRANCH-1, QA-5 |
| AC-6 | Median pipeline duration remains within agreed threshold | PERF-1, QA-6 |

---

## 3. Layered Implementation Tasks

## CI Pipeline Tasks

### CI-1: Required Check Workflow Design
- Define required lint, unit test, and security check stages for PR pipelines.
- Enforce fail-fast strategy for immediate feedback on hard failures.

### CI-2: PR Annotation and Result Reporting
- Publish check summaries and inline annotations in PR view.
- Standardize failure messages with actionable remediation guidance.

## Security Gate Tasks

### SEC-1: SAST/SCA Policy Configuration
- Define severity thresholds and gate behavior for vulnerability findings.
- Implement dependency/license scanning baseline rules.

### SEC-2: Waiver and Exception Workflow
- Define approved waiver process with owner, reason, and expiry controls.
- Ensure waived findings are auditable and time-bounded.

## Test Reliability Tasks

### TEST-1: Flaky Test Retry Policy
- Tag allowable flaky tests and define limited retry behavior.
- Preserve failure visibility even when retries pass.

## Branch Protection and Governance Tasks

### BRANCH-1: Protected Branch Requirements
- Configure protected branch rules to require all mandatory checks.
- Block merge when required checks are missing or stale.

### PERF-1: Pipeline Performance Optimization
- Parallelize independent jobs and cache dependencies.
- Track and tune median pipeline duration against target.

### DOC-1: CI Troubleshooting and Policy Runbook
- Document gate behavior, common failures, and waiver process.
- Include examples of blocked and passing PR scenarios.

## Testing Tasks

### QA-1: Lint/Test Blocking Validation
- Validate failed lint/tests block PR merge.

### QA-2: Security Blocking Validation
- Validate high/critical findings trigger merge block.

### QA-3: Annotation Validation
- Validate CI outputs are visible and actionable in PR UI.

### QA-4: Retry Policy Validation
- Validate flaky retry behavior is restricted to configured tests.

### QA-5: Branch Protection Validation
- Validate protected branch behavior for missing checks.

### QA-6: Pipeline Duration Validation
- Validate median CI duration remains within threshold after gate rollout.

---

## 4. Dependencies

- Repository admin permissions for branch protections.
- Security tooling configuration and ownership from platform/security teams.

---

## 5. Definition of Done

- [ ] Required quality and security checks are active on protected branches.
- [ ] PRs are blocked on policy-violating quality/security failures.
- [ ] Check annotations are visible and actionable in PRs.
- [ ] Flaky retry behavior is controlled and auditable.
- [ ] Security waiver process is documented and operational.
- [ ] Pipeline performance remains within agreed feedback threshold.
- [ ] CI runbook is published with troubleshooting guidance.
- [ ] Acceptance criteria AC-1 through AC-6 are validated and signed off.

---

## 6. Suggested Execution Order

1. CI-1, CI-2
2. SEC-1, SEC-2
3. TEST-1
4. BRANCH-1
5. PERF-1
6. DOC-1
7. QA-1 through QA-6
