# TASK-022: Build 360° Patient Profile UI

**User Story:** US-022 (EP-003)
**Source File:** `.propel/context/tasks/EP-003/us_022/us_022.md`
**Priority:** HIGH
**Estimated Effort:** 3-4 dev days
**Status:** Completed
**Created:** 2026-06-18

---

## 1. Objective

Implement a tabbed patient profile UI presenting intake summary, medications, allergies, and diagnoses in clearly labeled tabs with source attribution, responsive layout, and role-gated PHI display.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Profile displays Overview, Medications, Allergies, and Diagnoses tabs | FE-1, FE-2, QA-1 |
| AC-2 | Each tab shows data with labels and source attribution | FE-3, QA-2 |
| AC-3 | Layout is responsive across desktop and tablet | FE-4, QA-3 |
| AC-4 | Selecting a data element shows source document/intake details | FE-5, BE-1, QA-2 |

---

## 3. Layered Implementation Tasks

## Frontend Tasks

### FE-1: Tabbed Profile Shell
- Implement patient profile page with accessible tab navigation.
- Lazy-load tab content panels to avoid heavy initial render.

### FE-2: Overview Tab
- Display intake summary, demographics, and key clinical indicators.

### FE-3: Medications, Allergies, Diagnoses Tabs
- Display extracted or intake-sourced data with source label badges.

### FE-4: Responsive Layout
- Ensure profile layout adapts across desktop and tablet (768px+).

### FE-5: Source Detail Drill-Down
- On item selection, show source document name, type, and confidence metadata.

## Backend Tasks

### BE-1: Profile API
- Expose aggregated profile endpoint with tabbed data groupings.
- Apply role-based authorization to PHI fields.

## Security Tasks

### SEC-1: Role-Gated PHI Access
- Restrict profile data to authorized clinical staff roles.
- Validate authorization on each API call.

## Testing Tasks

### QA-1: Tab Functional Tests
- Validate all four tabs render correctly with sample data.

### QA-2: Source Attribution Tests
- Validate source labels and drill-down data are accurate.

### QA-3: Responsive Tests
- Validate layout across desktop and tablet breakpoints.

---

## 4. Dependencies

- Aggregated profile data from US-019.
- Extracted clinical data from US-021.

---

## 5. Definition of Done

- [x] Tabbed profile UI with four tabs implemented.
- [x] Source attribution and drill-down functioning.
- [x] Role-based PHI access enforced.
- [x] Responsive behavior validated.
- [x] AC-1 through AC-4 validated.

---

## 6. Suggested Execution Order

1. BE-1, SEC-1
2. FE-1, FE-2, FE-3, FE-4, FE-5
3. QA-1 through QA-3
