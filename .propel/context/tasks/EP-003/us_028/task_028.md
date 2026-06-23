# TASK-028: Build Code Verification UI (Accept/Reject/Override)

**User Story:** US-028 (EP-003)
**Source File:** `.propel/context/tasks/EP-003/us_028/us_028.md`
**Priority:** HIGH
**Estimated Effort:** 3-4 dev days
**Status:** Completed
**Created:** 2026-06-18

---

## 1. Objective

Build a code review UI that displays AI-suggested ICD-10 and CPT codes with confidence and evidence, and allows reviewers to accept, reject, or override each suggestion with full audit logging of every decision.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Reviewer can accept, reject, or override each suggestion | FE-1, BE-1, QA-1 |
| AC-2 | UI shows confidence score and source evidence | FE-2, QA-2 |
| AC-3 | Override is recorded and audit-logged | BE-2, DB-1, QA-3 |
| AC-4 | Rejected suggestions retained for audit and feedback | DB-1, QA-3 |

---

## 3. Layered Implementation Tasks

## Frontend Tasks

### FE-1: Code Review Queue UI
- List pending suggestions (ICD-10 and CPT) with confidence badge.
- Provide action buttons: Accept, Reject, Override with confirmation for override.

### FE-2: Evidence Panel
- Show supporting text excerpt or rule reference alongside each suggestion.
- Link to source document or extraction detail.

### FE-3: Override Input
- Provide code search/entry field for manual override.
- Validate override code against allowed code list.

## Backend Tasks

### BE-1: Review Action Endpoint
- Implement `POST /api/codes/{id}/review` accepting action and optional override code.
- Update suggestion status and record reviewer identity.

### BE-2: Audit Logging
- Log every accept/reject/override action with reviewer ID, timestamp, and decision metadata.

## Database Tasks

### DB-1: Review Decision Storage
- Add status, reviewer_id, reviewed_at, override_code, and rejection_reason fields to suggestion records.
- Retain rejected suggestions for audit (no hard delete).

## Testing Tasks

### QA-1: Action Functional Tests
- Validate accept/reject/override flows update suggestion status correctly.

### QA-2: Evidence Display Tests
- Validate confidence and source evidence display correctly for each suggestion.

### QA-3: Audit Tests
- Validate all review actions produce correct audit log entries.
- Validate rejected suggestions are retained and queryable.

---

## 4. Dependencies

- ICD-10 suggestions from US-026.
- CPT suggestions from US-027.
- Audit logging framework from EP-007.

---

## 5. Definition of Done

- [x] Code review UI with accept/reject/override implemented.
- [x] Audit log captures all decisions with metadata.
- [x] Rejected items retained.
- [x] AC-1 through AC-4 validated.

---

## 6. Suggested Execution Order

1. DB-1
2. BE-1, BE-2
3. FE-1, FE-2, FE-3
4. QA-1 through QA-3
