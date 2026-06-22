# TASK-102 Quality Assurance - Test Validation Plan

**Document ID**: QA-TEST_VALIDATION_PLAN  
**Task**: QA-1 through QA-6 (Quality Assurance Tests)  
**Last Updated**: 2026-06-22  
**Status**: Active

---

## Overview

This document outlines 17 test cases validating all 6 acceptance criteria for TASK-102. Tests organized by QA goal (QA-1 through QA-6), with detailed setup, execution, and verification steps.

---

## Test Organization

| QA ID | Acceptance Criteria | Feature | Test Count |
|-------|-------------------|---------|-----------|
| QA-1 | AC-1 | Timeout defaults apply | 3 tests |
| QA-2 | AC-2 | Retry exponential backoff + budget | 3 tests |
| QA-3 | AC-3 | Circuit breaker open behavior | 3 tests |
| QA-4 | AC-4 | Half-open probe recovery | 2 tests |
| QA-5 | AC-5 | Booking degradation with fallback | 3 tests |
| QA-6 | AC-6 | Error/latency guardrails under chaos | 3 tests |
| **Total** | | | **17 tests** |

---

## QA-1: Timeout Defaults Apply (AC-1)

### UT-102-001: Default timeout on unconfigured call

**Objective**: Verify timeout applies to calls without explicit timeout parameter

**Setup**:
```python
# Create HTTP client without explicit timeout
client = requests.Session()

# Call external endpoint
# (No timeout parameter specified)
```

**Expected**:
- [ ] Default timeout from RES-1 applied (e.g., 3s for external calls)
- [ ] Call times out at 3s if downstream slow
- [ ] No infinite hang

**Verification**:
```python
def test_default_timeout_applied():
    with mock_slow_endpoint(delay_ms=5000):
        with pytest.raises(requests.exceptions.Timeout):
            response = requests.get(url)  # No timeout param
```

---

### UT-102-002: Timeout override respected

**Objective**: Verify explicit timeout parameter overrides default

**Setup**:
```python
# Override default with explicit timeout
response = requests.get(url, timeout=10.0)  # 10 second override
```

**Expected**:
- [ ] Explicit timeout (10s) used instead of default (3s)
- [ ] Request succeeds if completes within 10s
- [ ] Request times out after 10s (not 3s)

**Verification**:
```python
def test_explicit_timeout_override():
    with mock_slow_endpoint(delay_ms=5000):
        # Should NOT timeout (5s < 10s override)
        response = requests.get(url, timeout=10.0)
        assert response.status_code == 200
```

---

### UT-102-003: Timeout applies by call type

**Objective**: Verify different timeouts for different call types

**Setup**:
```python
# Test different call types
timeout_db = call_database()  # Database call
timeout_external = call_api()  # External API
timeout_cache = get_cache()    # Cache lookup
```

**Expected**:
- [ ] Database calls: timeout = 5s (from RES-1)
- [ ] External API calls: timeout = 8-10s
- [ ] Cache lookups: timeout = 0.1-0.5s
- [ ] Each uses appropriate default

**Verification**:
```python
def test_timeout_by_call_type():
    with mock_slow_calls():
        # DB call should timeout at 5s
        with pytest.raises(Timeout):
            call_database()
        
        # Cache should timeout at 100ms
        with pytest.raises(Timeout):
            get_cache()  # 200ms delay > 100ms timeout
```

---

## QA-2: Retry Exponential Backoff + Budget (AC-2)

### UT-102-004: Exponential backoff increases delays

**Objective**: Verify retry delays increase exponentially (not linearly)

**Setup**:
```python
# Simulate 3 retries with delays
attempt_1: delay = 100ms + jitter
attempt_2: delay = 200ms + jitter
attempt_3: delay = 400ms + jitter
```

**Expected**:
- [ ] Attempt 1: ~100ms
- [ ] Attempt 2: ~200ms (2x)
- [ ] Attempt 3: ~400ms (4x)
- [ ] Total backoff: ~700ms before all attempts complete

**Verification**:
```python
def test_exponential_backoff():
    delays = []
    with mock_failing_endpoint(max_attempts=3):
        start = time.time()
        try:
            request_with_retries()
        except:
            pass
        elapsed = time.time() - start
    
    # Should take ~700ms backoff + request times
    assert elapsed > 0.7  # At least 700ms of backoff
```

---

### UT-102-005: Jitter prevents thundering herd

**Objective**: Verify jitter spreads retries to avoid synchronized load spike

**Setup**:
```python
# Send 100 requests; all fail and retry simultaneously
# Without jitter: all 100 retry at same time (thundering herd)
# With jitter: retries spread out
```

**Expected**:
- [ ] With jitter: retries distributed across time window
- [ ] Load spike smoother (not all-at-once spike)
- [ ] No thundering herd behavior

**Verification**:
```python
def test_jitter_spreads_retries():
    retry_times = []
    
    with mock_failing_endpoint():
        # Send 100 concurrent requests
        for i in range(100):
            start = time.time()
            try:
                request_with_retries()
            except:
                pass
            retry_times.append(time.time() - start)
    
    # Check distribution of retry times
    variance = numpy.var(retry_times)
    assert variance > 0.01  # Should be spread out (not all same)
```

---

### UT-102-006: Retry budget exhaustion stops retries

**Objective**: Verify retry budget prevents retry amplification

**Setup**:
```python
# Exhaust retry budget
# Send many requests; many fail and retry
# After budget exhausted: no more retries
```

**Expected**:
- [ ] Initially: Retries happen freely
- [ ] After budget exhausted: Retries rejected
- [ ] Error message: "RetryBudgetExhausted"

**Verification**:
```python
def test_retry_budget_exhaustion():
    with mock_failing_endpoint(failure_rate=50):
        retry_count_early = 0
        retry_count_after_exhaustion = 0
        
        # Phase 1: Normal retries
        for _ in range(200):
            try:
                request_with_retries()
            except RetryBudgetExhausted:
                break
            except:
                retry_count_early += 1
        
        # Check budget is exhausted
        assert budget.available_tokens < 100
        
        # Phase 2: Retries should be rejected
        for _ in range(100):
            try:
                request_with_retries()
            except RetryBudgetExhausted:
                retry_count_after_exhaustion += 1
        
        assert retry_count_after_exhaustion > 50  # Most rejected
```

---

### UT-102-007: Non-idempotent endpoints don't retry

**Objective**: Verify payment/delete endpoints are in blocklist (never retried)

**Setup**:
```python
# Try to call payment endpoint with retries
POST /payments/charge (in never_retry blocklist)
```

**Expected**:
- [ ] First attempt fails
- [ ] No retry happens
- [ ] Error returned to client (not retried)

**Verification**:
```python
def test_non_idempotent_endpoints_blocked():
    attempt_count = 0
    
    with mock_payment_failing():
        try:
            charge_payment(100)  # Should NOT retry
        except:
            pass
    
    # Check only 1 attempt was made (no retries)
    call_count = get_downstream_call_count()
    assert call_count == 1  # Only one attempt, no retries
```

---

## QA-3: Circuit Breaker Open Behavior (AC-3)

### UT-102-008: Circuit opens at failure threshold

**Objective**: Verify circuit opens when failure rate exceeds threshold

**Setup**:
```python
# Downstream service returns 500 errors
# Failure rate: 60% (exceeds 50% threshold from RES-3)
```

**Expected**:
- [ ] After N failures (threshold reached)
- [ ] Circuit state transitions: CLOSED → OPEN
- [ ] Subsequent requests fail immediately (fast-fail)

**Verification**:
```python
def test_circuit_opens_at_threshold():
    with mock_service_failing_60_percent():
        errors_before_open = 0
        errors_after_open = 0
        
        # Send requests until circuit opens
        for attempt in range(20):
            try:
                response = call_downstream()
                if response.status_code >= 500:
                    errors_before_open += 1
            except CircuitBreakerOpenError:
                # Circuit opened; subsequent errors fast-fail
                errors_after_open += attempt - errors_before_open
                break
        
        # Should open within ~10 attempts
        assert errors_before_open < 10
        assert circuit.state == "OPEN"
```

---

### UT-102-009: Open circuit fails fast

**Objective**: Verify circuit-open requests fail immediately (no network call)

**Setup**:
```python
# Circuit is OPEN
# Make request; should fail immediately without attempting call
```

**Expected**:
- [ ] Request fails immediately (< 10ms)
- [ ] No downstream call made
- [ ] Error: CircuitBreakerOpenError

**Verification**:
```python
def test_circuit_open_fails_fast():
    circuit.force_open()  # Manually open
    
    start = time.time()
    try:
        call_downstream()
        pytest.fail("Should have raised CircuitBreakerOpenError")
    except CircuitBreakerOpenError:
        elapsed = time.time() - start
        # Should be very fast (< 50ms)
        assert elapsed < 0.05
```

---

### UT-102-010: Failure count/rate tracked

**Objective**: Verify failure metrics tracked for circuit decision

**Setup**:
```python
# Send requests; some fail
# Track which ones count toward circuit opening
```

**Expected**:
- [ ] 5xx errors count as failures
- [ ] Timeouts count as failures
- [ ] 4xx errors don't count (not service failure)
- [ ] Metrics shown in dashboard

**Verification**:
```python
def test_failure_tracking():
    with mock_mixed_responses():
        # 50% 500 errors, 50% 200 success
        for _ in range(100):
            try:
                call_downstream()
            except:
                pass
        
        # Check metrics
        failure_count = circuit.failure_count
        assert failure_count == 50  # Only 5xx errors count
        
        # 4xx errors should not count
        assert circuit.client_error_count == 0
```

---

## QA-4: Half-Open Probe Recovery (AC-4)

### UT-102-011: Probe validates recovery

**Objective**: Verify health check probe confirms service recovery

**Setup**:
```python
# Circuit is OPEN
# Service recovers
# Probe sent to confirm recovery
```

**Expected**:
- [ ] Probe request sent (e.g., GET /health)
- [ ] Service responds OK (200)
- [ ] Probe marked success
- [ ] Circuit transitions: OPEN → HALF_OPEN → CLOSED

**Verification**:
```python
def test_probe_validates_recovery():
    # Force open circuit
    circuit.force_open()
    assert circuit.state == "OPEN"
    
    # Wait for auto-transition to HALF_OPEN
    time.sleep(31)  # Wait for open_duration
    
    # In HALF_OPEN: probe runs
    # Service is healthy, probe succeeds
    probe_result = circuit.last_probe_result
    assert probe_result == "success"
    
    # Circuit should now be CLOSED
    time.sleep(5)  # Wait for close decision
    assert circuit.state == "CLOSED"
```

---

### UT-102-012: Traffic ramps up gradually

**Objective**: Verify full traffic doesn't immediately resume

**Setup**:
```python
# Circuit just closed after recovery
# Traffic should ramp up gradually (not all-at-once)
```

**Expected**:
- [ ] T=0: Circuit closes; traffic at 0%
- [ ] T=10: Traffic at 16% (1/6 of full)
- [ ] T=20: Traffic at 33% (2/6 of full)
- [ ] T=60: Traffic at 100% (full)

**Verification**:
```python
def test_traffic_ramps_up():
    circuit.force_close_with_ramp()
    
    measurements = []
    for i in range(12):  # Measure every 5 seconds for 60s
        traffic_percent = get_traffic_to_service()
        measurements.append(traffic_percent)
        time.sleep(5)
    
    # Traffic should increase gradually
    assert measurements[0] < 20   # 0-5s: low traffic
    assert measurements[6] > 80   # 30-35s: most traffic
    assert measurements[11] == 100  # 55-60s: full traffic
```

---

## QA-5: Booking Degradation with Fallback (AC-5)

### UT-102-013: Core booking succeeds with SMS failure

**Objective**: Verify booking completes even if non-critical SMS fails

**Setup**:
```python
# SMS notification service is down
# User requests booking
```

**Expected**:
- [ ] Booking created successfully (201)
- [ ] SMS not sent immediately
- [ ] SMS queued for async retry

**Verification**:
```python
def test_booking_succeeds_sms_fails():
    with mock_sms_service_down():
        response = client.post("/bookings", json={
            "provider_id": 1,
            "date": "2026-06-23",
            "time": "10:00"
        })
        
        # Booking succeeds
        assert response.status_code == 201
        booking_id = response.json()["id"]
        
        # SMS was queued
        pending = queue.get_pending(f"sms:{booking_id}")
        assert pending is not None
```

---

### UT-102-014: Recommendations fallback to empty

**Objective**: Verify recommendations return empty if service down

**Setup**:
```python
# Recommendation engine is down
# User views recommendations after booking
```

**Expected**:
- [ ] Returns empty list (not error)
- [ ] Booking doesn't fail
- [ ] User sees "No recommendations" instead of error

**Verification**:
```python
def test_recommendations_fallback_empty():
    with mock_recommendations_down():
        response = client.get("/bookings/123/recommendations")
        
        # Returns 200 with empty list
        assert response.status_code == 200
        assert response.json() == []
```

---

### UT-102-015: Async queue processes backlog

**Objective**: Verify queued SMS messages are eventually sent

**Setup**:
```python
# SMS service down (messages queued)
# SMS service recovers
# Backlog should be processed
```

**Expected**:
- [ ] Messages stay in queue while service down
- [ ] Service recovers
- [ ] Queue processor resumes
- [ ] Messages sent within 1 hour

**Verification**:
```python
def test_queue_processes_backlog():
    # Phase 1: Service down; queue up messages
    with mock_sms_service_down():
        for i in range(10):
            book_appointment()  # Each queues SMS
    
    queue_size_while_down = queue.size()
    assert queue_size_while_down == 10
    
    # Phase 2: Service recovers
    time.sleep(60)  # Wait for processing
    
    # Queue should be draining
    queue_size_after_recovery = queue.size()
    assert queue_size_after_recovery < queue_size_while_down
    
    # Most messages should be sent
    time.sleep(300)  # Wait 5 min more
    assert queue.size() == 0  # All processed
```

---

## QA-6: Error/Latency Guardrails Under Chaos (AC-6)

### UT-102-016: Error rate stays below 10% under chaos

**Objective**: Verify system keeps errors < 10% even under failures

**Setup**:
```python
# Inject chaos: 20% of external calls fail
# Send 1000 booking requests
```

**Expected**:
- [ ] Total error rate < 10%
- [ ] Most bookings succeed (retries working)
- [ ] Circuit breaker prevents cascading

**Verification**:
```python
def test_error_rate_guardrail_under_chaos():
    with chaos.inject_failure_rate(20, endpoint="external_api"):
        results = []
        for _ in range(1000):
            try:
                response = book_appointment(...)
                if response.status_code in [200, 201]:
                    results.append("success")
                else:
                    results.append("error")
            except Exception:
                results.append("error")
        
        error_count = results.count("error")
        error_rate = error_count / len(results)
        
        # Should stay below 10% error rate
        assert error_rate < 0.10
```

---

### UT-102-017: P99 latency stays below 5 seconds

**Objective**: Verify latency doesn't spike above guardrail under chaos

**Setup**:
```python
# Inject latency: 50% of calls have 2s added delay
# Measure p99 latency
```

**Expected**:
- [ ] P99 latency < 5 seconds
- [ ] Timeouts prevent requests hanging forever
- [ ] Retries don't amplify latency

**Verification**:
```python
def test_latency_guardrail_under_chaos():
    latencies = []
    
    with chaos.inject_latency(delay_ms=2000, rate_percent=50):
        for _ in range(1000):
            start = time.time()
            try:
                book_appointment(...)
            except:
                pass
            elapsed = (time.time() - start) * 1000  # ms
            latencies.append(elapsed)
    
    # Calculate p99
    latencies.sort()
    p99_index = int(len(latencies) * 0.99)
    p99_latency = latencies[p99_index]
    
    # Should stay below 5 seconds
    assert p99_latency < 5000  # 5 seconds in ms
```

---

## Test Execution Plan

### Phase 1: Unit Tests (Week 1)

```
Monday: UT-102-001 through UT-102-007 (Timeout & Retry)
Tuesday: UT-102-008 through UT-102-012 (Circuit Breaker)
Wednesday: UT-102-013 through UT-102-015 (Fallback)
```

### Phase 2: Integration Tests (Week 2)

```
Thursday: UT-102-016 through UT-102-017 (Guardrails)
Friday: Full integration test; all components together
```

### Phase 3: Chaos Tests (Week 3)

```
Monday-Friday: Run chaos scenarios from TEST-1
  - Payment service down
  - Timeout cascade
  - Retry budget exhaustion
  - Half-open recovery
  - Error rate guardrails
```

---

## Acceptance Criteria Coverage Matrix

| AC | QA | Tests | Coverage |
|----|-----|-------|----------|
| AC-1: Timeout defaults apply | QA-1 | UT-001-003 | 3 tests ✅ |
| AC-2: Retry exponential backoff + budget | QA-2 | UT-004-007 | 4 tests ✅ |
| AC-3: Circuit breaker open behavior | QA-3 | UT-008-010 | 3 tests ✅ |
| AC-4: Half-open probe recovery | QA-4 | UT-011-012 | 2 tests ✅ |
| AC-5: Booking degradation with fallback | QA-5 | UT-013-015 | 3 tests ✅ |
| AC-6: Error/latency guardrails | QA-6 | UT-016-017 | 2 tests ✅ |

**Total**: 17 test cases covering all 6 acceptance criteria

---

## Success Criteria

✅ All 17 tests pass  
✅ Error rate stays < 10% under chaos  
✅ P99 latency stays < 5 seconds  
✅ Bookings complete with non-critical failures  
✅ No cascading failures  
✅ Circuit breaker operates as designed  

---

**Last Updated**: 2026-06-22  
**Test Maintainer**: QA Lead  
**Next Review**: 2026-09-22
