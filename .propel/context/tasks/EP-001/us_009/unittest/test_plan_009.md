# UNIT-TEST-PLAN-009: Bidirectional Calendar Sync (External Updates)

User Story: US-009 (EP-001)
Source File: .propel/context/tasks/EP-001/us_009/us_009.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for bidirectional calendar synchronization logic to validate push/pull orchestration, event-id tracking, cancellation sync, conflict resolution precedence, and retry-safe error handling.

---

## 2. Scope and Assumptions

### In Scope
- PropellQ-to-external push updates on reschedule/cancel events.
- External-to-PropellQ pull processing for deletion and reschedule signals.
- Event ID linkage persistence across lifecycle updates.
- Conflict resolution rules where PropellQ is source of truth.
- Retry queue behavior for transient sync errors.

### Out of Scope
- Real provider webhook endpoint behavior in production.
- End-to-end background polling scheduler reliability.
- External platform rate-limit policy conformance testing.

### Assumptions
- Sync engine exposes provider-agnostic orchestration interfaces.
- Provider-specific adapters for Google/Outlook are mockable.
- Conflict and retry decisions are centralized in deterministic logic.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | PropellQ reschedule pushes updates to connected providers | UT-009-001, UT-009-002 |
| AC-2 | External deletion/reschedule pull rules are handled correctly | UT-009-003, UT-009-004 |
| AC-3 | Event IDs tracked persistently for both providers | UT-009-005 |
| AC-4 | Cancellation in PropellQ deletes external event and logs action | UT-009-006, UT-009-007 |
| AC-5 | Conflict resolution keeps PropellQ as source of truth | UT-009-008 |
| AC-6 | API failures queue retries and avoid blocking core update flow | UT-009-009, UT-009-010 |
| AC-7 | Optional webhook path can route real-time sync intents | UT-009-011 |

---

## 4. Unit Test Areas

## A. Push Sync from PropellQ to External Providers

### UT-009-001: Reschedule event triggers provider update calls for each connected calendar
- Mock appointment reschedule domain event.
- Assert update intent sent to connected provider adapters.

### UT-009-002: Provider-specific payload mapping includes updated date/time and event id
- Assert mapped payload uses tracked external event ids and new schedule values.

## B. Pull Sync from External Providers

### UT-009-003: External deletion event maps to canceled status in PropellQ without record deletion
- Mock pull event indicating external deletion.
- Assert appointment status updated to canceled while preserving record.

### UT-009-004: External reschedule event logs manual-review entry (no auto-update)
- Mock external reschedule change.
- Assert manual review log/event emitted and appointment remains unchanged.

## C. Event ID Tracking and Cancellation

### UT-009-005: Lifecycle persistence maintains Google/Outlook event IDs
- Create/update appointment fixture with provider linkage.
- Assert both event ids are retained/updated appropriately.

### UT-009-006: PropellQ cancellation dispatches provider delete event within sync pipeline
- Trigger appointment cancellation.
- Assert delete requests generated for connected providers.

### UT-009-007: Cancellation sync writes audit trail entry
- Assert audit log contains deletion action metadata per provider.

## D. Conflict and Retry Policies

### UT-009-008: Simultaneous change conflict resolves in favor of PropellQ state
- Mock conflict scenario where external and PropellQ changed.
- Assert outgoing provider update aligns external state to PropellQ.

### UT-009-009: Transient provider error queues retry with exponential backoff metadata
- Mock rate-limit/network failure.
- Assert retry job queued with attempt count/backoff attributes.

### UT-009-010: Sync failure does not block PropellQ appointment update completion
- Simulate provider failure during push.
- Assert primary appointment update response/path remains successful.

## E. Optional Webhook Branch

### UT-009-011: Webhook event parser routes supported provider events to sync engine
- Mock webhook payload for supported event type.
- Assert sync handler dispatch receives normalized event.

---

## 5. Test Data Strategy

- Fixtures for appointment lifecycle events: create, reschedule, cancel.
- Provider fixtures for Google-only, Outlook-only, and both connected.
- Error fixtures: rate-limit, auth invalid, transient network failure.

---

## 6. Mocking Strategy

- Mock provider adapters, sync queue, and retry scheduler.
- Mock appointment repository and audit/event log sinks.
- Mock webhook parser for optional real-time branch.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-009-001 through UT-009-010 before merge.

---

## 8. Exit Criteria

- AC-mapped sync tests pass.
- Conflict and retry behavior validated deterministically.
- Event-id tracking and cancellation audit assertions pass.
- Coverage targets achieved.

---

## 9. Suggested File Layout

- tests/unit/integrations/sync/CalendarSyncPush.test.ts
- tests/unit/integrations/sync/CalendarSyncPull.test.ts
- tests/unit/integrations/sync/CalendarSyncConflictRetry.test.ts
- tests/unit/integrations/sync/__fixtures__/calendarSync.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-009.
- [ ] Test cases UT-009-001 through UT-009-011 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
