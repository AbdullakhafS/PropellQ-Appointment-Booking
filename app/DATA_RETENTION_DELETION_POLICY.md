# Data Retention and Deletion Policy

**Document ID:** POL-DATA-001  
**User Story:** US-080 (EP-007)  
**Tasks:** task_080_001, task_080_002, task_080_003  
**Version:** 1.0  
**Owner:** Compliance Officer / Security Engineer  
**Status:** Approved  
**Effective Date:** 2026-06-24  
**Regulatory References:** HIPAA 45 CFR § 164.530(j), 45 CFR § 164.524, 45 CFR § 164.526

---

## 1. Purpose

This policy establishes retention periods, deletion criteria, and approval controls for all Protected Health Information (PHI) and system audit logs managed by the PropelIQ Appointment Booking platform. It ensures the organisation:

- Retains data for the minimum period required by applicable law and regulation.
- Does not retain data beyond its authorised purpose without documented justification.
- Applies consistent, auditable controls before any permanent deletion is executed.
- Maintains evidence of policy compliance for HIPAA audit readiness.

This document is the umbrella data governance policy. For audit-log-specific technical controls, see [POL-AUDIT-001: Audit Log Retention and Archival Policy](AUDIT_RETENTION_POLICY.md).

---

## 2. Scope

This policy applies to:

| Data Category | Storage Location | Contains PHI |
|---------------|-----------------|--------------|
| Patient profiles | `patient_profiles` table | Yes |
| Appointment records | `appointments` table | Yes |
| Clinical documents (uploaded files) | `clinical_documents` table + `documents/` storage path | Yes |
| Clinical document processing records | `clinical_document_processing` table | Indirect |
| Appointment confirmation artefacts | `generated/confirmations/` directory | Yes |
| Audit log entries | `AppendOnlyAuditStore` (in-memory + archive tier) | No (PHI excluded by schema) |
| Admin change log | `_ADMIN_CHANGE_LOG` in-memory store | No |
| Session tokens | `_SESSION_STORE` (transient, in-memory) | No |
| Password reset tokens | `_RESET_TOKEN_STORE` (transient, in-memory) | No |
| MFA enrollment records | `MfaEnrollmentStore` (in-memory) | No |
| Backup codes (hashed) | `MfaBackupCodeStore` (in-memory) | No |

Out of scope: infrastructure logs, CI/CD artefacts, and backups managed by the cloud provider — those are governed by the infrastructure security policy.

---

## 3. Retention Periods by Data Category

### 3.1 Protected Health Information (PHI)

PHI must be retained for the minimum period required by HIPAA and applicable state law. PropelIQ adopts a **7-year minimum** (matching the audit log standard) to simplify lifecycle operations and satisfy the most restrictive state-level requirements.

| Data Category | Minimum Retention | Maximum Retention | Rationale |
|---------------|-------------------|-------------------|-----------|
| Patient profiles | 7 years from last appointment | 10 years | HIPAA + state mandate |
| Appointment records | 7 years from appointment date | 10 years | HIPAA 45 CFR § 164.530(j) |
| Clinical documents | 7 years from upload date | 10 years | Clinical record requirements |
| Clinical processing records | 7 years from creation date | 10 years | Linked to parent document |
| Appointment confirmation artefacts | 7 years from generation date | 10 years | Transactional audit evidence |

- **Minimum:** No record may be deleted before the minimum retention period has elapsed.
- **Maximum:** Records held beyond 10 years require documented justification (e.g. ongoing litigation hold, active patient relationship). Retention beyond 10 years is reviewed annually.
- **Litigation holds:** Any record subject to a litigation hold is excluded from routine lifecycle operations until the hold is lifted in writing by Legal Counsel.

### 3.2 Audit Log Records

Audit logs are governed by [POL-AUDIT-001](AUDIT_RETENTION_POLICY.md). Key parameters:

| Parameter | Value | Enforcement |
|-----------|-------|-------------|
| Minimum retention | 7 years (2 555 days) | `AUDIT_RETENTION_DAYS = 2555` in `audit_storage.py` |
| Active tier duration | 0 – 7 years | `AppendOnlyAuditStore` (hot storage) |
| Archive tier | After 7 years, indefinitely until approved deletion | `AuditArchiveTier` (cold storage) |
| Deletion eligibility | > 7 years old **and** in archive tier **and** approved | `AuditRetentionPolicy.is_eligible_for_deletion()` |

### 3.3 Operational and Security Records

| Data Category | Retention | Notes |
|---------------|-----------|-------|
| Admin change log | 3 years | Bounded in-memory; production must persist to durable store |
| Password reset audit log | 3 years | Security event record |
| Session tokens | Duration of session (≤ 24 h) + 30-day revocation log | Purged automatically on expiry |
| MFA enrollment records | Duration of account + 1 year after account deletion | Required for recovery audit trail |
| Backup code store (hashed) | Duration of enrollment period | Codes are single-use; store reset on re-enrolment |

---

## 4. Deletion Criteria and Approval Controls

### 4.1 PHI Deletion Criteria

A PHI record is eligible for **permanent deletion** only when **all** of the following conditions are met:

1. **Retention period elapsed** — The record's creation or last-activity date is older than the applicable minimum retention period (see Section 3.1).
2. **No active litigation hold** — Legal Counsel has confirmed in writing that no hold applies.
3. **Patient request or lifecycle trigger** — Deletion is either:
   - Requested by the patient under 45 CFR § 164.524 / right-to-erasure procedures, or
   - Triggered by a routine lifecycle job after retention expiry.
4. **Deletion approval issued** — A `DeletionApproval` record is created with:
   - `approver_id` — ID of the authorised approver (Compliance Officer or designated admin).
   - `reason` — Non-empty business justification for the deletion.
   - `approved_at` — UTC timestamp of approval.
5. **Pre-deletion audit event** — A `LIFECYCLE_DELETE_APPROVED` audit entry is appended before any storage mutation occurs.

Requests that fail any condition are rejected and logged as `LIFECYCLE_DELETE_DENIED`.

### 4.2 Audit Log Deletion Criteria

Audit log deletion follows the triple-gate enforced by `AuditedDeletionController` (see [POL-AUDIT-001 § 5](AUDIT_RETENTION_POLICY.md)):

| Gate | Enforcement Mechanism |
|------|-----------------------|
| Age > 7 years | `AuditRetentionPolicy.is_eligible_for_deletion()` |
| Archived tier membership | `AuditArchiveTier.contains()` |
| Valid `DeletionApproval` | `AuditedDeletionController._validate_approval()` |

### 4.3 Approval Workflow

```
[Deletion Request]
      │
      ▼
[Eligibility Check]  ──── FAIL ──▶  [LIFECYCLE_DELETE_DENIED logged]  ──▶  [Request rejected]
      │ PASS
      ▼
[Approver Review]
      │
      ├── Compliance Officer reviews retention age and litigation-hold status
      ├── Security Engineer verifies HMAC integrity chain (audit logs only)
      └── Approver signs DeletionApproval (approver_id + reason + timestamp)
      │
      ▼
[LIFECYCLE_DELETE_APPROVED event appended to audit store]
      │
      ▼
[Permanent deletion executed]
      │
      ▼
[Deletion confirmation archived]
```

### 4.4 Authorised Approvers

| Data Category | Authorised Approver Role |
|---------------|--------------------------|
| PHI (patient profiles, appointments, clinical documents) | Compliance Officer |
| Audit log records | Compliance Officer + Security Engineer (joint approval for records < 10 years in archive) |
| Operational records (admin log, reset tokens) | Operations Engineer |

---

## 5. Storage Lifecycle and Archival Guidance

### 5.1 PHI Lifecycle Stages

```
[Created / Ingested]
      │
      ▼
[Active Storage]  ─── 7-year mark ──▶  [Eligible for Archival Review]
      │                                         │
 Read / Write allowed                  Compliance review triggered
 Full API access                       (annual lifecycle job)
                                                │
                                     ┌──────────┴──────────┐
                                     │ Litigation hold?    │
                                     │ Active relationship?│
                                     └──────────┬──────────┘
                                           YES  │  NO
                                                │
                                     ┌──────────▼──────────┐
                                     │   Retain with       │
                                     │   documented        │ ◄── YES
                                     │   justification     │
                                     └─────────────────────┘
                                                │ NO
                                                ▼
                                     [Archive / Soft-delete]
                                                │
                                  10-year mark + approved deletion
                                                │
                                                ▼
                                     [Permanent deletion]
```

### 5.2 Audit Log Lifecycle (Automated)

The audit log lifecycle is automated via `AuditRetentionEnforcer.run_archival_cycle()`:

1. **Detection** — `AuditRetentionPolicy.get_archival_candidates()` scans the active store for entries with timestamp older than `now − 2 555 days`.
2. **Archival** — Candidates are moved to `AuditArchiveTier`; a `LIFECYCLE_ARCHIVE` event is appended to the active store.
3. **Retrieval** — Archived entries are returned by `AuditArchiveTier.retrieve()` on demand.
4. **Deletion** — Only after explicit `DeletionApproval`; managed by `AuditedDeletionController`.

### 5.3 Backup and Disaster Recovery Considerations

- Database backups (`backup.py`, `backup_schema.sql`) retain a point-in-time copy of all tables, including PHI.
- Backup retention must mirror the primary data retention schedule: **7-year minimum**.
- Backup media is subject to the same deletion approval controls as primary data.
- `restore_verification.py` must be executed after any backup restoration to confirm data integrity before production use.

---

## 6. Operational Alignment — Policy-to-Code Mapping

This section maps each policy requirement to the implementing code component, satisfying task_080_002.

| Policy Requirement | Code Component | File |
|---------------------|----------------|------|
| Audit log minimum retention (7 years) | `AUDIT_RETENTION_YEARS = 7`, `AUDIT_RETENTION_DAYS = 2555` | `app/src/audit_storage.py` |
| Audit log active-tier eligibility check | `AuditRetentionPolicy.is_eligible_for_deletion()` | `app/src/audit_storage.py` |
| Archival candidates detection | `AuditRetentionPolicy.get_archival_candidates()` | `app/src/audit_storage.py` |
| Archival execution | `AuditRetentionEnforcer.run_archival_cycle()` | `app/src/audit_storage.py` |
| Archive cold-tier storage | `AuditArchiveTier.archive()` / `retrieve()` / `contains()` | `app/src/audit_storage.py` |
| Deletion approval record | `DeletionApproval` dataclass (approver_id, reason, approved_at) | `app/src/audit_storage.py` |
| Triple-gate deletion control | `AuditedDeletionController.request_deletion()` | `app/src/audit_storage.py` |
| Pre-deletion audit event | `LIFECYCLE_DELETE_APPROVED` / `LIFECYCLE_DELETE_DENIED` appended before mutation | `app/src/audit_storage.py` |
| Append-only enforcement | `AppendOnlyAuditStore.delete()` / `update()` raise `AuditImmutabilityError` | `app/src/audit_storage.py` |
| HMAC integrity chain | `AuditIntegrityChecker`, `AuditIntegrityValidationJob` | `app/src/audit_storage.py` |
| PHI exclusion from audit fields | `AUDIT_PHI_EXCLUDED_FIELDS`, resource IDs numeric-only | `app/src/audit_events.py` |
| PHI access and modify events | `log_phi_access()`, `AuditEventType.PHI_ACCESS` / `PHI_MODIFY` | `app/src/audit_events.py` |
| Retention compliance evidence | `generate_retention_compliance_report()` | `app/src/audit_storage.py` |
| Integrity compliance evidence | `generate_integrity_compliance_report()` | `app/src/audit_storage.py` |
| Admin change audit trail | `_record_admin_change()`, `_ADMIN_CHANGE_LOG` | `app/src/rbac.py` |
| Database backup | `backup.py`, `backup_schema.sql` | `app/db/` |
| Backup restore verification | `restore_verification.py` | `app/src/` |

**Policy review checkpoint:** Any change to constants (`AUDIT_RETENTION_YEARS`, `AUDIT_RETENTION_DAYS`) or deletion logic (`AuditedDeletionController`, `AuditRetentionPolicy`) requires a corresponding version update to this document and to POL-AUDIT-001.

---

## 7. Roles and Responsibilities

| Role | Responsibility |
|------|----------------|
| Compliance Officer | Policy ownership, annual review, deletion approval for PHI and audit records |
| Security Engineer | HMAC integrity review, deletion approval (joint for archived audit logs), policy change assessment |
| Operations Engineer | Runs scheduled archival lifecycle jobs, monitors storage tiers, approves operational record deletion |
| QA / Compliance Engineer | Validates compliance report artefacts, confirms evidence generation functions correctly |
| Legal Counsel | Issues and lifts litigation holds; provides written confirmation before deletion proceeds |

---

## 8. Compliance Evidence and Audit Readiness

This section documents the evidence artefacts produced by the platform and satisfies task_080_003.

### 8.1 Automated Evidence Generation

| Evidence Artefact | Produced By | Covers |
|-------------------|-------------|--------|
| Retention compliance report | `generate_retention_compliance_report()` | Active entry count, archival candidates, archive size, policy settings, integrity check result |
| Integrity compliance report | `generate_integrity_compliance_report()` | HMAC chain status, validation run timestamp, failure count, algorithm in use |
| Audit query export (CSV / JSON) | `AuditQueryService.export_csv()` / `export_json()` | Full filtered audit entry set for a given review period |
| Deletion event trail | `LIFECYCLE_DELETE_APPROVED` / `LIFECYCLE_DELETE_DENIED` entries | Every deletion attempt, approved or rejected, with approver and reason |
| Archival event trail | `LIFECYCLE_ARCHIVE` entries | Every record moved from active to archive tier |

### 8.2 Pre-Audit Readiness Checklist

Before presenting to an external auditor, the Compliance Officer must verify:

- [ ] `generate_retention_compliance_report()` has been run within the last 30 days and the output is archived.
- [ ] `generate_integrity_compliance_report()` confirms `chain_intact = True` with zero failures.
- [ ] All deletion events in the audit store carry a valid `DeletionApproval` record with a named approver.
- [ ] No record in the active store is older than the maximum retention period without documented justification.
- [ ] POL-DATA-001 (this document) and POL-AUDIT-001 are at their current approved versions.
- [ ] Annual policy review has been completed and sign-off is documented.
- [ ] Backup retention schedule matches the primary data retention schedule (≥ 7 years).
- [ ] All staff and admin accounts have MFA enrolled (US-079 policy compliance).

### 8.3 Regulatory Cross-Reference

| Requirement | Regulation | PropelIQ Control |
|-------------|------------|-----------------|
| PHI retention ≥ 6 years | HIPAA 45 CFR § 164.530(j) | 7-year minimum enforced in `AUDIT_RETENTION_YEARS` and this policy (Section 3) |
| Access to own records | HIPAA 45 CFR § 164.524 | Deletion approval workflow (Section 4.1) |
| Amendment of records | HIPAA 45 CFR § 164.526 | RBAC-gated update operations; audit trail on every modification |
| Audit controls | HIPAA 45 CFR § 164.312(b) | `AppendOnlyAuditStore`, HMAC integrity chain, `AuditIntegrityValidationJob` |
| Integrity controls | HIPAA 45 CFR § 164.312(c)(1) | HMAC-SHA256 hash chain across all audit entries |

---

## 9. Policy Exceptions

Exceptions to this policy require:

1. Written request from the data owner or Compliance Officer.
2. Risk assessment documenting the business need and associated risk.
3. Approval from the Compliance Officer and Security Engineer.
4. Time-bounded exception with a defined review date.
5. Exception logged as an immutable audit event.

Exceptions are tracked in the policy exception register maintained by the Compliance Officer.

---

## 10. Version History

Policy changes must be reviewed and approved before taking effect. All versions are stored in version control alongside the source code.

| Version | Date | Author | Change Summary | Approved By |
|---------|------|--------|----------------|-------------|
| 1.0 | 2026-06-24 | Compliance Officer | Initial policy — covers PHI, audit logs, deletion approval workflow, lifecycle alignment, and audit readiness checklist. Implements US-080 task_080_001, task_080_002, task_080_003. | Compliance Officer |

---

## 11. Related Documents

| Document | Location | Relationship |
|----------|----------|--------------|
| POL-AUDIT-001: Audit Log Retention and Archival Policy | `app/AUDIT_RETENTION_POLICY.md` | Technical detail for audit log lifecycle; subordinate to this policy |
| EP-007 US-076: Audit Log Retention Story | `.propel/context/tasks/EP-007/us_076/us_076.md` | User story that implements audit retention in code |
| EP-007 US-077: Log Integrity Checking | `.propel/context/tasks/EP-007/us_077/us_077.md` | HMAC integrity controls referenced in Section 6 |
| EP-007 US-078: Admin Audit Query Interface | `.propel/context/tasks/EP-007/us_078/us_078.md` | Query and export functionality for evidence generation |
| EP-007 US-079: MFA Support | `.propel/context/tasks/EP-007/us_079/us_079.md` | MFA enrollment policy referenced in audit readiness checklist |
| Data Model | `app/db/DATA_MODEL.md` | Defines table structures for data categories in scope |
| Backup Runbook | `app/db/backup_runbook.md` | Operational backup and retention procedures |
| Database DDL and Migration | `app/db/DDL_AND_MIGRATION.md` | Schema version history for data lifecycle reference |
