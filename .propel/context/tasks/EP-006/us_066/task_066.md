# TASK-066: Display AI-Human Agreement Rate

**User Story:** US-066 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_066/us_066.md`
**Priority:** MEDIUM
**Status:** Planned
**Created:** 2026-06-19

## Objective
Provide agreement-rate analytics comparing AI suggestions and human-reviewed outcomes, including trend and category breakdown for quality oversight.

## AC Mapping
- AC-1: FE-1, BE-1, QA-1
- AC-2: FE-2, QA-2
- AC-3: FE-3, QA-2
- AC-4: FE-4, BE-2, QA-3

## Tasks
### FE-1: Agreement KPI Card
- Show current agreement percentage and directional change.

### FE-2: Trend Chart
- Plot agreement percentage over selected date range.

### FE-3: Filter Controls
- Bind date/provider/workflow filters to agreement metrics.

### FE-4: Category Breakdown View
- Provide breakdown by document type or workflow.

### BE-1: Agreement Metrics API
- Compute agreement from reviewed AI suggestions vs final human outcomes.

### BE-2: Category Aggregation API
- Return breakdown metrics by selected category dimension.

### QA-1: KPI Tests
- Validate agreement percentage calculations.

### QA-2: Trend/Filter Tests
- Validate trend updates and filter behavior.

### QA-3: Breakdown Tests
- Validate category drill-down output.

## Definition of Done
- [ ] Agreement KPI and trend implemented.
- [ ] Category breakdown available.
- [ ] Filter behavior validated.
- [ ] AC-1 through AC-4 validated.
