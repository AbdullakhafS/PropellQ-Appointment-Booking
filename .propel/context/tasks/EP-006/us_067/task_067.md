# TASK-067: Implement Dashboard Auto-Refresh (5 min)

**User Story:** US-067 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_067/us_067.md`
**Priority:** MEDIUM
**Status:** Planned
**Created:** 2026-06-19

## Objective
Implement low-disruption dashboard auto-refresh every 5 minutes with loading indicators, last-updated timestamps, and background throttling when inactive.

## AC Mapping
- AC-1: FE-1, QA-1
- AC-2: FE-2, BE-1, QA-2
- AC-3: FE-3, QA-3
- AC-4: FE-4, QA-4

## Tasks
### FE-1: Refresh Scheduler
- Add client refresh timer defaulting to 5 minutes.

### FE-2: Incremental Data Refresh
- Refresh metrics via API calls without full page reload.

### FE-3: Loading Indicator and Last Updated
- Show subtle loading state and timestamp of last successful refresh.

### FE-4: Inactive Tab Throttling
- Pause or throttle refresh when tab/window inactive.

### BE-1: Lightweight Refresh Endpoints
- Support efficient delta/full refresh endpoint usage.

### QA-1: Cadence Tests
- Validate automatic refresh every 5 minutes.

### QA-2: No-Reload Tests
- Validate UI updates without full page refresh.

### QA-3: Indicator Tests
- Validate loading and timestamp behavior.

### QA-4: Inactivity Tests
- Validate throttling/pause when dashboard inactive.

## Definition of Done
- [ ] 5-minute auto-refresh implemented.
- [ ] Loading and last-updated UX implemented.
- [ ] Inactive throttling behavior validated.
- [ ] AC-1 through AC-4 validated.
