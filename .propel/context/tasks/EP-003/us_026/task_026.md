# TASK-026: Implement ICD-10 Code Suggestion Engine

**User Story:** US-026 (EP-003)
**Source File:** `.propel/context/tasks/EP-003/us_026/us_026.md`
**Priority:** CRITICAL
**Estimated Effort:** 4-5 dev days
**Status:** Planned
**Created:** 2026-06-18

---

## 1. Objective

Build an ICD-10 code suggestion engine that uses aggregated patient data and extracted clinical text to propose relevant codes with confidence scores, and routes low-confidence suggestions to a manual review queue.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | System suggests relevant ICD-10 codes from clinical data | BE-1, INT-1, QA-1 |
| AC-2 | Each suggestion includes a confidence score | BE-2, DB-1, QA-2 |
| AC-3 | Low-confidence suggestions flagged for manual review | BE-3, DB-2, QA-2 |
| AC-4 | Suggestions stored for clinician or coder review | DB-1, BE-2, QA-1 |

---

## 3. Layered Implementation Tasks

## Backend Tasks

### BE-1: Suggestion Generation
- Invoke AI model or coding rules engine with normalized clinical terms.
- Return top-N ICD-10 code suggestions per patient encounter.

### BE-2: Confidence Scoring and Storage
- Attach confidence score from model output to each suggestion.
- Persist suggestions with encounter/patient reference, code, description, and confidence.

### BE-3: Review Flag Logic
- Apply configurable confidence threshold (default 70%).
- Tag suggestions below threshold with `review_required = true`.

## Integration Tasks

### INT-1: ICD-10 Engine Adapter
- Integrate AI model or external coding rules service.
- Handle inference errors and timeouts gracefully.

## Database Tasks

### DB-1: Code Suggestion Table
- Store suggestion rows with code, description, confidence, review flag, and status.

### DB-2: Review Queue Index
- Index review_required and status fields for queue queries.

## Testing Tasks

### QA-1: Suggestion Functional Tests
- Validate codes are generated for known clinical inputs.
- Validate persistence and retrieval.

### QA-2: Confidence and Threshold Tests
- Validate correct review flag applied based on threshold.
- Validate confidence scores fall within expected range.

---

## 4. Dependencies

- Aggregated patient profile from US-019.
- Clinical text extraction from US-021.

---

## 5. Definition of Done

- [ ] ICD-10 suggestion engine implemented and integrated.
- [ ] Confidence scoring and review flagging active.
- [ ] Suggestions persisted and accessible for review.
- [ ] AC-1 through AC-4 validated.

---

## 6. Suggested Execution Order

1. DB-1, DB-2
2. INT-1, BE-1, BE-2, BE-3
3. QA-1, QA-2
