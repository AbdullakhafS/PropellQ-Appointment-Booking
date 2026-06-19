# TASK-063: Display Appointment Utilization Analytics

**User Story:** US-063 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_063/us_063.md`
**Priority:** MEDIUM
**Status:** Planned
**Created:** 2026-06-19

## Objective
Provide utilization analytics showing booked vs available slots with provider/location/specialty filtering to support capacity optimization.

## AC Mapping
- AC-1: FE-1, QA-1
- AC-2: FE-2, BE-1, QA-2
- AC-3: FE-3, QA-1
- AC-4: FE-4, BE-1, QA-2

## Tasks
### FE-1: Utilization KPI Card
- Show utilization percentage and count summary.

### FE-2: Filter-Aware Utilization View
- Update analytics by provider/specialty/location filters.

### FE-3: Booked vs Available Chart
- Show comparative visualization for slot usage.

### FE-4: Scope Indicator
- Show currently selected provider/location scope in header.

### BE-1: Utilization API
- Compute utilization as booked/available by selected dimensions.

### QA-1: KPI + Chart Tests
- Validate utilization values and chart rendering.

### QA-2: Filter Scope Tests
- Validate provider/location filtering behavior.

## Definition of Done
- [ ] Utilization metrics and chart implemented.
- [ ] Filtering by dimensions validated.
- [ ] AC-1 through AC-4 validated.
