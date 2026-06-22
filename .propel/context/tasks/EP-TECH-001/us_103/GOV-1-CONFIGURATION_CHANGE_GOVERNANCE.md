# GOV-1: Configuration Change Governance

**Author**: Governance & Compliance Team  
**Date**: 2026-06-22  
**Status**: Active  
**Version**: 1.0  

---

## 1. Overview

This document defines the ownership, review requirements, and approval workflow for configuration schema changes. All changes to required configuration keys or constraints must follow this process.

---

## 2. Governance Roles

### 2.1 Roles and Responsibilities

| Role | Responsibilities | Authority |
|------|------------------|-----------|
| **Change Requester** | Proposes schema change with justification | Initiates request |
| **Platform Lead** | Owns config schema, reviews technical feasibility | Approves/rejects |
| **Product Manager** | Owns feature requirements, reviews business impact | Approves/rejects |
| **Security Lead** | Reviews access implications, audit impact | Approves/rejects |
| **Operations Lead** | Reviews deployment complexity, runbook updates | Approves/rejects |
| **Compliance Officer** | (Optional for audit-related changes) Reviews regulatory impact | Approves/rejects |

### 2.2 RACI Matrix

| Activity | Requester | Platform | Product | Security | Operations | Compliance |
|----------|-----------|----------|---------|----------|------------|------------|
| Submit request | R | | | | | |
| Technical review | I | R, A | C | C | C | |
| Business review | I | C | R, A | | C | |
| Security review | I | C | C | R, A | C | |
| Deploy to staging | I | A | | | R | |
| Monitor staging | I | R | | | C | |
| Promote to prod | I | A | | | R | |
| Audit documentation | I | R | | C | | R/A |

---

## 3. Change Request Process

### 3.1 Step 1: Submit Request

**Form: Configuration Change Request**

```markdown
## Configuration Change Request

### Metadata
- **Request ID**: CFG-CHANGE-2026-001
- **Requested by**: [Your Name]
- **Date**: 2026-06-22
- **Type**: Add/Modify/Remove/Rename

### Change Details
- **Service(s) Affected**: web_app, booking_service
- **Current Schema Version**: 1.0
- **Proposed Schema Version**: 1.1

### Specific Changes
```yaml
Current:
  DATABASE_POOL_SIZE:
    type: integer
    default: 10
    min: 2
    max: 100

Proposed:
  DATABASE_POOL_SIZE:
    type: integer
    default: 20        # Changed
    min: 2
    max: 200           # Changed
```

### Justification
**What**: Increase default database pool size  
**Why**: Performance testing shows 10 connections insufficient for peak load  
**Impact**: Will improve p99 latency by ~500ms  
**Timeline**: Needed by July 1st for summer campaign

### Technical Details
- Impact on services: web_app (direct), booking_service (indirect)
- Backward compatibility: Fully backward compatible (only increases default)
- Deployment complexity: Low (config-only change, no code changes)
- Testing: Load tested with new pool size in staging

### Risk Assessment
- **Risk Level**: LOW
- **Rollback Complexity**: LOW (revert config change)
- **Dependencies**: None
- **Conflicts**: None identified
```

### 3.2 Step 2: Platform Lead Review

Platform Lead reviews for technical feasibility:

```yaml
Review Checklist (Platform Lead):
  - [ ] Schema change is valid and follows naming conventions
  - [ ] No conflicts with existing schema
  - [ ] Backward compatibility verified
  - [ ] Migration path documented (if needed)
  - [ ] Performance impact assessed
  - [ ] All services using this key identified
  - [ ] Code changes required? Identified and planned
  - [ ] Recommended version number increment (major/minor/patch)
  - [ ] Deployment order documented
  
Recommendation: APPROVE / REQUEST_CHANGES / REJECT
```

**Approval Comment**:
```
Reviewed by: John Smith (Platform Lead)
Date: 2026-06-22
Status: APPROVED

Comments:
- Change is technically sound
- Backward compatible as noted
- Pool size increase aligns with load testing results
- Recommend staging validation for 48 hours before prod
- No code changes required
- Document updated default in runbook

Approved pending Product review.
```

### 3.3 Step 3: Product Manager Review

Product Manager reviews business impact:

```yaml
Review Checklist (Product Manager):
  - [ ] Change aligns with product roadmap
  - [ ] Business justification clear and compelling
  - [ ] User/feature impact assessed
  - [ ] Timeline and dependencies realistic
  - [ ] Go/no-go criteria defined
  - [ ] Communication plan for affected teams
  - [ ] Documentation and training needs identified

Recommendation: APPROVE / REQUEST_CHANGES / REJECT
```

**Approval Comment**:
```
Reviewed by: Sarah Johnson (Product Manager)
Date: 2026-06-22
Status: APPROVED

Comments:
- Performance improvement directly benefits users
- No user-facing changes required
- Summer campaign timeline makes sense
- Internal teams should be notified pre-deployment

Approved pending Security review.
```

### 3.4 Step 4: Security Lead Review

Security Lead reviews access and audit implications:

```yaml
Review Checklist (Security Lead):
  - [ ] No new secrets exposed
  - [ ] Access control implications assessed
  - [ ] Audit logging sufficient
  - [ ] Compliance implications reviewed
  - [ ] No breaking changes to security model
  - [ ] Change record captured for audit

Recommendation: APPROVE / REQUEST_CHANGES / REJECT
```

**Approval Comment**:
```
Reviewed by: Michael Chen (Security Lead)
Date: 2026-06-22
Status: APPROVED

Comments:
- No security implications identified
- Change is non-security-related
- Existing audit logging sufficient
- Will document in quarterly compliance report

Approved pending Operations review.
```

### 3.5 Step 5: Operations Lead Review

Operations Lead reviews deployment and runbook updates:

```yaml
Review Checklist (Operations Lead):
  - [ ] Deployment procedure documented
  - [ ] Rollback procedure documented
  - [ ] Monitoring alerts updated/verified
  - [ ] On-call team briefed on change
  - [ ] Runbooks updated with new config
  - [ ] Troubleshooting guides updated
  - [ ] Rollback SLA defined (<5 minutes)

Recommendation: APPROVE / REQUEST_CHANGES / REJECT
```

**Approval Comment**:
```
Reviewed by: Alex Martinez (Operations Lead)
Date: 2026-06-22
Status: APPROVED

Comments:
- Deployment is straightforward (config reload)
- Rollback simply reverts pool size to 10
- Updated monitoring to track active connections
- Added runbook entry for tuning pool size
- On-call team briefed

Ready for deployment. Recommend 24-hour staging validation.
```

---

## 4. Approval SLAs

### 4.1 SLA Matrix

| Complexity | Straightforward | Moderate | Complex | Critical |
|-----------|-----------------|----------|---------|----------|
| **Definition** | Config-only, low risk | Some code changes, medium risk | Major schema change, high risk | Urgent, security-related |
| **SLA** | 1 business day | 3 business days | 5 business days | 4 business hours |
| **Approvals** | Platform, Product, Security | All + Operations | All + Compliance | Exec override possible |
| **Example** | Default value change | New optional key | Key rename | Security misconfiguration |

### 4.2 Escalation Path

```
Day 1: Request submitted
Day 1: Platform Lead review (1-2 hours)
       ├─ Approved → Step 3
       ├─ Changes requested → Requester updates
       └─ Rejected → Close with explanation

Day 2: Product Manager review (1-2 hours)
       ├─ Approved → Step 4
       ├─ Changes requested → Requester updates
       └─ Rejected → Close with explanation

Day 2-3: Security Lead review (1-2 hours)
       ├─ Approved → Step 5
       ├─ Changes requested → Requester updates
       └─ Rejected → Close with explanation

Day 3: Operations Lead review (1-2 hours)
       ├─ Approved → Ready for deployment
       ├─ Changes requested → Requester updates
       └─ Rejected → Close with explanation

Stuck? After 24 hours waiting, escalate to Platform Director
```

---

## 5. Emergency and Expedited Changes

### 5.1 Emergency Change Process (< 1 hour)

For urgent security or critical operational issues:

```
Emergency change triggered by:
  1. Security vulnerability discovered
  2. Service unavailable due to config issue
  3. Critical business impact (e.g., payment system down)

Process:
  1. On-call Tech Lead approves emergency change
  2. Change implemented with incident ticket
  3. Post-implementation review within 24 hours
  4. Full governance review within 1 week
  5. Communication sent to all stakeholders

Example:
  - Incident: "Database connection pool exhausted"
  - Emergency fix: Increase DATABASE_POOL_SIZE from 10 to 50
  - On-call approval: Given immediately
  - Post-incident review: Permanent pool size increase approved through normal process
```

### 5.2 Expedited Change Process (< 4 hours)

For high-priority business changes:

```
Expedited change requested by Product Manager with:
  1. Business justification
  2. Urgency level (days until needed)
  3. Risk assessment
  4. Proposed testing plan

Fast-track reviewers:
  - Platform Lead: 30 min review
  - Product Manager: Requestor (already involved)
  - Security Lead: 30 min review
  - Operations Lead: 30 min review

Total: ~2 hours vs 1 business day normal SLA
```

---

## 6. Version Numbering

### 6.1 Semantic Versioning

```
MAJOR.MINOR.PATCH

Examples:
  1.0.0 - Initial schema version
  1.1.0 - Added optional DATABASE_REPLICA_HOST
  1.1.1 - Updated constraint on DATABASE_POOL_SIZE
  1.2.0 - Added feature flags category
  2.0.0 - Breaking change: renamed DATABASE_USER to DATABASE_USERNAME
```

### 6.2 Change Types and Version Bumps

| Change Type | Version Bump | Example | Backward Compatible |
|-------------|-------------|---------|-------------------|
| New optional key | Minor (1.0→1.1) | Add optional `CACHE_TTL` | Yes |
| New required key | Major (1.0→2.0) | Add required `SERVICE_ID` | No |
| Rename key | Major (1.0→2.0) | `DB_PASS`→`DATABASE_PASSWORD` | No |
| Change type | Major (1.0→2.0) | `PORT` from string to int | No |
| Relax constraint | Minor (1.0→1.1) | Widen port range | Yes |
| Tighten constraint | Patch (1.0→1.0.1) | Reduce pool size max | Maybe |
| Default value change | Patch (1.0→1.0.1) | `LOG_LEVEL: INFO`→`DEBUG` | Yes |

---

## 7. Documentation and Communication

### 7.1 Changelog Maintenance

```yaml
# CONFIGURATION_CHANGELOG.yaml

changes:
  - version: "1.1.0"
    date: 2026-06-25
    type: feature
    description: "Increased default database pool size"
    changes:
      - "DATABASE_POOL_SIZE default: 10 → 20"
      - "DATABASE_POOL_SIZE max: 100 → 200"
    impact: "Improves p99 latency by ~500ms under peak load"
    migration: "Automatic, backward compatible"
    approved_by: "Platform Lead, Product Manager, Security Lead, Operations Lead"
    
  - version: "1.0.1"
    date: 2026-06-20
    type: bug_fix
    description: "Fixed LOG_LEVEL enum documentation"
    changes:
      - "Added 'CRITICAL' to LOG_LEVEL allowed values"
    impact: "Documentation only, no runtime changes"
    migration: "No action required"
    approved_by: "Platform Lead"
```

### 7.2 Stakeholder Communication

**Template: Configuration Change Announcement**

```markdown
Subject: Configuration Schema Update v1.1.0

Hi Team,

We have approved and are preparing to deploy a configuration schema update.

## What's changing?
- DATABASE_POOL_SIZE default increased from 10 to 20
- DATABASE_POOL_SIZE maximum increased from 100 to 200

## Why?
Performance testing in staging showed that the current pool size is insufficient
during peak load periods, resulting in connection timeouts. This change enables
better connection reuse and reduces p99 latency by approximately 500ms.

## When?
- Staging deployment: 2026-06-25
- Production deployment: 2026-06-28 (after 48-hour staging validation)

## What do you need to do?
- Update any custom deployment scripts using old pool sizes
- Monitor performance metrics after deployment
- Report any connection-related issues in #performance-incidents

## Questions?
Reach out to the Platform Team in #platform-engineering

Thanks,
Platform Engineering Team
```

---

## 8. Compliance and Audit Trail

### 8.1 Change Record Template

```yaml
# .propel/config/changes/CFG-CHANGE-2026-001.yaml

request_id: CFG-CHANGE-2026-001
submitted_at: 2026-06-22T10:00:00Z
submitted_by: alice@example.com

change:
  title: "Increase database pool size"
  description: "Increase default pool size from 10 to 20 for better performance"
  services_affected:
    - web_app
    - booking_service
  
  schema_changes:
    - key: DATABASE_POOL_SIZE
      field: default
      old_value: 10
      new_value: 20
    - key: DATABASE_POOL_SIZE
      field: max
      old_value: 100
      new_value: 200

approvals:
  - role: platform_lead
    reviewer: john.smith@example.com
    decision: approved
    timestamp: 2026-06-22T11:00:00Z
    comment: "Technically sound, backward compatible"
  
  - role: product_manager
    reviewer: sarah.johnson@example.com
    decision: approved
    timestamp: 2026-06-22T12:00:00Z
    comment: "Performance improvement directly benefits users"
  
  - role: security_lead
    reviewer: michael.chen@example.com
    decision: approved
    timestamp: 2026-06-22T13:00:00Z
    comment: "No security implications"
  
  - role: operations_lead
    reviewer: alex.martinez@example.com
    decision: approved
    timestamp: 2026-06-22T14:00:00Z
    comment: "Deployment straightforward, runbook updated"

deployment:
  staged_at: 2026-06-25T09:00:00Z
  staged_by: devops@example.com
  production_at: 2026-06-28T14:00:00Z
  production_by: devops@example.com
  
  validation:
    staging_passed: true
    production_validation_duration: "24 hours"
    rollback_executed: false
    final_status: "successful"

schema_version_updated: "1.0.0" → "1.1.0"
```

---

## 9. Known Limitations

### 9.1 v1.0 Limitations

```
Current scope:
  ✓ Change request process
  ✓ Multi-level approvals
  ✓ SLA tracking
  ✓ Audit trail
  ✗ Automated approval workflows (v1.1)
  ✗ Compliance rule engine (v1.1)
  ✗ Integration with Jira/GitHub Issues (v1.1)

Planned enhancements:
  - v1.1: Automate low-risk approval workflows
  - v1.1: Custom compliance rules
  - v1.1: Jira/GitHub integration for issue tracking
  - v1.2: AI-powered risk assessment
```

---

## References

- [CFG-1: Configuration Schema and Catalog](CFG-1-CONFIGURATION_SCHEMA_AND_CATALOG.md)
- [AUDIT-1: Access and Change Audit Trail](AUDIT-1-ACCESS_AND_CHANGE_AUDIT_TRAIL.md)
