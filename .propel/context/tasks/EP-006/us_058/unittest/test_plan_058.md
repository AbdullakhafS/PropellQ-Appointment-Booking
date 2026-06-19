# UNIT-TEST-PLAN-058: Notification Preference Management

User Story: US-058 (EP-006)
Source File: .propel/context/tasks/EP-006/us_058/us_058.md
Priority: MEDIUM
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for notification preference management so patients can choose channels (email/SMS/in-app), persist updates, suppress opted-out channels, and see current saved settings when revisiting preferences.

---

## 2. Scope and Assumptions

### In Scope
- Preference controls UI behavior for email, SMS, and in-app channels.
- Save action and confirmation/error states.
- Preference rehydration and rendering of current settings.
- Opt-out suppression decision logic for reminder channel eligibility.
- Input-level validation interaction for contact requirements (email/mobile) where applicable.

### Out of Scope
- End-to-end reminder delivery across external providers.
- Notification infrastructure provisioning or push platform setup.
- Full integration testing of downstream communication services.

### Assumptions
- Preferences are accessed through a dedicated read/write service abstraction.
- Suppression logic is encapsulated in a testable helper/service.
- Unit tests run with Jest/Vitest and Testing Library patterns.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Patient can select preferred notification channels | UT-058-001, UT-058-002 |
| AC-2 | Saved preferences persist and apply to future reminders | UT-058-003, UT-058-004, UT-058-005 |
| AC-3 | Opted-out channels are suppressed | UT-058-006, UT-058-007 |
| AC-4 | Current settings display correctly on revisit | UT-058-008, UT-058-009 |

---

## 4. Unit Test Areas

## A. Preference Selection Controls

### UT-058-001: Channel toggles render with expected default state
- Render preference panel with initial settings fixture.
- Assert email/SMS/in-app controls exist and reflect initial values.

### UT-058-002: Patient can update channel selections before save
- Simulate toggle changes across channels.
- Assert local draft state reflects user selections without premature persistence calls.

## B. Save and Persistence Behavior

### UT-058-003: Save action sends normalized preference payload
- Mock successful save endpoint.
- Trigger save after selection changes.
- Assert write call payload matches expected channel flags and patient scope.

### UT-058-004: Successful save shows confirmation and clears dirty state
- Mock success response.
- Assert confirmation message appears.
- Assert save action is disabled/reset when no pending changes remain.

### UT-058-005: Save failure retains editable state and shows error
- Mock write failure.
- Assert error feedback is shown.
- Assert user can retry without losing selected values.

## C. Suppression Logic and Eligibility

### UT-058-006: Opted-out channel is excluded from reminder channel resolver
- Provide preference fixture with one or more channels opted out.
- Assert resolver output excludes disabled channels.

### UT-058-007: Fully opted-in profile allows all eligible channels
- Provide profile with all channels enabled and valid contact data.
- Assert resolver returns all channels allowed by policy.

## D. Revisit and Rehydration Behavior

### UT-058-008: Reopen preferences loads persisted settings accurately
- Mock read endpoint returning persisted channel values.
- Assert controls reflect stored preferences on initial render/revisit.

### UT-058-009: Rehydration handles partial settings payload safely
- Mock payload missing optional fields.
- Assert component applies defaults deterministically and avoids runtime errors.

## E. Validation and Edge Handling

### UT-058-010: Email/SMS-dependent channel toggle surfaces validation hints
- Enable email or SMS channel without valid contact data.
- Assert validation guidance is shown according to rules.

### UT-058-011: Validation resolution removes blocking state after data correction
- Start with invalid contact state, then provide valid value.
- Assert blocking error clears and save can proceed.

### UT-058-012: Rapid toggle changes preserve latest intended state
- Simulate quick successive toggle events.
- Assert final in-memory state and submitted payload reflect last user intent.

---

## 5. Non-Functional Unit Checks

### UT-058-013: Accessibility checks for preference controls and feedback
- Assert toggles are keyboard reachable with accessible names.
- Assert confirmation/error messages are announced via accessible regions.

### UT-058-014: Idempotent re-render behavior with unchanged preferences
- Re-render with same persisted state.
- Assert no redundant write calls and stable UI state.

---

## 6. Test Data Strategy

- Create deterministic fixtures for all preference combinations.
- Include contact-data variants (valid/invalid/missing email and phone).
- Include persisted payload variants (complete and partial data).
- Use stable user/profile identifiers for repeatable assertions.

---

## 7. Mocking Strategy

- Mock read/write preference API hooks/services.
- Mock reminder channel resolver dependencies where needed.
- Mock validation helpers for boundary and format cases.
- Mock telemetry/toast utilities if save feedback is instrumented.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-058-001 through UT-058-009 before merge.

---

## 9. Exit Criteria

- All AC-linked unit tests pass.
- Coverage thresholds met for preference modules.
- Suppression and rehydration behaviors validated under edge fixtures.
- No flaky failures across 3 consecutive local or CI runs.

---

## 10. Suggested File Layout

- tests/unit/notifications/NotificationPreferencePanel.test.tsx
- tests/unit/notifications/NotificationPreferencePersistence.test.ts
- tests/unit/notifications/NotificationSuppressionResolver.test.ts
- tests/unit/notifications/NotificationPreferenceValidation.test.tsx
- tests/unit/notifications/__fixtures__/notificationPreferences.fixtures.ts

---

## 11. Execution Checklist

1. Create preference and contact-data fixtures.
2. Implement selection control tests (UT-058-001..002).
3. Implement save/persistence tests (UT-058-003..005).
4. Implement suppression resolver tests (UT-058-006..007).
5. Implement rehydration tests (UT-058-008..009).
6. Implement validation and race/rapid-toggle tests (UT-058-010..012).
7. Add accessibility and rerender stability checks (UT-058-013..014).
8. Execute unit tests and verify coverage targets.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-058.
- [ ] Test cases UT-058-001 through UT-058-014 implemented.
- [ ] Acceptance criteria traceability preserved in test names/docs.
- [ ] Coverage targets achieved.
- [ ] CI unit-test gate passes without flaky failures.
