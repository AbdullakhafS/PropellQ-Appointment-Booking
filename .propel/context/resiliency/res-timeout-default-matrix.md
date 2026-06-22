# RES-1: Timeout Default Matrix

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, platform architects

---

## 1. Overview

This document defines safe-by-default timeout values for different types of service calls, ensuring predictable failure modes and preventing resource exhaustion from hanging requests.

**Principles:**
- All calls have explicit timeouts
- Defaults apply when unspecified
- Overrides require documented justification
- Timeouts prevent cascade failures

---

## 2. Timeout Classification Matrix

### 2.1 Call Types and Default Timeouts

| Call Type | Example | Default Timeout | Min | Max | Rationale |
|---|---|---|---|---|---|
| **Internal Sync** | Service-to-service REST API | 5 seconds | 1s | 15s | LAN, minimal network latency |
| **Internal Async** | Message queue, event bus | 30 seconds | 10s | 60s | Processing time allowed |
| **Database Query** | PostgreSQL, direct connection | 10 seconds | 2s | 30s | Query execution + network |
| **Database Transaction** | Multi-query transaction | 30 seconds | 5s | 60s | Lock wait time + queries |
| **External API** | Third-party HTTP service | 10 seconds | 5s | 30s | Network + processing |
| **External Payment** | Payment gateway (Stripe, etc) | 20 seconds | 10s | 45s | Critical flow, longer window |
| **File Upload** | S3, blob storage | 60 seconds | 30s | 120s | Large file transfer |
| **Search Query** | Elasticsearch, Algolia | 5 seconds | 2s | 15s | Fast response expected |
| **Cache Lookup** | Redis, Memcached | 1 second | 500ms | 5s | Should be very fast |
| **Health Check** | Liveness probe | 2 seconds | 1s | 5s | Frequent, must be fast |

### 2.2 Timeout by Layer

```
Client → Load Balancer → Gateway → Service → Dependency
 ↓           ↓               ↓        ↓           ↓
3s         5s              10s       15s        10s (DB)
```

**Key pattern:** Each layer's timeout > downstream timeout + network overhead

---

## 3. Language-Specific Implementation

### 3.1 C# / .NET

```csharp
// HttpClient with timeout
var httpClient = new HttpClient()
{
    Timeout = TimeSpan.FromSeconds(10)  // RES-1 default for external API
};

// For specific requests
using (var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5)))
{
    var response = await httpClient.GetAsync(url, cts.Token);
}

// Database connection timeout
var connectionString = "Server=db;Database=booking;Connection Timeout=10;";
var connection = new SqlConnection(connectionString);

// EF Core query timeout
using (var db = new AppDbContext())
{
    db.Database.SetCommandTimeout(10);  // seconds
    var result = await db.Users.ToListAsync();
}

// Custom ResiliencyPolicy with timeout
var policy = Policy.TimeoutAsync<HttpResponseMessage>(
    TimeSpan.FromSeconds(10),
    timeoutStrategy: TimeoutStrategy.Optimistic  // Don't cancel on timeout
);
```

**Configuration:**
```json
{
  "Resiliency": {
    "TimeoutDefaults": {
      "InternalSync": "00:00:05",
      "DatabaseQuery": "00:00:10",
      "ExternalApi": "00:00:10",
      "CacheLookup": "00:00:01"
    }
  }
}
```

### 3.2 TypeScript / Node.js

```typescript
// Axios timeout
const client = axios.create({
  timeout: 10000  // 10 seconds for external API
});

// Fetch with AbortController
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 10000);

try {
  const response = await fetch(url, { signal: controller.signal });
} finally {
  clearTimeout(timeoutId);
}

// Database pool timeout
const pool = new Pool({
  connectionTimeoutMillis: 10000,
  idleTimeoutMillis: 30000,
  statement_timeout: 10000  // Query timeout
});

// Axios interceptor for automatic timeout
const createApiClient = (baseURL: string, timeoutMs: number = 10000) => {
  return axios.create({
    baseURL,
    timeout: timeoutMs
  });
};

// Usage
const externalApi = createApiClient('https://api.external.com', 10000);
const internalApi = createApiClient('http://internal-service:8080', 5000);
```

**Configuration:**
```yaml
resiliency:
  timeouts:
    internalSync: 5000      # 5 seconds
    databaseQuery: 10000    # 10 seconds
    externalApi: 10000      # 10 seconds
    cacheLookup: 1000       # 1 second
```

### 3.3 Python

```python
# Requests library
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

response = requests.get(url, timeout=10)  # seconds

# Database connection timeout
import psycopg2

conn = psycopg2.connect(
    "dbname=booking user=postgres host=localhost",
    connect_timeout=10
)

cursor = conn.cursor()
cursor.execute("SET statement_timeout = 10000")  # milliseconds

# SQLAlchemy
from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://user:password@localhost/booking',
    connect_args={"connect_timeout": 10},
    pool_pre_ping=True,  # Test connections before use
    echo_pool=True
)

# Async client with timeout
import asyncio
import aiohttp

async def fetch(session, url):
    timeout = aiohttp.ClientTimeout(total=10)
    async with session.get(url, timeout=timeout) as resp:
        return await resp.text()

async def main():
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        await fetch(session, 'http://example.com')
```

**Configuration:**
```python
# config.py
TIMEOUT_DEFAULTS = {
    'INTERNAL_SYNC': 5,
    'DATABASE_QUERY': 10,
    'EXTERNAL_API': 10,
    'CACHE_LOOKUP': 1,
}

# Usage
import httpx

async def call_external_api():
    timeout = httpx.Timeout(TIMEOUT_DEFAULTS['EXTERNAL_API'])
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.get('https://api.external.com')
```

---

## 4. Override Policy

### 4.1 When Overrides Are Permitted

**✅ Allowed with documentation:**
- Specific endpoint with proven slow behavior (documented with baseline)
- Batch operations requiring longer processing
- Large file uploads/downloads
- Known external API latency requirements

**❌ Not allowed:**
- Removing timeouts entirely
- Setting timeouts > 2x default without business case
- Different timeout per developer per implementation

### 4.2 Override Approval Process

```
1. Document reason: "Payment API requires 30s due to ..."
2. Show evidence: "Historical p99 latency: 25s"
3. Get code review approval: PR review required
4. Track in code comment:
   
   // Override: External payment API timeout 30s (not 10s default)
   // Reason: Payment processor requires up to 25s for validation
   // Approved by: @backend-lead (2026-06-22)
   // SLA: Review and revert if latency improves below 20s
```

### 4.3 Override Template

```csharp
/// <summary>
/// Custom timeout for payment provider API.
/// </summary>
/// <remarks>
/// OVERRIDE: 20 seconds (default: 10 seconds)
/// Reason: Payment Gateway requires up to 18s for fraud checks
/// Baseline: p99 latency 16.2s, p95 13.1s
/// Approved: @security-lead (2026-06-22)
/// Review date: 2026-09-22
/// </remarks>
private static readonly TimeSpan PaymentApiTimeout = TimeSpan.FromSeconds(20);
```

---

## 5. Timeout Monitoring

### 5.1 Timeout Metrics

```
Track per endpoint:
  - Count: number of timeouts
  - Rate: timeouts/minute
  - Trend: increasing/stable/decreasing
  - Threshold: alert if timeout rate > 1% of requests
```

### 5.2 Alerting Rules

```
ALERT if:
  - Timeout rate > 1% for any endpoint
  - Timeout rate increasing > 50% week-over-week
  - Timeout duration pattern change (e.g., all hitting max)
```

---

## 6. Testing Timeout Behavior

### 6.1 Unit Test Example

```csharp
[TestClass]
public class TimeoutTests
{
    [TestMethod]
    [ExpectedException(typeof(OperationCanceledException))]
    public async Task ExternalApiCall_Timeout_ThrowsAfter10Seconds()
    {
        var client = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
        var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        
        // Simulate slow endpoint
        var response = await client.GetAsync(
            "https://httpbin.org/delay/15",
            cts.Token
        );
    }
}
```

### 6.2 Integration Test

```typescript
describe('Timeout defaults', () => {
  it('database query should timeout after 10s', async () => {
    const query = `SELECT pg_sleep(15)`;
    
    const start = Date.now();
    await expect(
      db.query(query)
    ).rejects.toThrow('timeout');
    
    const elapsed = Date.now() - start;
    expect(elapsed).toBeGreaterThan(10000);
    expect(elapsed).toBeLessThan(11000);  // Should be ~10s
  });
});
```

---

## 7. Configuration Management

### 7.1 Environment-Based Timeouts

```yaml
# development.yml
resiliency:
  timeouts:
    externalApi: 30000  # More lenient for local testing

# production.yml
resiliency:
  timeouts:
    externalApi: 10000  # Strict
```

### 7.2 Dynamic Configuration

**Allow hot reloading of timeouts:**

```csharp
// Inject configuration
public class ApiClient
{
    private readonly IOptionsMonitor<TimeoutConfig> _config;
    
    public async Task<Response> CallExternalApi()
    {
        var timeout = _config.CurrentValue.ExternalApiTimeoutMs;
        using (var cts = new CancellationTokenSource(timeout))
        {
            return await _httpClient.GetAsync(url, cts.Token);
        }
    }
}
```

---

## 8. Success Criteria

- [ ] Timeout defaults defined for all call types
- [ ] Min/max bounds enforced in code
- [ ] Override approval process documented
- [ ] Implementation in all languages (C#, TypeScript, Python)
- [ ] Configuration examples provided
- [ ] Monitoring/alerting configured
- [ ] Unit/integration tests validate timeout behavior
- [ ] Documentation published for engineers

---

## References

- OWASP: Insecure Timeout - https://owasp.org/www-community/attacks/Timeout_attacks
- Polly Resilience Policy: https://github.com/App-vNext/Polly
- Node.js Timeout: https://nodejs.org/en/docs/guides/simple-profiling/

**Next:** [RES-2: Retry Strategy with Budget Controls](res-retry-strategy-budget.md)
