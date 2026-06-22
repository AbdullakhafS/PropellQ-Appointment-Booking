# RES-3: Circuit Breaker Open-State Policy

**Document ID**: RES-3  
**Acceptance Criteria**: AC-3  
**Last Updated**: 2026-06-22  
**Status**: Active

---

## Overview

Circuit breakers prevent cascading failures by stopping requests to failing downstream services. When a service experiences repeated failures, the circuit "opens" and requests fail immediately without attempting the call.

---

## 1. Circuit Breaker States

```
CLOSED (Normal)
  ↓ (failure threshold exceeded)
OPEN (Failing - reject all requests)
  ↓ (after open duration)
HALF_OPEN (Testing recovery)
  ↓ (probe succeeds)
CLOSED (Back to normal)
        ↓ (probe fails)
      OPEN (Back to failing)
```

### 1.1 CLOSED State
- **Description**: Service is healthy; requests pass through
- **Behavior**: Monitor success/failure rate
- **Transition**: Open if failure rate exceeds threshold
- **Metrics**: Count successes, failures, timeouts

### 1.2 OPEN State
- **Description**: Service is failing; reject all requests
- **Behavior**: Return error immediately (fail-fast)
- **Duration**: Stays open for configured duration (e.g., 30 seconds)
- **Purpose**: Prevent cascading failures; give downstream service time to recover
- **Alert**: Page on-call; investigate

### 1.3 HALF_OPEN State
- **Description**: Testing if service has recovered
- **Behavior**: Allow limited probe requests; observe results
- **Transition**: Close if probe succeeds; reopen if probe fails
- **Duration**: Short (5-10 seconds); allow 1-2 probe requests

---

## 2. Failure Thresholds

### 2.1 Threshold Configuration

```yaml
circuit_breaker:
  failure_threshold:
    error_rate: 50           # % of requests returning 5xx
    error_count: 5           # Absolute count of consecutive errors
    timeout_rate: 30         # % of requests timing out
    window_seconds: 10       # Time window for measurement
  
  half_open_config:
    probe_timeout_seconds: 5
    max_probe_requests: 2    # Allow 2 probes
    probe_success_threshold: 1  # Need 1 success to close
  
  open_duration_seconds: 30  # How long to stay open
  max_open_duration_seconds: 300  # Don't stay open > 5 min
```

### 2.2 Failure Types

A failure is counted as:

```
- Timeout (no response within timeout window)
- 503 Service Unavailable
- 502 Bad Gateway
- 504 Gateway Timeout
- 500 Internal Server Error (sometimes)
- Connection refused
- Connection timeout
```

**NOT counted as failure**:
```
- 429 Too Many Requests (rate limited; not service failure)
- 401/403 Authentication error (not service failure)
- 404 Not Found (not service failure)
- 400 Bad Request (client error; not service failure)
```

### 2.3 Threshold Examples

**API Gateway** (high threshold):
```yaml
error_rate: 50%           # Higher tolerance
error_count: 10
window_seconds: 30
open_duration_seconds: 60
```

**Payment Service** (moderate threshold):
```yaml
error_rate: 25%           # Medium tolerance
error_count: 5
window_seconds: 10
open_duration_seconds: 30
```

**Search Service** (low threshold):
```yaml
error_rate: 10%           # Low tolerance (non-critical)
error_count: 5
window_seconds: 30
open_duration_seconds: 120
```

---

## 3. Pressure Relief Behavior

### 3.1 Fast Fail

When circuit is OPEN, requests fail immediately without overhead:

```python
if circuit_breaker.state == "OPEN":
    raise CircuitBreakerOpenError(
        service=service_name,
        estimated_recovery_time=open_since + open_duration
    )
# Don't waste time on network call; fail fast
```

### 3.2 Load Shedding

Prevent further load on failing service:

```
Normal traffic: 1000 req/sec
Service starts failing: Circuit opens
Rejected traffic: 1000 req/sec (not sent to service)
Service gets: 0 req/sec → time to recover
```

### 3.3 Cascading Prevention

Stop cascade by blocking early:

```
Service A → Service B → Service C (failing)
                ↑
         Circuit opens when B's requests to C fail
         B stops sending to C
         B returns error to A
         A's circuit doesn't open (doesn't see C's failure)
```

---

## 4. Probing & Recovery

### 4.1 Half-Open Probing Strategy

When transitioning to HALF_OPEN:

1. **Send probe request** to failing service
2. **Wait for response** (with timeout)
3. **Count as success if**: Response status 2xx-3xx
4. **Count as failure if**: 5xx, timeout, error
5. **Decision**:
   - Success: Close circuit (resume normal traffic)
   - Failure: Reopen circuit (try again later)

### 4.2 Probe Configuration

```yaml
probe_strategy: "health_check"

probe_endpoints:
  - service: "booking_service"
    probe_endpoint: "GET /health"
    probe_interval_seconds: 30
    max_probes_per_minute: 2
  
  - service: "payment_service"
    probe_endpoint: "GET /status"
    probe_interval_seconds: 60
    max_probes_per_minute: 1
```

### 4.3 Gradual Recovery

Don't immediately restore full traffic after recovery:

```python
# Circuit just closed after recovery
# Don't send all traffic immediately; ramp up
current_traffic = 0
traffic_ramp_up_seconds = 60

while current_traffic < total_traffic:
    time.sleep(10)
    current_traffic += total_traffic / 6  # Increase by 1/6 every 10s
    route_traffic(current_traffic)
```

---

## 5. Circuit Breaker by Service

### 5.1 Booking Service Dependencies

```yaml
circuit_breakers:
  - service: "appointment_db"
    state: "CLOSED"
    failure_threshold:
      error_rate: 20%
      error_count: 5
      window_seconds: 30
    open_duration_seconds: 60
    half_open_probe: "SELECT 1"  # SQL health check
  
  - service: "availability_search"
    state: "CLOSED"
    failure_threshold:
      error_rate: 30%
      error_count: 3
      window_seconds: 10
    open_duration_seconds: 30
    half_open_probe: "GET /health"
  
  - service: "payment_processor"
    state: "CLOSED"
    failure_threshold:
      error_rate: 10%           # Strict
      error_count: 2            # Very strict
      window_seconds: 60
    open_duration_seconds: 120  # Long recovery
    half_open_probe: "GET /status"
```

### 5.2 External Service Dependencies

```yaml
  - service: "stripe_payments"
    state: "CLOSED"
    failure_threshold:
      error_rate: 25%
      error_count: 5
      window_seconds: 30
    open_duration_seconds: 120
    fallback_behavior: "queue_for_retry"
  
  - service: "twilio_sms"
    state: "CLOSED"
    failure_threshold:
      error_rate: 40%
      error_count: 10
      window_seconds: 60
    open_duration_seconds: 300
    fallback_behavior: "queue_and_retry_later"
```

---

## 6. Observability & Alerting

### 6.1 Metrics to Track

```
- Circuit state (CLOSED, OPEN, HALF_OPEN)
- Transition count (how often circuit opens)
- Time in OPEN state
- Failure rate when CLOSED
- Probe success rate in HALF_OPEN
```

### 6.2 Alerts

**Alert: Circuit opened**
- Threshold: Immediate when state = OPEN
- Severity: WARNING
- Action: Investigate downstream service; check logs

**Alert: Circuit frequently opens**
- Threshold: > 3 times per 5 minutes
- Severity: CRITICAL
- Action: Page on-call; investigate root cause

**Alert: Circuit stuck in HALF_OPEN**
- Threshold: HALF_OPEN for > 10 minutes
- Severity: WARNING
- Action: Service not recovering; may need manual intervention

---

## 7. Manual Intervention

### 7.1 Force Circuit State

In emergencies, operators can manually control circuit state:

```bash
# Force circuit to CLOSED (emergency restore)
curl -X POST /admin/circuit-breaker/booking_service/close
# Risk: May send traffic to still-failing service

# Force circuit to OPEN (emergency stop)
curl -X POST /admin/circuit-breaker/booking_service/open
# Risk: Blocks all traffic; should be temporary

# Reset circuit to initial state
curl -X POST /admin/circuit-breaker/booking_service/reset
```

### 7.2 Approval & Audit

All manual interventions require:
- Ticket number (INC-XXXX)
- Approver (on-call engineer)
- Reason documented
- Duration specified (auto-revert after X minutes)

---

## 8. Fallback Behavior During OPEN

### 8.1 Fallback Responses

When circuit is OPEN, what to return?

```python
if circuit_breaker.state == "OPEN":
    return {
        "error": "Service temporarily unavailable",
        "fallback": True,
        "retry_after_seconds": 30,
        "error_code": "SERVICE_UNAVAILABLE"
    }
```

### 8.2 Fallback Cache

For GET requests, return stale cached data if available:

```python
if circuit_breaker.state == "OPEN":
    if cache.has_recent_value(key):
        return cache.get(key)  # Return last known good value
    else:
        raise ServiceUnavailable()
```

### 8.3 Fallback Queue

For write requests, queue for later retry:

```python
if circuit_breaker.state == "OPEN":
    if is_idempotent_request(request):
        queue.enqueue(request)  # Queue for later
        return {"status": "queued", "queue_id": "..."}
    else:
        raise ServiceUnavailable()
```

---

## 9. Testing Circuit Breaker

### 9.1 Unit Tests

```python
def test_circuit_opens_after_failure_threshold():
    """Verify circuit opens when failure rate exceeded."""
    cb = CircuitBreaker(failure_threshold_errors=5)
    
    # Simulate 5 failures
    for _ in range(5):
        cb.record_failure()
    
    assert cb.state == "OPEN"

def test_circuit_closes_after_probe_succeeds():
    """Verify circuit closes when probe succeeds."""
    cb = CircuitBreaker(open_duration_seconds=0)  # Immediate half-open
    
    # Open circuit
    for _ in range(5):
        cb.record_failure()
    assert cb.state == "OPEN"
    
    # Probe succeeds
    cb.record_probe_success()
    assert cb.state == "CLOSED"
```

### 9.2 Integration Tests

```python
def test_payment_circuit_breaker_integration():
    """Test payment service circuit breaker with real failures."""
    with mock_payment_service_down():
        # Circuit opens after threshold
        for _ in range(5):
            with pytest.raises(CircuitBreakerOpenError):
                charge_payment(100)
        
        # Later: service recovers
        # Circuit probes and eventually closes
```

---

## 10. Related Documents

- RES-1: Timeout values (trigger for circuit breaker)
- RES-2: Retry strategy (coordinates with circuit breaker)
- RES-4: Half-open recovery (part of circuit breaker lifecycle)
- FALL-1: Fallback behavior (activated when circuit open)
- OBS-1: Telemetry (monitors circuit state)

---

**Document Owner**: Infrastructure Team  
**Last Review**: 2026-06-22  
**Next Review**: 2026-09-22
