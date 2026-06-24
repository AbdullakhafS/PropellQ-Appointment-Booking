# HIPAA Compliance Checklist

**Document ID:** CHK-HIPAA-001  
**User Story:** US-081 (EP-007)  
**Tasks:** task_081_001, task_081_002, task_081_003  
**Version:** 1.0  
**Owner:** Compliance Officer / Security Engineer  
**Status:** Active  
**Effective Date:** 2026-06-24  
**Regulatory Standard:** HIPAA Security Rule — 45 CFR Part 164, Subpart C

---

## How to Use This Checklist

**Status legend:**

| Symbol | Meaning |
|--------|---------|
| ✅ | Completed — control is implemented and evidence is available |
| 🔄 | In Progress — control is partially implemented or under review |
| ⬜ | Not Started — control has not yet been addressed |
| N/A | Not Applicable — control does not apply to PropelIQ's operating model |

**Columns:**

- **Ref** — HIPAA CFR citation
- **Control Item** — Required safeguard or specification
- **Status** — Current implementation status
- **Owner** — Accountable role
- **PropelIQ Control / Implementation** — Mapped user story, code component, or document
- **Evidence Artifact** — Where to find proof of compliance
- **Notes** — Exceptions, gaps, or next actions

---

## Part A — Administrative Safeguards (45 CFR § 164.308)

### A-1 Security Management Process (§ 164.308(a)(1))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.308(a)(1)(ii)(A) | Risk Analysis — conduct accurate and thorough assessment of potential risks to ePHI | 🔄 | Security Engineer | Security threat model maintained in architecture design | `app/API_STANDARDS_CHECKLIST.md`, architecture review | Annual review cycle due |
| § 164.308(a)(1)(ii)(B) | Risk Management — implement security measures to reduce identified risks | 🔄 | Security Engineer | RBAC (US-043–046), MFA (US-079), encryption (EP-TECH), TLS enforcement | `app/src/rbac.py`, `app/src/tls_middleware.py`, `app/src/encryption_service.py` | Risk register to be formalised |
| § 164.308(a)(1)(ii)(C) | Sanction Policy — apply appropriate sanctions for policy violations | ⬜ | Compliance Officer | Account suspension via `set_user_status(user_id, "suspended")` (US-046) | `app/src/rbac.py` — `VALID_STATUSES` | Formal sanctions policy document needed |
| § 164.308(a)(1)(ii)(D) | Information System Activity Review — regularly review audit logs and access reports | ✅ | Operations Engineer | Admin audit query interface (US-078); integrity validation (US-077) | `GET /api/admin/audit/query`, `generate_integrity_compliance_report()` in `audit_storage.py` | Weekly review recommended |

### A-2 Assigned Security Responsibility (§ 164.308(a)(2))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.308(a)(2) | Designate a security official responsible for HIPAA security programme | 🔄 | Compliance Officer | Security Engineer role defined in all policy documents (POL-DATA-001, POL-AUDIT-001, CHK-HIPAA-001) | `app/DATA_RETENTION_DELETION_POLICY.md` § 7, `app/AUDIT_RETENTION_POLICY.md` § 7 | Formal designation letter required |

### A-3 Workforce Security (§ 164.308(a)(3))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.308(a)(3)(ii)(A) | Authorisation and/or Supervision — ensure workforce has appropriate access and is supervised | ✅ | Compliance Officer | Role-based access matrix (US-043); RBAC middleware on every endpoint | `PERMISSION_MATRIX` in `app/src/rbac.py`; `ENDPOINT_PERMISSION_MAP` | Least-privilege enforced per role |
| § 164.308(a)(3)(ii)(B) | Workforce Clearance — implement procedures to determine whether access is appropriate | ✅ | Operations Engineer | `register_user()` requires explicit role assignment; role enumeration via `ROLES` tuple | `app/src/rbac.py` — `register_user()` | Admin must explicitly assign role on account creation |
| § 164.308(a)(3)(ii)(C) | Termination Procedures — procedures to terminate access upon employment end | ✅ | Operations Engineer | `set_user_status(user_id, "inactive")` or `"suspended"` immediately blocks session token issuance | `app/src/rbac.py` — `check_user_login_allowed()`; `PATCH /api/admin/users/{id}/status` | Token revocation on status change should also be verified |

### A-4 Information Access Management (§ 164.308(a)(4))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.308(a)(4)(ii)(A) | Isolating Healthcare Clearinghouse Functions — isolate PHI processing systems | N/A | — | PropelIQ is not a healthcare clearinghouse | — | Not applicable |
| § 164.308(a)(4)(ii)(B) | Access Authorisation — implement policies for granting access to ePHI | ✅ | Security Engineer | `require_permission()` middleware; `PERMISSION_MATRIX` defines access per action per role | `app/src/rbac.py` — `check_permission()`, `require_permission()` | Covers 30+ endpoints |
| § 164.308(a)(4)(ii)(C) | Access Establishment and Modification — implement policies for establishing, documenting, reviewing, modifying access | ✅ | Operations Engineer | Admin change log records every role/status change with actor, action, reason, timestamp | `app/src/rbac.py` — `_ADMIN_CHANGE_LOG`, `record_admin_event()`; `GET /api/admin/users/change-log` | US-046 (task_046_002) |

### A-5 Security Awareness and Training (§ 164.308(a)(5))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.308(a)(5)(ii)(A) | Security Reminders — periodic security updates and reminders | ⬜ | Compliance Officer | Not yet implemented | — | Recurring training schedule to be defined |
| § 164.308(a)(5)(ii)(B) | Protection from Malicious Software — train workforce on identifying and reporting malware | ⬜ | Operations Engineer | Not yet implemented | — | Requires organisational training programme |
| § 164.308(a)(5)(ii)(C) | Log-in Monitoring — train users to report login discrepancies | ✅ | Security Engineer | Login failure events (`LOG_LOGIN_FAILURE`) logged and queryable via audit interface | `app/src/audit_events.py` — `log_login_failure()`; `GET /api/admin/audit/query?event=LOGIN_FAILURE` | US-075 |
| § 164.308(a)(5)(ii)(D) | Password Management — create, change, safeguard passwords | ✅ | Security Engineer | bcrypt cost=12 (US-072); password reset flow with rate limiting (US-049); min 8-char policy | `app/src/rbac.py` — `BCRYPT_COST_FACTOR = 12`, `_hash_password()`, `_check_password_policy()` | Legacy PBKDF2 migration path also in place |

### A-6 Security Incident Procedures (§ 164.308(a)(6))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.308(a)(6)(ii) | Response and Reporting — identify, respond to, document, and mitigate security incidents | ✅ | Security Engineer | `INTEGRITY_VALIDATION_FAILURE` events trigger alerting; login failure events audited; incident runbook documented | `app/src/audit_storage.py` — `AuditIntegrityValidationJob._emit_failure_event()`; `app/INCIDENT_INVESTIGATION_RUNBOOK.md` | US-077; incident runbook reviewed annually |

### A-7 Contingency Plan (§ 164.308(a)(7))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.308(a)(7)(ii)(A) | Data Backup Plan — create exact copies of ePHI | ✅ | Operations Engineer | Automated database backup (`backup_automation.py`); backup schema (`backup_schema.sql`) | `app/db/backup_runbook.md`; `app/src/backup_automation.py`; `app/db/backup.py` | Backup retention ≥ 7 years (POL-DATA-001 § 5.3) |
| § 164.308(a)(7)(ii)(B) | Disaster Recovery Plan — restore ePHI after emergency | ✅ | Operations Engineer | Restore verification (`restore_verification.py`); migration pipeline | `app/src/restore_verification.py`; `app/db/migration_runbook.md` | Recovery SLA to be documented |
| § 164.308(a)(7)(ii)(C) | Emergency Mode Operation Plan — continue business processes protecting ePHI during emergency | 🔄 | Operations Engineer | Read-only fallback patterns in WSGI app; admin bypass paths in RBAC | `app/src/web_app.py`; `app/src/rbac.py` | Formal emergency mode runbook needed |
| § 164.308(a)(7)(ii)(D) | Testing and Revision — test and revise contingency plans | 🔄 | Operations Engineer | `qa_test_suite.py` covers DB integrity; restore verification tested | `app/db/qa_test_suite.py`; `app/src/restore_verification.py` | Scheduled DR test cadence to be established |
| § 164.308(a)(7)(ii)(E) | Applications and Data Criticality Analysis — assess criticality of specific applications and data | 🔄 | Compliance Officer | Data model and architecture review package document criticality | `app/db/DATA_MODEL.md`; `app/db/ARCHITECTURE_REVIEW_PACKAGE.md` | Formal BIA document to be completed |

### A-8 Evaluation (§ 164.308(a)(8))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.308(a)(8) | Periodic technical and non-technical evaluation of security controls | 🔄 | Compliance Officer / Security Engineer | API standards checklist (US-098); code review process; tracing and observability | `app/API_STANDARDS_CHECKLIST.md`; `app/TRACING_IMPLEMENTATION_GUIDE.md`; `app/LOGGING_GOVERNANCE.md` | Annual evaluation schedule to be formalised |

### A-9 Business Associate Contracts (§ 164.308(b)(1))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.308(b)(1) | Business Associate Contracts — obtain satisfactory assurances from business associates | ✅ | Compliance Officer | Vendor BAA process, due diligence checklist, BAA template, and vendor register (US-082) | `app/VENDOR_BAA_PROCESS.md` — POL-BAA-001 | PHI access must be gated on BAA status in vendor register |

---

## Part B — Physical Safeguards (45 CFR § 164.310)

### B-1 Facility Access Controls (§ 164.310(a))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.310(a)(2)(i) | Contingency Operations — facility access during emergency | 🔄 | Operations Engineer | Cloud-hosted infrastructure enables remote access continuity | Infrastructure provider SLA | Formalise runbook for emergency cloud access |
| § 164.310(a)(2)(ii) | Facility Security Plan — physical security of facilities housing ePHI systems | 🔄 | Operations Engineer | Cloud data centres provide physical security (provider responsibility) | Cloud provider SOC 2 / ISO 27001 reports | Obtain and retain provider compliance attestations |
| § 164.310(a)(2)(iii) | Access Control and Validation — control access to facilities based on role | 🔄 | Operations Engineer | Cloud IAM controls access to production infrastructure | Cloud provider IAM policy | Map to PropelIQ admin roles |
| § 164.310(a)(2)(iv) | Maintenance Records — document repairs and modifications to physical components | ⬜ | Operations Engineer | Not yet implemented | — | Use infrastructure change log in CI/CD pipeline |

### B-2 Workstation Use (§ 164.310(b))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.310(b) | Define appropriate functions for workstations accessing ePHI and physical attributes of surroundings | ⬜ | Compliance Officer | Not yet implemented | — | Workstation use policy to be drafted |

### B-3 Workstation Security (§ 164.310(c))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.310(c) | Physical safeguards for workstations that access ePHI | ⬜ | Operations Engineer | Not yet implemented | — | Endpoint management (MDM/EDR) to be deployed |

### B-4 Device and Media Controls (§ 164.310(d))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.310(d)(2)(i) | Disposal — policies and procedures for final disposal of ePHI on hardware or media | ⬜ | Operations Engineer | Not yet implemented | — | Media disposal SOP required |
| § 164.310(d)(2)(ii) | Media Re-Use — remove ePHI before media reuse | ⬜ | Operations Engineer | Not yet implemented | — | Secure wipe procedure required |
| § 164.310(d)(2)(iii) | Accountability — maintain records of media movements | ⬜ | Operations Engineer | Not yet implemented | — | Asset inventory to be established |
| § 164.310(d)(2)(iv) | Data Backup and Storage — create backup copies before moving hardware | ✅ | Operations Engineer | Automated backup prior to any infrastructure change | `app/db/backup_runbook.md`; `app/src/backup_automation.py` | Backup integrity verified by `restore_verification.py` |

---

## Part C — Technical Safeguards (45 CFR § 164.312)

### C-1 Access Control (§ 164.312(a))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.312(a)(2)(i) | Unique User Identification — assign unique name/number for identifying and tracking user identity | ✅ | Security Engineer | `user_id` is the unique opaque identifier assigned at registration; JTI in session tokens provides per-session uniqueness | `app/src/rbac.py` — `register_user()`, `_USER_REGISTRY`; `issue_session_token()` with UUID JTI | US-043, US-051 |
| § 164.312(a)(2)(ii) | Emergency Access Procedure — obtain ePHI during emergency | 🔄 | Operations Engineer | Admin role has unrestricted audit/user management access; RBAC admin bypass paths documented | `app/src/rbac.py` — `PERMISSION_MATRIX` admin entries | Formal emergency access SOP needed |
| § 164.312(a)(2)(iii) | Automatic Logoff — implement electronic procedures to terminate sessions after inactivity | ✅ | Security Engineer | 15-minute inactivity timeout enforced on every token validation; tokens revoked on logout | `app/src/rbac.py` — `SESSION_INACTIVITY_TIMEOUT_SECONDS = 900`; `validate_session_token()` | US-073 |
| § 164.312(a)(2)(iv) | Encryption and Decryption — implement mechanism to encrypt and decrypt ePHI | ✅ | Security Engineer | AES-256-GCM encryption engine for at-rest PHI (`EncryptionEngine`); TLS 1.2+ minimum for in-transit data | `app/src/encryption_service.py`; `app/src/tls_middleware.py` — `TLSConfig.min_tls_version = "TLSv1.2"` | Key rotation via `rotate_key()` |

### C-2 Audit Controls (§ 164.312(b))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.312(b) | Implement hardware, software, and/or procedural mechanisms to record and examine activity in information systems containing ePHI | ✅ | Security Engineer | Append-only audit store; structured event schema; PHI excluded from log fields; HMAC integrity chain; 7-year retention; admin query interface | `app/src/audit_storage.py` — `AppendOnlyAuditStore`; `app/src/audit_events.py`; `app/AUDIT_RETENTION_POLICY.md` | US-074, US-075, US-076, US-077, US-078 |

### C-3 Integrity (§ 164.312(c))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.312(c)(1) | Integrity Controls — implement policies and procedures to protect ePHI from improper alteration or destruction | ✅ | Security Engineer | HMAC-SHA256 hash chain across all audit entries; `AuditImmutabilityError` blocks any delete/update on active records | `app/src/audit_storage.py` — `AuditIntegrityChecker`, `AuditIntegrityValidationJob`, `INTEGRITY_ALGORITHM = "HMAC-SHA256"` | US-077; chain verified by `run()` job |
| § 164.312(c)(2) | Transmission Integrity — implement security measures to ensure ePHI is not improperly modified during transmission | ✅ | Security Engineer | TLS with AEAD cipher suites (AES-GCM, ChaCha20-Poly1305) provides transmission integrity; weak protocols blocked | `app/src/tls_middleware.py` — `STRONG_CIPHERS_TLS12`; `WEAK_PROTOCOL_VERSIONS` blocked | EP-TECH |

### C-4 Person or Entity Authentication (§ 164.312(d))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.312(d) | Implement procedures to verify that a person or entity seeking access to ePHI is the one claimed | ✅ | Security Engineer | bcrypt password verification (US-072); TOTP MFA for staff and admin (US-079); RBAC role verification on every request | `app/src/rbac.py` — `verify_user_password()`, `BCRYPT_COST_FACTOR = 12`; `app/src/mfa_service.py` — `MfaEnrollmentService`, `MfaPolicyEnforcer` | MFA required for `staff` and `admin` roles |

### C-5 Transmission Security (§ 164.312(e))

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.312(e)(2)(i) | Integrity Controls — guard against unauthorised access to ePHI transmitted over network | ✅ | Security Engineer | TLS 1.2+ with AEAD ciphers; HTTP → HTTPS redirect enforced by `TLSEnforcementMiddleware` | `app/src/tls_middleware.py` — `TLSEnforcementMiddleware`; `WEAK_CIPHER_PATTERNS` blocked | EP-TECH |
| § 164.312(e)(2)(ii) | Encryption — implement mechanism to encrypt ePHI in transit | ✅ | Security Engineer | HTTPS enforced for all endpoints; TLS minimum 1.2; strong cipher suite list (`ECDHE-*-AES256-GCM-*`, `ECDHE-*-CHACHA20-POLY1305`) | `app/src/tls_middleware.py` — `TLSConfig`, `STRONG_CIPHERS_TLS12` | Weak protocols SSLv2, SSLv3, TLSv1.0, TLSv1.1 blocked |

---

## Part D — Breach Notification Requirements (45 CFR § 164.400–164.414)

| Ref | Control Item | Status | Owner | PropelIQ Control / Implementation | Evidence Artifact | Notes |
|-----|-------------|--------|-------|-----------------------------------|-------------------|-------|
| § 164.404 | Notify individuals of breach affecting their unsecured PHI within 60 days | 🔄 | Compliance Officer | Incident runbook covers breach identification; notification workflow not yet formalised | `app/INCIDENT_INVESTIGATION_RUNBOOK.md` | Patient notification SOP to be written |
| § 164.406 | Notify media for breaches affecting > 500 individuals in a state/jurisdiction | ⬜ | Compliance Officer | Not yet implemented | — | Requires legal counsel input |
| § 164.408 | Notify HHS Secretary of breaches annually (< 500) or within 60 days (≥ 500) | ⬜ | Compliance Officer | Not yet implemented | — | Register for HHS breach portal |
| § 164.412 | Notify business associates of breach discovery | 🔄 | Compliance Officer | BAA template clause 4 defines vendor breach notification obligations to PropelIQ; PropelIQ → BA notification SOP still needed | `app/VENDOR_BAA_PROCESS.md` § 4, § 5.3 | Notification SOP to be added to incident runbook |

---

## Part E — Compliance Summary

### E-1 Coverage Statistics

| Category | Total Items | ✅ Completed | 🔄 In Progress | ⬜ Not Started | N/A |
|----------|-------------|-------------|----------------|----------------|-----|
| Administrative Safeguards | 19 | 10 | 6 | 2 | 1 |
| Physical Safeguards | 8 | 1 | 3 | 4 | 0 |
| Technical Safeguards | 8 | 7 | 1 | 0 | 0 |
| Breach Notification | 4 | 0 | 1 | 3 | 0 |
| **Total** | **39** | **17** | **11** | **10** | **1** |

### E-2 Implemented Controls — User Story Traceability

| User Story | Title | HIPAA Safeguard Areas Addressed |
|------------|-------|--------------------------------|
| US-043 | RBAC Permission Matrix | § 164.308(a)(3)(ii)(A), § 164.308(a)(4)(ii)(B), § 164.312(a)(2)(i) |
| US-044 | Patient Ownership Filtering | § 164.308(a)(4)(ii)(B) — minimum necessary access |
| US-045 | Staff Queue Access (assignment scoping) | § 164.308(a)(4)(ii)(B) — workforce minimum necessary |
| US-046 | Admin-Only Management Endpoints | § 164.308(a)(3)(ii)(C), § 164.308(a)(4)(ii)(C) |
| US-049 | Password Reset Flow | § 164.308(a)(5)(ii)(D) — password management |
| US-051 | Session Token Issuance | § 164.312(a)(2)(i) — unique user identification |
| US-072 | Bcrypt Password Hashing | § 164.312(d) — person authentication |
| US-073 | Session Renewal / Inactivity Timeout | § 164.312(a)(2)(iii) — automatic logoff |
| US-074 | Audit Log Foundation | § 164.312(b) — audit controls |
| US-075 | Audit Event Schema (PHI exclusion) | § 164.312(b), § 164.308(a)(5)(ii)(C) |
| US-076 | Audit Log Retention (7 years) | § 164.308(a)(7)(ii)(A), § 164.312(b) |
| US-077 | Log Integrity Checking (HMAC-SHA256) | § 164.312(c)(1), § 164.308(a)(6)(ii) |
| US-078 | Admin Audit Query Interface | § 164.308(a)(1)(ii)(D) — activity review |
| US-079 | MFA Support (TOTP) | § 164.312(d) — person authentication |
| US-080 | Data Retention & Deletion Policy | § 164.308(a)(7)(ii)(A), § 164.310(d)(2)(iv) |

### E-3 Open Gaps and Remediation Actions

| Gap ID | Description | Priority | Owner | Target Date |
|--------|-------------|----------|-------|-------------|
| GAP-001 | Formal risk analysis and risk register document | HIGH | Security Engineer | Next sprint |
| GAP-002 | Sanctions policy document | HIGH | Compliance Officer | Next sprint |
| GAP-003 | Designated security official formal designation letter | HIGH | Compliance Officer | Immediate |
| ~~GAP-004~~ | ~~Business Associate Agreement template~~ | ~~HIGH~~ | ~~Legal Counsel~~ | ✅ Resolved by US-082 — POL-BAA-001 (`app/VENDOR_BAA_PROCESS.md`) |
| GAP-005 | Security awareness and training programme | MEDIUM | Compliance Officer | 30 days |
| GAP-006 | Emergency mode operation plan and DR runbook | MEDIUM | Operations Engineer | 30 days |
| GAP-007 | Workstation use and security policy | MEDIUM | Compliance Officer | 60 days |
| GAP-008 | Device and media disposal and re-use SOPs | MEDIUM | Operations Engineer | 60 days |
| GAP-009 | Patient breach notification SOP | HIGH | Compliance Officer | Before go-live |
| GAP-010 | HHS breach portal registration | HIGH | Compliance Officer | Before go-live |

---

## Part F — Revision History

Checklist revisions require review and approval before publication. All versions are stored in version control.

| Version | Date | Author | Change Summary | Reviewed By |
|---------|------|--------|----------------|-------------|
| 1.0 | 2026-06-24 | Compliance Officer | Initial checklist — covers all HIPAA Security Rule safeguard categories, mapped to PropelIQ US-043 through US-080 controls. Implements US-081 task_081_001, task_081_002, task_081_003. | Compliance Officer |

---

## Part G — Related Documents

| Document | Location | Relationship |
|----------|----------|--------------|
| POL-DATA-001: Data Retention and Deletion Policy | `app/DATA_RETENTION_DELETION_POLICY.md` | Governs retention and deletion — supports § 164.308(a)(7) and § 164.312(b) items |
| POL-BAA-001: Vendor BAA Process | `app/VENDOR_BAA_PROCESS.md` | Vendor due diligence, BAA template, and ongoing review controls — resolves § 164.308(b)(1) and GAP-004 |
| POL-AUDIT-001: Audit Log Retention and Archival Policy | `app/AUDIT_RETENTION_POLICY.md` | Technical detail for audit log lifecycle — supports § 164.312(b) and § 164.308(a)(1)(ii)(D) |
| Incident Investigation Runbook | `app/INCIDENT_INVESTIGATION_RUNBOOK.md` | Supports § 164.308(a)(6)(ii) security incident response |
| API Standards Checklist | `app/API_STANDARDS_CHECKLIST.md` | Technical security review artifact for § 164.308(a)(8) evaluation |
| Backup Runbook | `app/db/backup_runbook.md` | Operational procedures for § 164.308(a)(7)(ii)(A)–(B) contingency |
| Logging Governance | `app/LOGGING_GOVERNANCE.md` | Supports § 164.312(b) audit controls |
| Data Model | `app/db/DATA_MODEL.md` | PHI data category reference for scope definition |
