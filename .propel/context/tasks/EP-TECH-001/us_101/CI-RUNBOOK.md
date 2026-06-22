# CI/CD Runbook - TASK-101

**Purpose**: Comprehensive guide for CI troubleshooting, understanding quality gates, and best practices

**Last Updated**: 2026-06-22  
**Audience**: All developers  
**Quick Links**: [Troubleshooting](#troubleshooting) | [Common Issues](#common-issues) | [Waiver Process](#security-waiver-process)

---

## Table of Contents

1. [Overview](#overview)
2. [Quality Gates](#quality-gates)
3. [Troubleshooting](#troubleshooting)
4. [Common Issues & Solutions](#common-issues)
5. [Security Waiver Process](#security-waiver-process)
6. [Performance Tips](#performance-tips)
7. [FAQ](#faq)

---

## Overview

### What is the CI Pipeline?

The CI (Continuous Integration) pipeline runs automated checks on every pull request to ensure code quality before merge:

```
You create PR
    ↓
[GitHub] Detects PR → Triggers CI workflow
    ↓
[Parallel Jobs]:
    - Lint checks (code style)
    - Unit tests (correctness)
    - Security scanning (vulnerabilities)
    - File validation
    ↓
[Results]:
    ✅ All pass → Ready for merge
    ❌ Any fail → Fix and re-push
```

### Quality Gates (AC-1 to AC-6)

| Gate | Purpose | Blocks Merge |
|------|---------|------------|
| **Lint** (AC-1) | Code style violations (Black, isort, Flake8) | ❌ YES |
| **Tests** (AC-1) | Failing unit tests | ❌ YES |
| **Security** (AC-2) | HIGH/CRITICAL security findings | ❌ YES |
| **Required Files** (AC-5) | Missing key deliverables | ❌ YES |
| **Branch Protection** (AC-5) | Not up-to-date with main | ❌ YES |

---

## Quality Gates

### Gate 1: Lint & Code Quality (AC-1)

**What it checks**:
- ✅ Code formatted with Black (line length, spacing)
- ✅ Imports organized with isort (alphabetical)
- ✅ No syntax errors (Flake8 critical checks)
- ✅ Code quality score (Pylint, non-blocking)

**If failing**:

```bash
# 1. See which tool failed (check PR comments)
# 2. Fix locally:
cd PropellQ-Appointment-Booking

# Fix all formatting
black app/src app/tests --line-length=100

# Fix import ordering
isort app/src app/tests --profile black

# 3. Check for remaining issues
flake8 app/src app/tests --max-line-length=100

# 4. Commit and push
git add .
git commit -m "fix: apply code formatting"
git push origin your-branch-name

# 5. CI reruns automatically
```

**Common violations**:

| Issue | Fix |
|-------|-----|
| Line too long (>100 chars) | Break into multiple lines |
| Unsorted imports | Run: `isort app/` |
| Extra spaces | Run: `black app/` |
| Missing docstring | Add docstring to function |

### Gate 2: Unit Tests (AC-1)

**What it checks**:
- ✅ All tests pass (pytest)
- ✅ Code coverage ≥ 80%
- ✅ No broken test fixtures

**If failing**:

```bash
# 1. Run tests locally to debug
pytest app/tests/ -v

# 2. Fix failing test
# Either:
#   a) Fix the application code (test revealed bug)
#   b) Fix the test (test was wrong)

# 3. Verify tests pass locally
pytest app/tests/ --cov=app/src --cov-fail-under=80

# 4. Push fixed code
git add .
git commit -m "fix: resolve test failures"
git push origin your-branch-name
```

**Test tips**:

```python
# Mark test as flaky only if truly intermittent
@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_timing_sensitive():
    """Test that occasionally times out."""
    pass

# Don't mark as flaky if test is deterministic
# Instead: fix the test to be deterministic
```

### Gate 3: Security Scanning (AC-2)

**What it checks**:
- ✅ Bandit SAST: Hardcoded passwords, SQL injection, etc.
- ✅ pip-audit SCA: Vulnerable dependencies

**If finding HIGH or CRITICAL**:

```
Option 1: Fix the vulnerability
─────────────────────────────────
❌ BAD:
def login(user, password):
    query = f"SELECT * FROM users WHERE user='{user}' AND pass='{password}'"
    
✅ GOOD:
def login(user, password):
    query = "SELECT * FROM users WHERE user=? AND pass=?"
    execute_query(query, (user, password))

Option 2: Request security waiver (if legitimate)
──────────────────────────────────────────────────
See: SEC-2-SECURITY_WAIVER_WORKFLOW.md
```

**Common security findings**:

| Finding | Severity | Solution |
|---------|----------|----------|
| Hardcoded password | HIGH | Move to environment variable |
| SQL injection | CRITICAL | Use parameterized queries |
| Insecure pickle | HIGH | Use JSON instead |
| Eval usage | CRITICAL | Use ast.literal_eval |
| Random for crypto | HIGH | Use secrets module |

### Gate 4: Required Files Check (AC-5)

**What it checks**:
- ✅ api_standards.py exists (TASK-098)
- ✅ logging_schema.py exists (TASK-099)
- ✅ test_tracing_100.py exists (TASK-100)

**If failing**:

```
Missing file: app/src/tracing_instrumentation.py

Solution:
1. Ensure you created the required module
2. Push the file
3. CI will pass on next run
```

### Gate 5: Branch Protection (AC-5)

**What it checks**:
- ✅ PR is up-to-date with target branch (no conflicts)
- ✅ All required checks passed
- ✅ Minimum 1 approval from code owner

**If failing**:

```
Error: "Branch is out of date"

Solution:
# In GitHub UI:
1. Click "Update branch" button

# Or locally:
git fetch origin
git rebase origin/main
git push --force-with-lease origin your-branch-name
```

---

## Troubleshooting

### Troubleshooting Flowchart

```
PR blocked by CI?
    ↓
Which gate is failing?
    ├─ Lint → [See lint troubleshooting below]
    ├─ Tests → [See test troubleshooting below]
    ├─ Security → [See security troubleshooting below]
    ├─ Required Files → [See files troubleshooting below]
    └─ Branch Protection → [See branch troubleshooting below]
```

### Lint Troubleshooting

**Problem**: Black formatting check failed

```bash
# View the error
# Action: Run black locally

black app/src app/tests --line-length=100

# This fixes most style issues automatically
# Then commit and push
```

**Problem**: Flake8 says "E501 line too long"

```python
# ❌ BAD - too long
my_variable = some_function(arg1, arg2, arg3, arg4, arg5, arg6, arg7)

# ✅ GOOD - wrapped
my_variable = some_function(
    arg1, arg2, arg3,
    arg4, arg5, arg6,
    arg7
)
```

**Problem**: isort says "imports out of order"

```bash
# Fix automatically
isort app/src app/tests --profile black
```

### Test Troubleshooting

**Problem**: "Test failed: timeout"

```bash
# 1. Increase timeout locally
pytest app/tests/test_booking_platform.py::test_slow_query -v --timeout=30

# 2. If consistently slow:
#    - Review test for efficiency
#    - Check database queries
#    - Consider mocking external calls

# 3. If intermittently slow:
#    - Mark as flaky: @pytest.mark.flaky(reruns=2)
#    - But document root cause in TEST-1 registry
```

**Problem**: "Coverage below 80%"

```bash
# Check which lines aren't covered
pytest app/tests/ --cov=app/src --cov-report=html

# Open htmlcov/index.html in browser
# Red lines = not covered by tests
# Add tests to cover those lines
```

**Problem**: "Test passed locally but failed in CI"

```
Likely causes:
1. Different Python version (CI uses 3.11)
   → Fix: Test with Python 3.11 locally

2. Test depends on execution order
   → Fix: Make test independent (use fixtures)

3. Test has timing dependency
   → Fix: Mark as flaky if intermittent
   → Fix: Use polling instead of hard sleep

4. Test needs data that's not available
   → Fix: Mock external dependencies
```

### Security Troubleshooting

**Problem**: "Bandit found B105: Hardcoded Password"

```python
# Check if it's real or false positive

# ❌ Real issue (in test or config):
TEST_DB_PASSWORD = "postgres123"

# ✅ Solution 1 - Move to env var
import os
db_password = os.getenv("DB_PASSWORD", "default")

# ✅ Solution 2 - Request waiver (test fixture)
# See: SEC-2-SECURITY_WAIVER_WORKFLOW.md
```

**Problem**: "pip-audit found CRITICAL vulnerability"

```bash
# 1. Identify the package
pip-audit --desc

# 2. Check if fix available
pip install --upgrade package-name

# 3. If no fix:
#    - Request security waiver
#    - Or use alternative package
```

### Branch Protection Troubleshooting

**Problem**: "Cannot merge - branch is out of date"

```bash
# Solution 1 - GitHub UI (easiest)
1. Open PR
2. Click "Update branch" button
3. Wait for CI to rerun
4. Merge

# Solution 2 - Command line
git fetch origin
git rebase origin/main
git push --force-with-lease origin your-branch-name
```

**Problem**: "Cannot merge - required checks not passing"

```
Checklist:
☐ All CI checks green (lint ✅, tests ✅, security ✅)
☐ At least 1 approval from code owner
☐ Branch is up-to-date with main
☐ No unresolved conversations
☐ No pending CI runs (all checks completed)

If all checks pass but still can't merge:
→ Contact: tech-lead@propellq.com
```

---

## Common Issues

### Issue 1: "CI Takes Too Long"

**Target**: < 8 minutes  
**Actual**: > 10 minutes

**Debugging**:

```bash
# 1. Check GitHub Actions dashboard
https://github.com/PropellQ/PropellQ-Appointment-Booking/actions

# 2. Click on your workflow run
# 3. Identify slow job (usually Tests)

# 4. If tests slow:
pytest app/tests/ --durations=10  # Show slowest 10 tests
```

**Solutions**:

1. **Run tests in parallel** (automatic in CI)
2. **Skip optional reports** (CI does this)
3. **Cache dependencies** (CI does this automatically)
4. **Contact tech-lead** if consistently > 10 min

### Issue 2: "Flaky Test Keeps Failing"

**Symptoms**: Test passes locally, fails in CI intermittently

**Solution**:

```python
# 1. Mark as flaky (temporary)
@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_timing_sensitive():
    pass

# 2. File issue to fix root cause
# See: TEST-1-FLAKY_RETRY_POLICY.md

# 3. Don't add new flaky tests!
```

### Issue 3: "CI Check Blocked for Security Reason"

**Scenario**: PR blocked due to HIGH security finding

**Options**:

```
Option A: Fix the code (preferred)
──────────────────────────────────
1. Review finding details
2. Fix the vulnerability
3. Push fix
4. CI reruns automatically

Option B: Request waiver (if legitimate)
────────────────────────────────────────
1. Review SEC-2-SECURITY_WAIVER_WORKFLOW.md
2. Create waiver file in .propel/waivers/
3. Submit for security team review
4. Once approved, CI will pass

NOT AN OPTION:
❌ Never ask admin to bypass security gate
❌ Never disable required checks
```

### Issue 4: "My Commit Broke the Main Branch"

**Scenario**: You merged code that made main fail

**Immediate Action** (< 15 min):

```bash
# 1. Revert your merge
git revert -m 1 <merge-commit-hash>

# 2. Push revert
git push origin main

# 3. This unblocks other developers

# 4. Notify #development Slack channel
@channel Reverted commit XYZ due to CI failure - investigating now
```

**Long-term Fix**:

```bash
# 1. Investigate root cause
# 2. Fix the issue locally
# 3. Create new PR with fix
# 4. Ensure CI passes before merging
```

### Issue 5: "Need Emergency Fix to Production"

**Scenario**: Production bug, need to skip CI gates

**Process** (requires CTO approval):

1. Document the emergency: "Production database corruption, need immediate rollback"
2. Get 2 approvals:
   - CTO or Tech Lead
   - Security Lead
3. Admin temporarily disables branch protection
4. Emergency fix is pushed
5. Branch protection re-enabled immediately
6. Incident documented in `.propel/incidents/`

**For most cases**: Even critical bugs shouldn't skip ALL gates. Contact tech-lead first.

---

## Security Waiver Process

See: [SEC-2-SECURITY_WAIVER_WORKFLOW.md](SEC-2-SECURITY_WAIVER_WORKFLOW.md)

### Quick Summary

**If security finding is false positive or legitimate exception**:

```bash
# 1. Create waiver file
cat > .propel/waivers/bandit_b105_demo_2026_06_22.md << 'EOF'
---
waiver_type: false_positive
finding_tool: bandit
finding_id: B105
severity: HIGH
status: pending
requested_by: you@propellq.com
---

## Justification

This is a test fixture, not real credentials.
...
EOF

# 2. Comment on PR
@security-team-review false-positive-waiver in .propel/waivers/

# 3. Security team reviews and approves
# 4. CI automatically passes
```

---

## Performance Tips

### Tip 1: Run Tests Locally Before Pushing

```bash
# Takes ~5 min locally, saves time waiting for CI
pytest app/tests/ --cov=app/src --cov-fail-under=80
```

### Tip 2: Format Code Automatically

```bash
# Run before committing
black app/src app/tests --line-length=100
isort app/src app/tests --profile black
```

### Tip 3: Check Security Issues Locally

```bash
# Run before pushing
bandit -r app/src
pip-audit
```

### Tip 4: Use Git Hooks to Automate

```bash
# Auto-format on commit (optional)
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
black app/src app/tests --line-length=100
isort app/src app/tests --profile black
EOF
chmod +x .git/hooks/pre-commit
```

---

## FAQ

### Q: Can I merge without all checks passing?

**A**: No. All checks must pass:
- ✅ Lint
- ✅ Tests
- ✅ Security
- ✅ Required files
- ✅ At least 1 approval

Only exception: Emergency incident with CTO approval (rare).

---

### Q: How long should CI take?

**A**: Target < 8 minutes

| Duration | Status |
|----------|--------|
| < 5 min | Excellent 🟢 |
| 5-8 min | Good 🟡 |
| 8-10 min | Acceptable 🟡 |
| > 10 min | Slow 🔴 |

If consistently > 10 min, notify tech-lead.

---

### Q: What's the difference between passing locally but failing in CI?

**A**: Possible causes:
1. Different Python version (CI: 3.11)
2. Test isolation issue (test depends on order)
3. Timing issue (CI is faster/slower)
4. Missing data (mock not configured properly)

**Debug locally**:
```bash
python --version  # Check version
pytest app/tests/ -v  # Run with verbose output
pytest app/tests/ --durations=10  # Check slow tests
```

---

### Q: Can I retry a failed check without pushing new code?

**A**: Not easily. Options:

1. **Push empty commit**: `git commit --allow-empty && git push`
2. **Request admin re-run**: Contact tech-lead to manually trigger
3. **Fix and push**: Better approach - fix the underlying issue

---

### Q: What if a test is genuinely flaky?

**A**: Document it:

```python
@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_external_api():
    """
    Flaky because external API occasionally times out.
    Root cause: See .propel/context/tasks/.../TEST-1-FLAKY_RETRY_POLICY.md
    """
    pass
```

Then create ticket to fix root cause.

---

### Q: How do I report a CI issue?

**A**: Contact:
- **Quick questions**: Slack #development
- **CI bugs**: File issue in .propel/issues/
- **Urgent**: @tech-lead on Slack

---

### Q: Can I disable linting for my code?

**A**: Not recommended. But if necessary:

```python
# Disable for specific line (last resort)
query = f"SELECT * FROM users WHERE id={user_id}"  # noqa: SQL injection

# But better: Fix the issue properly
query = "SELECT * FROM users WHERE id=?"
execute(query, (user_id,))
```

Disabling checks hides technical debt.

---

## References

- [CI Quality Gates Workflow](../../../.github/workflows/ci-quality-gates.yml)
- [SEC-1: SAST/SCA Policy](./SEC-1-SAST_SCA_POLICY.md)
- [SEC-2: Security Waiver Workflow](./SEC-2-SECURITY_WAIVER_WORKFLOW.md)
- [TEST-1: Flaky Retry Policy](./TEST-1-FLAKY_RETRY_POLICY.md)
- [BRANCH-1: Branch Protection](./BRANCH-1-PROTECTED_BRANCH_REQUIREMENTS.md)
- [PERF-1: Pipeline Optimization](./PERF-1-PIPELINE_OPTIMIZATION.md)

---

## Support

**For questions, issues, or suggestions**:

1. Check this runbook first
2. Search #development Slack
3. Ask tech lead
4. File issue in .propel/issues/

**Last Updated**: 2026-06-22  
**Maintained By**: Tech Lead & DevOps  
**Next Review**: 2026-09-22
