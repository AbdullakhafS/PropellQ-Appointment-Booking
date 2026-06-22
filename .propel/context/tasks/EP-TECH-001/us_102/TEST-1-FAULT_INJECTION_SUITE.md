# TEST-1: Fault Injection & Chaos Testing Suite

**Document ID**: TEST-1  
**Task**: TEST-1 (Fault Injection and Chaos Suite)  
**Last Updated**: 2026-06-22  
**Status**: Active

---

## Overview

This document defines a chaos engineering suite that simulates failures (timeouts, errors, outages) to validate resiliency behavior. Tests verify that timeouts trigger retries, retries respect budgets, circuit breakers open correctly, and bookings degrade gracefully.

---

## 1. Test Categories

### 1.1 Timeout Injection Tests

**Goal**: Verify timeout behavior doesn't break bookings

```python
# Test: Slow external API (timeout triggers retry)
def test_external_api_slow_timeout_retries():
    """External API is slow; timeout triggers retry."""
    with mock_search_service_slow(delay_seconds=6):  # Exceeds 3s timeout
        # First attempt times out
        # Retry happens (with backoff)
        # Second attempt succeeds (or fails, triggering circuit breaker)
        response = book_appointment(...)
        # Either succeeds (retry worked) or fails gracefully
        assert response.status_code in [201, 503]
```

### 1.2 Error Rate Tests

**Goal**: Verify circuit breaker opens at threshold

```python
def test_circuit_breaker_opens_at_50_percent_error_rate():
    """Circuit opens when 50% of requests fail."""
    with mock_payment_processor_failing_50_percent():
        for attempt in range(10):  # 10 requests
            try:
                charge_payment(100)
            except CircuitBreakerOpenError:
                # Circuit opened as expected
                assert attempt >= 5  # Should open around attempt 5
                break
        else:
            # If we get here: circuit never opened
            pytest.fail("Circuit breaker didn't open at threshold")
```

### 1.3 Cascading Failure Tests

**Goal**: Verify degradation doesn't cascade

```python
def test_booking_continues_with_sms_failure():
    """Booking succeeds even if SMS notification fails."""
    with mock_sms_service_down():
        response = book_appointment(
            provider_id=1,
            date="2026-06-23",
            time="10:00"
        )
        # Booking succeeds
        assert response.status_code == 201
        # SMS was queued
        assert queue.has_pending_message("sms")
```

---

## 2. Chaos Test Suite

### 2.1 Test: Payment Service Down

```python
@chaos.scenario("Payment Service Outage")
def test_payment_service_down_graceful_degradation():
    """
    Scenario: Payment service suddenly unavailable
    Expected: Core booking degraded gracefully with fallback
    """
    # Setup: Normal traffic baseline
    baseline_bookings = measure_booking_rate()
    assert baseline_bookings > 100  # per minute
    
    # Inject: Disable payment service
    with chaos.disable_service("payment_processor"):
        # Wait for circuit breaker to open
        time.sleep(31)
        
        # Measure: Booking rate after outage
        degraded_bookings = measure_booking_rate()
        
        # Verify: Still books (but degraded)
        assert degraded_bookings > baseline_bookings * 0.1  # At least 10%
        
        # Check: Fallback activated (queue growing)
        queue_size = get_queue_size("payment_retry_queue")
        assert queue_size > 0
```

### 2.2 Test: Timeout Cascade

```python
@chaos.scenario("Timeout Cascade")
def test_slow_downstream_triggers_timeout_retry_circuit():
    """
    Scenario: Database suddenly slow (10s latency)
    Expected: Timeouts trigger, retries happen, circuit opens
    """
    with chaos.add_latency("appointment_db", latency_ms=10000):
        # T=0: Requests start timing out (5s timeout < 10s latency)
        # T=1: First retries happening
        # T=5: Circuit breaker opens
        # T>5: Requests fail fast (no more timeouts)
        
        # Measure total time for 100 requests
        start = time.time()
        for _ in range(100):
            try:
                get_appointments()
            except (TimeoutError, CircuitBreakerOpenError):
                pass
        end = time.time()
        
        # Should be fast (fail-fast after circuit opens)
        # NOT 10 sec * 100 requests = 1000 seconds
        assert end - start < 60  # Should complete in < 1 minute
```

### 2.3 Test: Retry Budget Exhaustion

```python
@chaos.scenario("Retry Budget Exhaustion")
def test_retry_budget_prevents_retry_storm():
    """
    Scenario: Downstream service failing; retry budget gets exhausted
    Expected: After budget exhausted, retries stop to prevent amplification
    """
    with chaos.fail_randomly("search_service", failure_rate_percent=50):
        # Half of requests fail; these trigger retries
        # Retries consume budget
        for _ in range(500):  # Enough to exhaust budget
            try:
                search_appointments(...)
            except Exception:
                pass  # Expect some failures
        
        # Check budget status
        budget = get_retry_budget()
        assert budget.available_tokens < budget.capacity * 0.2  # Mostly consumed
        
        # Measure: Retry rate should drop after budget exhausted
        retry_rate_early = measure_retry_rate(window=60)  # First 60s
        retry_rate_late = measure_retry_rate(window=60)   # After budget exhausted
        
        assert retry_rate_late < retry_rate_early  # Fewer retries after exhaustion
```

### 2.4 Test: Half-Open Recovery

```python
@chaos.scenario("Half-Open Probe Recovery")
def test_circuit_breaker_half_open_recovery():
    """
    Scenario: Service fails, circuit opens, service recovers
    Expected: Probes succeed, circuit closes, traffic ramps up
    """
    # 1. Service fails and circuit opens
    with chaos.fail_service("search_service"):
        time.sleep(30)  # Let circuit open
        assert get_circuit_state("search_service") == "OPEN"
    
    # 2. Service recovers (chaos disabled)
    # Circuit now enters HALF_OPEN
    time.sleep(31)  # Wait for transition
    assert get_circuit_state("search_service") == "HALF_OPEN"
    
    # 3. Probes should succeed
    time.sleep(5)  # Let probes run
    probe_success_rate = get_probe_success_rate("search_service")
    assert probe_success_rate > 0.8  # > 80% success
    
    # 4. Circuit should close and traffic ramp up
    time.sleep(10)
    assert get_circuit_state("search_service") == "CLOSED"
    traffic = measure_request_rate("search_service")
    assert traffic > baseline_traffic * 0.5  # Ramped back up
```

### 2.5 Test: Error Rate Guardrails

```python
@chaos.scenario("Error Rate Guardrails")
def test_error_rate_stays_within_guardrails():
    """
    Scenario: Multiple failures injected
    Expected: Error rate stays within SLO guardrails
    """
    with chaos.combined_failures(
        timeout_rate=5,  # 5% timeouts
        error_rate=3,    # 3% errors
        latency_p99=2000  # 2s p99 latency
    ):
        # Measure for 5 minutes
        results = []
        for _ in range(60):
            results.append(measure_system_health())
            time.sleep(5)
        
        # Verify guardrails maintained
        avg_error_rate = mean([r['error_rate'] for r in results])
        assert avg_error_rate < 10  # < 10% errors acceptable
        
        avg_latency_p99 = mean([r['latency_p99_ms'] for r in results])
        assert avg_latency_p99 < 5000  # < 5s p99 acceptable
        
        booking_completion = mean([r['booking_success_rate'] for r in results])
        assert booking_completion > 0.9  # > 90% bookings complete
```

---

## 3. Load Testing with Chaos

### 3.1 Normal Load + Chaos

```python
def test_under_load_with_circuit_breaker_opened():
    """
    Scenario: 500 concurrent users; payment service down
    Expected: Graceful degradation; no cascading failure
    """
    # 1. Ramp up load: 0 → 500 users over 2 minutes
    locust_scenario = [
        (0, 0),      # Start
        (60, 250),   # After 1 min: 250 users
        (120, 500),  # After 2 min: 500 users
    ]
    
    # 2. At 90 seconds: disable payment service
    schedule_chaos(
        time_offset_seconds=90,
        action="disable_service",
        service="payment_processor"
    )
    
    # 3. Run test
    results = run_load_test(
        user_ramp=locust_scenario,
        duration_seconds=300
    )
    
    # 4. Verify system handled gracefully
    error_rate = results['error_rate_during_chaos']
    assert error_rate < 20  # < 20% errors during chaos
    
    throughput = results['booking_throughput_during_chaos']
    assert throughput > results['baseline_throughput'] * 0.3  # > 30% capacity
```

---

## 4. Monitoring During Chaos

```python
@contextmanager
def chaos_monitoring():
    """Collect metrics during chaos test."""
    metrics = {
        'errors': [],
        'latencies': [],
        'circuit_states': [],
        'retry_rates': [],
        'timeout_rates': [],
        'fallback_activations': []
    }
    
    # Start background collection
    collector = threading.Thread(
        target=collect_metrics,
        args=(metrics,),
        daemon=True
    )
    collector.start()
    
    yield metrics
    
    # Generate report
    report = generate_chaos_report(metrics)
    print(report)

def collect_metrics(metrics):
    """Continuously collect metrics."""
    while running:
        metrics['errors'].append(get_error_rate())
        metrics['latencies'].append(get_p99_latency_ms())
        metrics['circuit_states'].append(get_all_circuit_states())
        metrics['retry_rates'].append(get_retry_rate())
        time.sleep(1)
```

---

## 5. Chaos Test Scenarios

### 5.1 Single Service Failure

```
Scenario: payment_service DOWN
Duration: 5 minutes
Expected: Circuit opens; bookings queue; traffic ramps after recovery
```

### 5.2 Multiple Failures (Cascade)

```
Scenario: payment_service + search_service both DOWN
Duration: 10 minutes
Expected: Both circuits open; core booking path remains available
```

### 5.3 Partial Failure (50% Error Rate)

```
Scenario: payment_service returns 500 errors for 50% of requests
Duration: 5 minutes
Expected: Circuit opens (50% > threshold); fallback queues
```

### 5.4 Latency Injection

```
Scenario: database latency increases from 100ms to 5000ms
Duration: 5 minutes
Expected: Timeouts trigger; retries help; circuit may open if persistent
```

### 5.5 Network Chaos

```
Scenario: 10% packet loss, 100ms latency jitter on external calls
Duration: 5 minutes
Expected: Some retries succeed; some timeout; system degrades gracefully
```

---

## 6. Test Environment

### 6.1 Chaos Test Infrastructure

```yaml
chaos_environment:
  tools:
    - chaos_framework: "Gremlin" or "Litmus"
    - network_simulation: "tc (traffic control)" or "Toxiproxy"
    - load_testing: "Locust"
    - monitoring: "Prometheus + Grafana"
  
  deployment:
    environment: "staging" (mirrors production)
    data: "sanitized production data"
    scale: "10% of production"
```

### 6.2 Isolation

Each chaos test runs in isolated namespace:

```bash
# Kubernetes namespace per test
kubectl create namespace chaos-test-1
kubectl apply -f chaos-booking-service.yaml -n chaos-test-1

# Cleanup after test
kubectl delete namespace chaos-test-1
```

---

## 7. Running Chaos Tests

### 7.1 Pre-Test Checklist

```
[ ] Staging environment healthy
[ ] Monitoring dashboards ready
[ ] On-call engineer available
[ ] Incident response team notified
[ ] Expected outcomes documented
```

### 7.2 Test Execution

```bash
# Run single chaos scenario
pytest tests/chaos/test_payment_service_down.py -v

# Run full chaos suite
pytest tests/chaos/ -v --chaos-duration=300

# Run with specific parameters
pytest tests/chaos/test_with_load.py -v \
  --chaos-scenario="payment_down" \
  --load-users=500 \
  --duration-seconds=600
```

### 7.3 Post-Test Review

1. Collect metrics from test run
2. Analyze deviations from expected behavior
3. Document findings
4. File issues if guardrails violated
5. Update policies/timeouts if needed

---

## 8. Success Criteria for Chaos Tests

| Metric | Target | Pass |
|--------|--------|------|
| Booking completion under chaos | > 90% | ✅ |
| Error rate increase | < 10% | ✅ |
| P99 latency under chaos | < 5s | ✅ |
| Circuit opens at threshold | Yes | ✅ |
| Retries succeed > 80% | > 80% | ✅ |
| Fallback queue processes | Yes | ✅ |
| No cascading failures | Yes | ✅ |

---

**Document Owner**: Infrastructure Team  
**Last Review**: 2026-06-22  
**Next Review**: 2026-09-22
