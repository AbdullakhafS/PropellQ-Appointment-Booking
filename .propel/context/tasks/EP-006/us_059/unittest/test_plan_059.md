# UNIT-TEST-PLAN-059: Patient Dashboard Mobile Responsiveness

User Story: US-059 (EP-006)
Source File: .propel/context/tasks/EP-006/us_059/us_059.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for mobile-responsive patient dashboard behavior, including breakpoint adaptation, card stacking without overflow, touch-friendly targets, and mobile-friendly loading behavior.

---

## 2. Scope and Assumptions

### In Scope
- Responsive layout behavior at 375px, 768px, and 1024px breakpoints.
- Vertical card stacking and overflow prevention for small screens.
- Touch target and spacing rules for interactive controls.
- Unit-level performance-related behavior (lazy section rendering and deferred content triggers).

### Out of Scope
- End-to-end real-device browser performance benchmarking.
- Native app behavior and offline support.
- Full network-layer optimization verification.

### Assumptions
- Dashboard uses component-level responsive utilities or CSS-in-JS classes that can be asserted in tests.
- Card layout and navigation controls are rendered through reusable dashboard components.
- Unit tests run with Jest/Vitest and Testing Library.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Dashboard layout adapts on phone and remains usable | UT-059-001, UT-059-002, UT-059-003 |
| AC-2 | Multiple cards stack vertically without overflow | UT-059-004, UT-059-005 |
| AC-3 | Buttons and links are large enough for touch input | UT-059-006, UT-059-007 |
| AC-4 | Dashboard performs acceptably on mobile network conditions | UT-059-008, UT-059-009 |

---

## 4. Unit Test Areas

## A. Breakpoint Adaptation and Usability

### UT-059-001: Layout applies phone breakpoint rules at 375px
- Render dashboard at 375px viewport mock.
- Assert mobile layout classes/variants are selected.
- Assert essential modules remain visible and navigable.

### UT-059-002: Tablet breakpoint behavior applies at 768px
- Render at 768px viewport mock.
- Assert intermediate responsive arrangement rules are applied.
- Assert no mobile-only collapse logic incorrectly persists.

### UT-059-003: Desktop breakpoint behavior restores wider layout at 1024px+
- Render at 1024px viewport mock.
- Assert desktop layout variants are used.
- Assert mobile compact controls are replaced with standard layout controls.

## B. Card Stacking and Overflow Prevention

### UT-059-004: Multiple dashboard cards stack vertically on mobile
- Provide fixture with multiple card widgets.
- Assert card ordering is vertical for small viewport.
- Assert each card remains fully rendered and reachable.

### UT-059-005: Horizontal overflow is prevented for card content and containers
- Render cards with long text/metadata edge fixtures.
- Assert overflow-safe classes/props are applied.
- Assert no horizontal scroll container is introduced by layout logic.

## C. Touch Target and Interaction Sizing

### UT-059-006: Interactive controls meet minimum touch target sizing rules
- Render buttons/links in mobile mode.
- Assert control sizing classes/props meet expected touch thresholds.

### UT-059-007: Spacing between adjacent touch controls remains tappable
- Render dense action areas in mobile viewport.
- Assert spacing utilities prevent crowded tap targets.
- Assert keyboard focus order remains logical.

## D. Mobile-Oriented Loading and Performance Behavior

### UT-059-008: Non-critical sections are deferred or lazy-rendered on mobile
- Mock mobile mode and initial render.
- Assert non-critical panels are not eagerly mounted until trigger/viewport condition.

### UT-059-009: Dashboard keeps essential content available under slow-state simulation
- Simulate delayed secondary content loading.
- Assert core summary and appointment actions render first.
- Assert loading placeholders/states appear for deferred sections.

## E. Robustness and Edge Cases

### UT-059-010: Orientation change recalculates layout without stale state
- Simulate viewport switch between portrait/landscape widths.
- Assert layout mode updates correctly and preserves dashboard state.

### UT-059-011: Dynamic card count changes do not break responsive grid logic
- Add/remove cards after initial render.
- Assert stacking and spacing remain valid without overlap.

### UT-059-012: Mobile navigation controls remain functional in collapsed mode
- Render mobile nav/collapsible sections.
- Assert toggle, expand/collapse, and linked actions work consistently.

---

## 5. Non-Functional Unit Checks

### UT-059-013: Accessibility checks for responsive and touch interactions
- Assert controls have accessible names and roles in mobile variants.
- Assert collapsed/expanded states expose correct ARIA attributes.

### UT-059-014: Deterministic rerender behavior under repeated viewport updates
- Trigger repeated viewport change events.
- Assert no duplicated nodes, stale classes, or memory-leak-prone listener patterns.

---

## 6. Test Data Strategy

- Build deterministic dashboard fixtures with varied card counts and content density.
- Include long-text fixtures to stress overflow behavior.
- Include control-dense fixtures to validate spacing and touch sizing.
- Use viewport helper utilities for 375px, 768px, 1024px scenarios.

---

## 7. Mocking Strategy

- Mock viewport/media-query hooks and resize observers.
- Mock lazy-loaded section boundaries where applicable.
- Mock secondary data fetch timing to simulate slow mobile conditions.
- Mock feature flags for mobile-specific simplification logic if present.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-059-001 through UT-059-009 before merge.

---

## 9. Exit Criteria

- All AC-mapped tests pass.
- Breakpoint adaptation, stacking, and touch-target behaviors validated.
- Mobile loading-state behavior verified for core-first rendering.
- No flaky failures across 3 consecutive runs in local or CI.

---

## 10. Suggested File Layout

- tests/unit/dashboard/DashboardResponsiveLayout.test.tsx
- tests/unit/dashboard/DashboardCardStacking.test.tsx
- tests/unit/dashboard/DashboardTouchTargets.test.tsx
- tests/unit/dashboard/DashboardMobileLoadingBehavior.test.tsx
- tests/unit/dashboard/__fixtures__/dashboardResponsive.fixtures.ts

---

## 11. Execution Checklist

1. Create viewport utilities and responsive dashboard fixtures.
2. Implement breakpoint adaptation tests (UT-059-001..003).
3. Implement stacking and overflow tests (UT-059-004..005).
4. Implement touch target and spacing tests (UT-059-006..007).
5. Implement mobile loading behavior tests (UT-059-008..009).
6. Implement orientation, dynamic-card, and collapsed-nav edge tests (UT-059-010..012).
7. Add accessibility and rerender stability checks (UT-059-013..014).
8. Run unit suite and confirm coverage thresholds.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-059.
- [ ] Test cases UT-059-001 through UT-059-014 implemented.
- [ ] Acceptance criteria traceability retained in test names/docs.
- [ ] Coverage targets achieved.
- [ ] CI unit-test gate passes reliably.
