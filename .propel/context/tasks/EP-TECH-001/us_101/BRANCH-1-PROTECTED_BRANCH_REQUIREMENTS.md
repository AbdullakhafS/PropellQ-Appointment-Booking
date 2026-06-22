# BRANCH-1: Protected Branch Requirements

## Overview

This document specifies the branch protection rules for the PropellQ repository to enforce code quality and security gates before merge.

---

## 1. Protected Branches

### Primary Protected Branches

| Branch | Purpose | Protection Level |
|--------|---------|-----------------|
| `main` | Production release branch | **STRICT** - All gates required |
| `develop` | Integration branch | **STANDARD** - All gates required |

### Secondary Protected Branches (Optional)

| Branch | Purpose | Protection Level |
|--------|---------|-----------------|
| `release/*` | Release preparation | **STANDARD** - All gates required |
| `hotfix/*` | Production emergency fixes | **STANDARD** - All gates required |

---

## 2. Required Status Checks

All of the following checks MUST pass before PR merge:

### 2.1 CI Quality Gate Checks (Mandatory)

| Check Name | Job ID | Required | Requirement |
|------------|--------|----------|-------------|
| Lint & Code Quality | `lint` | ✅ YES | Must pass. Cannot merge with style violations. |
| Unit Tests | `test` | ✅ YES | Must pass. Cannot merge with failing tests. |
| Security Scanning | `security` | ✅ YES | Must pass. HIGH/CRITICAL findings block merge. |
| Required Files Check | `check-required-files` | ✅ YES | Must pass. Cannot merge without required deliverables. |
| CI Summary | `summary` | ✅ YES | Must pass. Confirms all checks completed. |

### 2.2 Branch Protection Configuration

**GitHub Settings** → **Branches** → **main**:

```
✅ Require a pull request before merging
   ├─ Require approvals: 1
   ├─ Require review from code owners: YES
   ├─ Dismiss stale pull request approvals when new commits are pushed: YES
   └─ Require approval of the most recent reviewable push: YES

✅ Require status checks to pass before merging
   ├─ Require branches to be up to date before merging: YES (stale PR rejected)
   ├─ Required status checks:
   │  ├─ lint (CI Quality Gates)
   │  ├─ test (CI Quality Gates)
   │  ├─ security (CI Quality Gates)
   │  ├─ check-required-files (CI Quality Gates)
   │  └─ summary (CI Quality Gates)
   └─ Require commit signature: NO (can enable for security)

✅ Require branches to be up to date before merging

✅ Include administrators
   └─ Restrict who can push to matching branches
```

---

## 3. Merge Requirements

### 3.1 Before Merge

**Checklist for PR author**:

- [ ] All required status checks passing (green checkmarks)
- [ ] At least 1 approval from code owner
- [ ] No merge conflicts with `main` or `develop`
- [ ] Branch is up to date with target branch
- [ ] Commit history is clean (squash if needed)
- [ ] PR description documents changes
- [ ] No pending CI jobs (allow concurrent CI to complete)

### 3.2 Merge Blocking Rules

**PR cannot merge if**:

```
❌ Any required status check failing
❌ PR conflicts with target branch
❌ PR branch is out of date with target
❌ < 1 approvals from code owners
❌ Push pending (code changes waiting for CI)
❌ Force push without justification
```

### 3.3 Merge Methods

**Allowed merge methods**:

- ✅ **Squash and merge** (preferred) - Clean history, one commit per feature
- ✅ **Rebase and merge** - Preserves commit history for complex changes
- ✅ **Merge commit** (not preferred) - Creates merge commit (bloats history)

**Recommendation**: Squash and merge for most PRs

---

## 4. Handling Protected Branch Exceptions

### 4.1 Force Push to Protected Branch

**Process**:

1. Contact repository admin or tech lead
2. Provide justification: "Reverting broken commit abc123 introduced regression"
3. Admin unlocks branch temporarily
4. Developer performs force push
5. Branch automatically re-protected after 15 minutes

**Allowed reasons**:

✅ Revert broken production release  
✅ Fix non-squashable commit history error  
✅ Security incident response  

**Not allowed**:

❌ Rewriting history for cosmetic reasons  
❌ Removing previous commits without audit trail  

### 4.2 Bypassing Status Checks

**Policy**: Status checks cannot be bypassed. If check is blocking:

1. **Fix the issue** (preferred)
   - Run linter locally: `black app/src`
   - Run tests locally: `pytest app/tests/`
   - Run security scan: `bandit -r app/src`

2. **Request waiver** (if legitimate exception)
   - For security findings: See [SEC-2 Waiver Workflow](./SEC-2-SECURITY_WAIVER_WORKFLOW.md)
   - For flaky tests: See [TEST-1 Retry Policy](./TEST-1-FLAKY_RETRY_POLICY.md)

3. **Appeal to admin** (if check is buggy)
   - Provide evidence check is false positive
   - Request admin review to disable check temporarily

**Never**:
❌ Ask admin to bypass security or test gates  
❌ Disable required checks without security review  
❌ Merge broken code to debug in production  

---

## 5. Code Owner Requirements

### 5.1 Setting Code Owners

**File**: `.github/CODEOWNERS`

```
# PropellQ Code Ownership Map

# Infrastructure & CI/CD
.github/workflows/ @tech-lead @devops-team
.propel/ @tech-lead

# API & Standards (TASK-098)
app/src/api_standards.py @api-owner @tech-lead
app/src/middleware_contract.py @api-owner

# Logging (TASK-099)
app/src/logging_*.py @observability-lead @tech-lead
app/src/middleware_contract.py @observability-lead

# Tracing (TASK-100)
app/src/tracing_*.py @observability-lead @tech-lead
app/src/metrics_slo.py @observability-lead
app/src/alerting_engine.py @observability-lead
app/src/observability_dashboard.py @observability-lead

# Tests
app/tests/ @qa-lead @tech-lead

# Documentation
*.md @tech-lead @product-manager
app/ @tech-lead
```

### 5.2 Code Owner Approval Rules

**Rules**:

- ✅ PR requires approval from code owner
- ✅ Changes to codebase need relevant owner review
- ✅ Multiple code owners can review same file (1 approval sufficient)
- ✅ PR author cannot approve own changes
- ✅ Code owners are automatically requested as reviewers

---

## 6. Dismissing Stale Reviews

**Configuration**: When new commits are pushed to PR:

```
✅ Dismiss stale pull request approvals when new commits are pushed

Behavior:
- Existing approvals marked as "outdated"
- New approval required
- Forces re-review of changed code
```

**Rationale**: Ensures reviews reflect latest code

---

## 7. Require Commit Signatures

**Option**: Enforce GPG-signed commits (optional for security)

**Current**: NOT required  
**Future**: Consider enabling for `main` after dev team setup

**If enabled**:
```
✅ Require signed commits
   └─ Commits must be signed with verified GPG key
```

---

## 8. Permitted Branch Access

### 8.1 Who Can Push to Protected Branch

**Default**: All developers with repo access can push (via PR only)

**Cannot push directly to main/develop**:
```
Branch Protection Rule: "Restrict who can push to matching branches"
- Only repository admins and tech leads can push directly
- All other developers must use PR workflow
```

### 8.2 Exceptions

**When direct push allowed**:

1. Emergency production hotfix (15-minute window)
2. Reverting broken release
3. Admin performing authorized changes

**Process**:
1. Tech lead unlocks branch
2. Developer performs push with justification message
3. Branch auto-re-protected after push
4. Incident documented in .propel/incidents/

---

## 9. Stale PR Management

**Automatic rules** (GitHub settings):

```
Stale PR Detection:
- No activity for 30 days → Mark as stale
- After 60 days → Close with comment
- Preserve label: "stale" for later reference
```

**Manual override**:
- Team lead can keep old PR open if active
- Add label: "keep-open-wip"

---

## 10. Rollout Timeline

### Phase 1: Strict on `main` (Immediate)

```
Branch: main
- Require all status checks: YES
- Require 1 approval: YES
- Require up-to-date: YES
- Include admins: YES
```

### Phase 2: Standard on `develop` (After Phase 1 stabilizes - 2 weeks)

```
Branch: develop
- Require all status checks: YES
- Require 1 approval: YES
- Require up-to-date: YES
- Include admins: YES
```

### Phase 3: Release Branch Protection (After production release)

```
Branch: release/*
- Require all status checks: YES
- Require 2 approvals: YES (release stability)
- Require up-to-date: YES
```

---

## 11. Monitoring & Troubleshooting

### 11.1 CI Check Failure Reasons

**Status check failed?** Debug steps:

```bash
# 1. View workflow run details
https://github.com/PropellQ/PropellQ-Appointment-Booking/actions

# 2. Check which job failed
- lint (style issues)
- test (test failures)
- security (SAST/SCA findings)
- check-required-files (missing deliverables)

# 3. Fix locally and repush
black app/src  # Fix linting
pytest app/tests/ -v  # Fix tests
bandit -r app/src  # Check security

# 4. View updated CI status in PR
```

### 11.2 Stale Branch

**PR shows "branch out of date" error?**

```bash
# Approach 1: Update via GitHub UI
1. Click "Update branch" button in PR

# Approach 2: Update locally
git fetch origin
git rebase origin/main
git push --force-with-lease origin branch-name
```

### 11.3 Cannot Merge

**PR blocked for merge?** Checklist:

```
☐ All CI checks green (lint, test, security, files)
☐ Branch is up to date with main/develop
☐ At least 1 approval from code owner
☐ No unresolved conversations in review
☐ No pending CI runs (all checks completed)
```

**Still blocked?** 

```bash
# Check GitHub branch protection settings
https://github.com/PropellQ/PropellQ-Appointment-Booking/settings/branches

# View PR status details
https://github.com/PropellQ/PropellQ-Appointment-Booking/pull/{PR_NUMBER}/checks
```

---

## 12. Emergency Bypass (Security Incident Only)

**Procedure** (requires CTO/Security lead approval):

1. **Assessment**: Is this a genuine security incident?
   - Example: Zero-day exploit requiring immediate patch
   - Example: Production database breach requiring immediate rollback

2. **Approval**: Get 2 approvals from:
   - CTO or Tech Lead
   - Security Lead or VP Eng

3. **Bypass**: Repository admin performs bypass:
   ```bash
   # Temporarily disable protection
   # Perform emergency change
   # Re-enable protection immediately
   # Document in .propel/incidents/
   ```

4. **Post-Incident**: Full review within 24 hours
   - What was bypassed?
   - Was bypass justified?
   - How to prevent need for bypass in future?

---

## 13. Documentation

**User guides**:
- [CI Runbook](./CI-RUNBOOK.md) - Troubleshoot CI failures
- [SEC-2 Waiver Workflow](./SEC-2-SECURITY_WAIVER_WORKFLOW.md) - Request security exceptions
- [TEST-1 Retry Policy](./TEST-1-FLAKY_RETRY_POLICY.md) - Handle flaky tests

---

## 14. Metrics

**Track compliance**:

```
Branch Protection Metrics (monthly):
- Merges blocked by CI: (show improving trend)
- Average time to CI pass: (target < 10 min)
- PRs requiring security waiver: (show < 5% of PRs)
- False positive security findings: (track & reduce)
```

---

**Last Updated**: 2026-06-22  
**Approved By**: Tech Lead & DevOps  
**Effective Date**: 2026-06-22  
**Next Review**: 2026-09-22
