# SEC-2: Waiver and Exception Workflow

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Security team, backend engineers, DevOps

---

## 1. Overview

This document defines the security finding waiver and exception workflow, including approval criteria, tracking, auditing, and time-bound expiry controls.

**Objectives:**
- Provide controlled process for accepting security risks
- Ensure waivers are auditable and time-bounded
- Maintain exception registry
- Enable risk-based decision making
- Support compliance auditing

---

## 2. Waiver Eligibility Criteria

### 2.1 Waiverable Findings

**Can be waived (with justification):**

| Finding | Waiverable | Max Duration | Approval Level |
|---|---|---|---|
| **SQL Injection** | ❌ NO | - | - |
| **OS Command Injection** | ❌ NO | - | - |
| **Hardcoded Secrets** | ❌ NO | - | - |
| **Weak Cryptography (MD5)** | ❌ NO | - | - |
| **XXE/Deserialization** | ❌ NO | - | - |
| **Unpatched Critical CVE** | ❌ NO | - | - |
| **Deprecated Dependency** | ⚠️ LIMITED | 30 days | Security Lead |
| **Medium Severity SAST** | ✅ YES | 90 days | Security Lead |
| **Medium Severity CVE** | ✅ YES | 60 days | Security Lead |
| **License Issue (non-GPL)** | ✅ YES | 180 days | Legal + Security |
| **False Positive** | ✅ YES | Permanent | Security Lead |

### 2.2 Non-Waiverable Findings

**Must be fixed (no waiver allowed):**

```
CRITICAL Security Issues:
  - SQL Injection / Command Injection
  - Hardcoded API keys, passwords, tokens
  - Unpatched CRITICAL CVEs
  - Known active exploits
  - Authentication bypass vulnerabilities
  - Unencrypted sensitive data transmission
  - XXE / Deserialization attacks
  
HIGH Priority Issues (< 24 hours):
  - High-severity SQL injection
  - Weak cryptography (MD5, SHA1)
  - Missing authorization checks
  - Privilege escalation paths
  
Must fix before merge (no waiver).
```

---

## 3. Waiver Request Process

### 3.1 Waiver Submission

**Step 1: Create Waiver Request**

```
Title: SQL injection waiver - [justification]
Finding: SAST-SQL-001
Severity: HIGH
Tool: Semgrep
File: src/repositories/UserRepository.cs:45
Commit: abc123def456

Business Justification:
  This is a legacy integration with third-party API that 
  requires dynamic query construction. We're migrating to 
  parameterized queries in Q3 2026. Interim risk accepted.

Risk Assessment:
  - Exposure: Internal API, not user-facing
  - Likelihood: Low (input validated upstream)
  - Impact: Medium (database access required)
  - Mitigation: Input validation, WAF rules, audit logging

Proposed Fix Timeline:
  - Q3 2026: Refactor to parameterized queries
  - Test coverage: 100% of affected code paths

Owner: @backend-team
Reviewer: @security-lead
```

**Step 2: Select Waiver Duration**

```
Waiver Expiry Options:
  ⏰ 7 days (critical path, high-touch review)
  ⏰ 30 days (standard for medium/low findings)
  ⏰ 90 days (legacy code, planned refactoring)
  ⏰ 1 year (false positive, documented exception)
```

**Step 3: Submit for Review**

```bash
# CLI command (example - actual tool TBD)
security-cli waiver create \
  --finding-id=SAST-SQL-001 \
  --duration=90-days \
  --justification-file=waiver.md \
  --owner=backend-team \
  --target-fix-date=2026-09-30
```

### 3.2 Waiver Request Template

```markdown
# Security Finding Waiver Request

## Finding Details
- **Finding ID**: SAST-SQL-001
- **Severity**: HIGH
- **Tool**: Semgrep
- **CWE**: CWE-89 (SQL Injection)
- **File**: src/repositories/UserRepository.cs:45
- **Rule**: sql-injection-concatenation

## Current Code
```csharp
var query = "SELECT * FROM users WHERE id = " + userId;
var result = await _connection.QueryAsync(query);
```

## Business Justification
This legacy integration with [third-party API] requires dynamic 
SQL construction due to [reason]. We have planned migration to 
parameterized queries scheduled for Q3 2026.

## Risk Assessment
| Factor | Assessment | Evidence |
|---|---|---|
| Exposure | Internal | Behind VPN, service-to-service only |
| Validation | Yes | Input validated upstream before reaching DB layer |
| Likelihood | Low | No known active exploits, internal API |
| Impact | Medium | Requires database credentials + code execution |
| Compensating Controls | Yes | WAF rules, audit logging, IP allowlist |

## Mitigation Plan
1. **Immediate** (approved):
   - Add additional input validation
   - Enable audit logging for all queries
   - Deploy WAF rules to filter injection patterns
   - Quarterly security review

2. **Q3 2026**:
   - Refactor to use parameterized queries
   - Remove concatenation-based query construction
   - Add 100% test coverage for refactored code
   - Remove this waiver

## Approval Path
- [ ] Owner Sign-off: @backend-team-lead
- [ ] Security Lead Review: @security-lead
- [ ] Optional: CISO Review (if duration > 90 days)

## Expiry
- **Approved Until**: 2026-09-30
- **Auto-Remove**: Yes (flag if not fixed by expiry)
- **Review Reminder**: 2026-09-01 (30 days before expiry)
```

---

## 4. Waiver Approval Workflow

### 4.1 Approval Levels

| Approval Level | Authority | Can Waive | Max Duration | Examples |
|---|---|---|---|---|
| **Auto-Approve** | System | Non-critical false positives | Permanent | Duplicate findings, test code |
| **Developer** | Code owner | Not applicable | - | N/A (self-approval not allowed) |
| **Security Lead** | AppSec team | MEDIUM findings | 90 days | Medium CVE, code quality |
| **CISO** | Chief Security Officer | HIGH findings | 1 year | HIGH CVE, license issues |
| **Legal + Security** | Both required | License-related | 1 year | AGPL dependency exceptions |

### 4.2 Approval Checklist

**Security Lead reviews:**
```
☐ Finding is legitimate (not false positive)
☐ Finding is correctly categorized by severity
☐ Risk assessment is accurate
☐ Mitigation plan is feasible
☐ Timeline is realistic
☐ Business justification is valid
☐ Compensating controls are adequate
☐ Expiry date is reasonable
☐ No pattern of repeated waivers for same issue
```

**CISO reviews (HIGH findings):**
```
☐ All security lead checks passed
☐ Risk acceptable to organization
☐ Compliance implications reviewed
☐ Insurance/liability implications assessed
☐ Customer impact considered
☐ Audit trail complete
```

### 4.3 Approval Decision

**Example approval:**

```
APPROVED ✅
├─ Finding: SAST-SQL-001
├─ Duration: 90 days (until 2026-09-30)
├─ Approved by: @security-lead (Sarah Chen)
├─ Date: 2026-06-22
├─ Conditions:
│  ├─ Enable audit logging: ✅ Required
│  ├─ Add WAF rules: ✅ Required
│  ├─ Quarterly review: ✅ Required
│  └─ Fix plan documented: ✅ Required
└─ Next Review: 2026-09-01

REJECTED ❌
├─ Finding: SAST-CMD-001 (OS Command Injection)
├─ Reason: Cannot waive CRITICAL injection vulnerabilities
├─ Action Required: Fix must be completed before merge
└─ Reviewer: @security-lead (Sarah Chen)
```

---

## 5. Waiver Registry and Tracking

### 5.1 Registry Structure

**Central waiver registry (GitHub issue or database):**

```yaml
waivers:
  - id: W-2026-001
    finding_id: SAST-SQL-001
    severity: HIGH
    status: ACTIVE
    created_date: 2026-06-22
    expiry_date: 2026-09-30
    approved_by: security-lead@company.com
    owner: backend-team@company.com
    business_justification: "Legacy API integration, Q3 refactoring planned"
    mitigation: "Input validation, WAF, audit logging"
    review_reminder_sent: false
    auto_block_on_expiry: true
    
  - id: W-2026-002
    finding_id: LIC-GPL-001
    severity: MEDIUM
    status: EXPIRED
    created_date: 2026-03-15
    expiry_date: 2026-06-15
    approved_by: legal@company.com
    owner: devops-team@company.com
    auto_renewal: false
    remediation_applied: true
    
  - id: W-2026-003
    finding_id: SAST-MD5-001
    severity: HIGH
    status: REJECTED
    created_date: 2026-06-20
    rejection_reason: "Cannot waive weak cryptography"
    rejected_by: security-lead@company.com
    required_action: "Fix before merge"
```

### 5.2 Registry Queries

**Show all active waivers:**
```sql
SELECT * FROM waivers WHERE status = 'ACTIVE' AND expiry_date > NOW()
```

**Show waivers expiring soon:**
```sql
SELECT * FROM waivers 
WHERE status = 'ACTIVE' 
AND expiry_date BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 7 DAY)
```

**Show repeated waivers (same finding):**
```sql
SELECT finding_id, COUNT(*) as waiver_count, MAX(expiry_date) as latest
FROM waivers
GROUP BY finding_id
HAVING waiver_count > 1
ORDER BY waiver_count DESC
```

---

## 6. Waiver Expiry Management

### 6.1 Expiry Timeline

```
2026-06-22: Waiver created (Duration: 90 days)
     │
     ├─ 2026-08-31 (30 days before): Reminder email
     │              "Waiver expires in 30 days - fix plan due"
     │
     ├─ 2026-09-15 (15 days before): Escalation
     │              "Waiver expires in 15 days - confirm fix status"
     │
     ├─ 2026-09-28 (2 days before): Final notice
     │              "Waiver expires in 2 days - fix required"
     │
     └─ 2026-09-30: Expiry date
        ├─ Auto-block if not renewed
        ├─ Merge gates re-enabled
        └─ Finding re-appears in scans
```

### 6.2 Auto-Block on Expiry

```yaml
on_waiver_expiry:
  action: AUTO_BLOCK
  behavior:
    - Remove waiver from registry
    - Re-enable finding in SAST/SCA scans
    - Flag PRs with expired waivers as blocked
    - Notify owner and security team
    - Create tracking issue for remediation
    
  example:
    PR #1234 blocked: SAST-SQL-001 waiver expired
    Finding: SQL Injection (HIGH severity)
    Previous waiver expired on: 2026-09-30
    Action required: Fix or request renewal within 7 days
```

### 6.3 Waiver Renewal

**Renewal process:**

```markdown
# Waiver Renewal Request

Original Waiver ID: W-2026-001
Finding: SAST-SQL-001
Current Expiry: 2026-09-30
Requested New Expiry: 2026-12-31

## Update to Remediation Plan
We completed the architecture review (completed on 2026-09-15).
Development begins Q4 2026:
  - Phase 1 (Oct): Data model migration
  - Phase 2 (Nov): Query refactoring
  - Phase 3 (Dec): Validation and cleanup
  - Expected completion: 2026-12-20

## Justification for Extension
3 months needed for safe migration of production queries.
Additional 90 days acceptable due to:
  1. Detailed implementation plan complete
  2. No new exposure
  3. Enhanced compensating controls in place
  4. Quarterly security audits scheduled

Approved: ✅ by @security-lead
Duration: 90 days (extended to 2026-12-31)
```

---

## 7. Audit Trail and Compliance

### 7.1 Audit Log

**Every waiver action logged:**

```
Timestamp: 2026-06-22T14:30:00Z
Action: WAIVER_CREATED
Finding: SAST-SQL-001
User: alice@company.com
IP: 192.168.1.100
Details:
  - Severity: HIGH
  - Duration: 90 days
  - Expiry: 2026-09-30
  - Owner: backend-team

Timestamp: 2026-06-22T15:45:00Z
Action: WAIVER_APPROVED
Finding: SAST-SQL-001
User: security-lead@company.com
IP: 192.168.1.101
Decision: APPROVED
Conditions: Input validation required, WAF rules enabled

Timestamp: 2026-06-22T16:00:00Z
Action: WAIVER_ACTIVATED
Finding: SAST-SQL-001
Result: Merge gate bypassed, PR #1234 unblocked
```

### 7.2 Compliance Reporting

**Monthly waiver report:**

```
Security Waiver Report - June 2026
═══════════════════════════════════

Active Waivers: 12
  ├─ CRITICAL: 0 ✅
  ├─ HIGH: 3
  ├─ MEDIUM: 7
  ├─ LOW: 2
  └─ Expired: 0

Waiver Approvals:
  ├─ Approved: 14
  ├─ Rejected: 2
  ├─ Expired: 1
  └─ Renewed: 3

Top Finding Types:
  1. Deprecated Dependencies: 4
  2. Medium CVE: 3
  3. Code Quality: 3
  4. License Issues: 2

Timeline Compliance:
  ├─ Fixed within 30 days: 33% (7/21)
  ├─ Fixed within 60 days: 62% (13/21)
  ├─ Expired overdue: 0% (0/21)
  └─ Renewed on time: 100% (3/3)

Recommendations:
  - 2 findings should be expedited (> 90 days open)
  - License policy review needed (GPL dependency growth)
```

---

## 8. Tools and Integration

### 8.1 GitHub Issue Template for Waivers

```markdown
---
name: Security Finding Waiver
about: Request a waiver for a security finding
title: "Waiver: [Finding Type] - [Brief Description]"
labels: ["security", "waiver"]
---

## Finding Details
- **Finding ID**: 
- **Severity**: 
- **Tool**: 
- **CWE**: 
- **File**: 

## Risk Assessment
[Explain exposure, likelihood, impact, compensating controls]

## Business Justification
[Why this finding cannot be fixed immediately]

## Remediation Plan
[Timeline and steps to fix]

## Approval
- [ ] Owner: 
- [ ] Security Lead: 
- [ ] CISO (if HIGH severity):
```

### 8.2 CLI Tool for Waiver Management

```bash
# Create waiver
waiver create --finding-id=SAST-SQL-001 --duration=90d \
  --justification-file=waiver.md

# Approve waiver
waiver approve --waiver-id=W-2026-001 --approver=security-lead

# List active waivers
waiver list --status=active --severity=HIGH

# Renew expiring waiver
waiver renew --waiver-id=W-2026-001 --new-duration=90d

# Audit log
waiver audit --waiver-id=W-2026-001

# Generate report
waiver report --month=2026-06
```

---

## 9. Policy Enforcement

### 9.1 Merge Gate Rules with Waivers

```yaml
branch-protection:
  required_checks:
    - SAST_Scan:
        allow_with_waiver: true
        check_expiry: true
        auto_block_on_expiry: true
        
    - SCA_Scan:
        allow_with_waiver: true
        check_expiry: true
        
security-rules:
  # Non-waiverable findings always block
  - if: finding.severity == "CRITICAL"
    then: block_merge  # No waiver possible
    
  # HIGH findings require waiver or fix
  - if: finding.severity == "HIGH"
    then: require(waiver OR fix)
    
  # MEDIUM findings can be waived
  - if: finding.severity == "MEDIUM"
    then: allow(waiver OR fix)
```

---

## 10. Success Criteria

For SEC-2 completion, verify:

- [ ] Waiver request template created
- [ ] Approval levels defined (Security Lead, CISO, Legal)
- [ ] Waiver eligibility criteria documented
- [ ] Non-waiverable findings clearly marked
- [ ] Waiver registry structure defined
- [ ] Expiry timeline and auto-block implemented
- [ ] Audit trail captures all waiver actions
- [ ] Compliance reporting templates created
- [ ] CLI tool for waiver management (or GitHub issues as registry)
- [ ] Monthly waiver report generation enabled
- [ ] Renewal process documented

---

## References

- NIST Risk Assessment: https://nvlpubs.nist.gov/nistpubs/PubsBy Topics/Topic_SecurityandPrivacy.html
- OWASP Risk Assessment: https://owasp.org/www-community/risks/
- ISO 27001 Risk Management: https://www.iso.org/standard/54534.html

**Next:** [TEST-1: Flaky Test Retry Policy](test-flaky-retry-policy.md)
