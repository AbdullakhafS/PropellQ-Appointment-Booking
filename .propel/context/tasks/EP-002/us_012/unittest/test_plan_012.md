# UNIT-TEST-PLAN-012: Design Multi-Step Chatbot Conversation Flow

User Story: US-012 (EP-002)
Source File: .propel/context/tasks/EP-002/us_012/us_012.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for multi-step intake conversation flow logic, stage transitions, conditional branching, progress tracking, and skip/switch fallback behavior.

---

## 2. Scope and Assumptions

### In Scope
- Step engine progression across greeting, complaint, history, medications, allergies, insurance, and summary.
- Conditional branch rules for follow-up questions.
- Progress indicator state calculations.
- Summary generation and correction loop handling.
- Skip/switch fallback decision paths.

### Out of Scope
- Figma/flowchart artifact rendering verification.
- End-to-end conversational UX and animation timing.
- Live LLM response generation quality checks.

### Assumptions
- Flow engine is represented as finite-state machine or equivalent rule-driven orchestrator.
- Branch predicates are deterministic and unit-testable.
- Conversation stage metadata is available for progress indicator computation.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Conversation stage graph exists and transition map valid | UT-012-001 |
| AC-2 | Opening greeting stage behavior | UT-012-002 |
| AC-3 | Chief complaint stage + conditional follow-ups | UT-012-003, UT-012-004 |
| AC-4 | Medical history stage conditional prompts | UT-012-005 |
| AC-5 | Medication stage with per-medication follow-up prompts | UT-012-006 |
| AC-6 | Allergy stage conditional reaction capture | UT-012-007 |
| AC-7 | Insurance stage yes/no branching | UT-012-008 |
| AC-8 | Summary and confirm/edit loop | UT-012-009 |
| AC-9 | Progress indicator reflects step advancement | UT-012-010 |
| AC-10 | Skip/switch fallback offered in blocked flow states | UT-012-011 |

---

## 4. Unit Test Areas

## A. Stage Graph and Greeting

### UT-012-001: Flow definition includes all required stages and legal transitions
- Load flow definition.
- Assert stage keys and transition map completeness.

### UT-012-002: Entry state emits greeting with time estimate and readiness prompt
- Start flow.
- Assert greeting payload content fields.

## B. Conditional Branching per Stage

### UT-012-003: Chief complaint stage captures complaint and advances correctly
- Provide complaint response.
- Assert complaint persisted and next stage determined.

### UT-012-004: Symptom mention triggers severity/duration follow-up branch
- Provide symptom-rich complaint input.
- Assert follow-up branch route selected.

### UT-012-005: Medical history stage triggers condition-specific follow-up prompts
- Provide chronic condition responses.
- Assert duration/medication follow-up prompts generated.

### UT-012-006: Medication stage asks dosage/frequency for each listed medication
- Provide multi-medication input.
- Assert follow-up queue contains prompts per medication.

### UT-012-007: Allergy yes-branch captures drug and reaction details
- Provide allergy affirmative response.
- Assert allergy details stage fields required and persisted.

### UT-012-008: Insurance stage branches by yes/no and captures insurer/member fields when yes
- Test yes and no responses.
- Assert insurance data collection rules applied.

## C. Summary, Progress, and Fallback

### UT-012-009: Summary stage composes all collected data and supports edit loop
- Reach summary with full intake data.
- Assert summary includes complaint/history/medications/allergies/insurance and edit route.

### UT-012-010: Progress indicator computes current step and total consistently
- Move through staged responses.
- Assert step index/total values update correctly.

### UT-012-011: Skip/switch fallback action is exposed from blocked states
- Simulate frustration/invalid retries.
- Assert skip question and switch-to-form options are offered.

---

## 5. Test Data Strategy

- Stage response fixtures for each branch path.
- Inputs for positive/negative insurance and allergy branches.
- Correction-loop fixtures for summary edits.

---

## 6. Mocking Strategy

- Mock intent classifier and entity extraction outputs.
- Mock state persistence adapter and progress computation helper.
- Mock fallback policy engine for blocked/invalid response paths.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-012-001 through UT-012-010 before merge.

---

## 8. Exit Criteria

- AC-mapped flow rules are fully tested.
- Branching and summary edit loop paths validated.
- Progress/fallback behavior verified.
- Coverage thresholds achieved.

---

## 9. Suggested File Layout

- tests/unit/intake/chatflow/FlowDefinition.test.ts
- tests/unit/intake/chatflow/FlowBranching.test.ts
- tests/unit/intake/chatflow/FlowSummaryProgress.test.ts
- tests/unit/intake/chatflow/__fixtures__/flow.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-012.
- [ ] Test cases UT-012-001 through UT-012-011 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
