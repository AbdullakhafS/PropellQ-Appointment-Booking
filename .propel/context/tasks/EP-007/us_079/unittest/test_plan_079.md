# UNIT-TEST-PLAN-079: MFA Support (TOTP)

User Story: US-079 (EP-007)
Source File: .propel/context/tasks/EP-007/us_079/us_079.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for TOTP MFA enrollment and verification, backup/recovery controls, and role-based policy enforcement for Staff/Admin users.

---

## 2. Scope and Assumptions

### In Scope
- TOTP enrollment instruction generation.
- TOTP code verification on login.
- Invalid-code rejection behavior.
- Backup code single-use lifecycle handling.
- Policy enforcement blocking login when MFA setup is required.

### Out of Scope
- Biometric/passwordless authentication.
- MFA rollout for patient self-service accounts.

### Assumptions
- TOTP generation/verification uses standard RFC-compatible library wrappers.
- Role policy and enrollment state are available via auth service adapters.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Staff/Admin enrollment provides TOTP setup instructions | UT-079-001, UT-079-002 |
| AC-2 | Valid TOTP code allows login | UT-079-003, UT-079-004 |
| AC-3 | Invalid TOTP code rejects login with clear error | UT-079-005, UT-079-006 |
| AC-4 | Backup codes are single-use and securely managed | UT-079-007, UT-079-008 |
| AC-5 | Required MFA policy blocks login until setup complete | UT-079-009, UT-079-010 |

---

## 4. Unit Test Areas

### UT-079-001: Enrollment flow generates role-eligible TOTP setup payload
- Mock Staff/Admin user and unenrolled state.
- Assert provisioning data/instructions are produced.

### UT-079-002: Non-eligible role bypasses enrollment requirement in phase scope
- Mock out-of-scope role.
- Assert policy does not force TOTP enrollment.

### UT-079-003: Valid TOTP verification returns success token/continuation state
- Provide valid code fixture.
- Assert login continuation is granted.

### UT-079-004: TOTP verification handles allowed drift window correctly
- Provide boundary-time codes.
- Assert acceptable skew behavior.

### UT-079-005: Invalid TOTP code returns rejection status
- Provide invalid code.
- Assert authentication denied.

### UT-079-006: Invalid code response includes clear non-sensitive error reason
- Assert error message is user-actionable without disclosing secret internals.

### UT-079-007: Backup code redemption marks code as consumed
- Redeem valid backup code.
- Assert single-use state transition occurs.

### UT-079-008: Reuse attempt of consumed backup code is denied
- Attempt second use of same code.
- Assert rejection and security event.

### UT-079-009: Required-role user cannot complete login without MFA setup
- Mock required role with unenrolled status.
- Assert login blocked and enrollment step required.

### UT-079-010: Required-role user with completed MFA setup can proceed
- Mock required role enrolled status.
- Assert policy gate passes with completed MFA verification.

### UT-079-011: Recovery flow enforces secure approval/check criteria
- Simulate lost-device recovery initiation.
- Assert required verification flags and restricted path.

### UT-079-012: MFA secrets are excluded from logs and outward responses
- Assert serialization/logging helpers redact secret material.

---

## 5. Test Data and Mocking Strategy

- Fixtures: role-policy matrix, enrolled/unenrolled users, valid/invalid/boundary TOTP codes, backup code states.
- Mocks: TOTP provider, auth policy engine, backup code store, recovery workflow service.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-079-001 through UT-079-010.

---

## 7. Suggested File Layout

- tests/unit/auth/MfaEnrollmentFlow.test.ts
- tests/unit/auth/MfaTotpVerification.test.ts
- tests/unit/auth/MfaBackupCodeLifecycle.test.ts
- tests/unit/auth/MfaPolicyEnforcement.test.ts
- tests/unit/auth/__fixtures__/mfa.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-079-001 through UT-079-012 implemented.
- [ ] AC-1 through AC-5 traceability retained.
- [ ] Coverage and CI reliability targets met.
