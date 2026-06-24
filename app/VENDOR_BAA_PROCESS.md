# Vendor Business Associate Agreement (BAA) Process

**Document ID:** POL-BAA-001  
**User Story:** US-082 (EP-007)  
**Tasks:** task_082_001, task_082_002, task_082_003  
**Version:** 1.0  
**Owner:** Compliance Officer / Legal Counsel  
**Status:** Approved  
**Effective Date:** 2026-06-24  
**Regulatory References:** HIPAA 45 CFR § 164.308(b)(1), 45 CFR § 164.504(e), 45 CFR § 164.532

> **Legal Notice:** This document provides process guidance and a BAA template structure aligned with HIPAA regulatory requirements. All vendor BAA documents must be reviewed and finalised by qualified Legal Counsel before execution. Template clauses are not a substitute for legal advice.

---

## 1. Purpose

This document defines the PropelIQ Appointment Booking platform's formal process for engaging vendors that qualify as **Business Associates (BAs)** under HIPAA.  A Business Associate is any person or entity that performs functions or activities on behalf of PropelIQ that involve the use or disclosure of Protected Health Information (PHI).

This process ensures:
- All BA vendors are assessed for security and compliance risk before PHI access is granted.
- A signed BAA is in place before any BA accesses, processes, or transmits PHI.
- Ongoing compliance is monitored and reviewed on a defined cadence.
- BAA documentation is version-controlled and retained for the duration of the vendor relationship plus 7 years.

---

## 2. Scope

### 2.1 Vendors That Require a BAA

A BAA is required before engaging any vendor that will:

| Scenario | Example |
|----------|---------|
| Access, store, or transmit ePHI | Cloud database hosting, file storage providers |
| Process PHI on PropelIQ's behalf | Analytics platforms, clinical coding services |
| Provide IT services with incidental PHI access | IT support providers with system access |
| Operate subcontractors that handle PHI | Cloud providers using sub-processors with data access |

### 2.2 Vendors That Do Not Require a BAA

The following do not require a BAA (not business associates under HIPAA):

- Vendors providing purely administrative services with no PHI access (e.g. office supplies).
- Conduit providers that transport data but have no routine access to contents (e.g. ISPs acting as mere conduits).
- Vendors receiving PHI only as part of a treatment relationship (e.g. specialist referral networks — these have their own HIPAA obligations).

---

## 3. Vendor Due Diligence Process (task_082_001)

### 3.1 Overview

Before any PHI access is authorised, a risk assessment must be completed for every BA vendor.  The assessment uses the checklist in Section 3.2 and must be approved by the Compliance Officer.

### 3.2 Vendor Due Diligence Checklist

Complete all items before advancing a vendor to BAA execution.

#### Category 1 — Business and Legal Qualification

| # | Item | Completed | Notes |
|---|------|-----------|-------|
| DD-01 | Confirm vendor is legally classified as a Business Associate under 45 CFR § 160.103 | ☐ | |
| DD-02 | Verify vendor is not a covered entity (different rules apply) | ☐ | |
| DD-03 | Obtain vendor legal entity name, registered address, and primary compliance contact | ☐ | |
| DD-04 | Confirm vendor has a designated HIPAA Security Officer | ☐ | |
| DD-05 | Review vendor's existing BAA policy or compliance programme documentation | ☐ | |

#### Category 2 — Data Access and Classification

| # | Item | Completed | Notes |
|---|------|-----------|-------|
| DD-06 | Document which PHI data categories the vendor will access (appointments, patient profiles, clinical documents, other) | ☐ | |
| DD-07 | Confirm minimum-necessary access: vendor receives only the PHI required for the contracted function | ☐ | |
| DD-08 | Document whether the vendor will create, receive, maintain, or transmit PHI (or a combination) | ☐ | |
| DD-09 | Identify any subcontractors (sub-BAs) the vendor will use that may also access PHI | ☐ | |
| DD-10 | Confirm vendor will require sub-BAs to execute their own BAA before PHI access is granted | ☐ | |

#### Category 3 — Technical Security Controls

| # | Item | Completed | Notes |
|---|------|-----------|-------|
| DD-11 | Confirm vendor enforces encryption at rest (AES-256 or equivalent) for any stored PHI | ☐ | |
| DD-12 | Confirm vendor enforces encryption in transit (TLS 1.2 minimum, strong cipher suites) | ☐ | |
| DD-13 | Verify vendor employs access controls (role-based access, unique user IDs, MFA for privileged accounts) | ☐ | |
| DD-14 | Confirm vendor maintains audit logs for all PHI access and retains them for a minimum of 7 years | ☐ | |
| DD-15 | Verify vendor has an automatic session timeout policy (≤ 30 minutes for PHI systems) | ☐ | |
| DD-16 | Confirm vendor performs regular vulnerability assessments or penetration testing (at least annually) | ☐ | |

#### Category 4 — Breach Notification Capability

| # | Item | Completed | Notes |
|---|------|-----------|-------|
| DD-17 | Confirm vendor has a documented breach response and notification process | ☐ | |
| DD-18 | Verify vendor can notify PropelIQ of a breach or security incident within **24 hours** of discovery | ☐ | |
| DD-19 | Confirm vendor's breach notification covers all PHI categories in scope (not only a subset) | ☐ | |
| DD-20 | Request evidence of breach notification test (tabletop exercise or simulation within last 12 months) | ☐ | |

#### Category 5 — Audit Rights and Compliance Evidence

| # | Item | Completed | Notes |
|---|------|-----------|-------|
| DD-21 | Confirm vendor will permit PropelIQ to audit their HIPAA compliance upon reasonable notice | ☐ | |
| DD-22 | Obtain current third-party compliance attestation: SOC 2 Type II, ISO 27001, HITRUST CSF, or equivalent | ☐ | |
| DD-23 | Verify attestation covers the service scope that handles PropelIQ PHI (not a different product line) | ☐ | |
| DD-24 | Confirm vendor will provide updated compliance attestations annually or upon material scope change | ☐ | |

#### Category 6 — Termination and Data Return / Destruction

| # | Item | Completed | Notes |
|---|------|-----------|-------|
| DD-25 | Confirm vendor will return or destroy all PHI within 30 days of contract termination | ☐ | |
| DD-26 | Confirm vendor will certify in writing that PHI has been destroyed and is not recoverable | ☐ | |
| DD-27 | Confirm vendor's subcontractors are bound by equivalent return/destroy obligations | ☐ | |

### 3.3 Risk Scoring and Approval Thresholds

After completing the due diligence checklist, calculate a risk rating:

| Risk Rating | Criteria | Approval Required |
|-------------|----------|-------------------|
| **Low** | All DD items ✓; valid SOC 2 Type II or equivalent; no sub-BAs with PHI access | Compliance Officer |
| **Medium** | ≤ 3 DD items with caveats; valid compliance attestation; sub-BA BAAs in place | Compliance Officer + Security Engineer |
| **High** | > 3 DD items with caveats; no third-party attestation; or PHI at rest without verified encryption | Compliance Officer + Legal Counsel + Executive Sign-off |
| **Reject** | Material control gap (no encryption, no breach notification, refuses audit rights) | Do not proceed — escalate to Leadership |

---

## 4. BAA Template and Approval Workflow (task_082_002)

### 4.1 Required BAA Provisions (45 CFR § 164.504(e)(2))

The following provisions must appear in every executed BAA. Legal Counsel must review and customise these provisions before execution.

---

### BUSINESS ASSOCIATE AGREEMENT TEMPLATE

**[IMPORTANT: This template must be reviewed by qualified Legal Counsel before execution.  Bracketed placeholders must be completed.]**

---

**This Business Associate Agreement ("Agreement")** is entered into as of **[Effective Date]** between **PropelIQ, Inc.** ("Covered Entity") and **[Vendor Legal Name]** ("Business Associate").

---

#### 1. Definitions

Terms used but not otherwise defined in this Agreement shall have the same meaning as those terms in the HIPAA Rules (45 CFR Parts 160 and 164).

- **"HIPAA Rules"** means the Privacy, Security, Breach Notification, and Enforcement Rules at 45 CFR Part 160 and Part 164.
- **"PHI"** means Protected Health Information as defined at 45 CFR § 160.103, limited to the PHI created, received, maintained, or transmitted by Business Associate on behalf of Covered Entity.
- **"Services"** means the services described in the underlying services agreement between the parties, as may be amended.

---

#### 2. Permitted Uses and Disclosures of PHI

2.1 Business Associate may use or disclose PHI only:
  (a) as necessary to perform the Services for Covered Entity;
  (b) as required by law; or
  (c) as otherwise permitted or required under this Agreement.

2.2 Business Associate shall not use or disclose PHI in a manner that would violate the HIPAA Privacy Rule if done by Covered Entity, except as permitted under Section 2.1.

2.3 Business Associate agrees to make uses and disclosures and requests for PHI consistent with the minimum-necessary standard.

---

#### 3. Safeguards

3.1 **Administrative Safeguards.** Business Associate shall implement and maintain administrative safeguards as required by 45 CFR § 164.308 to protect the confidentiality, integrity, and availability of electronic PHI (ePHI).

3.2 **Physical Safeguards.** Business Associate shall implement and maintain physical safeguards as required by 45 CFR § 164.310 to protect ePHI.

3.3 **Technical Safeguards.** Business Associate shall implement and maintain technical safeguards as required by 45 CFR § 164.312, including:
  - Encryption of ePHI at rest (AES-256 or equivalent) and in transit (TLS 1.2 minimum).
  - Unique user identification and access controls for all personnel with PHI access.
  - Multi-factor authentication (MFA) for privileged and remote access.
  - Automatic session timeout (≤ 30 minutes) for PHI systems.

3.4 **Audit Logging.** Business Associate shall maintain audit logs for all access to PHI for a minimum of 7 years from the date of creation.

3.5 **Subcontractors.** Business Associate shall ensure that any subcontractor (sub-BA) that creates, receives, maintains, or transmits PHI on behalf of Business Associate executes a BAA with Business Associate that imposes the same restrictions and conditions as this Agreement.  Business Associate shall not permit a subcontractor to access PHI until such BAA is executed.

---

#### 4. Breach Notification

4.1 Business Associate shall notify Covered Entity within **24 hours** of discovering a Breach of Unsecured PHI (or a Security Incident that may constitute a breach), as defined in 45 CFR § 164.400–414.

4.2 Such notification shall include, to the extent known:
  (a) a description of what happened and when discovered;
  (b) a description of the types of PHI involved;
  (c) the name and contact information of any individual whose PHI was involved, if known;
  (d) any steps Business Associate is taking to investigate and mitigate the breach;
  (e) steps Covered Entity should take to protect affected individuals.

4.3 Business Associate shall cooperate with Covered Entity's breach investigation and remediation efforts.

---

#### 5. Covered Entity's Obligations

5.1 Covered Entity shall notify Business Associate of any limitation in its Notice of Privacy Practices that would affect Business Associate's use or disclosure of PHI.

5.2 Covered Entity shall notify Business Associate of any changes in, or revocation of, permission by an individual to use or disclose PHI.

5.3 Covered Entity shall not request Business Associate to use or disclose PHI in any manner that would violate the HIPAA Rules.

---

#### 6. Access, Amendment, and Accounting

6.1 Business Associate shall, within **15 business days** of a written request from Covered Entity, make available PHI required for Covered Entity to respond to an individual's request under 45 CFR § 164.524 (access) or § 164.526 (amendment).

6.2 Business Associate shall document disclosures of PHI as required for Covered Entity to respond to an accounting request under 45 CFR § 164.528 and make such documentation available to Covered Entity within **15 business days** of a written request.

---

#### 7. Audit Rights

7.1 Business Associate shall make available its internal practices, books, and records relating to the use and disclosure of PHI to the Secretary of the Department of Health and Human Services (HHS) or to Covered Entity for purposes of determining compliance with the HIPAA Rules, upon reasonable written notice.

7.2 Covered Entity may conduct an on-site compliance audit of Business Associate's HIPAA controls no more than once per calendar year (or at any time following notification of a breach or material compliance concern), on 10 business days' written notice.

---

#### 8. Term and Termination

8.1 **Term.** This Agreement commences on the Effective Date and remains in effect until the underlying services agreement is terminated or for as long as Business Associate retains PHI, whichever is later.

8.2 **Termination for Cause.** Either party may terminate this Agreement immediately if the other party materially breaches any provision of this Agreement and fails to cure such breach within **10 business days** of written notice.

8.3 **Effect of Termination — Return or Destruction of PHI.** Upon termination, Business Associate shall, within **30 days**:
  (a) return all PHI to Covered Entity in a mutually agreed format; or
  (b) destroy all PHI and certify in writing that it has been irreversibly destroyed and is not recoverable.

8.4 If return or destruction is infeasible, Business Associate shall notify Covered Entity and extend the protections of this Agreement to any retained PHI for as long as it is retained.

---

#### 9. Miscellaneous

9.1 **Amendment.** This Agreement may be amended only by a written instrument signed by both parties.  Either party may terminate this Agreement on 30 days' written notice if the parties cannot agree on amendments required by changes in the HIPAA Rules.

9.2 **Interpretation.** This Agreement shall be construed to give effect to the Parties' intent to comply with the HIPAA Rules.

9.3 **Survival.** Sections 3, 4, 6, 7, and 8.3–8.4 survive termination of this Agreement.

9.4 **Entire Agreement.** This Agreement, together with the underlying services agreement, constitutes the entire agreement between the Parties with respect to the subject matter hereof.

---

**COVERED ENTITY:** PropelIQ, Inc.

| Field | Value |
|-------|-------|
| Signature | ___________________________ |
| Printed Name | ___________________________ |
| Title | ___________________________ |
| Date | ___________________________ |

**BUSINESS ASSOCIATE:** [Vendor Legal Name]

| Field | Value |
|-------|-------|
| Signature | ___________________________ |
| Printed Name | ___________________________ |
| Title | ___________________________ |
| Date | ___________________________ |

---

### 4.2 BAA Approval Workflow

```
[Vendor Due Diligence Complete (Section 3)]
         │
         ▼
[Legal Counsel Drafts / Reviews BAA]
  ├── Customise template provisions for vendor scope
  ├── Review vendor's redline (if provided)
  └── Confirm all required HIPAA provisions are present
         │
         ▼
[Compliance Officer Review]
  ├── Confirm due diligence items satisfied
  ├── Confirm risk rating ≤ MEDIUM (or escalation approvals obtained)
  └── Sign compliance approval memo
         │
         ▼
[Escalation? (High-risk vendors only)]
  └── Executive sign-off required before proceeding
         │
         ▼
[Counter-signature by Vendor]
  └── Both parties execute the BAA
         │
         ▼
[BAA Filed in Vendor Register (Section 5)]
  ├── Scanned signed copy retained in secure contract repository
  ├── Vendor Register row updated with execution date and status
  └── Reminder set for annual compliance review (Section 5.3)
         │
         ▼
[PHI Access Authorised]
```

### 4.3 BAA Document Retention

Signed BAAs must be retained for the **duration of the vendor relationship plus 7 years** after termination, consistent with POL-DATA-001 (§ 3.3) and HIPAA 45 CFR § 164.530(j).

---

## 5. Vendor Register and Ongoing Review Controls (task_082_003)

### 5.1 Active Vendor Register

Maintain this register for all BA vendors with a signed or pending BAA.

| Vendor ID | Vendor Name | PHI Data Categories | BAA Status | BAA Executed | Compliance Attestation | Attestation Expiry | Review Due | Owner |
|-----------|-------------|---------------------|------------|-------------|------------------------|-------------------|------------|-------|
| BA-001 | [Vendor Name] | [Appointments / Clinical docs / etc.] | ⬜ Pending | — | — | — | — | Compliance Officer |

> Copy a row for each vendor. Update status as the process progresses.

**BAA Status Values:**

| Status | Meaning |
|--------|---------|
| ⬜ Pending | Due diligence in progress |
| 🔄 Under Review | BAA drafted, in legal review |
| ✅ Executed | Signed BAA on file |
| ⚠️ Expired | Review overdue or attestation expired |
| 🚫 Terminated | Vendor relationship ended; data return/destroy confirmed |

### 5.2 Annual Review Cadence

Every active BA vendor must be reviewed **annually** from the BAA execution date.  The review must confirm:

| Review Item | Verification Method |
|-------------|---------------------|
| BAA provisions still align with current vendor scope | Compare vendor scope in BAA to actual services used |
| Vendor's compliance attestation (SOC 2 / ISO 27001 / HITRUST) is current | Request updated report from vendor |
| No reportable security incidents in the prior 12 months | Review vendor's incident log or attestation |
| Sub-BA list is unchanged; sub-BA BAAs remain in place | Request vendor's sub-processor list |
| Vendor's contact information and security officer are current | Confirm with vendor via email |
| No regulatory or contractual changes requiring BAA amendment | Check HIPAA updates and service agreement amendments |

### 5.3 Trigger Events Requiring Immediate Review

The following events require an out-of-cycle BAA review and status update, regardless of the annual schedule:

| Trigger | Required Action | Deadline |
|---------|----------------|----------|
| Vendor notifies PropelIQ of a breach or security incident | Activate incident response; review BAA breach obligations; assess notification duties | Immediate (24 hours) |
| Vendor changes sub-processors that handle PHI | Request updated sub-BA BAA list; confirm new sub-processors are covered | 10 business days |
| Vendor expands service scope to cover additional PHI categories | Update due diligence checklist; amend BAA if necessary | Before new PHI access begins |
| Vendor is acquired by or merges with another entity | Verify successor entity's HIPAA compliance; obtain updated BAA under successor entity name | 30 days |
| Vendor's compliance attestation expires without renewal | Place PHI access on hold until renewed attestation is received | Same day as expiry |
| PropelIQ terminates the vendor relationship | Issue termination notice; initiate data return/destroy process (30-day window) | Day of termination |
| Change in HIPAA Rules affecting BAA required provisions | Legal Counsel reviews all active BAAs; amend as required | 60 days from rule effective date |

### 5.4 Vendor Compliance Review Record

For each annual or triggered review, document:

| Field | Value |
|-------|-------|
| Vendor ID | BA-00X |
| Review Date | YYYY-MM-DD |
| Review Type | Annual / Triggered (specify trigger) |
| Reviewer | Name + Role |
| Scope Changes Since Last Review | Yes / No — describe if Yes |
| Attestation Status | Current / Expired — attestation type and expiry |
| Open Incidents | None / Describe |
| BAA Amendment Required | Yes / No — if Yes, initiate amendment workflow |
| Outcome | No Action / BAA Amendment / PHI Access Suspended / BAA Terminated |
| Next Review Due | YYYY-MM-DD |

---

## 6. Roles and Responsibilities

| Role | Responsibility |
|------|----------------|
| Compliance Officer | Owns BAA programme; approves due diligence outcomes; manages vendor register; triggers review cycle |
| Legal Counsel | Reviews and finalises BAA template and executed BAAs; advises on vendor redlines; confirms regulatory alignment |
| Security Engineer | Reviews technical security controls in due diligence checklist (DD-11 to DD-16); validates encryption and audit log requirements |
| Operations Engineer | Facilitates technical onboarding after BAA execution; confirms PHI access is gated on BAA status in vendor register |
| Executive Sponsor | Provides sign-off for High-risk vendor engagements; escalation point for vendor disputes |

---

## 7. Integration with HIPAA Compliance Programme

This process directly addresses the following items from CHK-HIPAA-001 (HIPAA Compliance Checklist):

| Checklist Item | Status After US-082 |
|----------------|---------------------|
| § 164.308(b)(1) Business Associate Contracts | ✅ Completed — BAA template and process in POL-BAA-001 |
| § 164.412 Notify business associates of breach | 🔄 In Progress — BAA template clause 4 defines obligations; PropelIQ internal notification SOP still needed |
| CHK-HIPAA-001 GAP-004 (BAA template) | ✅ Resolved — POL-BAA-001 provides template and workflow |

---

## 8. Version History

| Version | Date | Author | Change Summary | Approved By |
|---------|------|--------|----------------|-------------|
| 1.0 | 2026-06-24 | Compliance Officer / Legal | Initial BAA process — vendor due diligence checklist, BAA template (45 CFR § 164.504(e)(2) compliant), approval workflow, vendor register, ongoing review controls. Implements US-082 task_082_001, task_082_002, task_082_003. | Compliance Officer |

---

## 9. Related Documents

| Document | Location | Relationship |
|----------|----------|--------------|
| CHK-HIPAA-001: HIPAA Compliance Checklist | `app/HIPAA_COMPLIANCE_CHECKLIST.md` | Umbrella compliance checklist — § 164.308(b)(1) and § 164.412 items resolved by this document |
| POL-DATA-001: Data Retention and Deletion Policy | `app/DATA_RETENTION_DELETION_POLICY.md` | BAA retention period aligns with 7-year data retention requirement |
| POL-AUDIT-001: Audit Log Retention and Archival Policy | `app/AUDIT_RETENTION_POLICY.md` | Vendor audit log obligations reference PropelIQ's own 7-year retention standard |
| Incident Investigation Runbook | `app/INCIDENT_INVESTIGATION_RUNBOOK.md` | Activated when a vendor notifies PropelIQ of a breach (trigger event) |
