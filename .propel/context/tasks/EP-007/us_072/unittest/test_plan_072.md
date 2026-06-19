# UNIT-TEST-PLAN-072: Bcrypt Password Hashing

User Story: US-072 (EP-007)
Source File: .propel/context/tasks/EP-007/us_072/us_072.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for bcrypt password security controls, including hashing on credential writes, bcrypt verification on login, legacy-hash migration behavior, cost-factor policy compliance, and prevention of raw-password logging.

---

## 2. Scope and Assumptions

### In Scope
- Bcrypt policy validation (cost factor and storage rules).
- Password create/reset write paths hashing behavior.
- Login verification via bcrypt compare.
- Legacy hash migration handling/documented fallback behavior.
- Log and telemetry redaction controls for raw credentials.

### Out of Scope
- Passwordless authentication implementations.
- External IdP password storage internals.

### Assumptions
- Auth service uses a hash adapter abstraction that can be mocked.
- Legacy-hash detection and migration logic are encapsulated in testable helper/service modules.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Created/reset passwords are hashed with bcrypt before storage | UT-072-001, UT-072-002 |
| AC-2 | Login validation uses bcrypt compare | UT-072-003, UT-072-004 |
| AC-3 | Legacy password format migration plan is documented/executed | UT-072-005, UT-072-006 |
| AC-4 | Bcrypt cost-factor parameters are reviewed for adequacy | UT-072-007, UT-072-008 |

---

## 4. Unit Test Areas

### UT-072-001: Credential create path hashes password before persistence
- Mock create-user flow with plaintext input.
- Assert bcrypt hash function is called before repository write.
- Assert repository receives hash output, not plaintext.

### UT-072-002: Password reset path hashes updated password before storage
- Trigger reset flow.
- Assert reset persistence contains only bcrypt hash material.

### UT-072-003: Login verification delegates to bcrypt compare for stored hash
- Mock stored bcrypt hash and valid plaintext login input.
- Assert compare function is invoked with expected values.

### UT-072-004: Invalid password compare fails safely with generic auth error
- Provide invalid password fixture.
- Assert authentication rejected without credential detail leakage.

### UT-072-005: Legacy hash detector identifies non-bcrypt records for migration path
- Provide legacy-format hash fixtures.
- Assert detector flags migration-required records.

### UT-072-006: Legacy migration flow upgrades hash to bcrypt on successful auth (if enabled)
- Simulate successful auth against legacy path.
- Assert migrated bcrypt hash write/update behavior occurs.

### UT-072-007: Bcrypt policy validator enforces minimum cost factor threshold
- Provide policy fixtures below/at/above threshold (for example 10/12/14).
- Assert below-threshold values are rejected.

### UT-072-008: Hashing configuration review output includes cost factor and policy metadata
- Assert security-review artifact contains configured rounds/cost settings.

### UT-072-009: Raw password values are redacted/excluded from logs and telemetry
- Simulate auth flow logs.
- Assert no plaintext credential appears in emitted messages.

### UT-072-010: Error handling in hash/compare failures remains non-sensitive and recoverable
- Mock hash or compare exception.
- Assert failure path returns safe diagnostics and does not leak secrets.

### UT-072-011: Hash storage validator rejects non-bcrypt hash formats on write path
- Attempt persistence with invalid hash format fixture.
- Assert validation failure.

### UT-072-012: Deterministic policy compliance check for environment-specific cost config
- Evaluate dev/stage/prod policy fixtures.
- Assert environment policy mapping is explicit and compliant.

---

## 5. Test Data and Mocking Strategy

- Fixtures: plaintext credentials, valid bcrypt hashes, legacy hash formats, policy configs by environment.
- Mocks: bcrypt adapter (hash/compare), auth repository, migration helper, logger/telemetry sink.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-072-001 through UT-072-008.

---

## 7. Suggested File Layout

- tests/unit/auth/PasswordHashWritePaths.test.ts
- tests/unit/auth/BcryptLoginVerification.test.ts
- tests/unit/auth/LegacyHashMigration.test.ts
- tests/unit/auth/BcryptPolicyValidation.test.ts
- tests/unit/auth/PasswordLogSafety.test.ts
- tests/unit/auth/__fixtures__/bcrypt.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-072-001 through UT-072-012 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
