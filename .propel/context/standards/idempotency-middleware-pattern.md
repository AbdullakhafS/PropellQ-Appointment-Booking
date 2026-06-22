# MID-3: Idempotency Middleware Pattern

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Approvals:** Architecture Review (Pending)

---

## 1. Overview

This document establishes the idempotency pattern for write operations (POST, PUT, PATCH). It defines:
- Idempotency key extraction and validation
- Deduplication store contract and implementation options
- Replay behavior for idempotent operations
- Safe usage patterns and client guidance
- Operational considerations and monitoring

Idempotency ensures that retried write operations do not create duplicate state changes, which is critical for distributed systems with unreliable networks.

---

## 2. Idempotency Principles

### 2.1 What Is Idempotency?

An operation is idempotent if calling it multiple times with the same parameters produces the same result as calling it once.

**Idempotent Request (same result regardless of retries):**
```http
PUT /api/v1/appointments/apt-001
X-Idempotency-Key: abc-123-def-456

{"status": "CONFIRMED", "confirmedAt": "2026-06-22T14:30:00Z"}
```

Response 1 (first call): 200 OK with updated appointment
Response 2 (retry with same key): 200 OK with same appointment (no duplicate)

**Non-Idempotent Without Pattern (duplicate on retry):**
```http
POST /api/v1/appointments
(no X-Idempotency-Key header)

{"patientId": "pat-123", "scheduledTime": "2026-07-01T10:00:00Z"}
```

Response 1: 201 Created appointment-1
Response 2 (retry): 201 Created appointment-2 (DUPLICATE - BAD!)

---

## 3. Idempotency Header Standard

### 3.1 Idempotency Key Header

All idempotent operations MUST accept the `X-Idempotency-Key` header:

| Header | Format | Required | Example |
|--------|--------|----------|---------|
| `X-Idempotency-Key` | UUID v4 or alphanumeric string (max 255 chars) | Recommended | `abc-123-def-456` or `550e8400-e29b-41d4-a716-446655440000` |

### 3.2 Header Validation Rules

- Must be provided by client for write operations
- Must be unique per operation (not reused across different operations)
- Must be treated as case-sensitive
- Can be any string 1-255 characters (UUID or custom format)
- Server generates unique key if not provided (for idempotency tracking)

### 3.3 Idempotency Key Propagation

Client libraries SHOULD:
1. Generate or accept idempotency key from caller
2. Include in all retry attempts for same operation
3. Use same key across service-to-service calls for same operation

```
Client Request 1:
  POST /api/v1/appointments
  X-Idempotency-Key: abc-123-def-456
  Network timeout after 5 seconds

Client Request 2 (Retry):
  POST /api/v1/appointments
  X-Idempotency-Key: abc-123-def-456 (SAME KEY)
  Server recognizes duplicate and replays cached response
```

---

## 4. Idempotent Operations Scope

### 4.1 Operations Requiring Idempotency

These operations MUST support idempotency:

| Method | Path | Example | Rationale |
|--------|------|---------|-----------|
| POST | Create resource | `POST /api/v1/appointments` | Network may drop response; retry would create duplicate |
| PUT | Replace resource | `PUT /api/v1/appointments/{id}` | Network may drop response; retry should be safe |
| PATCH | Partial update | `PATCH /api/v1/appointments/{id}/status` | Network may drop response; retry should be safe |
| DELETE | Soft delete | `DELETE /api/v1/appointments/{id}` | Retry should be safe (idempotent by nature) |

### 4.2 Operations NOT Requiring Idempotency

GET and HEAD are already idempotent by nature (read-only).

---

## 5. Idempotency Middleware Contract

### 5.1 Middleware Interface

**C# Interface:**
```csharp
public interface IIdempotencyMiddleware
{
    /// <summary>
    /// Checks for previous result using idempotency key.
    /// If found, returns cached response. Otherwise, proceeds and caches result.
    /// </summary>
    Task InvokeAsync(HttpContext context, RequestDelegate next);
}

public interface IIdempotencyStore
{
    /// <summary>
    /// Retrieves previously stored response for idempotency key.
    /// </summary>
    Task<IdempotencyResult> GetAsync(string key, string tenantId);

    /// <summary>
    /// Stores response for idempotency key with TTL.
    /// </summary>
    Task StoreAsync(string key, string tenantId, IdempotencyResult result, TimeSpan ttl);

    /// <summary>
    /// Marks key as "in-progress" to prevent concurrent duplicate processing.
    /// </summary>
    Task LockAsync(string key, string tenantId, TimeSpan timeout);

    /// <summary>
    /// Releases in-progress lock.
    /// </summary>
    Task UnlockAsync(string key, string tenantId);
}

public class IdempotencyResult
{
    public int StatusCode { get; set; }
    public byte[] ResponseBody { get; set; }
    public Dictionary<string, string> ResponseHeaders { get; set; }
    public DateTime CreatedAt { get; set; }
    public bool Replayed { get; set; }
}
```

**TypeScript Interface:**
```typescript
export interface IdempotencyMiddleware {
  (
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void>;
}

export interface IdempotencyStore {
  get(key: string, tenantId: string): Promise<IdempotencyResult | null>;
  store(key: string, tenantId: string, result: IdempotencyResult, ttl: number): Promise<void>;
  lock(key: string, tenantId: string, timeout: number): Promise<void>;
  unlock(key: string, tenantId: string): Promise<void>;
}

export interface IdempotencyResult {
  statusCode: number;
  responseBody: Buffer;
  responseHeaders: Record<string, string>;
  createdAt: Date;
  replayed: boolean;
}
```

---

## 6. Middleware Implementation

### 6.1 Idempotency Middleware (C#)

```csharp
public class IdempotencyMiddleware : IIdempotencyMiddleware
{
    private readonly RequestDelegate _next;
    private readonly IIdempotencyStore _store;
    private readonly ILogger<IdempotencyMiddleware> _logger;
    private const string IDEMPOTENCY_KEY_HEADER = "X-Idempotency-Key";
    private const int DEFAULT_TTL_SECONDS = 86400; // 24 hours

    public IdempotencyMiddleware(RequestDelegate next, 
        IIdempotencyStore store,
        ILogger<IdempotencyMiddleware> logger)
    {
        _next = next;
        _store = store;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        // Idempotency only applies to write operations
        if (!IsIdempotentMethod(context.Request.Method))
        {
            await _next(context);
            return;
        }

        // Extract idempotency key
        var idempotencyKey = ExtractIdempotencyKey(context);

        if (string.IsNullOrEmpty(idempotencyKey))
        {
            // No idempotency key provided - generate and log warning
            idempotencyKey = Guid.NewGuid().ToString();
            _logger.LogWarning("No X-Idempotency-Key provided for {Method} {Path}. Generated: {Key}",
                context.Request.Method, context.Request.Path, idempotencyKey);
        }

        var tenantId = context.Items["AuthContext"] is AuthContext auth 
            ? auth.TenantId 
            : "system";

        // Check for previous result
        var cachedResult = await _store.GetAsync(idempotencyKey, tenantId);
        
        if (cachedResult != null)
        {
            _logger.LogInformation("Idempotent request replayed. Key: {Key}, TenantId: {TenantId}",
                idempotencyKey, tenantId);

            // Return cached response
            await ReturnCachedResponse(context, cachedResult);
            return;
        }

        // Attempt to lock key (prevent concurrent requests with same key)
        try
        {
            await _store.LockAsync(idempotencyKey, tenantId, TimeSpan.FromSeconds(30));
        }
        catch (LockTimeoutException)
        {
            _logger.LogWarning("Idempotency key lock timeout. Key: {Key}", idempotencyKey);
            
            // Return 409 Conflict - concurrent request with same key
            context.Response.StatusCode = 409;
            await context.Response.WriteAsJsonAsync(new
            {
                statusCode = 409,
                success = false,
                error = new
                {
                    code = "REQUEST_IN_PROGRESS",
                    message = "Another request with this idempotency key is in progress"
                }
            });
            return;
        }

        try
        {
            // Capture response to cache it
            var originalBody = context.Response.Body;
            using (var memoryStream = new MemoryStream())
            {
                context.Response.Body = memoryStream;

                // Process request
                await _next(context);

                // Cache successful responses (2xx status codes)
                if (context.Response.StatusCode >= 200 && context.Response.StatusCode < 300)
                {
                    memoryStream.Position = 0;
                    var responseBody = memoryStream.ToArray();

                    var result = new IdempotencyResult
                    {
                        StatusCode = context.Response.StatusCode,
                        ResponseBody = responseBody,
                        ResponseHeaders = context.Response.Headers
                            .ToDictionary(h => h.Key, h => h.Value.ToString()),
                        CreatedAt = DateTime.UtcNow,
                        Replayed = false
                    };

                    await _store.StoreAsync(idempotencyKey, tenantId, result, 
                        TimeSpan.FromSeconds(DEFAULT_TTL_SECONDS));

                    _logger.LogInformation("Idempotent response cached. Key: {Key}, StatusCode: {StatusCode}",
                        idempotencyKey, context.Response.StatusCode);
                }

                // Copy response to original body
                memoryStream.Position = 0;
                await memoryStream.CopyToAsync(originalBody);
            }

            context.Response.Body = originalBody;
        }
        finally
        {
            // Always release lock
            try
            {
                await _store.UnlockAsync(idempotencyKey, tenantId);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to unlock idempotency key: {Key}", idempotencyKey);
            }
        }
    }

    private bool IsIdempotentMethod(string method)
    {
        return method.In("POST", "PUT", "PATCH", "DELETE");
    }

    private string ExtractIdempotencyKey(HttpContext context)
    {
        return context.Request.Headers[IDEMPOTENCY_KEY_HEADER].ToString();
    }

    private async Task ReturnCachedResponse(HttpContext context, IdempotencyResult result)
    {
        context.Response.StatusCode = result.StatusCode;

        // Restore headers (except content-length, as response body may differ)
        foreach (var header in result.ResponseHeaders)
        {
            if (header.Key.Equals("content-length", StringComparison.OrdinalIgnoreCase))
                continue;

            context.Response.Headers[header.Key] = header.Value;
        }

        // Add replayed indicator
        context.Response.Headers["X-Idempotency-Replayed"] = "true";

        // Write cached response body
        await context.Response.Body.WriteAsync(result.ResponseBody, 0, result.ResponseBody.Length);
    }
}
```

### 6.2 Idempotency Store - In-Memory Implementation (Development)

```csharp
public class InMemoryIdempotencyStore : IIdempotencyStore
{
    private readonly ConcurrentDictionary<string, (IdempotencyResult result, DateTime expiration)> _cache;
    private readonly ConcurrentDictionary<string, SemaphoreSlim> _locks;

    public InMemoryIdempotencyStore()
    {
        _cache = new();
        _locks = new();
    }

    public Task<IdempotencyResult> GetAsync(string key, string tenantId)
    {
        var cacheKey = $"{tenantId}:{key}";

        if (_cache.TryGetValue(cacheKey, out var entry))
        {
            if (entry.expiration > DateTime.UtcNow)
            {
                entry.result.Replayed = true;
                return Task.FromResult(entry.result);
            }

            // Expired
            _cache.TryRemove(cacheKey, out _);
        }

        return Task.FromResult<IdempotencyResult>(null);
    }

    public Task StoreAsync(string key, string tenantId, IdempotencyResult result, TimeSpan ttl)
    {
        var cacheKey = $"{tenantId}:{key}";
        var expiration = DateTime.UtcNow.Add(ttl);

        _cache[cacheKey] = (result, expiration);
        return Task.CompletedTask;
    }

    public async Task LockAsync(string key, string tenantId, TimeSpan timeout)
    {
        var lockKey = $"{tenantId}:{key}:lock";
        var semaphore = _locks.GetOrAdd(lockKey, _ => new SemaphoreSlim(1, 1));

        var acquired = await semaphore.WaitAsync(timeout);

        if (!acquired)
        {
            throw new LockTimeoutException($"Failed to acquire lock for key: {key}");
        }
    }

    public Task UnlockAsync(string key, string tenantId)
    {
        var lockKey = $"{tenantId}:{key}:lock";

        if (_locks.TryGetValue(lockKey, out var semaphore))
        {
            semaphore.Release();
        }

        return Task.CompletedTask;
    }
}
```

### 6.3 Idempotency Store - Redis Implementation (Production)

```csharp
public class RedisIdempotencyStore : IIdempotencyStore
{
    private readonly IConnectionMultiplexer _redis;
    private readonly ILogger<RedisIdempotencyStore> _logger;

    public RedisIdempotencyStore(IConnectionMultiplexer redis, 
        ILogger<RedisIdempotencyStore> logger)
    {
        _redis = redis;
        _logger = logger;
    }

    public async Task<IdempotencyResult> GetAsync(string key, string tenantId)
    {
        try
        {
            var db = _redis.GetDatabase();
            var cacheKey = $"idempotency:{tenantId}:{key}";

            var value = await db.StringGetAsync(cacheKey);

            if (value.IsNullOrEmpty)
            {
                return null;
            }

            var result = JsonSerializer.Deserialize<IdempotencyResult>(value.ToString());
            result.Replayed = true;
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to retrieve idempotency result from Redis");
            return null;
        }
    }

    public async Task StoreAsync(string key, string tenantId, IdempotencyResult result, TimeSpan ttl)
    {
        try
        {
            var db = _redis.GetDatabase();
            var cacheKey = $"idempotency:{tenantId}:{key}";

            var serialized = JsonSerializer.Serialize(result);
            await db.StringSetAsync(cacheKey, serialized, ttl);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to store idempotency result in Redis");
            // Don't throw - continue processing even if caching fails
        }
    }

    public async Task LockAsync(string key, string tenantId, TimeSpan timeout)
    {
        var db = _redis.GetDatabase();
        var lockKey = $"idempotency-lock:{tenantId}:{key}";
        var lockValue = Guid.NewGuid().ToString();
        var deadline = DateTime.UtcNow.Add(timeout);

        while (DateTime.UtcNow < deadline)
        {
            // Try to acquire lock (SET NX)
            if (await db.StringSetAsync(lockKey, lockValue, TimeSpan.FromSeconds(30), When.NotExists))
            {
                return; // Lock acquired
            }

            // Wait before retry
            await Task.Delay(100);
        }

        throw new LockTimeoutException($"Failed to acquire lock for key: {key}");
    }

    public async Task UnlockAsync(string key, string tenantId)
    {
        try
        {
            var db = _redis.GetDatabase();
            var lockKey = $"idempotency-lock:{tenantId}:{key}";
            await db.KeyDeleteAsync(lockKey);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to release idempotency lock");
        }
    }
}
```

---

## 7. Client Usage Patterns

### 7.1 Client Example - POST (Create)

```csharp
// Client library pattern
public class AppointmentClient
{
    private readonly HttpClient _httpClient;

    public async Task<Appointment> CreateAppointmentAsync(CreateAppointmentRequest request, 
        string idempotencyKey = null)
    {
        // Generate or use provided idempotency key
        idempotencyKey ??= Guid.NewGuid().ToString();

        var httpRequest = new HttpRequestMessage(HttpMethod.Post, "/api/v1/appointments")
        {
            Content = JsonContent.Create(request)
        };

        // Add idempotency key
        httpRequest.Headers.Add("X-Idempotency-Key", idempotencyKey);

        HttpResponseMessage response = null;
        var maxRetries = 3;
        var retryCount = 0;

        while (retryCount < maxRetries)
        {
            try
            {
                response = await _httpClient.SendAsync(httpRequest);

                if (response.IsSuccessStatusCode)
                {
                    return await response.Content.ReadAsAsync<Appointment>();
                }

                // 4xx errors are not retryable (except 429)
                if ((int)response.StatusCode >= 400 && (int)response.StatusCode < 500 &&
                    response.StatusCode != System.Net.HttpStatusCode.TooManyRequests)
                {
                    throw new HttpRequestException($"Request failed with status {response.StatusCode}");
                }
            }
            catch (HttpRequestException) when (retryCount < maxRetries - 1)
            {
                // Retry on network errors
                retryCount++;
                await Task.Delay(TimeSpan.FromSeconds(Math.Pow(2, retryCount))); // Exponential backoff
                continue;
            }

            // Server error or rate limit - retry
            if ((response?.StatusCode == System.Net.HttpStatusCode.InternalServerError ||
                 response?.StatusCode == System.Net.HttpStatusCode.ServiceUnavailable ||
                 response?.StatusCode == System.Net.HttpStatusCode.TooManyRequests) &&
                retryCount < maxRetries - 1)
            {
                retryCount++;
                await Task.Delay(TimeSpan.FromSeconds(Math.Pow(2, retryCount)));
                continue;
            }

            throw new HttpRequestException($"Request failed: {response?.StatusCode}");
        }

        throw new HttpRequestException("Max retries exceeded");
    }
}

// Usage
var client = new AppointmentClient(...);
var key = Guid.NewGuid().ToString();

var appointment = await client.CreateAppointmentAsync(new CreateAppointmentRequest
{
    PatientId = "pat-123",
    ClinicianId = "clin-456",
    ScheduledTime = DateTime.UtcNow.AddDays(7)
}, idempotencyKey: key);

// Retry with same key - server returns same appointment, no duplicate
var sameAppointment = await client.CreateAppointmentAsync(new CreateAppointmentRequest
{
    PatientId = "pat-123",
    ClinicianId = "clin-456",
    ScheduledTime = DateTime.UtcNow.AddDays(7)
}, idempotencyKey: key);

Assert.Equal(appointment.Id, sameAppointment.Id); // Same appointment!
```

### 7.2 Idempotency Response Headers

Responses to idempotent operations include:

| Header | Value | Meaning |
|--------|-------|---------|
| `X-Idempotency-Replayed` | `true` or `false` | Whether response was cached/replayed |
| `X-Idempotency-Key` | Key value | Echoes the idempotency key (optional) |

```http
HTTP/1.1 200 OK
X-Idempotency-Replayed: true
X-Idempotency-Key: abc-123-def-456
Content-Type: application/json

{
  "statusCode": 200,
  "success": true,
  "data": { "id": "apt-001", ... },
  "correlationId": "123e4567-e89b-12d3-a456-426614174000"
}
```

---

## 8. Edge Cases and Handling

### 8.1 Concurrent Requests with Same Key

When two requests arrive simultaneously with the same idempotency key:

1. First request acquires lock
2. Second request waits for lock with timeout (30 seconds)
3. If timeout, return 409 Conflict with message
4. If first request completes before timeout, second request uses cached response

### 8.2 Idempotency Key Collision

If two different operations use same key (user error):
- First operation stores result under key
- Second operation retrieves first operation's result
- Client receives unexpected response

**Mitigation:** Client must use unique keys per operation (GUID recommended)

### 8.3 Expired Idempotency Result

If cached result expires (beyond TTL):
- Retry request is processed as new request
- New result replaces expired entry
- May result in duplicate state changes if truly required (rare)

**Mitigation:** Set appropriate TTL (24-72 hours recommended)

### 8.4 Database Transaction Rolled Back

If operation succeeded, response cached, but database transaction rolled back:
- Cached response contains successful status code
- Retry returns cached response
- No duplicate creation, but database state doesn't match response

**Mitigation:** Only cache responses after transaction commit confirmed

---

## 9. Monitoring and Observability

### 9.1 Metrics to Track

```csharp
public class IdempotencyMetrics
{
    public long CacheHits { get; set; }          // Number of replayed responses
    public long CacheMisses { get; set; }        // Number of new operations
    public long LockTimeouts { get; set; }       // Concurrent request conflicts
    public long CacheStoreErrors { get; set; }   // Failed cache stores
    public decimal ReplayRate => CacheHits / (CacheHits + CacheMisses);
}
```

### 9.2 Logging

```csharp
// Log when idempotency result is replayed
_logger.LogInformation(
    "Idempotent request replayed. Key: {IdempotencyKey}, " +
    "TenantId: {TenantId}, StatusCode: {StatusCode}, " +
    "OriginalTime: {OriginalTime}, ReplayTime: {ReplayTime}ms",
    idempotencyKey, tenantId, result.StatusCode,
    result.CreatedAt, sw.ElapsedMilliseconds);

// Log cache storage
_logger.LogInformation(
    "Idempotent response cached. Key: {IdempotencyKey}, " +
    "TTL: {TTLSeconds}s, ResponseSize: {ResponseSizeBytes}",
    idempotencyKey, ttl.TotalSeconds, result.ResponseBody.Length);
```

---

## 10. Testing Idempotency

### 10.1 Unit Tests

```csharp
[Fact]
public async Task IdempotencyMiddleware_SameKeyRetursCachedResponse()
{
    // Arrange
    var key = "test-key-123";
    var middleware = CreateMiddleware();

    // Act - First request
    var response1 = await _client.PostAsJsonAsync("/api/v1/appointments", 
        new { patientId = "pat-123" },
        headers: new { XIdempotencyKey = key });

    // Act - Retry with same key
    var response2 = await _client.PostAsJsonAsync("/api/v1/appointments",
        new { patientId = "pat-123" },
        headers: new { XIdempotencyKey = key });

    // Assert
    Assert.Equal(response1.StatusCode, response2.StatusCode);
    var replayed = response2.Headers.GetValues("X-Idempotency-Replayed").FirstOrDefault();
    Assert.Equal("true", replayed);
}

[Fact]
public async Task IdempotencyMiddleware_DifferentKeyCreatesNewResource()
{
    // Act - First request
    var response1 = await _client.PostAsJsonAsync("/api/v1/appointments",
        new { patientId = "pat-123" },
        headers: new { XIdempotencyKey = "key-1" });
    var apt1 = await response1.Content.ReadAsAsync<Appointment>();

    // Act - Different key
    var response2 = await _client.PostAsJsonAsync("/api/v1/appointments",
        new { patientId = "pat-123" },
        headers: new { XIdempotencyKey = "key-2" });
    var apt2 = await response2.Content.ReadAsAsync<Appointment>();

    // Assert
    Assert.NotEqual(apt1.Id, apt2.Id); // Different resources created
}
```

---

## 11. Implementation Checklist

Services MUST verify:

- [ ] Idempotency middleware intercepts all write operations (POST, PUT, PATCH, DELETE)
- [ ] X-Idempotency-Key header is extracted and validated
- [ ] Cached responses are returned for duplicate keys
- [ ] Response includes X-Idempotency-Replayed header
- [ ] Lock prevents concurrent processing of same key
- [ ] Successful responses (2xx) are cached with appropriate TTL
- [ ] Idempotency store is implemented (Redis for production)
- [ ] Failed operations (4xx/5xx) are NOT cached
- [ ] Client retries use same idempotency key
- [ ] Metrics tracked for replay rate and cache performance
- [ ] Integration tests validate idempotency behavior
- [ ] Monitoring alerts on high lock timeout rates

---

## 12. Example: Complete Flow

```
Client Request 1:
  POST /api/v1/appointments
  X-Idempotency-Key: abc-123
  Body: {patientId: pat-123, scheduledTime: 2026-07-01}

Server Processing:
  1. Extract idempotency key: abc-123
  2. Check cache: MISS
  3. Acquire lock: OK
  4. Process request: Create appointment apt-001
  5. Store result in cache with TTL 24h
  6. Release lock
  7. Return 201 with appointment data

Client Network Timeout → Retry:
  POST /api/v1/appointments
  X-Idempotency-Key: abc-123 (SAME KEY)
  Body: {patientId: pat-123, scheduledTime: 2026-07-01}

Server Processing:
  1. Extract idempotency key: abc-123
  2. Check cache: HIT
  3. Return cached response immediately
  4. Add X-Idempotency-Replayed: true header

Result:
  Only one appointment created
  No duplicate state changes
  Client receives same result
```

---

## 13. Questions and Feedback

For questions about idempotency patterns:
- Open issue in: `.propel/context/standards/issues/`
- Platform team: platform@propellq.local
- Next review date: Q3 2026
