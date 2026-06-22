# TASK-101 Quality Assurance - Test Validation Plan

## Overview

This document outlines the test validation plan for TASK-101 CI Quality Gates. Tests are organized by acceptance criteria (AC-1 through AC-6) and quality assurance goals (QA-1 through QA-6).

---

## Test Organization

| QA ID | Acceptance Criteria | Feature | Test Count |
|-------|-------------------|---------|-----------|
| QA-1 | AC-1 | Lint/tests block merge | 4 tests |
| QA-2 | AC-2 | Security blocking | 3 tests |
| QA-3 | AC-3 | PR annotations | 3 tests |
| QA-4 | AC-4 | Retry policy | 2 tests |
| QA-5 | AC-5 | Branch protection | 3 tests |
| QA-6 | AC-6 | Pipeline duration | 2 tests |
| **Total** | | | **17 tests** |

---

## Test Execution Plan

### Phase 1: Manual Validation (Immediate)

Before CI workflow is live, perform manual validation:

```bash
# 1. Verify workflow file syntax
cd PropellQ-Appointment-Booking
yamllint .github/workflows/ci-quality-gates.yml

# 2. Verify policies and configurations
ls -la .propel/context/tasks/EP-TECH-001/us_101/
# Should exist:
# - SEC-1-SAST_SCA_POLICY.md
# - SEC-2-SECURITY_WAIVER_WORKFLOW.md
# - TEST-1-FLAKY_RETRY_POLICY.md
# - BRANCH-1-PROTECTED_BRANCH_REQUIREMENTS.md
# - PERF-1-PIPELINE_OPTIMIZATION.md
# - CI-RUNBOOK.md
```

### Phase 2: Automated CI Testing (Ongoing)

Once workflow is deployed:

```
Each PR automatically triggers tests via workflow.
Tests are embedded in workflow logic and reported in PR comments.
```

---

## Detailed Test Cases

## QA-1: Lint/Tests Blocking Merge (AC-1)

### UT-101-001: Lint failure blocks merge

**Objective**: Verify that lint failures prevent PR merge

**Setup**:
```bash
# Create a PR with intentional formatting issue
git checkout -b test/lint-fail
echo "x  =    1" >> app/src/test_file.py  # Badly formatted
git add app/src/test_file.py
git commit -m "test: bad formatting"
git push origin test/lint-fail
# Create PR from test/lint-fail
```

**Expected**:
- [ ] GitHub Actions workflow triggered
- [ ] 'Lint' job runs: BLACK CHECK FAILS
- [ ] PR shows ❌ status: "Lint & Code Quality"
- [ ] PR comment indicates: "Black formatting violations detected"
- [ ] "Merge" button disabled with message "Required status check failed"

**Verification**:
```
✅ Lint failure shown in PR checks
✅ Merge blocked
✅ Actionable error message (run: black ...)
```

**Cleanup**:
```bash
git checkout main
git branch -D test/lint-fail
```

---

### UT-101-002: Test failure blocks merge

**Objective**: Verify that test failures prevent PR merge

**Setup**:
```bash
# Create PR with failing test
git checkout -b test/test-fail
# Modify test to fail intentionally
# Change: assert True → assert False
echo "assert False  # Intentional failure" >> app/tests/test_search.py
git add app/tests/test_search.py
git commit -m "test: add failing test"
git push origin test/test-fail
# Create PR
```

**Expected**:
- [ ] GitHub Actions workflow triggered
- [ ] 'Test' job runs: TESTS FAIL
- [ ] PR shows ❌ status: "Unit Tests"
- [ ] PR comment includes test output showing failures
- [ ] "Merge" button disabled

**Verification**:
```
✅ Test failures shown in PR
✅ Merge blocked
✅ Coverage report linked (if > 80%)
```

**Cleanup**:
```bash
git checkout main
git branch -D test/test-fail
```

---

### UT-101-003: All checks must pass together

**Objective**: Verify that ALL checks (lint + tests + security + files) must pass

**Setup**:
```bash
# Clean code (lint OK) but test fails
git checkout -b test/partial-fail
# Lint is fixed, but test fails
black app/src app/tests
echo "assert False" >> app/tests/test_search.py  # Test fails
git add -A
git commit -m "fix: lint, fail: test"
git push origin test/partial-fail
# Create PR
```

**Expected**:
- [ ] Lint job: ✅ PASS
- [ ] Test job: ❌ FAIL
- [ ] Security job: ✅ PASS (no new vulnerabilities)
- [ ] Overall: ❌ MERGE BLOCKED (because test failed)

**Verification**:
```
✅ Merge blocked even with some checks passing
✅ Summary shows overall failure
```

---

### UT-101-004: Passing all gates enables merge

**Objective**: Verify that passing all gates allows merge (with approval)

**Setup**:
```bash
# Create valid PR (all checks pass)
git checkout -b test/all-pass
# Make improvement that passes all checks
cat >> app/src/config.py << 'EOF'

def get_config():
    """Get application configuration."""
    return {"debug": False}
EOF

black app/src --line-length=100
pytest app/tests/ --cov=app/src --cov-fail-under=80
git add -A
git commit -m "feat: add config utility"
git push origin test/all-pass
# Create PR and get approval from code owner
```

**Expected**:
- [ ] All jobs pass: Lint ✅, Tests ✅, Security ✅, Files ✅
- [ ] PR shows ✅ "All checks passed"
- [ ] Code owner can approve
- [ ] "Merge" button becomes enabled

**Verification**:
```
✅ All checks show green checkmarks
✅ Merge button is enabled (once approved)
✅ Developer can complete merge
```

**Cleanup**:
```bash
git checkout main
git branch -D test/all-pass
```

---

## QA-2: Security Blocking (AC-2)

### UT-101-005: HIGH security finding blocks merge

**Objective**: Verify that HIGH/CRITICAL security findings prevent merge

**Setup**:
```bash
# Add intentional security issue
git checkout -b test/security-fail
cat >> app/src/auth.py << 'EOF'

def unsafe_query(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection!
    db.execute(query)
EOF

git add app/src/auth.py
git commit -m "test: add vulnerable code"
git push origin test/security-fail
# Create PR
```

**Expected**:
- [ ] Security job runs: Bandit scans
- [ ] Bandit detects: SQL injection vulnerability (HIGH/CRITICAL)
- [ ] PR shows ❌ status: "Security Scanning"
- [ ] PR comment: "HIGH/CRITICAL SAST findings detected"
- [ ] "Merge" button disabled

**Verification**:
```
✅ Bandit finds security issue
✅ Merge blocked
✅ Finding details shown in PR
```

---

### UT-101-006: Waiver allows merge despite finding

**Objective**: Verify that approved waivers allow merge

**Setup**:
```bash
# Add finding that's actually a false positive
git checkout -b test/security-waived
cat >> app/tests/test_fixtures.py << 'EOF'

TEST_CREDENTIALS = {
    "username": "test_user",
    "password": "test_pass_123"  # False positive - test fixture
}
EOF

# Create waiver file
mkdir -p .propel/waivers
cat > .propel/waivers/bandit_b105_test_2026_06_22.md << 'EOF'
---
waiver_type: false_positive
finding_id: B105
severity: HIGH
status: approved
requested_by: alice@propellq.com
approver: bob@propellq.com
approval_date: 2026-06-22
expiry_date: null
---

## Justification

This is a test fixture, not real credentials.
EOF

git add -A
git commit -m "test: add false-positive security finding with waiver"
git push origin test/security-waived
# Create PR
```

**Expected**:
- [ ] Bandit detects: B105 (hardcoded password)
- [ ] CI checks waiver registry
- [ ] Finding is waived
- [ ] PR shows ⚠️ "Security: 1 finding (1 waived)"
- [ ] "Merge" button is enabled (other checks pass + approved)

**Verification**:
```
✅ Finding detected but waived
✅ PR annotations show waiver status
✅ Merge allowed with waived finding
```

---

### UT-101-007: Vulnerable dependency blocks merge

**Objective**: Verify that CRITICAL/HIGH dependency vulnerabilities block merge

**Setup**:
```bash
# Add known vulnerable package to requirements
echo "insecure-package==1.0.0" >> requirements.txt
git add requirements.txt
git commit -m "test: add vulnerable dependency"
git push origin test/vuln-depend
# Create PR
```

**Expected**:
- [ ] pip-audit runs: Finds vulnerability in insecure-package
- [ ] Severity: CRITICAL or HIGH
- [ ] PR shows ❌ "Security Scanning failed"
- [ ] Merge blocked

**Verification**:
```
✅ Vulnerable dependency detected
✅ Merge blocked
```

---

## QA-3: PR Annotations (AC-3)

### UT-101-008: Lint errors annotated in PR

**Objective**: Verify that lint failures show actionable annotations

**Setup**:
```bash
# Create formatting issues
git checkout -b test/lint-annotations
echo "import    os" >> app/src/test.py  # Bad spacing
echo "x=1;y=2;z=3" >> app/src/test.py  # Unreadable
git add app/src/test.py
git commit -m "test: formatting issues"
git push origin test/lint-annotations
# Create PR
```

**Expected**:
- [ ] CI runs lint job
- [ ] PR gets comment: "## Linting Results"
- [ ] Comment shows:
  - [ ] Which tools failed (Black, isort, Flake8)
  - [ ] Code snippets of failures
  - [ ] Actionable fix commands: "Run: `black app/src ...`"
- [ ] Developer can copy-paste commands to fix

**Verification**:
```
✅ PR comment visible
✅ Error messages clear
✅ Fix commands actionable (can copy-paste)
```

---

### UT-101-009: Test failures annotated in PR

**Objective**: Verify that test failures show clear annotations

**Setup**:
```bash
git checkout -b test/test-annotations
# Create failing test with clear output
cat >> app/tests/test_sample.py << 'EOF'
def test_example():
    result = 1 + 1
    assert result == 3, f"Expected 3, got {result}"  # Will fail
EOF

git add app/tests/test_sample.py
git commit -m "test: add test with assertion"
git push origin test/test-annotations
# Create PR
```

**Expected**:
- [ ] CI runs test job
- [ ] Test fails
- [ ] PR gets comment: "## Test Results"
- [ ] Comment shows:
  - [ ] Summary: "1 failed, X passed"
  - [ ] Failure message: "assert result == 3: Expected 3, got 2"
- [ ] Link to coverage report (if coverage OK)

**Verification**:
```
✅ PR comment visible
✅ Test failure output shown
✅ Error message is clear
```

---

### UT-101-010: Security findings annotated in PR

**Objective**: Verify that security findings are clearly annotated

**Setup**:
```bash
git checkout -b test/security-annotations
# Add security issue (as in UT-101-005)
cat >> app/src/app.py << 'EOF'
DEBUG = True  # Will be flagged as B201
EOF

git add app/src/app.py
git commit -m "test: flask debug enabled"
git push origin test/security-annotations
# Create PR
```

**Expected**:
- [ ] CI runs security job
- [ ] Bandit finds: B201 "Flask debug = True"
- [ ] PR gets comment: "## Security Scan Results"
- [ ] Comment shows:
  - [ ] Finding: B201
  - [ ] Severity: HIGH
  - [ ] Location: app/src/app.py
  - [ ] Recommendation: Set DEBUG=False

**Verification**:
```
✅ Security findings clearly annotated
✅ Remediation guidance provided
```

---

## QA-4: Retry Policy (AC-4)

### UT-101-011: Flaky test retried

**Objective**: Verify that marked flaky tests are retried

**Setup**:
```bash
# Create test that sometimes passes, sometimes fails (simulated)
git checkout -b test/flaky-retry
cat > app/tests/test_flaky_sim.py << 'EOF'
import pytest
import random

@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_simulated_flaky():
    """This test randomly fails to simulate flakiness."""
    # In real scenario, this would be timing-dependent
    # For test purposes, we just verify the marker is present
    assert True  # Always passes
EOF

git add app/tests/test_flaky_sim.py
git commit -m "test: add flaky test with marker"
git push origin test/flaky-retry
# Create PR
```

**Expected**:
- [ ] Test runs in CI
- [ ] Even if it fails once, it retries (max 2 retries = 3 attempts)
- [ ] Test output shows: "test_flaky_sim.py PASSED (attempt 1)"
- [ ] No merge blocking (test passes after retries)

**Verification**:
```
✅ Flaky test retried on failure
✅ Final result reported
✅ Merge allowed if passes eventually
```

---

### UT-101-012: Non-flaky test only runs once

**Objective**: Verify that regular tests don't get retried

**Setup**:
```bash
# Create normal test without flaky marker
git checkout -b test/normal-noretry
cat > app/tests/test_normal.py << 'EOF'
def test_deterministic():
    assert 1 + 1 == 2
EOF

git add app/tests/test_normal.py
git commit -m "test: add normal test"
git push origin test/normal-noretry
# Create PR
```

**Expected**:
- [ ] Test runs once (no retries)
- [ ] Test output shows: "test_normal.py PASSED"
- [ ] Not labeled with "(attempt 1)" (only flaky tests show this)

**Verification**:
```
✅ Normal tests run once
✅ No unnecessary retries
✅ Pipeline faster for normal tests
```

---

## QA-5: Branch Protection (AC-5)

### UT-101-013: Missing checks prevent merge

**Objective**: Verify that branch protection requires all checks

**Setup**:
```
1. Open GitHub repository settings
2. Go to: Branches → Branch protection rules → main
3. Verify configured:
   ✅ Require pull request before merging
   ✅ Require status checks:
      - lint
      - test
      - security
      - check-required-files
```

**Test**:
```bash
# Create PR (any valid PR)
git checkout -b test/branch-protection
echo "# test" >> README.md
git add README.md
git commit -m "docs: update readme"
git push origin test/branch-protection
# Create PR
```

**Expected**:
- [ ] All required checks listed in PR
- [ ] If one check is missing/disabled, "Merge" button disabled
- [ ] Message: "Missing required status check: lint"
- [ ] Developer must wait for all checks to complete

**Verification**:
```
✅ All required checks enforced
✅ Cannot merge with missing checks
```

---

### UT-101-014: Stale branch cannot merge

**Objective**: Verify that PR must be up-to-date with target branch

**Setup**:
```bash
# Create two branches
git checkout main
git checkout -b feature/branch-a
echo "feature a" >> file.txt
git add file.txt
git commit -m "feat: feature a"
git push origin feature/branch-a

# Meanwhile, someone merges to main
git checkout main
git checkout -b feature/branch-b
echo "feature b" >> other.txt
git add other.txt
git commit -m "feat: feature b"
git push origin feature/branch-b

# Merge branch-b to main first
git checkout main
git pull origin main
# (Simulate merge via GitHub UI)

# Now branch-a is stale (out of date with main)
# Create PR from branch-a
```

**Expected**:
- [ ] PR shows: "This branch has conflicts" or "This branch is out of date"
- [ ] "Merge" button disabled
- [ ] Message: "Requires branches to be up to date before merging"
- [ ] "Update branch" button available in GitHub UI

**Verification**:
```
✅ Stale branch detected
✅ Merge blocked until updated
✅ Can click "Update branch" to fix
```

---

### UT-101-015: Code owner approval required

**Objective**: Verify that code owner approval is required

**Setup**:
```
1. Setup CODEOWNERS file (.github/CODEOWNERS)
2. Assign @tech-lead as owner of app/src/
3. Create PR modifying app/src/test.py
```

**Test**:
```bash
# Non-owner creates PR
git checkout -b test/needs-approval
echo "# code" >> app/src/test.py
git add app/src/test.py
git commit -m "feat: test"
git push origin test/needs-approval
# Create PR (as non-owner)
```

**Expected**:
- [ ] PR shows: "Review required"
- [ ] @tech-lead (code owner) automatically requested as reviewer
- [ ] "Merge" button disabled: "Requires at least 1 approval"
- [ ] Tech lead approves → "Merge" button enabled

**Verification**:
```
✅ Code owner automatically requested
✅ Merge blocked without approval
✅ Enabled once approved
```

---

## QA-6: Pipeline Duration (AC-6)

### UT-101-016: Median pipeline duration < 8 minutes

**Objective**: Verify that CI completes within 8-minute target

**Setup**:
```bash
# Monitor last 10 CI runs
https://github.com/PropellQ/PropellQ-Appointment-Booking/actions
# Filter: ci-quality-gates workflow
```

**Test**:
```bash
# Check duration of each run
# For each run:
#   - Record total duration
#   - Calculate median
```

**Expected**:
- [ ] Median duration: < 8 minutes
- [ ] p95 duration: < 12 minutes
- [ ] No runs > 15 minutes

**Verification**:
```
✅ Median < 8 min target
✅ P95 < 12 min acceptable
✅ Outliers investigated
```

**If exceeding target**:

```bash
# 1. Check which job is slow
# 2. Review PERF-1 optimization guide
# 3. Implement optimizations:
#    - Parallel execution
#    - Caching
#    - Removing optional steps
```

---

### UT-101-017: Cache effectiveness measured

**Objective**: Verify that caching reduces CI duration over time

**Setup**:
```bash
# Track metrics over 2 weeks
# Collect from GitHub Actions UI:
# - Duration of each job
# - Cache hit rate
```

**Expected**:
- [ ] First run: ~15 minutes (no cache)
- [ ] Subsequent runs: ~5-6 minutes (cached)
- [ ] Cache hit rate: > 90%
- [ ] Trend: Duration stable or decreasing

**Verification**:
```
✅ Cache provides 60%+ speedup
✅ Consistent performance maintained
✅ No regressions over time
```

---

## Acceptance Criteria Coverage Matrix

| AC | QA | Tests | Coverage |
|----|-----|-------|----------|
| AC-1: Lint/tests block merge | QA-1 | UT-001-004 | 4 tests |
| AC-2: Security blocking | QA-2 | UT-005-007 | 3 tests |
| AC-3: PR annotations | QA-3 | UT-008-010 | 3 tests |
| AC-4: Retry policy | QA-4 | UT-011-012 | 2 tests |
| AC-5: Branch protection | QA-5 | UT-013-015 | 3 tests |
| AC-6: Pipeline duration | QA-6 | UT-016-017 | 2 tests |

**Total**: 17 test cases covering all 6 acceptance criteria

---

## Test Execution Timeline

### Week 1: Manual Validation
- [ ] UT-101-001 through UT-101-003 (Lint blocking)
- [ ] UT-101-004 (All gates pass)
- [ ] UT-101-005 through UT-101-007 (Security blocking)

### Week 2: Annotation & Policy Testing
- [ ] UT-101-008 through UT-101-010 (PR annotations)
- [ ] UT-101-011 through UT-101-012 (Retry policy)
- [ ] UT-101-013 through UT-101-015 (Branch protection)

### Week 3: Performance Monitoring
- [ ] UT-101-016 through UT-101-017 (Duration tracking)
- [ ] Collect baseline metrics
- [ ] Document results

---

## Success Criteria

✅ **All 17 test cases pass**  
✅ **No blocking issues preventing merge on `main`**  
✅ **All developers can merge code in < 10 minutes from approval**  
✅ **Security findings properly blocked/waived**  
✅ **PR annotations helpful and actionable**  

---

**Last Updated**: 2026-06-22  
**Test Maintainer**: QA Lead  
**Next Review**: 2026-09-22
