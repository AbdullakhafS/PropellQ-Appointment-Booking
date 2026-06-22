# RES-1: Safe Default Timeout Values by Call Type

**Document ID**: RES-1  
**Acceptance Criteria**: AC-1  
**Last Updated**: 2026-06-22  
**Status**: Active  

---

## Overview

This policy defines safe-by-default timeout values for all service communication. Timeouts prevent cascading failures by ensuring hung requests don't block indefinitely. Defaults are categorized by call type (synchronous, asynchronous, external) and can be overridden with documented justification.

---

## 1. Timeout Categories

### 1.1 Synchronous Internal Calls (In-Process)

**Definition**: Calls within the same service, synchronous execution path.

| Call Type | Default Timeout | Min Bound | Max Bound | Rationale |
|-----------|-----------------|-----------|-----------|-----------|
| **Cache Lookup** | 100 ms | 10 ms | 500 ms | Memory access; fail fast if slow |
| **Database Query** | 5 seconds | 1s | 30s | Single query; should be fast |
| **Local Storage** | 2 seconds | 100ms | 10s | Disk I/O; reasonable upper bound |
| **In-Memory Computation** | 500 ms | 50ms | 5s | CPU-bound; fail if stuck |

**Application**: Database operations, session lookups, configuration retrieval

---

### 1.2 Synchronous External Calls (RPC/REST)

**Definition**: Calls to external services over network; synchronous request-response.

| Call Type | Default Timeout | Min Bound | Max Bound | Rationale |
|-----------|-----------------|-----------|-----------|-----------|
| **Internal Microservice** | 3 seconds | 500ms | 15s | Trusted network; reasonable SLA |
| **Third-Party API (Payment)** | 10 seconds | 5s | 45s | Payment processing critical; higher latency OK |
| **Third-Party API (Messaging)** | 5 seconds | 2s | 30s | Notification; tolerate some latency |
| **Third-Party API (Other)** | 8 seconds | 3s | 30s | Generic; most SaaS APIs respond in 2-5s |
| **Search/Analytics** | 15 seconds | 5s | 60s | Complex queries; allow longer processing |
| **Health Check** | 2 seconds | 500ms | 5s | Quick service status; fail fast |

**Application**: REST calls, gRPC calls, message queue operations

---

### 1.3 Asynchronous Calls (Background Jobs)

**Definition**: Non-blocking operations, fire-and-forget or eventually-consistent.

| Call Type | Default Timeout | Min Bound | Max Bound | Rationale |
|-----------|-----------------|-----------|-----------|-----------|
| **Message Queue Publish** | 5 seconds | 1s | 30s | Queue op should be fast |
| **Background Job Queue** | 30 seconds | 10s | 120s | Job may queue; allow time |
| **Batch Processing** | 5 minutes | 1m | 30m | Batch work; higher tolerance |
| **Webhook Delivery** | 10 seconds | 3s | 60s | External callback; moderate wait |

**Application**: Email sending, report generation, async task queues

---

### 1.4 Streaming/Long-Poll

**Definition**: Continuous connections, streaming data, or long-poll subscriptions.

| Call Type | Default Timeout | Min Bound | Max Bound | Rationale |
|-----------|-----------------|-----------|-----------|-----------|
| **WebSocket Connection** | 30 seconds (idle) | 10s | 5 min | Keep-alive heartbeat; detect stale |
| **Server-Sent Events** | 30 seconds (idle) | 10s | 5 min | Stream idle timeout |
| **Long-Poll** | 60 seconds | 30s | 5 min | Allow client to wait for updates |

**Application**: Real-time notifications, live data feeds, subscription APIs

---

## 2. Timeout Override Policy

### 2.1 When Overrides Are Permitted

Overrides are permitted only for documented, justified use cases:

- **Batch processing** requiring > 5 minutes
- **Search/analytics** queries with high complexity (> 100M rows)
- **File upload/download** for large payloads (> 100 MB)
- **Webhook retries** to external partners with known slow response times
- **Scheduled maintenance** operations on large datasets

### 2.2 Override Approval Process

1. **Small override** (within 2x default): Tech lead approval only
2. **Large override** (> 2x default): Tech lead + security lead approval
3. **Emergency override** (incident): CTO approval; incident ticket required

### 2.3 Override Tracking

All overrides must be tracked in `app/config/timeout_overrides.yaml`:

```yaml
overrides:
  - service: payment_processor
    endpoint: /process_payment
    default_timeout_ms: 10000
    override_timeout_ms: 30000
    reason: "Payment processing may take 15-20s with fraud checks"
    approved_by: "bob@propellq.com"
    approval_date: "2026-06-15"
    expiry_date: "2026-12-15"
    ticket: "INC-2026-0615-001"
```

---

## 3. Timeout Configuration

### 3.1 Environment-Based Configuration

**Development**:
```yaml
timeouts:
  internal_call: 10000 ms    # Relaxed for debugging
  external_call: 30000 ms    # Relaxed for flaky test APIs
  health_check: 5000 ms
```

**Staging**:
```yaml
timeouts:
  internal_call: 5000 ms     # Production-like
  external_call: 15000 ms    # Some tolerance for test systems
  health_check: 2000 ms
```

**Production**:
```yaml
timeouts:
  internal_call: 3000 ms     # Strict
  external_call: 8000 ms     # Strict
  health_check: 2000 ms      # Strict
```

### 3.2 Per-Endpoint Configuration

```python
# In app/src/resiliency.py
TIMEOUT_DEFAULTS = {
    # Booking service
    "POST /bookings": {
        "timeout_ms": 5000,
        "call_type": "database_write"
    },
    "GET /bookings/{id}": {
        "timeout_ms": 2000,
        "call_type": "database_read"
    },
    "GET /availability": {
        "timeout_ms": 3000,
        "call_type": "external_search"
    },
    
    # Payment service (external)
    "POST /payments/charge": {
        "timeout_ms": 10000,
        "call_type": "external_payment"
    },
    
    # Messaging service
    "POST /notifications/send": {
        "timeout_ms": 5000,
        "call_type": "message_queue"
    }
}
```

---

## 4. Timeout Enforcement

### 4.1 Code-Level Enforcement

All outbound calls **must** specify a timeout. No timeout = code review rejection.

```python
# ✅ GOOD - Explicit timeout
response = requests.get(
    url,
    timeout=3.0  # 3 seconds
)

# ❌ BAD - No timeout (will be rejected in code review)
response = requests.get(url)

# ✅ GOOD - Using default from config
response = requests.get(
    url,
    timeout=TIMEOUT_DEFAULTS["GET /bookings/{id}"]["timeout_ms"] / 1000
)
```

### 4.2 Framework Integration

All HTTP clients configured with defaults:

```python
# requests library
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    timeout=(3.0, 10.0)  # connect=3s, read=10s
)
session.mount("https://", adapter)

# httpx library
client = httpx.Client(timeout=10.0)

# asyncio calls
asyncio.wait_for(coroutine, timeout=5.0)
```

### 4.3 Database Connection Pooling

```python
# SQLAlchemy
engine = create_engine(
    "postgresql://...",
    connect_args={
        "timeout": 5,  # connection timeout
        "statement_timeout": 5000  # query timeout (ms)
    }
)
```

---

## 5. Observability

### 5.1 Metrics to Track

- **Timeout events**: Count of requests that exceeded timeout (by endpoint)
- **Timeout duration distribution**: P50, P95, P99 latency vs timeout value
- **Timeout error rate**: % of requests timing out (by service, endpoint)

### 5.2 Alerts

**Alert on timeout rate**:
- Threshold: > 1% of requests timing out
- Severity: WARNING (investigate)
- Action: Check downstream service health

**Alert on frequent timeouts**:
- Threshold: > 10 timeouts/minute on single endpoint
- Severity: CRITICAL (page on-call)
- Action: Investigate cascading failure, increase timeout, or scale service

---

## 6. Timeout Best Practices

### 6.1 DO

✅ Set timeouts explicitly on every outbound call  
✅ Use shorter timeouts for health checks  
✅ Increase timeout for batch/background jobs  
✅ Document timeout overrides with justification  
✅ Monitor timeout rates in production  
✅ Fail fast on timeouts (don't retry indefinitely)  

### 6.2 DON'T

❌ Use infinite timeouts (0 or None)  
❌ Set timeout > 60 seconds without approval  
❌ Silently catch timeout exceptions (log them)  
❌ Retry indefinitely on timeout (use retry budget)  
❌ Use same timeout for cache and external API calls  

---

## 7. Testing Timeout Behavior

### 7.1 Unit Tests

```python
def test_timeout_enforced_on_slow_response():
    """Verify timeout is applied to slow external calls."""
    with pytest.raises(requests.exceptions.Timeout):
        requests.get(
            "http://httpbin.org/delay/10",  # 10 second delay
            timeout=2.0  # 2 second timeout
        )
```

### 7.2 Integration Tests

```python
def test_booking_api_respects_timeout():
    """Verify booking API times out on slow database."""
    # Mock slow database query
    with patch('app.db.query', side_effect=slow_query):
        response = client.get("/bookings/123", timeout=1.0)
        assert response.status_code == 504  # Gateway Timeout
```

### 7.3 Load Tests

- Measure p95/p99 latency under normal load
- Verify timeouts don't trigger on p99 (should be well below)
- Test cascading timeout behavior

---

## 8. Troubleshooting

### 8.1 Too Many Timeouts?

| Symptom | Cause | Fix |
|---------|-------|-----|
| Timeouts on specific endpoint | Endpoint is slow; check logs | Increase timeout OR optimize endpoint |
| Timeouts across all endpoints | Downstream service down | Page on-call; investigate service |
| Timeout rate increasing | Approaching resource limits | Scale service |

### 8.2 Timeout Too Long?

| Symptom | Cause | Fix |
|---------|-------|-----|
| User request hangs for 30s | Timeout set too high | Reduce timeout to fail-fast |
| Timeouts happen before requests complete | Timeout too short | Increase timeout; check p99 latency |

---

## 9. Timeline

- **Week 1**: Deploy timeout defaults to staging
- **Week 2**: Monitor staging; adjust based on actual latencies
- **Week 3**: Roll out to production with gradual ramp (10% → 50% → 100%)

---

## 10. Related Documents

- RES-2: Retry strategy (uses timeout to trigger retries)
- RES-3: Circuit breaker (opens after repeated timeouts)
- OBS-1: Telemetry (tracks timeout events)

---

**Document Owner**: Infrastructure Team  
**Last Review**: 2026-06-22  
**Next Review**: 2026-09-22
