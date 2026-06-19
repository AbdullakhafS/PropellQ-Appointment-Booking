# UNIT-TEST-PLAN-053: Patient Dashboard UI

User Story: US-053 (EP-006)
Source File: .propel/context/tasks/EP-006/us_053/us_053.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define a unit test plan for Patient Dashboard UI to validate rendering, data binding, responsive behavior, navigation interactions, and refresh behavior without full page reload.

---

## 2. Scope and Assumptions

### In Scope
- Dashboard container/component rendering logic.
- Dashboard cards: appointments, recent activity, profile summary, notifications/documents navigation triggers.
- Data states: loading, success, empty, and error where applicable.
- Client-side refresh/update behavior.
- Mobile-specific rendering rules exposed via component logic (breakpoint hooks/flags).

### Out of Scope
- Full end-to-end routing and backend integration correctness.
- Browser-level visual pixel validation.
- Admin analytics screens.

### Assumptions
- Frontend stack uses component-based UI (React or equivalent) with unit test tooling (Jest/Vitest + Testing Library).
- Data is provided via service hooks or API abstraction that can be mocked.
- Responsive behavior is controlled by viewport hook/util or conditional rendering logic testable in unit tests.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Logged-in patient can access dashboard from portal | UT-053-001, UT-053-002 |
| AC-2 | Dashboard shows appointments, activity, profile summary | UT-053-003, UT-053-004, UT-053-005 |
| AC-3 | Dashboard adapts to mobile screens | UT-053-006, UT-053-007 |
| AC-4 | Updated values appear without full page reload | UT-053-008, UT-053-009 |

---

## 4. Unit Test Areas

## A. Container and Access Behavior

### UT-053-001: Dashboard route guard allows authenticated user
- Mock authenticated state.
- Assert dashboard container renders.
- Assert no redirect/fallback message is shown.

### UT-053-002: Dashboard route guard blocks unauthenticated user
- Mock unauthenticated state.
- Assert dashboard content is not rendered.
- Assert expected access fallback behavior (redirect callback or access message trigger).

## B. Core Data Rendering

### UT-053-003: Dashboard renders all required sections on successful load
- Mock successful data for appointments, recent activity, profile summary.
- Assert all section headers/cards are present.
- Assert key summary values render from mock data.

### UT-053-004: Empty-state rendering for cards with no data
- Mock no upcoming appointments and no recent activity.
- Assert empty-state messages/actions appear per section.
- Assert component remains stable (no crash, no undefined output).

### UT-053-005: Error-state rendering for partial data failure
- Mock one data source failure (for example activity) while others succeed.
- Assert non-failing sections still render.
- Assert section-level fallback/error indicator appears for failed source.

## C. Responsive Behavior

### UT-053-006: Mobile breakpoint layout flags are applied
- Mock viewport hook/util to mobile size.
- Assert mobile layout variant/class/props are used by dashboard cards.
- Assert desktop-specific elements are hidden or replaced where expected.

### UT-053-007: Desktop breakpoint layout is preserved
- Mock viewport hook/util to desktop size.
- Assert desktop layout variant/class/props are used.
- Assert card ordering/grouping matches desktop rules.

## D. Refresh and Live Update Behavior

### UT-053-008: Data refresh updates displayed values without full remount
- Render dashboard with initial mock data.
- Trigger refresh/update callback (polling tick, refetch action, or subscription event).
- Assert changed values are displayed.
- Assert top-level component instance remains mounted (no forced full reload behavior).

### UT-053-009: Concurrent refresh handles race safely
- Simulate two close refresh events with different responses.
- Assert final rendered values reflect latest successful data.
- Assert no stale overwrite or unhandled promise errors.

## E. Navigation Actions from Dashboard Cards

### UT-053-010: Appointments card primary action triggers expected navigation intent
- Click appointments CTA/view-all action.
- Assert navigation callback invoked with expected destination.

### UT-053-011: Documents or notifications card action triggers expected navigation intent
- Click card action.
- Assert route/action intent emitted correctly.

---

## 5. Non-Functional Unit Checks

### UT-053-012: Accessibility smoke assertions for dashboard landmarks
- Assert primary heading exists and is unique.
- Assert card actions have accessible names.
- Assert no obvious aria-label regressions in rendered structure.

### UT-053-013: Lazy-loaded non-critical section fallback behavior
- Mock lazy section in loading state.
- Assert fallback placeholder is shown.
- Resolve lazy section and assert content replaces placeholder.

---

## 6. Test Data Strategy

- Use deterministic fixtures for appointments, activity events, and profile summary.
- Maintain separate fixtures for: full data, empty data, partial failure, stale-to-fresh update.
- Keep timestamps fixed to avoid flaky relative-time assertions.

---

## 7. Mocking Strategy

- Mock auth/session hook or context provider.
- Mock dashboard data service layer/hook with controllable responses.
- Mock viewport/breakpoint utility for mobile vs desktop assertions.
- Mock router/navigation callback rather than full router integration where possible.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-053-001 through UT-053-009 before merge.

---

## 9. Exit Criteria

- All mapped AC tests pass.
- No flaky test identified across 3 consecutive runs.
- Coverage targets met for dashboard module.
- No high-severity lint/test warning in CI for this test suite.

---

## 10. Suggested File Layout

- tests/unit/dashboard/Dashboard.test.tsx
- tests/unit/dashboard/DashboardCards.test.tsx
- tests/unit/dashboard/DashboardResponsive.test.tsx
- tests/unit/dashboard/DashboardRefresh.test.tsx
- tests/unit/dashboard/__fixtures__/dashboard.fixtures.ts

---

## 11. Execution Checklist

1. Create fixtures and mock builders.
2. Implement container/access tests (UT-053-001..002).
3. Implement core rendering tests (UT-053-003..005).
4. Implement responsive tests (UT-053-006..007).
5. Implement refresh/update tests (UT-053-008..009).
6. Implement card navigation tests (UT-053-010..011).
7. Add accessibility/lazy-load smoke tests (UT-053-012..013).
8. Run test suite and verify coverage thresholds.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-053.
- [ ] Test cases UT-053-001 through UT-053-013 implemented.
- [ ] AC traceability preserved in test names/comments.
- [ ] Coverage thresholds met.
- [ ] CI run for unit tests is green.
