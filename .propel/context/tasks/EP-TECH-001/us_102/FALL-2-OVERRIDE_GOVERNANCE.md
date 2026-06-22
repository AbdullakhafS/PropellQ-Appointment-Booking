# FALL-2: Override Governance & Critical Path Reclassification

**Document ID**: FALL-2  
**Acceptance Criteria**: AC-5 (indirectly; governance of critical path decisions)  
**Last Updated**: 2026-06-22  
**Status**: Active

---

## Overview

Critical vs. non-critical classification of services determines whether fallbacks are available. This policy governs reclassification requests and overrides to the default safe classification.

---

## 1. Service Classification

### 1.1 Default Classification (Conservative)

By default, all services are classified as **CRITICAL** unless explicitly approved otherwise.

```yaml
default_classification: "CRITICAL"
reason: "Fail-safe approach; assume all services are essential"
consequence: "No fallback; failure blocks booking"
```

### 1.2 Non-Critical Classification Criteria

A service may be reclassified to NON-CRITICAL only if ALL criteria are met:

1. **Service is not part of booking data path**
   - Not reading/writing appointment data
   - Not checking availability
   - Not processing payments
   
2. **Booking can complete without service**
   - Removing the service call doesn't break booking workflow
   - Example: SMS notifications (booking completes, SMS sent later)
   - Counter-example: Payment processing (booking fails without it)

3. **Fallback is well-defined**
   - Queue for retry, return empty, use cached data, etc.
   - Not "best effort" or "unclear"

4. **Business approves degradation**
   - Product agrees that missing this service is acceptable
   - Example: Recommendations not shown (acceptable degradation)
   - Counter-example: Payment not processed (unacceptable)

---

## 2. Reclassification Request Process

### 2.1 Submission

Submit reclassification request with:

```yaml
reclassification_request:
  date_submitted: "2026-06-15"
  submitted_by: "alice@propellq.com"
  service: "recommendation_engine"
  current_classification: "CRITICAL"
  requested_classification: "NON_CRITICAL"
  
  justification: |
    Recommendations are optional enhancement to booking flow.
    Booking completes successfully without recommendations.
    If service fails, we return empty recommendations list.
  
  fallback_strategy: "return_empty_list"
  
  business_impact: |
    Users won't see recommendations if service down.
    Booking workflow not affected.
    Acceptable degradation.
  
  testing_plan: |
    - Test booking success with service returning errors
    - Test empty recommendations returned on fallback
    - Load test to verify no cascading impact
  
  approval_contacts:
    - role: "Tech Lead"
      name: "Bob Johnson"
    - role: "Product Manager"
      name: "Carol Smith"
    - role: "Security Lead"
      name: "David Lee"
```

### 2.2 Review & Approval

Each reclassification requires approval from:

1. **Tech Lead** (Infrastructure impact)
   - Is fallback technically feasible?
   - Does circuit breaker work correctly?
   - Any cascading dependencies?
   
2. **Product Manager** (Business impact)
   - Is degradation acceptable?
   - Are users affected?
   - Revenue/compliance impact?
   
3. **Security Lead** (Information security)
   - Does fallback expose sensitive data?
   - Any security implications?
   - Audit trail maintained?

### 2.3 Approval SLA

| Scenario | SLA |
|----------|-----|
| Straightforward (clear fallback, low impact) | 1 business day |
| Moderate (some uncertainty) | 3 business days |
| Complex (significant risk) | 5 business days |
| Requires executive approval | 1 week |

### 2.4 Decision Record

Once approved, create record in `.propel/classifications/reclassified-services.yaml`:

```yaml
reclassifications:
  - service: "recommendation_engine"
    classification: "NON_CRITICAL"
    reclassified_date: "2026-06-15"
    reason: "Optional enhancement; booking completes without"
    fallback_strategy: "return_empty_list"
    approved_by:
      - name: "Bob Johnson"
        role: "Tech Lead"
        date: "2026-06-15"
      - name: "Carol Smith"
        role: "Product Manager"
        date: "2026-06-15"
      - name: "David Lee"
        role: "Security Lead"
        date: "2026-06-16"
    expiry_date: null  # No expiry; permanent unless reclassified back
    review_date: "2027-06-15"  # Annual review
```

---

## 3. Reclassification Reversal

### 3.1 When to Reverse

Reverse a NON_CRITICAL classification back to CRITICAL if:

- **Fallback is failing too often** (> 10% of activations)
- **Service becomes critical to booking** (new requirement added)
- **Business impact discovered** (revenue/compliance)
- **Security issue discovered** (fallback exposes data)

### 3.2 Reversal Process

1. File issue: "Reclassify {service} back to CRITICAL"
2. Brief review (usually 1 day)
3. Update classification in code and configuration
4. Deploy immediately (no fallback available anymore)
5. Notify development team

---

## 4. Override Decision Log

### 4.1 Logging All Decisions

Maintain audit trail of all classification decisions:

```yaml
override_log:
  - date: "2026-06-15"
    service: "recommendation_engine"
    action: "reclassified_to_non_critical"
    requested_by: "alice@propellq.com"
    approved_by: ["bob@propellq.com", "carol@propellq.com", "david@propellq.com"]
    reason: "Optional feature; acceptable degradation"
    status: "approved"
  
  - date: "2026-07-01"
    service: "analytics_tracking"
    action: "reclassified_to_non_critical"
    requested_by: "eve@propellq.com"
    approved_by: ["bob@propellq.com", "carol@propellq.com", "security_team@propellq.com"]
    reason: "Metrics collection; booking completes without"
    status: "approved"
  
  - date: "2026-07-15"
    service: "rating_service"
    action: "reclassified_to_critical"
    requested_by: "bob@propellq.com"
    reason: "Ratings now required for provider selection"
    status: "approved"
```

### 4.2 Querying Decision Log

```bash
# List all non-critical services
grep "reclassified_to_non_critical" override_log.yaml | grep approved

# List all reversals
grep "reclassified_to_critical" override_log.yaml

# Audit trail for specific service
grep "recommendation_engine" override_log.yaml
```

---

## 5. Emergency Overrides

### 5.1 Temporary Reclassification (Emergency)

In emergencies, Tech Lead can temporarily reclassify without full approval:

```yaml
emergency_override:
  date: "2026-06-20T03:15:00Z"
  service: "payment_processor"  # Normally CRITICAL
  temporary_classification: "NON_CRITICAL"
  reason: "Payment service degraded; queuing payments for async processing"
  approved_by: "bob@propellq.com"  # On-call tech lead
  incident_ticket: "INC-2026-0620-001"
  duration_hours: 2
  auto_revert_at: "2026-06-20T05:15:00Z"
```

### 5.2 Approval Requirements

Emergency overrides require:
- On-call tech lead approval
- Incident ticket filed
- Maximum 24-hour duration
- Daily extension requires business + tech lead approval

### 5.3 Post-Incident Review

After emergency expires:

1. Revert classification immediately
2. Post-incident meeting within 24 hours
3. Root cause analysis
4. Recommendations for permanent change (if needed)

---

## 6. Monitoring Classifications

### 6.1 Classification Drift Detection

Alert if classification doesn't match actual behavior:

```python
def detect_classification_drift():
    """Alert if classified service behaves differently."""
    for service, classification in SERVICE_CLASSIFICATIONS.items():
        actual_fallback = check_fallback_behavior(service)
        
        if classification == "CRITICAL" and actual_fallback == True:
            alert(f"Classification drift: {service} has fallback but marked CRITICAL")
        
        if classification == "NON_CRITICAL" and actual_fallback == False:
            alert(f"Classification drift: {service} has no fallback but marked NON_CRITICAL")
```

### 6.2 Classification Impact Metrics

```
- services_classified_critical: N
- services_classified_non_critical: N
- % of booking path in critical services: X%
- % of booking path with fallback: Y%
```

---

## 7. Testing Classification Changes

### 7.1 Test Procedure Before Approval

Before approving reclassification, execute:

```bash
# 1. Functional test
pytest tests/fallback_behavior.py -k "test_{service}_fallback"

# 2. Load test
locust -f tests/load_test.py --users=100 --hatch-rate=10

# 3. Chaos test
chaos run tests/chaos/{service}_down.yaml

# 4. Booking continuity test
pytest tests/integration/test_booking_with_{service}_down.py
```

### 7.2 Pre-Deployment Checklist

- [ ] Fallback tested and working
- [ ] Booking completes with service down
- [ ] Async queue (if applicable) processing correctly
- [ ] No cascading impact on other services
- [ ] Metrics/alerts configured
- [ ] Documentation updated

---

## 8. Annual Review

### 8.1 Classification Review Schedule

Every year, review all NON_CRITICAL classifications:

```yaml
annual_review:
  date: "2027-06-15"
  reviewers: ["bob@propellq.com", "carol@propellq.com"]
  services_to_review:
    - recommendation_engine
    - analytics_tracking
    - rating_service_cache
```

### 8.2 Review Questions

For each non-critical service:

1. Is fallback still working correctly?
2. Have we received user complaints about degradation?
3. Has business priority changed?
4. Should we invest in making this service critical?
5. Any security/compliance changes?

### 8.3 Review Outcome

- **Continue current classification**: Update `review_date`
- **Reclassify to CRITICAL**: Follow reversal process
- **Reclassify to CRITICAL with fallback**: Update fallback code
- **Decomission service**: Remove from system

---

## 9. Documentation Updates

When classification changes:

1. Update `SERVICE_CLASSIFICATIONS` in code
2. Update `.propel/classifications/reclassified-services.yaml`
3. Update `FALL-1` if fallback strategy changes
4. Update architecture diagrams
5. Notify development team in Slack

---

## 10. Related Documents

- FALL-1: Fallback guidelines (defines fallback strategies)
- RES-3: Circuit breaker (enforces classification)
- Architecture diagrams (shows critical path)

---

**Document Owner**: Infrastructure Team  
**Last Review**: 2026-06-22  
**Next Review**: 2026-09-22
