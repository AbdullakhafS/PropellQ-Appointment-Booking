# UNIT-TEST-PLAN-013: Build Manual Intake Form with Auto-Population

User Story: US-013 (EP-002)
Source File: .propel/context/tasks/EP-002/us_013/us_013.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for manual intake form behavior, including section structure, auto-population consent and mapping, editable repeating fields, submit-only validation, and responsive form-mode logic.

---

## 2. Scope and Assumptions

### In Scope
- Form section model and rendering contracts.
- Use-previous vs start-fresh decision path.
- Auto-population field mapping from prior intake data.
- Editable repeated medication/allergy entries.
- Submit-time validation and error model generation.

### Out of Scope
- End-to-end API persistence flow.
- Browser-level mobile gesture behavior.
- Visual styling verification beyond structural contracts.

### Assumptions
- Form state managed via deterministic schema + state manager.
- Prior intake fetch and mapping utilities are mockable.
- Validation engine supports submit-only execution mode.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Form contains required intake sections | UT-013-001 |
| AC-2 | Auto-population consent prompt behavior | UT-013-002 |
| AC-3 | Use-previous prefill mapping loads expected values | UT-013-003, UT-013-004 |
| AC-4 | All fields editable without load-time validation blockers | UT-013-005 |
| AC-5 | Chief complaint prefill and edit behavior | UT-013-006 |
| AC-6 | Medical history checkbox/text mapping | UT-013-007 |
| AC-7 | Repeating medication rows add/edit/delete behavior | UT-013-008, UT-013-009 |
| AC-8 | Allergy vs side-effect field handling | UT-013-010 |
| AC-9 | Insurance fields mapping and optionality | UT-013-011 |
| AC-10 | Submit-only validation and clear errors | UT-013-012 |
| AC-11 | Section last-modified timestamp updates | UT-013-013 |
| AC-12 | Responsive form-mode logic for mobile/tablet | UT-013-014 |

---

## 4. Unit Test Areas

## A. Form Structure and Auto-Population

### UT-013-001: Intake form schema includes all required sections in expected order
- Initialize form schema.
- Assert section keys: complaint, history, medications, allergies, insurance.

### UT-013-002: Auto-population consent prompt controls data-load path
- Trigger form load with historical data available.
- Assert user choice toggles use-previous vs start-fresh behavior.

### UT-013-003: Use-previous maps prior intake values into form fields
- Choose use-previous path.
- Assert mapped values populate complaint/history/medications/allergies/insurance fields.

### UT-013-004: Start-fresh path leaves fields empty/default
- Choose start-fresh path.
- Assert no historical values are auto-filled.

## B. Editability and Section Behavior

### UT-013-005: Loaded prefilled values remain fully editable and deletable
- Edit and clear prefilled values.
- Assert no blocking validation before submit.

### UT-013-006: Chief complaint field supports prefill override and clear operations
- Assert update and clear actions persist state correctly.

### UT-013-007: Medical history checkbox and other-conditions text fields map correctly
- Toggle common condition checkboxes and enter custom condition text.
- Assert state model update.

### UT-013-008: Medication rows support add/update actions
- Add medication row and update values.
- Assert row-state collection updates correctly.

### UT-013-009: Medication row delete removes selected entry without corrupting remaining rows
- Delete middle row in multi-row fixture.
- Assert remaining rows preserved in order.

### UT-013-010: Allergy section tracks allergic reaction vs side-effect type
- Enter mixed allergy/side-effect entries.
- Assert reaction_type classification in form model.

### UT-013-011: Insurance fields load/mutate with optional plan/group behavior
- Prefill insurance data and edit optional fields.
- Assert required vs optional constraints in state.

## C. Submit Validation, Timestamps, Responsive Mode

### UT-013-012: Submit-only validation returns clear errors for missing required fields
- Submit incomplete form.
- Assert validation errors generated only on submit event.

### UT-013-013: Section last-modified timestamp updates on edits
- Edit section fields.
- Assert timestamp value changes per section update.

### UT-013-014: Responsive layout mode toggles between single-column and multi-column variants
- Mock 375px and 768px breakpoints.
- Assert form mode flags and sticky-submit logic markers.

---

## 5. Test Data Strategy

- Historical intake fixtures with complete and partial data.
- Repeating medication/allergy fixtures with multiple rows.
- Incomplete submission fixtures for validation assertions.

---

## 6. Mocking Strategy

- Mock prior-intake data service and mapping utility.
- Mock breakpoint utility and form schema provider.
- Mock validation engine in submit-only mode.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-013-001 through UT-013-012 before merge.

---

## 8. Exit Criteria

- AC-mapped manual form logic tests pass.
- Auto-population and repeating-row behavior validated.
- Submit validation/timestamp/responsive branches covered.
- Coverage thresholds achieved.

---

## 9. Suggested File Layout

- tests/unit/intake/manual/ManualIntakeFormSchema.test.ts
- tests/unit/intake/manual/ManualIntakeAutoPopulate.test.ts
- tests/unit/intake/manual/ManualIntakeRowsValidation.test.ts
- tests/unit/intake/manual/__fixtures__/manualIntake.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-013.
- [ ] Test cases UT-013-001 through UT-013-014 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
