# TASK-061: Display No-Show Rate and Trends

**User Story:** US-061 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_061/us_061.md`
**Priority:** MEDIUM
**Status:** Done
**Created:** 2026-06-19

## Objective
Expose no-show rate KPI and trend charts with date filtering and period-over-period comparison for admin operational insight.

## AC Mapping
- AC-1: FE-1, QA-1
- AC-2: FE-2, BE-1, QA-2
- AC-3: FE-3, BE-1, QA-2
- AC-4: FE-4, BE-2, QA-3

## Tasks
### FE-1: No-Show KPI Card
- Show current no-show rate and change indicator.

### FE-2: Trend Visualization
- Plot no-show percentage over selectable time range.

### FE-3: Date Filter Binding
- Bind date range control to no-show trend queries.

### FE-4: Prior Period Comparison
- Display comparison vs prior baseline period.

### BE-1: No-Show Metrics API
- Calculate no-show rate from missed/scheduled appointments by period.

### BE-2: Comparison Metrics API
- Return prior-period value and delta.

### QA-1: KPI Tests
- Validate no-show card values.

### QA-2: Trend and Filter Tests
- Validate trend updates by selected date range.

### QA-3: Comparison Tests
- Validate period-over-period calculations and labels.

## Definition of Done
- [x] No-show KPI and trends implemented.
- [x] Filter and comparison logic validated.
- [x] AC-1 through AC-4 validated.
