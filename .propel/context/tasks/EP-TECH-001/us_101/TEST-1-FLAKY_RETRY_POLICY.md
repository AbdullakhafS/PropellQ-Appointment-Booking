# TEST-1: Flaky Test Retry Policy

## Overview

This document defines the policy for managing flaky tests in CI pipelines. The goal is to reduce false test failures while maintaining visibility into real issues.

---

## 1. Flaky Test Definition

A test is considered "flaky" if it:
- Passes and fails intermittently without code changes
- Depends on external timing (network delays, database response time)
- Has race conditions or state pollution from test order
- Uses hard timeouts or sleep() without proper waits
- Depends on system resources (disk space, memory, ports)

---

## 2. Retry Policy

### 2.1 Allowed Tests for Retry

Only tests explicitly marked as flaky can be retried.

**Tagging a flaky test**:

```python
import pytest

@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_external_api_call():
    """Test that occasionally times out due to network delays."""
    response = requests.get("https://external-api.example.com/data")
    assert response.status_code == 200
```

**Markers**:
- `@pytest.mark.flaky` - Enables retry behavior
- `reruns=2` - Maximum 2 retries (3 attempts total)
- `reruns_delay=1` - Wait 1 second between retries

### 2.2 Retry Constraints

| Aspect | Policy | Rationale |
|--------|--------|-----------|
| **Max retries** | 2 (3 attempts) | Beyond 2 reruns indicates deeper issue |
| **Retry delay** | 1-2 seconds | Allows external systems to recover |
| **Allowed test count** | < 5% of test suite | More than 5% means systematic problem |
| **Per-test limit** | Only specific tests tagged | Not all tests in file, just flaky ones |
| **Test result reporting** | Show all 3 attempts | Transparency on failure pattern |

### 2.3 Test Files with Flaky Tests

```
app/tests/
├── test_booking_platform.py
│   ├── test_create_appointment (flaky due to timing)
│   └── test_availability_check (flaky due to concurrent requests)
├── test_search.py
│   └── test_search_with_cache (flaky due to cache timing)
└── test_api_standards_098.py
    └── (no flaky tests - all deterministic)
```

**Current Flaky Tests**:
- `test_booking_platform.py::test_create_appointment`
- `test_booking_platform.py::test_availability_check`
- `test_search.py::test_search_with_cache`

---

## 3. Configuration

### 3.1 pytest.ini Configuration

```ini
[pytest]
# Flaky test retry configuration
addopts = --reruns-delay=1
markers =
    flaky: mark test as flaky, will be retried on failure
```

### 3.2 conftest.py Configuration

```python
# app/tests/conftest.py

import pytest

def pytest_configure(config):
    """Configure pytest with flaky test markers."""
    config.addinivalue_line(
        "markers", "flaky(reruns=2): mark test as flaky with specified reruns"
    )

@pytest.fixture(scope="session")
def flaky_test_config():
    """Configuration for flaky test retry policy."""
    return {
        "max_reruns": 2,
        "reruns_delay": 1,
        "allowed_markers": {"timing", "network", "concurrency", "external_api"},
        "max_flaky_percentage": 0.05  # 5% of test suite
    }
```

---

## 4. Usage Examples

### Example 1: Network-Based Flakiness

```python
import pytest
import requests

@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_external_api_call():
    """
    Test is flaky due to intermittent network timeouts.
    
    Flakiness markers:
    - Calls external service
    - No retry logic in app
    - Timeout varies based on network
    """
    try:
        response = requests.get(
            "https://external-service/api/data",
            timeout=5
        )
        assert response.status_code == 200
    except requests.Timeout:
        # This causes intermittent failures
        pytest.fail("External API timeout")
```

### Example 2: Timing-Based Flakiness

```python
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_concurrent_booking():
    """
    Test is flaky due to race condition in concurrent requests.
    
    Why it's flaky:
    - Multiple threads access same resource
    - Test order varies in CI
    - Timing of concurrent updates non-deterministic
    """
    future_time = datetime.utcnow() + timedelta(minutes=30)
    
    # Concurrent requests might race
    assert booking_service.is_available(future_time)
```

### Example 3: Cache Timing

```python
@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_cache_expiry():
    """
    Test is flaky due to cache timing edge cases.
    
    Why it's flaky:
    - Cache expiry timing is approximate
    - Test duration varies on different CI workers
    - Sleep() doesn't guarantee exact timing
    """
    cache.set("key", "value", ttl=1)
    time.sleep(1.1)  # ~1.1 seconds but not exact
    
    # Sometimes cache still present if sleep was < 1 second
    assert cache.get("key") is None
```

---

## 5. CI Workflow Integration

### 5.1 Running Tests with Retry

```bash
# Run tests with automatic retry on failure
pytest app/tests/ \
  -v \
  --reruns=2 \
  --reruns-delay=1 \
  --tb=short
```

### 5.2 Workflow Output

CI reports all attempts:

```
test_booking_platform.py::test_create_appointment FAILED (attempt 1)
test_booking_platform.py::test_create_appointment FAILED (attempt 2)
test_booking_platform.py::test_create_appointment PASSED (attempt 3) ✓

test_search.py::test_search_with_cache PASSED (attempt 1)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests: 3 passed, 0 failed (2 with retries)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 5.3 CI Annotation

```
⚠️ Flaky Test Alert

test_booking_platform.py::test_create_appointment
  - Status: PASSED after 3 attempts
  - Pattern: Fails first 2 attempts, passes 3rd
  - Recommendation: Investigate root cause

This test failed on first attempt but passed with retry.
Consider investigating the intermittent failure.
See .propel/context/tasks/EP-TECH-001/us_101/TEST-1-FLAKY_RETRY_POLICY.md
```

---

## 6. Identifying Flaky Tests

### 6.1 Diagnostic: Running Tests Multiple Times

```bash
# Run test 5 times to check for flakiness
for i in {1..5}; do
  echo "Attempt $i"
  pytest app/tests/test_booking_platform.py::test_create_appointment -q
done
```

### 6.2 Historical Analysis

```bash
# Check recent CI runs for retry patterns
cd .propel/security/ci-logs/
grep -r "FAILED.*attempt" . | \
  awk -F: '{print $1}' | \
  sort | uniq -c | sort -rn
```

---

## 7. Root Cause Analysis

When a flaky test is identified:

| Cause | Solution | Severity |
|-------|----------|----------|
| External API timeout | Add retry logic in code, increase timeout | HIGH |
| Race condition | Add proper synchronization, use locks | HIGH |
| Test order dependency | Use isolation fixtures, setup/teardown | MEDIUM |
| Hard sleep() | Use polling/wait loops with timeout | MEDIUM |
| Flaky assertion | Use proper wait utilities | LOW |

### Example Root Cause Fix

**Before** (Flaky):
```python
def test_cache_expiry():
    cache.set("key", "value", ttl=1)
    time.sleep(1.1)  # ❌ Hard sleep
    assert cache.get("key") is None
```

**After** (Deterministic):
```python
def test_cache_expiry():
    cache.set("key", "value", ttl=1)
    
    # ✅ Poll with timeout instead of hard sleep
    start = time.time()
    while time.time() - start < 3:
        if cache.get("key") is None:
            break
        time.sleep(0.1)
    
    assert cache.get("key") is None
```

---

## 8. Flaky Test Registry

**File**: `.propel/context/tasks/EP-TECH-001/us_101/FLAKY_TEST_REGISTRY.md`

```yaml
flaky_tests:
  - test_id: test_booking_platform.py::test_create_appointment
    marker: "@pytest.mark.flaky(reruns=2, reruns_delay=1)"
    root_cause: "Concurrent database write timing"
    status: active
    first_identified: 2026-06-15
    investigations: 
      - ticket: "#1234"
        date: 2026-06-20
        note: "Identified race condition in appointment lock"
    planned_fix: "Implement distributed lock (v1.2)"
    
  - test_id: test_booking_platform.py::test_availability_check
    marker: "@pytest.mark.flaky(reruns=2, reruns_delay=2)"
    root_cause: "External availability API timeout"
    status: active
    first_identified: 2026-06-10
    investigations:
      - ticket: "#1200"
        date: 2026-06-18
        note: "API response time varies 100-2000ms"
    planned_fix: "Add circuit breaker + local cache (v1.1)"
    
  - test_id: test_search.py::test_search_with_cache
    marker: "@pytest.mark.flaky(reruns=2, reruns_delay=1)"
    root_cause: "Cache invalidation timing"
    status: active
    first_identified: 2026-06-12
    investigations:
      - ticket: "#1250"
        date: 2026-06-19
        note: "Cache TTL edge case at 1-second boundary"
    planned_fix: "Increase TTL to 2 seconds or use event-based invalidation"
```

---

## 9. Metrics & Monitoring

### Track Flaky Test Behavior

```
Week 1:
- test_create_appointment: 3 failures, 14 passes (18% fail rate)
- test_availability_check: 1 failure, 16 passes (6% fail rate)
- test_search_with_cache: 2 failures, 15 passes (12% fail rate)

Average flaky test pass rate after retries: 95%
```

### Success Criteria

- ✅ All marked flaky tests pass after retries
- ✅ < 5% of test suite marked flaky
- ✅ No new flaky tests added without investigation
- ✅ No flaky test without documented root cause

---

## 10. Policy Enforcement

### Don't Mark Flaky Tests If:

❌ Test fails deterministically (always or never)  
❌ Test depends on test execution order (fix test isolation instead)  
❌ Test relies on exact timing with hard sleep() (fix timing instead)  
❌ Test is new and hasn't been run multiple times  

### Do Mark Flaky Tests If:

✅ Test fails intermittently without code changes  
✅ Root cause identified (external dependency, timing, concurrency)  
✅ Already investigated and no quick fix available  
✅ Marked as temporary until fix deployed  

---

## 11. Quarterly Review

Every 3 months:

1. Review all active flaky test markers
2. Check if root causes have been fixed
3. Remove markers for resolved flakiness
4. Update planned fix dates
5. Report metrics to team

**Target State**:
- 0 active flaky tests in production code path
- Any remaining flaky tests have active fix tickets
- No test marked flaky for more than 2 quarters

---

## 12. Exemptions

**Rare exemptions** (require CTO approval):

1. External vendor API with > 50% downtime
   - Retry policy: 3 attempts
   - Escalation: Skip test in CI, run manually

2. Hardware/infrastructure flakiness (CI runner failure)
   - Retry policy: 2 attempts
   - Mitigation: Switch CI runners if persistent

---

**Last Updated**: 2026-06-22  
**Approved By**: QA & Dev Lead  
**Effective Date**: 2026-06-22  
**Next Review**: 2026-09-22
