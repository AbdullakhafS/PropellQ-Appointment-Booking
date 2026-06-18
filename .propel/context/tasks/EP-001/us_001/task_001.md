# TASK-001: Implement Appointment Search Filters and Results

**User Story:** US-001 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_001/us_001.md`  
**Priority:** CRITICAL  
**Estimated Effort:** 3-4 dev days + QA  
**Status:** Planned  
**Created:** 2026-06-18

---

## 1. Objective

Implement a patient-facing appointment search experience with cumulative filters (date, time, provider, specialty), real-time slot retrieval, pagination/sorting, and accessibility-compliant responsive UI.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Four filter categories displayed | FE-1, FE-2 |
| AC-2 | Real-time availability with <2s latency | BE-1, DB-1, PERF-1 |
| AC-3 | Rich search results with action CTA | FE-3, BE-2 |
| AC-4 | Cumulative filters with live updates | FE-4, BE-2 |
| AC-5 | Helpful no-results fallback | FE-5 |
| AC-6 | Mobile-responsive layout | FE-6 |
| AC-7 | Accessibility compliance (WCAG 2.1 AA) | FE-7, QA-3 |

---

## 3. Layered Implementation Tasks

## Frontend Tasks

### FE-1: Build Search Filter Bar
- Implement filter inputs for:
  - Date range (from/to)
  - Time range (morning/afternoon/evening)
  - Provider autocomplete
  - Specialty dropdown
- Ensure labels and helper text are explicitly bound to inputs.
- Add client-side state model for filter object.

### FE-2: Add Provider Autocomplete UX
- Debounced provider lookup (300 ms).
- Keyboard navigation for suggestions.
- Empty/error states for failed provider query.

### FE-3: Build Search Results Grid
- Render cards with provider name, specialty, date/time, location, and Book Now CTA.
- Add pagination controls (10 per page).
- Add sorting selector (date asc, provider A-Z).

### FE-4: Implement Cumulative Filtering Behavior
- Trigger search refresh on filter changes without full reload.
- Keep all active filters applied in every query.
- Preserve filter state when paging/sorting.

### FE-5: No-Results UX
- Show user-friendly empty state with actionable suggestions.
- Include quick action links to clear filters or expand date range.

### FE-6: Responsive UI
- Validate at 375px, 768px, 1024px+ breakpoints.
- Ensure controls remain usable without horizontal scrolling.

### FE-7: Accessibility Compliance
- Validate semantic input structure and tab order.
- Add ARIA labels/roles only where native semantics are insufficient.
- Ensure focus visibility and keyboard-only operation for all controls.

## Backend/API Tasks

### BE-1: Implement Search Endpoint
- Add `GET /api/appointments/search` with query params:
  - `dateFrom`, `dateTo`, `timeWindow`, `provider`, `specialty`, `page`, `pageSize`, `sort`
- Validate and normalize incoming query parameters.
- Return deterministic JSON contract with total count and paginated results.

### BE-2: Add Filter Composition Logic
- Apply filters cumulatively in service layer.
- Include only available slots.
- Include provider/specialty/location projection required by FE.

### BE-3: Error Handling and Observability
- Return consistent 4xx for invalid filters.
- Add structured logs for query timing, filter usage, and result count.

## Database Tasks

### DB-1: Optimize Search Query Path
- Verify indexes for slot availability and search dimensions:
  - appointment date/time
  - status (available)
  - provider id
  - specialty id
- Verify query plan under expected load.

### DB-2: Pagination and Sorting Correctness
- Enforce stable ordering for pagination.
- Add tie-break order to avoid paging drift.

## Testing Tasks

### QA-1: Unit Tests
- Filter-to-query mapping tests.
- Cumulative filter behavior tests.
- Pagination/sorting edge cases.

### QA-2: Integration Tests
- API tests for all filter combinations.
- Verify response schema and pagination metadata.

### QA-3: Accessibility and Responsive Tests
- Keyboard-only flow test.
- Screen-reader label checks.
- Breakpoint checks at 375/768/1024+.

### QA-4: Performance Verification
- API p95 latency check on representative dataset.
- Validate search interaction under concurrent requests.

---

## 4. Dependencies

- EP-005 authentication and RBAC available for patient access.
- Appointment/provider/specialty seed data is present.
- Shared API response envelope conventions are finalized.

---

## 5. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Slow search queries under load | Misses UX latency target | Add/adjust indexes; inspect query plan; add caching if needed |
| Filter mismatch between FE and API enums | Incorrect results or errors | Shared enum contract; validation tests in CI |
| Accessibility regressions | Compliance and usability issues | Add automated a11y checks + manual keyboard/screen-reader pass |

---

## 6. Definition of Done

- [ ] FE filter bar, results grid, no-results state implemented.
- [ ] Search API with cumulative filtering and pagination implemented.
- [ ] Query performance validated and indexed.
- [ ] Unit + integration + accessibility tests added and passing.
- [ ] Responsive behavior verified at required breakpoints.
- [ ] Logging added for search observability.
- [ ] Story AC-1 through AC-7 mapped and validated.

---

## 7. Suggested Execution Order

1. BE-1, BE-2
2. DB-1, DB-2
3. FE-1 through FE-5
4. FE-6, FE-7
5. QA-1 through QA-4
6. Final AC validation and sign-off
