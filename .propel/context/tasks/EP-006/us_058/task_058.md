# TASK-058: Enable Notification Preference Management

**User Story:** US-058 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_058/us_058.md`
**Priority:** MEDIUM
**Status:** Planned
**Created:** 2026-06-19

## Objective
Provide patient controls to manage notification channel preferences (email/SMS/in-app), persist settings, and enforce opt-out suppression in downstream reminders.

## AC Mapping
- AC-1: FE-1, QA-1
- AC-2: FE-2, BE-1, QA-2
- AC-3: BE-2, QA-3
- AC-4: FE-3, BE-1, QA-2

## Tasks
### FE-1: Preference Controls UI
- Add channel toggles for email/SMS/in-app notifications.

### FE-2: Save Preference Action
- Persist changes and show save confirmation.

### FE-3: Preference Rehydration
- Load and display current saved settings on revisit.

### BE-1: Preference Store API
- Read/write notification preferences by patient.

### BE-2: Opt-Out Enforcement
- Ensure opted-out channels are suppressed in reminder pipeline.

### QA-1: Selection Tests
- Validate patient can choose channel preferences.

### QA-2: Persistence Tests
- Validate settings save and reload correctly.

### QA-3: Suppression Tests
- Validate opted-out channels do not receive notifications.

## Definition of Done
- [ ] Preference UI and persistence implemented.
- [ ] Opt-out channel suppression enforced.
- [ ] Settings reload correctly.
- [ ] AC-1 through AC-4 validated.
