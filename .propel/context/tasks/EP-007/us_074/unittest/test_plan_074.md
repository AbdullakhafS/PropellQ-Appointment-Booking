# UNIT-TEST-PLAN-074: Immutable Audit Log Infrastructure

User Story: US-074 (EP-007)
Source File: .propel/context/tasks/EP-007/us_074/us_074.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for immutable audit infrastructure, including append-only controls, 7-year retention policy behavior, tamper-evidence validation, RBAC-restricted access, and compliance evidence outputs.

---

## 2. Scope and Assumptions

### In Scope
- Append-only write model and API-level mutation block behavior.
- Retention configuration and minimum duration validation.
- Tamper-evidence/integrity check logic.
- Audit read access authorization checks.
- Compliance evidence/documentation generation.

### Out of Scope
- SIEM federation and external analytics integration.
- Live storage platform durability tests.

### Assumptions
- Audit storage access is abstracted through repositories/adapters.
- Integrity mechanism (hash chain/HMAC/signature) exposes verifiable helper APIs.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Written audit entries cannot be modified/deleted via app APIs | UT-074-001, UT-074-002 |
| AC-2 | Logs are retained for minimum 7 years | UT-074-003, UT-074-004 |
| AC-3 | Tamper evidence/integrity checks detect unauthorized changes | UT-074-005, UT-074-006 |
| AC-4 | Audit access is restricted to authorized roles | UT-074-007, UT-074-008 |
| AC-5 | Infrastructure controls and design are documented for compliance | UT-074-009, UT-074-010 |

---

## 4. Unit Test Areas

### UT-074-001: Audit repository permits append operations only
- Attempt create append entry.
- Assert append succeeds with immutable metadata.

### UT-074-002: Update/delete operations on audit entries are blocked
- Attempt update/delete via API/repository methods.
- Assert operation denied with immutable policy error.

### UT-074-003: Retention validator enforces minimum 7-year rule
- Provide policy fixtures below and above threshold.
- Assert below-threshold policy rejected.

### UT-074-004: Expiration eligibility logic excludes non-expired records
- Provide records with varied ages.
- Assert only records beyond policy become deletion candidates.

### UT-074-005: Integrity checker detects modified audit payload
- Alter payload/hash chain fixture.
- Assert integrity check fails and emits tamper signal.

### UT-074-006: Integrity checker passes unchanged append sequence
- Provide valid chain fixture.
- Assert integrity verification passes.

### UT-074-007: RBAC guard allows audit reads for authorized roles
- Mock authorized compliance/admin roles.
- Assert read access granted.

### UT-074-008: RBAC guard denies unauthorized audit access paths
- Mock unauthorized role.
- Assert forbidden result and access attempt telemetry.

### UT-074-009: Compliance evidence builder includes immutability and retention controls
- Assert generated evidence covers append-only, retention, integrity configuration.

### UT-074-010: Compliance evidence includes access-control validation artifacts
- Assert output includes role policy mapping and access verification records.

### UT-074-011: Audit storage separation validator ensures non-transactional target
- Assert configuration checks keep audit storage isolated from transactional data stores.

### UT-074-012: Error handling for audit storage failures remains fail-safe
- Mock storage failure.
- Assert no partial mutation path and clear recoverable diagnostics.

---

## 5. Test Data and Mocking Strategy

- Fixtures: append-only records, tampered records, role matrices, retention windows.
- Mocks: audit repository adapter, integrity checker, RBAC authorizer, compliance evidence exporter.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-074-001 through UT-074-010.

---

## 7. Suggested File Layout

- tests/unit/audit/ImmutableAuditRepository.test.ts
- tests/unit/audit/AuditRetentionPolicy.test.ts
- tests/unit/audit/AuditIntegrityChecks.test.ts
- tests/unit/audit/AuditAccessRbac.test.ts
- tests/unit/audit/AuditComplianceEvidence.test.ts
- tests/unit/audit/__fixtures__/immutableAudit.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-074-001 through UT-074-012 implemented.
- [ ] AC-1 through AC-5 traceability retained.
- [ ] Coverage and CI reliability targets met.
