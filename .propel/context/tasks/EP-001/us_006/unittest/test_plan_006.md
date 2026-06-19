# UNIT-TEST-PLAN-006: Send Appointment Reminders (48h, 24h, 2h)

User Story: US-006 (EP-001)
Source File: .propel/context/tasks/EP-001/us_006/us_006.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for reminder scheduling and delivery orchestration to validate interval generation, channel preferences, timezone-correct dispatch windows, retry policy, and delivery tracking.

---

## 2. Scope and Assumptions

### In Scope
- Reminder schedule creation at 48h/24h/2h offsets.
- Channel routing logic using patient reminder preferences.
- Reminder message composition for SMS and email models.
- Retry policy execution after provider failures.
- Reminder log write behavior for attempts/outcomes.

### Out of Scope
- Provider-level deliverability guarantees.
- End-to-end calendar attachment rendering.
- Real cron/queue infrastructure health behavior.

### Assumptions
- Reminder service exposes pure scheduling and composition functions.
- Timezone resolver utility is testable and mockable.
- Delivery adapters are injected and mockable.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Creates 48h/24h/2h reminders and checks on schedule | UT-006-001, UT-006-002 |
| AC-2 | SMS content model correctness | UT-006-003 |
| AC-3 | Email reminder content model correctness | UT-006-004 |
| AC-4 | Patient preference channels respected | UT-006-005, UT-006-006 |
| AC-5 | Timezone-accurate reminder timing | UT-006-007 |
| AC-6 | Retry policy for failed sends | UT-006-008, UT-006-009 |
| AC-7 | ReminderLog entries include required metadata | UT-006-010 |
| AC-8 | Do-not-disturb / opt-out skip behavior | UT-006-011 |

---

## 4. Unit Test Areas

## A. Reminder Scheduling

### UT-006-001: Generates reminder events at configured offsets
- Provide appointment datetime fixture.
- Assert scheduled reminder events at 48h, 24h, and 2h offsets.

### UT-006-002: Pending reminder selector returns due reminders for current cycle
- Mock current time and reminder store.
- Assert only due reminders are selected for dispatch.

## B. Message Composition

### UT-006-003: SMS message builder composes required concise reminder text
- Build SMS payload.
- Assert patient first name, provider, date/time, and reschedule link fields appear.

### UT-006-004: Email model builder composes rich reminder template payload
- Build email payload model.
- Assert appointment details, provider profile fields, map/link placeholders, and subject format.

## C. Preferences and Timezone

### UT-006-005: Defaults to both channels when no explicit preferences exist
- Mock missing preference record.
- Assert delivery channel selection includes sms + email.

### UT-006-006: Honors single-channel preference (sms-only or email-only)
- Mock preference variants.
- Assert only selected channel dispatches are emitted.

### UT-006-007: Reminder schedule resolves using patient-local timezone
- Mock patient timezone and UTC appointment input.
- Assert scheduled dispatch times match local-time offsets.

## D. Retry and Logging

### UT-006-008: Transient send failure triggers retry sequence
- Mock first-attempt provider failure.
- Assert retry jobs scheduled at configured intervals.

### UT-006-009: Retry exhaustion raises manual-review signal
- Force repeated failures across max attempts.
- Assert escalation/manual-review event is emitted.

### UT-006-010: Delivery attempts write ReminderLog with required fields
- Execute send path.
- Assert log entry includes patient_id, appointment_id, reminder_type, channel, sent_at, status, retry_count.

## E. Opt-Out and Cancellation Guards

### UT-006-011: Opted-out or canceled appointments are skipped safely
- Provide opted-out and canceled fixtures.
- Assert no reminder creation/dispatch occurs.

---

## 5. Test Data Strategy

- Appointment fixtures across multiple timezones and boundary times.
- Preference fixtures: both, sms-only, email-only, none.
- Delivery fixtures: success, transient failure, terminal failure.

---

## 6. Mocking Strategy

- Mock reminder repository, delivery adapters, and retry scheduler.
- Mock timezone resolver and clock utility.
- Mock audit/log persistence for deterministic assertions.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-006-001 through UT-006-010 before merge.

---

## 8. Exit Criteria

- All AC-mapped reminder tests pass.
- Timezone and channel-routing logic verified.
- Retry and log behavior validated.
- Coverage thresholds achieved.

---

## 9. Suggested File Layout

- tests/unit/reminders/ReminderSchedule.test.ts
- tests/unit/reminders/ReminderDispatch.test.ts
- tests/unit/reminders/ReminderPreferences.test.ts
- tests/unit/reminders/__fixtures__/reminder.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-006.
- [ ] Test cases UT-006-001 through UT-006-011 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
