# TASK-006: Implement Multi-Channel Appointment Reminder Engine

**User Story:** US-006 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_006/us_006.md`  
**Priority:** CRITICAL  
**Estimated Effort:** 4-5 dev days + QA/delivery validation  
**Status:** Completed  
**Created:** 2026-06-18

---

## 1. Objective

Implement a reliable reminder system that sends SMS and email reminders at 48h, 24h, and 2h before appointment time, honoring channel preferences and timezone rules, with retries, delivery logging, and opt-out handling.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Schedule reminders at 48h/24h/2h; scan every 15 minutes | BE-1, BE-2, OPS-1 |
| AC-2 | SMS content and provider integration | FE-1, INT-1 |
| AC-3 | Email reminder template with ICS and links | FE-2, INT-2 |
| AC-4 | Patient channel preferences with default both | BE-3, DB-2 |
| AC-5 | Timezone-accurate reminder timing and display | BE-4, QA-2 |
| AC-6 | Retry logic up to 3 attempts with backoff | BE-5, OPS-2 |
| AC-7 | ReminderLog tracking for every attempt | DB-1, BE-6 |
| AC-8 | Skip logic for opt-out and cancelled appointments | BE-7, QA-3 |

---

## 3. Layered Implementation Tasks

## Frontend/Template Tasks

### FE-1: SMS Reminder Template
- Implement concise SMS message template under 160 chars.
- Include first name, provider, local date/time, and reschedule link.
- Add template token validation (no unresolved placeholders).

### FE-2: Email Reminder Template
- Build HTML reminder template with:
  - appointment details
  - provider information
  - location/context links
  - reschedule/cancel actions
  - ICS attachment metadata
- Add subject format: `Appointment Reminder: {Date} with Dr. {Provider}`.

### FE-3: Preference Management Surface (if existing profile UI)
- Ensure channel preference values map to backend model (`sms`, `email`, both).
- Default to both when no explicit preference exists.

## Backend/Service Tasks

### BE-1: Reminder Scheduler Job
- Implement scheduler that runs every 15 minutes.
- Detect due reminder windows (48h, 24h, 2h) using appointment time and timezone-aware evaluation.
- Prevent duplicate creation for each reminder window.

### BE-2: Reminder Event Generation
- Create reminder events per due window and channel.
- Mark appointment reminder flags (`reminder_sent_48h_at`, etc.) only after successful dispatch attempt creation.
- Ensure cancelled/no-show/completed appointments are excluded.

### BE-3: Channel Preference Enforcement
- Resolve patient reminder preferences from stored settings.
- If preference missing, apply default channels (SMS + Email).
- Respect opt-out and do-not-disturb flags where configured.

### BE-4: Timezone Conversion Logic
- Normalize storage in UTC and calculate send times in patient local timezone.
- Resolve timezone source priority: patient profile -> browser fallback/default.
- Include local display time formatting in outbound messages.

### BE-5: Retry Orchestration
- Implement retry attempts on transient send failures:
  - +5 seconds
  - +30 seconds
  - +5 minutes
- Stop after max attempts and set status for manual review.

### BE-6: Delivery Logging
- Persist all attempts to `ReminderLog` including:
  - patient_id
  - appointment_id
  - reminder_type
  - channel
  - sent_at
  - delivery_status
  - retry_count
  - external_message_id
  - failure_reason
- Add correlation IDs for traceability across services.

### BE-7: Skip/Guard Conditions
- Skip if appointment cancelled/rescheduled beyond relevant window.
- Skip if all channels opted out.
- Record skip reasons for operational visibility.

## Database Tasks

### DB-1: ReminderLog Table
- Create/validate `ReminderLog` schema and indexes:
  - appointment_id
  - patient_id
  - reminder_type
  - sent_at
  - delivery_status
- Ensure searchable operational queries by date range and status.

### DB-2: Appointment and Patient Reminder Fields
- Validate reminder timestamps on appointments (`48h`, `24h`, `2h`).
- Validate patient preference fields:
  - preferred_timezone
  - reminder_channels JSON
- Add migration defaults for existing users.

### DB-3: Duplicate-Send Safeguards
- Add uniqueness/idempotency guard for appointment+reminder_type+channel where applicable.
- Ensure scheduler reruns do not create duplicate sends.

## Integration Tasks

### INT-1: SMS Provider Integration
- Integrate with SMS provider API (Twilio-equivalent).
- Map provider response IDs and error codes to internal statuses.
- Handle rate-limit and temporary outage responses.

### INT-2: Email Provider Integration
- Reuse email infrastructure from confirmation pipeline.
- Attach ICS payload when required.
- Capture provider message IDs and bounce/failure callbacks.

## Ops/Observability Tasks

### OPS-1: Reminder Throughput and SLA Metrics
- Track metrics per channel:
  - reminders scheduled
  - reminders sent
  - delivery success rate
  - send latency
  - skip counts
- Publish dashboard segmented by 48h/24h/2h windows.

### OPS-2: Alerting and Failure Recovery
- Alert when delivery rates fall below thresholds:
  - SMS <95%
  - Email <99%
- Alert on sustained retry spikes and provider errors.
- Queue failed reminders for manual triage workflow.

## Testing Tasks

### QA-1: Unit Tests
- Window calculation tests for 48h/24h/2h boundaries.
- Preference filtering and channel selection tests.
- Retry sequencing and max-attempt cutoff tests.

### QA-2: Integration Tests
- End-to-end reminder generation for each window.
- Timezone conversion validation across UTC-8 to UTC+12.
- SMS and email provider response mapping verification.

### QA-3: Behavioral/Edge Case Tests
- Cancelled appointment should not send reminders.
- Opted-out patient should not receive reminders.
- Rescheduled appointments should use updated reminder schedule.
- Duplicate scheduler runs should not duplicate sends.

### QA-4: Delivery/Load Tests
- Batch test of 100+ reminders across channels.
- Validate success-rate objectives (>95% SMS, >99% Email) in controlled environment.
- Validate scheduler stability under peak reminder windows.

---

## 4. Dependencies

- US-003 booking flow must provide stable appointment records.
- US-004 email infrastructure available for reminder email path.
- Patient profile/preferences (EP-005) available for channel and timezone settings.
- Notification provider credentials and secrets configured.

---

## 5. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Provider throttling drops reminder throughput | High | Backoff + queue buffering + provider health alerting |
| Timezone miscalculation sends reminders at wrong local time | Medium | UTC normalization, timezone regression tests, explicit offset logging |
| Duplicate sends from scheduler reruns | Medium | Idempotency guard and per-window send flags |
| High bounce/failure rate due to stale contacts | Medium | Contact validation and manual follow-up queue |
| Reminder sent after cancellation | Medium | Final status check immediately before send |

---

## 6. Definition of Done

- [x] 15-minute scheduler implemented and running.
- [x] 48h/24h/2h reminder windows generated correctly.
- [x] SMS and email templates finalized and integrated.
- [x] Channel preferences and defaults enforced.
- [x] Timezone-aware scheduling and rendering validated.
- [x] Retry flow implemented with max 3 attempts.
- [x] ReminderLog persistence and indexing complete.
- [x] Opt-out/cancelled guard paths implemented.
- [x] Delivery metrics dashboards and alerts configured.
- [x] Unit/integration/edge/load tests passing.
- [x] Story AC-1 through AC-8 mapped and validated.

---

## 7. Suggested Execution Order

1. DB-1, DB-2, DB-3
2. BE-1, BE-2
3. BE-3, BE-4
4. FE-1, FE-2, FE-3
5. INT-1, INT-2
6. BE-5, BE-6, BE-7
7. OPS-1, OPS-2
8. QA-1 through QA-4
9. Final AC validation and sign-off
