# CI-2: PR Annotation and Result Reporting

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, CI/CD platform teams, product engineers

---

## 1. Overview

This document defines how CI/CD check results are published to pull requests, annotated inline, and presented to developers with actionable remediation guidance.

**Objectives:**
- Publish check summaries and status to PR
- Annotate code inline at problem location
- Provide clear, actionable error messages
- Enable quick fix identification
- Maintain consistent reporting format

---

## 2. PR Check Status Reporting

### 2.1 Check Status Indicator

**GitHub PR Checks Tab:**

```
PR #1234: Add User Authentication
───────────────────────────────────

✅ Lint Check         Passed (2 min ago)
✅ Build              Passed (1 min ago)  
✅ Unit Tests         Passed (4 min ago, 87% coverage)
✅ Integration Tests  Passed (6 min ago)
❌ SAST Scan          Failed (found 2 HIGH severity issues)
❌ Merge Blocked      Check details required

[View on GitHub Checks page]
```

### 2.2 Detailed Status Page

**When user clicks on failed check:**

```
SAST Scan - Failed ❌
════════════════════════════════════

Run: https://github.com/.../actions/runs/123456
Branch: feature/auth
Duration: 2 min 34 sec

Failure Details:
─────────────────
Critical Issues: 0
High Severity: 2
Medium Severity: 1
Low Severity: 3

Issues Found:
1. SQL Injection Vulnerability in UserService.cs:145
   → Use parameterized queries instead of string concatenation
   
2. Hardcoded Secret in config.json:12
   → Move to environment variable
   
3. Missing Input Validation in AuthHandler.cs:89
   → Add input validation before use

Logs: [Download Full Logs]
```

---

## 3. Inline Code Annotations

### 3.1 Annotation Placement in PR

**GitHub PR diff view:**

```diff
  public class AuthService
  {
      public async Task<User> LoginAsync(string username, string password)
      {
          // ⚠️ ESLint: no-hard-coded-strings
          // Move this magic string to config
          string query = "SELECT * FROM users WHERE username = '" + username + "'";
+         
+         // GitHub Annotation:
+         // ❌ CRITICAL: SQL injection vulnerability
+         // Line 42: Don't concatenate SQL - use parameterized queries
+         // Fix: var query = _db.Query("SELECT * FROM users WHERE username = @user", 
+         //      new { user = username });
          
          var result = await _db.ExecuteAsync(query);
          return result;
      }
  }
```

### 3.2 Annotation Types

**GitHub supports three annotation levels:**

| Level | Icon | Color | Behavior |
|---|---|---|---|
| Error | ❌ | Red | Blocks merge, requires fix |
| Warning | ⚠️ | Yellow | Flagged, doesn't block |
| Notice | ℹ️ | Blue | Informational only |

### 3.3 Annotation Structure

Each annotation includes:

```
File: src/UserService.cs
Line: 42
Type: error
Title: SQL Injection Vulnerability
Body: Use parameterized queries instead of string concatenation
Details: 
  Current: SELECT * FROM users WHERE username = '" + username + "'"
  Recommended: SELECT * FROM users WHERE username = @user
  Reference: OWASP A03:2021 - Injection
```

---

## 4. GitHub Actions Annotation Implementation

### 4.1 Adding Annotations via Workflow

```yaml
- name: Lint with ESLint
  run: npm run lint -- --format json > lint-results.json 2>&1 || true

- name: Process Lint Results
  run: |
    cat lint-results.json | jq -r '.[] | select(.messages | length > 0) | 
      "\(.filePath):\(.messages[0].line):\(.messages[0].column): 
       \(.messages[0].severity) - \(.messages[0].message) (\(.messages[0].ruleId))"' | 
    while read line; do
      echo "::error file=$(echo $line | cut -d: -f1),line=$(echo $line | cut -d: -f2),col=$(echo $line | cut -d: -f3)::$(echo $line | cut -d: -f5-)"
    done
```

### 4.2 Creating Check Runs

**Using GitHub API:**

```bash
curl -X POST \
  https://api.github.com/repos/OWNER/REPO/check-runs \
  -H "Authorization: Bearer ${{ secrets.GITHUB_TOKEN }}" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{
    "name": "ESLint",
    "head_sha": "${{ github.sha }}",
    "status": "completed",
    "conclusion": "failure",
    "output": {
      "title": "ESLint Found Issues",
      "summary": "Found 3 errors and 2 warnings",
      "annotations": [
        {
          "path": "src/App.tsx",
          "start_line": 42,
          "end_line": 42,
          "annotation_level": "error",
          "title": "Unexpected console.log",
          "message": "Remove console.log before deployment",
          "raw_details": "Rule: no-console"
        }
      ]
    }
  }'
```

### 4.3 Workflow Job Summary

**Modern GitHub Actions feature (captured in job summary):**

```yaml
- name: Generate Test Report
  if: always()
  run: |
    echo "# Test Results" >> $GITHUB_STEP_SUMMARY
    echo "## Unit Tests" >> $GITHUB_STEP_SUMMARY
    echo "- Total: 142 tests" >> $GITHUB_STEP_SUMMARY
    echo "- Passed: 140 ✅" >> $GITHUB_STEP_SUMMARY
    echo "- Failed: 2 ❌" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo "### Failed Tests" >> $GITHUB_STEP_SUMMARY
    echo "1. AuthService::LoginAsync_WithInvalidCredentials_ReturnsNull" >> $GITHUB_STEP_SUMMARY
    echo "   Expected: null, Got: User(id=123)" >> $GITHUB_STEP_SUMMARY
    echo "2. PaymentService::ProcessRefund_WithZeroAmount_Throws" >> $GITHUB_STEP_SUMMARY
    echo "   Expected: ArgumentException, Got: success" >> $GITHUB_STEP_SUMMARY
```

---

## 5. Standardized Error Message Format

### 5.1 Error Message Template

```
[CHECK_NAME] [SEVERITY] Failure

File: <path>
Line: <line>
Reason: <what failed>

Current: <current code/configuration>
Expected: <what should be>

Fix: <how to fix in 1-2 sentences>
Reference: <link to docs>

Example:
─────────
```

### 5.2 Examples by Check Type

#### ESLint Error

```
ESLint ERROR: Code style violation

File: src/components/UserForm.tsx
Line: 42
Rule: no-console

Reason: console.log should not be in production code

Current:
  console.log('User ID:', userId);

Expected:
  logger.debug('User ID:', userId);

Fix: Replace console.log with logger.debug() from @app/logger
Reference: https://eslint.org/docs/rules/no-console
```

#### TypeScript Error

```
TypeScript ERROR: Type mismatch

File: src/services/UserService.ts
Line: 156
Error: Argument of type 'string | null' is not assignable to parameter of type 'string'

Current:
  const name: string | null = fetchName(id);
  processName(name);  // ← Error here

Expected:
  const name: string | null = fetchName(id);
  if (name) {
    processName(name);
  }

Fix: Add null check before using potentially null value
Reference: https://www.typescriptlang.org/docs/handbook/2/narrowing.html
```

#### Test Failure

```
Jest FAILURE: Test assertion

File: src/__tests__/AuthService.test.ts
Test: AuthService::login_WithValidCredentials_ReturnsToken
Line: 89
Duration: 2.3s

Error:
  Expected: token length >= 32
  Received: token length = 0

Current Code:
  const token = await authService.login(email, password);
  expect(token.length).toBeGreaterThanOrEqual(32);

The login method returned empty string instead of JWT token.

Debugging Tips:
  1. Verify test data: email & password are valid
  2. Check if AuthService.login is mocked properly
  3. Run: npm test -- --verbose AuthService.test.ts

Reference: https://jestjs.io/docs/expect
```

#### SAST Finding

```
Semgrep CRITICAL: SQL Injection Vulnerability

File: src/repositories/UserRepository.cs
Line: 45
Rule: SQL.Injection.Parameterization

Reason: SQL query uses string concatenation with user input

Vulnerable Code:
  string query = "SELECT * FROM users WHERE id = " + userId;
  var result = await connection.QueryAsync(query);

Secure Fix:
  const query = "SELECT * FROM users WHERE id = @id";
  var result = await connection.QueryAsync(query, new { id = userId });

Severity: CRITICAL (blocks merge)
OWASP: A03:2021 - Injection
Reference: https://owasp.org/www-community/attacks/SQL_Injection

Additional Resources:
  - OWASP SQL Injection: https://owasp.org/www-community/attacks/SQL_Injection
  - Parameterized Queries: https://cheatsheetseries.owasp.org/cheatsheets/...
```

---

## 6. Status Summary Aggregation

### 6.1 PR Status Check Result

**Consolidated status shown on PR:**

```
✅ All Checks Passed (123 checks)

✅ Code Quality
  ├─ ESLint ........................ ✅ 0 errors, 2 warnings
  ├─ TypeScript ................... ✅ strict mode
  ├─ Prettier ..................... ✅ formatted
  └─ Code Coverage ................ ✅ 87% (threshold: 80%)

✅ Build & Tests
  ├─ Build ........................ ✅ 45s
  ├─ Unit Tests ................... ✅ 142/142 passed
  ├─ Integration Tests ............ ✅ 28/28 passed
  └─ E2E Tests .................... ⏭️ skipped (non-web changes)

✅ Security
  ├─ SAST Scan .................... ✅ 0 critical findings
  ├─ SCA Scan ..................... ✅ 0 high-risk dependencies
  └─ Secrets Detection ............ ✅ no secrets found

├─ Accessibility
  ├─ WCAG Compliance .............. ✅ AA rated (if UI changes)
  └─ Keyboard Navigation .......... ✅ tested

✅ Governance
  ├─ Commit Message Format ........ ✅ conventional commits
  ├─ Branch Name Format ........... ✅ feature/auth
  └─ PR Description ............... ✅ complete

Ready to merge ✅
```

### 6.2 Failed Status Example

```
❌ Merge Blocked - Critical Checks Failed

❌ Code Quality
  ├─ ESLint ........................ ❌ 3 errors, 8 warnings
  │  └─ src/App.tsx:42 - no-console
  │  └─ src/utils/helpers.ts:156 - unused-variable
  ├─ TypeScript ................... ✅ strict mode
  ├─ Prettier ..................... ❌ 12 files not formatted
  └─ Code Coverage ................ ⚠️ 76% (threshold: 80%, -4%)

❌ Build & Tests
  ├─ Build ........................ ✅ 45s
  ├─ Unit Tests ................... ❌ 3/142 failed
  │  └─ AuthService.test.ts:89 - login should return token
  │  └─ PaymentService.test.ts:156 - refund should process
  └─ Integration Tests ............ ✅ 28/28 passed

⚠️ Security  
  ├─ SAST Scan .................... ⚠️ 2 HIGH findings
  │  └─ UserRepository.cs:45 - SQL injection (needs waiver or fix)
  │  └─ ConfigService.cs:12 - hardcoded secret (CRITICAL)
  └─ SCA Scan ..................... ✅ 0 high-risk dependencies

Required Actions to Merge:
  1. Fix ESLint errors in src/App.tsx and src/utils/helpers.ts
  2. Run 'npm run format' to auto-fix Prettier issues
  3. Debug & fix 3 failing unit tests (see logs)
  4. Request SAST waiver for SQL injection (optional, or fix)
  5. Remove hardcoded secret from ConfigService.cs (required)

View Detailed Logs: [CI Run #456]
```

---

## 7. Check Result Visibility

### 7.1 GitHub PR Locations

**Check results visible in:**

1. **PR Checks Tab** (top of PR)
   - All checks listed
   - Click to see details

2. **Conversation Tab**
   - Check summary in PR comments
   - Inline code annotations

3. **Files Changed Tab**
   - Inline warnings/errors next to code
   - Hover to see details

4. **Checks Details Page**
   - Full logs and artifacts
   - Download full logs button

### 7.2 Notification Strategy

**Who gets notified:**
- PR author: ✅ Always (via GitHub notification)
- Reviewers: ✅ Always (check status visible)
- PR requester: ✅ Always (watch notifications)

**Notification triggers:**
- First check failure: Comment with summary
- All checks pass: Silent (no comment spam)
- Critical findings: Tag team/platform

---

## 8. Actionable Remediation Examples

### 8.1 Lint Error with Auto-Fix

```
ESLint WARNING: Inconsistent spacing

File: src/helpers.ts
Line: 23

Current:  const x=1+2;
Fix:      const x = 1 + 2;

Auto-fix available: Run 'npm run format' to fix all formatting issues
Documentation: https://prettier.io/
```

### 8.2 Test Failure with Debugging

```
Jest FAILURE: Assertion failed

Test: calculateTotal should sum multiple items

Expected: 150
Received: 0

Debugging checklist:
  ✓ Test data set up correctly
  ✓ Mock dependencies initialized
  ✓ Function parameters passed
  ? Check: Is calculateTotal being called with correct arguments?
  
Debug steps:
  1. Run: npm test -- --verbose --no-coverage calculateTotal
  2. Add: console.log('Input:', items); inside calculateTotal
  3. Compare: Expected flow vs. actual flow
  
View full test output: [CI Run Logs]
```

### 8.3 Security Finding with Fix

```
Snyk CRITICAL: Vulnerable Dependency

Package: lodash
Version: 4.17.20 (current) → 4.17.21 (latest)
Vulnerability: Prototype Pollution

Fix:
  npm update lodash  # Updates to 4.17.21

Or explicitly:
  npm install lodash@4.17.21

Verification:
  npm audit  # Should show 0 vulnerabilities after update
  
Reference: https://nvd.nist.gov/vuln/detail/CVE-2021-23337
```

---

## 9. Configuration Examples

### 9.1 GitHub Action for Reporting

```yaml
- name: Publish Check Results
  if: always()
  uses: actions/github-script@v7
  with:
    script: |
      const fs = require('fs');
      const results = JSON.parse(fs.readFileSync('test-results.json', 'utf8'));
      
      const annotations = results.failures.map(failure => ({
        path: failure.file,
        start_line: failure.line,
        end_line: failure.line,
        annotation_level: failure.severity === 'critical' ? 'error' : 'warning',
        title: failure.title,
        message: failure.message + '\n\nFix: ' + failure.fix
      }));
      
      await github.rest.checks.create({
        owner: context.repo.owner,
        repo: context.repo.repo,
        name: 'Quality Gates',
        head_sha: context.sha,
        status: 'completed',
        conclusion: results.passed ? 'success' : 'failure',
        output: {
          title: 'Check Results',
          summary: `${results.passed_count} passed, ${results.failed_count} failed`,
          annotations: annotations.slice(0, 50)  // GitHub limits to 50 annotations
        }
      });
```

---

## 10. Success Criteria

For CI-2 completion, verify:

- [ ] Check status displayed in PR Checks tab
- [ ] Failed checks block merge (red status)
- [ ] Passed checks show green status
- [ ] Inline annotations appear in Files Changed view
- [ ] Error messages include actionable remediation
- [ ] Examples provided for all check types (lint, test, SAST, SCA)
- [ ] Severity levels (error/warning/notice) properly categorized
- [ ] Check result aggregation shows summary view
- [ ] Notifications configured for critical failures

---

## References

- GitHub Checks API: https://docs.github.com/en/rest/checks
- GitHub Actions Job Summaries: https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary
- GitHub Status Checks: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories/about-status-checks

**Next:** [SEC-1: SAST/SCA Policy Configuration](sast-sca-policy-configuration.md)
