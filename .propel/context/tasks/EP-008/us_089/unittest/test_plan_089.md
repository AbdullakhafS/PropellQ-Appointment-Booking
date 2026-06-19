# UNIT-TEST-PLAN-089: Async Queue for Reminders

User Story: US-089 (EP-008)
Source File: .propel/context/tasks/EP-008/us_089/us_089.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for reminder job enqueuing, asynchronous worker processing, retry and dead-letter handling, delivery status tracking, and non-blocking booking flow.

---

## 2. Scope and Assumptions

### In Scope
- Reminder job enqueuing after booking events.
- Worker processing of email/SMS jobs.
- Retry logic and dead-letter handling.
- Delivery status and failure reason queries.
- Queue monitoring and telemetry.

### Out of Scope
- External notification provider integration details.
- Reminder content authoring.

### Assumptions
- Queue abstraction is injectable and testable.
- Worker processing is encapsulated in unit-testable modules.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Reminder jobs enqueued asynchronously | UT-089-001, UT-089-002 |
| AC-2 | Workers send reminders reliably | UT-089-003, UT-089-004 |
| AC-3 | Retries and dead-letter handling work | UT-089-005, UT-089-006 |
| AC-4 | Delivery status is queryable | UT-089-007, UT-089-008 |

---

## 4. Unit Test Areas

### UT-089-001: Booking event enqueues reminder job asynchronously
- Trigger booking flow.
- Assert reminder job created in queue without blocking.

### UT-089-002: Enqueue is idempotent (no duplicate jobs)
- Enqueue same reminder twice.
- Assert deduplication or single job processed.

### UT-089-003: Worker processes job and sends reminder
- Mock job from queue.
- Assert email/SMS delivery attempted.

### UT-089-004: Delivery status is recorded
- Simulate successful delivery.
- Assert status recorded (sent/failed/pending).

### UT-089-005: Failed job retries with backoff
- Simulate delivery failure.
- Assert retry scheduled with delay.

### UT-089-006: Exhausted retries move job to dead-letter queue
- Simulate max retry exceeded.
- Assert job moved to DLQ.

### UT-089-007: Delivery status query API returns job state
- Query job status.
- Assert current status and failure reason (if failed).

### UT-089-008: Status query works across multiple job states
- Query jobs in sent/failed/retrying states.
- Assert correct status returned for each.

---

## 5. Test Data and Mocking Strategy

- Fixtures: booking events, reminder job payloads, delivery outcomes, retry configs.
- Mocks: queue adapter, worker processor, delivery provider, status store.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-089-001 through UT-089-008.

---

## 7. Suggested File Layout

- tests/unit/queue/ReminderEnqueue.test.ts
- tests/unit/queue/ReminderWorker.test.ts
- tests/unit/queue/ReminderRetryDlq.test.ts
- tests/unit/queue/DeliveryStatusQuery.test.ts
- tests/unit/queue/__fixtures__/reminder.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-089-001 through UT-089-008 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
