# TASK-025: Implement Allergy-Drug Interaction Check

**User Story:** US-025 (EP-003)
**Source File:** `.propel/context/tasks/EP-003/us_025/us_025.md`
**Priority:** CRITICAL
**Estimated Effort:** 3-4 dev days
**Status:** Completed
**Created:** 2026-06-18

---

## 1. Objective

Cross-reference extracted patient allergies against current medications, surface any interaction risks with severity in the patient profile, and ensure the check degrades gracefully when the underlying service is unavailable.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | System identifies allergy-drug interactions from medication + allergy data | BE-1, INT-1, QA-1 |
| AC-2 | Conflicts displayed with severity and allergy details | FE-1, DB-1, QA-2 |
| AC-3 | Service unavailability handled gracefully without blocking access | BE-2, QA-3 |
| AC-4 | Viewer sees source allergy and medication details per conflict | FE-1, QA-2 |

---

## 3. Layered Implementation Tasks

## Backend Tasks

### BE-1: Allergy-Drug Interaction Check
- Normalize allergy and medication terminology to a common vocabulary.
- Query allergy interaction service or database with normalized pairs.
- Map returned interactions to internal severity model.

### BE-2: Graceful Failure
- Return non-blocking degraded profile state if service unavailable.
- Log failure for ops review without exposing error to patient-facing UI.

## Integration Tasks

### INT-1: Allergy Interaction Service Adapter
- Integrate chosen allergy interaction database or API.
- Handle rate limits and timeouts safely.

## Database Tasks

### DB-1: Allergy-Drug Conflict Storage
- Store detected conflicts with severity, involved allergy, involved medication, and source.

## Frontend Tasks

### FE-1: Allergy Conflict Display
- Show conflicts in the allergies/medications tab with severity badge.
- Display source allergy and medication detail on conflict expansion.

## Testing Tasks

### QA-1: Detection Tests
- Validate known allergy-drug conflict pairs are flagged.
- Validate correct severity mapping.

### QA-2: Display Tests
- Validate conflict cards show severity and source details correctly.

### QA-3: Failure Tests
- Validate profile accessible and displays safe message when service unavailable.

---

## 4. Dependencies

- Extracted allergy and medication data from US-021.
- Allergy interaction data source.

---

## 5. Definition of Done

- [x] Allergy-drug interaction check implemented with service adapter.
- [x] Conflicts displayed in profile with severity and source details.
- [x] Graceful failure behavior validated.
- [x] AC-1 through AC-4 validated.

---

## 6. Suggested Execution Order

1. INT-1, DB-1
2. BE-1, BE-2
3. FE-1
4. QA-1 through QA-3
