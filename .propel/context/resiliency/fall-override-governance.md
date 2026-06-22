# FALL-2: Override Governance

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, platform architects, security team

---

## 1. Overview

This document defines the governance process for service-level overrides of default resiliency behavior, including approval workflows, audit trails, and enforcement.

**Principles:**
- Overrides require explicit approval
- All overrides are time-bounded
- Override rationale is documented
- Audit trail maintained for compliance

---

## 2. Override Approval Matrix

| Override Type | Default Behavior | Override Behavior | Approver | Duration | Use Case |
|---|---|---|---|---|---|
| **Skip Circuit Breaker** | Breaker opens at 50% failures | Ignore failures, call every time | Security Lead | 7 days | Temporary degraded service acceptable |
| **Disable Timeout** | 10s timeout enforced | Remove timeout or extend to 30s | Backend Lead | 7 days | Batch operation needs longer |
| **Disable Retry** | Retry up to 3x | Call once only | Backend Lead | 3 days | Non-idempotent operation |
| **Skip Fallback** | Use fallback on dep failure | Fail fast if dependency fails | Security Lead | 7 days | Data consistency critical |
| **Increase Retry Budget** | 500 retries/service/day | Increase to 1000 | Platform Lead | 14 days | Seasonal spike |

---

## 3. Override Request Template

```markdown
## Override Request: [Service Name] - [Override Type]

### 1. Justification
[2-5 sentences explaining why override is needed]

Example:
"Payment service experiencing gradual recovery after maintenance. 
We need to temporarily extend the timeout from 10s to 20s to allow 
for slower response times during recovery period."

### 2. Business Impact
- If override NOT approved: [What breaks?]
- If override approved: [Expected improvement]

### 3. Duration
Start: 2026-06-22 14:00 UTC
End: 2026-06-29 14:00 UTC
Reason: Give service 1 week to fully recover

### 4. Monitoring Plan
- Metric to watch: [metric_name]
- Alert threshold: [threshold]
- Action if issue: [revert / escalate]

### 5. Removal Plan
- Will remove on: [date]
- OR when: [condition]
- Approved by: [person]
```

---

## 4. Approval Workflow

### 4.1 Request to Approval Flow

```
Engineer submits override request
  ↓
System logs to override audit table
  ↓
Notify approver via Slack/email
  ↓
Approver reviews:
  - Business justification valid?
  - Duration reasonable?
  - Monitoring plan adequate?
  ↓
✅ APPROVED
   │
   ├─ Enable override in code
   ├─ Log approval details
   └─ Set expiry timer
   
OR

❌ REJECTED
   │
   ├─ Notify requester with reason
   └─ Can re-request after addressing feedback
```

### 4.2 Multi-Level Approval for High-Risk Overrides

| Risk Level | Approvers | Turnaround |
|---|---|---|
| **Low** (non-critical service) | 1 Backend Lead | 4 hours |
| **Medium** (important service) | 2 (Backend Lead + Platform Lead) | 24 hours |
| **High** (critical service) | 3 (Backend Lead + Platform Lead + CTO) | 24 hours |
| **Emergency** (production incident) | 2 (Backend Lead + On-Call Lead) | 15 minutes |

---

## 5. Implementation - Override Registry

### 5.1 Override Registry Schema

```yaml
overrides:
  - id: override-2026-06-22-001
    service: PaymentGateway
    overrideType: ExtendTimeout
    originalValue: "10 seconds"
    overriddenValue: "20 seconds"
    status: approved
    createdBy: alice@company.com
    createdAt: "2026-06-22T14:00:00Z"
    approvedBy: bob@company.com
    approvedAt: "2026-06-22T14:15:00Z"
    startsAt: "2026-06-22T14:00:00Z"
    expiresAt: "2026-06-29T14:00:00Z"
    justification: |
      Payment service experiencing slow recovery after maintenance.
      Extended timeout allows API to process requests without timeout.
    businessImpact: "Reduced failed transactions during recovery window"
    monitoringPlan: "Watch payment_timeout_rate, alert if > 5%"
    removalReason: "Service recovered, timeout back to 10s"
    removalAt: null
    removedBy: null
```

### 5.2 Override Configuration in Code

```csharp
// Load overrides at startup
public class ResiliencyConfiguration
{
    private readonly OverrideRegistry _registry;
    
    public TimeSpan GetTimeout(string service)
    {
        var override = _registry.GetActive(service);
        
        if (override != null)
        {
            _logger.LogInformation(
                "Using override timeout for {Service}: {Value}",
                service,
                override.OverriddenValue
            );
            return override.OverriddenValue;
        }
        
        // Use default
        return _defaults.GetTimeout(service);
    }
    
    public bool IsRetryEnabled(string service)
    {
        var override = _registry.GetActive(service, "DisableRetry");
        return override?.IsActive != true;  // Retry enabled unless overridden
    }
}
```

---

## 6. Expiry and Auto-Revert

### 6.1 Override Expiry Timeline

```
T+0: Override activated
     Status: active
     
T-2 days: Expiry warning sent
          "Override expires in 2 days"
          Action: Re-request if needed or prepare for revert
          
T-1 day: Escalation notice
         "Override expires in 24 hours"
         Action: If monitoring shows issues, escalate to maintain
         
T+0: Override expires
     Status: expired
     Action: Auto-revert to default behavior
     Alert: "Override expired, reverted to defaults"
```

### 6.2 Auto-Revert Logic

```python
async def check_expired_overrides():
    """Periodically check and revert expired overrides."""
    
    expired = await override_registry.get_expired()
    
    for override in expired:
        logger.info(
            f"Auto-reverting override {override.id} for {override.service}"
        )
        
        # Revert in code config
        config.set_default_for_service(
            override.service,
            override.originalValue
        )
        
        # Update registry
        await override_registry.mark_reverted(
            override.id,
            reason="auto_expiry"
        )
        
        # Alert
        await alert_slack(
            f"⚠️ Override expired: {override.service} "
            f"reverted to {override.originalValue}"
        )
        
        # Emit metric
        telemetry.track_override_expired(override.service)

# Schedule daily check
scheduler.schedule(check_expired_overrides, every_day_at="00:00Z")
```

---

## 7. Override Audit and Compliance

### 7.1 Audit Queries

```sql
-- Find all active overrides
SELECT * FROM overrides 
WHERE status = 'active' 
  AND expires_at > NOW()
ORDER BY expires_at ASC;

-- Find recently expired overrides
SELECT * FROM overrides 
WHERE status = 'expired'
  AND expires_at > NOW() - INTERVAL '7 days'
ORDER BY expires_at DESC;

-- Find approval patterns
SELECT 
  approved_by,
  COUNT(*) as approval_count,
  AVG(approval_time_minutes) as avg_approval_time
FROM overrides 
WHERE approved_at > NOW() - INTERVAL '30 days'
GROUP BY approved_by
ORDER BY approval_count DESC;

-- Compliance: No expired overrides in production
SELECT * FROM overrides 
WHERE status = 'active' 
  AND expires_at < NOW()
  AND environment = 'production';
```

### 7.2 Monthly Compliance Report

```
OVERRIDE COMPLIANCE REPORT - June 2026
=====================================

Active Overrides: 3
  - PaymentGateway (timeout): expires 2026-06-29
  - SearchService (circuit breaker): expires 2026-06-28
  - NotificationService (retry): expires 2026-06-25

Recent Approvals: 5
  Alice (3 approvals, avg 45 min)
  Bob (2 approvals, avg 120 min)

Expired Overrides (auto-reverted): 2
  - Cache timeout (2026-06-15)
  - Rate limit (2026-06-18)

Violations: 0
  ✅ No expired overrides remain in production
  ✅ All overrides have documented justifications
  ✅ All overrides approved by authorized approvers
```

---

## 8. Testing Override Enforcement

### 8.1 Unit Test - Override Applied

```csharp
[TestMethod]
public void OverrideRegistry_EnablesTimeout_Override()
{
    var registry = new OverrideRegistry();
    registry.Add(new Override
    {
        Service = "PaymentGateway",
        OverrideType = "ExtendTimeout",
        OverriddenValue = TimeSpan.FromSeconds(20),
        ExpiresAt = DateTime.UtcNow.AddDays(7)
    });
    
    var config = new ResiliencyConfiguration(registry);
    var timeout = config.GetTimeout("PaymentGateway");
    
    Assert.AreEqual(TimeSpan.FromSeconds(20), timeout);
}
```

### 8.2 Integration Test - Auto-Revert on Expiry

```typescript
describe('Override expiry', () => {
  it('should auto-revert expired override', async () => {
    const override = {
      id: 'test-override',
      service: 'TestService',
      expiresAt: new Date(Date.now() - 1000),  // Already expired
      status: 'active'
    };
    
    await overrideRegistry.add(override);
    
    // Run expiry check
    await checkExpiredOverrides();
    
    // Should be marked as reverted
    const updated = await overrideRegistry.get('test-override');
    expect(updated.status).toBe('reverted');
  });
});
```

---

## 9. Success Criteria

- [ ] Override approval workflow documented and enforced
- [ ] Override registry tracks all overrides with audit trail
- [ ] Multi-level approval implemented for high-risk overrides
- [ ] Auto-expiry and revert logic operational
- [ ] Override expiry notifications sent on time
- [ ] Compliance reports generated monthly
- [ ] Unit/integration tests validate enforcement
- [ ] Documentation published for engineers and approvers

---

## References

- AWS System Manager Change Calendar: https://docs.aws.amazon.com/systems-manager/
- Access Control Best Practices: https://cheatsheetseries.owasp.org/

**Next:** [OBS-1: Resiliency Telemetry and Alerting](obs-resiliency-telemetry.md)
