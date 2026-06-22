# RES-4: Half-Open Recovery Policy

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, platform architects

---

## 1. Overview

This document defines half-open circuit breaker behavior for testing downstream service recovery before allowing normal traffic.

**Principles:**
- Half-open probes test recovery without risking normal traffic
- Only successful probes close the circuit
- Failed probes reopen the circuit for longer duration
- Probes use same endpoint as normal traffic

---

## 2. Half-Open State

### 2.1 Transition Timeline

```
T+0: Circuit OPEN (service failing)
     Requests rejected fast

T+60s: Timeout expires
       Circuit enters HALF-OPEN
       Probe request sent (1st real request allowed)

T+60s+10ms: Probe succeeds
            Circuit CLOSES
            Normal traffic resumes
            
OR

T+60s+10ms: Probe fails
            Circuit reopens
            Back to OPEN state
            Reset timeout doubled to 120s
```

### 2.2 Configuration

| Setting | Value | Purpose |
|---|---|---|
| **Probe Timeout** | 10 seconds | Probe has same timeout as normal requests |
| **Probe Count** | 1 | Single successful probe to close circuit |
| **Probe Cadence** | Every 30s | Try recovery every 30s while in half-open |
| **Reopen Delay** | Double previous | Exponential backoff if probe fails |
| **Max Reopen Delay** | 600s (10 min) | Cap exponential growth |

---

## 3. Probe Strategy

### 3.1 Probe Selection

```
✅ Good probes (use for half-open):
  - GET /health
  - GET /status
  - GET /metrics (lightweight)
  - HEAD request (cheaper than GET)

❌ Bad probes (don't use):
  - POST /create (state-changing)
  - DELETE /resource (destructive)
  - GET with side effects (not idempotent)
```

### 3.2 Probe Success Criteria

```
Probe succeeds if:
  - Response received within timeout
  - Status code in 2xx range
  - Body parses without error
  - Response indicates service is healthy
  
Examples:
  ✅ GET /health → {"status": "healthy"}
  ✅ GET /health → {"status": "ok"}
  ✅ HEAD / → 200 OK
  ❌ GET /health → timeout
  ❌ GET /health → 503 Service Unavailable
  ❌ GET /health → {"status": "degraded"}
```

---

## 4. Half-Open Recovery Flow

### 4.1 Example: Database Connection Recovery

```
T+0: Database connection fails
     Circuit opens
     All queries rejected fast

T+60s: Circuit half-open
       Send probe: SELECT 1;
       ↓
       Timeout expired (10s), no response
       → Probe fails
       → Circuit reopens
       → Wait 120s before next probe

T+180s: Next probe
        Send probe: SELECT 1;
        ↓
        Response: 1 row
        → Probe succeeds
        → Circuit closes
        → Normal queries resume
```

### 4.2 Example: External API Recovery

```
T+0: API returns 500
     Circuit opens after 5 consecutive 500s

T+30s: Circuit half-open
       Probe: GET /health?lightweight=true
       Response: 200 {"status": "recovering"}
       → Still unhealthy
       → Probe fails
       → Circuit reopens
       → Wait 60s before next probe

T+90s: Probe: GET /health?lightweight=true
       Response: 200 {"status": "healthy"}
       → Probe succeeds
       → Circuit closes
       → Normal requests resume
```

---

## 5. Implementation

### 5.1 C# / .NET Implementation

```csharp
using Polly;
using Polly.CircuitBreaker;

// Circuit breaker with half-open probe
var circuitBreakerPolicy = Policy
    .Handle<HttpRequestException>()
    .OrResult<HttpResponseMessage>(r => 
        r.StatusCode == System.Net.HttpStatusCode.InternalServerError ||
        r.StatusCode == System.Net.HttpStatusCode.ServiceUnavailable)
    .CircuitBreakerAsync<HttpResponseMessage>(
        handledEventsAllowedBeforeBreaking: 5,
        durationOfBreak: TimeSpan.FromSeconds(30),
        onBreak: (outcome, duration) =>
        {
            _logger.LogError("Circuit breaker opened for {Duration}s", 
                duration.TotalSeconds);
            _telemetry.TrackEvent("CircuitBreakerOpened");
        },
        onReset: () =>
        {
            _logger.LogInformation("Circuit breaker closed");
            _telemetry.TrackEvent("CircuitBreakerClosed");
        },
        onHalfOpen: async () =>
        {
            _logger.LogInformation("Circuit breaker half-open, sending probe");
            
            // Send probe request
            try
            {
                using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
                var probeResponse = await _httpClient.GetAsync(
                    "/health",
                    cts.Token
                );
                
                if (probeResponse.IsSuccessStatusCode)
                {
                    _logger.LogInformation("Probe succeeded, closing circuit");
                    _telemetry.TrackEvent("ProbeSucceeded");
                }
                else
                {
                    _logger.LogWarning("Probe failed with status {StatusCode}",
                        probeResponse.StatusCode);
                    _telemetry.TrackEvent("ProbeFailed");
                }
            }
            catch (OperationCanceledException)
            {
                _logger.LogWarning("Probe timed out");
                _telemetry.TrackEvent("ProbeTimedOut");
            }
        }
    );
```

### 5.2 TypeScript / Node.js Implementation

```typescript
import CircuitBreaker from 'opossum';

class HealthProbeManager {
  private breaker: CircuitBreaker;
  private openDuration = 30000;  // Start with 30s
  private maxOpenDuration = 600000;  // Max 10 minutes

  constructor(private httpClient: HttpClient) {
    this.breaker = new CircuitBreaker(
      this.executeRequest.bind(this),
      {
        timeout: 10000,
        errorThresholdPercentage: 50,
        resetTimeout: this.openDuration,
        name: 'ExternalApi'
      }
    );

    this.breaker.on('halfOpen', () => this.sendProbe());
    this.breaker.on('open', () => this.onCircuitOpened());
    this.breaker.on('close', () => this.onCircuitClosed());
  }

  private async sendProbe(): Promise<void> {
    try {
      const response = await this.httpClient.get('/health', {
        timeout: 10000
      });

      if (response.status === 200 && response.data.status === 'healthy') {
        console.log('Probe succeeded, circuit closing');
        this.telemetry.trackEvent('ProbeSucceeded');
        // Circuit will auto-close on next successful request
      } else {
        console.warn('Probe returned unhealthy status:', response.data.status);
        this.telemetry.trackEvent('ProbeUnhealthy');
        throw new Error('Service unhealthy');
      }
    } catch (error) {
      console.error('Probe failed:', error.message);
      this.telemetry.trackEvent('ProbeFailed');
      
      // Double the open duration, cap at max
      this.openDuration = Math.min(
        this.openDuration * 2,
        this.maxOpenDuration
      );
      
      // Update reset timeout
      this.breaker.resetTimeout = this.openDuration;
      throw error;
    }
  }

  private async executeRequest(url: string): Promise<any> {
    return this.httpClient.get(url, { timeout: 10000 });
  }

  private onCircuitOpened(): void {
    console.error('Circuit breaker opened');
    this.telemetry.trackEvent('CircuitOpened', {
      nextProbeIn: this.openDuration
    });
  }

  private onCircuitClosed(): void {
    console.log('Circuit breaker closed, traffic resumed');
    this.telemetry.trackEvent('CircuitClosed');
    // Reset open duration to initial value
    this.openDuration = 30000;
  }
}
```

### 5.3 Python Implementation

```python
import asyncio
import logging
from datetime import datetime
from typing import Optional

class HalfOpenProber:
    def __init__(
        self,
        http_client,
        initial_open_duration: int = 30,
        max_open_duration: int = 600
    ):
        self.http_client = http_client
        self.open_duration = initial_open_duration
        self.max_open_duration = max_open_duration
        self.circuit_state = 'closed'
        self.last_probe_time: Optional[datetime] = None
    
    async def send_probe(self) -> bool:
        """
        Send health check probe.
        Returns True if probe succeeds (circuit should close),
        False if probe fails (circuit should reopen).
        """
        try:
            logging.info('Sending health probe')
            response = await asyncio.wait_for(
                self.http_client.get('/health'),
                timeout=10.0
            )
            
            if response.status == 200:
                health_data = await response.json()
                if health_data.get('status') == 'healthy':
                    logging.info('Probe succeeded, closing circuit')
                    self._on_probe_success()
                    return True
                else:
                    logging.warning(
                        f"Probe unhealthy status: {health_data.get('status')}"
                    )
                    self._on_probe_failed()
                    return False
            else:
                logging.warning(f"Probe returned status {response.status}")
                self._on_probe_failed()
                return False
                
        except asyncio.TimeoutError:
            logging.error('Probe timed out')
            self._on_probe_failed()
            return False
        except Exception as e:
            logging.error(f'Probe failed: {str(e)}')
            self._on_probe_failed()
            return False
    
    def _on_probe_success(self):
        """Handle successful probe."""
        self.circuit_state = 'closed'
        self.open_duration = 30  # Reset to initial
        self.last_probe_time = datetime.now()
    
    def _on_probe_failed(self):
        """Handle failed probe."""
        # Double open duration, capped at max
        self.open_duration = min(
            self.open_duration * 2,
            self.max_open_duration
        )
        logging.warning(
            f"Probe failed, next probe in {self.open_duration}s"
        )
        self.last_probe_time = datetime.now()
    
    async def monitor_half_open(self):
        """Continuously check half-open state and send probes."""
        while True:
            if self.circuit_state == 'half_open':
                await self.send_probe()
            await asyncio.sleep(self.open_duration)
```

---

## 6. Half-Open Telemetry

### 6.1 Metrics

```
Circuit breaker half-open events:
  - half_open_probes_sent{service="booking_db"}
  - half_open_probes_succeeded{service="booking_db"}
  - half_open_probes_failed{service="booking_db"}
  - circuit_closed_from_half_open{service="booking_db"}
  - circuit_reopened_from_half_open{service="booking_db"}
```

### 6.2 Events to Emit

```
When entering half-open:
  event: "CircuitHalfOpen"
  service: "external_api"
  timestamp: <ISO8601>
  nextProbeIn: 30000

When probe succeeds:
  event: "ProbeSucceeded"
  service: "external_api"
  probeLatencyMs: 45
  timestamp: <ISO8601>

When probe fails:
  event: "ProbeFailed"
  service: "external_api"
  reason: "timeout|unhealthy|error"
  nextProbeIn: 60000
  timestamp: <ISO8601>

When circuit closes:
  event: "CircuitClosed"
  service: "external_api"
  openDurationMs: 31000
  timestamp: <ISO8601>
```

---

## 7. Testing Half-Open Recovery

### 7.1 Unit Test - Probe Success Closes Circuit

```csharp
[TestMethod]
public async Task HalfOpen_SuccessfulProbe_ClosesCircuit()
{
    int probeAttempts = 0;
    
    Func<Task<HttpResponseMessage>> request = async () =>
    {
        probeAttempts++;
        if (probeAttempts == 1)
            throw new HttpRequestException();  // Fail first request
        return new HttpResponseMessage(System.Net.HttpStatusCode.OK);
    };
    
    var policy = Policy
        .Handle<HttpRequestException>()
        .CircuitBreakerAsync<HttpResponseMessage>(
            handledEventsAllowedBeforeBreaking: 1,
            durationOfBreak: TimeSpan.FromSeconds(1)
        );
    
    // First request fails, opens circuit
    try { await policy.ExecuteAsync(request); }
    catch { }
    
    Assert.AreEqual(CircuitState.Open, policy.CircuitState);
    
    // Wait for half-open timeout
    await Task.Delay(1100);
    
    Assert.AreEqual(CircuitState.HalfOpen, policy.CircuitState);
    
    // Next request succeeds, should close circuit
    await policy.ExecuteAsync(request);
    
    Assert.AreEqual(CircuitState.Closed, policy.CircuitState);
    Assert.AreEqual(2, probeAttempts);
}
```

### 7.2 Integration Test - Failed Probe Reopens

```typescript
describe('Half-open recovery', () => {
  it('should reopen circuit if probe fails', async () => {
    let callCount = 0;
    const breaker = new CircuitBreaker(async () => {
      callCount++;
      if (callCount <= 5) {
        throw new Error('Service down');
      }
      throw new Error('Still down'); // Probe will fail
    }, {
      errorThresholdPercentage: 50,
      resetTimeout: 1000,
      timeout: 5000
    });

    // Trigger failures to open circuit
    for (let i = 0; i < 5; i++) {
      try { await breaker.fire(); } catch (e) { }
    }
    expect(breaker.opened).toBe(true);

    // Wait for half-open
    await new Promise(resolve => setTimeout(resolve, 1100));
    expect(breaker.halfOpen).toBe(true);

    // Send probe request (will fail)
    try {
      await breaker.fire();
    } catch (e) {
      // Expected
    }

    // Circuit should reopen
    expect(breaker.opened).toBe(true);
    expect(breaker.resetTimeout).toBe(2000);  // Doubled
  });
});
```

---

## 8. Success Criteria

- [ ] Half-open state transitions after open duration expires
- [ ] Probes use safe, idempotent endpoints
- [ ] Successful probes close the circuit
- [ ] Failed probes reopen circuit with exponential backoff
- [ ] Probe duration tracked and alerted on
- [ ] Metrics emit for all state transitions
- [ ] Unit/integration tests validate behavior
- [ ] Documentation published for engineers

---

## References

- Polly Circuit Breaker: https://github.com/App-vNext/Polly
- Opossum (Node.js): https://github.com/nodeshift/opossum
- Circuit Breaker Pattern: https://martinfowler.com/bliki/CircuitBreaker.html

**Next:** [FALL-1: Non-Critical Dependency Fallback Guidelines](fall-fallback-guidelines.md)
