# TASK-068: Implement Date/Provider/Location Dashboard Filters

**User Story:** US-068 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_068/us_068.md`
**Priority:** MEDIUM
**Status:** Planned
**Created:** 2026-06-19

## Objective
Implement accessible date/provider/location filters that apply server-side across dashboard KPIs and charts, with clear reset behavior and safe fallback handling.

## AC Mapping
- AC-1: FE-1, QA-1
- AC-2: FE-2, BE-1, QA-2
- AC-3: FE-3, QA-3
- AC-4: FE-4, BE-2, QA-4

## Tasks
### FE-1: Filter Control Set
- Add date-range picker, provider selector, and location selector.

### FE-2: Filtered Data Updates
- Trigger dashboard re-query on filter changes.

### FE-3: Clear/Reset Behavior
- Implement clear filters action returning dashboard to default scope.

### FE-4: Invalid Selection UX
- Show fallback value/message for invalid filter combinations.

### BE-1: Server-Side Filter Support
- Apply filter parameters consistently across KPI/chart queries.

### BE-2: Validation and Fallback
- Validate filter inputs and return safe default on invalid values.

### QA-1: Filter Availability Tests
- Validate all three filters present and usable.

### QA-2: Update Tests
- Validate dashboard updates on filter change.

### QA-3: Reset Tests
- Validate clearing filters restores default scope.

### QA-4: Invalid Input Tests
- Validate invalid selection fallback behavior.

## Definition of Done
- [ ] Date/provider/location filters implemented.
- [ ] Server-side filtering behavior validated.
- [ ] Reset and fallback handling complete.
- [ ] AC-1 through AC-4 validated.
