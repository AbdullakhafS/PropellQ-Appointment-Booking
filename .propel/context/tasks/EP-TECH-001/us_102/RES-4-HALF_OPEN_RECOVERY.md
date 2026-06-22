# RES-4: Half-Open Recovery Policy

**Document ID**: RES-4  
**Acceptance Criteria**: AC-4  
**Last Updated**: 2026-06-22  
**Status**: Active

---

## Overview

Half-open state enables automatic recovery detection. When a circuit breaker transitions to half-open, controlled probe requests validate whether the failing service has recovered before resuming full traffic.

---

## 1. Half-Open Lifecycle

```
Service failing → Circuit OPEN
    ↓ (open_duration elapses, e.g., 30s)
Transition to HALF_OPEN
    ↓
Send probe request
    ↓
Probe succeeds? ──YES──→ CLOSED (resume full traffic)
    │
    NO
    ↓
Reopen (try again after delay)
```

---

## 2. Probe Configuration

### 2.1 Probe Endpoints

Each service defines a health check probe endpoint:

```yaml
probe_config:
  - service: "booking_service"
    endpoint: "GET /health"
    timeout_ms: 2000
    expected_status: 200
    expected_response: '{"status": "healthy"}'
  
  - service: "payment_processor"
    endpoint: "GET /status"
    timeout_ms: 3000
    expected_status: 200
  
  - service: "search_service"
    endpoint: "GET /ping"
    timeout_ms: 1000
    expected_status: 200
```

### 2.2 Probe Execution

```python
def probe_service(service_name: str) -> bool:
    """
    Probe the service to check if it's recovered.
    Returns True if service is healthy; False otherwise.
    """
    config = PROBE_CONFIG[service_name]
    
    try:
        response = requests.get(
            f"{service_url}{config['endpoint']}",
            timeout=config['timeout_ms'] / 1000
        )
        
        # Check status code
        if response.status_code != config['expected_status']:
            return False
        
        # Check response content if specified
        if 'expected_response' in config:
            if config['expected_response'] not in response.text:
                return False
        
        return True
    
    except (TimeoutError, ConnectionError):
        return False
```

---

## 3. Probe Cadence

### 3.1 Probe Timing

```yaml
probe_timing:
  initial_probe_delay_seconds: 30  # Wait 30s after circuit opens before first probe
  probe_interval_seconds: 60       # Try probe every 60s while HALF_OPEN
  max_probe_attempts: 5            # Try up to 5 times before giving up
  probe_success_threshold: 1       # Need 1 success to close circuit
```

### 3.2 Probe Scheduling

```
T=0s   Circuit opens (service failed)
T=30s  First probe (transition to HALF_OPEN)
T=31s  If fails: reopen; retry at T=91s
T=91s  Second probe attempt
T=92s  If succeeds: close circuit; resume full traffic
       If fails: reopen; retry at T=152s
```

### 3.3 Max Probe Duration

```
If probing for > 5 minutes without success:
  - Circuit remains open
  - Alert: "Service not recovering"
  - Page on-call engineer
  - Manual intervention may be needed
```

---

## 4. Transitional Behavior

### 4.1 Limiting Probe Requests

Don't send too many probe requests to struggling service:

```yaml
probe_limits:
  max_probes_per_minute: 1        # Only 1 probe per minute
  max_probes_per_hour: 10         # Max 10 probes per hour
  probe_success_rate_threshold: 50  # Need >50% success to close
```

### 4.2 Exponential Backoff for Probes

Probes themselves use backoff:

```python
probe_attempt = 0
while probe_attempt < MAX_PROBE_ATTEMPTS:
    if should_probe():  # Rate limited
        success = probe_service()
        if success:
            close_circuit()
            break
        else:
            probe_attempt += 1
            wait_seconds = min(300, 30 * (2 ** probe_attempt))
            time.sleep(wait_seconds)
```

---

## 5. Traffic Ramping During Recovery

### 5.1 Gradual Traffic Restoration

When circuit closes after recovery, don't send all traffic immediately:

```python
def ramp_up_traffic_after_recovery(service_name: str):
    """Gradually restore traffic to recovered service."""
    total_traffic = get_current_traffic_level(service_name)
    current_traffic = 0
    ramp_up_duration_seconds = 60
    steps = 6
    
    while current_traffic < total_traffic:
        current_traffic += total_traffic / steps
        route_traffic_to_service(service_name, current_traffic)
        time.sleep(ramp_up_duration_seconds / steps)  # 10s per step
    
    # Full traffic restored
    log.info(f"Traffic fully restored to {service_name}")
```

### 5.2 Ramp-Up Configuration

```yaml
traffic_ramp:
  enabled: true
  duration_seconds: 60
  steps: 6
  monitoring_interval_seconds: 10
  
  # If error rate increases during ramp-up, abort
  abort_if_error_rate_exceeds: 10%
```

---

## 6. Monitoring Probe Health

### 6.1 Metrics

```
- probe_attempt_count (how many probes sent)
- probe_success_rate (% probes succeeding)
- probe_latency (how long probes take)
- circuit_close_latency (how long from OPEN to CLOSED)
- traffic_ramp_duration (time to restore full traffic)
```

### 6.2 Alerts

**Alert: Probe consistently failing**
- Condition: > 5 consecutive probe failures
- Severity: CRITICAL
- Action: Manual investigation required; service may be permanently down

**Alert: Slow probe response**
- Condition: Probe latency > 5s (when normal is 100-500ms)
- Severity: WARNING
- Action: Service may be struggling; monitor closely

**Alert: Traffic ramp-up failed**
- Condition: Error rate increased during ramp-up
- Severity: CRITICAL
- Action: Abort ramp-up; reopen circuit; investigate

---

## 7. Probe Events & Logging

### 7.1 Events to Emit

```python
class CircuitBreakerEvent:
    """Emitted when circuit breaker transitions."""
    
    def __init__(
        self,
        service_name: str,
        event_type: str,  # "opened", "closed", "probe_sent", etc.
        timestamp: datetime,
        reason: str = None,
        probe_result: str = None
    ):
        self.service_name = service_name
        self.event_type = event_type
        self.timestamp = timestamp
        self.reason = reason
        self.probe_result = probe_result
```

### 7.2 Sample Logs

```
[2026-06-22T10:15:30Z] Circuit OPENED: payment_service
  Reason: Failure rate 60% > threshold 50%
  
[2026-06-22T10:15:45Z] Circuit HALF_OPEN: payment_service
  Sending probe to GET /status
  
[2026-06-22T10:15:46Z] Probe FAILED: payment_service
  Status: 503, Response time: 2500ms
  
[2026-06-22T10:16:45Z] Probe RETRY: payment_service
  Attempt 2 of 5
  
[2026-06-22T10:16:46Z] Probe SUCCEEDED: payment_service
  Status: 200, Response time: 85ms
  
[2026-06-22T10:16:47Z] Circuit CLOSED: payment_service
  Starting traffic ramp-up
  
[2026-06-22T10:17:47Z] Traffic FULLY RESTORED: payment_service
```

---

## 8. Probe Configuration Per Service

### 8.1 Critical Services (Strict Probing)

```yaml
critical_services:
  - service: "payment_processor"
    probe:
      endpoint: "GET /health"
      timeout_ms: 1000
      expected_status: 200
      probe_interval_seconds: 30
      max_probes: 3
    ramp_up:
      duration_seconds: 120
      steps: 6
```

### 8.2 Non-Critical Services (Lenient Probing)

```yaml
non_critical_services:
  - service: "notification_service"
    probe:
      endpoint: "GET /ping"
      timeout_ms: 3000
      expected_status: 200
      probe_interval_seconds: 60
      max_probes: 10
    ramp_up:
      duration_seconds: 30
      steps: 3
```

---

## 9. Testing Half-Open Behavior

### 9.1 Unit Tests

```python
def test_transition_to_half_open_after_duration():
    """Verify circuit transitions to HALF_OPEN after open_duration."""
    cb = CircuitBreaker(open_duration_seconds=0)  # Immediate transition
    
    # Open circuit
    for _ in range(5):
        cb.record_failure()
    assert cb.state == "OPEN"
    
    # Immediately transition to HALF_OPEN
    time.sleep(0.1)  # Wait for transition
    assert cb.state == "HALF_OPEN"

def test_probe_success_closes_circuit():
    """Verify successful probe closes circuit."""
    cb = CircuitBreaker()
    cb.state = "HALF_OPEN"
    
    cb.record_probe_success()
    assert cb.state == "CLOSED"

def test_probe_failure_reopens_circuit():
    """Verify failed probe reopens circuit."""
    cb = CircuitBreaker()
    cb.state = "HALF_OPEN"
    
    cb.record_probe_failure()
    assert cb.state == "OPEN"
```

### 9.2 Integration Tests

```python
def test_full_recovery_flow():
    """Test complete recovery flow: OPEN → HALF_OPEN → CLOSED."""
    with mock_service_failure():
        # Service fails; circuit opens
        for _ in range(5):
            with pytest.raises(CircuitBreakerOpenError):
                call_service()
        
        # Service recovers; probe succeeds
        with mock_service_healthy():
            time.sleep(OPEN_DURATION + 1)
            
            # Circuit is now HALF_OPEN
            # Probe succeeds
            response = call_service()
            
            # Traffic ramping up
            assert response is not None
```

---

## 10. Related Documents

- RES-3: Circuit breaker (defines HALF_OPEN state)
- RES-1: Timeouts (used in probe execution)
- OBS-1: Telemetry (monitors probe health)

---

**Document Owner**: Infrastructure Team  
**Last Review**: 2026-06-22  
**Next Review**: 2026-09-22
