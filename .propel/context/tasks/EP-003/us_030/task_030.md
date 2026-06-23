# TASK-030: Build Conflict Resolution UI (Side-by-Side Comparison)

**User Story:** US-030 (EP-003)
**Source File:** `.propel/context/tasks/EP-003/us_030/us_030.md`
**Priority:** HIGH
**Estimated Effort:** 3-4 dev days
**Status:** Completed
**Created:** 2026-06-18

---

## 1. Objective

Build a conflict resolution UI that presents conflicting clinical data items side-by-side with source provenance, enables reviewers to resolve/merge/discard with audit logging, and removes resolved items from the active conflict queue.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Both conflicting versions displayed side-by-side | FE-1, QA-1 |
| AC-2 | Source provenance and confidence metrics shown per version | FE-2, QA-2 |
| AC-3 | Resolution action persisted and audit-logged | BE-1, BE-2, DB-1, QA-3 |
| AC-4 | Resolved conflicts removed from active queue | BE-1, DB-1, QA-3 |

---

## 3. Layered Implementation Tasks

## Frontend Tasks

### FE-1: Side-by-Side Comparison Panel
- Render two-column comparison layout for conflicting data versions.
- Visually differentiate values that differ between the two versions.

### FE-2: Provenance and Confidence Display
- Show source document/intake name, type, extraction confidence, and timestamp for each side.

### FE-3: Resolution Action Controls
- Provide Resolve (pick one), Merge, and Discard actions.
- Require confirmation for irreversible decisions.

### FE-4: Active Conflict Queue
- Display list of unresolved conflicts filtered by severity.
- Refresh queue after each resolution.

## Backend Tasks

### BE-1: Resolution Action Endpoint
- Implement `POST /api/conflicts/{id}/resolve` with action and metadata.
- Update conflict status and remove from active queue on success.

### BE-2: Audit Logging
- Log every resolution action with reviewer ID, chosen action, timestamp, and source versions.

## Database Tasks

### DB-1: Conflict Resolution Storage
- Store resolution status, action taken, reviewer, and resolved_at for each conflict.
- Retain pre-resolution versions for audit (no hard delete).

## Testing Tasks

### QA-1: Comparison Display Tests
- Validate side-by-side layout and value differentiation render correctly.

### QA-2: Provenance Tests
- Validate source metadata displays correctly for each version.

### QA-3: Resolution Persistence Tests
- Validate all resolution actions update status and produce audit log entries.
- Validate resolved conflicts are removed from active queue.

---

## 4. Dependencies

- Conflict detection outputs from US-024 and US-025.
- Audit logging framework from EP-007.

---

## 5. Definition of Done

- [x] Side-by-side conflict comparison UI implemented.
- [x] Resolution actions (resolve/merge/discard) persist and log.
- [x] Active queue clears on resolution.
- [x] AC-1 through AC-4 validated.

---

## 6. Suggested Execution Order

1. DB-1
2. BE-1, BE-2
3. FE-1, FE-2, FE-3, FE-4
4. QA-1 through QA-3
