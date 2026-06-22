# GOV-1: API Conformance Checklist and Lint Rules

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Approvals:** Architecture Review (Pending)

---

## 1. Overview

This document establishes governance rules and automated checks to enforce API standards across all services. It includes:
- Manual PR checklist for code reviewers
- Automated lint rules for CI/CD pipelines
- Schema validation rules
- Conformance scoring
- Enforcement strategy

All new API endpoints MUST pass these checks before merge to main branch.

---

## 2. PR Review Checklist

### 2.1 Manual Checklist for API Reviewers

Code reviewers MUST verify these items before approving API changes:

#### Request/Response Structure
- [ ] All endpoints use standard request envelope (STD-1 § 2.1)
- [ ] All endpoints return standard response envelope (STD-1 § 3.1)
- [ ] Error responses use standard error envelope (STD-1 § 4.1)
- [ ] All responses include statusCode, success, timestamp fields
- [ ] All responses include correlationId (from request or generated)

#### HTTP Methods and Status Codes
- [ ] GET endpoints return 200 OK for success
- [ ] POST endpoints return 201 Created for new resources
- [ ] PUT/PATCH endpoints return 200 OK for updates
- [ ] DELETE endpoints return 204 No Content
- [ ] Error status codes match standard mapping (STD-1 § 7)
- [ ] No custom status codes used (must align with HTTP standards)

#### Naming Conventions
- [ ] JSON field names use camelCase (not snake_case)
- [ ] Query parameters use snake_case (not camelCase)
- [ ] Path parameters use camelCase
- [ ] Enum values use SCREAMING_SNAKE_CASE
- [ ] Resource names are plural nouns (e.g., /appointments, /patients)
- [ ] HTTP methods are uppercase (GET, POST, PUT, DELETE, PATCH)

#### Error Handling
- [ ] All error responses follow standard error envelope
- [ ] Error codes are documented and consistent
- [ ] Error details include field, issue, code, value (if applicable)
- [ ] Sensitive data not exposed in errors (no tokens, passwords, PII)
- [ ] Correlation ID propagated in all responses
- [ ] Error messages are user-friendly (not stack traces)

#### Validation
- [ ] Request validation executed before business logic
- [ ] Validation errors return 400 with VALIDATION_ERROR code
- [ ] All required fields validated and documented
- [ ] Format validation (email, UUID, dates) applied
- [ ] Business logic validation rules documented
- [ ] Error details explain what's wrong and why

#### Authentication & Authorization
- [ ] Public endpoints explicitly marked as such
- [ ] Protected endpoints require Bearer token
- [ ] Authorization checks prevent unauthorized access
- [ ] Permission/role checks documented per endpoint
- [ ] 401 returned for missing/invalid auth
- [ ] 403 returned for insufficient permissions

#### Idempotency
- [ ] Write operations (POST, PUT, PATCH) accept X-Idempotency-Key
- [ ] Idempotency key validated (non-empty, max 255 chars)
- [ ] Duplicate requests with same key return cached response
- [ ] Cache TTL documented (recommended: 24-72 hours)
- [ ] X-Idempotency-Replayed header added to cached responses

#### Pagination & Collection Endpoints
- [ ] Collection endpoints accept pageNumber and pageSize parameters
- [ ] pageSize limited to max 500, default 20
- [ ] Pagination metadata includes totalItems, totalPages, hasNextPage
- [ ] Sort parameters use sort_by with field name
- [ ] Descending sort uses prefix: -field
- [ ] Filter parameters use filter_{field} naming
- [ ] Filter operators documented (=, !=, >, <, >=, <=, IN, LIKE)
- [ ] Empty collections return 200 OK with empty array

#### Correlation ID & Logging
- [ ] Correlation ID extracted from X-Correlation-ID header
- [ ] New correlation ID generated if not provided
- [ ] Correlation ID included in all response envelopes
- [ ] Correlation ID propagated to downstream service calls
- [ ] Correlation ID logged with all service logs
- [ ] X-Correlation-ID header included in responses

#### Documentation
- [ ] All endpoints documented in API spec
- [ ] Request parameters documented (type, format, required)
- [ ] Response fields documented
- [ ] Error codes and messages documented
- [ ] Examples provided for common scenarios
- [ ] Authentication requirements documented
- [ ] Rate limiting documented (if applicable)
- [ ] API version and deprecation status documented

#### Security
- [ ] TLS required (no HTTP endpoints)
- [ ] No secrets in request/response bodies
- [ ] No PII in error messages or logs
- [ ] CORS headers configured appropriately
- [ ] Rate limiting implemented for public endpoints
- [ ] Input validation prevents injection attacks
- [ ] Output encoding prevents XSS attacks

#### Code Quality
- [ ] Code follows language-specific standards
- [ ] Unit tests cover happy path and error cases
- [ ] Integration tests validate end-to-end behavior
- [ ] No hardcoded credentials or API keys
- [ ] No TODO/FIXME comments in merged code
- [ ] Performance acceptable (<200ms typical response)

---

## 3. Automated Lint Rules

### 3.1 Lint Configuration File

Services MUST include `.propelq-api-lint.yml` in repository root:

```yaml
# API Conformance Lint Configuration
version: "1.0"

# Enable/disable specific rule categories
rules:
  envelope:
    enabled: true
    severity: error
  
  naming:
    enabled: true
    severity: error
  
  status_codes:
    enabled: true
    severity: error
  
  error_handling:
    enabled: true
    severity: error
  
  validation:
    enabled: true
    severity: warning
  
  documentation:
    enabled: true
    severity: warning
  
  security:
    enabled: true
    severity: error

# API specification file
spec_file: "./api-spec.json"

# Exclude paths from linting
exclude:
  - "/health"
  - "/metrics"
  - "/swagger/**"

# Report format
report:
  format: "json" # json, html, text
  output: "./api-lint-report.json"
```

### 3.2 Lint Rules - Response Envelope

**Rule ID: ENVELOPE-001**  
**Name:** Response Envelope Structure  
**Severity:** ERROR

Validates all endpoints return responses with required envelope fields.

```
✓ PASS:
{
  "statusCode": 200,
  "success": true,
  "correlationId": "...",
  "timestamp": "2026-06-22T14:30:00Z",
  "data": {...}
}

✗ FAIL: Missing statusCode
{
  "success": true,
  "data": {...}
}

✗ FAIL: Missing correlationId
{
  "statusCode": 200,
  "success": true,
  "data": {...}
}
```

**Rule ID: ENVELOPE-002**  
**Name:** Error Envelope Structure  
**Severity:** ERROR

Validates error responses follow standard error envelope.

```
✓ PASS:
{
  "statusCode": 400,
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "...",
    "details": [...]
  },
  "correlationId": "..."
}

✗ FAIL: Missing error.code
{
  "statusCode": 400,
  "success": false,
  "error": {
    "message": "Invalid request"
  }
}
```

### 3.3 Lint Rules - Naming Conventions

**Rule ID: NAMING-001**  
**Name:** JSON Field Naming (camelCase)  
**Severity:** ERROR

All JSON fields must use camelCase.

```
✓ PASS: "firstName", "appointmentId", "createdAt"
✗ FAIL: "first_name", "FirstName", "appointment_id"
```

**Rule ID: NAMING-002**  
**Name:** Query Parameter Naming (snake_case)  
**Severity:** ERROR

All query parameters must use snake_case.

```
✓ PASS: "page_number", "page_size", "sort_by"
✗ FAIL: "pageNumber", "PageSize", "sortBy"
```

**Rule ID: NAMING-003**  
**Name:** Enum Naming (SCREAMING_SNAKE_CASE)  
**Severity:** ERROR

All enum values must use SCREAMING_SNAKE_CASE.

```
✓ PASS: "PENDING", "IN_PROGRESS", "COMPLETED"
✗ FAIL: "pending", "in_progress", "Completed"
```

**Rule ID: NAMING-004**  
**Name:** Resource Names (Plural Nouns)  
**Severity:** WARNING

Collection endpoints must use plural resource names.

```
✓ PASS: "/api/v1/appointments", "/api/v1/patients"
✗ FAIL: "/api/v1/appointment", "/api/v1/patient"
```

### 3.4 Lint Rules - HTTP Status Codes

**Rule ID: STATUSCODE-001**  
**Name:** Status Code Mapping  
**Severity:** ERROR

Enforces standard HTTP status code usage.

```
✓ PASS: 
  GET /appointments → 200 OK
  POST /appointments → 201 Created
  PUT /appointments/{id} → 200 OK
  DELETE /appointments/{id} → 204 No Content

✗ FAIL:
  POST /appointments → 200 OK (should be 201)
  GET /appointments → 201 Created (invalid)
```

**Rule ID: STATUSCODE-002**  
**Name:** Error Status Code Mapping  
**Severity:** ERROR

Enforces standard error status code usage.

```
✓ PASS:
  Missing auth → 401 Unauthorized
  Missing permission → 403 Forbidden
  Resource not found → 404 Not Found
  Validation error → 400 Bad Request

✗ FAIL:
  Missing auth → 403 (should be 401)
  Validation error → 422 (should be 400 in Phase 1)
```

### 3.5 Lint Rules - Error Handling

**Rule ID: ERROR-001**  
**Name:** Error Code Consistency  
**Severity:** ERROR

All error responses must use defined error codes.

```
✓ PASS: "code": "VALIDATION_ERROR" (defined in STD-1)
✗ FAIL: "code": "INVALID_DATA" (not in standard list)
```

**Rule ID: ERROR-002**  
**Name:** Error Detail Structure  
**Severity:** ERROR

Error details must include required fields.

```
✓ PASS:
{
  "details": [
    {
      "field": "email",
      "issue": "Invalid email format",
      "code": "InvalidFormat"
    }
  ]
}

✗ FAIL:
{
  "details": [
    {
      "field": "email",
      "message": "Bad email"
    }
  ]
}
```

**Rule ID: ERROR-003**  
**Name:** No Sensitive Data in Errors  
**Severity:** ERROR

Error responses must not contain passwords, tokens, or PII.

```
✗ FAIL: "message": "Database error: connection failed for user 'admin' with password 'secret'"
✓ PASS: "message": "Database connection failed"
```

### 3.6 Lint Rules - Authentication & Authorization

**Rule ID: AUTH-001**  
**Name:** Bearer Token Format  
**Severity:** ERROR

Protected endpoints must validate Bearer token format.

```
✓ PASS: Authorization: Bearer eyJhbGciOi...
✗ FAIL: Authorization: eyJhbGciOi... (missing "Bearer ")
```

**Rule ID: AUTH-002**  
**Name:** Permission Enforcement  
**Severity:** ERROR

Protected endpoints must return 403 if permission denied.

```
✓ PASS: 
  [Authorize]
  [RequirePermission("write:appointments")]
  public IActionResult Create(...) { }

✗ FAIL:
  [Authorize]
  public IActionResult Create(...) { } // No permission check
```

### 3.7 Lint Rules - Idempotency

**Rule ID: IDEMPOTENT-001**  
**Name:** Write Operations Accept Idempotency Key  
**Severity:** ERROR

All POST/PUT/PATCH operations must accept X-Idempotency-Key.

```
✓ PASS: POST /api/v1/appointments accepts X-Idempotency-Key header
✗ FAIL: POST /api/v1/appointments ignores X-Idempotency-Key
```

**Rule ID: IDEMPOTENT-002**  
**Name:** Cached Response Indicator  
**Severity:** WARNING

Replayed responses should include X-Idempotency-Replayed header.

```
✓ PASS: Response includes X-Idempotency-Replayed: true
✗ FAIL: Response missing X-Idempotency-Replayed header
```

### 3.8 Lint Rules - Pagination

**Rule ID: PAGINATION-001**  
**Name:** Collection Endpoints Pagination  
**Severity:** ERROR

Collection endpoints must support pagination parameters.

```
✓ PASS: GET /api/v1/appointments supports ?page_number=1&page_size=20
✗ FAIL: GET /api/v1/appointments returns all results without pagination
```

**Rule ID: PAGINATION-002**  
**Name:** Pagination Metadata  
**Severity:** ERROR

Paginated responses must include pagination metadata.

```
✓ PASS:
{
  "data": [...],
  "pagination": {
    "pageNumber": 1,
    "pageSize": 20,
    "totalItems": 100,
    "totalPages": 5
  }
}

✗ FAIL:
{
  "data": [...]
}
```

### 3.9 Lint Rules - Documentation

**Rule ID: DOC-001**  
**Name:** API Documentation Present  
**Severity:** WARNING

All endpoints must have documentation.

```
✓ PASS: Endpoint documented in OpenAPI spec with description
✗ FAIL: Endpoint missing from API documentation
```

**Rule ID: DOC-002**  
**Name:** Request/Response Examples  
**Severity:** WARNING

Endpoints should include usage examples.

```
✓ PASS: Documentation includes request and response examples
✗ FAIL: Documentation missing examples
```

### 3.10 Lint Rules - Security

**Rule ID: SEC-001**  
**Name:** HTTPS Enforcement  
**Severity:** ERROR

All endpoints must use HTTPS (no HTTP).

```
✓ PASS: https://api.propellq.local/v1/appointments
✗ FAIL: http://api.propellq.local/v1/appointments
```

**Rule ID: SEC-002**  
**Name:** CORS Headers  
**Severity:** ERROR

API must configure appropriate CORS headers.

```
✓ PASS: Access-Control-Allow-Origin: https://app.propellq.local
✗ FAIL: Access-Control-Allow-Origin: *
```

---

## 4. Automated Linting in CI/CD

### 4.1 GitHub Actions Workflow

```yaml
name: API Conformance Lint

on:
  pull_request:
    paths:
      - 'src/Controllers/**'
      - 'src/DTOs/**'
      - '.propelq-api-lint.yml'

jobs:
  lint:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Download API Lint Tool
        run: |
          wget https://releases.propellq.local/api-lint/latest/api-lint-linux-x64
          chmod +x api-lint-linux-x64
      
      - name: Run API Conformance Linting
        run: |
          ./api-lint-linux-x64 \
            --spec-file ./src/api-spec.json \
            --config .propelq-api-lint.yml \
            --format json \
            --output ./lint-report.json
      
      - name: Comment PR with Results
        if: always()
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('./lint-report.json', 'utf8'));
            
            let comment = `## API Conformance Lint Results\n\n`;
            
            if (report.errors.length === 0 && report.warnings.length === 0) {
              comment += `✅ All checks passed!\n`;
            } else {
              if (report.errors.length > 0) {
                comment += `### ❌ Errors (${report.errors.length})\n`;
                report.errors.forEach(err => {
                  comment += `- **${err.rule}**: ${err.message}\n`;
                });
              }
              
              if (report.warnings.length > 0) {
                comment += `### ⚠️ Warnings (${report.warnings.length})\n`;
                report.warnings.forEach(warn => {
                  comment += `- **${warn.rule}**: ${warn.message}\n`;
                });
              }
            }
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
      
      - name: Fail if Errors
        if: failure() && steps.lint.outputs.error-count > 0
        run: exit 1
```

### 4.2 OpenAPI Schema Validation

```bash
# Validate OpenAPI spec conforms to standards
npx openapi-lint ./src/api-spec.json --ruleset propellq-standards.yml

# Sample rules in propellq-standards.yml:
- rule: operation-4xx-response
  description: All 4xx responses must use standard error envelope
  given: $.paths[*][*].responses.4xx
  then:
    function: schema
    functionOptions:
      schema:
        type: object
        properties:
          error:
            type: object
            required:
              - code
              - message

- rule: response-has-pagination
  description: Collection endpoints must include pagination
  given: $.paths[*].get.responses.200
  then:
    function: schema
    functionOptions:
      schema:
        type: object
        properties:
          pagination:
            type: object
            required:
              - pageNumber
              - pageSize
              - totalItems
```

---

## 5. Conformance Scoring

### 5.1 Score Calculation

Each endpoint receives a conformance score (0-100):

```
Base Score: 100

Deductions:
- Missing required envelope fields: -10 per field
- Non-standard naming convention: -5 per instance
- Incorrect HTTP status code: -10
- Missing error details: -5
- No idempotency on write op: -10
- No pagination on collection: -15
- Missing documentation: -10
- Security issues: -20

Minimum Score: 0
```

### 5.2 Score Interpretation

| Score | Status | Action |
|-------|--------|--------|
| 90-100 | ✅ Compliant | Approve and merge |
| 70-89 | ⚠️ Warning | Approve with comments, address in next sprint |
| 50-69 | ❌ Non-compliant | Request changes before merge |
| 0-49 | 🚫 Critical | Reject, major refactoring required |

---

## 6. Exception Process

### 6.1 Exceptions to Standards

Standards exceptions require:
1. Written justification from service owner
2. Approval from 2 architecture reviewers
3. Documentation of exception in ADR (Architecture Decision Record)
4. Plan to remediate before next release

**Exception Template:**
```
---
Service: AppointmentService
Endpoint: POST /batch-import
Exception: Accepts multipart/form-data instead of JSON

Justification:
Bulk import requires file uploads, not practical in JSON.
Alternative considered: Separate file upload endpoint + reference ID approach.

Timeline: Remediate in Q3 2026 sprint
Tracked in: ADR-042
---
```

---

## 7. Monitoring and Reporting

### 7.1 Conformance Dashboard

Track conformance across all services:
- Total endpoints: 234
- Fully compliant (90-100): 198 (84%)
- Partial compliance (70-89): 28 (12%)
- Non-compliant (50-69): 6 (3%)
- Critical (<50): 2 (1%)

### 7.2 Monthly Reports

Generate monthly conformance reports:
- Services with best conformance
- Services needing remediation
- Trend analysis (improving/declining)
- Top violations

---

## 8. Implementation Checklist

Services MUST verify:

- [ ] `.propelq-api-lint.yml` configuration file created
- [ ] API specification (OpenAPI/Swagger) up-to-date
- [ ] API linting enabled in CI/CD pipeline
- [ ] PR template includes API conformance checklist
- [ ] All team members aware of standards
- [ ] Code review guidelines reference this document
- [ ] Automated linting passes before merge
- [ ] Conformance dashboard accessible to team
- [ ] Exception process documented and followed
- [ ] Monthly conformance reports generated

---

## 9. Questions and Feedback

For questions about API conformance governance:
- Open issue in: `.propel/context/standards/issues/`
- Quality team: quality@propellq.local
- Next review date: Q3 2026
