# TASK-054: Display Upcoming Appointments with Actions

**User Story:** US-054 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_054/us_054.md`
**Priority:** HIGH
**Status:** Planned
**Created:** 2026-06-19

## Objective
Show upcoming appointments with key details and context-sensitive actions for reschedule/cancel/view details.

## AC Mapping
- AC-1: FE-1, BE-1, QA-1
- AC-2: FE-2, BE-2, QA-2
- AC-3: BE-1, QA-1
- AC-4: FE-3, QA-3

## Tasks
### FE-1: Upcoming Appointments List
- Render provider, date/time, location, and status badge.

### FE-2: Conditional Action Buttons
- Show reschedule/cancel only when policy allows.

### FE-3: Action Workflow Triggers
- Route to reschedule/cancel/detail workflows.

### BE-1: Upcoming Filter API
- Return only future appointments.

### BE-2: Action Eligibility Rules
- Return action eligibility flags per appointment.

### QA-1: Listing Tests
- Validate only upcoming appointments shown.

### QA-2: Permission Tests
- Validate action button visibility by policy.

### QA-3: Workflow Navigation Tests
- Validate action click starts correct workflow.

## Definition of Done
- [ ] Upcoming appointments list implemented.
- [ ] Action eligibility correctly enforced.
- [ ] Workflow initiation validated.
- [ ] AC-1 through AC-4 validated.
