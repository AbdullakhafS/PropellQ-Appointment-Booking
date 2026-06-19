# TASK-065: Display Insurance Verification Status Metrics

**User Story:** US-065 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_065/us_065.md`
**Priority:** MEDIUM
**Status:** Planned
**Created:** 2026-06-19

## Objective
Expose insurance verification analytics (verified/pending/failed) with trend and status filtering for operational follow-up.

## AC Mapping
- AC-1: FE-1, BE-1, QA-1
- AC-2: FE-2, QA-2
- AC-3: FE-3, BE-2, QA-3
- AC-4: FE-4, QA-2

## Tasks
### FE-1: Verification KPI Card
- Show counts for verified, pending, failed statuses.

### FE-2: Filtered Verification View
- Update metrics by date/provider/status filters.

### FE-3: Issue Highlight
- Highlight pending/failed buckets needing action.

### FE-4: Status Filter Controls
- Add status-specific filtering for verification state.

### BE-1: Verification Metrics API
- Aggregate status counts and trend by selected scope.

### BE-2: Issue Flag Output
- Return issue emphasis metadata for dashboard display.

### QA-1: KPI Tests
- Validate status counts displayed accurately.

### QA-2: Filter Tests
- Validate status/date/provider filtering behavior.

### QA-3: Highlight Tests
- Validate issue states highlighted correctly.

## Definition of Done
- [ ] Verification metrics and status breakdown implemented.
- [ ] Filters and highlighting validated.
- [ ] AC-1 through AC-4 validated.
