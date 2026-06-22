# TRACE-1: Instrumentation Baseline

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Audience:** Backend engineers, platform teams, DevOps

---

## 1. Overview

This document defines the distributed tracing instrumentation baseline for all PropellQ services. All services MUST emit OpenTelemetry spans conforming to this specification to enable end-to-end request tracing, latency analysis, and dependency visualization.

**Objectives:**
- Instrument all services with OpenTelemetry SDK
- Standardize span naming and tagging conventions
- Propagate trace context across service boundaries
- Export traces to centralized backend (Jaeger, Datadog, etc.)
- Enable debugging, performance analysis, and SLO tracking

---

## 2. OpenTelemetry Integration Architecture

### 2.1 Instrumentation Stack

```
┌─────────────────────────────────────────┐
│ Application Code                        │
│  ├─ HTTP handlers                      │
│  ├─ Database queries                   │
│  ├─ External API calls                 │
│  └─ Message queue operations           │
└────────────────────┬────────────────────┘
                     │
         ┌───────────▼──────────┐
         │ OpenTelemetry SDK    │
         │ ├─ Tracer            │
         │ ├─ Spans             │
         │ ├─ Baggage           │
         │ └─ Context           │
         └────────┬──────┬──────┘
                  │      │
        ┌─────────▼─┐  ┌─▼─────────┐
        │ Sampler   │  │ Processor  │
        │ (100%)    │  │ (Batch)    │
        └───────────┘  └─────┬──────┘
                             │
        ┌────────────────────▼──────────────┐
        │ Exporter (W3C Trace Context)      │
        │ ├─ OTLP (gRPC/HTTP)             │
        │ ├─ Jaeger                        │
        │ └─ Datadog                       │
        └────────────────────┬──────────────┘
                             │
        ┌────────────────────▼──────────────┐
        │ Centralized Backend               │
        │ ├─ Jaeger                        │
        │ ├─ Datadog                       │
        │ ├─ Elastic APM                   │
        │ └─ Lightstep                     │
        └──────────────────────────────────┘
```

### 2.2 Span Hierarchy Example

```
Root Span: POST /api/v1/appointments
├─ HTTP Request Handler
│  ├─ Database: INSERT appointments
│  │  └─ Connection pool acquisition
│  ├─ External Call: notification-service
│  │  ├─ HTTP: POST /notify
│  │  └─ JSON serialization
│  └─ Message Queue: PUBLISH AppointmentCreated
│     └─ Event serialization

Attributes (on root span):
- trace_id: 0af7651916cd43dd8448eb211c80319c
- span_id: b7ad6b7169203331
- parent_span_id: null (root)
- service.name: appointment-service
- service.version: 1.2.0
- http.method: POST
- http.url: /api/v1/appointments
- http.status_code: 201
- http.client_ip: 192.168.1.100
- span.kind: SERVER
- otel.library.name: OpenTelemetry
- otel.library.version: 1.0.0
```

---

## 3. SDK Installation and Configuration

### 3.1 C# / .NET Instrumentation

**Install packages:**
```bash
dotnet add package OpenTelemetry
dotnet add package OpenTelemetry.Exporter.Jaeger
dotnet add package OpenTelemetry.Exporter.Console
dotnet add package OpenTelemetry.Instrumentation.AspNetCore
dotnet add package OpenTelemetry.Instrumentation.HttpClient
dotnet add package OpenTelemetry.Instrumentation.SqlClient
```

**Program.cs configuration:**
```csharp
using OpenTelemetry;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);

// Configure OpenTelemetry
var otelResource = ResourceBuilder.CreateDefault()
    .AddService(serviceName: "appointment-service",
        serviceVersion: "1.2.0")
    .AddAttributes(new Dictionary<string, object>
    {
        ["deployment.environment"] = builder.Environment.EnvironmentName,
        ["service.instance.id"] = Environment.MachineName
    });

builder.Services.AddOpenTelemetry()
    .WithTracing(tracerProvider =>
    {
        tracerProvider
            .SetResourceBuilder(otelResource)
            .AddAspNetCoreInstrumentation(options =>
            {
                // Record request/response body size
                options.RecordException = true;
                options.EnrichWithHttpRequest = (activity, request) =>
                {
                    activity.SetTag("http.client_ip",
                        request.HttpContext.Connection.RemoteIpAddress);
                };
                options.EnrichWithHttpResponse = (activity, response) =>
                {
                    activity.SetTag("http.response.body_size",
                        response.ContentLength);
                };
            })
            .AddHttpClientInstrumentation(options =>
            {
                options.RecordException = true;
                options.EnrichWithHttpRequestMessage = (activity, request) =>
                {
                    activity.SetTag("http.request_content_length",
                        request.Content?.Headers.ContentLength);
                };
            })
            .AddSqlClientInstrumentation(options =>
            {
                options.SetDbStatementForText = true;
                options.RecordException = true;
            })
            .AddConsoleExporter() // Development
            .AddJaegerExporter(options =>
            {
                options.AgentHost = Environment.GetEnvironmentVariable("JAEGER_HOST") ?? "localhost";
                options.AgentPort = int.Parse(
                    Environment.GetEnvironmentVariable("JAEGER_PORT") ?? "6831");
            });
    });

var app = builder.Build();

app.UseOpenTelemetryPrometheusScrapingEndpoint();

app.Run();
```

### 3.2 TypeScript / Node.js Instrumentation

**Install packages:**
```bash
npm install @opentelemetry/api @opentelemetry/sdk-node
npm install @opentelemetry/auto
npm install @opentelemetry/exporter-trace-otlp-http
npm install @opentelemetry/resources
npm install @opentelemetry/semantic-conventions
```

**Initialize (before app start):**
```typescript
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import {
  PeriodicExportingMetricReader,
  MeterProvider,
} from '@opentelemetry/sdk-metrics';

const sdk = new NodeSDK({
  resource: {
    attributes: {
      'service.name': 'appointment-service',
      'service.version': '1.2.0',
      'deployment.environment': process.env.NODE_ENV,
      'service.instance.id': require('os').hostname(),
    },
  },
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318/v1/traces',
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();
console.log('OpenTelemetry SDK started');
```

---

## 4. Span Naming Conventions

### 4.1 HTTP Server Spans

**Format:** `{HTTP_METHOD} {route_pattern}`

| Endpoint | Span Name |
|---|---|
| `POST /api/v1/appointments` | `POST /api/v1/appointments` |
| `GET /api/v1/appointments/{id}` | `GET /api/v1/appointments/{id}` |
| `PUT /api/v1/appointments/{id}` | `PUT /api/v1/appointments/{id}` |
| `DELETE /api/v1/appointments/{id}` | `DELETE /api/v1/appointments/{id}` |

**Rationale:** Route pattern prevents cardinality explosion (e.g., `/appointments/123`, `/appointments/456` all map to same span name)

### 4.2 HTTP Client Spans

**Format:** `{HTTP_METHOD} {hostname}/{path}`

| Call | Span Name |
|---|---|
| `POST to notification-service/notify` | `POST notification-service/notify` |
| `GET from clinical-data-service/labs/{id}` | `GET clinical-data-service/labs/{id}` |

### 4.3 Database Spans

**Format:** `{DATABASE} {OPERATION} {TABLE}`

| Operation | Span Name |
|---|---|
| `SELECT * FROM appointments` | `SELECT appointments` |
| `INSERT INTO appointments ...` | `INSERT appointments` |
| `UPDATE appointments SET ...` | `UPDATE appointments` |
| `DELETE FROM appointments ...` | `DELETE appointments` |

### 4.4 Message Queue Spans

**Format:** `{QUEUE_NAME} {OPERATION}`

| Operation | Span Name |
|---|---|
| Publish to appointment_events | `appointment_events PUBLISH` |
| Consume from appointment_events | `appointment_events CONSUME` |

---

## 5. Span Attributes Standard

### 5.1 HTTP Server Span Attributes

```
http.method                   = "POST"
http.url                      = "/api/v1/appointments"
http.scheme                   = "https"
http.target                   = "/api/v1/appointments?filter=pending"
http.host                     = "api.propellq.local"
http.status_code              = 201
http.request_content_length   = 256
http.response_content_length  = 512
http.flavor                   = "1.1"
http.client_ip                = "192.168.1.100"

span.kind                      = "SERVER"
span.status.code               = "OK"
span.status.description        = ""

service.name                   = "appointment-service"
service.version                = "1.2.0"
service.instance.id            = "pod-appointment-001"
deployment.environment         = "production"

http.request_duration_ms       = 145
correlation_id                 = "550e8400-e29b-41d4-a716-446655440000"
user_id                        = "user-123"
tenant_id                      = "tenant-456"
```

### 5.2 HTTP Client Span Attributes

```
http.method                   = "POST"
http.url                      = "https://notification-service/api/v1/notify"
http.status_code              = 200
http.request_content_length   = 128
http.response_content_length  = 64

span.kind                      = "CLIENT"
peer.service                   = "notification-service"
rpc.system                     = "http"
```

### 5.3 Database Span Attributes

```
db.system                      = "postgresql"
db.name                        = "propellq_appointments"
db.user                        = "service_account"
db.operation                   = "SELECT"
db.statement                   = "SELECT * FROM appointments WHERE id = ?"

span.kind                      = "CLIENT"
db.client.connection.pool.name = "appointment-pool"
db.client.connections.idle     = 5
db.client.connections.usage    = 8
```

### 5.4 Custom Business Attributes

Add custom attributes for business context:

```csharp
using System.Diagnostics;

var activity = Activity.Current;
if (activity != null)
{
    activity.SetTag("appointment.id", appointmentId);
    activity.SetTag("patient.id", patientId);
    activity.SetTag("clinician.id", clinicianId);
    activity.SetTag("appointment.type", "CONSULTATION");
    activity.SetTag("appointment.outcome", "SUCCESS");
    activity.SetTag("appointment.duration_minutes", 30);
}
```

---

## 6. Span Events and Exceptions

### 6.1 Logging Exceptions to Spans

```csharp
try
{
    await _appointmentService.CreateAsync(request);
}
catch (ValidationException ex)
{
    var activity = Activity.Current;
    if (activity != null)
    {
        activity.RecordException(ex);
        activity.SetStatus(ActivityStatusCode.Error, ex.Message);
    }
    throw;
}
```

### 6.2 Recording Span Events

```csharp
var activity = Activity.Current;
if (activity != null)
{
    activity.AddEvent(new ActivityEvent("cache_miss",
        new ActivityTagsCollection(
            new Dictionary<string, object>
            {
                ["cache.key"] = appointmentId,
                ["cache.miss_count"] = 1
            })));
}
```

---

## 7. Context Propagation

### 7.1 W3C Trace Context Header

All outbound requests MUST include W3C Trace Context header:

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01

Format: 00-{traceId}-{spanId}-{traceFlags}
- traceId: 32 hex chars (128-bit)
- spanId: 16 hex chars (64-bit)
- traceFlags: 02 hex chars (sampled bit)
```

### 7.2 Automatic Propagation (C#)

HttpClient automatically propagates trace context via `System.Net.Http.HttpClientHandler`:

```csharp
var client = new HttpClient();
// Trace context automatically added to all requests
await client.PostAsync("https://notification-service/notify", content);
```

### 7.3 Manual Propagation (Custom Code)

```csharp
var activity = Activity.Current;
if (activity != null)
{
    var propagationContext = new PropagationContext(
        activity.TraceId, activity.SpanId, activity.ActivityTraceFlags);
    
    W3CFormat.Inject(propagationContext, requestHeaders, (h, k, v) =>
    {
        h.Add(k, v);
    });
}
```

---

## 8. Sampling Strategy

### 8.1 Production Sampling Configuration

**Default:** 100% sampling (sample all traces)

```csharp
var sampler = new AlwaysOnSampler();
// Or: new ProbabilitySampler(0.1) // 10% sampling
```

**Rationale:**
- Traces are relatively low volume (~1-10 MB/day per service)
- 100% sampling enables accurate SLO calculation
- Distributed sampling can lose critical error traces

### 8.2 Sampler Configuration by Environment

| Environment | Sampling Rate | Rationale |
|---|---|---|
| Production | 100% | Accurate SLO tracking, low volume |
| Staging | 100% | Pre-production validation |
| Development | 10% | Reduce noise, enable fast iteration |

---

## 9. Deployment Configuration

### 9.1 Environment Variables

```bash
OTEL_SERVICE_NAME=appointment-service
OTEL_SDK_DISABLED=false
OTEL_TRACES_EXPORTER=jaeger
OTEL_EXPORTER_JAEGER_ENDPOINT=http://jaeger-collector:14268/api/traces
OTEL_EXPORTER_JAEGER_AGENT_HOST=jaeger-agent
OTEL_EXPORTER_JAEGER_AGENT_PORT=6831
OTEL_EXPORTER_JAEGER_SAMPLER_TYPE=const
OTEL_EXPORTER_JAEGER_SAMPLER_PARAM=1
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production,service.version=1.2.0
```

### 9.2 Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-config
  namespace: production
data:
  OTEL_SERVICE_NAME: appointment-service
  OTEL_TRACES_EXPORTER: jaeger
  OTEL_EXPORTER_JAEGER_AGENT_HOST: jaeger-agent.logging.svc
  OTEL_EXPORTER_JAEGER_AGENT_PORT: "6831"
  OTEL_RESOURCE_ATTRIBUTES: deployment.environment=production
```

---

## 10. Span Collection and Export

### 10.1 Batch Export Configuration

```csharp
var exportOptions = new BatchExportActivityProcessorOptions
{
    ExportTimeoutMilliseconds = 30000,
    MaxExportBatchSize = 512,
    MaxQueueSize = 2048,
    ScheduledDelayMilliseconds = 5000
};

var processor = new BatchActivityExportProcessor(exporter, exportOptions);
```

### 10.2 Fallback/Local Storage

On export failure, write spans to local file:

```csharp
public class LocalFallbackExporter : BaseExporter<Activity>
{
    public override ExportResult Export(in Batch<Activity> batch)
    {
        try
        {
            // Try primary export
            return primaryExporter.Export(batch);
        }
        catch (Exception)
        {
            // Fallback to local file
            WriteToLocalFile(batch);
            return ExportResult.Failure;
        }
    }
}
```

---

## 11. Instrumentation Checklist

For each service, verify:

- [ ] OpenTelemetry SDK installed and configured
- [ ] Service name, version, environment attributes set
- [ ] HTTP server instrumentation enabled
- [ ] HTTP client instrumentation enabled (for outbound calls)
- [ ] Database instrumentation enabled (for queries)
- [ ] Message queue instrumentation enabled
- [ ] Custom business attributes added
- [ ] Exception recording configured
- [ ] Trace context propagation (W3C headers)
- [ ] Exporter configured for centralized backend
- [ ] Sampling strategy configured for environment
- [ ] Health check includes tracer health

---

## 12. Validation and Testing

### 12.1 Trace Verification Checklist

After deploying instrumentation:

- [ ] Traces appear in Jaeger/backend within 10 seconds
- [ ] Span names follow naming conventions
- [ ] All required attributes present
- [ ] Exception recording working
- [ ] Trace context propagates across services
- [ ] Sampling rate matches configuration
- [ ] Export latency < 100ms

### 12.2 Test Span Generation

```csharp
[TestMethod]
public void TestTraceGeneration()
{
    // Arrange
    var httpClient = new HttpClient();

    // Act
    var response = await httpClient.PostAsync(
        "http://localhost:5000/api/v1/appointments",
        new StringContent("{}"));

    // Assert
    Assert.IsTrue(response.IsSuccessStatusCode);
    
    // Verify trace was exported (wait 5s for batch export)
    Thread.Sleep(5000);
    
    var traces = QueryJaegerForTraces("appointment-service");
    Assert.IsTrue(traces.Count > 0);
}
```

---

## 13. References

- OpenTelemetry Specification: https://opentelemetry.io/docs/reference/specification/
- Jaeger Documentation: https://www.jaegertracing.io/docs/
- W3C Trace Context: https://w3c.github.io/trace-context/
- Semantic Conventions: https://opentelemetry.io/docs/reference/specification/protocol/exporter/

**Next:** [TRACE-2: Critical Journey Coverage](critical-journey-coverage.md)
