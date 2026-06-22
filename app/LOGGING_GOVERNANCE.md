# Logging Policy and Governance (GOV-1)

**Task**: TASK-099: Implement Centralized Logging with Correlation IDs  
**Component**: GOV-1 - Logging Policy Governance  
**Date**: 2026-06-22

## Overview

This document establishes logging governance policies for the PropellQ platform, covering retention, access controls, and operational procedures for centralized logging infrastructure.

## 1. Retention Policy (AC-6)

### Environment-Specific Retention

Logs are retained based on environment and log classification:

| Environment | Retention | Rationale |
|-------------|-----------|-----------|
| **Development** | 7 days | Cost optimization, frequent log rotation |
| **Staging** | 30 days | Extended window for pre-release testing |
| **Production** | 90 days | Compliance, incident investigation, SLA |

### Retention Enforcement

- Logs older than retention window are automatically purged
- Deletion is performed nightly (00:00 UTC)
- Purged log IDs are archived to audit trail
- No manual restoration possible (compliance requirement)

### Exception Process

**Temporary Retention Extension**: For active incident investigation

1. **Request**: Submit incident ID and justification to ops-team@propellq.com
2. **Approval**: Requires ops manager sign-off
3. **Duration**: Maximum 30-day extension
4. **Audit**: All extensions logged in governance audit trail

**Example Request**:
```
Subject: Log Retention Extension - INC-2026-0615-001
  
Incident ID: INC-2026-0615-001
Current Retention Expires: 2026-09-20
Requested Extension: Until 2026-10-20
Reason: Active forensic analysis of data consistency issue
Requested By: incident-commander@propellq.com
```

## 2. Access Control (SEC-2)

### Log Access Roles

| Role | Access Level | Purpose |
|------|--------------|---------|
| **Engineer** | Own service logs | Development and debugging |
| **On-Call** | Production logs | Incident response |
| **Security Team** | All logs (redacted) | Security audit and forensics |
| **Ops Team** | All logs (unredacted) | Infrastructure operations |
| **Compliance** | Read-only archive | Audit trail verification |

### Access Control Enforcement

- Authentication: Service account API key (for programmatic access)
- Authorization: Role-based access via API
- Audit logging: All log access logged
- No direct file system access

### Sensitive Log Access

Accessing unredacted logs (passwords, tokens, etc.):

1. Requires explicit approval from security team
2. Must be within 48-hour window
3. Reason must be documented
4. All access is timestamped and audited

## 3. Logging Standards and Practices

### Required Log Attributes (LOG-1)

Every log entry MUST include:

```python
{
    "timestamp": "2026-06-22T10:30:00Z",      # ISO 8601 UTC
    "correlation_id": "uuid",                 # AC-1: End-to-end tracing
    "severity": "INFO",                        # EMERGENCY..DEBUG
    "source": "API",                           # Where log originated
    "environment": "production",               # Deployment env
    "service_name": "booking_service",         # Service identifier
    "message": "Human-readable message",
    "trace_id": "uuid"                         # Root trace
}
```

### Forbidden in Logs (SEC-2)

The following MUST NEVER appear in logs:

- Passwords, API keys, tokens, secrets
- Credit card numbers or CVV
- Medical record numbers (MRN)
- SSN/tax IDs
- Private encryption keys
- Full request/response payloads (errors only)

**Enforcement**: Automatic redaction via `LogRedactor` at emit time

### Recommended Log Fields

For debugging and correlation:

```python
{
    "route": "/api/appointments/book",        # HTTP path
    "actor": "user_123",                       # User/service ID
    "status": "success",                       # success/failure/partial
    "http_status": 200,                        # HTTP response code
    "duration_ms": 145.3,                      # Operation duration
    "parent_id": "parent-uuid",                # For nested operations
    "details": {...}                           # Extra context (dict)
}
```

## 4. Log Delivery Reliability (AC-4, PIPE-1/2)

### SLA: 99.9% Delivery Success

- Target: ≥99.9% of logs delivered within 5 seconds
- Retry: Exponential backoff (1s, 2s, 4s max)
- Dead Letter: Failed logs after 3 attempts archived
- Monitoring: Dashboard alerts if success rate drops below 99.5%

### Monitoring and Alerting

| Alert | Threshold | Action |
|-------|-----------|--------|
| **Delivery Failure Rate** | >0.5% | Page on-call ops |
| **Backpressure Events** | >100/min | Investigate pipeline bottleneck |
| **Dead Letter Queue Size** | >10,000 | Immediate ops review |
| **Sink Health** | Unhealthy | Failover to backup sink |

### Backup Sinks and Failover

Primary sink: Elasticsearch cluster (production)  
Backup sink: File system (`/var/log/app.log`)  
Automatic failover: If primary unhealthy for >30s

## 5. Correlation ID Propagation (LOG-2, AC-1)

### Propagation Rules

**Inbound Requests**:
- Extract from `X-Correlation-ID` header
- If missing: Generate new UUID v4
- Pass to all downstream services

**Outbound Calls**:
- Include correlation ID in `X-Correlation-ID` header
- Include parent ID in `X-Parent-ID` header
- Maintain chain for debugging

**Async Tasks**:
- Include correlation ID in message metadata
- Preserve for cross-service message tracing

### Example Header Propagation

```
Inbound:
  X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
  X-Trace-ID: 550e8400-e29b-41d4-a716-446655440000

Outbound Call:
  X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
  X-Parent-ID: 550e8400-e29b-41d4-a716-446655440000
  X-Trace-ID: 550e8400-e29b-41d4-a716-446655440000
```

## 6. Redaction Policy (AC-3, SEC-1)

### Automatic Redaction Levels

| Level | Coverage | Use Case |
|-------|----------|----------|
| **NONE** | No redaction | Development only |
| **LOW** | Type and length only | Staging |
| **MEDIUM** | Hashed sensitive fields | Production |
| **HIGH** | Complete masking | High-risk data |

### Redaction Rules

**Sensitive Field Names** (auto-detect):
- `password`, `api_key`, `secret`, `token`, `credit_card`
- `mrn`, `patient_name`, `diagnosis`, `email`, `phone`, `ssn`

**Pattern Matching**:
- Email: `user@domain.com` → `[REDACTED:EMAIL]`
- Phone: `555-123-4567` → `[REDACTED:PHONE]`
- SSN: `123-45-6789` → `[REDACTED:SSN]`

**Nested Structures**:
- Recursively redact to depth 3
- Redact all values in sensitive fields
- Truncate field values >10KB to prevent exhaustion

## 7. Incident Investigation Process (DOC-1)

### Correlation ID-Based Investigation

1. **Obtain Incident Correlation ID**
   - From error response: `correlation_id` field
   - From user report: "Request ID" or "Ref #"
   - From alert: Embedded in incident ticket

2. **Query Timeline**
   ```
   QueryBuilder()
     .with_correlation_id(incident_id)
     .with_last_hours(1)
     .sort_by_time_asc()
   ```

3. **Analyze Event Sequence**
   - Identify request start/end times
   - Note all service transitions
   - Locate first error (if any)

4. **Cross-Service Tracing**
   - Follow parent IDs to root cause
   - Check related service logs
   - Verify timing between services

### Common Query Patterns (SEARCH-1)

**Find all events for a request** (AC-2):
```
SELECT * FROM logs
WHERE correlation_id = ?
ORDER BY timestamp ASC
```

**Find errors in last hour** (AC-5):
```
SELECT * FROM logs
WHERE environment = 'production'
  AND severity IN ('ERROR', 'CRITICAL')
  AND timestamp >= NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC
```

**Find slow requests** (AC-5):
```
SELECT correlation_id, service_name, duration_ms
FROM logs
WHERE source = 'API'
  AND duration_ms > 1000
  AND environment = 'production'
ORDER BY duration_ms DESC
LIMIT 100
```

## 8. Operational Procedures

### Daily Operations

- **08:00 UTC**: Check dead letter queue size, investigate if >100
- **16:00 UTC**: Review log delivery success rate (target >99.9%)
- **00:00 UTC**: Automatic retention cleanup

### Incident Response

1. **Alert Triggered**: Delivery failure or error spike
2. **Correlation Query**: Extract incident correlation ID
3. **Timeline Analysis**: Reconstruct event sequence
4. **Root Cause**: Identify first error in timeline
5. **Resolution**: Fix issue and validate recovery

### Debug Level Increase

**Temporary elevation for troubleshooting**:

1. Request approval via incident ticket
2. Duration: Maximum 2 hours
3. Must be reverted manually
4. All debug logs kept for 48 hours

## 9. Compliance and Audit

### Audit Trail

All of the following are logged:
- Log retention extensions
- Unredacted log access
- Debug level elevations
- System configuration changes
- Pipeline failover events

### Compliance Checklist

- [ ] All logs contain required fields (LOG-1)
- [ ] Correlation IDs propagate correctly (LOG-2, AC-1)
- [ ] Sensitive data is redacted (AC-3, SEC-1)
- [ ] Delivery success ≥99.9% (AC-4)
- [ ] Search filters work correctly (AC-5)
- [ ] Retention policy enforced (AC-6)
- [ ] Access controls enforced (SEC-2)

### Annual Review

- Policy effectiveness review
- Technology and tool assessment
- Retention period adjustment if needed
- Training and knowledge transfer

---

**Next**: See [INCIDENT_INVESTIGATION_RUNBOOK.md](INCIDENT_INVESTIGATION_RUNBOOK.md) for detailed debugging procedures.
