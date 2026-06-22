# BRANCH-1: Protected Branch Requirements

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, repo admins, security team

---

## 1. Overview

This document defines protected branch requirements to enforce mandatory quality gates and prevent unauthorized merges.

---

## 2. GitHub Branch Protection Rules

### 2.1 Main Branch Protection

```yaml
# Branch: main

branch_protection_rules:
  require_pull_request_reviews:
    required_number_of_reviews: 1
    dismiss_stale_reviews: true
    require_review_from_code_owners: true
    require_approval_before_dismissing: true
    
  require_status_checks_to_pass_before_merge:
    required_checks:
      - "Lint Check"
      - "Build"
      - "Unit Tests"
      - "Integration Tests"
      - "SAST Scan"
      - "SCA Scan"
    strict: true  # Re-check after new commits
    
  require_branches_to_be_up_to_date_before_merging: true
  require_code_reviews_before_merging: true
  
  restrictions:
    users: []
    teams:
      - DevOps
      - Security
    apps: []
    
  allow_force_pushes: false
  allow_deletions: false
  require_signed_commits: true
  
  dismiss_stale_pull_request_approvals_on_push: false
```

### 2.2 Develop Branch Protection

```yaml
# Branch: develop
# Slightly less strict than main

required_checks:
  - "Lint Check"
  - "Build"
  - "Unit Tests"
  - "SAST Scan (HIGH/CRITICAL)"
  
required_reviews: 1
dismiss_stale_reviews: true
require_signed_commits: false  # Optional for develop
allow_force_pushes: false
```

### 2.3 Release Branch Protection

```yaml
# Branch: release/*
# Extra strict for releases

required_reviews: 2  # Two approvals required
require_code_owners: true
required_checks:
  - "All quality gates"
  - "Security scan (all levels)"
  - "Performance tests"
  
allow_force_pushes: false
allow_deletions: false
require_signed_commits: true
```

---

## 3. Required Status Checks

### 3.1 Check Enforcement Matrix

| Check | Main | Develop | Release | Blocks Merge |
|---|---|---|---|---|
| Lint | ✅ Required | ✅ Required | ✅ Required | ❌ No |
| Build | ✅ Required | ✅ Required | ✅ Required | ✅ Yes |
| Unit Tests | ✅ Required | ✅ Required | ✅ Required | ✅ Yes |
| Integration Tests | ✅ Required | ⚠️ Optional | ✅ Required | ✅ Yes |
| SAST Scan | ✅ Required | ✅ Required | ✅ Required | ✅ Yes |
| SCA Scan | ✅ Required | ✅ Required | ✅ Required | ✅ Yes |
| E2E Tests | ⚠️ Optional | ⚠️ Optional | ✅ Required | ✅ Yes |

### 3.2 Required vs Optional

**Required (must pass):**
- Lint / Format checks
- Build compilation
- Unit tests (≥80% coverage)
- SAST findings (HIGH/CRITICAL)
- SCA findings (HIGH/CRITICAL)

**Optional (informational):**
- Performance tests
- E2E tests (unless UI changed)
- Documentation coverage

---

## 4. Access Control

### 4.1 Merge Permissions

**Who can merge to main?**

```
Allowed:
  ✅ DevOps team members
  ✅ Release manager
  
Restricted:
  ❌ Developers (must use PR)
  ❌ Service accounts (manual approval)
```

### 4.2 Force Push Restrictions

```
Allowed to force push:
  ❌ No one (disabled for all branches)
  
Rationale:
  - Protects audit trail
  - Prevents accidental history rewrite
  - Enforces proper rebasing workflow
```

---

## 5. Signed Commits

### 5.1 GPG Signing Requirement

```bash
# Configure Git signing
git config --global user.signingKey <GPG_KEY_ID>
git config --global commit.gpgSign true

# Commit with signature (automatic with config)
git commit -m "Fix: SQL injection vulnerability"
  # Signature automatically included

# Verify signature
git log --show-signature
```

### 5.2 GitHub Config

```yaml
require_signed_commits:
  main: true         # Enforce signatures
  develop: false     # Optional
  release/*: true    # Enforce signatures
```

---

## 6. Review Requirements

### 6.1 Code Review Policy

```
Minimum Reviews Required: 1 (main), 2 (release)

Review Criteria:
  ☐ Code follows project standards
  ☐ No security vulnerabilities introduced
  ☐ Tests cover new functionality
  ☐ Documentation updated
  ☐ No merge conflicts
  ☐ All quality gates passed
```

### 6.2 Code Owners

```
# .github/CODEOWNERS file

# Backend
/src/services/      @backend-team
/src/database/      @database-team
/tests/             @qa-team

# Security
/src/auth/          @security-team
/src/crypto/        @security-team

# DevOps
/.github/           @devops-team
/terraform/         @devops-team
/docker/            @devops-team
```

---

## 7. Stale Branch Management

### 7.1 Auto-Delete Stale Branches

```yaml
github-actions:
  delete-stale-branches:
    enabled: true
    stale_after_days: 30
    exclude_branches:
      - main
      - develop
      - release/*
    notification: true
```

### 7.2 Require Up-to-Date Branch

```yaml
require_branches_to_be_up_to_date_before_merging: true

Behavior:
  - PR must be rebased on main before merge
  - Prevents merge conflicts
  - Ensures all checks pass against latest main
```

---

## 8. Enforcement in GitHub Actions

### 8.1 Status Check Success Validation

```yaml
- name: Check All Status Checks Passed
  uses: actions/github-script@v7
  if: always()
  with:
    script: |
      const requiredChecks = [
        'Lint Check',
        'Build',
        'Unit Tests',
        'SAST Scan',
        'SCA Scan'
      ];
      
      const pr = await github.rest.pulls.get({
        owner: context.repo.owner,
        repo: context.repo.repo,
        pull_number: context.issue.number
      });
      
      for (const check of requiredChecks) {
        const status = await github.rest.checks.listForRef({
          owner: context.repo.owner,
          repo: context.repo.repo,
          ref: pr.head.sha,
          check_name: check
        });
        
        if (!status.data.check_runs[0]?.completed) {
          core.setFailed(`${check} not completed`);
        }
      }
```

---

## 9. Bypass Procedures

### 9.1 Emergency Bypass

**Emergency hotfixes bypass review/checks:**

```
Conditions:
  ✅ Production incident (severity SEV1/SEV2)
  ✅ Limited time window (< 30 min)
  ✅ Two-person approval (DevOps + Security)
  
Process:
  1. Create emergency branch from main
  2. Apply minimal fix only
  3. Run all quality gates manually
  4. Get 2 approvals
  5. Merge with force if necessary
  
Audit:
  - Flag in commit message: [EMERGENCY]
  - Notify security/compliance
  - Create incident postmortem
```

### 9.2 Approval Override

```
Only CISO or CTO can override:
  ☐ Signed request issued
  ☐ Documented business justification
  ☐ Automatic audit logging
  ☐ Compliance notification sent
```

---

## 10. Verification Checklist

- [ ] Branch protection rules configured in GitHub
- [ ] All required status checks defined
- [ ] Review requirements set (1+ approval)
- [ ] Code owner enforcement enabled
- [ ] Signed commits required (main, release branches)
- [ ] Force push disabled
- [ ] Up-to-date branch requirement enabled
- [ ] Status check success validation in CI
- [ ] Bypass procedures documented
- [ ] Regular audit of branch rules

---

## References

- GitHub Branch Protection: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches
- GitHub Code Owners: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners

**Next:** [PERF-1: Pipeline Performance Optimization](perf-pipeline-optimization.md)
