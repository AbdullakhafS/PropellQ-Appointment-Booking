# TASK-060: Build Admin Operational Dashboard UI

**User Story:** US-060 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_060/us_060.md`
**Priority:** HIGH
**Status:** Done
**Created:** 2026-06-19

## Objective
Create an admin operations dashboard with KPI cards, charts, and filters for date/provider/location, with secure role-gated access and fast refresh behavior.

## AC Mapping
- AC-1: FE-1, SEC-1, QA-1
- AC-2: FE-2, BE-1, QA-2
- AC-3: FE-3, BE-2, QA-3
- AC-4: BE-3, QA-4

## Tasks
### FE-1: Admin Dashboard Route and Access
- Add admin-only dashboard route and navigation entry.

### FE-2: KPI and Chart Components
- Render utilization, wait-time, and no-show KPI cards and charts.

### FE-3: Filter Controls
- Add date/provider/location filters with immediate data update behavior.

### BE-1: Admin Metrics API
- Provide aggregate metrics endpoint for dashboard cards and charts.

### BE-2: Filtered Query Support
- Support filter parameters across all metric queries.

### BE-3: Freshness/Refresh Metadata
- Return last-updated timestamp and support refresh calls.

### SEC-1: Role Authorization
- Enforce admin role checks on route and API.

### QA-1: Access Tests
- Validate only authorized admins can access dashboard.

### QA-2: Render Tests
- Validate KPI cards and charts appear with expected data.

### QA-3: Filter Tests
- Validate metrics update correctly when filters change.

### QA-4: Refresh Tests
- Validate latest data appears on refresh.

## Definition of Done
- [x] Admin dashboard UI implemented.
- [x] Metrics and filters functional.
- [x] Authorization enforced.
- [x] AC-1 through AC-4 validated.
