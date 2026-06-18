# TASK-008: Implement Outlook Calendar OAuth Authorization

**User Story:** US-008 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_008/us_008.md`  
**Priority:** HIGH  
**Estimated Effort:** 3-4 dev days + security validation  
**Status:** Planned  
**Created:** 2026-06-18

---

## 1. Objective

Implement a secure Microsoft identity OAuth 2.0 flow for Outlook calendar authorization, enabling patients to connect and disconnect Outlook while preserving encrypted token storage, resilient error handling, and parity with existing Google calendar integration.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Show Connect Outlook Calendar button on booking confirmation and settings/profile | FE-1, FE-2, QA-1 |
| AC-2 | Initiate Microsoft OAuth with Calendars.ReadWrite and offline_access | BE-1, INT-1, QA-2 |
| AC-3 | Consent UX communicates event-management permission | FE-3, QA-2 |
| AC-4 | Exchange auth code for access and refresh tokens | BE-2, INT-2 |
| AC-5 | Encrypt and store refresh token in PatientSessions.outlook_refresh_token | SEC-1, DB-1, BE-3 |
| AC-6 | Show successful linked-account confirmation and manage-permissions path | FE-4, BE-4 |
| AC-7 | Disconnect removes token and disables future Outlook sync | FE-5, BE-5, DB-2 |
| AC-8 | Authorization failure/denial surfaces clear retryable message | FE-6, BE-6, QA-3 |
| AC-9 | Support concurrent Google and Outlook connections and sync fan-out | BE-7, DB-3, QA-4 |

---

## 3. Layered Implementation Tasks

## Frontend Tasks

### FE-1: Booking Confirmation Entry Point
- Add `Connect Outlook Calendar` CTA on booking confirmation page.
- Show integration state indicator when Outlook is connected.
- Prevent repeated click during redirect bootstrap.

### FE-2: Settings/Profile Integration Card
- Add Outlook integration card parallel to Google card.
- Display state badges: `Not Connected`, `Connected`, `Connection Error`.
- Keep Google and Outlook controls independent and simultaneously visible.

### FE-3: Consent Pre-Context Messaging
- Add pre-redirect helper text:
  `PropellQ will request access to manage your Outlook calendar events.`
- Include privacy/help link before redirect.

### FE-4: Success UX and Manage Permissions
- Show success banner after callback:
  `Outlook Calendar connected! Appointments will be added automatically.`
- Provide `Manage Permissions` link to integration settings section.

### FE-5: Disconnect UX
- Add `Disconnect Outlook Calendar` action with confirmation dialog.
- Preserve Google connected state when Outlook is disconnected.
- Refresh UI state after disconnect response.

### FE-6: Error UX + Retry
- Standardize user-facing error message:
  `Outlook Calendar authorization failed. Please try again or contact support.`
- Provide retry action to restart OAuth flow.
- Distinguish consent-denied and transient network failures for diagnostics.

## Backend/API Tasks

### BE-1: Outlook Authorize Endpoint
- Implement `GET /api/auth/outlook/authorize`.
- Build Microsoft authorize URL with required scopes and secure state.
- Request offline access to receive refresh token.
- Validate authenticated patient context before redirect.

### BE-2: Outlook Callback and Token Exchange
- Implement `GET /api/auth/outlook/callback`.
- Validate callback state and authorization code.
- Exchange code at Microsoft token endpoint for access/refresh token and expiry metadata.
- Handle OAuth errors (access_denied, invalid_grant, redirect mismatch) safely.

### BE-3: Token Persistence and Auth Status
- Encrypt and persist Outlook refresh token and token expiry metadata.
- Set `outlook_auth_status` to `authorized` on success.
- Save selected/default calendar ID when returned by Microsoft Graph.
- Ensure tokens are never logged.

### BE-4: Integration State Endpoint
- Extend integration status API to report Outlook state.
- Return deterministic success/error status for frontend banners and badges.

### BE-5: Disconnect Endpoint
- Implement `POST /api/auth/outlook/disconnect`.
- Null Outlook token fields and update `outlook_auth_status` to `revoked`.
- Ensure downstream sync jobs skip revoked Outlook connections.

### BE-6: Error Handling and Retry Safety
- Normalize provider failures to safe client-facing codes.
- Add retry-safe behavior for temporary provider/network failures.
- Preserve internal diagnostic details in secure server logs.

### BE-7: Multi-Provider Connection Orchestration
- Update integration model to support active Google and Outlook tokens concurrently.
- Ensure appointment sync scheduler fans out event creation to all active providers.
- Prevent one provider failure from blocking the other provider sync path.

## Database Tasks

### DB-1: Outlook Session Columns
- Add or validate columns in patient session storage:
  - `outlook_refresh_token`
  - `outlook_access_token_expires_at`
  - `outlook_calendar_id`
  - `outlook_auth_status`
- Add default migration value for existing rows.

### DB-2: Disconnect Clearing Rules
- Ensure disconnect path nulls Outlook token data only.
- Retain non-sensitive audit metadata for supportability.
- Add index support for querying active Outlook-authorized users.

### DB-3: Dual-Provider State Integrity
- Validate schema supports both Google and Outlook token sets without collision.
- Add integrity checks to avoid overwriting Google fields during Outlook auth flow.
- Add migration test cases for records with one or both providers connected.

## Integration Tasks

### INT-1: Microsoft App Registration and OAuth Config
- Configure Microsoft Entra app registration (client ID/secret, redirect URI).
- Enforce environment-specific redirect URI exact matches.
- Configure scopes:
  - `Calendars.ReadWrite`
  - `offline_access`

### INT-2: Microsoft Token/Graph Adapter
- Integrate MSAL or token endpoint adapter for exchange/refresh support.
- Map Microsoft OAuth error payloads to internal typed error model.
- Capture correlation/request IDs when available for support tracing.

## Security/Compliance Tasks

### SEC-1: Encryption and Key Management
- Encrypt Outlook refresh token at rest using approved algorithm (AES-256 or managed equivalent).
- Keep encryption keys in secure secret manager only.
- Ensure key rotation compatibility.

### SEC-2: OAuth Hardening
- Require state-based CSRF protection.
- Validate callback input schema and reject malformed requests.
- Restrict redirect URIs with strict allowlist.

### SEC-3: HIPAA and Data Exposure Controls
- Redact tokens from logs, traces, and exceptions.
- Verify TLS for all token transport operations.
- Complete HIPAA/security review checklist for Outlook path.

## Ops/Observability Tasks

### OPS-1: Metrics and Dashboarding
- Track metrics:
  - OAuth initiation count
  - callback success/failure rate
  - disconnect count
  - token exchange latency
  - dual-provider connection count
- Segment failure reasons (denied, invalid_grant, network, config).

### OPS-2: Alerting and Runbooks
- Alert on elevated Outlook auth failure rate.
- Alert on redirect mismatch/config errors.
- Add support runbook for reauthorization and dual-provider troubleshooting.

## Testing Tasks

### QA-1: UI/Functional Tests
- Verify Connect Outlook button appears in booking confirmation and settings.
- Verify connected/disconnected badges and state transitions.
- Verify disconnect only impacts Outlook state.

### QA-2: OAuth Integration Tests
- Full flow: authorize -> callback -> token exchange -> encrypted storage.
- Validate scope request includes Calendars.ReadWrite and offline_access.
- Validate success redirect and banner behavior.

### QA-3: Security and Negative Tests
- Denied consent should show expected error and store no token.
- Invalid/missing state should be rejected.
- Invalid authorization code should fail safely.
- Ensure no token appears in logs or error payloads.

### QA-4: Dual-Provider Behavior Tests
- Connect Google first, then Outlook: both remain active.
- Connect Outlook first, then Google: both remain active.
- New appointment triggers sync attempts for both providers.
- Outlook auth failure does not block Google sync path (and vice versa).

---

## 4. Dependencies

- US-003 appointment flow available for downstream sync events.
- US-007 Google integration path available for parity and shared integration model.
- EP-005 authentication/session context available for patient identity.
- EP-TECH-001 secret management available for client credentials and encryption keys.
- Microsoft app registration completed for all deployment environments.

---

## 5. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Refresh token leakage through storage/logging | Critical | Encrypt at rest, strict redaction, mandatory security review |
| OAuth state/redirect validation weakness | High | Enforce state checks and redirect URI allowlist |
| Microsoft Graph/API throttling affects sync reliability | Medium | Backoff strategy, queue retry, provider-level alerts |
| Outlook disconnect accidentally clears Google integration | Medium | Provider-specific data clearing and regression tests |
| Dual-provider sync contention causes missed event updates | Medium | Per-provider isolation, idempotent fan-out, independent failure handling |

---

## 6. Definition of Done

- [ ] Connect Outlook button available in booking confirmation and settings.
- [ ] Microsoft authorize endpoint implemented with required scopes and state.
- [ ] Callback endpoint exchanges auth code and persists tokens securely.
- [ ] Outlook refresh token encrypted at rest with managed keys.
- [ ] Success and error UX messaging implemented with retry path.
- [ ] Disconnect flow revokes only Outlook connection and stops Outlook sync.
- [ ] Google and Outlook can be connected simultaneously.
- [ ] Dual-provider sync fan-out behavior validated.
- [ ] Security controls validated (state, redirect allowlist, redaction, HIPAA checklist).
- [ ] Metrics, dashboards, and alerts configured.
- [ ] Unit, integration, negative, and dual-provider tests passing.
- [ ] AC-1 through AC-9 fully traced and validated.

---

## 7. Suggested Execution Order

1. DB-1, DB-2, DB-3
2. INT-1, SEC-1, SEC-2
3. BE-1, BE-2, BE-3
4. FE-1, FE-2, FE-3
5. BE-4, FE-4
6. BE-5, FE-5
7. BE-6, FE-6
8. BE-7
9. OPS-1, OPS-2
10. QA-1 through QA-4
11. Final security/compliance sign-off and AC validation
