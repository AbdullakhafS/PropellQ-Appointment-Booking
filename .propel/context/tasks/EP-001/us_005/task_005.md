# TASK-005: Implement Preferred Slot Auto-Swap Orchestration

**User Story:** US-005 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_005/us_005.md`  
**Priority:** CRITICAL  
**Estimated Effort:** 5-6 dev days + QA/concurrency validation  
**Status:** Planned  
**Created:** 2026-06-18

---

## 1. Objective

Implement an hourly auto-swap engine that monitors preferred slots, atomically swaps qualifying appointments, releases original slots safely, notifies patients within SLA, and writes auditable swap events with robust edge-case handling.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Capture preferred_slot_id at booking and store nullable field | BE-1, DB-1 |
| AC-2 | Hourly monitoring job for active preferred slots | BE-2, OPS-1 |
| AC-3 | Eligibility checks before swap (status, availability, window, overlap) | BE-3, DB-2 |
| AC-4 | Atomic swap + clear preferred fields + release original slot | BE-4, DB-3 |
| AC-5 | Notify patient by SMS+email within 5 minutes | BE-5, INT-1 |
| AC-6 | Original slot reusable within 2 minutes without race issues | BE-4, DB-3, QA-4 |
| AC-7 | Audit event for each successful swap | BE-6, DB-4 |
| AC-8 | Skip behavior when preferred slot unavailable at execution time | BE-7, QA-2 |

---

## 3. Layered Implementation Tasks

## Backend/Service Tasks

### BE-1: Preferred Slot Persistence Contract
- Confirm checkout/booking flow persists `preferred_slot_id` and `swap_window_expires_at`.
- Ensure fields remain nullable and backward-compatible for bookings without preferred slot.
- Validate API contract and DTO mapping for preferred slot payload.

### BE-2: Swap Scheduler Job
- Implement hourly scheduled worker (configurable cron/interval).
- Query only eligible candidate appointments:
  - status = booked
  - preferred_slot_id IS NOT NULL
  - swap_window_expires_at > now
- Add job-run correlation ID and run metrics.

### BE-3: Eligibility Evaluation Engine
- Validate all eligibility checks before attempting swap:
  - appointment still active (not cancelled)
  - preferred slot currently available
  - within monitoring window
  - no overlap/conflict with patient’s other appointments
- Return deterministic evaluation result codes for observability.

### BE-4: Atomic Swap Transaction
- Execute swap in single transaction:
  - update appointment slot_id to preferred slot
  - clear `preferred_slot_id` and `swap_window_expires_at`
  - set `swap_completed_at`
  - release original slot to available pool
- Add row-level locking/pessimistic lock strategy to avoid concurrent update races.
- Guarantee idempotency if job retries the same candidate.

### BE-5: Notification Orchestration
- Trigger SMS and email notification after successful commit.
- Include old vs new appointment time in payload.
- Enforce delivery target: notify within 5 minutes of swap completion.

### BE-6: Audit and Event Logging
- Write success audit event with:
  - appointment_id
  - original_slot_id
  - new_slot_id
  - triggered_by = system
  - timestamp
- Include correlation ID and swap transaction ID for traceability.

### BE-7: Skip/No-op Handling
- If preferred slot unavailable at execution time, skip safely.
- Keep original appointment unchanged.
- Log explicit skip event (reason code: slot_unavailable, window_expired, conflict_detected).

## Database Tasks

### DB-1: Appointments Swap Metadata
- Ensure columns exist and are indexed:
  - preferred_slot_id (nullable FK)
  - swap_window_expires_at
  - swap_completed_at
  - swap_initiated_by
- Add index for scheduler candidate scans.

### DB-2: SlotSwaps Tracking Table
- Create/verify `SlotSwaps` table fields:
  - id
  - appointment_id
  - original_slot_id
  - new_slot_id
  - triggered_at
  - completed_at
  - status
  - failure_reason
- Add indexes on `appointment_id`, `status`, `triggered_at`.

### DB-3: Concurrency Guards
- Enforce constraints preventing duplicate active bookings per slot.
- Use transactional isolation suitable for concurrent scheduler and user-triggered reschedules.
- Add tie-break strategy for simultaneous preferred-slot candidates.

### DB-4: Audit Searchability
- Ensure audit log schema allows lookup by `appointment_id`, `event_type`, `timestamp`.
- Add index for swap-specific event queries.

## Integration Tasks

### INT-1: Notification Integration
- Reuse notification services from reminder/confirmation flows.
- Add swap-specific template variants (SMS + email).
- Include idempotency keys to avoid duplicate sends.

### INT-2: Scheduler Config Integration
- Expose job frequency and window defaults via configuration.
- Support environment-specific tuning without code changes.

## Ops/Observability Tasks

### OPS-1: Runtime Metrics and Alerts
- Capture metrics:
  - candidates scanned
  - swaps completed
  - skips by reason
  - swap latency
  - notification latency
  - failed transactions
- Alert on abnormal failure/skip spikes.

### OPS-2: Recovery and Backoff Strategy
- Implement retry policy for transient DB/service errors.
- Use circuit breaker pattern for downstream notification failures.
- Route hard failures to dead-letter/review queue.

## Testing Tasks

### QA-1: Unit Tests
- Eligibility decision matrix tests.
- Swap transaction command mapping tests.
- Idempotency tests for repeated job attempts.

### QA-2: Integration Tests
- End-to-end auto-swap flow from booked appointment with preferred slot.
- Skip scenarios (preferred slot unavailable, window expired, conflict).
- Audit + SlotSwaps record creation verification.

### QA-3: Notification Tests
- Validate SMS/email content includes old and new slot details.
- Validate notification dispatch within 5-minute target.
- Ensure duplicate notification suppression works.

### QA-4: Concurrency and Load Tests
- Simulate 100 parallel swap attempts and concurrent user reschedules.
- Validate zero data corruption and no duplicate bookings.
- Validate original slot re-enters available pool within 2 minutes.

---

## 4. Dependencies

- US-003 must persist preferred slot metadata at booking time.
- Notification services (email and SMS) available and stable.
- Appointment/slot data model and locking strategy finalized.
- EP-TECH-001 observability stack available for scheduler telemetry.

---

## 5. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Concurrent swap and user reschedule causes inconsistent slot state | Critical | Transactional locks, strict isolation level, deterministic conflict resolution |
| Duplicate scheduler runs trigger duplicate swaps/notifications | High | Idempotency key per appointment+preferred_slot_id+window |
| High candidate volume delays job cycle completion | Medium | Candidate batching and indexed query plan tuning |
| Notification failures hide successful swap from patient | Medium | Retry queue, alerting, in-portal status visibility fallback |
| Swap window edge timing causes unexpected no-op behavior | Low | Explicit boundary tests and consistent UTC time handling |

---

## 6. Definition of Done

- [ ] Preferred slot metadata persistence verified from booking flow.
- [ ] Hourly scheduler implemented and configurable.
- [ ] Eligibility checks and result codes implemented.
- [ ] Atomic swap transaction implemented with rollback safety.
- [ ] Original slot release behavior validated within 2 minutes.
- [ ] Swap notifications dispatched within 5-minute target.
- [ ] Audit and SlotSwaps tracking records persisted and searchable.
- [ ] Idempotency and skip/no-op handling validated.
- [ ] Unit/integration/concurrency/load tests passing.
- [ ] Monitoring dashboards and failure alerts configured.
- [ ] Story AC-1 through AC-8 mapped and validated.

---

## 7. Suggested Execution Order

1. DB-1, DB-2, DB-3
2. BE-1, BE-2
3. BE-3, BE-4
4. BE-6, DB-4
5. INT-1, BE-5
6. BE-7, OPS-1, OPS-2
7. QA-1 through QA-4
8. Final AC validation and sign-off
