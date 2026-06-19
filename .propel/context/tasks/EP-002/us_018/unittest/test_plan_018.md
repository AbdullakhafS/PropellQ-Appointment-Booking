# UNIT-TEST-PLAN-018: Display Intake Responses in Patient Profile

User Story: US-018 (EP-002)
Source File: .propel/context/tasks/EP-002/us_018/us_018.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for patient-profile intake display logic, including latest-intake selection, section mapping, verification status indicators, edit gating, edit timestamp updates, export intents, and responsive/accessibility-safe behavior contracts.

---

## 2. Scope and Assumptions

### In Scope
- Intake tab data selection and section view-model construction.
- Latest-completed intake selection logic.
- Display models for complaint/history/medications/allergies/insurance.
- Edit eligibility rules and edit mode transitions.
- Timestamp, print/export action model generation, responsive/accessibility metadata logic.

### Out of Scope
- Full PDF rendering engine output fidelity.
- End-to-end profile routing and auth checks.
- Browser-level table scrolling behavior.

### Assumptions
- Profile intake module uses selector/service layer with deterministic outputs.
- Edit action and save updates call mockable services.
- Accessibility semantics are represented in component attributes/metadata.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Intake tab inclusion in profile navigation model | UT-018-001 |
| AC-2 | Most recent completed intake selection | UT-018-002 |
| AC-3 | Chief complaint read model | UT-018-003 |
| AC-4 | Medical history list/collapsible notes mapping | UT-018-004 |
| AC-5 | Medication table data mapping | UT-018-005 |
| AC-6 | Allergy list mapping | UT-018-006 |
| AC-7 | Insurance section + verification color mapping | UT-018-007 |
| AC-8 | Metadata fields (completed via mode version) | UT-018-008 |
| AC-9 | Edit button visibility gating by appointment status/time | UT-018-009 |
| AC-10 | Edit mode prefill and save action behavior | UT-018-010 |
| AC-11 | Last-updated timestamp refresh after edits | UT-018-011 |
| AC-12 | Print/download export action model generation | UT-018-012 |
| AC-13 | Responsive section/table mode logic | UT-018-013 |
| AC-14 | Accessibility attribute model assertions | UT-018-014 |

---

## 4. Unit Test Areas

## A. Intake Selection and Display Models

### UT-018-001: Profile nav model includes Intake tab entry
- Build profile tabs model.
- Assert intake tab presence and key metadata.

### UT-018-002: Selector returns latest completed intake record
- Provide multi-intake fixture with mixed timestamps/statuses.
- Assert latest completed intake chosen.

### UT-018-003: Chief complaint section model renders expected read-only text
- Build section model.
- Assert complaint text and editability flag behavior.

### UT-018-004: Medical history mapper builds collapsible row models with condition metadata
- Assert condition name/date/status and notes collapse metadata.

### UT-018-005: Medication mapper builds table rows with required columns
- Assert medication, dosage, frequency, route fields.

### UT-018-006: Allergy mapper builds list rows with reaction/severity fields
- Assert allergen, reaction type, severity, description mappings.

### UT-018-007: Insurance section maps verification status to semantic indicator token
- Assert verified/unverified status token mapping.

### UT-018-008: Metadata formatter outputs completed timestamp, mode label, and version
- Assert metadata string/model correctness.

## B. Edit and Export Behavior

### UT-018-009: Edit availability rule enforces appointment status/time constraints
- Test checked-in, future, and past appointment fixtures.
- Assert edit button visibility rules.

### UT-018-010: Edit mode loads prefilled intake form model and emits save action payload
- Enter edit mode.
- Assert prefilled values and save payload composition.

### UT-018-011: Successful edit updates last-updated timestamp model
- Simulate save success.
- Assert updated timestamp field changes.

### UT-018-012: Print and download actions emit expected export intent payloads
- Trigger print/download actions.
- Assert export service intent payloads.

## C. Responsive and Accessibility Contracts

### UT-018-013: Responsive mode selector applies stacked/scrollable table variants for mobile
- Mock 375px and desktop widths.
- Assert section/table mode flags.

### UT-018-014: Accessibility model includes semantic headings, table header scopes, and labeled form fields
- Assert heading level markers, table-header scope attributes, and form label links.

---

## 5. Test Data Strategy

- Fixtures for multiple intake versions and appointment statuses.
- Insurance status fixtures for color indicator mapping.
- Responsive-mode fixtures for mobile and desktop branches.

---

## 6. Mocking Strategy

- Mock intake selector service and profile edit/save service.
- Mock export action service and timestamp provider.
- Mock breakpoint utility and accessibility metadata helpers.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-018-001 through UT-018-011 before merge.

---

## 8. Exit Criteria

- AC-mapped intake-profile logic tests pass.
- Edit gating, timestamps, and export intent behavior validated.
- Responsive/accessibility contracts covered.
- Coverage thresholds achieved.

---

## 9. Suggested File Layout

- tests/unit/profile/intake/ProfileIntakeSelectionDisplay.test.ts
- tests/unit/profile/intake/ProfileIntakeEditExport.test.ts
- tests/unit/profile/intake/ProfileIntakeResponsiveA11y.test.ts
- tests/unit/profile/intake/__fixtures__/profileIntake.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-018.
- [ ] Test cases UT-018-001 through UT-018-014 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
