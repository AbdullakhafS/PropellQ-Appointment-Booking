# UNIT-TEST-PLAN-005: Implement Preferred Slot Swap Logic

User Story: US-005 (EP-001)
Source File: .propel/context/tasks/EP-001/us_005/us_005.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for preferred slot swap automation to validate eligibility evaluation, safe transactional swap updates, notification triggering, audit logging, and edge-case skip behavior.

---

## 2. Scope and Assumptions

### In Scope
- Preferred slot capture model behavior.
- Scheduled swap eligibility evaluator logic.
- Transactional swap state transitions for original/preferred slots.
- Notification trigger emission after successful swap.
- Audit event creation and edge-case skip decisions.

### Out of Scope
- Scheduler infrastructure reliability itself.
- Real database lock behavior under distributed load.
- End-to-end SMS/email provider delivery.

### Assumptions
- Swap execution service encapsulates rules and repository updates.
- Job scheduler invokes swap service with candidate appointments.
- Notification and audit publishers are mockable.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Preferred slot is captured as nullable booking field | UT-005-001 |
| AC-2 | Hourly job candidate selection path is supported | UT-005-002 |
| AC-3 | Eligibility validator enforces all preconditions | UT-005-003, UT-005-004 |
| AC-4 | Successful swap updates appointment and slot states atomically | UT-005-005, UT-005-006 |
| AC-5 | Successful swap triggers SMS/email notification event | UT-005-007 |
| AC-6 | Original slot returns to availability safely | UT-005-008 |
| AC-7 | Audit event recorded with required slot transition metadata | UT-005-009 |
| AC-8 | Unavailable preferred slot path skips swap with no notification | UT-005-010 |

---

## 4. Unit Test Areas

## A. Capture and Candidate Selection

### UT-005-001: Booking model stores preferred slot only when provided
- Build booking model with/without preferred slot.
- Assert nullable preferred slot behavior is correct.

### UT-005-002: Candidate selector returns only appointments eligible for swap checks
- Provide mixed appointments (missing preferred slot, expired window, canceled).
- Assert only eligible candidates proceed.

## B. Eligibility Evaluation

### UT-005-003: Eligibility validator passes only when all required conditions are true
- Mock appointment active, preferred slot available, valid time window, and no conflicts.
- Assert validator returns eligible.

### UT-005-004: Validator rejects when any required condition fails
- Parameterize failures: canceled appointment, unavailable preferred slot, expired window, conflict.
- Assert correct reject reason per case.

## C. Transactional Swap Execution

### UT-005-005: Successful swap updates appointment slot and clears preferred fields
- Execute swap service with eligible candidate.
- Assert appointment slot_id becomes preferred_slot_id.
- Assert preferred_slot_id and swap_window_expires_at are cleared.

### UT-005-006: Original slot state transitions back to available within same operation boundary
- Assert original slot status update and appointment update are emitted as one transactional unit.

## D. Notifications and Audit

### UT-005-007: Successful swap publishes notification payload for SMS and email channels
- Run successful swap.
- Assert notification event contains old/new slot context and patient identifiers.

### UT-005-008: Swap operation protects against intermediate rebooking race in transaction workflow
- Simulate lock/transaction guard branch.
- Assert operation acquires and releases expected guard semantics in service layer.

### UT-005-009: Audit trail records preferred slot swap event with full metadata
- Assert event contains appointment_id, original_slot_id, new_slot_id, triggered_by=system, and timestamp.

## E. Edge Cases

### UT-005-010: Preferred slot unavailable at execution time causes safe skip
- Mock availability changed to unavailable.
- Assert no swap update, no notification, and no destructive side effect.

---

## 5. Non-Functional Unit Checks

### UT-005-011: Idempotent processing prevents duplicate swap on repeated job invocation
- Invoke swap handler twice for same candidate.
- Assert only one successful swap transition occurs.

### UT-005-012: Structured logging includes decision reason for skipped candidates
- Trigger rejection paths.
- Assert log payload includes machine-readable skip reason.

---

## 6. Test Data Strategy

- Appointment fixtures: active, canceled, expired-window, conflict, eligible.
- Slot fixtures: available/unavailable with deterministic times.
- Separate notification/audit payload fixtures for assertion reuse.

---

## 7. Mocking Strategy

- Mock appointment repository, slot repository, and transaction manager.
- Mock scheduler input feed and time provider.
- Mock notification and audit publishers.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-005-001 through UT-005-010 before merge.

---

## 9. Exit Criteria

- Eligibility and swap transition tests pass.
- Notification and audit events verified.
- Coverage thresholds met for swap module.
- No flaky behavior across 3 consecutive runs.

---

## 10. Suggested File Layout

- tests/unit/booking/PreferredSlotCapture.test.ts
- tests/unit/booking/PreferredSlotEligibility.test.ts
- tests/unit/booking/PreferredSlotSwapExecution.test.ts
- tests/unit/booking/PreferredSlotSwapEvents.test.ts
- tests/unit/booking/__fixtures__/preferredSlot.fixtures.ts

---

## 11. Execution Checklist

1. Create appointment/slot fixtures for all eligibility branches.
2. Implement capture and candidate selection tests.
3. Implement validator pass/fail matrix tests.
4. Implement transactional swap update tests.
5. Implement notification/audit assertions.
6. Add idempotency and structured-logging checks.
7. Run suite and verify coverage thresholds.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-005.
- [ ] Test cases UT-005-001 through UT-005-012 implemented.
- [ ] Acceptance criteria traceability preserved.
- [ ] Coverage thresholds met.
- [ ] CI unit-test stage passes.