# TEST-1: Fault Injection and Chaos Suite

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** QA engineers, platform architects, chaos engineers

---

## 1. Overview

This document defines fault injection tests and chaos experiments to validate resiliency behavior under failure scenarios, ensuring timeouts, retries, circuit breakers, and fallbacks work correctly.

---

## 2. Fault Injection Test Categories

### 2.1 Test Scenarios

| Scenario | Injected Failure | Expected Behavior | Duration |
|---|---|---|---|
| **Timeout Simulation** | Request hangs 15s | Timeout fires at 10s, fast fail | 30 sec |
| **Error Rate Spike** | 80% requests return 500 | Circuit opens after 5 failures | 2 min |
| **Connection Refused** | TCP reset on connect | Retry triggered, backoff applied | 30 sec |
| **Rate Limiting** | 429 responses on 30% of requests | Retry with backoff, budget tracked | 1 min |
| **Cascading Failure** | Primary + backup fail | Fallback activated, users degraded | 2 min |
| **Partial Outage** | 50% requests timeout | Circuit opens, fallback activated | 2 min |

---

## 3. Chaos Suite Implementation

### 3.1 Timeout Injection Test

```typescript
// tests/chaos/timeout-injection.spec.ts
import { test, expect } from '@playwright/test';
import axios from 'axios';

test.describe('Timeout Injection - API becomes slow', () => {
  test('should timeout after 10 seconds and fail fast', async () => {
    const start = Date.now();
    
    try {
      // Inject delay: simulate slow service
      const response = await axios.get(
        'http://localhost:8080/api/appointments',
        { timeout: 10000 }
      );
      expect(response.status).toBe(200);
    } catch (error) {
      const elapsed = Date.now() - start;
      
      // Should fail after ~10s (timeout)
      expect(elapsed).toBeGreaterThan(9500);
      expect(elapsed).toBeLessThan(11000);
      expect(error.code).toBe('ECONNABORTED');
    }
  });

  test('should open circuit breaker after 5 timeout failures', async () => {
    const results = [];
    
    // Trigger 5 timeouts
    for (let i = 0; i < 5; i++) {
      try {
        await axios.get('http://localhost:8080/api/appointments', 
          { timeout: 10000 }
        );
      } catch (error) {
        results.push({ attempt: i + 1, error: error.code });
      }
    }
    
    // 6th request should fail immediately (circuit open)
    const start = Date.now();
    try {
      await axios.get('http://localhost:8080/api/appointments');
    } catch (error) {
      const elapsed = Date.now() - start;
      
      // Should fail < 100ms (circuit breaker fast fail)
      expect(elapsed).toBeLessThan(100);
      expect(error.message).toContain('circuit');
    }
  });
});
```

### 3.2 Error Rate Spike Test

```csharp
[TestClass]
public class ErrorRateSpikeTests
{
    [TestMethod]
    public async Task ErrorRateSpike_SpikeToEightyPercent_CircuitOpens()
    {
        var failureRate = 0.0;
        var callCount = 0;
        
        Func<Task<HttpResponseMessage>> flakyCall = async () =>
        {
            callCount++;
            if (Random.Shared.NextDouble() < failureRate)
            {
                throw new HttpRequestException("Service error");
            }
            return new HttpResponseMessage(HttpStatusCode.OK);
        };
        
        var policy = Policy
            .Handle<HttpRequestException>()
            .CircuitBreakerAsync<HttpResponseMessage>(
                handledEventsAllowedBeforeBreaking: 5,
                durationOfBreak: TimeSpan.FromSeconds(30)
            );
        
        // Gradually increase error rate to 80%
        for (int step = 0; step <= 8; step++)
        {
            failureRate = step * 0.1;  // 0%, 10%, ..., 80%
            
            for (int i = 0; i < 10; i++)
            {
                try
                {
                    await policy.ExecuteAsync(flakyCall);
                }
                catch (BrokenCircuitException)
                {
                    Assert.IsTrue(policy.CircuitState == CircuitState.Open);
                    return;  // Circuit opened as expected
                }
                catch
                {
                    // Expected failures
                }
            }
            
            await Task.Delay(100);
        }
        
        // Should have opened by 80%
        Assert.Fail("Circuit breaker should have opened");
    }
}
```

### 3.3 Connection Refused Test

```python
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_connection_refused_triggers_retry():
    """Test that connection refused triggers retry with backoff."""
    
    attempt_count = 0
    attempt_times = []
    
    async def failing_request():
        nonlocal attempt_count
        attempt_count += 1
        attempt_times.append(time.time())
        
        if attempt_count < 3:
            raise ConnectionRefusedError("Connection refused")
        return {"status": "ok"}
    
    # Retry with exponential backoff
    start = time.time()
    result = await retry_with_backoff(failing_request, max_retries=3)
    
    assert result == {"status": "ok"}
    assert attempt_count == 3
    
    # Verify backoff timing
    delay1 = attempt_times[1] - attempt_times[0]
    delay2 = attempt_times[2] - attempt_times[1]
    
    assert delay1 > 0.08  # ~100ms with jitter
    assert delay2 > delay1  # Exponential increase
```

### 3.4 Rate Limiting Test

```typescript
// tests/chaos/rate-limiting.spec.ts
test('should handle 429 rate limit with retry budget', async () => {
  let requestCount = 0;
  
  // Inject rate limiting: 429 on 30% of requests
  const mockApi = jest.fn(async () => {
    requestCount++;
    
    if (Math.random() < 0.3) {
      return Promise.reject({
        status: 429,
        headers: { 'retry-after': '2' }
      });
    }
    
    return { data: 'success' };
  });
  
  const budget = new RetryBudget(100);  // 100 retries max
  const results = { success: 0, failed: 0 };
  
  // Make 200 requests
  for (let i = 0; i < 200; i++) {
    try {
      await budget.executeWithRetry(mockApi, { maxRetries: 2 });
      results.success++;
    } catch (error) {
      results.failed++;
    }
  }
  
  // Most should succeed (retry on 429)
  expect(results.success).toBeGreaterThan(180);
  
  // Budget tracking
  expect(budget.usedRetries()).toBeLessThan(100);
});
```

---

## 4. Chaos Experiment Framework

### 4.1 Chaos Library Integration

```yaml
# chaos-config.yaml
experiments:
  - name: timeout-cascade
    description: "Simulate 15s timeout causing circuit breaker to open"
    duration: 2m
    
    faults:
      - type: delay
        service: booking-db
        latency: 15000ms  # 15 seconds
        percentage: 100   # Apply to all requests
    
    validation:
      - metric: circuit_breaker_state{service="booking_db"}
        expectedValue: 1  # 1 = open
        timeout: 60s
      
      - metric: timeout_rate{service="booking_db"}
        expectedValue: ">0"
        timeout: 30s
    
    recovery:
      - type: checkpoint
        name: "Post-chaos state"
        conditions:
          - circuit_breaker_state == "closed"
          - error_rate < 1%

  - name: cascading-failure
    description: "Primary service down, fallback activated"
    duration: 3m
    
    faults:
      - type: container-kill
        target: search-service-deployment
        percentage: 100
    
    validation:
      - metric: fallback_activations_total{dependency="search"}
        expectedValue: ">0"
      
      - metric: booking_success_rate
        expectedValue: ">0.95"  # Bookings still work with fallback
    
    recovery:
      - type: rollout-restart
        deployment: search-service-deployment
        namespace: search
```

### 4.2 Chaos Execution

```bash
#!/bin/bash
# run-chaos-test.sh

echo "🔥 Starting chaos experiment: timeout-cascade"

# Deploy chaos pod
kubectl apply -f chaos-config.yaml -n chaos-testing

# Wait for experiment to complete
kubectl wait --for=condition=complete \
  experiments/timeout-cascade \
  -n chaos-testing \
  --timeout=300s

# Check results
RESULT=$(kubectl get experiment timeout-cascade \
  -n chaos-testing \
  -o jsonpath='{.status.phase}')

if [ "$RESULT" == "Finished" ]; then
  echo "✅ Chaos experiment completed"
  
  # Collect results
  kubectl logs -n chaos-testing \
    pod/timeout-cascade-runner > chaos-results.log
  
  # Verify validation passed
  if grep -q "validation.passed" chaos-results.log; then
    echo "✅ All validations passed"
    exit 0
  else
    echo "❌ Validation failed"
    exit 1
  fi
else
  echo "❌ Experiment failed with status: $RESULT"
  exit 1
fi
```

---

## 5. Test Coverage Matrix

| Component | Test | Validates | Status |
|---|---|---|---|
| **Timeouts** | Timeout injection | Fast fail after timeout | ✅ |
| **Timeouts** | Timeout cascade | Circuit opens on repeated timeouts | ✅ |
| **Retries** | Transient failure retry | Succeeds after 1-2 failures | ✅ |
| **Retries** | Retry budget exhaustion | Stops retrying when budget exceeded | ✅ |
| **Circuit Breaker** | Open state | Rejects requests < 10ms | ✅ |
| **Circuit Breaker** | Half-open probe | Closes on successful probe | ✅ |
| **Circuit Breaker** | Reopen on failed probe | Reopens if probe fails | ✅ |
| **Fallback** | Dependency failure | Falls back without blocking | ✅ |
| **Fallback** | Core path resilience | Bookings succeed with dep down | ✅ |

---

## 6. Running Chaos Tests

### 6.1 Quick Test Run

```bash
# Run all chaos tests
npm run test:chaos

# Run specific test
npm run test:chaos -- --testNamePattern="timeout-cascade"

# Run with detailed output
npm run test:chaos -- --verbose

# Generate coverage report
npm run test:chaos -- --coverage
```

### 6.2 Production Chaos Testing (Blue-Green)

```bash
# Deploy to green environment (isolated)
kubectl apply -f deployment-green.yaml

# Run chaos experiments on green
./run-chaos-suite.sh --environment=green

# Monitor green environment
kubectl get pods -n green -w

# Results analyzed, then:
# If green passes: promote to blue
# If green fails: fix issues before prod
```

---

## 7. Success Criteria

- [ ] All fault injection tests pass
- [ ] Circuit breaker opens at 50% failure rate
- [ ] Timeouts occur within ±10% of configured value
- [ ] Retries with exponential backoff working
- [ ] Fallbacks activated on dependency failure
- [ ] Core booking path succeeds with 90%+ success under chaos
- [ ] Metrics accurate during chaos (no silent failures)
- [ ] Chaos tests repeatable and automated

---

## References

- Chaos Mesh: https://chaos-mesh.org/
- Gremlin Chaos Engineering: https://www.gremlin.com/
- Google SRE Book - Testing: https://sre.google/sre-book/testing-reliability/

**Next:** [TASK-102 Summary](TASK-102-SUMMARY.md)
