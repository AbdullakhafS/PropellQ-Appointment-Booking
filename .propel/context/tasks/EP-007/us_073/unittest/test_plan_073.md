# UNIT-TEST-PLAN-073: Session Timeout (15-Minute Inactivity)

User Story: US-073 (EP-007)
Source File: .propel/context/tasks/EP-007/us_073/us_073.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for inactivity-based session expiration, active-use renewal behavior, unauthorized responses for expired sessions, and timeout audit logging.

---

## 2. Scope and Assumptions

### In Scope
- Server-side 15-minute inactivity timeout enforcement.
- Sliding/fixed expiration logic behavior.
- Session renewal on valid user activity.
- 401 response behavior for expired sessions.
- Audit event emission for timeout events.

### Out of Scope
- MFA step-up flows.
- Long-lived persistent session policies.

### Assumptions
- Session management uses an injectable clock/time provider for deterministic tests.
- Audit logging is available through a testable event emitter interface.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Session expires after 15 minutes inactivity and requires re-auth | UT-073-001, UT-073-002 |
| AC-2 | Activity within timeout window extends session | UT-073-003, UT-073-004 |
| AC-3 | Expired session returns 401 Unauthorized | UT-073-005, UT-073-006 |
| AC-4 | Session timeout event is audit-logged | UT-073-007, UT-073-008 |

---

## 4. Unit Test Areas

### UT-073-001: Session expires at inactivity threshold boundary
- Advance mock clock to 15-minute inactivity mark.
- Assert session marked expired.

### UT-073-002: Requests after expiration require re-authentication
- Use expired session token/cookie fixture.
- Assert auth middleware rejects request and requires login flow.

### UT-073-003: Activity before threshold renews session expiry
- Simulate user activity within window.
- Assert expiry timestamp extends as defined by policy.

### UT-073-004: Renewal logic follows configured sliding/fixed policy mode
- Run same scenario in sliding vs fixed mode fixtures.
- Assert expiration math matches selected mode.

### UT-073-005: Expired session yields 401 status consistently
- Trigger protected endpoint call with expired session.
- Assert 401 status and standard unauthorized payload structure.

### UT-073-006: Active valid session does not produce false 401
- Use non-expired session fixture.
- Assert request continues to protected handler.

### UT-073-007: Timeout event emits audit log with required metadata
- Cause timeout event.
- Assert audit payload includes user/session/timestamp/reason fields.

### UT-073-008: Audit logger failure does not bypass session expiration enforcement
- Mock audit sink failure.
- Assert timeout still enforced and failure handled safely.

### UT-073-009: Frontend timeout handling maps 401 to re-auth UX state
- Mock 401 from protected API call.
- Assert timeout UI/re-auth path state transition.

### UT-073-010: Session timeout tests handle clock skew tolerance logic
- Provide small skew in server/client time fixtures.
- Assert no premature expiry beyond tolerated skew.

---

## 5. Test Data and Mocking Strategy

- Fixtures: active session, near-expiry session, expired session, policy modes.
- Mocks: clock provider, session store, auth middleware dependencies, audit event sink.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-073-001 through UT-073-008.

---

## 7. Suggested File Layout

- tests/unit/auth/SessionTimeoutPolicy.test.ts
- tests/unit/auth/SessionRenewalBehavior.test.ts
- tests/unit/auth/SessionUnauthorizedHandling.test.ts
- tests/unit/auth/SessionTimeoutAuditLogging.test.ts
- tests/unit/auth/__fixtures__/sessionTimeout.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-073-001 through UT-073-010 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
