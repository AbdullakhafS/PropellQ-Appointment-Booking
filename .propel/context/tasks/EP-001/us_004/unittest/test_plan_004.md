# UNIT-TEST-PLAN-004: Send Confirmation Email (PDF) Within 60 Seconds

User Story: US-004 (EP-001)
Source File: .propel/context/tasks/EP-001/us_004/us_004.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for booking confirmation notification orchestration to validate queue enqueue behavior, payload completeness, retry/backoff control flow, audit logging, and HIPAA-safe content rules.

---

## 2. Scope and Assumptions

### In Scope
- Booking success trigger logic that enqueues confirmation jobs.
- Email payload builder for subject/body fields and attachment metadata.
- PDF metadata generation and mandatory field population checks.
- Retry/backoff policy logic for failed sends.
- Audit log write model and security filters for sensitive data.

### Out of Scope
- Actual SMTP/provider delivery timing in production.
- End-to-end PDF binary rendering correctness beyond payload metadata.
- External ICS client compatibility testing.

### Assumptions
- Notification workflow separates trigger, composition, and delivery layers.
- Queue and email provider adapters are mockable.
- HIPAA-safe field filtering is centralized in reusable utility/service.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Booking success enqueues confirmation quickly | UT-004-001, UT-004-002 |
| AC-2 | Delivery pipeline path supports within-SLA flow intent | UT-004-003 |
| AC-3 | PDF payload includes mandatory appointment details | UT-004-004 |
| AC-4 | Email template includes required summary and links | UT-004-005 |
| AC-5 | Subject line format includes date/provider info | UT-004-006 |
| AC-6 | Delivery failures follow retry/backoff policy and escalation | UT-004-007, UT-004-008 |
| AC-7 | Audit log records confirmation events with key fields | UT-004-009 |
| AC-8 | HIPAA filtering removes restricted PII and secures links | UT-004-010, UT-004-011 |

---

## 4. Unit Test Areas

## A. Trigger and Queue Enqueue

### UT-004-001: Booking success event triggers notification job enqueue
- Simulate successful booking result.
- Assert queue publish/enqueue called with expected job type and identifiers.

### UT-004-002: User response path does not block on send operation
- Mock enqueue success and deferred send path.
- Assert confirmation orchestration returns immediate success contract to caller.

## B. Email/PDF Composition

### UT-004-003: Delivery job handler builds complete provider send request
- Execute handler with booking fixture.
- Assert downstream provider request contains recipient, subject, body, and attachments list.

### UT-004-004: PDF metadata builder includes required appointment fields
- Build PDF model from fixture.
- Assert date/time, provider/specialty, location, confirmation number, duration, cost, instructions, and cancellation link token fields are present.

### UT-004-005: Template model includes required greeting/summary/portal/ICS/contact fields
- Generate email template model.
- Assert patient name, next steps, portal link, ICS reference, contact, and unsubscribe fields are set.

### UT-004-006: Subject formatter outputs expected appointment-specific subject line
- Provide booking fixture.
- Assert subject contains provider name and appointment date in expected format.

## C. Retry and Escalation

### UT-004-007: Failed send schedules retries with exponential backoff profile
- Mock provider failure on first attempts.
- Assert retry scheduler receives configured retry sequence and attempt count increments.

### UT-004-008: Max retry exhaustion flags escalation path
- Force repeated failures through max attempts.
- Assert admin alert/manual follow-up flag is emitted.

## D. Audit and Compliance Safety

### UT-004-009: Audit record is written with required trace fields
- Execute successful send path.
- Assert audit write includes user_id, appointment_id, email, sent_at, status, and template version.

### UT-004-010: HIPAA-safe content filter excludes restricted sensitive fields
- Build outbound model with extra personal fields in source fixture.
- Assert SSN/full DOB do not appear in composed payload.

### UT-004-011: Confirmation link token policy enforces secure token metadata
- Assert generated link model includes one-time token and expiry metadata.

---

## 5. Non-Functional Unit Checks

### UT-004-012: Idempotency guard prevents duplicate confirmation sends
- Trigger same booking event twice.
- Assert duplicate detection/idempotency key blocks second send.

### UT-004-013: Template version fallback behaves safely
- Mock missing/nonexistent template version.
- Assert safe fallback template resolution and warning path.

---

## 6. Test Data Strategy

- Booking fixtures for normal, partial optional fields, and compliance-edge values.
- Delivery fixtures for success, transient error, and permanent failure.
- Token fixtures with deterministic timestamps for expiry assertions.

---

## 7. Mocking Strategy

- Mock queue adapter, email provider adapter, and PDF generator interface.
- Mock retry scheduler and alert publisher.
- Mock audit repository for write assertions.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-004-001 through UT-004-011 before merge.

---

## 9. Exit Criteria

- AC-mapped notification tests pass.
- Retry/escalation and audit/compliance checks pass.
- Coverage thresholds met for notification module.
- No flaky behavior across 3 consecutive runs.

---

## 10. Suggested File Layout

- tests/unit/notifications/ConfirmationTrigger.test.ts
- tests/unit/notifications/ConfirmationComposer.test.ts
- tests/unit/notifications/ConfirmationRetryPolicy.test.ts
- tests/unit/notifications/ConfirmationCompliance.test.ts
- tests/unit/notifications/__fixtures__/confirmation.fixtures.ts

---

## 11. Execution Checklist

1. Create booking and delivery fixtures.
2. Implement trigger/enqueue tests.
3. Implement composition tests for email/PDF/subject.
4. Implement retry/backoff and escalation tests.
5. Implement audit/compliance safety tests.
6. Add idempotency and template fallback checks.
7. Run suite and validate coverage thresholds.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-004.
- [ ] Test cases UT-004-001 through UT-004-013 implemented.
- [ ] Acceptance criteria traceability preserved.
- [ ] Coverage thresholds met.
- [ ] CI unit-test stage passes.