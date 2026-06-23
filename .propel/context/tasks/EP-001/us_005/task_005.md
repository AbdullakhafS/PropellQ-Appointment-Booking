# TASK-005: Implement Preferred Slot Auto-Swap Orchestration

**User Story:** US-005 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_005/us_005.md`  
**Priority:** CRITICAL  
**Estimated Effort:** 5-6 dev days + concurrency validation  
**Status:** Completed  
**Created:** 2026-06-18

---

## 1. Objective

Implement a scheduled preferred-slot swap engine that automatically reschedules eligible appointments to preferred slots, preserves transactional consistency, and notifies patients reliably.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Capture preferred slot at booking | DB-1, BE-1, QA-1 |
| AC-2 | Hourly monitoring job | BE-2, OPS-1, QA-2 |
| AC-3 | Eligibility checks before swap | BE-3, QA-2 |
| AC-4 | Atomic swap execution and state cleanup | BE-4, DB-2, QA-3 |
| AC-5 | SMS/email swap notification within 5 minutes | BE-5, INT-1, QA-4 |
| AC-6 | Original slot reopens quickly and safely | BE-4, DB-2, QA-3 |
| AC-7 | Audit entry for each swap | DB-3, BE-6, QA-5 |
| AC-8 | Skip behavior when preferred slot unavailable | BE-3, QA-2 |

---

## 3. Layered Implementation Tasks

## Backend Tasks

### BE-1: Preferred Slot Persistence
- Persist preferred slot and swap window metadata on booking.

### BE-2: Hourly Scheduler
- Run monitoring job hourly (configurable).
- Select appointments with active preferred-slot windows.

### BE-3: Eligibility Engine
- Validate appointment status, preferred slot availability, window validity, and overlap constraints.

### BE-4: Atomic Swap Transaction
- In one transaction: move appointment to preferred slot, release old slot, clear preferred metadata.
- Ensure lock ordering prevents deadlocks/races.

### BE-5: Notification Trigger
- Trigger swap-complete notifications (SMS and email).
- Enforce idempotent send behavior.

### BE-6: Audit and Skip Logging
- Log completed swaps and skipped attempts with explicit reason codes.

## Database Tasks

### DB-1: Preferred Slot Columns
- Add/validate preferred-slot and swap-window columns.

### DB-2: Slot/Appointment Integrity
- Add indexes and constraints supporting fast, safe swap transactions.

### DB-3: Swap History Table
- Create swap history records with original/new slot IDs, timestamps, status, failure reason.

## Integration Tasks

### INT-1: Notification Integration
- Reuse existing reminder/confirmation infrastructure for swap notifications.

## Ops/Observability Tasks

### OPS-1: Job Health Metrics
- Track job duration, processed records, swaps completed, skips, failures.
- Alert on repeated failures or stale queue/job lag.

## Testing Tasks

### QA-1: Preferred Slot Capture Tests
- Validate preferred slot persistence from checkout payload.

### QA-2: Eligibility and Skip Tests
- Validate all positive and negative eligibility branches.

### QA-3: Transaction and Concurrency Tests
- Simulate concurrent reschedules and swaps; verify atomic outcomes.

### QA-4: Notification Tests
- Validate message content and timing after swap.

### QA-5: Audit Tests
- Validate completed/failed/skip audit records with correlation IDs.

---

## 4. Dependencies

- US-003 checkout preferred slot capture.
- US-006 notification infrastructure.

---

## 5. Definition of Done

- [x] Preferred slot schema and scheduler implemented.
- [x] Eligibility and atomic swap logic complete.
- [x] Notifications and audit logs integrated.
- [x] Concurrency and race-condition scenarios validated.
- [x] Job observability and alerts active.
- [x] AC-1 through AC-8 fully validated.

---

## 6. Suggested Execution Order

1. DB-1, DB-2, DB-3  
2. BE-1, BE-2, BE-3  
3. BE-4  
4. INT-1, BE-5, BE-6  
5. OPS-1  
6. QA-1 through QA-5
