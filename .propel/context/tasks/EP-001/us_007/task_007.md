# TASK-007: Implement Google Calendar OAuth Authorization

**User Story:** US-007 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_007/us_007.md`  
**Priority:** HIGH  
**Estimated Effort:** 3-4 dev days + security validation  
**Status:** Planned  
**Created:** 2026-06-18

---

## 1. Objective

Implement a secure Google Calendar OAuth 2.0 authorization flow that lets patients connect/disconnect one Google account, stores refresh tokens encrypted at rest, and provides reliable UX messaging for success and failure paths.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Show Connect Google Calendar button in booking confirmation and settings/profile | FE-1, FE-2, QA-1 |
| AC-2 | Start OAuth consent with required Google calendar scopes | BE-1, INT-1, QA-2 |
| AC-3 | Consent message communicates calendar-event management permission | FE-3, QA-2 |
| AC-4 | Exchange auth code for access + refresh token | BE-2, INT-2 |
| AC-5 | Encrypt and store refresh token in patient session record | SEC-1, DB-1, BE-3 |
| AC-6 | Show successful linked-account confirmation and manage-permissions path | FE-4, BE-4 |
| AC-7 | Disconnect removes token and stops future sync | FE-5, BE-5, DB-2 |
| AC-8 | Handle denied/failed auth with clear retry UX | FE-6, BE-6, QA-3 |

---

## 3. Layered Implementation Tasks

## Frontend Tasks

### FE-1: Booking Confirmation Entry Point
- Add `Connect Google Calendar` CTA on booking confirmation page.
- Show connected state when account is already authorized.
- Disable duplicate connect clicks while redirect is in progress.

### FE-2: Settings/Profile Entry Point
- Add Google Calendar integration card in settings/profile.
- Display status badge: `Not Connected`, `Connected`, `Connection Error`.
- Reuse a shared connect action handler used by booking confirmation.

### FE-3: Consent Pre-Context Messaging
- Add pre-redirect helper text: `PropellQ will request access to create and manage your calendar events.`
- Include a short privacy note and link to permissions help.

### FE-4: Success UX and Manage Permissions
- On successful callback redirect, display success banner:
  `Google Calendar connected! Appointments will be added automatically.`
- Provide `Manage Calendar Permissions` action linking to integration settings.

### FE-5: Disconnect UX
- Add `Disconnect Google Calendar` action in settings.
- Include confirmation dialog for irreversible revoke in-app state.
- Update UI status immediately after success.

### FE-6: Error UX + Retry
- Show standardized error message when OAuth fails/denied:
  `Google Calendar authorization failed. Please try again or contact support.`
- Provide retry button to restart auth flow.
- Distinguish recoverable transient failures from revoked/denied state.

## Backend/API Tasks

### BE-1: OAuth Authorize Endpoint
- Implement `GET /api/auth/google/authorize`.
- Build Google authorization URL with required scopes and secure state value.
- Include offline access and consent prompt to obtain refresh token.
- Validate authenticated patient context before redirect generation.

### BE-2: OAuth Callback + Token Exchange
- Implement `GET /api/auth/google/callback`.
- Validate state and authorization code.
- Exchange code with Google token endpoint for `access_token`, `refresh_token`, and expiry.
- Handle provider-side error responses (denied consent, invalid_grant, redirect mismatch).

### BE-3: Token Persistence and Lifecycle Metadata
- Persist encrypted refresh token and token expiry metadata.
- Update auth status field to `authorized`.
- Record selected/primary calendar ID when available.
- Ensure no tokens are written to logs, telemetry, or exception payloads.

### BE-4: Linked Account Confirmation State
- Return or redirect with deterministic success state for UI rendering.
- Add endpoint to fetch integration state for current patient.

### BE-5: Disconnect/Revoke Endpoint
- Implement `POST /api/auth/google/disconnect`.
- Remove encrypted refresh token and related auth metadata.
- Set auth status to `revoked` and prevent downstream sync attempts.

### BE-6: Error Handling and Failure Modes
- Normalize OAuth failure reasons into safe client-facing error codes.
- Add retry-safe behavior for transient provider/network failures.
- Keep internal diagnostic detail in secure server logs only.

## Database Tasks

### DB-1: Session/Auth Storage Schema
- Add or validate session columns:
  - `google_refresh_token`
  - `google_access_token_expires_at`
  - `google_calendar_id`
  - `google_auth_status`
- Add migration defaults for existing rows (`google_auth_status = 'revoked'` or equivalent baseline).

### DB-2: Disconnect Data Clearing Rules
- Ensure disconnect flow nulls sensitive token columns.
- Keep non-sensitive audit timestamps/status for support traceability.
- Add index support for querying authorized sessions when sync jobs run.

## Integration Tasks

### INT-1: Google OAuth Client Configuration
- Configure Google OAuth client (client ID/secret, redirect URI).
- Enforce exact redirect URI match per environment.
- Use approved scopes:
  - `https://www.googleapis.com/auth/calendar.events`
  - `https://www.googleapis.com/auth/calendar.calendarList.readonly`
  - `https://www.googleapis.com/auth/calendar.settings.readonly`

### INT-2: Token Endpoint/SDK Integration
- Integrate Google Auth SDK or direct token endpoint adapter.
- Map provider error payloads to internal typed errors.
- Capture provider request IDs/correlation when available.

## Security/Compliance Tasks

### SEC-1: Encryption and Secret Handling
- Encrypt refresh token at rest (AES-256 or platform-managed equivalent).
- Store encryption keys in secure secret manager; never in source code.
- Add key-rotation-safe token decrypt/encrypt path.

### SEC-2: OAuth Hardening
- Enforce CSRF protection using `state` validation.
- Validate callback parameters and reject malformed requests.
- Apply strict redirect URI allowlist.

### SEC-3: HIPAA and Privacy Controls
- Redact tokens from logs and support tooling.
- Document data retention behavior for revoked integrations.
- Complete security review checklist for token handling workflow.

## Ops/Observability Tasks

### OPS-1: Metrics and Monitoring
- Track metrics:
  - OAuth initiation count
  - callback success/failure rate
  - disconnect count
  - token exchange latency
- Segment failures by reason (denied, invalid_grant, network, config).

### OPS-2: Alerting
- Alert on elevated authorization failure rate above threshold.
- Alert on redirect mismatch or client credential misconfiguration spikes.
- Provide runbook entries for support triage and retry guidance.

## Testing Tasks

### QA-1: UI/Functional Tests
- Verify connect button appears in booking confirmation and settings.
- Verify connected/disconnected status rendering.
- Verify retry button behavior after failure.

### QA-2: OAuth Flow Integration Tests
- Full flow: authorize -> callback -> token exchange -> encrypted persistence.
- Validate requested scopes and callback state verification.
- Validate success redirect/banner behavior.

### QA-3: Negative and Security Tests
- User denies consent -> correct user-facing error and no token stored.
- Invalid/missing state -> request rejected.
- Invalid auth code -> safe error response.
- Disconnect -> token removed and status updated to revoked.

### QA-4: Token Handling Unit Tests
- Encryption/decryption roundtrip tests.
- Token expiry computation and near-expiry refresh trigger helper tests.
- Ensure no sensitive fields leak in serialized error/log outputs.

---

## 4. Dependencies

- US-003 appointment flow available for downstream event creation context.
- EP-005 authentication/session context available for patient identity.
- EP-TECH-001 secret management available for OAuth credentials and encryption keys.
- Google OAuth app registration completed for all environments.

---

## 5. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Refresh token leakage through storage/logging | Critical | Encrypt at rest, strict log redaction, security review gates |
| Callback/state validation flaw (CSRF) | High | Mandatory state validation and callback input hardening |
| Misconfigured redirect URI blocks authorization | Medium | Environment-specific config validation and startup checks |
| Missing refresh token on re-consent | Medium | Request offline access + consent prompt and detect missing token case |
| Disconnect does not fully stop sync behavior | Medium | Clear token + set revoked status + enforce sync guard clause |

---

## 6. Definition of Done

- [ ] Connect button available in booking confirmation and settings.
- [ ] OAuth authorize endpoint implemented with required scopes/state.
- [ ] Callback endpoint exchanges auth code for tokens successfully.
- [ ] Refresh token encrypted and stored securely.
- [ ] Linked account success messaging and manage-permissions path implemented.
- [ ] Disconnect flow removes token data and marks account revoked.
- [ ] Error handling and retry UX implemented for denied/failed authorization.
- [ ] Security controls validated (state, redirect allowlist, redaction).
- [ ] Metrics and alerts configured for OAuth success/failure monitoring.
- [ ] Unit + integration + negative tests passing.
- [ ] AC-1 through AC-8 fully traced and validated.

---

## 7. Suggested Execution Order

1. DB-1, DB-2
2. INT-1, SEC-1, SEC-2
3. BE-1, BE-2, BE-3
4. FE-1, FE-2, FE-3
5. BE-4, FE-4
6. BE-5, FE-5
7. BE-6, FE-6
8. OPS-1, OPS-2
9. QA-1 through QA-4
10. Final security/compliance sign-off and AC validation
