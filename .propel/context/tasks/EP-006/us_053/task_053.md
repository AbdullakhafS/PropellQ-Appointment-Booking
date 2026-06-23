# TASK-053: Build Patient Dashboard UI

**User Story:** US-053 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_053/us_053.md`
**Priority:** HIGH
**Status:** Done
**Created:** 2026-06-19

## Objective
Build a patient-facing dashboard with appointment, activity, profile, and notification cards that is responsive, accessible, and refreshes data without full page reload.

## AC Mapping
- AC-1: FE-1, BE-1, QA-1
- AC-2: FE-2, BE-1, QA-1
- AC-3: FE-3, QA-2
- AC-4: FE-4, BE-2, QA-3

## Tasks
### FE-1: Dashboard Entry and Routing
- Add dashboard route and authenticated access guard.

### FE-2: Core Card Layout
- Implement cards for upcoming appointments, recent activity, profile summary, notifications/documents.

### FE-3: Responsive Grid
- Apply 375/768/1024+ breakpoints and card stacking behavior.

### FE-4: Incremental Refresh UX
- Refresh card data via API polling or event-based updates without full reload.

### BE-1: Dashboard Aggregate API
- Provide consolidated endpoint for dashboard card data.

### BE-2: Refresh-Optimized Payloads
- Support partial payload updates to minimize network costs.

### QA-1: Functional Tests
- Validate dashboard access and card rendering for logged-in patient.

### QA-2: Responsive Tests
- Validate layout on mobile/tablet/desktop.

### QA-3: Refresh Tests
- Validate data updates without full page refresh.

## Definition of Done
- [x] Dashboard route and cards implemented.
- [x] Responsive behavior validated.
- [x] Incremental refresh working.
- [x] AC-1 through AC-4 validated.
