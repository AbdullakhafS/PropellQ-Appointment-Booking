# UNIT-TEST-PLAN-010: Mobile-Responsive Booking Experience

User Story: US-010 (EP-001)
Source File: .propel/context/tasks/EP-001/us_010/us_010.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for responsive booking UI behavior to validate breakpoint-driven layout logic, touch-friendly interaction constraints, accessibility-safe mobile forms, and image/performance-related presentation guards.

---

## 2. Scope and Assumptions

### In Scope
- Breakpoint-based layout mode selection (mobile/tablet/desktop).
- Conditional rendering for search, calendar, and checkout components per breakpoint.
- Touch-target sizing constraints represented by component props/classes.
- Accessibility form/input semantics and error association logic.
- Image metadata constraints and lazy-loading flags in UI model.

### Out of Scope
- Real Lighthouse performance score collection.
- Browser/device-specific touch hardware behavior.
- End-to-end swipe gesture physics fidelity.

### Assumptions
- Responsive behavior implemented through breakpoint hook/util and conditional component variants.
- Component-level tests can assert class/prop/state contracts for responsive tokens.
- Image optimizer metadata is exposed through helper/util functions.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Mobile (375px) layout rules | UT-010-001, UT-010-002, UT-010-003 |
| AC-2 | Tablet (768px) layout rules | UT-010-004 |
| AC-3 | Desktop (1024px+) layout rules | UT-010-005 |
| AC-4 | Performance-oriented UI guards (FCP/LCP/CLS intent proxies) | UT-010-006 |
| AC-5 | Touch interaction constraints and non-hover fallback | UT-010-007, UT-010-008 |
| AC-6 | Mobile accessibility requirements | UT-010-009, UT-010-010 |
| AC-7 | Image optimization metadata behavior | UT-010-011 |
| AC-8 | Mobile form optimization rules | UT-010-012, UT-010-013 |

---

## 4. Unit Test Areas

## A. Breakpoint Layout Behavior

### UT-010-001: Mobile breakpoint applies stacked filter and single-column checkout variants
- Mock 375px viewport.
- Assert stacked filter layout and single-column checkout markers.

### UT-010-002: Mobile primary CTA uses full-width touch-friendly style contract
- Assert Book Now button style props/classes indicate full width and minimum height constraints.

### UT-010-003: Mobile calendar variant renders scrollable month/week mode selectors
- Assert mobile calendar mode controls and scrollable container markers.

### UT-010-004: Tablet breakpoint applies two-column or sidebar layout variants
- Mock 768px viewport.
- Assert tablet-specific layout mode and navigation variant.

### UT-010-005: Desktop breakpoint applies sidebar/month/details panel variants
- Mock 1024px+ viewport.
- Assert desktop layout mode, sticky filters, and detail panel markers.

## B. Performance-Intent and Touch Behavior

### UT-010-006: Responsive component avoids layout thrash during data update transitions
- Trigger data update/rerender sequence.
- Assert stable key structure and no duplicate-mount warning paths.

### UT-010-007: Touch target helper enforces minimum target size contract
- Validate computed size constraints for interactive controls.

### UT-010-008: Hover-dependent interactions provide touch fallback handlers
- Assert components expose click/tap alternatives for hover-only affordances.

## C. Accessibility and Form Optimization

### UT-010-009: Mobile form inputs enforce accessible label and error association contracts
- Assert labels and aria-describedby/error ids for validation messages.

### UT-010-010: Text scale and contrast token usage references compliant design tokens
- Assert typography and color token selectors map to accessibility-compliant token set.

### UT-010-011: Image metadata helper applies compression/responsive/lazy flags
- Assert provider image model includes max-size constraints and lazy-load hints.

### UT-010-012: Native input types and autocomplete attributes are applied
- Assert input fields use email/tel/date types and autocomplete attributes.

### UT-010-013: Sticky-submit visibility logic remains active in mobile form mode
- Mock long-form content at mobile breakpoint.
- Assert submit action model remains reachable via sticky footer logic.

---

## 5. Test Data Strategy

- Viewport fixtures for 375px, 768px, and 1024px+.
- UI fixtures for booking/search/calendar in multiple data states.
- Token fixtures for accessibility typography/color mappings.

---

## 6. Mocking Strategy

- Mock breakpoint hook/util and gesture capability flags.
- Mock image metadata helper and form-field schema provider.
- Mock navigation/panel state callbacks.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-010-001 through UT-010-010 before merge.

---

## 8. Exit Criteria

- AC-mapped responsive behavior tests pass.
- Touch and accessibility contracts validated.
- Form and image optimization logic covered.
- Coverage targets achieved.

---

## 9. Suggested File Layout

- tests/unit/responsive/BookingResponsiveLayout.test.tsx
- tests/unit/responsive/BookingTouchAccessibility.test.tsx
- tests/unit/responsive/BookingFormOptimization.test.tsx
- tests/unit/responsive/__fixtures__/responsiveBooking.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-010.
- [ ] Test cases UT-010-001 through UT-010-013 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
