# TASK-062: Display Average Wait Time Metrics

**User Story:** US-062 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_062/us_062.md`
**Priority:** MEDIUM
**Status:** Planned
**Created:** 2026-06-19

## Objective
Show average wait-time KPIs and trends for clinic operations, including threshold-based warning states and filter-aware analytics.

## AC Mapping
- AC-1: FE-1, QA-1
- AC-2: FE-2, BE-1, QA-2
- AC-3: FE-3, BE-1, QA-2
- AC-4: FE-4, BE-2, QA-3

## Tasks
### FE-1: Wait-Time KPI Card
- Display average check-in-to-start wait time.

### FE-2: Wait-Time Trend Chart
- Display trend by selected date range.

### FE-3: Filter Integration
- Bind filters to wait-time metric requests.

### FE-4: Threshold Warning UI
- Highlight KPI when configured threshold exceeded.

### BE-1: Wait-Time Aggregation API
- Compute average and percentile wait metrics from event timestamps.

### BE-2: Threshold Evaluation
- Return threshold state for dashboard warning display.

### QA-1: KPI Tests
- Validate wait-time KPI value rendering.

### QA-2: Trend + Filter Tests
- Validate trend and filter updates.

### QA-3: Warning State Tests
- Validate high-wait threshold warning behavior.

## Definition of Done
- [ ] Wait-time metrics and trends implemented.
- [ ] Filtered calculations and warning states verified.
- [ ] AC-1 through AC-4 validated.
