# TASK-004: Implement Confirmation Email with PDF Delivery Pipeline

**User Story:** US-004 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_004/us_004.md`  
**Priority:** CRITICAL  
**Estimated Effort:** 4-5 dev days + QA/SLA validation  
**Status:** Planned  
**Created:** 2026-06-18

---

## 1. Objective

Implement asynchronous confirmation email delivery (with PDF and ICS attachments) after successful booking, meeting 60-second SLA, retry/error handling, audit logging, and HIPAA-safe transmission and content controls.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Enqueue email job within 500ms after successful booking | BE-1, BE-2 |
| AC-2 | Deliver confirmation email within 60s (95% SLA) | BE-3, PERF-1, QA-4 |
| AC-3 | PDF includes required appointment fields and secure link | FE-1, BE-4, SEC-1 |
| AC-4 | HTML email includes required content + ICS | FE-2, BE-4 |
| AC-5 | Clear subject format with date/provider | FE-3 |
| AC-6 | Retry failures up to 3 attempts + alert escalation | BE-5, OPS-1 |
| AC-7 | Audit log entries searchable by user/appointment | DB-2, BE-6 |
| AC-8 | HIPAA-safe transport/content/token expiry controls | SEC-1, SEC-2, QA-3 |

---

## 3. Layered Implementation Tasks

## Frontend/Template Tasks

### FE-1: PDF Template Implementation
- Create branded confirmation PDF template with:
  - appointment date/time
  - provider name/specialty
  - location
  - confirmation number
  - duration and cost estimate (if available)
  - check-in instructions
  - cancellation/reschedule link with expiring token
- Mask sensitive fields (no SSN, no full DOB).

### FE-2: HTML Email Template + ICS Attachment Support
- Build responsive HTML email template including:
  - greeting with patient name
  - appointment summary
  - next-step instructions
  - View in Portal link
  - company contact block
  - unsubscribe link
- Generate ICS attachment with appointment metadata.

### FE-3: Subject-Line Policy
- Implement deterministic subject format:
  - `Your Appointment Confirmation - {Provider} on {Date}`
- Add tests for formatting and localization-safe date rendering.

## Backend/API/Worker Tasks

### BE-1: Booking Event Hook
- On `POST /api/appointments/book` success, emit confirmation event payload.
- Ensure synchronous booking response is not blocked by email generation.

### BE-2: Queue Enqueue Path
- Enqueue confirmation job within 500ms with payload:
  - appointmentId
  - recipientEmail
  - templateVersion
  - correlationId
- Return booking response immediately after enqueue success.

### BE-3: Worker Processing Pipeline
- Worker pulls job and executes pipeline:
  1. load appointment/patient/provider data
  2. generate PDF and ICS
  3. render HTML email
  4. send via email provider
  5. write audit + delivery record
- Enforce SLA metrics from booking timestamp to send acknowledgment.

### BE-4: Artifact Generation Services
- Build reusable services for PDF generation and email rendering.
- Keep template versioning traceable in payload and persisted records.
- Validate required appointment fields before send attempt.

### BE-5: Retry + Escalation Logic
- On send failure, retry up to 3 attempts with exponential backoff.
- Persist retry count and failure reason per attempt.
- After max retries, raise admin alert and mark account for manual follow-up.

### BE-6: Resend API Endpoint
- Implement `POST /api/appointments/{id}/confirmation/resend`.
- Enforce authorization checks and rate limits.
- Ensure resend attempts are fully audited.

## Database Tasks

### DB-1: ConfirmationEmails Table
- Create table with required fields:
  - id
  - appointment_id
  - recipient_email
  - sent_at
  - delivery_status
  - template_version
  - retry_count
  - provider_message_id
  - failure_reason
- Add indexes on `appointment_id`, `recipient_email`, `sent_at`.

### DB-2: Audit Log Events
- Add audit event entries for:
  - enqueue
  - send success
  - send failure
  - retries
  - escalation
  - resend
- Ensure events are searchable by `user_id` and `appointment_id`.

## Security/Compliance Tasks

### SEC-1: HIPAA Content Guardrails
- Add content validation checks to reject prohibited PII fields in PDF/email.
- Ensure cancellation link tokens are one-time and expire after configured TTL (30 days).

### SEC-2: Transport and Secret Safety
- Enforce TLS for all outbound email provider connections.
- Store email credentials/API keys in secret manager only.
- Prevent credential or token leakage in logs/errors.

## Ops/Observability Tasks

### OPS-1: SLA + Delivery Monitoring
- Track metrics:
  - enqueue latency
  - send latency
  - delivery success rate
  - retry rate
  - failed-after-retry count
- Add alerts when SLA breaches exceed threshold.

### OPS-2: Quota/Provider Health Handling
- Monitor provider quota and throttling signals.
- Add fallback provider strategy or graceful degradation policy.

## Testing Tasks

### QA-1: Unit Tests
- PDF field mapping and masking tests.
- Email template rendering tests.
- Subject line formatting tests.
- Retry backoff and stop-at-3 behavior tests.

### QA-2: Integration Tests
- End-to-end booking -> enqueue -> send success flow.
- Resend endpoint flow and authorization checks.
- Audit row creation validation for each state transition.

### QA-3: Security/Compliance Tests
- Verify no prohibited PII appears in generated PDF/email.
- Verify token expiry and one-time usage behavior.
- Validate TLS and secret-handling paths.

### QA-4: Load/SLA Tests
- Simulate high booking volume (for example 1000 bookings burst).
- Validate at least 95% of confirmations sent within 60 seconds.
- Validate worker throughput and retry behavior under provider transient failures.

---

## 4. Dependencies

- US-003 booking finalization endpoint and appointment identifiers available.
- Email provider account/API credentials provisioned.
- Worker runtime and queue infrastructure available.
- Audit logging pipeline available (EP-007 alignment).

---

## 5. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Email provider throttling causes SLA misses | High | Queue smoothing, retry with jitter, provider health alerts, fallback route |
| PDF generation latency degrades delivery time | Medium | Precompiled templates and worker-side generation profiling |
| Invalid recipient addresses increase bounce rates | Medium | Upstream email validation + bounce monitoring + manual resend flow |
| Sensitive data leakage in generated documents | Critical | PII guardrails, masked field policy, compliance tests in CI |
| Silent worker failures lose confirmations | High | Durable queue, dead-letter handling, retry metrics, alerting |

---

## 6. Definition of Done

- [ ] Booking success path enqueues confirmation job in <=500ms.
- [ ] Worker pipeline sends confirmation with PDF + ICS attachments.
- [ ] 60-second SLA met for >=95% of sends under target load.
- [ ] Retry logic (max 3) and escalation path implemented.
- [ ] ConfirmationEmails and audit events persisted and searchable.
- [ ] Resend endpoint implemented with authorization and audit.
- [ ] HIPAA safeguards (PII masking, TLS, token expiry) validated.
- [ ] Unit/integration/security/load tests passing.
- [ ] API and template specifications documented.
- [ ] Story AC-1 through AC-8 mapped and validated.

---

## 7. Suggested Execution Order

1. DB-1, DB-2
2. BE-1, BE-2
3. FE-1, FE-2, FE-3
4. BE-3, BE-4
5. BE-5, BE-6
6. SEC-1, SEC-2
7. OPS-1, OPS-2
8. QA-1 through QA-4
9. Final AC validation and sign-off
