# TASK-056: Display Personal Health Profile

**User Story:** US-056 (EP-006)
**Source File:** `.propel/context/tasks/EP-006/us_056/us_056.md`
**Priority:** HIGH
**Status:** Planned
**Created:** 2026-06-19

## Objective
Show patient-friendly health profile sections for medications, allergies, diagnoses, and active alerts with a clear correction-report path.

## AC Mapping
- AC-1: FE-1, BE-1, QA-1
- AC-2: FE-2, QA-2
- AC-3: FE-3, QA-1
- AC-4: FE-4, BE-2, QA-3

## Tasks
### FE-1: Health Profile Sections
- Render medications, allergies, diagnoses, and chronic conditions.

### FE-2: Correction Reporting CTA
- Provide path to report profile discrepancies.

### FE-3: Patient-Friendly Terminology
- Replace jargon where possible and add labels/tooltips.

### FE-4: Live Data Refresh
- Refresh profile state after source updates.

### BE-1: Profile Read API
- Return structured profile payload for patient view.

### BE-2: Refresh/Version Metadata
- Return profile version/timestamp for update checks.

### QA-1: Display Tests
- Validate profile sections and readability.

### QA-2: Correction Flow Tests
- Validate support/report action availability.

### QA-3: Update Propagation Tests
- Validate profile updates after source changes.

## Definition of Done
- [ ] Profile sections rendered accurately.
- [ ] Correction path available.
- [ ] Update behavior validated.
- [ ] AC-1 through AC-4 validated.
