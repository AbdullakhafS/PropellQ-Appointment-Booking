# UNIT-TEST-PLAN-071: TLS 1.2+ for API Traffic

User Story: US-071 (EP-007)
Source File: .propel/context/tasks/EP-007/us_071/us_071.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for transport security controls, including HTTPS enforcement, TLS version/cipher policy, certificate lifecycle handling, and audit documentation outputs.

---

## 2. Scope and Assumptions

### In Scope
- HTTP-to-HTTPS redirect/reject policy logic.
- TLS minimum version and cipher policy validators.
- Secure-header/cookie policy checks where applicable.
- Certificate renewal and expiration monitoring logic.
- TLS posture evidence/documentation output.

### Out of Scope
- End-to-end network handshake tests against live infrastructure.
- mTLS partner integration flows.

### Assumptions
- Gateway/API ingress configuration is represented by testable config objects.
- Certificate lifecycle actions are abstracted via providers/clients.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | HTTP requests redirect/reject in favor of HTTPS | UT-071-001, UT-071-002 |
| AC-2 | TLS negotiates 1.2 or higher only | UT-071-003, UT-071-004 |
| AC-3 | Weak ciphers/protocols are disabled | UT-071-005, UT-071-006 |
| AC-4 | Certificate renewal occurs before expiration without downtime | UT-071-007, UT-071-008 |
| AC-5 | TLS and certificate management are documented for audit | UT-071-009, UT-071-010 |

---

## 4. Unit Test Areas

### UT-071-001: HTTP request handler issues redirect/reject per policy
- Mock inbound HTTP request.
- Assert expected redirect status or explicit rejection behavior.

### UT-071-002: HTTPS-preferred policy applies consistently across routes
- Provide multiple endpoint route fixtures.
- Assert policy middleware behavior is route-consistent.

### UT-071-003: TLS config validator accepts only 1.2+
- Provide valid 1.2/1.3 configs.
- Assert validator passes approved versions.

### UT-071-004: TLS validator rejects 1.1/1.0 and invalid protocol sets
- Provide weak protocol fixtures.
- Assert startup/config validation fails with clear reasons.

### UT-071-005: Cipher-suite policy excludes weak ciphers
- Mock cipher list including weak suites.
- Assert weak entries are stripped/rejected.

### UT-071-006: HSTS and secure-cookie policy flags are enforced
- Assert generated security headers/cookie flags include secure defaults.

### UT-071-007: Renewal scheduler triggers before certificate expiry threshold
- Mock certificate nearing expiry.
- Assert renewal workflow dispatches before hard expiry.

### UT-071-008: Renewal failure path emits alert and preserves current cert state safely
- Mock renewal failure.
- Assert monitoring/alert event and no invalid cert swap.

### UT-071-009: TLS evidence builder outputs protocol/cipher posture summary
- Assert evidence includes min TLS version and disabled protocol/cipher listing.

### UT-071-010: Documentation output includes cert lifecycle and renewal proof metadata
- Assert audit export includes expiry window, renewal action, and timestamped records.

### UT-071-011: Certificate monitoring computes correct days-to-expiry thresholds
- Provide boundary-date fixtures.
- Assert warning/critical threshold behavior.

### UT-071-012: Error messages avoid leaking sensitive certificate material
- Assert diagnostics include identifiers only, not private key content.

---

## 5. Test Data and Mocking Strategy

- Fixtures: protocol/cipher policy sets, certificate states (healthy/expiring/expired), header policies.
- Mocks: ingress config provider, certificate manager client, monitoring event sink.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-071-001 through UT-071-010.

---

## 7. Suggested File Layout

- tests/unit/security/HttpsEnforcementPolicy.test.ts
- tests/unit/security/TlsVersionCipherValidator.test.ts
- tests/unit/security/TlsSecurityHeaders.test.ts
- tests/unit/security/CertificateRenewalScheduler.test.ts
- tests/unit/security/TlsComplianceEvidence.test.ts
- tests/unit/security/__fixtures__/tls.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-071-001 through UT-071-012 implemented.
- [ ] AC-1 through AC-5 traceability retained.
- [ ] Coverage and CI reliability targets met.
