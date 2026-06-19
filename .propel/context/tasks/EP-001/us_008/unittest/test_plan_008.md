# UNIT-TEST-PLAN-008: Authorize Outlook Integration

User Story: US-008 (EP-001)
Source File: .propel/context/tasks/EP-001/us_008/us_008.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit tests for Outlook Calendar OAuth flow to validate authorization initiation, code exchange, secure token persistence, connected/disconnected state transitions, and dual-calendar compatibility logic.

---

## 2. Scope and Assumptions

### In Scope
- Connect Outlook action and OAuth request construction.
- Callback token exchange and validation behavior.
- Encrypted refresh token persistence for Outlook integration.
- Disconnect handling and sync-disable behavior.
- Coexistence logic when Google and Outlook are both linked.

### Out of Scope
- Real Microsoft identity platform/network responses.
- End-to-end Graph API behavior.
- UI visual regression for account settings.

### Assumptions
- OAuth handling abstraction follows provider-specific adapters.
- Integration state store supports multiple providers.
- Encryption/persistence paths are testable via mocks.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Connect Outlook button visibility | UT-008-001 |
| AC-2 | OAuth request includes required scopes | UT-008-002 |
| AC-3 | Consent messaging model correctness | UT-008-003 |
| AC-4 | Code exchange token handling | UT-008-004 |
| AC-5 | Encrypted token storage path | UT-008-005, UT-008-006 |
| AC-6 | Connected confirmation state | UT-008-007 |
| AC-7 | Disconnect flow clears token and sync | UT-008-008 |
| AC-8 | Authorization failure messaging and retry | UT-008-009 |
| AC-9 | Both Google and Outlook integration states can coexist | UT-008-010 |

---

## 4. Unit Test Areas

## A. Authorization Initiation

### UT-008-001: Connect Outlook action renders in target contexts
- Render booking confirmation and settings contexts.
- Assert connect action is visible when feature enabled.

### UT-008-002: Connect action composes Microsoft OAuth request with required scopes
- Trigger connect action.
- Assert OAuth request includes Calendars.ReadWrite and offline_access scopes.

### UT-008-003: Consent helper model includes expected manage-calendar intent
- Assert provider-specific consent copy model fields.

## B. Callback and Token Storage

### UT-008-004: Callback exchanges authorization code and handles response
- Mock callback with auth code.
- Assert token exchange adapter called and response mapped.

### UT-008-005: Refresh token encryption occurs before persistence
- Mock token response.
- Assert refresh token goes through encryption utility.

### UT-008-006: Persisted token contract writes encrypted value to provider-specific field
- Assert repository receives encrypted outlook token and metadata.

## C. Integration State and Errors

### UT-008-007: Successful link updates connected state and success notification
- Assert linked state true and success model visible.

### UT-008-008: Disconnect action clears outlook token and stops sync state
- Trigger disconnect.
- Assert token removal and disconnected status.

### UT-008-009: Authorization denial/error path returns retry-capable state
- Mock consent denial or exchange failure.
- Assert error message model and retry action are available.

## D. Multi-Provider Compatibility

### UT-008-010: Google + Outlook linked states coexist without overwriting each other
- Seed state with Google connected then link Outlook.
- Assert both provider states remain connected and independently manageable.

---

## 5. Test Data Strategy

- OAuth success/denial/error fixtures for Outlook.
- Integration-state fixtures covering none, single-provider, and dual-provider links.
- Deterministic token fixtures for encryption assertions.

---

## 6. Mocking Strategy

- Mock Microsoft OAuth adapter, encryption utility, and integration repository.
- Mock provider state store/selectors.
- Mock notification presenter model.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-008-001 through UT-008-009 before merge.

---

## 8. Exit Criteria

- AC-mapped Outlook integration tests pass.
- Token handling and disconnect behavior verified.
- Dual-provider coexistence validated.
- Coverage targets achieved.

---

## 9. Suggested File Layout

- tests/unit/integrations/outlook/OutlookAuthInitiation.test.ts
- tests/unit/integrations/outlook/OutlookAuthCallback.test.ts
- tests/unit/integrations/outlook/OutlookIntegrationState.test.tsx
- tests/unit/integrations/outlook/__fixtures__/outlookAuth.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-008.
- [ ] Test cases UT-008-001 through UT-008-010 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
