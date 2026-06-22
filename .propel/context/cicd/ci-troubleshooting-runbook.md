# DOC-1: CI Troubleshooting Runbook

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, DevOps, support team

---

## 1. Overview

This runbook provides step-by-step troubleshooting guides for common CI/CD failures and how to resolve them.

---

## 2. Common CI Failures and Solutions

### 2.1 ESLint Failure

**Symptoms:** PR blocked with "❌ Lint Check failed"

**Diagnosis:**
```bash
npm run lint
# View output to identify violations
```

**Common Issues & Fixes:**

| Issue | Fix |
|---|---|
| `no-console` | Remove `console.log()` or use logger instead |
| `unused-variable` | Remove unused variable or prefix with `_` |
| Format issues | Run `npm run format` to auto-fix |

**Resolution Steps:**
```bash
# 1. Auto-fix formatting
npm run format

# 2. Review and fix manually
npm run lint

# 3. Commit and push
git add .
git commit -m "fix: lint errors"
git push
```

### 2.2 Build Failure

**Symptoms:** "❌ Build failed - Compilation error"

**Diagnosis:**
```bash
npm run build 2>&1 | head -50
# View first 50 lines of error
```

**Common Causes:**

1. **TypeScript Error**
   ```
   Error: src/App.tsx:45 - TS2339: Property 'foo' does not exist on type 'Bar'
   
   Fix: Check type definition or add property to interface
   ```

2. **Missing Import**
   ```
   Error: Module not found: './utils'
   
   Fix: Check file path or run npm install
   ```

3. **Out of Memory**
   ```
   Error: JavaScript heap out of memory
   
   Fix: npm run build -- --max-old-space-size=4096
   ```

### 2.3 Test Failure

**Symptoms:** "❌ Unit Tests - 3 failed"

**Diagnosis:**
```bash
# Run failing test
npm test -- --testNamePattern="failing test name"

# View detailed output
npm test -- --verbose --no-coverage
```

**Common Causes & Fixes:**

```
1. Assertion Error
   Expected: true, Received: false
   Fix: Check test logic or implementation

2. Timeout Error
   Error: Timeout - Async callback was not invoked
   Fix: Increase timeout or add await/return

3. Mock Error
   Error: Cannot read property 'mock' of undefined
   Fix: Ensure mock setup complete in beforeEach
```

**Resolution:**
```bash
# 1. Run single test with verbose output
npm test -- AuthService.test.ts --verbose

# 2. Check test expectations
# 3. Debug with console.log or debugger
# 4. Re-run to confirm fix
npm test -- AuthService.test.ts
```

### 2.4 SAST Finding - Cannot Waive

**Symptoms:** "❌ SAST Scan - 1 CRITICAL finding"

**Error Message:**
```
CRITICAL: SQL Injection in UserService.cs:145
├─ Issue: SQL query concatenation with user input
├─ Status: NON-WAIVERABLE (CRITICAL severity)
└─ Action: Fix required before merge
```

**Resolution - Must Fix:**

```csharp
// ❌ WRONG (vulnerable to injection)
string query = "SELECT * FROM users WHERE id = '" + userId + "'";

// ✅ CORRECT (parameterized)
var query = "SELECT * FROM users WHERE id = @id";
var result = await _db.QueryAsync(query, new { id = userId });
```

### 2.5 SCA Finding - Vulnerable Dependency

**Symptoms:** "❌ SCA Scan - npm package 'lodash' has CRITICAL CVE"

**Diagnosis:**
```bash
npm audit
# View detailed vulnerability report
```

**Resolution:**

```bash
# Option 1: Update to fixed version
npm install lodash@latest

# Option 2: If auto-fix available
npm audit fix

# Option 3: If no fix, create waiver (see SEC-2)
# (only for non-critical vulnerabilities)
```

---

## 3. Blocking PR Merges

### 3.1 "Check Required" Error

**Problem:** PR can't merge even though checks show green

**Cause:** 
- GitHub requires status checks to be "required" (not just passing)
- Check may have been manually created instead of from GitHub Actions

**Fix:**
```
1. Go to Settings → Branches → Branch Protection
2. Under "Require status checks to pass"
3. Select the missing check
4. Save
5. Re-run workflow or wait for new push
```

### 3.2 "Review Required"

**Problem:** PR needs approval but all tests pass

**Cause:** 
- Review requirement configured in branch protection
- No code owner approval yet

**Fix:**
```
1. Request review from someone in CODEOWNERS
2. They approve PR
3. Merge becomes available
```

### 3.3 "Branch Out of Date"

**Problem:** "This branch has conflicts with the base branch"

**Fix:**
```bash
# Update local branch
git fetch origin
git rebase origin/main

# Resolve conflicts in editor
# Then force-push
git push origin feature/my-change -f

# OR use merge
git merge origin/main
# Resolve conflicts
git push origin feature/my-change
```

---

## 4. Workflow Re-run

### 4.1 When to Re-run

✅ **Re-run if:**
- Flaky test (documented as flaky)
- Network timeout
- External service unavailable
- Infrastructure issue

❌ **Don't re-run if:**
- Deterministic failure (logic error)
- Linting violation (fix needed)
- Build error (compilation issue)

### 4.2 How to Re-run

**GitHub UI:**
1. Go to PR → "Checks" tab
2. Click failed job
3. Click "Re-run job"

**CLI:**
```bash
# Trigger new workflow run
gh workflow run pr-checks.yml --ref my-branch
```

---

## 5. Performance Issues

### 5.1 "Pipeline Takes 45 Minutes"

**Diagnosis:**
```bash
# Check job timing in GitHub Actions logs
# Each job shows duration

# Slow jobs typically:
# - Unit tests (if not parallelized)
# - Integration tests (if DB slow)
# - E2E tests (if not cached)
```

**Solutions:**

| Problem | Fix |
|---|---|
| Tests serial | Enable test sharding (see PERF-1) |
| No npm cache | Check Actions cache config |
| Slow runner | Use `ubuntu-latest-16-cores` |
| Hanging job | Reduce timeout, debug infinite loop |

### 5.2 "Build Takes 10 Minutes"

**Cause:** Cache miss or slow compilation

**Fix:**
```bash
# Force cache clear
gh cache delete npm-cache

# Re-run to rebuild cache
git commit --allow-empty -m "rebuild cache"
git push
```

---

## 6. Secrets and Credentials

### 6.1 "Hardcoded Secret Found"

**Error:**
```
CRITICAL: Hardcoded credentials in config.json:12
├─ Pattern: api_key = "sk-1234567890abcdef"
└─ Action: Move to environment variable
```

**Fix:**

```json
// ❌ WRONG
{
  "apiKey": "sk-1234567890abcdef"
}

// ✅ CORRECT
{
  "apiKey": "${process.env.API_KEY}"
}
```

**Then:**
```bash
# Add to .env or GitHub Secrets
# Never commit secrets to repo
```

---

## 7. Waiver Process

### 7.1 Creating a Waiver

**For waiverable findings (MEDIUM, some HIGH):**

1. Click the finding in PR
2. Select "Request Waiver"
3. Provide business justification
4. Set expiry date (30-90 days)
5. Submit for review

**See SEC-2 for full details**

---

## 8. Support Escalation

### 8.1 When to Contact DevOps

```
Contact @devops-team if:
✓ GitHub Actions workflow syntax error
✓ Runner unavailable or timing out
✓ Artifact storage full
✓ Cache not working
✓ Can't approve waiver (policy issue)
```

### 8.2 When to Contact Security

```
Contact @security-team if:
✓ SAST/SCA finding severity question
✓ Waiver denied and need to appeal
✓ Suspected false positive
✓ Security-related configuration issue
```

---

## 9. Quick Reference

### 9.1 Common Commands

```bash
# Check local lint
npm run lint

# Fix formatting
npm run format

# Run single test
npm test -- AuthService.test.ts

# Run tests matching pattern
npm test -- --testNamePattern="login"

# Audit dependencies
npm audit

# View CI logs
gh run view <run-id>

# Rerun failed job
gh run rerun <run-id>
```

### 9.2 Useful Links

- GitHub Actions docs: https://docs.github.com/en/actions
- ESLint rules: https://eslint.org/docs/rules
- Jest docs: https://jestjs.io/docs
- npm audit: https://docs.npmjs.com/cli/audit

---

## 10. FAQ

**Q: Why did my PR get blocked after passing tests?**
A: A new commit was pushed to main and your branch is out of date. Rebase and re-push.

**Q: Can I merge without code review?**
A: No. At least 1 approval required for main branch.

**Q: How do I skip tests for documentation-only changes?**
A: Use `[skip ci]` in commit message. (Note: Not recommended for production branches)

**Q: What if the external API is down?**
A: Tests that call external APIs may fail. Wait for service recovery or use mocks.

**Q: Can I waive all findings?**
A: No. CRITICAL vulnerabilities cannot be waived. See SEC-1 for details.

---

## Success Criteria

- [ ] Runbook covers 8+ common failure scenarios
- [ ] Each scenario has diagnosis, root cause, and fix steps
- [ ] Escalation paths clearly defined
- [ ] Links to relevant documentation
- [ ] Quick reference section present
- [ ] FAQ section addresses common questions

---

**Questions?** Reach out to @devops-team or @security-team

**Feedback?** Update this runbook and PR with improvements
