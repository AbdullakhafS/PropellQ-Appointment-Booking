# TASK-009: Implement Bidirectional Calendar Sync for Google and Outlook

**User Story:** US-009 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_009/us_009.md`  
**Priority:** HIGH  
**Estimated Effort:** 5-6 dev days + reliability/performance validation  
**Status:** Completed  
**Created:** 2026-06-18

---

## 1. Objective

Implement reliable bidirectional synchronization between PropellQ appointments and connected Google/Outlook calendars, including push updates on PropellQ changes, pull reconciliation from external calendars, conflict handling with PropellQ as source of truth, and retryable failure recovery.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Push sync updates external events within 10 seconds when PropellQ appointment changes | BE-1, BE-2, INT-1, INT-2, OPS-1, QA-2 |
| AC-2 | Pull sync every 30 minutes; external delete cancels appointment; external reschedule logs manual review | BE-3, BE-4, QA-3 |
| AC-3 | Persist Google and Outlook event IDs on appointment lifecycle | DB-1, BE-5, QA-1 |
| AC-4 | PropellQ cancellation deletes external events and logs audit | BE-2, BE-6, QA-2 |
| AC-5 | Conflict resolution: PropellQ wins and conflict is audited | BE-7, DB-3, QA-4 |
| AC-6 | API failure handling with retry queue and admin alert after max attempts | BE-8, OPS-2, DB-2, QA-5 |
| AC-7 | Optional webhook ingestion for near real-time sync acceleration | BE-9, INT-3, QA-6 |

---

## 3. Layered Implementation Tasks

## Backend/Service Tasks

### BE-1: Push Sync Event Production
- Trigger sync work item creation when appointment is rescheduled/cancelled in PropellQ.
- Create per-provider jobs only for connected calendars (Google and/or Outlook).
- Include action type (`update`, `delete`) and deterministic idempotency key.

### BE-2: Push Sync Worker (10s SLO)
- Implement async worker to process queued push sync actions.
- For Google-connected users, call Google Calendar Events API for update/delete.
- For Outlook-connected users, call Microsoft Graph Calendar Events API for update/delete.
- Enforce target SLO: successful external update/delete within 10 seconds under normal load.

### BE-3: Pull Sync Scheduler (30-min cadence)
- Implement polling job running every 30 minutes per connected provider.
- Query provider APIs for updated/deleted events since last sync watermark.
- Support provider-specific paging and incremental sync tokens where available.

### BE-4: Pull Sync Reconciliation Rules
- If mapped external event is deleted, mark PropellQ appointment status as `cancelled` (soft state change only).
- If mapped external event time changed externally, create manual review record; do not auto-reschedule in Phase 1.
- Skip unknown external events that are not mapped to existing appointment IDs.

### BE-5: Event ID Lifecycle Management
- Persist and maintain `google_event_id` and `outlook_event_id` on appointment creation and updates.
- Validate mapping integrity before external API operations.
- Backfill mapping metadata for existing connected appointments where feasible.

### BE-6: Cancellation Propagation + Audit
- On PropellQ cancellation, enqueue external delete actions for all active providers.
- Write audit entries with appointment ID, provider, external event ID, action result, timestamp.
- Ensure cancellation processing does not hard-delete appointment rows.

### BE-7: Conflict Resolution Engine (PropellQ Wins)
- Detect concurrent update windows via version or last-updated comparison.
- If conflict is detected, preserve PropellQ state and overwrite external event to match PropellQ.
- Emit conflict audit event including old/new values and resolution reason.

### BE-8: Retry/Backoff and Failure Isolation
- On provider/network/rate-limit failures, keep appointment transaction successful and enqueue retry.
- Apply exponential backoff retry strategy up to 3 attempts.
- Mark sync item as failed after max retries and emit admin alert event.

### BE-9: Webhook Handlers (Optional Acceleration)
- Implement optional webhook endpoints for Google/Outlook change notifications.
- Validate webhook signatures/challenges and map to provider event references.
- Use webhook events to trigger expedited pull reconciliation while retaining polling as source of reliability.

## Database Tasks

### DB-1: Appointments Sync Columns
- Add or validate appointment columns:
  - `google_event_id`
  - `outlook_event_id`
  - `last_synced_at`
  - `sync_status`
- Add indexes for provider event IDs and sync status queries.

### DB-2: CalendarSyncQueue Schema
- Create or validate `CalendarSyncQueue` with fields:
  - `appointment_id`
  - `action`
  - `calendar_type`
  - `retry_count`
  - `scheduled_retry_at`
  - `last_error`
- Add dequeue/processing indexes (`scheduled_retry_at`, `retry_count`, `calendar_type`).

### DB-3: Concurrency and Idempotency Controls
- Add optimistic concurrency/version field support on appointments.
- Add idempotency constraint to avoid duplicate queue rows for same appointment-action-provider key.
- Add audit tables/indexes for conflict and sync-failure review workflows.

## Integration Tasks

### INT-1: Google Calendar Sync Adapter
- Implement provider adapter for Google event update/delete/get changes.
- Handle pagination, updatedMin/sync token behavior, and provider error normalization.
- Detect and classify auth failures vs transient failures.

### INT-2: Microsoft Graph Sync Adapter
- Implement provider adapter for Outlook event update/delete/get changes.
- Handle delta/paging semantics and normalize Graph-specific errors.
- Detect token invalidation and route to reauthorization state.

### INT-3: Webhook Integration (Optional)
- Register/renew webhook subscriptions where supported.
- Process webhook callbacks with verification and replay protection.
- Fallback to polling-only mode when webhook subscription is unavailable/expired.

## Security/Compliance Tasks

### SEC-1: Token Use and Data Protection
- Ensure token refresh/exchange paths reuse secure storage from US-007/US-008.
- Redact tokens and provider secrets from logs/errors.
- Enforce TLS and secure outbound client configuration.

### SEC-2: Webhook Security Controls
- Verify provider signatures/challenge tokens.
- Reject unauthenticated or malformed webhook payloads.
- Rate-limit webhook endpoint abuse patterns.

## Ops/Observability Tasks

### OPS-1: Sync SLO/SLA Metrics
- Track and dashboard:
  - push sync latency percentiles (P50/P95/P99)
  - push success/failure by provider
  - pull reconciliation outcomes
  - conflict counts
  - queue depth and age
- Monitor compliance with 10-second push target.

### OPS-2: Alerting and Recovery Runbooks
- Alert on queue backlog growth and repeated provider failures.
- Alert when retry-exhausted items exceed threshold.
- Alert on token invalidation spikes requiring patient reauthorization.
- Add runbook for manual retry and external incident handling.

## Testing Tasks

### QA-1: Mapping and Persistence Tests
- Verify `google_event_id`/`outlook_event_id` persistence through appointment lifecycle.
- Verify sync status transitions (`pending`, `synced`, `failed`).

### QA-2: Push Sync Integration Tests
- Reschedule/cancel in PropellQ and verify external provider updates/deletes.
- Validate both providers update when dual connection is active.
- Verify push completion within 10 seconds under nominal conditions.

### QA-3: Pull Sync Behavioral Tests
- External event deletion should mark appointment cancelled in PropellQ.
- External time change should create manual review record (no auto-reschedule).
- Unknown external event IDs should be ignored safely.

### QA-4: Conflict Resolution Tests
- Simulate simultaneous PropellQ and external update.
- Validate PropellQ-wins behavior and external overwrite.
- Validate conflict audit entries are persisted.

### QA-5: Failure and Retry Tests
- Inject provider 429/network/token failures.
- Validate exponential backoff, max 3 attempts, and alert emission on exhaustion.
- Confirm appointment update flow remains non-blocking even when sync fails.

### QA-6: Webhook Tests (If Enabled)
- Validate webhook verification handshake.
- Validate real-time trigger path updates reconciliation timing.
- Validate polling still recovers missed webhook deliveries.

### QA-7: Load and Resilience Tests
- Simulate 1000 concurrent reschedules and measure queue stability.
- Validate worker throughput, queue drain time, and absence of duplicate sync actions.

---

## 4. Dependencies

- US-003 provides stable appointment lifecycle events.
- US-007 provides Google OAuth/token infrastructure.
- US-008 provides Outlook OAuth/token infrastructure.
- EP-TECH-001 provides centralized monitoring/alerting and secret management.

---

## 5. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Concurrent updates cause inconsistent state | High | Optimistic locking + PropellQ-wins conflict resolver + audit trail |
| Provider API rate limiting or outages | Medium | Exponential backoff, retry queue, provider-specific alerting |
| Corrupt/missing external event IDs break sync | Medium | Mapping integrity validation, safe skip, recovery path to recreate mapping |
| Token invalidation causes persistent sync failure | Medium | Detect auth failures, mark provider auth state expired, prompt reauthorization |
| Webhook delivery gaps create stale sync windows | Low | Polling remains canonical reconciliation mechanism |

---

## 6. Definition of Done

- [x] Appointment event ID columns and queue schema implemented.
- [x] Push sync worker updates/deletes external events for Google and Outlook.
- [x] Pull sync scheduler runs every 30 minutes with reconciliation rules.
- [x] Cancellation propagation and audit logging implemented.
- [x] Conflict resolution enforces PropellQ as source of truth.
- [x] Retry/backoff queue with max-attempt alerting implemented.
- [x] Optional webhook handlers implemented or explicitly feature-flagged off.
- [x] Metrics dashboards and alerts operational for sync latency/failures.
- [x] Unit, integration, conflict, failure, and load tests passing.
- [x] AC-1 through AC-7 fully traced and validated.

---

## 7. Suggested Execution Order

1. DB-1, DB-2, DB-3
2. INT-1, INT-2, SEC-1
3. BE-1, BE-2, BE-5, BE-6
4. BE-3, BE-4
5. BE-7, BE-8
6. BE-9, INT-3, SEC-2 (if webhook-enabled)
7. OPS-1, OPS-2
8. QA-1 through QA-7
9. Final AC validation and release readiness sign-off
