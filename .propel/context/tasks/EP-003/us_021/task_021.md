# TASK-021: Implement Structured Data Extraction from PDF/DOCX

**User Story:** US-021 (EP-003)
**Source File:** `.propel/context/tasks/EP-003/us_021/us_021.md`
**Priority:** CRITICAL
**Estimated Effort:** 4-5 dev days
**Status:** Completed
**Created:** 2026-06-18

---

## 1. Objective

Extract structured clinical entities (medications, allergies, diagnoses, dates) from processed PDF and DOCX documents, attaching confidence scores and source references to each element for downstream profile aggregation.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Structured fields extracted and stored from processed documents | BE-1, INT-1, DB-1, QA-1 |
| AC-2 | Each extracted element includes a confidence score | BE-2, DB-2, QA-2 |
| AC-3 | Extraction errors flagged for review with failure reason recorded | BE-3, DB-3, QA-3 |
| AC-4 | Extraction source and timestamps preserved | BE-2, DB-2, QA-2 |

---

## 3. Layered Implementation Tasks

## Backend Tasks

### BE-1: Extraction Worker
- Invoke AI/NLP extraction service or rules engine on document text.
- Normalize returned entities (medications, allergies, diagnoses, dates) to internal schema.

### BE-2: Confidence and Provenance Recording
- Attach confidence score, source document reference, extraction timestamp to each entity.

### BE-3: Error Handling
- Mark document as `review_required` on extraction failure.
- Log failure reason and partial results (if any) for triage.

## Integration Tasks

### INT-1: Extraction Service Adapter
- Implement adapter for AI/NLP or rule-based extraction API.
- Handle service unavailability with graceful fallback and retry.

## Database Tasks

### DB-1: Extracted Entity Storage
- Store normalized extracted entities (type, value, unit, date context).
- Link entities to source document and patient ID.

### DB-2: Confidence and Source Metadata
- Persist confidence score, extraction model/version, and source text reference per entity.

### DB-3: Review Flag Storage
- Add review_required flag and failure_reason to document processing record.

## Testing Tasks

### QA-1: Extraction Functional Tests
- Validate entities are extracted and normalized for valid PDF and DOCX inputs.

### QA-2: Confidence Score Tests
- Validate confidence scores are present and within expected range.

### QA-3: Failure Handling Tests
- Validate review flag and reason captured on extraction failure.
- Validate extraction service unavailability is handled gracefully.

---

## 4. Dependencies

- Document processing pipeline from US-020.
- AI/NLP extraction service or rule-based engine.

---

## 5. Definition of Done

- [x] Extraction worker and service adapter implemented.
- [x] Confidence scores and provenance stored per entity.
- [x] Review flag and failure logging implemented.
- [x] AC-1 through AC-4 validated.

---

## 6. Suggested Execution Order

1. DB-1, DB-2, DB-3
2. INT-1, BE-1, BE-2, BE-3
3. QA-1 through QA-3
