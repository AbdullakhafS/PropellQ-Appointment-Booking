# TASK-089: Implement Async Queue for Reminders

**User Story:** US-089 (EP-008)
**Source File:** `.propel/context/tasks/EP-008/us_089/us_089.md`
**Priority:** HIGH
**Status:** Done
**Created:** 2026-06-19

## Objective
Move reminder dispatch to a durable asynchronous queue so booking stays non-blocking and reminder delivery scales independently with retries and dead-letter handling.

## AC Mapping
- AC-1: BE-1, QA-1
- AC-2: WORKER-1, QA-2
- AC-3: WORKER-2, OPS-1, QA-3
- AC-4: BE-2, QA-4

## Tasks
### BE-1: Reminder Job Enqueue
- Publish reminder jobs asynchronously after booking events.
- Ensure enqueue path is idempotent.

### WORKER-1: Reminder Worker Processing
- Process email/SMS jobs from queue reliably and record status.

### WORKER-2: Retry and Dead-Letter Strategy
- Apply retries for transient failures and dead-letter exhausted jobs.

### BE-2: Delivery Status Query API
- Expose reminder job state and failure reason lookup.

### OPS-1: Queue Monitoring
- Track queue depth, retry count, worker failures, and dead-letter volume.

### QA-1: Non-Blocking Booking Tests
- Validate booking flow enqueues jobs without waiting for dispatch.

### QA-2: Worker Delivery Tests
- Validate workers send reminders reliably.

### QA-3: Retry/DLQ Tests
- Validate retry logic and dead-letter handling.

### QA-4: Status Query Tests
- Validate reminder job state is queryable.

## Definition of Done
- [x] Reminder queue and worker flow implemented.
- [x] Retry and dead-letter handling configured.
- [x] Monitoring and status lookup available.
- [x] AC-1 through AC-4 validated.
