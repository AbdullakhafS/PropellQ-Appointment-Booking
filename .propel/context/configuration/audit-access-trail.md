# AUDIT-1: Access and Change Audit Trail

**Status:** Published | **Version:** 1.0 | **Date:** 2026-06-22

---

## 1. Overview

Capture and maintain immutable audit trail of all secret access and configuration changes for compliance and forensic analysis.

---

## 2. Audit Events

### 2.1 Secret Access Events

```yaml
SecretAccessEvent:
  timestamp: 2026-06-22T14:30:15.123Z
  eventId: aud-sec-12345
  secretName: db-password
  secretVersion: 2
  action: get_secret_value
  
  Actor:
    serviceId: booking-service
    serviceVersion: 1.0.0
    environment: production
    identity: arn:aws:iam::ACCOUNT:role/booking-service
  
  Result:
    status: success
    latencyMs: 45
    cacheHit: false
    
  Metadata:
    region: us-east-1
    source: SecretsManager
    ipAddress: 10.0.1.5
```

### 2.2 Configuration Change Events

```yaml
ConfigChangeEvent:
  timestamp: 2026-06-22T15:00:00.000Z
  eventId: aud-cfg-67890
  
  Change:
    type: schema_update
    schema: booking-service
    action: add_key
    key: BOOKING_MAX_SIZE
    
  ApprovedBy:
    email: alice@company.com
    role: backend-lead
    
  Metadata:
    gitCommit: abc123def456
    pullRequest: PR-1234
    reviewed: true
```

---

## 3. Audit Log Storage

```
S3 Bucket Structure:
  s3://audit-logs-prod/
  ├─ 2026/
  │  └─ 06/
  │     └─ 22/
  │        ├─ secrets/
  │        │  └─ 2026-06-22T14-30-access.jsonl
  │        └─ config/
  │           └─ 2026-06-22T15-00-change.jsonl

Retention:
  Production: 7 years (compliance)
  Staging: 1 year
  Development: 90 days
  
Security:
  - Immutable (S3 Object Lock)
  - Encrypted at rest (KMS)
  - Versioning enabled
  - Server access logging enabled
```

---

## 4. Query Examples

### 4.1 Find Secret Access in Date Range

```sql
SELECT * FROM audit_logs
WHERE 
  event_type = 'secret_access'
  AND secret_name = 'db-password'
  AND timestamp BETWEEN '2026-06-01' AND '2026-06-30'
ORDER BY timestamp DESC;

Results:
  2026-06-22T14:30 | booking-service | get | success
  2026-06-21T09:15 | search-service  | get | success
  2026-06-20T16:45 | api-gateway     | get | success
```

### 4.2 Find Configuration Changes by Service

```sql
SELECT * FROM audit_logs
WHERE 
  event_type = 'config_change'
  AND service = 'booking-service'
ORDER BY timestamp DESC;

Results:
  2026-06-22T15:00 | alice | add_key   | BOOKING_MAX_SIZE   | approved
  2026-06-20T10:30 | bob   | update_value | DB_POOL_SIZE | approved
```

### 4.3 Unauthorized Access Attempts

```sql
SELECT * FROM audit_logs
WHERE 
  event_type = 'secret_access'
  AND result_status = 'denied'
  AND timestamp > now() - INTERVAL '7 days'
ORDER BY timestamp DESC;

Results:
  2026-06-22T11:20 | unauthorized-service | denied | access_denied
  2026-06-21T14:15 | invalid-credentials  | denied | auth_failed
```

---

## 5. Compliance Reports

### 5.1 Monthly Access Report

```
AUDIT REPORT: Secret Access - June 2026
======================================

Total Access Events: 12,547
  - Successful: 12,510 (99.7%)
  - Denied: 37 (0.3%)

Top Services by Access:
  1. booking-service: 4,200 accesses
  2. api-gateway: 3,100 accesses
  3. search-service: 2,500 accesses

Anomalies Detected: 2
  - 2026-06-15T03:45: Unusual access time from booking-service
  - 2026-06-18T22:30: Access from unexpected IP

No policy violations found.
```

### 5.2 Annual Configuration Change Report

```
CONFIG CHANGES - 2026
====================

Total Changes: 145
  - Schema updates: 23
  - Value updates: 89
  - Key removals: 33

Approval Rate: 100%
  - 2-approvers average
  - Average approval time: 4 hours

Change Categories:
  - Performance tuning: 45 changes
  - Security hardening: 23 changes
  - Feature additions: 34 changes
  - Deprecations: 43 changes

No unauthorized changes detected.
```

---

## 6. SIEM Integration

```json
{
  "siem": {
    "platform": "Splunk",
    "integration": "AWS Firehose",
    "index": "audit_logs",
    "sourcetype": "_json",
    "fields": [
      "timestamp",
      "eventId",
      "eventType",
      "secretName",
      "serviceId",
      "action",
      "result",
      "actor"
    ]
  }
}
```

---

## 7. Audit Log Retrieval

### 7.1 For Compliance Audit

```bash
# Export all secret access logs for audit period
aws s3 sync s3://audit-logs-prod/2026/ ./audit-export/ \
  --exclude "*" \
  --include "*/secrets/*.jsonl"

# Verify integrity
sha256sum audit-export/secrets/*.jsonl > audit-checksums.txt

# Generate report
generate-compliance-report.sh audit-export/ > compliance-report.pdf
```

### 7.2 For Incident Investigation

```bash
# Find all access to specific secret in date range
grep 'db-password' audit-logs/2026/06/*.jsonl | \
  jq 'select(.timestamp > "2026-06-20")'

# Find all access from specific service
grep 'booking-service' audit-logs/2026/06/*.jsonl | \
  jq '.action, .result, .timestamp'
```

---

## 8. Testing Audit Trail

```csharp
[TestMethod]
public async Task AuditLogging_SecretAccess_Logged()
{
    // Access secret
    var secret = await secretManager.GetSecretAsync("db-password");
    
    // Wait for audit log
    await Task.Delay(100);
    
    // Verify audit log entry
    var auditLog = await auditService.GetLatestEventAsync(
        eventType: "secret_access",
        secretName: "db-password"
    );
    
    Assert.IsNotNull(auditLog);
    Assert.AreEqual("success", auditLog.Result.Status);
    Assert.AreEqual("booking-service", auditLog.Actor.ServiceId);
}
```

---

## 9. Retention Policy

```
ConfigRetentionPolicy:
  Production:
    retention: 7 years  # Compliance requirement
    archive: Glacier after 1 year
  
  Staging:
    retention: 1 year
    archive: Delete after 1 year
  
  Development:
    retention: 90 days
    archive: Delete after 90 days
```

---

## References

- AWS CloudTrail: https://docs.aws.amazon.com/cloudtrail/
- OWASP: Audit Logging: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

**Next:** [DOC-1: Onboarding and Runbooks](doc-onboarding-runbooks.md)
