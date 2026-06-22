# RES-3: Circuit Breaker Open-State Policy

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, platform architects

---

## 1. Overview

This document defines circuit breaker behavior for detecting and responding to cascading failures, preventing retry amplification and resource exhaustion when downstream services fail.

**Principles:**
- Failures are counted and thresholds trigger circuit open
- Open circuit rejects fast without calling downstream
- Half-open allows probe requests to test recovery
- Transitions emit metrics for visibility

---

## 2. Circuit Breaker States

```
CLOSED (Normal)
  ↓ failures > threshold
OPEN (Failure detected)
  ↓ timeout expires
HALF-OPEN (Testing recovery)
  ↓ probe succeeds
CLOSED (Recovered)

OR

HALF-OPEN ↓ probe fails
OPEN (Still failing)
```

---

## 3. Failure Thresholds

### 3.1 Threshold Matrix

| Metric | Threshold | Duration | Action |
|---|---|---|---|
| **Failure Rate** | 50% of requests fail | 30 seconds | Open circuit |
| **Consecutive Failures** | 5+ failures in a row | Any time | Open circuit |
| **Error Count** | 100+ errors | 1 minute | Open circuit |
| **Timeout Rate** | 30%+ requests timeout | 30 seconds | Open circuit |

### 3.2 Example Scenarios

**Scenario 1: Database Connection Failure**
```
T+0: 1st request fails (timeout) → failure_count=1
T+2: 2nd request fails (timeout) → failure_count=2
T+4: 3rd request fails (timeout) → failure_count=3
T+6: 4th request fails (timeout) → failure_count=4
T+8: 5th request fails (timeout) → failure_count=5
     → OPEN CIRCUIT (5 consecutive failures)
T+9: All new requests rejected fast
T+70: Half-open probe sent
```

**Scenario 2: Gradual Error Rate Increase**
```
First 30 seconds:
  Requests: 200
  Failures: 80 (40%)
  → Still below 50% threshold

Next 30 seconds:
  Requests: 200
  Failures: 110 (55%)
  → Exceeds 50% threshold
  → OPEN CIRCUIT
```

---

## 4. Circuit Breaker Configuration

### 4.1 By Service Type

| Service Type | Failure Rate | Consecutive | Open Duration | Reason |
|---|---|---|---|---|
| **Internal Service** | 50% | 5 | 30s | Fast recovery expected |
| **External API** | 30% | 3 | 60s | Slower recovery |
| **Database** | 50% | 3 | 60s | Connection pool restart |
| **Cache** | 50% | 10 | 10s | Fast fallback available |
| **Payment** | 10% | 1 | 120s | Critical, conservative |

### 4.2 Configuration Template

```yaml
CircuitBreakerPolicy:
  # Booking database
  BookingDb:
    FailureThreshold: 0.50        # 50% failure rate
    ConsecutiveFailures: 5
    SamplingDuration: 30s          # Time window for failure rate
    OpenDuration: 60s              # How long to stay open
    
  # External payment API
  PaymentGateway:
    FailureThreshold: 0.10         # 10% failure rate (conservative)
    ConsecutiveFailures: 1         # Fail fast for payments
    SamplingDuration: 30s
    OpenDuration: 120s             # Longer recovery window

  # Appointment search service
  SearchService:
    FailureThreshold: 0.50
    ConsecutiveFailures: 5
    SamplingDuration: 30s
    OpenDuration: 30s              # Fast fallback (search not critical)
```

---

## 5. Open Circuit Behavior

### 5.1 What Happens When Circuit Opens

```
Request arrives
  ↓
Circuit breaker checks state
  ↓
Circuit is OPEN
  ↓
Immediately return failure (no downstream call)
  ↓
Client sees error with ≈0ms latency (vs 10s timeout)
```

### 5.2 Fast Failure Response

```csharp
public async Task<Result> CallDownstreamService()
{
    if (breaker.State == CircuitState.Open)
    {
        // Return fast failure without calling downstream
        return new Result(
            Success: false,
            Error: "Service temporarily unavailable (circuit open)",
            RetryAfterMs: breaker.GetOpenDurationRemaining()
        );
    }
    
    // Normal flow if closed
    return await _httpClient.GetAsync(url);
}
```

**Impact:**
- Client: Sees error immediately (~1ms)
- Downstream: Gets no traffic (circuit open)
- Resource pressure: Relieved by stopped retry attempts

---

## 6. Implementation

### 6.1 C# / .NET Implementation

```csharp
using Polly;
using Polly.CircuitBreaker;

// Define circuit breaker policy
var circuitBreakerPolicy = Policy
    .Handle<HttpRequestException>()
    .OrResult<HttpResponseMessage>(r => !r.IsSuccessStatusCode)
    .CircuitBreakerAsync<HttpResponseMessage>(
        handledEventsAllowedBeforeBreaking: 5,  // Open after 5 failures
        durationOfBreak: TimeSpan.FromSeconds(60),
        onBreak: (outcome, duration) =>
        {
            _logger.LogError(
                "Circuit breaker opened for {Duration}s. Outcome: {Outcome}",
                duration.TotalSeconds,
                outcome.Exception?.Message ?? outcome.Result?.StatusCode.ToString()
            );
            _telemetry.TrackCircuitBreakerOpened("ExternalApi", duration);
        },
        onReset: () =>
        {
            _logger.LogInformation("Circuit breaker reset");
            _telemetry.TrackCircuitBreakerReset("ExternalApi");
        },
        onHalfOpen: () =>
        {
            _logger.LogInformation("Circuit breaker half-open, testing recovery");
            _telemetry.TrackCircuitBreakerHalfOpen("ExternalApi");
        }
    );

// Combine with timeout policy
var resilientPolicy = Policy.WrapAsync(
    timeoutPolicy,
    retryPolicy,
    circuitBreakerPolicy
);

// Usage
var result = await resilientPolicy.ExecuteAsync(
    async () => await _httpClient.GetAsync(url)
);
```

### 6.2 TypeScript / Node.js Implementation

```typescript
import CircuitBreaker from 'opossum';

const breaker = new CircuitBreaker(
  async (url: string) => {
    return fetch(url);
  },
  {
    timeout: 10000,                    // Timeout request after 10s
    errorThresholdPercentage: 50,      // Open after 50% failures
    resetTimeout: 30000,               // Try again after 30s
    name: 'ExternalApi',
    fallback: () => ({ status: 503, message: 'Service unavailable' })
  }
);

// Listen to events
breaker.on('open', () => {
  console.error('Circuit breaker opened');
  telemetry.trackCircuitBreakerOpened('ExternalApi');
});

breaker.on('halfOpen', () => {
  console.log('Circuit breaker half-open, testing recovery');
  telemetry.trackCircuitBreakerHalfOpen('ExternalApi');
});

breaker.on('close', () => {
  console.log('Circuit breaker closed, service recovered');
  telemetry.trackCircuitBreakerClosed('ExternalApi');
});

// Usage
try {
  const response = await breaker.fire('https://api.external.com/data');
} catch (error) {
  console.error('Request failed:', error.message);
}
```

### 6.3 Python Implementation

```python
from pybreaker import CircuitBreaker
import asyncio
import logging

# Create circuit breaker
breaker = CircuitBreaker(
    fail_max=5,                    # Open after 5 failures
    reset_timeout=60,              # Reset after 60s
    name='ExternalApi',
    listeners=[                    # Event listeners
        CircuitBreakerListener()
    ]
)

class CircuitBreakerListener:
    def state_change(self, cb, old_state, new_state):
        if new_state == 'open':
            logging.error(f"Circuit breaker {cb.name} opened")
            telemetry.track_circuit_breaker_opened(cb.name)
        elif new_state == 'half_open':
            logging.info(f"Circuit breaker {cb.name} half-open")
            telemetry.track_circuit_breaker_half_open(cb.name)
        elif new_state == 'closed':
            logging.info(f"Circuit breaker {cb.name} recovered")
            telemetry.track_circuit_breaker_closed(cb.name)

# Usage with async
async def call_external_api():
    try:
        response = await breaker.call(
            fetch_from_api,
            'https://api.external.com/data'
        )
        return response
    except CircuitBreakerListener:
        return {'error': 'Service temporarily unavailable'}

# Apply to function
@breaker
async def fetch_from_api(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()
```

---

## 7. Circuit Breaker Telemetry

### 7.1 Metrics to Track

```
Circuit breaker state transitions:
  - breaker_opened{service="external_api"}
  - breaker_half_open{service="external_api"}
  - breaker_closed{service="external_api"}
  - breaker_state{service="external_api", state="open|closed|half_open"}

Circuit breaker events:
  - fast_failures{service="external_api"} (requests rejected while open)
  - probe_attempts{service="external_api"} (half-open probe requests)
  - probe_successes{service="external_api"} (successful probes)
```

### 7.2 Alerting Rules

```yaml
alerts:
  - name: CircuitBreakerOpen
    condition: breaker_state{state="open"} > 0
    duration: 1m
    severity: CRITICAL
    action: "Investigate downstream service health"
    
  - name: CircuitBreakerFrequentOpen
    condition: |
      rate(breaker_opened[5m]) > 0.1  # Opens more than 6x per hour
    duration: 5m
    severity: WARNING
    action: "Review failure patterns, increase thresholds if needed"
```

---

## 8. Testing Circuit Breaker

### 8.1 Unit Test - Open State

```csharp
[TestMethod]
public async Task CircuitBreaker_OpensAfterThreshold()
{
    var failureCount = 0;
    
    var policy = Policy
        .Handle<Exception>()
        .CircuitBreakerAsync(
            handledEventsAllowedBeforeBreaking: 3,
            durationOfBreak: TimeSpan.FromSeconds(1)
        );
    
    // Trigger failures
    for (int i = 0; i < 5; i++)
    {
        try
        {
            await policy.ExecuteAsync(async () =>
            {
                failureCount++;
                throw new Exception("Failure");
            });
        }
        catch (BrokenCircuitException)
        {
            // Expected: circuit breaker rejects request
            Assert.IsTrue(policy.CircuitState == CircuitState.Open);
        }
    }
}
```

### 8.2 Integration Test - Failure Injection

```typescript
describe('Circuit breaker', () => {
  it('should open after 5 consecutive failures', async () => {
    const breaker = new CircuitBreaker(async () => {
      throw new Error('Service unavailable');
    }, {
      timeout: 5000,
      errorThresholdPercentage: 50,
      resetTimeout: 10000
    });

    for (let i = 0; i < 5; i++) {
      try {
        await breaker.fire();
      } catch (e) {
        // Expected
      }
    }

    expect(breaker.opened).toBe(true);
    
    // 6th request should fail immediately
    const start = Date.now();
    try {
      await breaker.fire();
    } catch (e) {
      const elapsed = Date.now() - start;
      expect(elapsed).toBeLessThan(100);  // < 100ms (fast fail)
    }
  });
});
```

---

## 9. Success Criteria

- [ ] Circuit breaker thresholds defined for all service types
- [ ] Open circuit rejects requests fast (<10ms)
- [ ] Transitions emit metrics/events
- [ ] Alerting configured for state changes
- [ ] Recovery to half-open implemented
- [ ] Unit/integration tests validate behavior
- [ ] Documentation published for engineers

---

## References

- Netflix Hystrix (archived): https://github.com/Netflix/Hystrix
- Polly Circuit Breaker: https://github.com/App-vNext/Polly
- AWS Systems Manager OpsCenter: https://docs.aws.amazon.com/systems-manager/latest/userguide/

**Next:** [RES-4: Half-Open Recovery Policy](res-half-open-recovery.md)
