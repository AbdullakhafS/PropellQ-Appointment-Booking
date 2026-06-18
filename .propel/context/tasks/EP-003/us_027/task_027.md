# TASK-027: Implement CPT Code Suggestion Engine

**User Story:** US-027 (EP-003)
**Source File:** `.propel/context/tasks/EP-003/us_027/us_027.md`
**Priority:** CRITICAL
**Estimated Effort:** 4-5 dev days
**Status:** Planned
**Created:** 2026-06-18

---

## 1. Objective

Build a CPT code suggestion engine that derives procedural codes from clinical notes and encounter context, attaches confidence scores, flags low-confidence items for coder review, and stores suggestions for approval workflows.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | System suggests CPT codes from clinical procedure data | BE-1, INT-1, QA-1 |
| AC-2 | Each suggestion includes confidence scores | BE-2, DB-1, QA-2 |
| AC-3 | Low-confidence suggestions flagged for manual review | BE-3, DB-2, QA-2 |
| AC-4 | Suggestions available for approval or editing | DB-1, QA-1 |

---

## 3. Layered Implementation Tasks

## Backend Tasks

### BE-1: CPT Suggestion Generation
- Invoke ML/NLP model or coding rules engine with procedure descriptions and clinical context.
- Return ranked CPT code suggestions per encounter.

### BE-2: Confidence Scoring
- Attach model-provided confidence scores to each suggestion.
- Persist evidence source (text excerpt or rule reference) supporting each suggestion.

### BE-3: Review Flag Logic
- Apply configurable confidence threshold to route low-confidence suggestions to review queue.

## Integration Tasks

### INT-1: CPT Engine Adapter
- Integrate chosen ML model or coding rules service.
- Handle errors, timeouts, and partial results gracefully.

## Database Tasks

### DB-1: CPT Suggestion Table
- Store suggestion rows with code, description, confidence, evidence, review flag, and approval status.

### DB-2: Review Queue Index
- Index review_required and approval_status for efficient queue retrieval.

## Testing Tasks

### QA-1: Suggestion Generation Tests
- Validate CPT codes generated for known procedure descriptions.

### QA-2: Confidence and Threshold Tests
- Validate threshold-based review flag assignment.
- Validate stored evidence references are accurate.

---

## 4. Dependencies

- Clinical data extraction from US-021.
- Patient profile and procedure metadata.

---

## 5. Definition of Done

- [ ] CPT suggestion engine implemented and integrated.
- [ ] Confidence scoring and review flagging active.
- [ ] Suggestions persisted with evidence for review.
- [ ] AC-1 through AC-4 validated.

---

## 6. Suggested Execution Order

1. DB-1, DB-2
2. INT-1, BE-1, BE-2, BE-3
3. QA-1, QA-2
