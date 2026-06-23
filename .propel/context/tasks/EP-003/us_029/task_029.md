# TASK-029: Implement Confidence Score Thresholds

**User Story:** US-029 (EP-003)
**Source File:** `.propel/context/tasks/EP-003/us_029/us_029.md`
**Priority:** HIGH
**Estimated Effort:** 2-3 dev days
**Status:** Completed
**Created:** 2026-06-18

---

## 1. Objective

Apply configurable confidence thresholds to ICD-10 and CPT suggestions to auto-accept high-confidence outputs and route low-confidence items to a visible review queue, with threshold settings manageable by authorized users.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Suggestions above threshold are auto-accepted | BE-1, DB-1, QA-1 |
| AC-2 | Suggestions below threshold are flagged for manual review | BE-1, DB-1, QA-1 |
| AC-3 | Review queue shows low-confidence items | FE-1, QA-2 |
| AC-4 | Threshold is configurable by authorized users | BE-2, FE-2, SEC-1, QA-3 |

---

## 3. Layered Implementation Tasks

## Backend Tasks

### BE-1: Threshold Evaluation
- Apply configured threshold during suggestion persistence.
- Tag suggestions as `auto_accepted` or `review_required` at generation time.

### BE-2: Threshold Configuration API
- Implement read/write endpoint for threshold configuration.
- Record each configuration change with actor and timestamp for auditability.

## Frontend Tasks

### FE-1: Review Queue View
- Filter suggestion queue to show only `review_required` items.
- Display confidence score visually (e.g., badge or progress bar).

### FE-2: Threshold Configuration UI
- Provide threshold setting control for authorized admin/coder roles.
- Show current threshold and save history.

## Database Tasks

### DB-1: Threshold Configuration Storage
- Store configurable threshold value per code type (ICD-10 / CPT).
- Maintain configuration change history.

## Security Tasks

### SEC-1: Configuration Access Control
- Restrict threshold write access to authorized roles.
- Validate authorization on every configuration update.

## Testing Tasks

### QA-1: Auto-Accept/Flag Tests
- Validate correct routing at and around threshold boundary values.

### QA-2: Queue Tests
- Validate review queue filters and displays flagged items correctly.

### QA-3: Configuration Tests
- Validate threshold changes take effect immediately.
- Validate unauthorized users cannot modify thresholds.

---

## 4. Dependencies

- ICD-10/CPT suggestion engines from US-026/US-027.
- Code verification flow from US-028.

---

## 5. Definition of Done

- [x] Threshold evaluation and auto-accept logic implemented.
- [x] Review queue and configuration UI complete.
- [x] Authorization enforced for configuration changes.
- [x] AC-1 through AC-4 validated.

---

## 6. Suggested Execution Order

1. DB-1
2. BE-1, BE-2, SEC-1
3. FE-1, FE-2
4. QA-1 through QA-3
