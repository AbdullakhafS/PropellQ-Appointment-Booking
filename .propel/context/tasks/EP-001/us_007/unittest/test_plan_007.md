# UNIT-TEST-PLAN-007: Authorize Google Calendar Integration

User Story: US-007 (EP-001)
Source File: .propel/context/tasks/EP-001/us_007/us_007.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit tests for Google Calendar OAuth integration flow to validate authorization initiation, token exchange handling, encrypted token storage contract, connection/disconnection state, and error paths.

---

## 2. Scope and Assumptions

### In Scope
- Connect button behavior and OAuth initiation intent.
- OAuth callback handler for code exchange success/failure.
- Token persistence contract (encrypted refresh token handling).
- Connected/disconnected state transitions in settings/profile flow.
- User-facing error and retry state behavior.

### Out of Scope
- Real Google OAuth endpoint/network behavior.
- End-to-end cryptographic implementation verification.
- Full account permission dashboard UX.

### Assumptions
- OAuth client adapter and token repository are injectable/mocked.
- Encryption utility exposes deterministic test seam/mocks.
- UI state derives from integration status in store/service.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Connect button appears in expected contexts | UT-007-001 |
| AC-2 | OAuth flow initiates with expected scopes | UT-007-002 |
| AC-3 | Consent context messaging is prepared correctly | UT-007-003 |
| AC-4 | Code exchange handles token response | UT-007-004 |
| AC-5 | Refresh token stored via secure/encrypted path | UT-007-005, UT-007-006 |
| AC-6 | Success state shows connected confirmation | UT-007-007 |
| AC-7 | Disconnect removes token and disables sync | UT-007-008 |
| AC-8 | OAuth denial/failure surfaces retry-safe message | UT-007-009, UT-007-010 |

---

## 4. Unit Test Areas

## A. Authorization Initiation

### UT-007-001: Connect Google Calendar action is rendered in booking/settings contexts
- Render contexts with integration feature enabled.
- Assert connect action visibility.

### UT-007-002: Connect action builds OAuth request with required scopes
- Trigger connect action.
- Assert auth URL/request contains configured Google scopes and redirect uri.

### UT-007-003: Consent messaging model includes manage-events intent text
- Build consent helper model.
- Assert expected explanation content fields.

## B. Callback and Token Handling

### UT-007-004: OAuth callback exchanges auth code for access/refresh tokens
- Mock callback with auth code.
- Assert token exchange adapter called and response handled.

### UT-007-005: Refresh token passes through encryption utility before persistence
- Mock token exchange success.
- Assert raw refresh token is encrypted before repository write.

### UT-007-006: Persistence payload stores encrypted token in expected field contract
- Assert token repository write uses encrypted field and account linkage metadata.

## C. Connection State and Disconnection

### UT-007-007: Successful link updates integration status and success notification model
- Assert connected state flag true and success message action model available.

### UT-007-008: Disconnect action clears stored token and disables sync state
- Trigger disconnect.
- Assert token cleared and integration status becomes disconnected.

## D. Error and Retry Paths

### UT-007-009: Consent denial path maps to user-friendly failure state
- Mock OAuth provider denial response.
- Assert failure message model and retry action state.

### UT-007-010: Token exchange failure preserves safe recoverable state
- Mock exchange error.
- Assert no token persisted and system remains disconnected with retry path.

---

## 5. Test Data Strategy

- OAuth fixtures for success, denial, and exchange failure.
- Deterministic token fixtures for encryption/persistence assertions.
- Integration-state fixtures for connected/disconnected rendering.

---

## 6. Mocking Strategy

- Mock OAuth adapter, encryption utility, and session repository.
- Mock notification/message presenter model.
- Mock feature flags or settings context providers.

---

## 7. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-007-001 through UT-007-008 before merge.

---

## 8. Exit Criteria

- AC-mapped OAuth tests pass.
- Token handling and disconnection behavior verified.
- Error/retry paths validated.
- Coverage targets achieved.

---

## 9. Suggested File Layout

- tests/unit/integrations/google/GoogleAuthInitiation.test.ts
- tests/unit/integrations/google/GoogleAuthCallback.test.ts
- tests/unit/integrations/google/GoogleIntegrationState.test.tsx
- tests/unit/integrations/google/__fixtures__/googleAuth.fixtures.ts

---

## 10. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-007.
- [ ] Test cases UT-007-001 through UT-007-010 implemented.
- [ ] Acceptance criteria traceability retained.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
