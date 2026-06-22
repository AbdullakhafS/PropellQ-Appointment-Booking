# STD-1: API Contract Specification

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Approvals:** Architecture Review (Pending)

---

## 1. Overview

This document establishes the standard API contract that all services MUST follow. It defines:
- Request/response envelope structures
- Naming conventions and casing rules
- HTTP status code mappings
- Standard error response envelope
- Correlation ID propagation
- Request/response validation principles

---

## 2. Request Envelope Structure

### 2.1 Standard Request Structure

All API requests MUST follow this structure:

```json
{
  "requestId": "uuid-v4",
  "correlationId": "uuid-v4 or inherited from header",
  "timestamp": "ISO-8601 UTC",
  "apiVersion": "v1",
  "payload": {
    "field1": "value1",
    "field2": 123
  }
}
```

### 2.2 HTTP Headers

| Header | Required | Format | Example |
|--------|----------|--------|---------|
| `Content-Type` | Yes | application/json | `application/json; charset=utf-8` |
| `Accept` | No | application/json | `application/json` |
| `X-Correlation-ID` | No | UUID v4 | `123e4567-e89b-12d3-a456-426614174000` |
| `X-Request-ID` | No | UUID v4 | `987f6543-e89b-12d3-a456-426614174111` |
| `Authorization` | Conditional | Bearer {token} | `Bearer eyJhbGciOi...` |
| `X-API-Version` | No | Semantic version | `X-API-Version: 1.0.0` |

### 2.3 Naming Conventions

- **JSON field names:** `camelCase` (e.g., `firstName`, `appointmentId`, `createdAt`)
- **Query parameters:** `snake_case` (e.g., `page_number`, `sort_by`, `filter_status`)
- **Path parameters:** `camelCase` in routes, refer by ID or semantic name (e.g., `/appointments/{appointmentId}`)
- **Enum values:** `SCREAMING_SNAKE_CASE` (e.g., `PENDING`, `IN_PROGRESS`, `COMPLETED`)
- **Resource names:** Plural nouns (e.g., `/appointments`, `/patients`, `/clinicians`)

---

## 3. Response Envelope Structure

### 3.1 Successful Response (2xx)

All successful responses MUST follow this structure:

```json
{
  "statusCode": 200,
  "success": true,
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "requestId": "987f6543-e89b-12d3-a456-426614174111",
  "timestamp": "2026-06-22T14:30:00Z",
  "data": {
    "id": "apt-001",
    "patientId": "pat-123",
    "scheduledTime": "2026-07-01T10:00:00Z"
  },
  "meta": {
    "version": "1.0.0"
  }
}
```

### 3.2 List Response with Pagination

```json
{
  "statusCode": 200,
  "success": true,
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:30:00Z",
  "data": [
    { "id": "apt-001", "patientId": "pat-123" },
    { "id": "apt-002", "patientId": "pat-124" }
  ],
  "pagination": {
    "pageNumber": 1,
    "pageSize": 20,
    "totalItems": 150,
    "totalPages": 8,
    "hasNextPage": true,
    "hasPreviousPage": false
  },
  "meta": {
    "version": "1.0.0"
  }
}
```

### 3.3 Empty Response (204 No Content)

Status code only; no body required.

---

## 4. Error Response Envelope

### 4.1 Standard Error Structure

All error responses MUST follow this structure:

```json
{
  "statusCode": 400,
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "appointmentId",
        "issue": "Invalid UUID format",
        "value": "not-a-uuid"
      },
      {
        "field": "startTime",
        "issue": "Must be in future",
        "value": "2026-01-01T10:00:00Z"
      }
    ]
  },
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "requestId": "987f6543-e89b-12d3-a456-426614174111",
  "timestamp": "2026-06-22T14:30:00Z"
}
```

### 4.2 Error Code Reference

| HTTP Status | Error Code | Description | Example Scenario |
|-------------|-----------|-------------|-------------------|
| 400 | `VALIDATION_ERROR` | Request data fails schema/business validation | Invalid email format |
| 400 | `INVALID_REQUEST` | Malformed request structure | Missing required field |
| 400 | `CONFLICT` | Resource state conflict (e.g., duplicate ID) | Appointment slot unavailable |
| 401 | `UNAUTHORIZED` | Missing/invalid authentication | No bearer token |
| 403 | `FORBIDDEN` | User lacks permission | Non-admin calling admin endpoint |
| 404 | `NOT_FOUND` | Resource does not exist | Appointment ID not found |
| 409 | `RESOURCE_CONFLICT` | Concurrent modification/conflict | Optimistic lock failure |
| 422 | `UNPROCESSABLE_ENTITY` | Request semantically invalid | Requesting reschedule on completed appointment |
| 429 | `RATE_LIMITED` | Rate limit exceeded | Too many requests |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected server error | Database connection failure |
| 502 | `INVALID_GATEWAY` | External service dependency failure | Payment processor down |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily down | Maintenance window |

### 4.3 Error Details Object

Each error detail MUST include:

- **field** (string): JSON path or field name where error occurred
- **issue** (string): Human-readable description of the problem
- **code** (string, optional): Machine-readable error code for this specific field
- **value** (any, optional): The problematic value (redact PII/secrets)

---

## 5. Synchronous Endpoint Examples

### 5.1 GET - Retrieve Single Resource

**Request:**
```http
GET /api/v1/appointments/apt-001
X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000
Accept: application/json
```

**Response (200 OK):**
```json
{
  "statusCode": 200,
  "success": true,
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:30:00Z",
  "data": {
    "id": "apt-001",
    "patientId": "pat-123",
    "clinicianId": "clin-456",
    "appointmentType": "CONSULTATION",
    "scheduledTime": "2026-07-01T10:00:00Z",
    "status": "CONFIRMED",
    "createdAt": "2026-06-20T09:15:00Z",
    "updatedAt": "2026-06-22T14:30:00Z"
  },
  "meta": {
    "version": "1.0.0"
  }
}
```

### 5.2 POST - Create Resource

**Request:**
```http
POST /api/v1/appointments
Content-Type: application/json
X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000

{
  "patientId": "pat-123",
  "clinicianId": "clin-456",
  "appointmentType": "CONSULTATION",
  "scheduledTime": "2026-07-01T10:00:00Z",
  "duration": 30
}
```

**Response (201 Created):**
```json
{
  "statusCode": 201,
  "success": true,
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:30:00Z",
  "data": {
    "id": "apt-001",
    "patientId": "pat-123",
    "clinicianId": "clin-456",
    "appointmentType": "CONSULTATION",
    "scheduledTime": "2026-07-01T10:00:00Z",
    "status": "PENDING",
    "duration": 30,
    "createdAt": "2026-06-22T14:30:00Z"
  },
  "meta": {
    "version": "1.0.0"
  }
}
```

**Response (400 Bad Request):**
```json
{
  "statusCode": 400,
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "scheduledTime",
        "issue": "Must be in the future",
        "value": "2026-05-01T10:00:00Z"
      }
    ]
  },
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:30:00Z"
}
```

### 5.3 PUT - Update Resource

**Request:**
```http
PUT /api/v1/appointments/apt-001
Content-Type: application/json
X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000
X-Idempotency-Key: abc-123-def-456

{
  "status": "CONFIRMED",
  "notes": "Confirmed by patient"
}
```

**Response (200 OK):**
```json
{
  "statusCode": 200,
  "success": true,
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:30:00Z",
  "data": {
    "id": "apt-001",
    "patientId": "pat-123",
    "status": "CONFIRMED",
    "notes": "Confirmed by patient",
    "updatedAt": "2026-06-22T14:30:00Z"
  },
  "meta": {
    "version": "1.0.0"
  }
}
```

### 5.4 PATCH - Partial Update

**Request:**
```http
PATCH /api/v1/appointments/apt-001/status
Content-Type: application/json
X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000

{
  "status": "CANCELLED",
  "cancellationReason": "Patient requested reschedule"
}
```

**Response (200 OK):**
Similar to PUT response above.

### 5.5 DELETE - Remove Resource

**Request:**
```http
DELETE /api/v1/appointments/apt-001
X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000
```

**Response (204 No Content):**
```
(empty body, status code only)
```

### 5.6 GET - List with Pagination and Filtering

**Request:**
```http
GET /api/v1/appointments?page_number=1&page_size=20&status=CONFIRMED&sort_by=-scheduledTime
X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000
Accept: application/json
```

**Response (200 OK):**
```json
{
  "statusCode": 200,
  "success": true,
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:30:00Z",
  "data": [
    {
      "id": "apt-001",
      "patientId": "pat-123",
      "status": "CONFIRMED",
      "scheduledTime": "2026-07-05T14:00:00Z"
    },
    {
      "id": "apt-002",
      "patientId": "pat-124",
      "status": "CONFIRMED",
      "scheduledTime": "2026-07-04T10:00:00Z"
    }
  ],
  "pagination": {
    "pageNumber": 1,
    "pageSize": 20,
    "totalItems": 45,
    "totalPages": 3,
    "hasNextPage": true,
    "hasPreviousPage": false
  },
  "meta": {
    "version": "1.0.0"
  }
}
```

---

## 6. Asynchronous Endpoint Pattern

For long-running operations, use the polling or webhook pattern:

### 6.1 Polling Pattern (Recommended for Phase 1)

**Request (Initiate async operation):**
```http
POST /api/v1/appointments/batch-import
Content-Type: application/json
X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000

{
  "sourceFormat": "CSV",
  "fileSize": 2048000
}
```

**Response (202 Accepted):**
```json
{
  "statusCode": 202,
  "success": true,
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:30:00Z",
  "data": {
    "operationId": "op-import-001",
    "status": "IN_PROGRESS",
    "statusUrl": "/api/v1/appointments/batch-import/op-import-001/status",
    "estimatedCompletionTime": "2026-06-22T14:35:00Z"
  },
  "meta": {
    "version": "1.0.0"
  }
}
```

**Poll for Status:**
```http
GET /api/v1/appointments/batch-import/op-import-001/status
X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000
```

**Response (200 OK - In Progress):**
```json
{
  "statusCode": 200,
  "success": true,
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:32:00Z",
  "data": {
    "operationId": "op-import-001",
    "status": "IN_PROGRESS",
    "progress": {
      "processed": 150,
      "total": 500,
      "percentComplete": 30
    },
    "statusUrl": "/api/v1/appointments/batch-import/op-import-001/status"
  }
}
```

**Response (200 OK - Completed):**
```json
{
  "statusCode": 200,
  "success": true,
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:35:00Z",
  "data": {
    "operationId": "op-import-001",
    "status": "COMPLETED",
    "result": {
      "imported": 500,
      "failed": 0,
      "resultUrl": "/api/v1/appointments/batch-import/op-import-001/result"
    }
  }
}
```

---

## 7. HTTP Status Code Mapping

| Status | Use Case | Example |
|--------|----------|---------|
| **200 OK** | Successful GET, PUT, PATCH | Retrieve appointment, update status |
| **201 Created** | Resource successfully created | POST to create appointment |
| **202 Accepted** | Async operation accepted | Long-running batch import started |
| **204 No Content** | Successful deletion or empty result | DELETE appointment, empty list |
| **400 Bad Request** | Client error in request format | Invalid JSON, missing required field |
| **401 Unauthorized** | Authentication required or failed | Missing token, expired token |
| **403 Forbidden** | User lacks permission | Non-clinician accessing clinical data |
| **404 Not Found** | Resource does not exist | Appointment ID not found |
| **409 Conflict** | Resource state conflict | Slot no longer available, concurrent update |
| **422 Unprocessable Entity** | Request semantically invalid | Reschedule completed appointment |
| **429 Too Many Requests** | Rate limit exceeded | Rate limiter activated |
| **500 Internal Server Error** | Unexpected server error | Database connection timeout |
| **502 Bad Gateway** | External service failure | Payment processor unavailable |
| **503 Service Unavailable** | Service temporarily down | Maintenance window |

---

## 8. Correlation ID Propagation

1. **Client generates or provides:** X-Correlation-ID header
2. **Service receives request:** Extract X-Correlation-ID from header
3. **Service processes:** Include correlationId in all logs, internal calls, and response
4. **Service responds:** Include correlationId in response envelope
5. **All downstream calls:** Pass correlationId to dependent services

---

## 9. API Versioning Strategy

### 9.1 URL-Based Versioning (Preferred)

```
/api/v1/appointments
/api/v2/appointments
```

### 9.2 Header-Based Versioning (Alternative)

```
Accept: application/vnd.propellq.v1+json
X-API-Version: 1.0.0
```

### 9.3 Version Lifecycle

- **CURRENT:** Latest stable version, all features active
- **DEPRECATED:** Active but scheduled for removal (min. 6 months notice)
- **SUNSET:** Removed from production (only in documentation)

---

## 10. Validation Rules

### 10.1 Request Validation Priority

1. **Schema validation** (JSON structure, field types)
2. **Format validation** (email, UUID, ISO-8601 date)
3. **Business logic validation** (domain rules, constraints)

### 10.2 Validation Error Response

Always include detailed error array with:
- Field path where validation failed
- Issue description
- Optionally: problematic value (redact PII)
- Optionally: suggested correction

---

## 11. Security Considerations

- All requests and responses MUST use TLS 1.2+
- Sensitive data (passwords, tokens, PII) MUST be redacted from error responses
- Correlation IDs MUST be generated server-side if not provided by client
- Request IDs MUST be unique per request
- Authorization errors MUST NOT reveal resource existence

---

## 12. Implementation Checklist

Service teams MUST verify:

- [ ] All endpoints follow request envelope structure
- [ ] All responses use standard response envelope
- [ ] Error responses use standard error envelope with proper error codes
- [ ] All endpoints return appropriate HTTP status codes
- [ ] Correlation ID propagation working end-to-end
- [ ] Query parameters use snake_case naming
- [ ] JSON fields use camelCase naming
- [ ] Pagination parameters match standard (pageNumber, pageSize, etc.)
- [ ] API documentation reflects these standards
- [ ] Unit tests validate envelope compliance

---

## 13. Questions and Feedback

For questions about this standard:
- Open issue in: `.propel/context/standards/issues/`
- Architecture review: architecture-team@propellq.local
- Next review date: Q3 2026
