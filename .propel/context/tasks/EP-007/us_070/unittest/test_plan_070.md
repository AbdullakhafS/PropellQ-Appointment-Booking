# UNIT-TEST-PLAN-070: AES-256 Database Encryption

User Story: US-070 (EP-007)
Source File: .propel/context/tasks/EP-007/us_070/us_070.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for AES-256 encryption-at-rest controls across PHI stores, audit logs, backups, key management integration, and compliance evidence generation.

---

## 2. Scope and Assumptions

### In Scope
- Encryption policy/config selection logic for in-scope stores.
- Storage encryption enablement checks for PHI and audit logs.
- Backup encryption verification logic.
- Key store integration and rotation workflow behavior.
- Evidence/metadata generation for compliance review.

### Out of Scope
- End-to-end infrastructure provisioning tests.
- TLS payload encryption behavior.
- Live key vault performance benchmarking.

### Assumptions
- Encryption status and key management are exposed through service adapters that are mockable.
- Backup verification exposes deterministic encryption metadata.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | PHI data at rest is AES-256 encrypted | UT-070-001, UT-070-002 |
| AC-2 | Audit logs at rest are AES-256 encrypted | UT-070-003, UT-070-004 |
| AC-3 | Backups remain encrypted | UT-070-005, UT-070-006 |
| AC-4 | Encryption keys are managed by secure key store | UT-070-007, UT-070-008 |
| AC-5 | Compliance evidence is available | UT-070-009, UT-070-010 |

---

## 4. Unit Test Areas

### UT-070-001: PHI store encryption policy resolves to AES-256
- Mock PHI store config inputs.
- Assert selected algorithm and mode match required AES-256 profile.

### UT-070-002: Unencrypted/weak storage path is rejected by validator
- Provide weak or missing encryption config.
- Assert validation failure and explicit remediation message.

### UT-070-003: Audit log storage adapter enforces encrypted-at-rest flag
- Mock audit storage config.
- Assert encryption enforcement flag is true and immutable.

### UT-070-004: Audit log write path blocks noncompliant storage targets
- Attempt write to noncompliant target in test double.
- Assert write is denied with policy violation error.

### UT-070-005: Backup artifact metadata indicates encrypted state
- Mock backup metadata payload.
- Assert encryption marker/algorithm fields are present and valid.

### UT-070-006: Backup verification fails on plaintext backup artifact
- Mock backup with missing encryption marker.
- Assert verification failure and alertable status output.

### UT-070-007: Key retrieval uses external key store adapter only
- Assert key acquisition path calls secure key store adapter.
- Assert local/static key source paths are not used.

### UT-070-008: Key rotation workflow updates key reference safely
- Simulate rotation event.
- Assert new key version is adopted without decryptability regressions in adapter contract.

### UT-070-009: Compliance evidence generator includes encryption controls
- Assert output includes PHI stores, audit logs, and backup encryption verification records.

### UT-070-010: Evidence generator includes key-management proof fields
- Assert evidence includes key source, version/rotation metadata, and timestamps.

### UT-070-011: Encryption metadata is stored separately from encrypted payload references
- Assert metadata mapping avoids storing sensitive key material with data payload.

### UT-070-012: Error handling returns non-sensitive diagnostics
- Assert failures omit sensitive key values while preserving actionable error context.

---

## 5. Test Data and Mocking Strategy

- Fixtures: compliant AES-256 configs, weak/noncompliant configs, encrypted/plain backups.
- Mocks: key store adapter, storage encryption status provider, compliance evidence formatter.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-070-001 through UT-070-010.

---

## 7. Suggested File Layout

- tests/unit/security/EncryptionPolicyResolver.test.ts
- tests/unit/security/EncryptionComplianceValidator.test.ts
- tests/unit/security/BackupEncryptionVerifier.test.ts
- tests/unit/security/KeyStoreIntegration.test.ts
- tests/unit/security/EncryptionEvidenceBuilder.test.ts
- tests/unit/security/__fixtures__/encryption.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-070-001 through UT-070-012 implemented.
- [ ] AC-1 through AC-5 traceability retained.
- [ ] Coverage and CI reliability targets met.
