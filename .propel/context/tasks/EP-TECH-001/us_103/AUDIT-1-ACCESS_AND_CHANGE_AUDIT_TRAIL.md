# AUDIT-1: Access and Change Audit Trail

**Author**: Security & Compliance Team  
**Date**: 2026-06-22  
**Status**: Active  
**Version**: 1.0  

---

## 1. Overview

This document defines audit logging for secret access and configuration changes. All events are logged, retrievable for audit/compliance review, and retained according to policy.

---

## 2. Audit Event Categories

### 2.1 Secret Access Audit Events

Every access to a secret is logged:

```yaml
Event Type: secret.accessed
Timestamp: 2026-06-22T14:30:15Z
Service: web_app
Secret Path: prod/database/master_password
Secret ARN: arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/database/master_password
Action: GetSecretValue
Principal: arn:aws:iam::ACCOUNT_ID:role/propellq-web-app-prod
Result: SUCCESS
Latency: 145ms
Source IP: 10.0.1.50 (EC2 instance)
User Agent: boto3/1.26.0

Event Type: secret.accessed
Timestamp: 2026-06-22T14:31:02Z
Service: booking_service
Secret Path: prod/booking/service_api_key
Action: GetSecretValue
Principal: arn:aws:iam::ACCOUNT_ID:role/propellq-booking-service-prod
Result: SUCCESS
Latency: 98ms

Event Type: secret.access_denied
Timestamp: 2026-06-22T14:32:45Z
Principal: arn:aws:iam::ACCOUNT_ID:user/developer@example.com
Secret Path: prod/database/master_password
Action: GetSecretValue
Result: ACCESS_DENIED (insufficient permissions)
Reason: User lacks secretsmanager:GetSecretValue on this secret
```

### 2.2 Configuration Change Audit Events

Every configuration change is logged:

```yaml
Event Type: config.changed
Timestamp: 2026-06-22T15:00:00Z
Change ID: CFG-CHANGE-2026-001
Change Type: schema_update
Service: web_app, booking_service
Schema Version: 1.0.0 → 1.1.0

Changed Keys:
  - DATABASE_POOL_SIZE.default: 10 → 20
  - DATABASE_POOL_SIZE.max: 100 → 200

Approver: alex.martinez@example.com (Operations Lead)
Staged At: 2026-06-25T09:00:00Z
Staged By: devops@example.com
Produced At: 2026-06-28T14:00:00Z
Deployed By: devops@example.com

Environment: production
Duration: 00:15:32
Status: SUCCESS
Rollback Needed: false
```

### 2.3 Secret Rotation Audit Events

```yaml
Event Type: secret.rotated
Timestamp: 2026-06-22T20:00:00Z
Secret Path: prod/database/master_password
Rotation ID: ROT-2026-06-001

Phases:
  - Phase 1 (Create): 2026-06-22T20:00:00Z - SUCCESS
  - Phase 2 (Validate): 2026-06-22T20:15:00Z - SUCCESS
  - Phase 3 (Staging): 2026-06-22T20:30:00Z - SUCCESS
  - Phase 4 (Production): 2026-06-22T21:00:00Z - SUCCESS
  - Phase 5 (Archive): 2026-06-22T21:30:00Z - SUCCESS

Old Version: v5 (ARCHIVED)
New Version: v6 (AWSCURRENT)
Orchestrator Role: rotation-automation@example.com

Services Affected: web_app, booking_service, search_service
Health Status During Rotation: OK (no errors)
Rollback Count: 0
```

### 2.4 Access Control Change Events

```yaml
Event Type: iam_policy.changed
Timestamp: 2026-06-22T10:00:00Z
Role: propellq-web-app-prod
Change Type: policy_attached

Policy Name: web-app-secrets-v2
Policy ARN: arn:aws:iam::ACCOUNT_ID:policy/web-app-secrets-v2

Changes:
  - Added: secretsmanager:GetSecretValue on prod/auth/secret_key-*
  - Added: secretsmanager:GetSecretValue on prod/aws/*
  - Removed: secretsmanager:GetSecretValue on dev/*

Changed By: john.smith@example.com (Platform Lead)
Change Request: CFG-CHANGE-2026-002

Reason: "Production service now needs AWS credentials for S3 uploads"
Approval: Completed 2026-06-22T09:30:00Z
Effective Date: 2026-06-22T10:00:00Z
```

---

## 3. Audit Log Storage

### 3.1 Multi-Tier Storage Architecture

```
Tier 1 (Hot - 30 days)
  └─ CloudWatch Logs
     └─ Log group: /aws/secretsmanager/audit
     └─ Retention: 30 days
     └─ Search: Real-time via CloudWatch Insights
     └─ Use case: Incident investigation

Tier 2 (Warm - 90 days)
  └─ S3 (Standard storage)
     └─ Bucket: propellq-audit-logs
     └─ Path: s3://propellq-audit-logs/secrets/{date}/
     └─ Retention: 90 days (via lifecycle policy)
     └─ Use case: Compliance review

Tier 3 (Cold - 7 years)
  └─ S3 Glacier
     └─ Bucket: propellq-audit-archive
     └─ Retention: 7 years
     └─ Use case: Long-term compliance/legal hold
     └─ Retrieval time: 1-5 minutes (Expedited tier)
```

### 3.2 Audit Log Format

```json
{
  "timestamp": "2026-06-22T14:30:15.123Z",
  "event_type": "secret.accessed",
  "event_id": "evt-7f4a9c2b1e8d3f6a",
  "trace_id": "trace-abc123def456",
  
  "service": {
    "name": "web_app",
    "version": "2.1.0",
    "instance_id": "i-0a1b2c3d4e5f6g7h8"
  },
  
  "principal": {
    "type": "role",
    "arn": "arn:aws:iam::123456789012:role/propellq-web-app-prod",
    "user_id": "AIDZ1EXAMPLE",
    "account_id": "123456789012"
  },
  
  "action": {
    "name": "GetSecretValue",
    "resource": "prod/database/master_password",
    "resource_arn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/database/master_password-*"
  },
  
  "result": {
    "status": "SUCCESS",
    "error_code": null,
    "error_message": null,
    "http_status": 200
  },
  
  "performance": {
    "duration_ms": 145,
    "cache_hit": false
  },
  
  "network": {
    "source_ip": "10.0.1.50",
    "user_agent": "boto3/1.26.0"
  },
  
  "environment": {
    "aws_region": "us-east-1",
    "environment": "prod"
  }
}
```

---

## 4. Audit Retrieval

### 4.1 CloudWatch Insights Queries

**Recent secret access by service**:

```
fields timestamp, service, action, result.status
| filter event_type = "secret.accessed"
| filter timestamp > ago(1h)
| stats count() by service, result.status
```

**Failed access attempts**:

```
fields timestamp, principal, action, error_message
| filter event_type = "secret.accessed"
| filter result.status = "ACCESS_DENIED"
| filter timestamp > ago(24h)
```

**Secret rotation audit trail**:

```
fields timestamp, event_type, "secret.rotated".phases
| filter event_type = "secret.rotated"
| filter timestamp > ago(7d)
```

**Configuration changes in last 30 days**:

```
fields timestamp, "config.changed".change_id, "config.changed".service
| filter event_type = "config.changed"
| filter timestamp > ago(30d)
```

### 4.2 S3 Audit Log Retrieval

**Query via Athena**:

```sql
-- Retrieve all secret access in last 7 days
SELECT
  timestamp,
  service.name,
  principal.arn,
  action.name,
  result.status,
  performance.duration_ms
FROM audit_logs
WHERE
  event_type = 'secret.accessed'
  AND timestamp > current_timestamp - interval '7' day
ORDER BY timestamp DESC
LIMIT 1000;

-- Find configuration changes
SELECT
  timestamp,
  json_extract(event, '$.change_id'),
  json_extract(event, '$.service'),
  json_extract(event, '$.approver')
FROM audit_logs
WHERE
  event_type = 'config.changed'
  AND timestamp > current_timestamp - interval '90' day
ORDER BY timestamp DESC;
```

### 4.3 AWS CLI Access

```bash
# Export recent audit logs
aws logs describe-log-streams \
  --log-group-name /aws/secretsmanager/audit \
  --query 'logStreams[].[logStreamName,lastEventTimestamp]' \
  --sort ascending

# Get logs for specific service
aws logs filter-log-events \
  --log-group-name /aws/secretsmanager/audit \
  --filter-pattern '{ $.service.name = "web_app" }' \
  --start-time $(date -d '24 hours ago' +%s)000

# Export to CSV
aws logs get-log-events \
  --log-group-name /aws/secretsmanager/audit \
  --log-stream-name "2026/06/22/prod" \
  --query 'events[].[timestamp,message]' \
  --output text > audit_logs.txt
```

---

## 5. Compliance Reporting

### 5.1 Monthly Audit Report

```markdown
# Configuration and Secrets Audit Report
## June 2026

### Executive Summary
- Total secret access events: 15,247
- Failed access attempts: 12 (0.08%)
- Configuration changes: 3
- All changes approved and documented

### Secret Access Statistics
- Services accessing secrets: 5
- Unique secrets accessed: 18
- Average access latency: 124ms

### Top Secret Access (by service)
1. web_app: 8,925 accesses (58.5%)
2. booking_service: 4,102 accesses (26.9%)
3. search_service: 1,845 accesses (12.1%)
4. notification_service: 268 accesses (1.8%)
5. admin_dashboard: 107 accesses (0.7%)

### Configuration Changes
1. CFG-CHANGE-2026-001: Increased DATABASE_POOL_SIZE (2026-06-25)
   - Impact: Improved p99 latency
   - Status: Deployed successfully

2. CFG-CHANGE-2026-002: Added AWS credentials to web_app (2026-06-15)
   - Impact: S3 upload capability
   - Status: Deployed successfully

3. CFG-CHANGE-2026-003: Security hotfix for LOG_LEVEL (2026-06-08)
   - Impact: Added CRITICAL level
   - Status: Deployed successfully

### Failed Access Attempts
- 12 total failed attempts (0.08% of all access)
- All failures due to insufficient IAM permissions (expected)
- No unauthorized access attempts detected

### Access Control Changes
- 2 IAM policy attachments
- 1 IAM policy update
- All changes documented and approved

### Security Findings
- No suspicious access patterns detected
- No unauthorized services attempting secret access
- All access from approved principals
- No secrets modified outside of rotation

### Recommendations
- Continue monthly audits
- Review quarterly for trends
- Consider automated alerting for anomalies

Report generated: 2026-07-01T10:00:00Z
Reviewed by: Security Team, Compliance Officer
```

### 5.2 Annual Compliance Certification

```yaml
Certification: Annual Configuration and Secrets Audit
Period: 2025-06-01 to 2026-06-01
Organization: PropellQ Inc.

Certifications:
  - ✓ All secrets stored in approved manager (AWS Secrets Manager)
  - ✓ No plaintext secrets in code or configuration files
  - ✓ All secret access logged and auditable
  - ✓ Configuration changes followed governance process
  - ✓ IAM policies follow least-privilege principle
  - ✓ Rotation performed according to schedule
  - ✓ Emergency access procedures tested annually
  - ✓ Disaster recovery tested

Audit Summary:
  - Secrets managed: 28
  - Access events logged: 5.2M
  - Configuration changes: 12
  - Failed access attempts: 143 (0.003%)
  - Security incidents: 0

Compliance Status: ✅ PASSED
Certifying Officer: Sarah Chen, Chief Security Officer
Certification Date: 2026-06-01
Expiration: 2027-06-01
```

---

## 6. Incident Investigation

### 6.1 Example: Investigating Suspected Unauthorized Access

**Scenario**: Alert triggered for unusual secret access pattern

```bash
#!/bin/bash
# investigate_unauthorized_access.sh

SECRET_PATH="prod/database/master_password"
ALERT_TIME="2026-06-22T15:30:00Z"

echo "Investigation: Suspected unauthorized access to $SECRET_PATH"
echo "Alert time: $ALERT_TIME"
echo ""

# 1. Get all access events for this secret in last 4 hours
echo "=== Step 1: All recent access to secret ==="
aws logs filter-log-events \
  --log-group-name /aws/secretsmanager/audit \
  --filter-pattern "{ $.action.resource = \"$SECRET_PATH\" }" \
  --start-time $(date -d '4 hours ago' +%s)000

# 2. Check for failed access attempts
echo ""
echo "=== Step 2: Failed access attempts ==="
aws logs filter-log-events \
  --log-group-name /aws/secretsmanager/audit \
  --filter-pattern "{ $.action.resource = \"$SECRET_PATH\" && $.result.status = \"ACCESS_DENIED\" }" \
  --start-time $(date -d '24 hours ago' +%s)000

# 3. Get CloudTrail events for related IAM activity
echo ""
echo "=== Step 3: Related IAM changes ==="
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue="$SECRET_PATH" \
  --max-results 50

# 4. Check service health during incident
echo ""
echo "=== Step 4: Service health at alert time ==="
aws logs filter-log-events \
  --log-group-name /app/web_app/logs \
  --start-time $(date -d '10 minutes before' +%s)000 \
  --end-time $(date -d '10 minutes after' +%s)000 \
  --filter-pattern "ERROR"
```

### 6.2 Root Cause Analysis Template

```markdown
# Incident Investigation Report

## Incident Summary
- **Incident ID**: SEC-2026-001
- **Alert Time**: 2026-06-22T15:30:00Z
- **Discovery Method**: Automated anomaly detection
- **Severity**: Medium

## Initial Alert
- Unusual access pattern detected
- Service: booking_service
- Secret: prod/database/master_password
- Access frequency: 10x normal rate over 5 minutes

## Investigation Findings

### Timeline
| Time | Event | Detail |
|------|-------|--------|
| 15:30:00 | Alert triggered | Anomaly detected |
| 15:30:15 | Alert investigation | Reviewed logs |
| 15:32:00 | Contacted on-call | Service health OK |
| 15:35:00 | Root cause identified | Load test in progress |

### Root Cause
Load testing in staging environment accidentally targeted production secret manager
due to misconfigured endpoint in CI/CD pipeline.

### Impact
- 50 extra access calls to secret manager (no data exfiltration)
- No operational impact
- Cost impact: <$0.01 (negligible)

### Remediation
1. Fixed CI/CD pipeline configuration to use staging endpoint
2. Added validation to prevent production access from CI/CD
3. Increased monitoring threshold to reduce false positives

### Preventive Measures
1. Separate AWS accounts for staging/prod (prevents cross-environment access)
2. Add approval gate for CI/CD secrets access
3. Review IAM policies quarterly for over-permissioning

**Incident closed**: 2026-06-22T16:30:00Z  
**Follow-up**: Implemented preventive measures completed 2026-06-29
```

---

## 7. Retention Policies

### 7.1 Retention Schedule

```yaml
Audit Log Category: Hot (CloudWatch Logs)
  Retention: 30 days
  Access: Real-time
  Cost: ~$5/month

Audit Log Category: Warm (S3 Standard)
  Retention: 60 days (after hot expiration = 90 days total)
  Access: Minutes
  Cost: ~$0.50/month

Audit Log Category: Cold (S3 Glacier)
  Retention: 7 years (for compliance hold)
  Access: 1-5 minutes (Expedited tier)
  Cost: ~$0.10/month

Configuration Change Records: Indefinite
  Location: GitHub (version control history)
  Retention: Entire project history
  Location: S3 archive (immutable record)
  Cost: ~$0.05/month
```

### 7.2 Legal Hold

For active investigations or litigation:

```bash
# Place legal hold on audit logs
aws s3 put-object-legal-hold \
  --bucket propellq-audit-archive \
  --key "secrets/2026/06/22/..." \
  --legal-hold Status=ON

# List all objects under legal hold
aws s3 list-object-legal-holds \
  --bucket propellq-audit-archive \
  --query 'LegalHolds[].[Key,LegalHold.Status]'
```

---

## 8. Known Limitations

### 8.1 v1.0 Limitations

```
Current scope:
  ✓ Multi-tier audit logging
  ✓ CloudWatch Logs retention
  ✓ S3 archive and retrieval
  ✓ Athena querying
  ✓ Compliance reporting
  ✗ Real-time alerting on anomalies (v1.1)
  ✗ Machine learning for anomaly detection (v1.2)
  ✗ Automated compliance report generation (v1.1)

Planned enhancements:
  - v1.1: Real-time alerts for suspicious access patterns
  - v1.1: Automated compliance report generation
  - v1.2: ML-based anomaly detection
  - v1.2: Integration with SIEM systems
```

---

## References

- [SEC-1: Secret Manager Integration](SEC-1-SECRET_MANAGER_INTEGRATION.md)
- [SEC-2: Least-Privilege Access Controls](SEC-2-LEAST_PRIVILEGE_ACCESS_CONTROLS.md)
- [GOV-1: Configuration Change Governance](GOV-1-CONFIGURATION_CHANGE_GOVERNANCE.md)
