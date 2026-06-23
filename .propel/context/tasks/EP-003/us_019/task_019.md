# TASK-019: Implement Patient Data Aggregation into Unified Profile

**User Story:** US-019 (EP-003)
**Source File:** `.propel/context/tasks/EP-003/us_019/us_019.md`
**Priority:** CRITICAL
**Estimated Effort:** 3-4 dev days
**Status:** Completed
**Created:** 2026-06-18

---

## 1. Objective

Aggregate patient intake form responses and document-extracted clinical data into a single normalized profile record, preserving source provenance and making all data available for profile display and downstream clinical workflows.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Intake and document data aggregated into unified profile | BE-1, BE-2, DB-1, QA-1 |
| AC-2 | Source metadata available for each element | BE-3, DB-2, QA-2 |
| AC-3 | Profile includes intake answers, medications, allergies, key extracted fields | BE-2, FE-1, QA-1 |
| AC-4 | Data provenance preserved on profile update | BE-3, DB-2, QA-2 |

---

## 3. Layered Implementation Tasks

## Backend Tasks

### BE-1: Aggregation Pipeline Trigger
- Trigger profile re-aggregation when intake is submitted or document processing completes.
- Support idempotent re-runs without data duplication.

### BE-2: Normalized Profile Builder
- Merge intake form responses and document-extracted entities into a single patient profile record.
- Resolve deduplication by source priority order (intake > document extraction).

### BE-3: Source Provenance Recording
- Tag each aggregated element with source type (`intake` / `document`), source ID, and aggregated timestamp.

## Database Tasks

### DB-1: Unified Profile Schema
- Design/validate normalized tables for profile elements (medications, allergies, diagnoses, intake fields).
- Add patient profile version/updated_at tracking.

### DB-2: Provenance Columns
- Store `source_type`, `source_id`, `extracted_at`, and `confidence_score` alongside each element.

## Frontend Tasks

### FE-1: Profile Data API
- Expose a profile endpoint consumed by profile UI (US-022).

## Testing Tasks

### QA-1: Aggregation Functional Tests
- Verify profile completeness when both intake and document data are present.
- Verify deduplication behavior across data sources.

### QA-2: Provenance Tests
- Verify source metadata persists through aggregation.
- Verify profile update preserves provenance history.

---

## 4. Dependencies

- Intake data from EP-002.
- Document extraction output from US-020/US-021.

---

## 5. Definition of Done

- [x] Aggregation pipeline and normalized profile schema implemented.
- [x] Source provenance preserved for all elements.
- [x] Profile data exposed for UI consumption.
- [x] AC-1 through AC-4 validated.

---

## 6. Suggested Execution Order

1. DB-1, DB-2
2. BE-1, BE-2, BE-3
3. FE-1
4. QA-1, QA-2
