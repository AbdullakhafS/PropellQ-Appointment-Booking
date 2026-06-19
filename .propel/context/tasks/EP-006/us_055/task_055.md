# TASK-055: Display Past Appointments with Clinical Notes

**User Story:** US-055 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_055/us_055.md`
**Priority:** MEDIUM
**Status:** Planned
**Created:** 2026-06-19

## Objective
Provide a past appointment history view with released notes/download links and graceful empty/unavailable states.

## AC Mapping
- AC-1: FE-1, BE-1, QA-1
- AC-2: FE-2, BE-2, QA-2
- AC-3: FE-3, QA-2
- AC-4: FE-4, QA-3

## Tasks
### FE-1: Past Appointment History List
- Render date, provider, status for prior visits.

### FE-2: Released Notes Access
- Show view/download links for released summaries.

### FE-3: Unavailable Notes Messaging
- Show clear message when notes are not released.

### FE-4: Appointment Detail Panel
- Load visit details without navigation errors.

### BE-1: Past Visits API
- Return historical appointments for authenticated patient.

### BE-2: Release Policy Filter
- Include only released clinical notes and secure links.

### QA-1: Past History Tests
- Validate historical list completeness.

### QA-2: Notes Availability Tests
- Validate released/unreleased behavior.

### QA-3: Detail Loading Tests
- Validate selecting visit loads details correctly.

## Definition of Done
- [ ] Past appointments rendered.
- [ ] Released notes displayed securely.
- [ ] Missing-note UX handled.
- [ ] AC-1 through AC-4 validated.
