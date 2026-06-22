# TEST-1: Flaky Test Retry Policy

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, QA engineers, CI/CD platform teams

---

## 1. Overview

This document defines how flaky tests are identified, tagged, and retried in CI pipelines with visibility controls to preserve failure awareness.

**Objectives:**
- Tag tests known to be flaky
- Implement limited retry behavior
- Preserve failure visibility
- Prevent flaky tests from blocking merge
- Track and remediate flaky tests

---

## 2. Flaky Test Definition and Causes

### 2.1 What is a Flaky Test?

A flaky test is one that produces both **pass** and **fail** results on identical code:

```
Run 1: ✅ PASS
Run 2: ✅ PASS
Run 3: ❌ FAIL (same code, same commit)
Run 4: ✅ PASS

Result: FLAKY (non-deterministic behavior)
```

### 2.2 Common Causes

```
Timing/Race Conditions:
  ├─ Async operations not awaited
  ├─ setTimeout without guaranteed completion
  ├─ Race between setup and test execution
  └─ Database transactions not isolated

External Dependencies:
  ├─ Network timeouts
  ├─ External API failures
  ├─ Database connection pool exhaustion
  └─ File system race conditions

Test Isolation Issues:
  ├─ Shared state between tests
  ├─ Global variables modified
  ├─ Mock cleanup incomplete
  └─ Database state not reset

Resource Constraints:
  ├─ Memory exhaustion
  ├─ CPU contention
  ├─ Disk space low
  └─ Port already in use
```

---

## 3. Tagging Flaky Tests

### 3.1 Jest Test Tagging

```typescript
// Mark test as flaky with retry limit
describe('AuthService', () => {
  // Flaky test - may timeout intermittently
  test.flaky(
    'should authenticate with external OAuth',
    async () => {
      const result = await authService.loginWithOAuth(email, password);
      expect(result.token).toBeDefined();
    },
    { maxRetries: 2, timeout: 5000 } // Retry up to 2x
  );

  // Alternative: use custom jest.retryOnFailure
  test('should handle network timeout', async () => {
    // This test is known to timeout intermittently
    jest.retryOnFailure(this, 3); // Implicit tagging
    
    const response = await externalAPI.fetch();
    expect(response.ok).toBe(true);
  });
});
```

### 3.2 xUnit (C#) Test Tagging

```csharp
[TestClass]
public class PaymentServiceTests
{
    [TestMethod]
    [Flaky(RetryCount = 2, Reason = "External API timeout")]
    public async Task PaymentService_ChargeCard_WithNetworkIssue_Retries()
    {
        // This test flakes due to external payment gateway timeouts
        var result = await _paymentService.ChargeAsync(cardToken, amount);
        Assert.IsTrue(result.IsSuccess);
    }
    
    [TestMethod]
    [Trait("Flaky", "true")]  // Alternative tagging
    [Timeout(10000)]
    public void DatabaseService_QueryWithTimeout_Retries()
    {
        var result = _db.Query("SELECT * FROM large_table");
        Assert.IsNotNull(result);
    }
}

// Custom attribute
[AttributeUsage(AttributeTargets.Method)]
public class FlakyAttribute : Attribute
{
    public int RetryCount { get; set; } = 2;
    public string Reason { get; set; }
}
```

### 3.3 Pytest (Python) Test Tagging

```python
import pytest

@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_external_api_call():
    """Test may timeout on external API calls"""
    response = external_api.request()
    assert response.status == 200

@pytest.mark.flaky(reruns=3, condition=lambda: os.getenv("CI") == "true")
def test_database_connection():
    """Only flaky in CI environment"""
    result = db.query("SELECT * FROM users")
    assert len(result) > 0

# Custom flaky marker
def flaky(test_func, max_retries=2):
    """Decorator to mark tests as flaky"""
    test_func.flaky = True
    test_func.max_retries = max_retries
    return test_func

@flaky(max_retries=3)
def test_with_custom_marker():
    pass
```

---

## 4. Retry Policy Configuration

### 4.1 Retry Limits by Failure Type

| Failure Type | Max Retries | Rationale |
|---|---|---|
| **Timeout** (Network) | 3x | External transient failures |
| **Timeout** (Database) | 2x | DB query may be slow |
| **Flaky async** | 2x | Race condition may not repeat |
| **Resource exhaustion** | 1x | Usually indicates real issue |
| **Logic errors** | 0x | Cannot retry (deterministic failure) |

### 4.2 Retry Configuration

```yaml
# .jest.config.js
module.exports = {
  testRunner: 'jest-circus/runner',
  testTimeout: 10000,
  
  // Flaky test settings
  flakyTestRetries: {
    defaultMaxRetries: 2,
    retryDelay: 1000,  // 1 second between retries
    retryStrategy: 'exponential-backoff',  // 1s, 2s, 4s
  }
};

# pytest.ini
[pytest]
addopts = 
  --reruns=2
  --reruns-delay=1
  --strict-markers

markers =
  flaky: marks tests as flaky
  slow: marks tests as slow (deselect with '-m "not slow"')
```

---

## 5. GitHub Actions Retry Implementation

### 5.1 Workflow Configuration

```yaml
name: Tests with Flaky Retry

on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - run: npm ci
      
      # Run tests with built-in retry for flaky
      - name: Run Tests
        run: npm test -- --testPathIgnorePatterns=e2e
        env:
          # Env var for test framework to enable retries
          FLAKY_RETRY_ENABLED: true
          FLAKY_MAX_RETRIES: 2
          
      # Separate job for flaky tests (with retry)
      - name: Run Flaky Tests (with retry)
        uses: nick-invision/retry@v2
        with:
          timeout_minutes: 10
          max_attempts: 3
          retry_wait_seconds: 5
          command: npm test -- --testPathPattern=flaky
          
      # Upload test report
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: coverage/
```

### 5.2 Test Summary with Retry Info

```yaml
- name: Publish Test Results
  if: always()
  uses: actions/github-script@v7
  with:
    script: |
      const fs = require('fs');
      const results = JSON.parse(fs.readFileSync('test-results.json'));
      
      let summary = `
      # Test Results
      
      ✅ **Passed**: ${results.passed} tests
      ❌ **Failed**: ${results.failed} tests
      ⏭️ **Skipped**: ${results.skipped} tests
      
      ## Flaky Tests Status
      ${results.flaky_tests.map(t => 
        `- ${t.name}: ${t.final_status} (${t.retry_count} retries)`
      ).join('\n')}
      `;
      
      core.setOutput('summary', summary);
```

---

## 6. Failure Visibility with Retries

### 6.1 Preserve Failure Awareness

**Even when retries pass, flag as flaky:**

```
Test Run Report:
════════════════

✅ authentication_external_oauth
   Status: PASSED (but flaky)
   Attempt 1: ❌ FAIL (timeout after 5s)
   Attempt 2: ✅ PASS
   Retry Count: 1
   ⚠️ ACTION REQUIRED: Test is flaky, needs investigation

✅ payment_processor_charge
   Status: PASSED (but flaky)
   Attempt 1: ✅ PASS
   Attempt 2: ❌ FAIL (connection timeout)
   Attempt 3: ✅ PASS
   Retry Count: 2
   🔴 CRITICAL: Test flaked twice, needs urgent fix

❌ database_query_large_result
   Status: FAILED
   Attempt 1: ❌ FAIL (logic error)
   Attempt 2: ❌ FAIL (logic error)
   Retry Count: 2
   📝 Not flaky - deterministic failure
```

### 6.2 Tracking Flaky Test Patterns

```json
{
  "flaky_tests": [
    {
      "test_name": "authentication_external_oauth",
      "total_runs": 487,
      "failures": 12,
      "flake_rate": "2.5%",
      "cause": "External OAuth timeout",
      "mitigation": "Increase timeout to 10s, add retry",
      "created_date": "2026-05-15",
      "assigned_to": "alice@company.com",
      "due_date": "2026-07-15"
    }
  ]
}
```

---

## 7. Flaky Test Remediation Workflow

### 7.1 Detection and Alerting

```
Trigger: Test marked flaky after 3+ failures in 2 weeks

→ Alert: @engineering-leads
  Subject: "Flaky test alert: authentication_external_oauth"
  Body:
    Test has failed 5 times in last 14 days (2.5% flake rate)
    Root cause suspected: External OAuth timeout
    Action: Investigate and create fix issue
    Due: 2026-07-15
```

### 7.2 Fix Template

```markdown
# Fix: Flaky Test - [Test Name]

## Current Status
- Flake Rate: 2.5% (12 failures / 487 runs)
- Impact: Blocks ~2.5% of PR merges
- Owner: @alice

## Root Cause Analysis
[Describe investigation findings]

## Proposed Fix
[Steps to eliminate flakiness]

## Testing Plan
- [ ] Run test 50x locally to verify determinism
- [ ] Run in CI 10x to verify fix
- [ ] Remove @flaky tag
- [ ] Monitor flake rate in production

## Validation
```

---

## 8. Flaky Test Registry

### 8.1 Registry Structure

```yaml
flaky_tests_registry:
  - id: FLAKY-001
    name: AuthService::LoginAsync_WithOAuth
    file: tests/auth.test.ts:156
    severity: MEDIUM
    flake_rate: 2.5%
    root_cause: External API timeout
    max_retries: 2
    created_date: 2026-05-15
    owner: alice@company.com
    status: OPEN
    fix_due_date: 2026-07-15
    attempts_to_fix: 1
    last_occurrence: 2026-06-21
    
  - id: FLAKY-002
    name: PaymentService::ChargeCard_WithNetworkIssue
    file: tests/payment.test.cs:234
    severity: HIGH
    flake_rate: 5.2%
    root_cause: DB connection pool exhaustion
    max_retries: 3
    created_date: 2026-04-01
    owner: bob@company.com
    status: IN_PROGRESS
    fix_due_date: 2026-07-01
    attempts_to_fix: 3
    last_occurrence: 2026-06-22
```

---

## 9. Metrics and Monitoring

### 9.1 Flaky Test Metrics

```
Dashboard: Flaky Test Health
────────────────────────────

Flaky Test Count: 8
├─ Critical: 1
├─ High: 2
└─ Medium: 5

Trend (Last 30 Days):
  Week 1: 12 flaky tests
  Week 2: 10 flaky tests
  Week 3:  8 flaky tests
  Week 4:  8 flaky tests  ← Improving but plateauing

Overall Flake Rate: 1.2%
  - Target: < 0.5%
  - Status: ⚠️ Above target

Tests Awaiting Fix:
  - Due this week: 2
  - Due next week: 1
  - Overdue: 1 ❌
```

---

## 10. Best Practices

### 10.1 When NOT to Retry

```
❌ DO NOT RETRY:
  - Logic errors (deterministic failures)
  - Assertion failures (test bug)
  - Setup/teardown failures
  - Missing test data

✅ DO RETRY:
  - Network timeouts
  - External API failures
  - Race conditions
  - Resource contention
```

### 10.2 When to Remove Flaky Tag

```
Remove @flaky tag when:
  ✅ Test runs 100+ times without failure
  ✅ Root cause identified and fixed
  ✅ 2 weeks without any flaky failures
  ✅ Code review approved removal
  ✅ Root cause PR merged
```

---

## 11. Success Criteria

For TEST-1 completion, verify:

- [ ] Flaky test tagging system implemented
- [ ] Retry configuration defined per language
- [ ] Retry limits configured (2-3 max)
- [ ] GitHub Actions retry workflow created
- [ ] Failure visibility preserved in reports
- [ ] Flaky test registry created
- [ ] Monitoring/alerts configured
- [ ] Remediation workflow documented
- [ ] Best practices guide created
- [ ] Flaky test SLA defined (fix within 14-30 days)

---

## References

- Jest Flaky Tests: https://jestjs.io/docs/timer-mocks
- pytest-rerunfailures: https://github.com/pytest-dev/pytest-rerunfailures
- GitHub Actions Retry: https://github.com/nick-invision/retry
- Flaky Test Prevention: https://research.google/pubs/Flaky-Tests-at-Google-and-How-We-Mitigate-Them/

**Next:** [BRANCH-1: Protected Branch Requirements](branch-protected-requirements.md)
