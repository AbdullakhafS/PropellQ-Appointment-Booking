# TASK-023: Implement Document Source Traceability UI

**User Story:** US-023 (EP-003)
**Source File:** `.propel/context/tasks/EP-003/us_023/us_023.md`
**Priority:** HIGH
**Estimated Effort:** 2-3 dev days
**Status:** Planned
**Created:** 2026-06-18

---

## 1. Objective

Surface document-level provenance metadata on profile data items, allow users to securely preview or access source documents, and display intake source details where applicable.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Each extracted item links to its source document or intake entry | FE-1, BE-1, QA-1 |
| AC-2 | Source metadata shows name, type, and extraction confidence | FE-2, QA-1 |
| AC-3 | Source link opens secure preview or access to document | FE-3, BE-2, SEC-1, QA-2 |
| AC-4 | Intake-sourced items show intake entry and timestamp | FE-2, QA-1 |

---

## 3. Layered Implementation Tasks

## Frontend Tasks

### FE-1: Source Badge on Profile Items
- Add source indicator chip/badge on each data element in profile tabs.

### FE-2: Source Metadata Tooltip/Panel
- Show document name, source type, confidence, and timestamp in a detail panel.

### FE-3: Document Preview Action
- Provide link/button to securely open or preview source document.
- Differentiate intake vs document source display.

## Backend Tasks

### BE-1: Source Reference API
- Return source metadata with each profile element in the profile API.

### BE-2: Secure Document Access
- Generate signed, time-limited access URL for source document preview.
- Validate authorization before issuing URL.

## Security Tasks

### SEC-1: Access Control on Preview
- Enforce per-request authorization for document access.
- Prevent PHI leakage through unauthenticated document URLs.

## Testing Tasks

### QA-1: Source Display Tests
- Validate metadata display for document and intake sourced items.

### QA-2: Secure Access Tests
- Validate signed URL behavior and expired URL rejection.
- Validate unauthorized access is blocked.

---

## 4. Dependencies

- Profile API from US-022.
- Document storage and metadata from US-020.

---

## 5. Definition of Done

- [ ] Source metadata displayed on profile data items.
- [ ] Secure preview access implemented.
- [ ] Authorization enforced for document access.
- [ ] AC-1 through AC-4 validated.

---

## 6. Suggested Execution Order

1. BE-1, BE-2, SEC-1
2. FE-1, FE-2, FE-3
3. QA-1, QA-2
