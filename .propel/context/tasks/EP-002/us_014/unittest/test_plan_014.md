# UNIT-TEST-PLAN-014: Enable Intake Mode Switching (AI to Manual)

User Story: US-014 (EP-002)
Source File: .propel/context/tasks/EP-002/us_014/us_014.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for intake-mode switching to validate mode selection defaults, data-preserving mapping between chatbot and form states, switch-limit enforcement, progress recalculation, and confirmation-flow safeguards.

---

## 2. Scope and Assumptions

### In Scope
- Initial mode selection behavior and default fallback.
- Switch action availability and confirmation flow.
- Chatbot-to-form mapping and form-to-chatbot mapping logic.
- Switch count guard and disable behavior after allowed limit.
- Progress indicator state updates after mode transition.

### Out of Scope
- End-to-end UX animation and full session routing.
- NLP content generation quality for converted prompts.
- Real device rendering-specific placement metrics.

### Assumptions
- Mode switch orchestrator centralizes mapping and state transitions.
- Mapping transforms are implemented in dedicated helper modules.
- Switch confirmation modal is represented by deterministic state/actions.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Switch affordance visible after partial completion | UT-014-001 |
| AC-2 | Initial mode choice default behavior | UT-014-002 |
| AC-3 | Switch button available throughout intake flow | UT-014-003 |
| AC-4 | Chatbot to form data preservation mapping | UT-014-004, UT-014-005 |
| AC-5 | Form to chatbot continuation mapping | UT-014-006 |
| AC-6 | Canonical data mapping rules for medications/allergies/context | UT-014-007 |
| AC-7 | Switch-limit enforcement | UT-014-008 |
| AC-8 | Progress indicator updates in target mode | UT-014-009 |
| AC-9 | Mobile-visible switch action contract | UT-014-010 |
| AC-10 | Confirmation modal gates switch action | UT-014-011 |

---

## 4. Unit Test Areas

## A. Mode Entry and Switch Visibility

### UT-014-001: Switch option appears after any section progress is recorded
- Seed partial intake state.
- Assert switch action visibility true.

### UT-014-002: Initial mode chooser defaults to AI when no explicit selection
- Initialize intake without mode choice.
- Assert active mode resolves to AI.

### UT-014-003: Switch action remains exposed in active flow states
- Step through multiple intake stages.
- Assert switch action remains available (until limit reached).

## B. Data Preservation and Mapping

### UT-014-004: Chatbot-to-form mapping pre-fills structured fields
- Provide chatbot state with complaint/history/medications/allergies.
- Assert mapped form state contains equivalent prefilled values.

### UT-014-005: Mapping includes explanatory status flag for previously answered items
- Switch from chatbot to form.
- Assert info banner/state flag indicates carried-over answers.

### UT-014-006: Form-to-chatbot mapping converts form values into continuation prompts/context
- Provide form values then switch to chatbot.
- Assert continuation prompt queue references existing entered values.

### UT-014-007: Canonical mapping covers medication rows and allergy structures accurately
- Test medication and allergy fixtures.
- Assert no data loss and field-level correspondence.

## C. Guardrails, Progress, and Confirmation

### UT-014-008: Switch guard enforces max switch count
- Perform allowed number of switches.
- Assert further switch attempts are blocked with disable reason.

### UT-014-009: Progress model recalculates current step/position after mode transition
- Switch modes at mid-progress.
- Assert updated progress representation in target mode context.

### UT-014-010: Mobile mode marks switch control as primary visible action
- Mock mobile viewport.
- Assert switch control visibility/state contract for mobile branch.

### UT-014-011: Confirmation modal requires explicit consent before executing switch
- Trigger switch action.
- Assert switch not executed until confirm action chosen; cancel preserves current mode.

---

## 5. Test Data Strategy

- Partial and complete intake states for both chatbot and form modes.
- Mapping fixtures for medications, allergies, and condition lists.
- Switch-count boundary fixtures (0, max-1, max, max+1 attempts).

---

## 6. Mocking Strategy

- Mock mode-switch orchestrator dependencies and mapping helpers.
- Mock breakpoint utility for mobile-specific branch assertions.
- Mock progress computation service.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-014-001 through UT-014-009 before merge.

---

## 8. Exit Criteria

- AC-mapped mode-switch behavior validated.
- Data preservation mappings and switch limits verified.
- Progress and confirmation gating behavior covered.
- Coverage thresholds achieved.

---

## 9. Suggested File Layout

- tests/unit/intake/switch/ModeSelectionSwitchVisibility.test.ts
- tests/unit/intake/switch/ModeMappingPreservation.test.ts
- tests/unit/intake/switch/ModeSwitchGuardsProgress.test.ts
- tests/unit/intake/switch/__fixtures__/modeSwitch.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-014.
- [ ] Test cases UT-014-001 through UT-014-011 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
