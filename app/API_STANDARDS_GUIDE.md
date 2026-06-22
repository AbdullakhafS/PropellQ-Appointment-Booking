# API Standards and Shared Middleware Guide

**Task**: TASK-098: Define API Standards and Shared Middleware Contracts  
**Epic**: EP-TECH-001 (Technical Infrastructure)  
**Priority**: CRITICAL  
**Status**: COMPLETE

## Overview

This guide defines the PropellQ API contract and shared middleware model for consistent request/response behavior, error handling, idempotency, and versioning across all services.

## Table of Contents

1. [API Contract (STD-1)](#api-contract)
2. [Collection Semantics (STD-2)](#collection-semantics)
3. [Middleware Contracts](#middleware-contracts)
4. [Governance Policies](#governance-policies)
5. [Implementation Examples](#implementation-examples)
6. [Compliance Checklist](#compliance-checklist)

---

## API Contract (STD-1)

### Standard Response Envelope (AC-1)

All API responses MUST follow the standard envelope format:

```json
{
  "success": boolean,
  "data": object | array | null,
  "error": {
    "code": string,
    "message": string,
    "field": string | null,
    "details": object | null
  } | null,
  "meta": object,
  "correlation_id": string,
  "timestamp": string (ISO 8601),
  "api_version": string
}
```

#### Required Fields

- **success**: Boolean indicating request success
- **correlation_id**: Unique ID for request tracking (UUID v4)
- **timestamp**: ISO 8601 timestamp when response was generated
- **api_version**: Current API version (e.g., "1.0")

#### Conditional Fields

- **data**: Present on success, contains result payload
- **error**: Present on failure, contains error details

#### Optional Fields

- **meta**: Additional metadata (pagination info, rate limits, etc.)

### Status Codes

| Code | Meaning | When to Use |
|------|---------|------------|
| 200 | OK | Successful GET/POST/PUT/DELETE |
| 201 | Created | Resource created (e.g., POST returning new ID) |
| 204 | No Content | Success with no response body |
| 400 | Bad Request | Validation error (AC-2) |
| 401 | Unauthorized | Authentication required (AC-5) |
| 403 | Forbidden | Authorization failed (AC-5) |
| 409 | Conflict | Duplicate request / idempotency violation (AC-3) |
| 500 | Internal Error | Server error |

### Naming Conventions

#### Endpoint Paths

- Use **kebab-case** for multi-word segments: `/api/appointments/search`
- Use **plural nouns** for resources: `/api/appointments`, `/api/providers`
- Use **hierarchical structure**: `/api/appointments/{id}/confirmations`

#### Request/Response Fields

- Use **camelCase** for JSON fields: `firstName`, `appointmentId`
- Use **_id** suffix for identifiers: `appointmentId`, `providerId`
- Use **createdAt**, **updatedAt** for timestamps
- Use **is_** prefix for boolean fields: `isConfirmed`, `isActive`

#### Error Codes

Standard error codes follow `SCREAMING_SNAKE_CASE`:

```python
VALIDATION_ERROR          # Input validation failed
INVALID_PARAMETER         # Parameter is invalid type/format
MISSING_REQUIRED_FIELD    # Required field missing
UNAUTHORIZED              # No authentication token
FORBIDDEN                 # Insufficient permissions
TOKEN_EXPIRED             # Auth token expired
INVALID_TOKEN             # Token invalid or malformed
NOT_FOUND                 # Resource not found
CONFLICT                  # State conflict (e.g., double-book)
RESOURCE_ALREADY_EXISTS   # Duplicate resource
IDEMPOTENCY_CONFLICT      # Conflicting idempotency key
DUPLICATE_REQUEST         # Duplicate idempotent request
INTERNAL_ERROR            # Unhandled server error
SERVICE_UNAVAILABLE       # Service temporarily unavailable
UNAVAILABLE_SLOT          # Requested slot unavailable
APPOINTMENT_CONFLICT      # Appointment time conflict
INVALID_STATE_TRANSITION  # Business logic violation
```

---

## Collection Semantics (STD-2)

### Pagination Parameters

Standard query parameters for paginated endpoints:

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| page | int | 1 | ∞ | Page number (1-indexed) |
| limit | int | 20 | 100 | Items per page |
| sort_by | string | (none) | - | Field to sort by |
| sort_order | string | asc | - | "asc" or "desc" |

### Paginated Response Format

```json
{
  "success": true,
  "data": {
    "items": [
      {"id": 1, "name": "Appointment 1"},
      {"id": 2, "name": "Appointment 2"}
    ],
    "total": 42,
    "page": 1,
    "limit": 20,
    "total_pages": 3,
    "has_more": true,
    "sort_by": "createdAt",
    "sort_order": "desc"
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-06-22T10:30:00Z",
  "api_version": "1.0"
}
```

### Filtering

Use query parameters for filters. Examples:

```
GET /api/appointments?specialization=cardiology&status=available
GET /api/providers?rating_min=4.5&availability=true
```

---

## Middleware Contracts

### MID-1: Error/Exception Middleware (AC-2, AC-5)

**Responsibility**: Convert exceptions to standardized error responses

**Contract**:

```python
from src.middleware_contract import ErrorHandler, MiddlewareException

handler = ErrorHandler()

# Converts any exception to standard response
status_code, response_dict = handler.handle_error(exception, correlation_id)

# Returns (status_code, response_dict)
# Response dict conforms to standard envelope
```

**Supported Exceptions**:

- `ValidationError`: validation/input errors (400)
- `AuthenticationError`: auth token issues (401)
- `AuthorizationError`: permission issues (403)
- `IdempotencyError`: duplicate request (409)
- Standard `Exception`: generic errors (500)

### MID-2: Validation and Auth Middleware (AC-5)

**Responsibility**: Validate requests and authenticate/authorize users

**Validation Contract**:

```python
from src.middleware_contract import ValidationMiddleware, ValidationError

validator = ValidationMiddleware()

# Define schema
schema = {
    "required": ["email", "name"],
    "types": {"age": int},
    "custom": {
        "email": lambda x: "@" in x
    }
}

# Validate request
valid, errors = validator.validate_request(request_data, schema)
if not valid:
    raise ValidationError(errors[0], field="email")
```

**Auth Contract**:

```python
from src.middleware_contract import AuthMiddleware, AuthenticationError

auth = AuthMiddleware()

# Register user token
auth.register_token(token, {"user_id": "123", "role": "patient"})

# Authenticate request
auth_header = environ.get("HTTP_AUTHORIZATION")
authenticated, user_context = auth.authenticate(auth_header, environ)
if not authenticated:
    raise AuthenticationError("Invalid or missing token")
```

### MID-3: Idempotency Middleware (AC-3)

**Responsibility**: Prevent duplicate side effects on retried requests

**Contract**:

```python
from src.middleware_contract import IdempotencyMiddleware, IdempotencyError

middleware = IdempotencyMiddleware()

# 1. Extract idempotency key from request
idempotency_key = middleware.extract_idempotency_key(environ)
if not idempotency_key:
    raise IdempotencyError("Idempotency-Key header required")

# 2. Compute request hash
request_hash = middleware.compute_request_hash(body, method, path)

# 3. Check for duplicate
is_duplicate, cached_response = middleware.check_duplicate(idempotency_key, request_hash)
if is_duplicate:
    return cached_response  # Return cached response

# 4. Process request...
response = process_request(...)

# 5. Record response for future replays
middleware.record_response(idempotency_key, request_hash, response, 200)

return response
```

**Usage Requirements**:

- All POST/PUT/PATCH endpoints SHOULD support `Idempotency-Key` header
- Key format: UUID v4 or other unique string (max 255 chars)
- Replay window: 24 hours (configurable)
- Conflict detection: Different request with same key raises 409

---

## Governance Policies

### GOV-1: Conformance Checklist (AC-1, GOV-1)

Before deploying an endpoint, verify:

**Request/Response Format**:
- [ ] Response contains `success`, `correlation_id`, `timestamp`, `api_version`
- [ ] Success responses include `data` field
- [ ] Error responses include `error` with `code` and `message`
- [ ] All field names use camelCase
- [ ] All ID fields end with `_id`

**Error Handling**:
- [ ] Validation errors return 400 with `VALIDATION_ERROR` code
- [ ] Auth errors return 401 with `UNAUTHORIZED` code
- [ ] Permission errors return 403 with `FORBIDDEN` code
- [ ] Duplicates return 409 with conflict info
- [ ] All errors include correlation ID

**Collections**:
- [ ] Paginated endpoints accept `page`, `limit`, `sort_by`, `sort_order`
- [ ] Pagination response includes `total`, `total_pages`, `has_more`
- [ ] Defaults: page=1, limit=20, sort_order=asc
- [ ] Limit capped at 100

**Idempotency** (for write endpoints):
- [ ] POST/PUT/PATCH endpoints accept `Idempotency-Key` header
- [ ] Duplicate requests return 409 or cached response
- [ ] Key checked before processing
- [ ] Response recorded for replay

**Tests**:
- [ ] Unit tests for happy path and error cases
- [ ] Contract conformance tests with validator
- [ ] Tests for pagination edge cases
- [ ] Tests for idempotency (duplicate, conflict)

### GOV-2: Versioning and Deprecation Policy (AC-6, GOV-2)

#### Version Lifecycle

```
1.0 (Released) ---(6 months)---> 1.0 (Deprecated) ---(6 months)---> 1.0 (Sunset)
                                      ↓
                              1.1 Released
                              1.2 Released
```

#### Policy Rules

1. **Current**: Latest minor version is actively supported
2. **Deprecated**: Previous minor version (6-month window)
   - Must include deprecation header: `Deprecated: true; sunset="2026-12-01T00:00:00Z"`
   - Documentation must include migration guide
3. **Sunset**: End-of-life version, removed from service

#### Breaking Changes

Breaking changes REQUIRE:

1. **New major version** (e.g., 1.0 → 2.0)
2. **6-month deprecation notice** with:
   - Clear migration guide
   - Deprecation date
   - Sunset date
   - Contact for questions
3. **Parallel operation** (old and new endpoints during window)

#### Compatible Changes

No new version needed:

- Adding optional fields
- Adding optional query parameters
- Adding new endpoints
- Adding new error codes
- Extending enum values (add-only)

#### Incompatible Changes

Require major version bump:

- Removing fields
- Removing endpoints
- Changing field types
- Renaming fields/paths
- Changing required parameters
- Changing status codes

---

## Implementation Examples

### Example 1: Search Appointments (Paginated, Filtered)

**Request**:
```http
GET /api/appointments/search?specialization=cardiology&page=1&limit=20&sort_by=date&sort_order=asc
```

**Response**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "providerId": 42,
        "specialization": "cardiology",
        "startTime": "2026-07-01T10:00:00Z",
        "endTime": "2026-07-01T10:30:00Z",
        "available": true
      }
    ],
    "total": 150,
    "page": 1,
    "limit": 20,
    "total_pages": 8,
    "has_more": true,
    "sort_by": "date",
    "sort_order": "asc"
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-06-22T10:30:00Z",
  "api_version": "1.0"
}
```

### Example 2: Create Appointment with Idempotency

**Request**:
```http
POST /api/appointments/book
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440001
Content-Type: application/json

{
  "appointmentId": 1,
  "patientId": 99,
  "notes": "Requires translation"
}
```

**Response (First Request)**:
```json
{
  "success": true,
  "data": {
    "id": 2001,
    "appointmentId": 1,
    "patientId": 99,
    "status": "confirmed",
    "createdAt": "2026-06-22T10:30:00Z"
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-06-22T10:30:00Z",
  "api_version": "1.0"
}
```

**Response (Retry with Same Key)**:
```json
{
  "success": true,
  "data": {
    "id": 2001,
    "appointmentId": 1,
    "patientId": 99,
    "status": "confirmed",
    "createdAt": "2026-06-22T10:30:00Z"
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-06-22T10:30:00Z",
  "api_version": "1.0"
}
```

### Example 3: Validation Error

**Request**:
```http
POST /api/appointments/book
Content-Type: application/json

{
  "appointmentId": 1
  // Missing patientId
}
```

**Response**:
```json
{
  "success": false,
  "error": {
    "code": "MISSING_REQUIRED_FIELD",
    "message": "Missing required field: patientId",
    "field": "patientId"
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-06-22T10:30:00Z",
  "api_version": "1.0"
}
```

---

## Compliance Checklist

### AC-1: New Endpoints Conform to Contract Template

- [ ] All endpoints return standard envelope
- [ ] Correlation IDs included
- [ ] Proper status codes used
- [ ] Field naming conventions followed

### AC-2: Error Responses Use Standard Envelope with Correlation ID/Code

- [ ] Errors include code (e.g., `VALIDATION_ERROR`)
- [ ] Errors include message
- [ ] Correlation ID present in all responses
- [ ] Error field information included for validation errors

### AC-3: Idempotency Keys Prevent Duplicate Write Side Effects

- [ ] Write endpoints support `Idempotency-Key` header
- [ ] Duplicate requests return cached response
- [ ] Conflicting requests rejected (409)
- [ ] 24-hour replay window enforced

### AC-4: Pagination/Sort Conventions Consistent

- [ ] All collections support `page`, `limit`, `sort_by`, `sort_order`
- [ ] Default page=1, limit=20, limit_max=100
- [ ] Responses include pagination metadata
- [ ] `has_more` field indicates more pages

### AC-5: Shared Middleware Handles Auth/Validation Errors in Standard Format

- [ ] All validation errors use standard format
- [ ] All auth errors use standard format
- [ ] Middleware preserves correlation IDs
- [ ] Error handler converts all exceptions

### AC-6: Breaking Change Proposals Enforce Versioning/Deprecation Policy

- [ ] Breaking changes create new major version
- [ ] Deprecation notices include sunset date
- [ ] 6-month deprecation window enforced
- [ ] Migration guides provided

---

## Next Steps

1. **Pilot Adoption**: Implement standards in one service endpoint
2. **Lint Rules**: Add PR checks for conformance
3. **Monitoring**: Track API errors and latencies
4. **Feedback**: Collect issues and refinements
5. **Rollout**: Deploy to all services
