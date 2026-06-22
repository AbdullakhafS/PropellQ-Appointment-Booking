# RES-2: Retry Strategy with Budget Controls

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, platform architects

---

## 1. Overview

This document defines retry behavior with exponential backoff, jitter, and retry budgets to handle transient failures while preventing retry storms that amplify outages.

**Principles:**
- Transient failures are retried with exponential backoff
- Jitter prevents thundering herd
- Retry budget prevents retry amplification
- Non-idempotent operations don't retry

---

## 2. Retry Strategy

### 2.1 Exponential Backoff with Jitter

```
Attempt 1: Immediate (0ms)
Attempt 2: 100ms + jitter(±50%)   = 50-150ms
Attempt 3: 200ms + jitter(±50%)   = 100-300ms
Attempt 4: 400ms + jitter(±50%)   = 200-600ms

Total: ~1.5 seconds across 4 attempts

Formula:
  delay = min(max_delay, base_delay * 2^attempt) + jitter
  jitter = random(-delay * 0.5, delay * 0.5)
```

### 2.2 Retry Matrix by Failure Type

| Failure Type | Retryable | Max Retries | Backoff | Reason |
|---|---|---|---|---|
| **Timeout** | ✅ Yes | 3 | Exponential | Transient network latency |
| **DNS Error** | ✅ Yes | 2 | Exponential | DNS cache may update |
| **Connection Refused** | ✅ Yes | 2 | Exponential | Service starting |
| **5xx Server Error** | ✅ Yes | 3 | Exponential | Transient server issue |
| **429 Rate Limited** | ✅ Yes | 5 | Exponential | Wait for rate limit reset |
| **4xx Client Error** | ❌ No | 0 | N/A | Permanent, won't fix |
| **Database Deadlock** | ✅ Yes | 3 | Exponential | Lock may clear |
| **Database Timeout** | ✅ Yes | 2 | Exponential | Query may succeed |
| **Auth Failure** | ❌ No | 0 | N/A | Token invalid, won't fix |
| **Not Found** | ❌ No | 0 | N/A | Resource doesn't exist |

---

## 3. Retry Budget

### 3.1 Budget Model

```
Daily Budget: 1000 total retry attempts
Per Service: 100 retries max
Per Endpoint: 10 retries max

When budget exceeded:
  - Stop retrying
  - Emit alert
  - Escalate to circuit breaker
```

### 3.2 Budget Calculation

```
Service A makes 1M requests/day:
  - Expected failures: 0.1% = 1,000 requests
  - 3 retries each = 3,000 total attempts
  - Budget allocated: 3,500 (with buffer)
  
If failures spike to 1%:
  - Total retries: 30,000
  - Exceeds budget: 3,500
  - Circuit breaker opens
  - Returns fast failure instead of retrying
```

### 3.3 Budget Allocation per Environment

| Environment | Total Daily Budget | Per Service | Per Endpoint |
|---|---|---|---|
| **Production** | 10,000 | 500 | 50 |
| **Staging** | 5,000 | 250 | 25 |
| **Development** | Unlimited | Unlimited | Unlimited |

---

## 4. Non-Retryable Operations

### 4.1 Idempotency Classification

```
✅ SAFE TO RETRY (idempotent):
  - GET /appointments/{id}
  - POST /appointments/{id}/confirm (second attempt is no-op)
  - DELETE /user/{id} (already deleted is success)

❌ UNSAFE TO RETRY (non-idempotent):
  - POST /payments (creates duplicate charge)
  - POST /appointments (creates duplicate appointment)
  - PUT /user/{id}/credits (increments twice)
```

### 4.2 Idempotency Keys

```
For unsafe operations, use idempotency key:

POST /payments
{
  "idempotencyKey": "user-123-payment-456",
  "amount": 100,
  "currency": "USD"
}

Server: If key already processed, return cached response
```

### 4.3 Allowlist Pattern

```csharp
// Only retry if endpoint is in allowlist
private static readonly HashSet<string> RetryableEndpoints = new()
{
    "/api/appointments",
    "/api/users",
    "/api/slots"
};

private bool IsRetryable(string endpoint, HttpStatusCode statusCode)
{
    // Only retry GET requests
    if (httpMethod != "GET") return false;
    
    // Only retry 5xx and timeout errors
    if (statusCode >= 400 && statusCode < 500) return false;
    
    // Only retry if endpoint in allowlist
    return RetryableEndpoints.Contains(endpoint);
}
```

---

## 5. Implementation

### 5.1 C# / .NET Implementation

```csharp
// Using Polly
var policy = Policy
    .Handle<HttpRequestException>()
    .Or<TimeoutRejectedException>()
    .OrResult<HttpResponseMessage>(r => 
        r.StatusCode == System.Net.HttpStatusCode.RequestTimeout ||
        (int)r.StatusCode >= 500)
    .WaitAndRetryAsync(
        retryCount: 3,
        sleepDurationProvider: attempt =>
        {
            var baseDelay = Math.Pow(2, attempt);
            var jitter = Random.Shared.NextDouble() - 0.5;
            var totalMs = baseDelay * 100 * (1 + jitter);
            return TimeSpan.FromMilliseconds(Math.Max(0, totalMs));
        },
        onRetry: (outcome, timespan, retryCount, context) =>
        {
            _logger.LogWarning(
                "Retry {RetryCount} after {DelayMs}ms for {Operation}",
                retryCount,
                timespan.TotalMilliseconds,
                context["operation"]
            );
        }
    );

// Wrap with budget tracking
var budgetedPolicy = policy
    .WrapAsync(Policy.BulkheadAsync(
        maxParallelization: 100,
        maxQueuingActions: 1000
    ));

// Usage
var context = new Context { ["operation"] = "GetAppointment" };
var result = await budgetedPolicy.ExecuteAsync(
    ctx => _httpClient.GetAsync(url),
    context
);
```

### 5.2 TypeScript / Node.js Implementation

```typescript
import pRetry from 'p-retry';
import { AbortSignal } from 'abort-controller';

// Retry with exponential backoff
async function callWithRetry<T>(
  fn: () => Promise<T>,
  options?: {
    maxRetries?: number;
    minDelay?: number;
    maxDelay?: number;
  }
): Promise<T> {
  return pRetry(fn, {
    retries: options?.maxRetries ?? 3,
    minTimeout: options?.minDelay ?? 100,
    maxTimeout: options?.maxDelay ?? 5000,
    onFailedAttempt: (error) => {
      console.warn(
        `Attempt ${error.attemptNumber} failed. ${error.retriesLeft} retries left. Error: ${error.message}`
      );
    },
  });
}

// Custom retry logic with jitter
async function retryWithJitter<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3
): Promise<T> {
  let lastError: Error;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      
      if (attempt === maxRetries) break;
      
      const baseDelay = Math.pow(2, attempt) * 100;
      const jitter = (Math.random() - 0.5) * baseDelay;
      const delay = Math.max(0, baseDelay + jitter);
      
      console.warn(
        `Retry ${attempt + 1}/${maxRetries} after ${delay}ms: ${lastError.message}`
      );
      
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError;
}

// Usage
const appointment = await callWithRetry(
  () => api.get('/appointments/123'),
  { maxRetries: 3, minDelay: 100, maxDelay: 5000 }
);
```

### 5.3 Python Implementation

```python
import asyncio
import random
import logging
from functools import wraps
from typing import TypeVar, Callable, Any

T = TypeVar('T')

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 5.0
):
    """Decorator for retry with exponential backoff and jitter."""
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    if attempt == max_retries:
                        break
                    
                    # Exponential backoff with jitter
                    backoff = base_delay * (2 ** attempt)
                    jitter = random.uniform(-backoff * 0.5, backoff * 0.5)
                    delay = min(max_delay, max(0, backoff + jitter))
                    
                    logging.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed. "
                        f"Retrying after {delay:.2f}s: {str(e)}"
                    )
                    
                    await asyncio.sleep(delay)
            
            raise last_error
        
        return wrapper
    
    return decorator

# Usage
@retry_with_backoff(max_retries=3, base_delay=0.1, max_delay=5.0)
async def fetch_appointment(session, appointment_id: str):
    async with session.get(f'/appointments/{appointment_id}') as resp:
        if resp.status >= 400:
            raise Exception(f"HTTP {resp.status}")
        return await resp.json()
```

---

## 6. Budget Tracking and Alerts

### 6.1 Budget Metrics

```
Per service endpoint:
  - Retry count: total retries attempted
  - Budget used: retries / allocated budget
  - Alert threshold: 80% of budget
  - Critical threshold: 95% of budget
```

### 6.2 Alerting Rules

```yaml
alerts:
  - name: RetryBudgetExhausted
    condition: |
      retry_budget_used{service="booking"} > 0.95
    duration: 5m
    severity: CRITICAL
    action: "Escalate to on-call, open circuit breaker"
  
  - name: RetryBudgetWarning
    condition: |
      retry_budget_used{service="booking"} > 0.80
    duration: 1m
    severity: WARNING
    action: "Notify team, investigate failure spike"
```

---

## 7. Testing Retry Behavior

### 7.1 Unit Test

```csharp
[TestClass]
public class RetryTests
{
    [TestMethod]
    public async Task TransientFailure_RetriedWithBackoff()
    {
        var attempt = 0;
        var delays = new List<int>();
        var startTime = DateTime.UtcNow;
        
        Func<Task<string>> flakyCall = async () =>
        {
            attempt++;
            if (attempt < 3)
                throw new TimeoutException();
            return "Success";
        };
        
        var policy = Policy
            .Handle<TimeoutException>()
            .WaitAndRetryAsync(
                retryCount: 3,
                sleepDurationProvider: a => TimeSpan.FromMilliseconds(100 * a)
            );
        
        var result = await policy.ExecuteAsync(flakyCall);
        
        Assert.AreEqual("Success", result);
        Assert.AreEqual(3, attempt);
    }
}
```

### 7.2 Integration Test - Budget Exhaustion

```typescript
describe('Retry budget', () => {
  it('should stop retrying when budget exhausted', async () => {
    const budget = new RetryBudget(10);  // 10 retries max
    
    for (let i = 0; i < 12; i++) {
      try {
        await budget.executeWithRetry(async () => {
          throw new Error('Transient failure');
        });
      } catch (e) {
        // After 10 attempts, should stop retrying
        if (i > 10) {
          expect(budget.isExhausted()).toBe(true);
          expect((e as Error).message).toContain('budget exhausted');
        }
      }
    }
  });
});
```

---

## 8. Success Criteria

- [ ] Exponential backoff with jitter implemented
- [ ] Retry matrix defined for all failure types
- [ ] Retry budget tracking implemented
- [ ] Non-retryable operations identified
- [ ] Allowlist enforcement working
- [ ] Metrics and alerting configured
- [ ] Unit/integration tests validate retry behavior
- [ ] Documentation published for engineers

---

## References

- AWS Retry Strategy: https://docs.aws.amazon.com/general/latest/gr/api-retries.html
- Google SRE Book - Handling Overload: https://sre.google/books/
- Polly Retry Policy: https://github.com/App-vNext/Polly

**Next:** [RES-3: Circuit Breaker Open-State Policy](res-circuit-breaker-policy.md)
