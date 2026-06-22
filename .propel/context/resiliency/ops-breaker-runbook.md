# OPS-1: Breaker and Recovery Runbook

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** On-call engineers, DevOps, platform team

---

## 1. Overview

This operational runbook provides triage and recovery procedures for circuit breaker events, retry amplification, and fallback failures.

---

## 2. Circuit Breaker Open - Triage and Recovery

### 2.1 Alert: "Circuit Breaker Open - PaymentGateway"

**What it means:**
- PaymentGateway has failed 50% of requests in last 30 seconds
- All new requests will be rejected fast (circuit OPEN)
- System is protecting itself from cascading failure

**Step 1: Assess Impact**
```
1. Check service status dashboard
2. Look at customer impact:
   - Are bookings failing?
   - Are checkouts affected?
   - How many customers affected?
3. Note current time for timeline
```

**Step 2: Investigate Root Cause**

```
Check logs:
  kubectl logs -n payment deployment/payment-gateway | tail -100
  
Look for:
  ✗ Connection refused (service down)
  ✗ Timeout (service slow or unreachable)
  ✗ 500 errors (service crashing)
  ✗ 429 rate limited (quota exceeded)

Check dependencies:
  curl https://payment-gateway.internal/health
  → 200 OK {status: "healthy"}     ✅ Service healthy
  → 503 Service Unavailable        ❌ Service down
  → Timeout                        ❌ Service unreachable
```

**Step 3: Short-term Mitigation**

Option A: Service is recovering naturally
```
1. Monitor circuit breaker state
   watch -n 1 'curl localhost:8080/metrics | grep circuit_state'
2. Wait for half-open probe
3. Monitor timeout rate dropping
4. Circuit will close automatically
Timeline: Usually 30-60 seconds
```

Option B: Service is down, needs restart
```
1. Restart the service
   kubectl rollout restart deployment/payment-gateway -n payment
   
2. Monitor pod startup
   kubectl get pods -n payment -w
   
3. Wait for half-open probe
   T+30s: Circuit enters half-open
   T+30s+10ms: Probe request sent
   T+31s: Circuit closes if probe succeeds
   
4. Verify service health
   curl https://payment-gateway.internal/health
```

Option C: Emergency bypass (last resort)
```
1. Create override to disable circuit breaker
   POST /api/overrides
   {
     "service": "PaymentGateway",
     "overrideType": "DisableCircuitBreaker",
     "duration": "1h",
     "justification": "Manual override during incident"
   }
   
2. Monitor closely for issues
3. Plan proper fix for next day
4. Override auto-expires after 1 hour
```

**Step 4: Root Cause Fix**

| If Cause Is | Action |
|---|---|
| Database connection down | Restart DB or failover to replica |
| Service out of memory | Increase heap size, restart service |
| Network latency spike | Check network team for backbone issues |
| Rate limit hit | Work with external API team to increase quota |
| Code bug causing 500s | Rollback recent deployment or patch bug |

---

## 3. Retry Storm - Detection and Response

### 3.1 Alert: "Retry Budget Exhausted - BookingService"

**What it means:**
- BookingService has exhausted its daily retry budget
- Retries are being dropped (no more attempts)
- Upstream services may see timeout errors

**Triage:**

```bash
# 1. Check retry metrics
curl localhost:8080/metrics | grep retry_budget

Output:
retry_budget_used{service="booking_db"} 0.95
retry_attempts_total{service="booking_db"} 7000

# 2. Calculate time to exhaustion
echo "Budget was 7000, current 6900"
echo "At rate of 100/min, will exhaust in 69 minutes"

# 3. Check downstream service health
kubectl get events -n database
kubectl logs -n database deployment/postgres | tail -50

# 4. Look for error patterns
grep -i "error\|fail\|timeout" service.log | tail -20
```

**Recovery Steps:**

```
1. Fix underlying service:
   - If DB slow: optimize queries or increase connections
   - If API failing: rollback bad deployment
   - If timeouts: increase timeout or scale service up

2. Increase retry budget temporarily:
   POST /api/overrides
   {
     "overrideType": "IncreaseRetryBudget",
     "service": "BookingService",
     "budgetLimit": "10000"  # doubled from 5000
   }

3. Monitor recovery:
   watch -n 5 'curl localhost:8080/metrics | grep retry_budget'

4. When service stabilizes:
   - Remove override (auto-expires in 24 hours)
   - Review why retries spiked
   - Adjust thresholds if necessary
```

---

## 4. Fallback Activation Spike

### 4.1 Alert: "SearchService Fallback Activated 50 Times (1 hour)"

**What it means:**
- SearchService is failing frequently
- Booking system falling back to empty search results
- Users see empty search results instead of recommendations

**Triage:**

```bash
# 1. Check SearchService status
curl https://search-service.internal/health

# 2. Check logs for errors
kubectl logs -n search deployment/search-service | grep -i error | tail -20

# 3. Check dependencies (Elasticsearch)
curl localhost:9200/_cluster/health

# 4. Monitor query latency
kubectl exec -it pod/search-service-xyz -- \
  tail -f /var/log/search-service.log | grep "query_duration"
```

**Recovery Steps:**

```
1. If SearchService itself is down:
   kubectl rollout restart deployment/search-service -n search

2. If Elasticsearch is down:
   kubectl rollout restart deployment/elasticsearch -n search

3. If queries are slow:
   - Check for runaway query
   - Increase Elasticsearch heap size
   - Scale up search service replicas

4. Monitor fallback rate dropping:
   watch -n 5 'kubectl logs -n booking deployment/booking | grep "fallback"'

5. Expected timeline:
   T+0: Fallback triggered, users see empty results
   T+5: SearchService restarted
   T+10: Elasticsearch recovered
   T+15: Fallback rate returns to 0
   ✅ Normal search results resume
```

---

## 5. Timeout Cascade

### 5.1 Alert: "Timeout Rate Spike - ExternalPaymentAPI"

**What it means:**
- Requests to payment API are timing out
- May cascade to booking service if not handled
- Circuit breaker should open to prevent amplification

**Triage:**

```bash
# 1. Check payment API
curl -v https://api.payment-provider.com/health --max-time 5

# 2. Check our network connectivity
traceroute api.payment-provider.com
ping api.payment-provider.com

# 3. Check current timeout rate
curl localhost:8080/metrics | grep timeout_rate
Output: timeout_rate{service="payment_api"} = 5.2

# 4. Check if circuit opened (should be automatic)
curl localhost:8080/metrics | grep circuit_state{service="payment"}
Output: circuit_breaker_state{service="payment_api"} = 1  (1 = open)
```

**Recovery Steps:**

```
1. If payment API is down:
   - Contact payment provider support
   - Check their status page
   - Estimated recovery time?

2. If network issue:
   - Check VPN/routing
   - Failover to backup connection
   - Work with network team

3. Extend timeout temporarily:
   POST /api/overrides
   {
     "service": "PaymentGateway",
     "overrideType": "ExtendTimeout",
     "value": "30 seconds"  # from 10 seconds
   }

4. What users see:
   - Existing requests: May still timeout (already in flight)
   - New requests: Fast fail (circuit open)
   - Bookings: Can't complete (payment critical)

5. When service recovers:
   - Circuit enters half-open (after timeout expires)
   - Probe request sent
   - If successful: circuit closes automatically
   - Override auto-expires after 1 hour
```

---

## 6. False Positive Alerts

### 6.1 Circuit Opens but Service is Healthy

**Symptoms:**
- Alert: "Circuit breaker opened"
- But service is responding fine
- No errors in logs

**Diagnosis:**
```bash
# 1. Check error rate
curl localhost:8080/metrics | grep "errors_total"

# 2. Check latency distribution
curl localhost:8080/metrics | grep "latency_p95"

# 3. Check circuit breaker threshold
config show service=PaymentGateway | grep failureThreshold
Output: failureThreshold: 0.50 (50% failures to open)

# Check actual failure %
echo "Success: 1000, Failures: 100" | awk '{print $5/$3*100 "%"}'
Output: 10%  (well below 50% threshold)
```

**Action:**
- Circuit should not have opened with 10% failure rate
- Check if threshold was accidentally lowered
- Check for transient spikes (e.g., deployment rolling out)
- If false positive: check for bugs in circuit breaker logic

---

## 7. Common Issues and Solutions

| Issue | Symptom | Solution |
|---|---|---|
| **Circuit stuck OPEN** | Circuit stays open > 30 min | Check if service actually recovered; manually trigger probe |
| **Retries causing amplification** | 10x load spike when 1 endpoint fails | Verify endpoint is on non-retryable list; adjust retry budget |
| **Fallback data stale** | Users seeing old recommendations | Check cache TTL; refresh cache; verify cache backend healthy |
| **Timeout too aggressive** | 80% of requests timing out | Increase timeout temporarily via override; investigate latency |
| **Probe failing continuously** | Half-open state never closes | Manually fix service; extend override to keep requests flowing |

---

## 8. Escalation Contacts

**Level 1 (0-5 min):**
- On-call engineer (page via PagerDuty)
- Check runbook (this document)

**Level 2 (5-15 min):**
- Backend team lead (@backend-lead)
- Platform team (@platform-team)

**Level 3 (15+ min):**
- CTO (@cto)
- Security team (if data-related)

**External:**
- Payment provider support: api-support@provider.com
- Infrastructure team: infrastructure@company.com

---

## 9. Success Criteria

- [ ] Runbook covers all common failure scenarios
- [ ] Recovery procedures are tested and validated
- [ ] Escalation contacts are current
- [ ] On-call engineers trained on runbook
- [ ] Decision tree for triage is clear
- [ ] Expected timelines documented

---

## Quick Reference Card

```
┌─ Circuit Breaker Open ─────────────────────┐
│ 1. Check service health                    │
│ 2. Restart if needed                       │
│ 3. Wait for half-open probe (30-60s)      │
│ 4. Should auto-close                       │
│ If persists > 5 min: escalate              │
└────────────────────────────────────────────┘

┌─ Retry Budget Exhausted ───────────────────┐
│ 1. Find failed service                     │
│ 2. Fix root cause (DB, API, etc)          │
│ 3. Increase budget override if needed      │
│ 4. Monitor budget returning to 0           │
│ 5. Remove override after recovery          │
└────────────────────────────────────────────┘

┌─ Timeout Spike ────────────────────────────┐
│ 1. Check downstream service status         │
│ 2. Verify network connectivity             │
│ 3. Extend timeout via override if critical │
│ 4. Fix root cause (scaling, optimization)  │
│ 5. Revert override when fixed              │
└────────────────────────────────────────────┘
```

**Next:** [TEST-1: Fault Injection and Chaos Suite](test-fault-injection-chaos.md)
