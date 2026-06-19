# UNIT-TEST-PLAN-011: Implement AI Chatbot Engine (NLP Integration)

User Story: US-011 (EP-002)
Source File: .propel/context/tasks/EP-002/us_011/us_011.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for chatbot-engine orchestration to validate conversation turns, NLP extraction outputs, context-aware follow-ups, misunderstanding recovery, summary confirmation, and response-time-safe control flow.

---

## 2. Scope and Assumptions

### In Scope
- Chat session initialization and greeting turn generation.
- Intent/entity extraction mapping for complaint/history/medications/allergies.
- Context memory behavior across turns.
- Unparseable-input handling and reattempt limits.
- Summary generation and edit/confirm transition logic.

### Out of Scope
- Real LLM/NLP vendor latency and production throughput.
- End-to-end UI rendering and network transport.
- Clinical correctness of external medical ontology databases.

### Assumptions
- Chatbot orchestration has deterministic test seams for NLP and policy modules.
- NLP responses are mockable with controlled confidence and extracted entities.
- Conversation state persists in testable in-memory or repository abstraction.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Chat interface/session initialization behavior | UT-011-001 |
| AC-2 | Greeting and intake kickoff turn correctness | UT-011-002 |
| AC-3 | Chief complaint capture and follow-up generation | UT-011-003, UT-011-004 |
| AC-4 | Medical history extraction/classification | UT-011-005 |
| AC-5 | Medication extraction from natural language | UT-011-006 |
| AC-6 | Allergy vs side-effect differentiation logic | UT-011-007 |
| AC-7 | Context-aware cross-turn follow-up (allergy derivative checks) | UT-011-008 |
| AC-8 | Misunderstanding recovery with max reattempts | UT-011-009, UT-011-010 |
| AC-9 | Completion summary composition and confirm/edit flow | UT-011-011 |
| AC-10 | Turn pipeline response-time guard intent | UT-011-012 |

---

## 4. Unit Test Areas

## A. Session Start and Greeting

### UT-011-001: Session start initializes conversation state and history container
- Trigger start-intake action.
- Assert session id/state and initial conversation container are created.

### UT-011-002: Greeting turn includes patient name and expected kickoff prompt
- Provide patient profile fixture.
- Assert generated greeting references patient and asks chief complaint question.

## B. NLP Extraction and Follow-Ups

### UT-011-003: Chief complaint extraction stores normalized symptom payload
- Mock natural-language complaint input.
- Assert parsed complaint is stored in structured state.

### UT-011-004: Follow-up generator asks duration/severity based on symptom detection
- Provide parsed symptom entity.
- Assert follow-up question strategy selects duration/severity prompts.

### UT-011-005: Medical history extraction classifies chronic conditions
- Mock response including chronic conditions.
- Assert condition classification and persisted fields.

### UT-011-006: Medication parser extracts names/dosage/frequency tokens
- Provide medication sentence fixture.
- Assert parsed medication records include expected fields.

### UT-011-007: Allergy classifier separates allergic reaction vs side-effect statements
- Provide mixed allergy-side-effect inputs.
- Assert reaction_type classification aligns with policy rules.

## C. Contextual Reasoning and Recovery

### UT-011-008: Context engine triggers derivative-allergy follow-up when relevant medication appears later
- Seed context with penicillin allergy mention.
- Provide later amoxicillin mention.
- Assert chatbot asks derivative-allergy clarification.

### UT-011-009: Unparseable input triggers polite rephrase request
- Mock low-confidence/unparseable NLP output.
- Assert rephrase prompt generated.

### UT-011-010: Reattempt cap routes to skip/manual fallback path
- Simulate repeated unparseable turns.
- Assert after max retries chatbot offers skip/switch option.

## D. Summary and Performance Guards

### UT-011-011: Summary composer includes chief complaint/history/medications/allergies with confirm/edit options
- Build summary from collected intake state.
- Assert summary sections and confirm/edit actions present.

### UT-011-012: Response-time guard emits timeout fallback when turn budget exceeded
- Mock delayed NLP/provider response beyond threshold.
- Assert timeout-safe fallback response and recoverable state.

---

## 5. Test Data Strategy

- NLP fixtures for clear intent, ambiguous input, and unparseable utterances.
- Clinical entity fixtures for symptoms, chronic conditions, meds, and allergies.
- Context fixtures spanning multi-turn conversation dependencies.

---

## 6. Mocking Strategy

- Mock NLP engine, medical-knowledge mapper, and time budget guard.
- Mock conversation store/repository and summary builder.
- Mock telemetry or latency measurement utility for timeout path assertions.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-011-001 through UT-011-011 before merge.

---

## 8. Exit Criteria

- AC-mapped chatbot logic tests pass.
- Context and misunderstanding recovery behavior validated.
- Summary and timeout fallback behavior covered.
- Coverage thresholds achieved.

---

## 9. Suggested File Layout

- tests/unit/intake/chatbot/ChatSessionOrchestrator.test.ts
- tests/unit/intake/chatbot/ChatNlpExtraction.test.ts
- tests/unit/intake/chatbot/ChatContextRecovery.test.ts
- tests/unit/intake/chatbot/__fixtures__/chatbot.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-011.
- [ ] Test cases UT-011-001 through UT-011-012 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
