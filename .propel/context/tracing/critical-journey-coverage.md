# TRACE-2: Critical Journey Coverage

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Audience:** Product leads, backend engineers, platform teams

---

## 1. Overview

This document identifies the critical user journeys and workflows that MUST have comprehensive tracing coverage to enable SLO tracking, incident investigation, and performance optimization.

**Focus Areas:**
- Core business flows (appointment creation, booking confirmation)
- Queue and async operations (appointment notifications, data sync)
- Cross-service dependencies (clinical data retrieval, scheduling)
- Error paths and degradation scenarios

---

## 2. Critical Journey Map

### 2.1 Core Journeys (Must Trace)

#### Journey 1: Appointment Creation → Confirmation

```
User initiates appointment creation
    ↓
[SPAN] POST /api/v1/appointments
    ├─ [SPAN] Validate request
    ├─ [SPAN] Check patient eligibility
    ├─ [SPAN] Query available clinician slots
    │  ├─ [SPAN] GET clinical-data-service/clinicians/{id}/availability
    │  └─ [SPAN] SELECT slots FROM clinician_schedule
    ├─ [SPAN] Create appointment record
    │  └─ [SPAN] INSERT INTO appointments
    ├─ [SPAN] Publish event: AppointmentCreated
    │  └─ [SPAN] PUBLISH appointment_events queue
    ├─ [SPAN] Generate confirmation code
    └─ [SPAN] Send confirmation response
         └─ Response time: < 200ms (p95)

Event consumed asynchronously:
    ↓
[SPAN] Consume: AppointmentCreated
    ├─ [SPAN] Notify patient (SMS/email)
    │  └─ [SPAN] POST notification-service/send
    ├─ [SPAN] Notify clinician (calendar sync)
    │  └─ [SPAN] POST calendar-service/create-event
    ├─ [SPAN] Record audit event
    │  └─ [SPAN] INSERT audit_log
    └─ [SPAN] Update analytics (non-blocking)
         └─ [SPAN] POST analytics-service/track-event
```

**Tracing Requirements:**
- Trace ID: Same for sync + all async operations
- Parent-child span relationships: All child spans linked to parent
- Attributes: appointment.id, patient.id, clinician.id, outcome
- Errors: All exceptions recorded with stack traces
- Duration thresholds: P95 latency tracked per span

#### Journey 2: Patient Views Appointments (List + Details)

```
[SPAN] GET /api/v1/appointments?patient_id=pat-123
    ├─ [SPAN] Authenticate request
    ├─ [SPAN] Query appointments
    │  └─ [SPAN] SELECT * FROM appointments WHERE patient_id = ?
    ├─ [SPAN] Hydrate appointment details
    │  ├─ [SPAN] Fetch clinician info (parallel)
    │  │  └─ [SPAN] SELECT clinicians WHERE id IN (...)
    │  └─ [SPAN] Fetch location info (parallel)
    │     └─ [SPAN] SELECT locations WHERE id IN (...)
    ├─ [SPAN] Apply pagination
    └─ Response time: < 100ms (p95)

[SPAN] GET /api/v1/appointments/{id}
    ├─ [SPAN] Authenticate and authorize
    ├─ [SPAN] Query appointment
    │  └─ [SPAN] SELECT * FROM appointments WHERE id = ?
    ├─ [SPAN] Fetch related data (async)
    │  ├─ Clinician profile
    │  ├─ Patient notes
    │  └─ Encounter history
    └─ Response time: < 150ms (p95)
```

#### Journey 3: Appointment Confirmation/Cancellation

```
[SPAN] PATCH /api/v1/appointments/{id}/confirm
    ├─ [SPAN] Validate state transition
    ├─ [SPAN] Check confirmation deadline
    ├─ [SPAN] Update appointment status
    │  └─ [SPAN] UPDATE appointments SET status = 'CONFIRMED'
    ├─ [SPAN] Publish event: AppointmentConfirmed
    │  └─ [SPAN] PUBLISH appointment_events
    └─ Response time: < 100ms (p95)

[SPAN] DELETE /api/v1/appointments/{id}
    ├─ [SPAN] Validate cancellation policy
    ├─ [SPAN] Update appointment status
    │  └─ [SPAN] UPDATE appointments SET status = 'CANCELLED'
    ├─ [SPAN] Publish event: AppointmentCancelled
    │  └─ [SPAN] PUBLISH appointment_events
    ├─ [SPAN] Process refund (if applicable)
    │  └─ [SPAN] POST payment-service/refund
    └─ Response time: < 150ms (p95)
```

---

## 3. Critical Path Analysis

### 3.1 Appointment Creation Critical Path

```
Critical Path (determines response time):
1. Validate request [5ms]
2. Check eligibility [20ms]
3. Query available slots [40ms]  ← Longest single operation
4. Create appointment [25ms]
5. Publish event [10ms]
────────────────
Total: 100ms P95 target

Non-critical (async, parallel):
- Notify patient [background]
- Notify clinician [background]
- Analytics [background]
```

**SLO Target:** Response time p95 < 200ms (includes network)

### 3.2 List Appointments Critical Path

```
Critical Path:
1. Authenticate [3ms]
2. Query appointments [30ms]  ← Bottleneck if many appointments
3. Hydrate details [40ms]     ← Parallelized where possible
────────────────
Total: ~73ms

Optimization: Database query needs index on patient_id
```

**SLO Target:** Response time p95 < 100ms

---

## 4. Span Coverage by Journey

### 4.1 Appointment Creation Coverage Matrix

| Component | Span Type | Min Spans | Coverage |
|---|---|---|---|
| HTTP Request | server | 1 | Entry point |
| Validation | internal | 1-2 | Request schema + business rules |
| Auth | client | 1 | Authorization service call |
| Database | client | 2-3 | Eligibility query + insert |
| External Services | client | 1-2 | Clinical data, notification service |
| Events | internal | 1 | Event publish |
| **Total per request** | - | **7-10** | **100%** |

### 4.2 Async Event Consumer Coverage

| Component | Span Type | Min Spans | Coverage |
|---|---|---|---|
| Event Consumption | internal | 1 | Message dequeue |
| Notification | client | 2 | SMS + Email services |
| Audit Logging | client | 1 | Audit service |
| Calendar Sync | client | 1 | Calendar service |
| **Total per event** | - | **5-6** | **100%** |

---

## 5. Data Enrichment Requirements

### 5.1 Required Span Tags by Journey

#### Appointment Creation

```
HTTP Server Span (root):
  http.method = "POST"
  http.url = "/api/v1/appointments"
  http.status_code = 201
  http.client_ip = "192.168.1.100"
  user_id = "user-123"
  tenant_id = "tenant-456"
  
Business Span Tags:
  appointment.id = "apt-001"
  patient.id = "pat-123"
  clinician.id = "clin-456"
  appointment.type = "CONSULTATION"
  appointment.duration_minutes = 30
  appointment.created_at = "2026-06-22T10:00:00Z"
  
Error Span Tags (if applicable):
  error.type = "ValidationException"
  error.message = "Patient not eligible"
  http.status_code = 400
  span.status = "ERROR"
```

#### List Appointments

```
HTTP Server Span (root):
  http.method = "GET"
  http.url = "/api/v1/appointments"
  http.status_code = 200
  query_params = "patient_id=pat-123&page=1&page_size=20"
  
Business Span Tags:
  patient.id = "pat-123"
  appointments_returned = 15
  total_count = 127
  response_time_ms = 85
  
Database Span Tags:
  db.operation = "SELECT"
  db.statement = "SELECT * FROM appointments WHERE patient_id = ?"
  db.rows_returned = 15
  db.query_time_ms = 45
```

---

## 6. Error Path Tracing

### 6.1 Expected Error Scenarios

For each journey, trace these error paths:

#### Appointment Creation Errors

```
Span Path: POST /api/v1/appointments → ValidationException

Trace Attributes:
  error.type = "ValidationException"
  error.message = "Patient ID is required"
  error.stack_trace = "at Validators.ValidateAsync() ..."
  span.status = "ERROR"
  http.status_code = 400
  
Expected Spans:
  1. HTTP Server span (400)
  2. Validate Span (ERROR)
  3. Response span (error serialization)
```

#### Database Connection Error

```
Span Path: POST /api/v1/appointments → 
  → Query Available Slots → ConnectionException

Trace Attributes:
  error.type = "SqlException"
  error.message = "Failed to connect to database"
  db.connection_timeout = 5000
  db.retry_count = 3
  span.status = "ERROR"
  http.status_code = 503 (Service Unavailable)
```

#### External Service Timeout

```
Span Path: POST /api/v1/appointments → 
  → Notify Clinician → TimeoutException

Trace Attributes:
  peer.service = "notification-service"
  http.status_code = 504 (timeout)
  error.type = "TimeoutException"
  error.message = "Request timeout after 30 seconds"
  http.request_duration_ms = 30005
  span.status = "ERROR"
```

---

## 7. Async Operation Tracing

### 7.1 Event-Driven Span Linkage

```
Synchronous Flow (response to user):
┌─────────────────────────────────┐
│ POST /api/v1/appointments       │ ← User waits here
│ traceId: abc-123                │
│ spanId: span-001                │
│ Status: 201 Created             │
└─────────────────────────────────┘
                ↓
Asynchronous Flow (background):
┌─────────────────────────────────┐
│ Message: AppointmentCreated     │ ← No user waiting
│ traceId: abc-123 (SAME!)        │ ← Link to sync trace
│ spanId: span-async-001 (new)    │
│ parentSpanId: span-001          │ ← Child of sync
│ Links: [abc-123/span-001]       │ ← Explicit link
└─────────────────────────────────┘
```

**Implementation:**
```csharp
// In synchronous handler
var syncSpanId = Activity.Current?.SpanId;

// When publishing event
var evt = new AppointmentCreatedEvent
{
    CorrelationId = correlationId,
    TraceId = Activity.Current?.TraceId.ToString(),
    SpanId = syncSpanId.ToString(),
    // ...
};

// In async consumer
var linkedSpans = new[]
{
    new ActivityLink(
        new ActivityContext(
            ActivityTraceId.CreateFromString(evt.TraceId),
            ActivitySpanId.CreateFromString(evt.SpanId),
            ActivityTraceFlags.Recorded))
};

using var activity = new Activity("AppointmentCreatedConsumer")
    .AddLinks(linkedSpans)
    .Start();
```

---

## 8. Journey Testing Checklist

For each critical journey, verify:

- [ ] **Synchronous traces:** All sync calls captured in single trace tree
- [ ] **Async spans:** Async operations linked to sync trace
- [ ] **Error traces:** Exceptions recorded with full context
- [ ] **Performance:** P95 latency meets SLO target
- [ ] **Span naming:** Follows conventions (no high-cardinality IDs in names)
- [ ] **Attributes:** All required business attributes present
- [ ] **Cross-service:** Trace propagates across service boundaries
- [ ] **Query-ability:** Traces searchable by key attributes (patient_id, appointment_id)

---

## 9. Monitoring by Journey

### 9.1 Key Metrics per Journey

#### Appointment Creation

| Metric | Target | Query |
|---|---|---|
| Request Success Rate | 99.5% | `span.name="POST /api/v1/appointments" span.status="OK"` |
| P95 Latency | 200ms | `span.name="POST /api/v1/appointments" histogram_quantile(0.95, duration_ms)` |
| Error Rate | < 0.5% | `span.name="POST /api/v1/appointments" span.status="ERROR"` |
| DB Query Latency | < 50ms | `span.name="SELECT appointments" histogram_quantile(0.95, duration_ms)` |

#### List Appointments

| Metric | Target | Query |
|---|---|---|
| Request Success Rate | 99.9% | `span.name="GET /api/v1/appointments" span.status="OK"` |
| P95 Latency | 100ms | `span.name="GET /api/v1/appointments" histogram_quantile(0.95, duration_ms)` |
| Average Result Set Size | < 100 appointments | `span.name="GET /api/v1/appointments" avg(appointments_returned)` |

---

## 10. Coverage Validation Plan

### 10.1 Coverage Matrix by Service

| Service | Appointment Creation | List Appointments | Confirmation | Comments |
|---|---|---|---|---|
| API Gateway | ✅ | ✅ | ✅ | All entry points traced |
| Appointment Service | ✅ | ✅ | ✅ | Core business logic |
| Clinical Data Service | ✅ | ✅ | ❌ | Only when eligibility checked |
| Notification Service | ✅ (async) | ❌ | ✅ (async) | Async events only |
| Payment Service | ✅ (if paid) | ❌ | ✅ (refunds) | On demand |
| Analytics Service | ✅ (async) | ✅ (async) | ✅ (async) | Event consumer |

**Coverage Target:** 100% of critical journeys fully traced

---

## 11. Span Generation Examples

### 11.1 Appointment Creation Trace

```json
{
  "trace_id": "0af7651916cd43dd8448eb211c80319c",
  "spans": [
    {
      "span_id": "b7ad6b7169203331",
      "parent_span_id": null,
      "name": "POST /api/v1/appointments",
      "start_time": "2026-06-22T10:00:00.000Z",
      "end_time": "2026-06-22T10:00:00.145Z",
      "status": "OK",
      "attributes": {
        "http.method": "POST",
        "http.status_code": 201,
        "appointment.id": "apt-001",
        "duration_ms": 145
      }
    },
    {
      "span_id": "c8be6c7269204332",
      "parent_span_id": "b7ad6b7169203331",
      "name": "Validate Request",
      "duration_ms": 5,
      "status": "OK"
    },
    {
      "span_id": "d9cf7d7369205333",
      "parent_span_id": "b7ad6b7169203331",
      "name": "SELECT appointments",
      "duration_ms": 40,
      "status": "OK",
      "attributes": {
        "db.system": "postgresql",
        "db.statement": "SELECT * FROM clinician_schedule"
      }
    }
  ]
}
```

---

## 12. References

- [TRACE-1: Instrumentation Baseline](instrumentation-baseline.md)
- [METRIC-1: Golden Signal Metrics](../metrics/golden-signals.md)
- [SLO-1: SLO Definition](../slo/slo-definition.md)
- OpenTelemetry: https://opentelemetry.io/docs/

**Next:** [METRIC-1: Golden Signal Metrics](../metrics/golden-signals.md)
