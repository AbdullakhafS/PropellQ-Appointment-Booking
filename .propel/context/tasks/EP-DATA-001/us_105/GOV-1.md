# GOV-1: Approval Checkpoint Controls

**Task ID:** GOV-1  
**Parent:** TASK-105  
**Category:** Governance and Audit  
**Points:** 3  
**Status:** Planned (after SAFE-2, VERIFY-2)  
**Created:** 2026-06-22

---

## 1. Objective

Establish mandatory approval gates that capture approver identity, timestamp, and rationale for all production migrations while enforcing least-privilege access controls.

---

## 2. Inputs

- PIPE-2: Environment promotion workflow
- Authentication and authorization infrastructure (GitHub/Azure DevOps)
- User role definitions (DBA, Platform-Eng, Developer)
- Audit logging system

---

## 3. Outputs

**Deliverables:**
- [ ] Approval gate implementation in CI/CD
- [ ] Approval data schema (version, approver, timestamp, rationale, approval_expires)
- [ ] Approval audit trail and query interface
- [ ] Least-privilege role definitions and enforcement
- [ ] Approval workflow documentation

---

## 4. Acceptance Criteria

1. **Approval Requirement:**
   - [ ] Manual approval required for production migrations
   - [ ] Dev/Test approvals automatic (CI/CD gates)
   - [ ] Staging requires approval from single team (Platform-Eng or DBA)
   - [ ] Prod requires approval from multiple teams (DBA + Platform-Eng)

2. **Approval Capture:**
   - [ ] Approver identity always recorded
   - [ ] Approval timestamp in ISO 8601 format
   - [ ] Approval rationale/comments captured
   - [ ] Approval valid for 24 hours (expires automatically)

3. **Least-Privilege Enforcement:**
   - [ ] Only DBAs/Platform-Eng can approve prod migrations
   - [ ] Developers cannot approve their own migrations
   - [ ] On-call has limited approval for emergency rollbacks
   - [ ] Role-based access control enforced

4. **Audit Trail:**
   - [ ] All approvals logged and immutable
   - [ ] Approval changes tracked (revoked, expired)
   - [ ] Queryable by version, approver, date range
   - [ ] Approval history retained per compliance policy

---

## 5. Implementation Details

### Approval Levels by Environment

| Environment | Auto-Approve | Manual Approval | Approvers | Approval Window |
|---|---|---|---|---|
| **DEV** | ✅ CI/CD gates | ❌ None | N/A | Immediate |
| **TEST** | ✅ CI/CD gates | ❌ None | N/A | Immediate |
| **STAGING** | ❌ Manual | ✅ Required | Platform-Eng | 24 hours |
| **PROD** | ❌ Manual | ✅ Required | DBA + Platform-Eng (2) | 24 hours |

### Approval Workflow

```
Commit to main with migration V005
  ↓
GitHub/Azure DevOps PR Created
  ↓
Code Review (2 approvals required)
  ├─ Approver 1: alice-smith (DBA)
  │  └─ "Approved - matches performance guidelines"
  ├─ Approver 2: bob-jones (Platform-Eng)
  │  └─ "Approved - no impact on other services"
  ↓
PR Merged to main
  ↓
Staging Deployment Approval (1 approver)
  ├─ Approver: carol-lee (Platform-Eng)
  │  └─ "Approved for staging validation"
  ├─ Valid until: 2026-06-23 14:30:00 UTC
  ↓
Staging Deployment Executed ✅
  ↓
Production Deployment Request (Awaits manual trigger)
  ↓
Approval Gate: Prod Migration Approval (2 required)
  ├─ Approver 1: alice-smith (DBA)
  │  Status: ✅ Approved at 2026-06-22T14:30:00Z
  │  Rationale: "Reviewed schema changes, tested rollback path"
  ├─ Approver 2: bob-jones (Platform-Eng)
  │  Status: ✅ Approved at 2026-06-22T14:35:00Z
  │  Rationale: "Validated no service compatibility issues"
  ├─ Valid until: 2026-06-23T14:30:00Z
  ↓
Production Deployment Executed ✅
  ↓
Approval Log Entry Created
  {
    version: "V005",
    environment: "prod",
    status: "approved",
    approvers: [
      { id: "alice-smith", timestamp: "2026-06-22T14:30:00Z", rationale: "..." },
      { id: "bob-jones", timestamp: "2026-06-22T14:35:00Z", rationale: "..." }
    ],
    approval_expires_at: "2026-06-23T14:30:00Z",
    deployed_at: "2026-06-22T14:40:00Z"
  }
```

### Approval Data Schema

```sql
CREATE TABLE migration_approvals (
  approval_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  migration_version VARCHAR(50) NOT NULL,           -- V005
  target_environment VARCHAR(50) NOT NULL,           -- prod, staging
  approval_status ENUM('pending', 'approved', 'rejected', 'expired'),
  
  -- First approver
  approver_1_id VARCHAR(100),                        -- alice-smith
  approver_1_timestamp DATETIME,
  approver_1_rationale TEXT,
  
  -- Second approver (for prod)
  approver_2_id VARCHAR(100),                        -- bob-jones
  approver_2_timestamp DATETIME,
  approver_2_rationale TEXT,
  
  -- Approval metadata
  approval_requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  approval_expires_at DATETIME NOT NULL,             -- +24 hours from first approval
  approval_revoked_at DATETIME,                      -- if revoked
  revoked_by VARCHAR(100),
  revoked_reason TEXT,
  
  -- Deployment metadata
  deployed_at DATETIME,
  deployed_by VARCHAR(100),                          -- ci-service-account
  deployment_duration_seconds INT,
  
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  UNIQUE INDEX idx_version_env (migration_version, target_environment),
  INDEX idx_approver_1 (approver_1_id),
  INDEX idx_approver_2 (approver_2_id),
  INDEX idx_expires (approval_expires_at)
) ENGINE=InnoDB;
```

### Least-Privilege Role Model

**Role Definitions:**

| Role | Permissions | Scope |
|---|---|---|
| **Developer** | Create PR with migrations | Any environment |
| | Review code | Any |
| | ❌ Approve migration | BLOCKED |
| | ❌ Deploy migration | BLOCKED |
| **Platform-Eng** | Create/review migrations | Any |
| | Approve staging migrations | Staging only |
| | Approve prod migrations | Prod (co-approval with DBA) |
| | Deploy migrations | Any (with approval) |
| **DBA** | Create/review migrations | Any |
| | Approve staging migrations | Staging only |
| | Approve prod migrations | Prod (co-approval with Platform-Eng) |
| | Deploy migrations | Any (with approval) |
| | Emergency rollback | Prod (no approval needed) |
| **On-Call** | Emergency rollback | Prod only |
| | ❌ Approve migrations | BLOCKED |

### GitHub Approval Gate Implementation

**CODEOWNERS File:**
```
# .github/CODEOWNERS
# Require approval from designated teams for migrations

db/migrations/ @dba-team @platform-eng-team
```

**Branch Protection Rules:**
```
Branch: main
  - Require pull request reviews before merging: ✅ 2
  - Require status checks to pass: ✅
    - ci/migration-validation
    - ci/lint-checks
    - ci/security-scan
  - Require branches to be up to date: ✅
  - Require approval from code owners: ✅
  - Dismiss stale PR approvals: ✅
```

**Approval Script (Python):**
```python
import datetime
from github import Github

def get_approvals(repo, pr_number):
    """Get all approvals for a PR"""
    pr = repo.get_pull(pr_number)
    
    approvals = []
    for review in pr.get_reviews():
        if review.state == "APPROVED":
            approvals.append({
                'approver_id': review.user.login,
                'timestamp': review.submitted_at.isoformat(),
                'rationale': review.body
            })
    
    return approvals

def validate_approval_permission(approver_id, environment):
    """Check if approver has permission to approve in environment"""
    dba_team = ['alice-smith', 'charlie-admin']
    platform_eng_team = ['bob-jones', 'diana-ops']
    
    if environment in ['prod', 'staging']:
        if approver_id in dba_team or approver_id in platform_eng_team:
            return True
    
    if environment in ['test', 'dev']:
        return True  # Any developer can approve non-prod
    
    return False

def check_approval_expiry(approval_timestamp):
    """Check if approval is still valid (24-hour window)"""
    approval_time = datetime.datetime.fromisoformat(approval_timestamp)
    expiry_time = approval_time + datetime.timedelta(hours=24)
    
    return datetime.datetime.now() < expiry_time

def record_approval(approval_data):
    """Record approval in audit database"""
    db.insert('migration_approvals', {
        'migration_version': approval_data['version'],
        'target_environment': approval_data['environment'],
        'approver_1_id': approval_data['approvers'][0]['id'],
        'approver_1_timestamp': approval_data['approvers'][0]['timestamp'],
        'approver_1_rationale': approval_data['approvers'][0]['rationale'],
        'approver_2_id': approval_data['approvers'][1]['id'] if len(approval_data['approvers']) > 1 else None,
        'approval_expires_at': calculate_expiry(approval_data['approvers'][0]['timestamp']),
        'approval_status': 'approved'
    })
```

### Approval Audit Queries

```sql
-- Query 1: All approvals for a specific migration
SELECT * FROM migration_approvals 
WHERE migration_version = 'V005' AND target_environment = 'prod';

-- Query 2: Approvals by approver
SELECT approver_1_id AS approver, COUNT(*) AS approval_count
FROM migration_approvals
WHERE target_environment = 'prod'
GROUP BY approver_1_id
ORDER BY approval_count DESC;

-- Query 3: Expired approvals
SELECT * FROM migration_approvals
WHERE approval_expires_at < NOW();

-- Query 4: Rejected approvals
SELECT * FROM migration_approvals
WHERE approval_status = 'rejected'
ORDER BY approval_requested_at DESC;

-- Query 5: Approval timeline (when approvals happen)
SELECT 
  DATE(approver_1_timestamp) AS approval_date,
  COUNT(*) AS total_approvals
FROM migration_approvals
WHERE target_environment = 'prod'
GROUP BY DATE(approver_1_timestamp)
ORDER BY approval_date DESC;
```

---

## 6. Success Metrics

- [ ] 100% of production migrations have approval records
- [ ] All approvers captured with identity and timestamp
- [ ] 0 deployments without valid approvals
- [ ] Approval audit trail immutable and queryable
- [ ] Approval expiry working (24-hour window)
- [ ] Least-privilege enforcement validated
- [ ] 0 unauthorized deployments

---

## 7. Definition of Done

- [ ] Approval gate configured in CI/CD
- [ ] Approval audit schema implemented
- [ ] Role-based access control enforced
- [ ] Approval capture working end-to-end
- [ ] Audit queries validated
- [ ] Tested with sample migrations
- [ ] Team trained on approval workflow
- [ ] Ready for AUDIT-1

---

## Next Task

→ AUDIT-1: Execution Logging and Traceability
