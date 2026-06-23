# TASK-004: Implement Confirmation Email and PDF Delivery Pipeline

**User Story:** US-004 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_004/us_004.md`  
**Priority:** CRITICAL  
**Estimated Effort:** 3-4 dev days + delivery SLA validation  
**Status:** Completed  
**Created:** 2026-06-18

---

## 1. Objective

Build an asynchronous confirmation pipeline that sends appointment confirmation email with PDF attachment within 60 seconds, with retries, auditability, and HIPAA-safe content handling.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Enqueue email quickly after successful booking | BE-1, OPS-1, QA-1 |
| AC-2 | Deliver within 60-second SLA (95%) | BE-2, OPS-1, QA-2 |
| AC-3 | PDF contains required appointment details | DOC-1, QA-3 |
| AC-4 | Email template includes required content and links | FE-1, QA-3 |
| AC-5 | Clear subject format | FE-1, QA-3 |
| AC-6 | Retry with exponential backoff and admin flag after max attempts | BE-3, OPS-2, QA-4 |
| AC-7 | Audit logging for each delivery | DB-1, BE-4, QA-5 |
| AC-8 | HIPAA-safe transport/content/token handling | SEC-1, SEC-2, QA-6 |

---

## 3. Layered Implementation Tasks

## Backend/Queue Tasks

### BE-1: Post-Booking Enqueue
- Enqueue confirmation job within booking flow after successful commit.
- Keep booking API response non-blocking.

### BE-2: Email Worker
- Fetch appointment context, render template, attach PDF, send email.
- Capture latency and delivery result metadata.

### BE-3: Retry Orchestration
- Implement retry schedule (1s, 5s, 30s or configured equivalent).
- Mark failed-after-max and trigger admin attention workflow.

### BE-4: Resend Endpoint
- Implement manual resend endpoint for support/self-service use.

## Template/Document Tasks

### FE-1: HTML Email Template
- Build responsive email body with greeting, summary, links, and contact info.
- Add clear subject line convention.

### DOC-1: PDF Template
- Generate appointment PDF with required fields and instructions.
- Exclude prohibited sensitive fields and include tokenized action links.

## Database Tasks

### DB-1: Delivery and Audit Persistence
- Create/validate email delivery table and audit events.
- Record recipient, status, timestamps, template version, retry count.

## Security/Compliance Tasks

### SEC-1: Transport and Link Security
- Ensure TLS transport and expiring one-time action tokens.

### SEC-2: Data Minimization in Artifacts
- Ensure no SSN/full DOB in PDF or logs.
- Redact sensitive fields in error traces.

## Ops/Observability Tasks

### OPS-1: SLA Monitoring
- Track queue-to-delivery timing and SLA compliance rates.

### OPS-2: Failure Alerting
- Alert on retry exhaustion and provider outages.

## Testing Tasks

### QA-1: Booking-to-Queue Tests
- Validate enqueue behavior and non-blocking API response.

### QA-2: SLA Tests
- Validate 95th percentile delivery time target.

### QA-3: Content Tests
- Validate email subject/body and PDF fields.

### QA-4: Retry Tests
- Inject provider failures and validate backoff + escalation.

### QA-5: Audit Tests
- Validate audit entries for success/failure paths.

### QA-6: Security/Compliance Tests
- Validate redaction, token expiry, and restricted content rules.

---

## 4. Dependencies

- US-003 finalized booking event.
- Email provider credentials and delivery infrastructure.

---

## 5. Definition of Done

- [x] Async confirmation job pipeline implemented.
- [x] Email and PDF templates completed.
- [x] 60-second delivery SLA monitored and validated.
- [x] Retry, alerting, and manual resend flows implemented.
- [x] Audit logging and compliance controls complete.
- [x] AC-1 through AC-8 fully validated.

---

## 6. Suggested Execution Order

1. DB-1  
2. BE-1, BE-2, BE-3, BE-4  
3. FE-1, DOC-1  
4. SEC-1, SEC-2  
5. OPS-1, OPS-2  
6. QA-1 through QA-6
