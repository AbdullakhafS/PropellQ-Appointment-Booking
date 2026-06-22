# LOG-2: Correlation Propagation Pattern

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Audience:** Backend engineers, middleware developers, DevOps

---

## 1. Overview

This document defines how correlation IDs are generated and propagated throughout the PropellQ system to enable end-to-end request tracing across service boundaries, asynchronous operations, and distributed system components.

**Key Principles:**
- **Single source of truth:** Each request/operation has exactly one correlation ID
- **Universal propagation:** Correlation ID flows through all synchronous and asynchronous paths
- **Non-breaking:** Correlation propagation doesn't modify request/response contracts
- **Observability:** All logs automatically tagged with correlation context

---

## 2. Correlation ID Lifecycle

### 2.1 Generation on Ingress

When a request enters the system without a correlation ID, generate one:

```
Client Request (no X-Correlation-ID)
         ↓
[API Gateway / Ingress Controller]
         ↓
Generate new correlationId = UUID v4
         ↓
Set X-Correlation-ID: {uuid}
         ↓
Route to Service
```

**Rules:**
- If `X-Correlation-ID` header present in inbound request → Use it
- If `X-Correlation-ID` header absent → Generate new UUID v4
- Generate UUID v4 using cryptographically secure random source
- Never use empty string or null as correlation ID

### 2.2 Propagation Through Synchronous Calls

When Service A calls Service B synchronously, propagate the correlation ID:

```
Service A (correlationId = abc-123)
    ↓
    [Create HTTP Request to Service B]
    ├─ Headers: X-Correlation-ID: abc-123
    ├─ Body: {... request payload ...}
    ↓
Service B receives X-Correlation-ID: abc-123
    ↓
    [Service B logs and traces all work with correlationId = abc-123]
    ↓
    [Service B calls Service C]
    ├─ Headers: X-Correlation-ID: abc-123
    ├─ Body: {... request payload ...}
    ↓
Service C receives X-Correlation-ID: abc-123
    ↓
    [All services share same correlationId throughout chain]
```

**Implementation:**
```csharp
// Outbound HTTP client automatically injects correlation ID
public class CorrelationIdDelegatingHandler : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var correlationId = HttpContext.Current?.Items["correlationId"]?.ToString();
        
        if (!string.IsNullOrEmpty(correlationId))
        {
            request.Headers.Add("X-Correlation-ID", correlationId);
        }
        
        return await base.SendAsync(request, cancellationToken);
    }
}

// Register in DI container
services.AddHttpClient<IAppointmentClient>()
    .AddHttpMessageHandler(() => new CorrelationIdDelegatingHandler());
```

### 2.3 Propagation Through Asynchronous Operations

When dispatching async work (background jobs, event handlers, scheduled tasks), embed correlation ID in the operation context:

```
Service A (correlationId = abc-123)
    ↓
    [Publish Event: AppointmentCreated]
    ├─ Event contains: { correlationId: "abc-123", ... payload ... }
    ↓
Message Queue (RabbitMQ, Kafka, etc.)
    ↓
Service B Event Handler
    ├─ Receive Event with correlationId = abc-123
    ├─ Extract: correlationId from event metadata
    ├─ Set: LogContext.Push("correlationId", "abc-123")
    ↓
    [All logs within handler tagged with correlationId = abc-123]
    ↓
    [If handler calls Service C, include correlationId in request]
    ├─ Headers: X-Correlation-ID: abc-123
    ↓
Service C also receives correlationId = abc-123
```

**Implementation Pattern:**

```csharp
// Event definition includes correlation context
public class AppointmentCreatedEvent
{
    public string CorrelationId { get; set; }
    public string AppointmentId { get; set; }
    public DateTime CreatedAt { get; set; }
    // ... other fields ...
}

// Publisher embeds correlation ID
public class AppointmentService
{
    private readonly IEventBus _eventBus;
    private readonly ILogger _logger;

    public async Task CreateAsync(CreateAppointmentRequest request, string correlationId)
    {
        var appointment = new Appointment { ... };

        // Publish event with correlation context
        await _eventBus.PublishAsync(new AppointmentCreatedEvent
        {
            CorrelationId = correlationId,  // ← Include correlation ID
            AppointmentId = appointment.Id,
            CreatedAt = DateTime.UtcNow
        });

        _logger.LogInformation(
            "Appointment created. CorrelationId: {CorrelationId}",
            correlationId);
    }
}

// Consumer extracts and uses correlation ID
public class AppointmentCreatedEventHandler
{
    private readonly ILogger _logger;

    public async Task HandleAsync(AppointmentCreatedEvent @event)
    {
        using (LogContext.PushProperty("correlationId", @event.CorrelationId))
        {
            _logger.LogInformation(
                "Processing appointment creation. AppointmentId: {AppointmentId}",
                @event.AppointmentId);

            // All logs automatically include correlation ID
            await NotifyClinicianAsync(@event.AppointmentId);
        }
    }
}
```

---

## 3. Correlation ID Header Propagation

### 3.1 Inbound Header: X-Correlation-ID

**Header Name:** `X-Correlation-ID`  
**Format:** UUID v4 (36 characters with hyphens)  
**Required:** For service-to-service calls; optional for external clients

**Example:**
```
GET /api/v1/appointments HTTP/1.1
X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer {token}
Content-Type: application/json
```

### 3.2 Outbound Header: X-Correlation-ID

All outbound requests to other services MUST include the same correlation ID:

```
Service A → Service B Request:
    POST /api/v1/notifications HTTP/1.1
    X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
    Host: notification-service
    Content-Type: application/json
```

### 3.3 Response Header: X-Correlation-ID

Services MUST echo the correlation ID in HTTP responses:

```
HTTP/1.1 201 Created
X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "statusCode": 201,
  "success": true,
  "correlationId": "550e8400-e29b-41d4-a716-446655440000",
  "data": { ... }
}
```

---

## 4. OpenTelemetry Trace Correlation

### 4.1 Trace ID and Span ID Relationship

While correlation IDs trace business operations, OpenTelemetry provides distributed tracing at the span level:

```
X-Correlation-ID (Business Level)
    ├─ Traces complete business operation
    ├─ Persists in logs and events
    └─ Used for incident investigation

OpenTelemetry Trace (System Level)
    ├─ W3C Trace Context: traceparent header
    ├─ Format: 00-{traceId}-{spanId}-{traceFlags}
    └─ Example: traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
```

**Mapping:**
- `X-Correlation-ID` ← Business correlation (UUID)
- `traceparent` ← OpenTelemetry trace (W3C standard)
- Both flow together through all services
- Correlation ID lives in application logs
- Trace ID lives in distributed tracing backend (Jaeger, Datadog, etc.)

### 4.2 Propagating Both Headers

```csharp
public class DistributedTracingMiddleware
{
    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        // Extract correlation ID
        var correlationId = context.Request.Headers
            .FirstOrDefault(x => x.Key == "X-Correlation-ID").Value;
        
        if (string.IsNullOrEmpty(correlationId))
        {
            correlationId = Guid.NewGuid().ToString();
        }

        // Extract/create OpenTelemetry trace context
        var activity = new Activity("HttpRequest");
        activity.Start();

        // Add to log context
        using (LogContext.PushProperty("correlationId", correlationId))
        using (LogContext.PushProperty("traceId", activity.Id))
        using (LogContext.PushProperty("spanId", activity.SpanId))
        {
            // Continue processing
            await next(context);

            // Add correlation ID to response
            context.Response.Headers["X-Correlation-ID"] = correlationId;
        }

        activity.Dispose();
    }
}
```

---

## 5. Correlation ID Storage and Context Management

### 5.1 Middleware Registration Order

Correlation ID middleware MUST run EARLY in the pipeline:

```csharp
public void Configure(IApplicationBuilder app)
{
    // Correlation ID middleware first (before logging, auth, etc.)
    app.UseMiddleware<CorrelationIdMiddleware>();
    
    // Logging middleware (uses correlation ID)
    app.UseMiddleware<LoggingMiddleware>();
    
    // Then authentication, authorization, etc.
    app.UseAuthentication();
    app.UseAuthorization();
    
    // Finally route handlers
    app.UseRouting();
    app.UseEndpoints(endpoints => { ... });
}
```

### 5.2 Context Storage Patterns

**C# - AsyncLocal/LogContext:**
```csharp
// Option 1: Serilog LogContext (recommended)
using (LogContext.PushProperty("correlationId", correlationId))
{
    // correlationId automatically added to all logs in this scope
}

// Option 2: AsyncLocal (for thread-safe context)
public static class CorrelationContext
{
    private static AsyncLocal<string> _correlationId = new();

    public static string GetCorrelationId() => _correlationId.Value;
    public static void SetCorrelationId(string id) => _correlationId.Value = id;
}
```

**TypeScript/Node.js - Async Context Storage:**
```typescript
import { AsyncLocalStorage } from 'async_hooks';

const correlationIdStorage = new AsyncLocalStorage<string>();

export function getCorrelationId(): string | undefined {
  return correlationIdStorage.getStore();
}

export function withCorrelationId<T>(
  correlationId: string,
  fn: () => T
): T {
  return correlationIdStorage.run(correlationId, fn);
}

// Usage in middleware
app.use((req, res, next) => {
  const correlationId = req.headers['x-correlation-id'] || generateUUID();
  
  withCorrelationId(correlationId, () => {
    logger.info('Request started');
    next();
  });
});
```

---

## 6. Database and Cache Propagation

### 6.1 Logging Correlation ID with Database Operations

Include correlation ID when logging database queries:

```csharp
public class AppointmentRepository
{
    private readonly ILogger _logger;
    private readonly IDbConnection _connection;

    public async Task<Appointment> GetByIdAsync(string appointmentId, string correlationId)
    {
        var stopwatch = Stopwatch.StartNew();

        try
        {
            _logger.LogInformation(
                "Executing query: SELECT * FROM appointments WHERE id = @id. " +
                "CorrelationId: {CorrelationId}",
                correlationId);

            var appointment = await _connection.QuerySingleOrDefaultAsync(
                "SELECT * FROM appointments WHERE id = @id",
                new { id = appointmentId });

            stopwatch.Stop();

            _logger.LogInformation(
                "Query completed in {Duration}ms. CorrelationId: {CorrelationId}",
                stopwatch.ElapsedMilliseconds,
                correlationId);

            return appointment;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "Query failed. CorrelationId: {CorrelationId}",
                correlationId);
            throw;
        }
    }
}
```

### 6.2 Cache Key Isolation (Optional)

For sensitive cache data, consider including correlation ID in cache key:

```csharp
// Don't include correlation ID in cache key (cache is shared)
public string GetCacheKey(string appointmentId)
{
    return $"appointment:{appointmentId}";
}

// But DO log cache operations with correlation ID
_logger.LogInformation(
    "Cache hit: {CacheKey}. CorrelationId: {CorrelationId}",
    cacheKey,
    correlationId);
```

---

## 7. Common Propagation Patterns

### 7.1 HTTP Request Chain

```
Client Browser
    ↓ GET /api/v1/appointments
    ├─ Header: X-Correlation-ID: abc-123 [generated by gateway]
    ↓
API Gateway
    ├─ Logs: correlationId: abc-123
    ├─ Adds header: X-Correlation-ID: abc-123
    ↓
Appointment Service
    ├─ Logs: correlationId: abc-123
    ├─ Calls Clinical Data Service
    ├─ Headers: X-Correlation-ID: abc-123
    ↓
Clinical Data Service
    ├─ Logs: correlationId: abc-123
    ├─ Calls Authentication Service
    ├─ Headers: X-Correlation-ID: abc-123
    ↓
Auth Service
    ├─ Logs: correlationId: abc-123
    ↓
Response flows back with same correlationId
    └─ All logs queryable by correlationId: abc-123
```

### 7.2 Event-Driven Architecture

```
Command: CreateAppointment
    ├─ correlationId: abc-123
    ↓
Appointment Service
    ├─ Logs: correlationId: abc-123
    ├─ Creates appointment
    ├─ Publishes Event: AppointmentCreated
    ├─ Event metadata: correlationId: abc-123
    ↓
Message Queue
    ├─ Stores: { correlationId: abc-123, ... event data ... }
    ↓
Notification Service
    ├─ Consumes event
    ├─ Extracts: correlationId: abc-123
    ├─ Logs: correlationId: abc-123
    ├─ Sends notification
    ↓
Analytics Service
    ├─ Consumes same event
    ├─ Extracts: correlationId: abc-123
    ├─ Logs: correlationId: abc-123
    ├─ Records metrics
    ↓
All logs/events linked by correlationId: abc-123
```

### 7.3 Background Job Processing

```
Scheduled Task
    ├─ Generate: correlationId = xyz-789
    ↓
Background Job Runner
    ├─ Logs: correlationId: xyz-789
    ├─ Enqueues job with correlationId
    ↓
Job Queue
    ├─ Stores: { correlationId: xyz-789, ... job data ... }
    ↓
Worker Process
    ├─ Dequeues job
    ├─ Extracts: correlationId: xyz-789
    ├─ Sets: LogContext.PushProperty("correlationId", xyz-789)
    ├─ Logs: correlationId: xyz-789
    ├─ Executes job (may call services with correlationId)
    ↓
All job processing steps tagged with correlationId: xyz-789
```

---

## 8. Correlation ID Injection Checklist

For each service, verify:

- [ ] **Inbound:** Middleware extracts `X-Correlation-ID` from request headers
- [ ] **Generation:** If missing, generate new UUID v4
- [ ] **Storage:** Correlation ID stored in AsyncLocal/LogContext
- [ ] **Logging:** All logs automatically include correlation ID (via structured logging)
- [ ] **Outbound HTTP:** All outbound requests include `X-Correlation-ID` header
- [ ] **Outbound Events:** Events published with `correlationId` in metadata
- [ ] **Outbound Database:** Correlation ID logged with SQL operations
- [ ] **Response:** Response headers include `X-Correlation-ID`
- [ ] **Async Operations:** Background jobs include correlation ID
- [ ] **Error Handling:** Error logs include correlation ID

---

## 9. Testing Correlation Propagation

### 9.1 Unit Test Example

```csharp
[TestClass]
public class CorrelationIdPropagationTests
{
    [TestMethod]
    public void CorrelationId_GeneratedWhenMissing()
    {
        // Arrange
        var context = new DefaultHttpContext();
        var middleware = new CorrelationIdMiddleware(async (ctx) => { });

        // Act
        middleware.Invoke(context);

        // Assert
        var correlationId = context.Items["correlationId"];
        Assert.IsNotNull(correlationId);
        Assert.IsTrue(Guid.TryParse((string)correlationId, out _));
    }

    [TestMethod]
    public void CorrelationId_PropagatedInLogs()
    {
        // Arrange
        var correlationId = "abc-123-def-456";
        var logRecords = new List<LogRecord>();

        var testSink = new TestLogSink(logRecords);
        var logger = new LoggerBuilder().AddSink(testSink).Build();

        // Act
        using (LogContext.PushProperty("correlationId", correlationId))
        {
            logger.LogInformation("Test message");
        }

        // Assert
        var logRecord = logRecords.First();
        Assert.AreEqual(correlationId, logRecord.Properties["correlationId"]);
    }
}
```

### 9.2 Integration Test Example

```csharp
[TestClass]
public class CorrelationIdIntegrationTests
{
    [TestMethod]
    public async Task CorrelationId_PropagatedAcrossServices()
    {
        // Arrange
        var correlationId = Guid.NewGuid().ToString();
        var appointmentService = new AppointmentService(_httpClient);

        // Act
        var response = await appointmentService.CreateAsync(
            new CreateAppointmentRequest { ... },
            correlationId);

        // Assert
        Assert.AreEqual(correlationId, response.CorrelationId);
        
        // Verify correlation ID in logs
        var logs = _logSink.GetLogs();
        Assert.IsTrue(logs.All(l => l.CorrelationId == correlationId));
    }
}
```

---

## 10. Best Practices

- ✅ Generate UUID v4 for new correlation IDs (cryptographically unique)
- ✅ Always propagate received correlation ID (never modify)
- ✅ Include correlation ID in all logs automatically (structured logging)
- ✅ Add correlation ID to outbound requests and events
- ✅ Store correlation ID in request-scoped context (AsyncLocal/LogContext)
- ✅ Log correlation ID in error messages for debugging

- ❌ Never use correlation ID as primary key or persist long-term
- ❌ Never include sensitive data in correlation ID
- ❌ Never modify correlation ID mid-request
- ❌ Never make correlation ID optional for service-to-service calls

---

## 11. References

- Structured Logging Schema: [LOG-1](structured-log-schema-standard.md)
- Log Redaction Rules: [SEC-1](../security/redaction-masking-rules.md)
- Centralized Log Pipeline: [PIPE-1](../pipeline/log-shipping-pipeline.md)

---

**Next:** [PIPE-1: Centralized Log Shipping Pipeline](../pipeline/log-shipping-pipeline.md)
