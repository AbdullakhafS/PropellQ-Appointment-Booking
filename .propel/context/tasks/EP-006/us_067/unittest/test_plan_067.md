# UNIT-TEST-PLAN-067: Dashboard Auto-Refresh (5 min)

User Story: US-067 (EP-006)
Source File: .propel/context/tasks/EP-006/us_067/us_067.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for dashboard auto-refresh behavior, including 5-minute cadence scheduling, no-reload updates, loading indicators, and inactive-tab throttling.

---

## 2. Scope and Assumptions

### In Scope
- Client scheduler that triggers refresh every 5 minutes.
- Metric updates without full page reload.
- Loading indicator and last-updated timestamp behavior.
- Inactive tab pause/throttling logic.

### Out of Scope
- Real-time websocket event stream implementation.
- Cross-service performance benchmarking.

### Assumptions
- Refresh logic uses timer abstraction/hook testable with fake timers.
- Visibility/inactivity state uses document visibility APIs or equivalent wrapper.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Dashboard auto-refreshes every 5 minutes | UT-067-001, UT-067-002 |
| AC-2 | Metrics update without full page reload | UT-067-003, UT-067-004 |
| AC-3 | Subtle loading indicator appears during refresh | UT-067-005, UT-067-006 |
| AC-4 | Inactive dashboard refresh throttles or pauses | UT-067-007, UT-067-008 |

---

## 4. Unit Test Areas

### UT-067-001: Refresh scheduler triggers poll on 5-minute cadence
- Use fake timers.
- Assert refresh action dispatch at 300000ms intervals.

### UT-067-002: Scheduler starts and cleans up timer on mount/unmount
- Mount/unmount component/hook.
- Assert timer registration and cleanup to prevent leaks.

### UT-067-003: Refresh updates metrics in-place without route reload
- Mock refresh response.
- Assert component state updates while route/page identity remains stable.

### UT-067-004: Incremental refresh preserves user context (filters/scroll state abstraction)
- Simulate refresh with active filters.
- Assert filters remain applied and data reflects same scope.

### UT-067-005: Loading indicator appears only during active refresh cycle
- Trigger refresh request lifecycle.
- Assert indicator appears on pending and clears on resolve.

### UT-067-006: Last-updated timestamp changes after successful refresh
- Mock successive refresh responses.
- Assert timestamp updates deterministically.

### UT-067-007: Visibility hidden state pauses or throttles refresh dispatch
- Simulate inactive tab/document hidden state.
- Assert scheduled refresh calls are paused/reduced.

### UT-067-008: Visibility restored resumes refresh cadence correctly
- Switch back to active visibility.
- Assert scheduler resumes with expected timing behavior.

### UT-067-009: Refresh failure shows non-blocking error and retains old data
- Mock failed refresh.
- Assert recoverable message and preservation of previous metrics.

### UT-067-010: Concurrent refresh guard prevents duplicate overlapping requests
- Simulate slow request and repeated timer ticks.
- Assert single in-flight request policy is enforced.

---

## 5. Test Data and Mocking Strategy

- Fixtures: baseline metrics, successive updates, error response.
- Mock utilities: fake timers, visibility API wrapper, refresh endpoint/service hook.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-067-001 through UT-067-008.

---

## 7. Suggested File Layout

- tests/unit/dashboard/DashboardAutoRefreshScheduler.test.ts
- tests/unit/dashboard/DashboardAutoRefreshBehavior.test.tsx
- tests/unit/dashboard/DashboardRefreshIndicators.test.tsx
- tests/unit/dashboard/DashboardRefreshVisibilityThrottle.test.ts
- tests/unit/dashboard/__fixtures__/dashboardRefresh.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-067-001 through UT-067-010 implemented.
- [ ] AC traceability retained.
- [ ] Coverage and CI reliability targets met.
