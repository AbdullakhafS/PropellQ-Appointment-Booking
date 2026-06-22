# SEC-2: Security Waiver and Exception Workflow

## Overview

This document defines the process for requesting, approving, and tracking security finding waivers and exceptions for TASK-101.

---

## 1. Waiver Types

### Type 1: False Positive Waiver

**Definition**: Tool reported finding that is not actually a vulnerability

**Example**: 
```python
# This flags as B105 (hardcoded_password) but is actually demo code
TEST_CREDENTIALS = {
    "username": "demo_user",
    "password": "demo_pass_12345"  # Not real credentials
}
```

**Approval**: Can be approved by developer lead or senior engineer  
**Duration**: Permanent (until next Bandit version bump)  
**Tracking**: Single waiver request, documented in `.propel/waivers/`

### Type 2: Risk Acceptance Waiver

**Definition**: Finding is real but acceptable risk in specific context

**Example**:
```python
# This is intentional - we need eval for user formula evaluation
# Risk: Formula stored in database cannot be modified by user
result = eval(user_formula)  # Risk accepted in READ_ONLY context
```

**Approval**: Requires security review by security@propellq.com  
**Duration**: Time-limited (30/60/90 days based on risk)  
**Tracking**: Formal waiver record with business justification

### Type 3: Remediation Defer Waiver

**Definition**: Finding is valid but fix deferred to future sprint

**Example**:
```
- Finding: B104 (hardcoded_bind_all_interfaces)
- Current: bind("0.0.0.0")  # Needed for Docker network discovery
- Fix: Extract to env var (planned for v1.2)
- Risk: Temporary until v1.2 release
```

**Approval**: Team lead + product owner  
**Duration**: Capped at next sprint (2-4 weeks)  
**Tracking**: Issue created in backlog, waiver references ticket

---

## 2. Waiver Request Process

### Step 1: Detect Finding (CI Reports)

CI workflow detects HIGH/CRITICAL finding:

```
❌ Security gate failed: HIGH/CRITICAL SAST findings detected

Finding: B105 - Hardcoded Password String
File: app/src/config.py:45
Severity: HIGH
Text: Possible hardcoded password: '***'

Action Required: Fix code, request waiver, or contact security team
```

### Step 2: Create Waiver Request

**For developers**: Create file in `.propel/waivers/` directory:

**Filename format**: `{TOOL}_{FINDING_ID}_{DESCRIPTION}_{DATE}.md`

**Example**: `.propel/waivers/bandit_b105_demo_credentials_2026_06_22.md`

**Minimal Content**:

```yaml
---
waiver_type: false_positive  # false_positive | risk_acceptance | remediation_defer
finding_tool: bandit
finding_id: B105
severity: HIGH
status: pending  # pending | approved | expired | revoked
requested_by: alice@propellq.com
requested_date: 2026-06-22
approver: bob@propellq.com (security lead)
approval_date: null
expiry_date: null  # null = permanent | 2026-07-22 (30 days)
business_justification: null
technical_details: null
---

## Waiver Details

### Finding

- **Tool**: Bandit
- **Check**: B105 - Hardcoded Password String
- **Severity**: HIGH
- **File**: app/src/config.py
- **Line**: 45
- **Code Snippet**:
  ```python
  TEST_CREDENTIALS = {
      "username": "test_user",
      "password": "test_pass_123"
  }
  ```

### Justification

This is a false positive. The credentials are:
- Only used in unit tests (never in production)
- Stored in test fixtures, not application code
- Not real credentials (test values only)
- Isolated to test environment

### Mitigation

- Code is in test file only
- Not accessible from production application
- Credentials rotated periodically as part of CI test suite setup

### Approval

- **Requested**: alice@propellq.com on 2026-06-22
- **Approved**: bob@propellq.com on 2026-06-22
- **Expires**: Permanent (no expiry)
```

### Step 3: Submit for Approval

**For Low-Risk Waivers** (False Positive):
1. Create `.md` file in `.propel/waivers/`
2. Comment on PR: "@security-team-review false-positive-waiver in .propel/waivers/"
3. Developer lead reviews and approves
4. Update `status: approved` in file

**For Higher-Risk Waivers** (Risk Acceptance):
1. Create `.md` file with full business justification
2. Create issue: `[SECURITY WAIVER] {finding_id} - {description}`
3. Assign to security@propellq.com
4. Security team reviews and:
   - Approves with time limit, OR
   - Requires fix instead of waiver
5. Update waiver file with approval and expiry date

**Process Duration**:
- False positive: 24 hours
- Risk acceptance: 3-5 business days
- If not approved within SLA, PR remains blocked

### Step 4: Apply to CI

Once waiver approved, add to `.propel/security/.waiver-registry`:

```yaml
# .propel/security/.waiver-registry

waivers:
  - finding_id: B105
    file_pattern: "app/src/config.py"
    line_range: "45"
    expiry_date: null
    waiver_file: ".propel/waivers/bandit_b105_demo_credentials_2026_06_22.md"
    status: active

  - finding_id: B104
    file_pattern: "app/src/web_app.py"
    line_range: "120-130"
    expiry_date: "2026-07-22"
    waiver_file: ".propel/waivers/bandit_b104_docker_bind_2026_06_22.md"
    status: active
    reason: "Deferred to v1.2 release - issue #1234"
```

### Step 5: CI Verification

Updated CI workflow:

```python
# During security job:
1. Run bandit as normal
2. Load waiver registry
3. For each finding:
   - Check if in waiver registry
   - If yes: suppress finding, note as waived
   - If no: fail the check
4. Report:
   - "✅ X findings (Y waived, Z active issues)"
   - If any active HIGH/CRITICAL: ❌ Block merge
```

---

## 3. Waiver Lifecycle

### Active Waivers

**Tracking**: All active waivers tracked in `.propel/security/.waiver-registry`

**Monthly Review**:
```bash
# List all active waivers expiring in next 30 days
grep -r "expiry_date: 202[6-9]" .propel/waivers/*.md | \
  sort | \
  head -20
```

**Automated Expiry Notification** (weekly):
```
❌ Waiver Expiry Alert

The following waivers expire in 7 days:
- B105 (demo_credentials): expires 2026-07-22
- B104 (docker_bind): expires 2026-07-29

Action Required:
1. Fix the issue, OR
2. Request renewal by updating waiver file expiry_date

If not renewed, security gate will block merge.
```

### Renewing a Waiver

To extend expiry:

1. Update waiver file:
```yaml
status: approved
expiry_date: 2026-08-22  # Extend another 30 days
approval_date: 2026-06-22
renewer: charlie@propellq.com
renewal_date: 2026-06-30
renewal_reason: "Fix deferred to v1.3, tracking in #2045"
```

2. Update waiver registry with new expiry
3. Note renewal in PR comment if currently blocking a PR

### Revoking a Waiver

If vulnerability is fixed or becomes too risky:

1. Delete entry from `.propel/security/.waiver-registry`
2. Update waiver file:
```yaml
status: revoked
revoked_by: security@propellq.com
revoked_date: 2026-06-30
revocation_reason: "Issue #1234 fixed in commit abc123"
```

3. Next CI run will fail if finding still present
4. Dev team must fix or request new waiver

---

## 4. Waiver Audit Trail

All waivers automatically generate audit:

```
.propel/security/.audit-log

2026-06-22T10:30:00Z | CREATED  | B105 | app/src/config.py:45 | alice@propellq.com
2026-06-22T14:15:00Z | APPROVED | B105 | app/src/config.py:45 | bob@propellq.com
2026-06-30T09:00:00Z | RENEWED  | B105 | app/src/config.py:45 | charlie@propellq.com
```

**Audit includes**:
- Timestamp
- Action (CREATED/APPROVED/RENEWED/REVOKED/EXPIRED)
- Finding ID
- File/location
- Actor (who approved)
- Status after action

---

## 5. Waiver Statistics

**Dashboard View** (`.propel/security/dashboard.json`):

```json
{
  "total_active_waivers": 3,
  "by_type": {
    "false_positive": 2,
    "risk_acceptance": 1,
    "remediation_defer": 0
  },
  "by_tool": {
    "bandit": 2,
    "pip_audit": 1
  },
  "by_severity": {
    "CRITICAL": 0,
    "HIGH": 2,
    "MEDIUM": 1
  },
  "expiring_soon": [
    {
      "finding_id": "B104",
      "expires_in_days": 7,
      "waiver_file": ".propel/waivers/bandit_b104_docker_bind_2026_06_22.md"
    }
  ],
  "metrics": {
    "false_positive_rate": "67%",
    "avg_waiver_duration_days": 45,
    "waivers_renewed": 1,
    "waivers_expired": 0
  }
}
```

---

## 6. Escalation Path

### Waiver Request Blocked?

1. **First Contact**: Team lead or development manager
2. **Escalation 1**: Security team lead (bob@propellq.com)
3. **Escalation 2**: CISO or Security Director
4. **Final**: CTO/Product VP for business-critical exceptions

### When Escalation Needed

- Finding affects critical production path
- Fix would delay release > 1 week
- Finding is strategic (not security-only issue)
- Waiver requested for >60 days

---

## 7. Common Scenarios & Handling

### Scenario 1: False Positive in Test Code

```
Finding: B105 - Hardcoded password in app/tests/test_auth.py:50
Waiver Type: false_positive
Approval: Developer lead (24 hours)
Expires: Permanent
```

**Template**: Copy `.propel/waivers/TEMPLATE_FALSE_POSITIVE.md`

### Scenario 2: Valid Vulnerability, Fix Deferred

```
Finding: B104 - Bind to 0.0.0.0 in app/src/web_app.py:120
Current Mitigation: Network isolation via container orchestration
Fix: Extract to env var (planned v1.2)
Waiver Type: remediation_defer
Approval: Team lead + Product owner (48 hours)
Expires: 2026-07-22 (next sprint)
```

**Process**: Create issue #1234, reference in waiver

### Scenario 3: Dependency Vulnerability, No Patch

```
Finding: pip-audit CRITICAL in package==1.0.0
Root Cause: Transitive dependency outdated
Current Status: No patch available from upstream
Mitigation: Pin parent to version with fixed dependency tree
Waiver Type: risk_acceptance (temporary)
Approval: Security team (5 days)
Expires: 2026-07-22 (must upgrade by then)
```

**Action**: Create ticket to upgrade dependency

---

## 8. Documentation

All waivers stored in:
```
.propel/security/
├── .waiver-registry          (active waivers index)
├── .audit-log                (audit trail)
├── .waiver-stats             (metrics)
├── WAIVERS/
│   ├── bandit_b105_demo_2026_06_22.md
│   ├── bandit_b104_docker_2026_06_22.md
│   └── ...
└── TEMPLATES/
    ├── TEMPLATE_FALSE_POSITIVE.md
    ├── TEMPLATE_RISK_ACCEPTANCE.md
    └── TEMPLATE_REMEDIATION_DEFER.md
```

---

## 9. Compliance

**Requirements**:

✅ All waivers require written justification  
✅ All waivers must be time-limited (except false positives)  
✅ All waivers auditable and traceable  
✅ All waivers reviewed at least quarterly  
✅ All waivers expiring documented  
✅ All waivers have defined rollback/fix plan  

**Non-Compliance Consequences**:

- Expired waiver = security gate blocks merge
- Missing waiver documentation = PR rejected
- Waiver abuse = escalation to management

---

## 10. Contact & Support

- **Security Questions**: security@propellq.com
- **Waiver Approval**: bob@propellq.com (security lead)
- **Escalation**: cto@propellq.com
- **Slack Channel**: #security-waivers

---

**Last Updated**: 2026-06-22  
**Approved By**: Security Team  
**Effective Date**: 2026-06-22  
**Next Review**: 2026-09-22
