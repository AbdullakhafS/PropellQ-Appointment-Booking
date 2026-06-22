# RES-2: Retry Strategy with Budget Controls

**Document ID**: RES-2  
**Acceptance Criteria**: AC-2  
**Last Updated**: 2026-06-22  
**Status**: Active

---

## Overview

This policy defines standardized retry behavior using exponential backoff with jitter. Retry budgets prevent retry storms, and endpoint allowlists prevent retrying on unsafe operations (e.g., payment processing, account deletion).

---

## 1. Exponential Backoff Strategy

### 1.1 Backoff Formula

```
delay = min(cap, base * (multiplier ^ attempt)) + random_jitter
```

Where:
- `base` = initial delay in milliseconds
- `multiplier` = 2 (exponential: 1x, 2x, 4x, 8x, 16x...)
- `cap` = maximum delay (prevents unbounded growth)
- `random_jitter` = random value in [0, delay * 0.1] to prevent thundering herd
- `attempt` = retry count (0, 1, 2, ...)

### 1.2 Standard Retry Configuration

**Idempotent Safe Operations** (safe to retry):

```yaml
retry_policy:
  name: "standard_safe_retry"
  base_delay_ms: 100
  multiplier: 2
  max_delay_ms: 10000
  max_retries: 3
  jitter_factor: 0.1
```

**Example delays**:
- Attempt 1: 100 ms + jitter
- Attempt 2: 200 ms + jitter
- Attempt 3: 400 ms + jitter
- Total backoff: ~700 ms (plus actual request times)

**Non-Idempotent Operations** (special handling):

```yaml
retry_policy:
  name: "non_idempotent_retry"
  base_delay_ms: 500
  multiplier: 1.5  # Less aggressive
  max_delay_ms: 5000
  max_retries: 2   # Fewer retries
  jitter_factor: 0.2
```

---

## 2. Retry Decision Tree

```
Request fails with exception?
├─ Timeout (no response from server)
│  └─ Idempotent? YES → Retry with backoff
│  └─ Idempotent? NO → Fail immediately
├─ Connection error (network down)
│  └─ YES → Retry with backoff
├─ 5xx (server error)
│  └─ Transient (502, 503, 504)? YES → Retry with backoff
│  └─ Permanent (500, 501)? NO → Fail immediately
├─ 429 (rate limit)
│  └─ YES → Retry with backoff (use Retry-After header if present)
├─ 4xx (client error)
│  └─ NO → Fail immediately (don't retry)
└─ Other
   └─ NO → Fail immediately
```

---

## 3. Retry Allowlist & Blocklist

### 3.1 Safe-to-Retry Operations

Operations marked as **idempotent** and safe to retry:

```yaml
safe_to_retry:
  # Database reads (no side effects)
  - "GET /bookings/{id}"
  - "GET /availability"
  - "GET /appointments"
  
  # Search operations
  - "POST /search"
  - "POST /search/facets"
  
  # Status checks
  - "GET /health"
  - "GET /status"
  
  # Metadata operations
  - "GET /appointments/types"
  - "GET /locations"
```

### 3.2 NEVER Retry Operations

Operations marked as **NOT idempotent** - dangerous to retry:

```yaml
never_retry:
  # Payment processing (charges duplicate if retried)
  - "POST /payments/charge"
  - "POST /payments/refund"
  
  # Account state changes (would delete twice)
  - "DELETE /appointments/{id}"
  - "DELETE /bookings/{id}"
  
  # One-time operations
  - "POST /auth/register"
  - "POST /auth/verify_otp"
  
  # State mutations (no idempotent key)
  - "PATCH /appointments/{id}" (unless endpoint is idempotent)
```

### 3.3 Conditional Retry Operations

Operations that require **idempotent key** to be retried safely:

```yaml
conditional_retry:
  # Create operations (OK to retry with idempotent key)
  - endpoint: "POST /bookings"
    requires_idempotent_key: true
    key_header: "Idempotence-Key"
    description: "Use UUID; safe to retry with same key"
  
  # Update operations (OK if using conditional update)
  - endpoint: "PATCH /bookings/{id}"
    requires_idempotent_key: false
    requires_version_check: true
    description: "Check version; fail if stale"
```

---

## 4. Retry Budget

### 4.1 Budget Concept

**Retry budget** limits total retry load to prevent retry storms. Each operation has:

- **Budget**: How many retries are allowed per window
- **Window**: Time period (typically 1 minute)
- **Tokens**: Consumed on each retry; replenished over time

### 4.2 Budget Configuration

```yaml
retry_budget:
  window_seconds: 60
  
  # Per endpoint budget
  budget_rules:
    - endpoint: ".*"  # Default for all endpoints
      tokens_per_minute: 1000
      reserved_for_retries: 0.1  # 10% reserved for retries
    
    - endpoint: "GET /.*"  # Reads can retry more
      tokens_per_minute: 2000
      reserved_for_retries: 0.2  # 20% for retries
    
    - endpoint: "POST /payments/.*"  # Payments strict
      tokens_per_minute: 100
      reserved_for_retries: 0.05  # 5% for retries
```

### 4.3 Budget Exhaustion Behavior

When retry budget is exhausted:

1. **First retry**: Succeeds (retry allowed)
2. **Second retry**: Fails with `RetryBudgetExhausted` error
3. **Log**: Incident logged; alert fired if persistent
4. **Action**: Investigate root cause; scale service if needed

---

## 5. Jitter Implementation

### 5.1 Why Jitter?

Without jitter, all clients retry at same times → **thundering herd** → spike in load → all fail → retry again → worse spike.

With jitter, retries spread out → smooth load → many succeed → fewer retry → healthy system.

### 5.2 Jitter Algorithm

```python
import random
import time

def calculate_backoff_with_jitter(
    attempt: int,
    base_ms: int = 100,
    multiplier: float = 2.0,
    max_ms: int = 10000,
    jitter_factor: float = 0.1
) -> float:
    """Calculate backoff delay with jitter."""
    # Exponential backoff
    delay_ms = min(max_ms, base_ms * (multiplier ** attempt))
    
    # Add random jitter (±10% by default)
    jitter_ms = delay_ms * jitter_factor
    jitter = random.uniform(-jitter_ms, jitter_ms)
    
    total_delay_ms = max(0, delay_ms + jitter)
    return total_delay_ms / 1000  # Convert to seconds
```

### 5.3 Jitter in Action

```
Attempt 1: 100 ms + jitter [-10, +10] = 95-110 ms
Attempt 2: 200 ms + jitter [-20, +20] = 180-220 ms
Attempt 3: 400 ms + jitter [-40, +40] = 360-440 ms
```

Multiple clients → retries spread across entire jitter range → no spike.

---

## 6. Specific Retry Policies by Endpoint Type

### 6.1 Search & Read Operations

```yaml
search_retry_policy:
  max_retries: 4
  base_delay_ms: 100
  multiplier: 2.0
  max_delay_ms: 10000
  retry_on: ["TimeoutError", "500", "502", "503", "504"]
  dont_retry_on: ["400", "401", "403", "404"]
```

Example: Booking search times out
- Attempt 1: Timeout
- Attempt 2: +100ms
- Attempt 3: +200ms
- Attempt 4: +400ms
- Total: ~700ms of backoff + request times

### 6.2 Payment Operations

```yaml
payment_retry_policy:
  max_retries: 0  # NO RETRIES without idempotent key
  requires_idempotent_key: true
  idempotent_key_header: "Idempotence-Key"
```

If idempotent key provided:
```yaml
payment_retry_with_key_policy:
  max_retries: 1
  base_delay_ms: 1000  # Longer backoff
  multiplier: 1.5
  max_delay_ms: 5000
  retry_on: ["TimeoutError", "503", "504"]  # Only transient errors
```

### 6.3 Notification Operations

```yaml
notification_retry_policy:
  max_retries: 3
  base_delay_ms: 500
  multiplier: 2.0
  max_delay_ms: 30000
  retry_on: ["TimeoutError", "500", "502", "503", "504", "429"]
  dont_fail_on_exhaustion: true  # Best effort; don't block if retries exhausted
```

---

## 7. Code Implementation

### 7.1 Retry Decorator

```python
@retry(
    max_attempts=3,
    backoff=ExponentialBackoff(
        base_ms=100,
        multiplier=2,
        max_ms=10000,
        jitter=True
    ),
    retry_on=[TimeoutError, ConnectionError],
    dont_retry_on=[ValueError]
)
def call_external_api(endpoint: str, data: dict) -> Response:
    response = requests.post(endpoint, json=data, timeout=5)
    response.raise_for_status()
    return response
```

### 7.2 Retry Budget Middleware

```python
class RetryBudgetMiddleware:
    def __init__(self, tokens_per_minute: int = 1000):
        self.budget = RetryBudget(
            capacity=tokens_per_minute,
            refill_per_second=tokens_per_minute / 60
        )
    
    def can_retry(self, endpoint: str) -> bool:
        """Check if retry budget allows this retry."""
        if self.budget.available_tokens() > 0:
            self.budget.consume(1)
            return True
        else:
            log.warning(f"Retry budget exhausted for {endpoint}")
            return False
```

---

## 8. Observability

### 8.1 Metrics to Track

- **Retry count**: Number of retries per endpoint
- **Retry success rate**: % of retries that succeeded
- **Budget consumption**: % of retry budget used
- **Retry amplification**: Ratio of retries to original requests

### 8.2 Alerts

**Alert: High retry rate**
- Threshold: > 5% of requests retried
- Severity: WARNING
- Action: Investigate downstream service health

**Alert: Retry budget exhausted**
- Threshold: Budget fully consumed for > 5 min
- Severity: CRITICAL
- Action: Scale service or reduce traffic

---

## 9. Retry Best Practices

### 9.1 DO

✅ Use exponential backoff with jitter  
✅ Retry only idempotent operations  
✅ Use idempotent keys for non-idempotent operations  
✅ Monitor retry rates  
✅ Implement retry budgets  
✅ Document retry behavior for each endpoint  

### 9.2 DON'T

❌ Retry forever (use max_retries)  
❌ Use same retry policy for all endpoints  
❌ Retry without jitter (causes thundering herd)  
❌ Retry non-idempotent operations without idempotent key  
❌ Ignore retry budget exhaustion  

---

## 10. Testing Retry Behavior

### 10.1 Unit Tests

```python
def test_exponential_backoff_with_jitter():
    """Verify backoff delays increase exponentially."""
    delays = [
        calculate_backoff_with_jitter(i)
        for i in range(3)
    ]
    # Each delay ~2x previous (within jitter)
    assert delays[1] > delays[0]
    assert delays[2] > delays[1]

def test_retry_not_on_4xx_errors():
    """Verify 4xx errors don't trigger retries."""
    response = requests.Response()
    response.status_code = 404
    assert should_retry(response) is False
```

### 10.2 Integration Tests

```python
def test_payment_requires_idempotent_key():
    """Verify payment endpoint requires idempotent key to retry."""
    # Without key: no retries
    response = client.post("/payments/charge", json={...})
    assert response.status_code in [500, 503]  # Not retried
    
    # With key: retried
    response = client.post(
        "/payments/charge",
        json={...},
        headers={"Idempotence-Key": "uuid-123"}
    )
    # May still fail but was retried
```

---

## 11. Related Documents

- RES-1: Timeout values (trigger for retries)
- RES-3: Circuit breaker (stops retries after repeated failures)
- OBS-1: Telemetry (monitors retry rate)

---

**Document Owner**: Infrastructure Team  
**Last Review**: 2026-06-22  
**Next Review**: 2026-09-22
