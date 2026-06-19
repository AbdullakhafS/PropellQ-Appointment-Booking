# TASK-064: Display Intake Completion Rates

**User Story:** US-064 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_064/us_064.md`
**Priority:** MEDIUM
**Status:** Planned
**Created:** 2026-06-19

## Objective
Show intake completion KPIs and trends to track pre-visit readiness, with date/provider filters and low-completion highlighting.

## AC Mapping
- AC-1: FE-1, BE-1, QA-1
- AC-2: FE-2, QA-2
- AC-3: FE-3, BE-2, QA-3
- AC-4: FE-2, QA-2

## Tasks
### FE-1: Completion Rate KPI
- Display completion percentage and count summary.

### FE-2: Date/Provider Filter Binding
- Apply filters to intake completion queries.

### FE-3: Low Completion Highlight
- Emphasize KPI when completion rate is below threshold.

### BE-1: Completion Aggregation API
- Compute completed intake forms / scheduled visits by filter scope.

### BE-2: Threshold Flag Output
- Return low-completion flag for dashboard highlighting.

### QA-1: KPI Tests
- Validate completion rate values.

### QA-2: Filter Tests
- Validate completion metrics update by selected filters.

### QA-3: Highlight Tests
- Validate low-completion state appears correctly.

## Definition of Done
- [ ] Intake completion KPI and trend components implemented.
- [ ] Filter and threshold highlight behavior validated.
- [ ] AC-1 through AC-4 validated.
