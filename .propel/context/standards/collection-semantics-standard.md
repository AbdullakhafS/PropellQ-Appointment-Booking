# STD-2: Collection Semantics Standard

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Approvals:** Architecture Review (Pending)

---

## 1. Overview

This document establishes standard conventions for collection endpoints, including pagination, filtering, sorting, and response metadata. All collection endpoints MUST implement these standards to ensure consistent behavior across services.

---

## 2. Pagination Standard

### 2.1 Query Parameters

All paginated collection endpoints MUST accept these parameters:

| Parameter | Type | Required | Default | Valid Range | Description |
|-----------|------|----------|---------|-------------|-------------|
| `page_number` | integer | No | 1 | 1 to 999999 | Current page (1-based indexing) |
| `page_size` | integer | No | 20 | 1 to 500 | Records per page (max 500) |

### 2.2 Pagination Response Metadata

All paginated responses MUST include a `pagination` object at root level:

```json
{
  "pagination": {
    "pageNumber": 1,
    "pageSize": 20,
    "totalItems": 150,
    "totalPages": 8,
    "hasNextPage": true,
    "hasPreviousPage": false,
    "firstItemNumber": 1,
    "lastItemNumber": 20
  }
}
```

### 2.3 Pagination Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `pageNumber` | integer | Current page number (1-based) |
| `pageSize` | integer | Records returned on this page |
| `totalItems` | integer | Total records matching filter criteria |
| `totalPages` | integer | Calculated as ceil(totalItems / pageSize) |
| `hasNextPage` | boolean | True if current page is not the last |
| `hasPreviousPage` | boolean | True if current page is not the first |
| `firstItemNumber` | integer | Ordinal of first item on page (for UI display) |
| `lastItemNumber` | integer | Ordinal of last item on page (for UI display) |

### 2.4 Pagination Examples

**Request (First page):**
```http
GET /api/v1/appointments?page_number=1&page_size=10
```

**Response:**
```json
{
  "statusCode": 200,
  "success": true,
  "data": [
    {"id": "apt-001", "patientId": "pat-123"},
    {"id": "apt-002", "patientId": "pat-124"},
    ...
  ],
  "pagination": {
    "pageNumber": 1,
    "pageSize": 10,
    "totalItems": 100,
    "totalPages": 10,
    "hasNextPage": true,
    "hasPreviousPage": false,
    "firstItemNumber": 1,
    "lastItemNumber": 10
  }
}
```

**Request (Last page with fewer items):**
```http
GET /api/v1/appointments?page_number=10&page_size=10
```

**Response:**
```json
{
  "pagination": {
    "pageNumber": 10,
    "pageSize": 10,
    "totalItems": 100,
    "totalPages": 10,
    "hasNextPage": false,
    "hasPreviousPage": true,
    "firstItemNumber": 91,
    "lastItemNumber": 100
  }
}
```

**Request (Out of range page):**
```http
GET /api/v1/appointments?page_number=50&page_size=10
```

**Response (400 or 404):**
```json
{
  "statusCode": 400,
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Page number 50 exceeds total pages (10)",
    "details": [
      {
        "field": "page_number",
        "issue": "Requested page is out of range"
      }
    ]
  }
}
```

---

## 3. Sorting Standard

### 3.1 Query Parameter

All collection endpoints supporting sorting MUST accept:

| Parameter | Type | Format | Description |
|-----------|------|--------|-------------|
| `sort_by` | string | `field` or `-field` | Sort by field; prefix with `-` for descending |

### 3.2 Sorting Rules

1. **Single sort:** `sort_by=createdAt` (ascending) or `sort_by=-createdAt` (descending)
2. **Multiple sorts** (if supported): `sort_by=status,createdAt` or `sort_by=-status,-createdAt`
3. **Default sort:** Must be documented per endpoint (e.g., `-createdAt` for activities)
4. **Sortable fields:** Clearly document which fields support sorting
5. **Invalid field:** Return 400 error with list of valid fields

### 3.3 Sortable Fields (Per Resource Type)

**Appointments:**
- `id`
- `patientId`
- `clinicianId`
- `status` (PENDING, CONFIRMED, COMPLETED, CANCELLED)
- `scheduledTime`
- `createdAt`
- `updatedAt`

**Patients:**
- `id`
- `firstName`
- `lastName`
- `email`
- `phone`
- `status`
- `createdAt`
- `updatedAt`

**Clinicians:**
- `id`
- `firstName`
- `lastName`
- `specialization`
- `status`
- `createdAt`

### 3.4 Sorting Examples

**Request (Ascending):**
```http
GET /api/v1/appointments?page_number=1&page_size=20&sort_by=scheduledTime
```

**Request (Descending):**
```http
GET /api/v1/appointments?page_number=1&page_size=20&sort_by=-createdAt
```

**Request (Multiple sorts):**
```http
GET /api/v1/appointments?page_number=1&page_size=20&sort_by=status,-scheduledTime
```

**Response (with sorted data):**
```json
{
  "statusCode": 200,
  "success": true,
  "data": [
    {
      "id": "apt-005",
      "scheduledTime": "2026-07-01T08:00:00Z",
      "createdAt": "2026-06-10T10:00:00Z"
    },
    {
      "id": "apt-001",
      "scheduledTime": "2026-07-01T10:00:00Z",
      "createdAt": "2026-06-22T14:30:00Z"
    }
  ],
  "pagination": {
    "pageNumber": 1,
    "pageSize": 20,
    "totalItems": 2,
    "totalPages": 1,
    "hasNextPage": false,
    "hasPreviousPage": false
  }
}
```

**Request (Invalid sort field):**
```http
GET /api/v1/appointments?sort_by=invalidField
```

**Response (400 Bad Request):**
```json
{
  "statusCode": 400,
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid sort field",
    "details": [
      {
        "field": "sort_by",
        "issue": "Field 'invalidField' is not sortable",
        "validFields": [
          "id",
          "patientId",
          "clinicianId",
          "status",
          "scheduledTime",
          "createdAt",
          "updatedAt"
        ]
      }
    ]
  }
}
```

---

## 4. Filtering Standard

### 4.1 Query Parameter Convention

All collection endpoints supporting filtering MUST use this convention:

| Parameter | Format | Description |
|-----------|--------|-------------|
| `filter_{field}` | Value or operator:value | Filter by field |

### 4.2 Filter Operators

| Operator | Symbol | Example | Meaning |
|----------|--------|---------|---------|
| Equals | `=` (default) | `filter_status=CONFIRMED` | Exact match |
| Not Equals | `!=` | `filter_status!=CANCELLED` | Exclude value |
| Greater Than | `>` | `filter_scheduledTime=>2026-07-01T00:00:00Z` | Date/time after |
| Less Than | `<` | `filter_scheduledTime=<2026-07-15T00:00:00Z` | Date/time before |
| Greater or Equal | `>=` | `filter_createdAt=>=2026-06-01` | On or after |
| Less or Equal | `<=` | `filter_createdAt=<=2026-06-30` | On or before |
| In | `IN` | `filter_status=IN:CONFIRMED,PENDING` | Match any value in list |
| Not In | `NOT_IN` | `filter_status=NOT_IN:CANCELLED,FAILED` | Exclude values in list |
| Like | `LIKE` | `filter_patientName=LIKE:John*` | Substring match (case-insensitive) |
| Is Null | `IS_NULL` | `filter_cancelReason=IS_NULL:true` | Field is null |

### 4.3 Filterable Fields (Per Resource Type)

**Appointments:**
- `patientId` (exact match)
- `clinicianId` (exact match)
- `status` (exact or IN operator)
- `appointmentType` (exact or IN operator)
- `scheduledTime` (range operators: >, <, >=, <=)
- `createdAt` (range operators)
- `updatedAt` (range operators)

**Patients:**
- `firstName` (LIKE operator)
- `lastName` (LIKE operator)
- `email` (exact match)
- `phone` (exact match)
- `status` (exact or IN operator)

**Clinicians:**
- `firstName` (LIKE operator)
- `lastName` (LIKE operator)
- `specialization` (exact or IN operator)
- `status` (exact or IN operator)

### 4.4 Filter Examples

**Request (Single exact-match filter):**
```http
GET /api/v1/appointments?filter_status=CONFIRMED
```

**Request (Multiple filters):**
```http
GET /api/v1/appointments?filter_status=CONFIRMED&filter_clinicianId=clin-456&page_number=1&page_size=20
```

**Request (Range filter):**
```http
GET /api/v1/appointments?filter_scheduledTime=>=2026-07-01T00:00:00Z&filter_scheduledTime=<2026-07-31T23:59:59Z
```

**Request (IN operator):**
```http
GET /api/v1/appointments?filter_status=IN:CONFIRMED,PENDING
```

**Request (LIKE operator):**
```http
GET /api/v1/patients?filter_firstName=LIKE:John*&page_number=1&page_size=20
```

**Request (Combined pagination, sort, filter):**
```http
GET /api/v1/appointments?filter_status=CONFIRMED&filter_scheduledTime=>=2026-07-01T00:00:00Z&sort_by=-scheduledTime&page_number=1&page_size=20
```

**Response:**
```json
{
  "statusCode": 200,
  "success": true,
  "data": [
    {
      "id": "apt-001",
      "status": "CONFIRMED",
      "scheduledTime": "2026-07-05T10:00:00Z"
    }
  ],
  "pagination": {
    "pageNumber": 1,
    "pageSize": 20,
    "totalItems": 1,
    "totalPages": 1,
    "hasNextPage": false,
    "hasPreviousPage": false
  }
}
```

**Request (Invalid filter field):**
```http
GET /api/v1/appointments?filter_invalidField=someValue
```

**Response (400 Bad Request):**
```json
{
  "statusCode": 400,
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid filter parameter",
    "details": [
      {
        "field": "filter_invalidField",
        "issue": "Field 'invalidField' is not filterable",
        "validFilters": [
          "filter_patientId",
          "filter_clinicianId",
          "filter_status",
          "filter_appointmentType",
          "filter_scheduledTime",
          "filter_createdAt"
        ]
      }
    ]
  }
}
```

---

## 5. Search Standard

For text-based search across multiple fields:

| Parameter | Format | Description |
|-----------|--------|-------------|
| `search` | string | Search term across indexed fields |
| `search_fields` | CSV | Restrict search to specific fields (optional) |

### 5.1 Search Examples

**Request (Full-text search):**
```http
GET /api/v1/appointments?search=John+Smith&page_number=1&page_size=20
```

**Request (Search in specific fields):**
```http
GET /api/v1/patients?search=john&search_fields=firstName,lastName&page_number=1&page_size=20
```

---

## 6. Complex Filter Scenarios

### 6.1 Boolean Logic

Use multiple query parameters for AND logic:
```http
GET /api/v1/appointments?filter_status=CONFIRMED&filter_clinicianId=clin-456
```
Interpreted as: `status = CONFIRMED AND clinicianId = clin-456`

### 6.2 Combining Operators on Same Field

For range filters, repeat the parameter:
```http
GET /api/v1/appointments?filter_scheduledTime=>=2026-07-01T00:00:00Z&filter_scheduledTime=<2026-07-31T23:59:59Z
```
Interpreted as: `scheduledTime >= 2026-07-01 AND scheduledTime < 2026-07-31`

### 6.3 Invalid Combinations

If conflicting operators on same field:
```http
GET /api/v1/appointments?filter_status=CONFIRMED&filter_status=PENDING
```
Response: 400 Bad Request with error indicating conflicting filters

---

## 7. Performance and Limits

### 7.1 Query Constraints

| Constraint | Limit | Rationale |
|-----------|-------|-----------|
| Max page_size | 500 | Prevent excessive data transfer |
| Default page_size | 20 | Balance between granularity and performance |
| Max filter complexity | 10 active filters | Prevent query explosion |
| Max sort fields | 3 | Prevent performance degradation |
| Timeout | 30 seconds | Standard request timeout |

### 7.2 Rate Limiting

Collection endpoints follow standard rate limits:
- Standard tier: 100 requests/minute per API key
- Premium tier: 500 requests/minute per API key
- Bursting: 10 requests in 1-second window allowed

---

## 8. Cursor-Based Pagination (Future)

For very large datasets (Phase 2+), support cursor-based pagination:

```http
GET /api/v1/appointments?cursor=abc123def456&page_size=20
```

Response includes `nextCursor` for efficient large-offset pagination.

---

## 9. Empty Collections

When filter returns no results:

**Response (200 OK):**
```json
{
  "statusCode": 200,
  "success": true,
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:30:00Z",
  "data": [],
  "pagination": {
    "pageNumber": 1,
    "pageSize": 20,
    "totalItems": 0,
    "totalPages": 0,
    "hasNextPage": false,
    "hasPreviousPage": false,
    "firstItemNumber": 0,
    "lastItemNumber": 0
  }
}
```

---

## 10. Documentation Requirements

Each collection endpoint MUST document:

1. **Available filters** with supported operators
2. **Sortable fields** with sort direction support
3. **Default sort order** if applicable
4. **Performance notes** for expensive filters
5. **Examples** for common use cases
6. **Field type** for each filterable/sortable field (string, date, enum, etc.)

### 10.1 Example Documentation Template

```markdown
## GET /api/v1/appointments

### Filters
- `filter_status` (enum: PENDING, CONFIRMED, COMPLETED, CANCELLED)
- `filter_clinicianId` (string: UUID)
- `filter_scheduledTime` (datetime: ISO-8601, supports >, <, >=, <=)
- `filter_createdAt` (datetime: ISO-8601, supports >, <, >=, <=)

### Sortable Fields
- `id` (ascending/descending)
- `status` (ascending/descending)
- `scheduledTime` (ascending/descending)
- `createdAt` (ascending/descending, default: -createdAt)

### Examples
- List all confirmed appointments: `/appointments?filter_status=CONFIRMED`
- List appointments for a clinician: `/appointments?filter_clinicianId=clin-456`
- List next 7 days: `/appointments?filter_scheduledTime=>=2026-07-01T00:00:00Z&filter_scheduledTime=<2026-07-08T00:00:00Z`
- Sorted by scheduled time (newest first): `/appointments?sort_by=-scheduledTime&page_size=50`
```

---

## 11. Implementation Checklist

Collection endpoints MUST verify:

- [ ] All pagination parameters follow standard (pageNumber, pageSize)
- [ ] Pagination response includes all required metadata fields
- [ ] Sort parameters use snake_case format (sort_by)
- [ ] Sort supports ascending (field) and descending (-field) syntax
- [ ] Filter parameters use filter_{field} naming convention
- [ ] Filter operators match standard (=, !=, >, <, >=, <=, IN, LIKE, etc.)
- [ ] Empty collections return 200 OK with empty data array
- [ ] Out-of-range page requests return 400 or 404 with helpful error
- [ ] Invalid sort fields return 400 with list of valid fields
- [ ] Invalid filters return 400 with helpful error message
- [ ] Documentation lists filterable and sortable fields
- [ ] Default page_size is 20, max is 500
- [ ] Performance tested with edge cases (large datasets, complex filters)

---

## 12. Examples Across Services

### 12.1 Appointments Collection

```http
GET /api/v1/appointments?filter_status=CONFIRMED&filter_clinicianId=clin-456&sort_by=-scheduledTime&page_number=1&page_size=20
```

### 12.2 Patients Collection

```http
GET /api/v1/patients?search=john&filter_status=ACTIVE&sort_by=lastName,firstName&page_number=1&page_size=50
```

### 12.3 Audit Logs Collection

```http
GET /api/v1/audit-logs?filter_entityType=APPOINTMENT&filter_action=CREATED&filter_createdAt=>=2026-06-01&sort_by=-createdAt&page_number=1&page_size=100
```

---

## 13. Version Compatibility

- **v1.0 (Current):** All collection endpoints follow this standard
- **v1.1 (Planned Q3 2026):** Add cursor-based pagination support
- **v2.0 (Future):** GraphQL as alternative query interface

---

## 14. Questions and Feedback

For questions about collection semantics:
- Open issue in: `.propel/context/standards/issues/`
- Data architecture team: data-architects@propellq.local
- Next review date: Q3 2026
