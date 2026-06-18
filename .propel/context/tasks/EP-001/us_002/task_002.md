# TASK-002: Implement Interactive Appointment Calendar View

**User Story:** US-002 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_002/us_002.md`  
**Priority:** CRITICAL  
**Estimated Effort:** 3-5 dev days + QA  
**Status:** Planned  
**Created:** 2026-06-18

---

## 1. Objective

Implement an interactive appointment calendar with month/week views, slot-level interaction, provider preview, responsive behavior, timezone-safe display, and performance/accessibility compliance.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Month view with color-coded slot states | FE-1, FE-2, BE-1 |
| AC-2 | Week view toggle and hourly slots | FE-3, BE-1 |
| AC-3 | Slot click shows details and Select action | FE-4 |
| AC-4 | Provider hover preview popover | FE-5 |
| AC-5 | Prev/next month + date jump navigation | FE-6 |
| AC-6 | Mobile responsive behavior at 375/768+ | FE-7, QA-3 |
| AC-7 | Local timezone rendering with UTC offset footer | FE-8, BE-2, QA-2 |
| AC-8 | Calendar renders within 3 seconds for month view | PERF-1, FE-9, QA-4 |

---

## 3. Layered Implementation Tasks

## Frontend Tasks

### FE-1: Calendar Component Foundation
- Integrate selected calendar library (or approved custom calendar implementation).
- Default to month view on first load.
- Support rendering daily slot buckets with status color mapping:
  - available = green
  - booked/full = gray
  - preferred = blue

### FE-2: Slot State Rendering Model
- Implement slot card model with required fields:
  - appointment date/time
  - provider name
  - specialty
  - duration
  - location
- Ensure status legend is visible and understandable.

### FE-3: Week View Toggle
- Add Month/Week view switch.
- In week mode, render 7-day hourly timeline with slot start times.
- Preserve selected filters/state while toggling views.

### FE-4: Slot Interaction Panel
- On slot click, open inline detail panel (no page navigation).
- Show provider/specialty/duration/location and Select CTA.
- Ensure closing/opening panel does not reset calendar position.

### FE-5: Provider Hover Preview
- Add hover/focus popover over provider name.
- Display provider photo, credentials, and review count (if present).
- Ensure keyboard focus path can trigger equivalent preview.

### FE-6: Calendar Navigation Controls
- Implement Previous/Next month navigation.
- Implement direct date jump behavior.
- Keep controls keyboard accessible and screen-reader labeled.

### FE-7: Responsive Layout
- 375px: scrollable month grid and touch-friendly interactions.
- 768px+: standard calendar layout and clearer slot density.
- Prevent overflow and horizontal clipping of controls/cards.

### FE-8: Timezone-safe Rendering
- Read timezone from profile or browser fallback.
- Convert UTC slot times to local display times.
- Render UTC offset text in footer.

### FE-9: Rendering Performance Optimizations
- Use memoization/virtualization where needed for high slot counts.
- Avoid unnecessary rerenders when changing navigation controls.
- Lazy-load non-critical subcomponents (e.g., popovers/details).

## Backend/API Tasks

### BE-1: Calendar Data Contract
- Extend/reuse `GET /api/appointments/search` for calendar views with optional `view=calendar` and range params.
- Return normalized grouped payload for month/week rendering.
- Ensure status values are canonical and match FE color mapping.

### BE-2: Timezone-safe API Handling
- Keep persistence and transport in UTC.
- Return consistent ISO timestamps with timezone-safe serialization.
- Include metadata needed for local display transformations.

### BE-3: Query Bounds and Validation
- Validate date-window inputs for month/week ranges.
- Guard against oversized date ranges and malformed params.
- Return consistent 4xx schema on validation failures.

## Database Tasks

### DB-1: Date-range Query Optimization
- Validate indexes supporting month/week date windows.
- Ensure status/provider filters remain index-friendly.
- Verify query plan for 30+ slot/day scenarios.

### DB-2: Prefetch Readiness
- Validate API can efficiently retrieve current month + adjacent prefetch windows.
- Prevent N+1 query patterns in provider joins.

## Testing Tasks

### QA-1: Unit Tests
- View toggle state tests (month/week).
- Slot color/status mapping tests.
- Navigation state persistence tests.

### QA-2: Integration Tests
- API contract tests for month/week windows.
- Timezone conversion tests across UTC-8 through UTC+8.
- Slot detail panel data-binding verification.

### QA-3: Accessibility and Responsive Tests
- Keyboard navigation through controls and slots.
- Screen-reader label checks for calendar controls/slots.
- Breakpoint verification at 375/768/1024+.

### QA-4: Performance Verification
- Measure first interactive load for calendar page (<3 seconds target under 4G simulation).
- Render stress test with dense month dataset (30+ slots).
- Validate no major layout shifts during navigation.

---

## 4. Dependencies

- US-001 search endpoint and filter behavior available for calendar data retrieval.
- Appointment/provider schema and seed data available.
- Design decisions finalized for selected calendar library and slot legend semantics.

---

## 5. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Calendar library increases bundle size too much | Slower initial load | Lazy-load calendar route/components and review library footprint early |
| Incorrect timezone conversion | Wrong appointment times displayed | Store/transmit UTC only, convert at display layer, add UTC-range tests |
| Dense month view performs poorly on low-end mobile | Laggy interaction | Virtualize slot rendering and memoize expensive computations |
| Hover-only preview inaccessible on touch/keyboard | Usability/accessibility gap | Add focus/tap equivalent interaction path for provider preview |

---

## 6. Definition of Done

- [ ] Month view with slot color coding implemented.
- [ ] Week view toggle and hourly rendering implemented.
- [ ] Slot detail panel and Select CTA implemented.
- [ ] Provider preview (hover/focus/tap equivalent) implemented.
- [ ] Calendar navigation controls fully keyboard accessible.
- [ ] Responsive behavior validated at required breakpoints.
- [ ] Timezone conversion and UTC offset footer validated.
- [ ] Calendar load/render performance target met (<3 seconds).
- [ ] Unit/integration/accessibility/performance tests passing.
- [ ] Story AC-1 through AC-8 mapped and validated.

---

## 7. Suggested Execution Order

1. BE-1, BE-3
2. DB-1, DB-2
3. FE-1, FE-2, FE-3
4. FE-4, FE-5, FE-6
5. FE-7, FE-8, FE-9
6. QA-1 through QA-4
7. Final AC validation and sign-off
