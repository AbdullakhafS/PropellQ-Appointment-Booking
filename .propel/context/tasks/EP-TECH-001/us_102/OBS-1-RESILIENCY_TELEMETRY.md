# OBS-1: Resiliency Telemetry & Alerting

**Document ID**: OBS-1  
**Task**: OBS-1 (Observability and Operations Tasks)  
**Last Updated**: 2026-06-22  
**Status**: Active

---

## Overview

This policy defines metrics, logging, and alerts for resiliency components (timeouts, retries, circuit breakers, fallbacks). Comprehensive observability enables rapid incident detection and troubleshooting.

---

## 1. Core Metrics

### 1.1 Timeout Metrics

```
resiliency.timeout.events
  description: "Count of timeout events"
  labels:
    - endpoint (e.g., "POST /bookings")
    - call_type (e.g., "external_api", "database", "cache")
    - service (e.g., "booking_service")
  type: Counter
  example: resiliency.timeout.events{endpoint="GET /availability", call_type="search_api"} = 10

resiliency.timeout.duration_seconds
  description: "Time until timeout occurred"
  labels: [endpoint, call_type, service]
  type: Histogram
  buckets: [0.1, 0.5, 1, 2, 5, 10, 30]
  percentiles: [50, 95, 99]

resiliency.timeout.rate_percent
  description: "% of requests timing out"
  labels: [endpoint, service]
  type: Gauge
  example: resiliency.timeout.rate_percent{endpoint="GET /bookings"} = 2.5  # 2.5%
```

### 1.2 Retry Metrics

```
resiliency.retry.attempts
  description: "Number of retries per request"
  labels:
    - endpoint
    - call_type
    - retry_reason (e.g., "timeout", "5xx", "429")
  type: Counter
  example: resiliency.retry.attempts{endpoint="GET /appointments", retry_reason="timeout"} = 45

resiliency.retry.success_rate
  description: "% of retries that succeeded"
  labels: [endpoint, call_type]
  type: Gauge
  example: resiliency.retry.success_rate{endpoint="POST /bookings"} = 85  # 85% of retries succeeded

resiliency.retry.budget_available
  description: "Remaining tokens in retry budget"
  labels: [endpoint]
  type: Gauge
  example: resiliency.retry.budget_available{endpoint=".*"} = 750  # 750 tokens left

resiliency.retry.max_attempts_exceeded
  description: "Requests that exceeded max retry count"
  labels: [endpoint, call_type]
  type: Counter
  example: resiliency.retry.max_attempts_exceeded{endpoint="POST /payments"} = 2
```

### 1.3 Circuit Breaker Metrics

```
resiliency.circuit_breaker.state
  description: "Current state of circuit breaker"
  labels:
    - service (e.g., "payment_processor")
  type: Gauge
  values: [0=CLOSED, 1=OPEN, 2=HALF_OPEN]
  example: resiliency.circuit_breaker.state{service="payment_processor"} = 0  # CLOSED

resiliency.circuit_breaker.state_changes
  description: "Count of state transitions"
  labels: [service, from_state, to_state]
  type: Counter
  example: resiliency.circuit_breaker.state_changes{service="payment_processor", from="CLOSED", to="OPEN"} = 3

resiliency.circuit_breaker.failure_rate
  description: "Current failure rate (when CLOSED)"
  labels: [service]
  type: Gauge
  example: resiliency.circuit_breaker.failure_rate{service="search_service"} = 35.5  # 35.5%

resiliency.circuit_breaker.time_in_state_seconds
  description: "How long circuit has been in current state"
  labels: [service, state]
  type: Gauge
  example: resiliency.circuit_breaker.time_in_state_seconds{service="payment_processor", state="OPEN"} = 45
```

### 1.4 Fallback Metrics

```
resiliency.fallback.activations
  description: "Number of fallbacks triggered"
  labels:
    - service
    - fallback_type (e.g., "queue", "cache", "empty", "skip")
  type: Counter
  example: resiliency.fallback.activations{service="sms_notifications", fallback_type="queue"} = 42

resiliency.fallback.queue_size
  description: "Number of items in async fallback queue"
  labels: [service, queue_name]
  type: Gauge
  example: resiliency.fallback.queue_size{service="sms_notifications", queue="sms_queue"} = 1250

resiliency.fallback.queue_age_seconds
  description: "Age of oldest item in queue"
  labels: [service, queue_name]
  type: Gauge
  example: resiliency.fallback.queue_age_seconds{service="sms_notifications", queue="sms_queue"} = 3600  # 1 hour old

resiliency.fallback.dead_letter_count
  description: "Messages that failed and went to DLQ"
  labels: [service, queue_name, reason]
  type: Counter
  example: resiliency.fallback.dead_letter_count{service="sms_notifications", queue="sms_queue", reason="max_retries"} = 3
```

---

## 2. Dashboards

### 2.1 Resiliency Overview Dashboard

**URL**: `/monitoring/dashboards/resiliency-overview`

Panels:
- Circuit breaker state (all services)
- Timeout rate trend (last 24h)
- Retry success rate (last 24h)
- Active fallback counts
- Health score

### 2.2 Service-Specific Dashboards

**URL**: `/monitoring/dashboards/resiliency/{service}`

Panels for each service:
- Circuit breaker state & transitions
- Failure rate & trends
- Probe success rate
- Traffic ramp-up progress
- Recent incidents

### 2.3 Fallback Status Dashboard

**URL**: `/monitoring/dashboards/fallback-status`

Panels:
- Active fallback counts by type
- Queue sizes & age
- Dead letter counts
- Processing lag

---

## 3. Alerts

### 3.1 Timeout Alerts

```yaml
alert: TimeoutRateHigh
  condition: |
    resiliency.timeout.rate_percent{endpoint="~.*"} > 1%
  for: 5m
  severity: WARNING
  description: "{{ $labels.endpoint }} timeout rate {{ $value }}% exceeds 1%"
  action: "Investigate downstream service; check health metrics"

alert: TimeoutRateVeryHigh
  condition: |
    resiliency.timeout.rate_percent{endpoint="~.*"} > 10%
  for: 1m
  severity: CRITICAL
  description: "{{ $labels.endpoint }} timeout rate {{ $value }}% critically high"
  action: "Page on-call; investigate service failure"
```

### 3.2 Retry Alerts

```yaml
alert: HighRetryRate
  condition: |
    resiliency.retry.attempts > 100 per minute
  for: 5m
  severity: WARNING
  description: "High retry activity: {{ $value }} retries/min"
  action: "Check for cascading failures; monitor downstream services"

alert: RetryBudgetExhausted
  condition: |
    resiliency.retry.budget_available < 100
  for: 2m
  severity: CRITICAL
  description: "Retry budget nearly exhausted"
  action: "Scale service or reduce traffic"

alert: RetryFailureRate
  condition: |
    resiliency.retry.success_rate < 50%
  for: 5m
  severity: WARNING
  description: "Less than 50% of retries succeeding"
  action: "Investigate downstream service; may need to increase timeout/retries"
```

### 3.3 Circuit Breaker Alerts

```yaml
alert: CircuitBreakerOpened
  condition: |
    resiliency.circuit_breaker.state{service="~.*"} == 1
  for: 30s
  severity: WARNING
  description: "Circuit breaker opened for {{ $labels.service }}"
  action: "Investigate service; check logs"

alert: CircuitBreakerFrequentlyOpens
  condition: |
    increase(
      resiliency.circuit_breaker.state_changes{from="CLOSED", to="OPEN"}[5m]
    ) > 3
  for: 1m
  severity: CRITICAL
  description: "Circuit breaker {{ $labels.service }} opened 3+ times in 5m"
  action: "Page on-call; probable cascading failure"

alert: CircuitBreakerStuckHalfOpen
  condition: |
    resiliency.circuit_breaker.time_in_state_seconds{state="HALF_OPEN"} > 600
  for: 1m
  severity: WARNING
  description: "Circuit {{ $labels.service }} stuck in HALF_OPEN for >10min"
  action: "Service not recovering; may need manual intervention"
```

### 3.4 Fallback Alerts

```yaml
alert: HighFallbackActivation
  condition: |
    rate(resiliency.fallback.activations[5m]) > 10 per second
  for: 2m
  severity: WARNING
  description: "High fallback activation rate: {{ $value }}/sec"
  action: "Investigate affected service; check circuit breaker state"

alert: FallbackQueueGrowing
  condition: |
    resiliency.fallback.queue_size{service="sms_notifications"} > 50000
  for: 5m
  severity: CRITICAL
  description: "SMS notification queue has {{ $value }} pending items"
  action: "Page on-call; queue processor may be down"

alert: FallbackQueueAgeHigh
  condition: |
    resiliency.fallback.queue_age_seconds{queue_name="sms_queue"} > 86400
  for: 1m
  severity: CRITICAL
  description: "SMS queue oldest message is {{ $value }}s old (>24h)"
  action: "Messages stuck; investigate queue processor; restart if needed"

alert: DeadLetterQueueGrowing
  condition: |
    rate(resiliency.fallback.dead_letter_count[1h]) > 100
  for: 5m
  severity: CRITICAL
  description: "{{ $value }} messages moved to DLQ in last hour"
  action: "Investigate root cause; may indicate permanent failure"
```

---

## 4. Logging

### 4.1 Timeout Events

```json
{
  "timestamp": "2026-06-22T10:15:30Z",
  "event_type": "timeout",
  "service": "booking_service",
  "endpoint": "POST /bookings",
  "duration_ms": 5003,
  "timeout_ms": 5000,
  "call_type": "external_api",
  "status": "timeout",
  "trace_id": "abc-123-def",
  "correlation_id": "booking-456"
}
```

### 4.2 Retry Events

```json
{
  "timestamp": "2026-06-22T10:15:31Z",
  "event_type": "retry",
  "service": "booking_service",
  "endpoint": "POST /bookings",
  "attempt": 1,
  "retry_reason": "timeout",
  "backoff_ms": 100,
  "trace_id": "abc-123-def"
}
```

### 4.3 Circuit Breaker Events

```json
{
  "timestamp": "2026-06-22T10:15:45Z",
  "event_type": "circuit_breaker_transition",
  "service": "payment_processor",
  "from_state": "CLOSED",
  "to_state": "OPEN",
  "failure_rate": 60.5,
  "failure_count": 6,
  "window_seconds": 10,
  "reason": "Failure rate 60.5% exceeds threshold 50%"
}
```

### 4.4 Fallback Events

```json
{
  "timestamp": "2026-06-22T10:15:46Z",
  "event_type": "fallback_activated",
  "service": "sms_notifications",
  "fallback_type": "queue_and_retry",
  "reason": "Service unavailable",
  "original_request_id": "sms-789",
  "queue_id": "queue-msg-001"
}
```

---

## 5. SLOs & Error Budgets

### 5.1 Timeout SLO

```
SLO: Timeouts affect < 0.5% of requests
Error Budget: 0.5% per month = ~3.6 hours downtime
```

### 5.2 Retry SLO

```
SLO: Retry success rate > 90%
Error Budget: Retries can fail for < 10% of attempts
```

### 5.3 Circuit Breaker SLO

```
SLO: Circuit breaker in OPEN state < 1% of time
Error Budget: Circuit can be open ~7.2 hours per month
```

### 5.4 Fallback SLO

```
SLO: Fallback queue processing latency < 1 hour
Error Budget: Messages can be queued up to 1 hour before alerting
```

---

## 6. Observability Best Practices

### 6.1 DO

✅ Emit metrics for every timeout/retry/circuit event  
✅ Include trace IDs for correlation  
✅ Set up dashboards before going live  
✅ Alert on SLO violations, not just errors  
✅ Monitor queue sizes & age  

### 6.2 DON'T

❌ Emit too many metrics (cardinality explosion)  
❌ Log sensitive data (PII, credit cards)  
❌ Alert on every single error  
❌ Ignore metrics without alerts  
❌ Set alert thresholds without baseline data  

---

## 7. Related Documents

- RES-1 through RES-4: Resiliency policies (define what to measure)
- FALL-1 & FALL-2: Fallback policies (define fallback metrics)
- OPS-1: Operations runbook (uses these metrics for troubleshooting)

---

**Document Owner**: Infrastructure Team  
**Last Review**: 2026-06-22  
**Next Review**: 2026-09-22
