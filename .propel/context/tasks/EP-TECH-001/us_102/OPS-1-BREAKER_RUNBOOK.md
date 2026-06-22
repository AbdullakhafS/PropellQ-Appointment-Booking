# OPS-1: Resiliency Operations Runbook

**Document ID**: OPS-1  
**Task**: OPS-1 (Operational Runbook for Breaker States and Recovery)  
**Last Updated**: 2026-06-22  
**Status**: Active

---

## Overview

This runbook guides on-call engineers through troubleshooting resiliency issues: high timeouts, circuit breakers, retry storms, and fallback failures.

---

## 1. Rapid Response Checklist

When alerted about resiliency issue:

```
STEP 1: Identify the issue
  [ ] Read alert message
  [ ] Check which service is affected
  [ ] Determine if CRITICAL or WARNING

STEP 2: Assess impact
  [ ] Check booking completion rate
  [ ] Check user complaints in #incidents
  [ ] Determine if core path affected

STEP 3: Initial actions
  [ ] Open resiliency dashboard
  [ ] Check metrics for affected service
  [ ] Read recent logs (last 5 minutes)

STEP 4: Triage
  [ ] Is this timeout? retry? circuit breaker? fallback?
  [ ] Is it ongoing or resolved?
  [ ] Do we need to page manager on-call?
```

---

## 2. Circuit Breaker: OPEN State

### 2.1 Symptom

Alert: "Circuit breaker opened for {service}"

### 2.2 Diagnosis

```bash
# 1. Check circuit state
curl https://monitoring/api/circuit_breaker/status
# Expected output:
# service: payment_processor
# state: OPEN
# failure_rate: 65%
# opened_at: 2026-06-22T10:15:30Z

# 2. Check when it opened
opened_duration = now - opened_at
# If < 30 seconds: just opened
# If > 5 minutes: been open too long

# 3. Check failure details
curl https://monitoring/api/circuit_breaker/payment_processor/failures
# Expected: Recent 5xx errors or timeouts

# 4. Check downstream service health
curl https://payment-processor.internal/health
# Status: UP or DOWN?
```

### 2.3 Root Cause Analysis

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Circuit opened; service not responding | Service crashed/rebooted | Wait for service restart (usually 30-60s) |
| Circuit opened; service responding but slow | Service overloaded | Scale service; check for resource limits |
| Circuit opened; service healthy | Timeout too short | Increase timeout in RES-1 |
| Circuit opened; external API failing | Third-party API down | Contact third-party; activate fallback |

### 2.4 Actions

**Option A: Service recovering (most common)**
```
1. Confirm service is healthy: curl https://{service}/health
2. Wait 30+ seconds for circuit to transition to HALF_OPEN
3. Observe as probes succeed
4. Circuit automatically closes & traffic ramps up
5. Monitor error rate; if spikes, reopen circuit
```

**Option B: Service not recovering**
```
1. SSH into service
2. Check logs for errors: tail -f /var/log/service.log
3. Check resource usage: free -h, df -h, top
4. Restart service if necessary
5. Monitor circuit breaker; should close within 60s
```

**Option C: Timeout too short**
```
1. Check recent latencies: monitoring dashboard
2. If p99 latency near timeout value, increase timeout
3. Update RES-1 configuration
4. Deploy change; circuit should close naturally
5. Monitor to confirm fix
```

**Option D: External API down**
```
1. Check third-party status page
2. Contact third-party support if not listed
3. Activate fallback (already enabled in FALL-1)
4. Booking should continue with degraded functionality
5. Monitor fallback queue (OBS-1)
```

### 2.5 Manual Intervention (Emergency Only)

If circuit stuck OPEN for > 5 minutes and above steps didn't work:

```bash
# Force circuit to HALF_OPEN immediately
curl -X POST /admin/circuit-breaker/payment_processor/half_open

# Force circuit to CLOSED (USE WITH CAUTION)
curl -X POST /admin/circuit-breaker/payment_processor/close

# Then monitor closely for failures
watch -n 1 "curl https://monitoring/api/circuit_breaker/status"
```

### 2.6 Post-Incident

1. Document what happened in incident ticket
2. Root cause analysis (was it timeout? overload?)
3. Permanent fix (increase timeout? scale service? improve code?)
4. Update documentation if needed

---

## 3. High Timeout Rate

### 3.1 Symptom

Alert: "Timeout rate > 1%" or "Timeout rate very high (>10%)"

### 3.2 Diagnosis

```bash
# 1. Which endpoint has high timeouts?
curl https://monitoring/api/metrics/timeouts?endpoint="~.*"
# Shows timeout rate per endpoint

# 2. Is this new or ongoing?
curl https://monitoring/dashboards/timeout-trend?hours=24
# Check if recent spike or gradual increase

# 3. Are retries happening?
curl https://monitoring/api/metrics/retries
# See if retries are successfully masking timeouts

# 4. Check downstream service latency
curl https://monitoring/api/latency/{downstream_service}?percentile=p99
# Is downstream service just slow?
```

### 3.3 Root Cause Analysis

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Timeouts on database queries | Database overloaded/slow | Optimize query; scale database |
| Timeouts on external API calls | API slow or overloaded | Increase timeout; contact provider |
| Timeouts on search queries | Search engine slow | Add index; optimize query; scale |
| All endpoints timing out | Network/infrastructure issue | Check network; restart service |

### 3.4 Actions

**Option A: Downstream service slow**
```
1. Check p95/p99 latency
2. If latency < timeout: not a timeout issue
3. If latency >= timeout: increase timeout
4. If latency consistently high: optimize service
```

**Option B: Downstream service overloaded**
```
1. Check CPU/memory utilization
2. If > 80%: scale service horizontally
3. Add load balancer if needed
4. Monitor as new instances come online
```

**Option C: Timeout too short**
```
1. Check actual request latencies (p99)
2. If p99 > timeout: increase timeout in RES-1
3. Deploy config change
4. Monitor timeout rate; should decrease
```

**Option D: Network issue**
```
1. Check network metrics (packet loss, latency)
2. Check DNS resolution times
3. Check connection pool exhaustion
4. Restart service if connection pool exhausted
```

### 3.5 Monitoring During Fix

```bash
# Watch timeout rate improve
watch -n 5 "curl https://monitoring/api/metrics/timeout_rate"

# Check if retries are succeeding
curl https://monitoring/api/metrics/retry_success_rate

# Check circuit breaker hasn't opened
curl https://monitoring/api/circuit_breaker/status
```

---

## 4. Retry Storm

### 4.1 Symptom

Alert: "High retry rate" or "Retry budget exhausted"

### 4.2 Diagnosis

```bash
# 1. How many retries happening?
curl https://monitoring/api/metrics/retry_rate
# Expected: < 100 retries/min
# Alert: > 100 retries/min

# 2. Retry success rate?
curl https://monitoring/api/metrics/retry_success_rate
# If < 50%: retries mostly failing (amplifying issue)
# If > 90%: retries mostly working (normal)

# 3. Which endpoints retrying?
curl https://monitoring/api/metrics/retries?endpoint="~.*"
# Identify high-retry endpoints

# 4. Retry budget status
curl https://monitoring/api/retry_budget/available_tokens
# If < 100: budget exhausted soon
```

### 3.3 Root Cause Analysis

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| High retry rate; mostly succeeding (>90%) | Transient failures; normal | Monitor; retries working as designed |
| High retry rate; mostly failing (<50%) | Downstream service broken | Fix downstream service |
| Retry budget exhausted | Too many retries happening | Reduce max_retries; fix downstream |
| Retries on non-idempotent endpoints | Config error | Review RES-2; remove unsafe endpoints |

### 4.4 Actions

**Option A: Transient failures (retries working)**
```
1. Confirm downstream service is recovering
2. Monitor circuit breaker
3. If retries > 80% successful: let it continue
4. If continues for > 5 min: investigate root cause
5. Ensure budgets aren't exhausted
```

**Option B: Downstream service broken**
```
1. Identify which service (from retry_reason)
2. Check service health: curl {service}/health
3. Investigate service logs
4. Restart if necessary
5. Verify circuit breaker opens (stops retry storm)
```

**Option C: Retry budget exhausted**
```
1. Check which endpoints consuming budget
2. If legitimate: increase budget
3. If abuse: add rate limiting
4. Reduce max_retries for non-critical endpoints
5. Monitor for future exhaustion
```

**Option D: Unsafe retries**
```
1. Check RES-2 allowlist
2. Verify non-idempotent endpoints not in allowlist
3. Add payment/auth endpoints to blocklist if present
4. Deploy config fix immediately
5. Monitor for duplicate operations (payments charged twice, etc.)
```

### 4.5 Monitoring During Fix

```bash
# Watch retry rate decrease
watch -n 5 "curl https://monitoring/api/metrics/retry_rate"

# Confirm budget recovering
curl https://monitoring/api/retry_budget/available_tokens

# Check for duplicate operations (if payment affected)
curl https://monitoring/api/duplicate_charges?hours=1
```

---

## 5. Fallback Queue Growing

### 5.1 Symptom

Alert: "Fallback queue size > 50,000" or "Queue age > 24 hours"

### 5.2 Diagnosis

```bash
# 1. Which queue?
curl https://monitoring/api/fallback/queue_sizes
# Check sms_notifications, email_notifications, etc.

# 2. How fast is queue growing?
curl https://monitoring/api/fallback/queue_growth_rate
# Messages/minute being added

# 3. How fast is it processing?
curl https://monitoring/api/fallback/queue_drain_rate
# Messages/minute being processed

# 4. Age of oldest message?
curl https://monitoring/api/fallback/queue/sms_notifications/oldest_age
# Should be < 1 hour; alert if > 24 hours

# 5. Queue processor running?
curl https://services/sms-processor/health
# Status should be UP
```

### 5.3 Root Cause Analysis

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Queue growing; processor UP | Processor can't keep up | Scale processor; optimize processing |
| Queue growing; processor DOWN | Processor crashed | Restart processor; check logs |
| Queue growing; drain rate 0 | Processor not running | Check deployment; restart |
| Queue age very high | Service being queued to is down | Wait for service recovery; then process |

### 5.4 Actions

**Option A: Processor can't keep up**
```
1. Check processor CPU/memory: top
2. If high: scale processor horizontally
3. Check if batching can improve throughput
4. Optimize message processing code
5. Monitor queue drain rate; should decrease
```

**Option B: Processor crashed**
```
1. SSH into processor: ssh sms-processor
2. Check logs: tail -f /var/log/sms-processor.log
3. Look for errors or crashes
4. Restart: systemctl restart sms-processor
5. Verify with: curl https://services/sms-processor/health
```

**Option C: Service being queued to is down**
```
1. Check service status: curl {downstream}/health
2. Wait for service recovery
3. Once up, processor will resume draining queue
4. Monitor: curl https://monitoring/api/fallback/queue_size?queue=sms
5. Should decrease as processing resumes
```

**Option D: Emergency queue drain**
```
# If queue will exceed capacity before recovery:
# Manually flush queue to dead letter (WARNING: data loss)
curl -X POST /admin/fallback/sms_notifications/flush_to_dlq

# Then document in incident ticket
# Investigate why this happened
# Adjust queue capacity/SLOs if needed
```

### 5.5 Monitoring During Fix

```bash
# Watch queue size decrease
watch -n 5 "curl https://monitoring/api/fallback/queue_sizes"

# Check drain rate improving
curl https://monitoring/api/fallback/queue_drain_rate

# Confirm no more messages being queued
curl https://monitoring/api/fallback/enqueue_rate
```

---

## 6. Fallback Failure (Dead Letter Queue Growing)

### 6.1 Symptom

Alert: "Dead letter queue growing" or "> 100 messages in DLQ per hour"

### 6.2 Diagnosis

```bash
# 1. Check DLQ size
curl https://monitoring/api/fallback/dead_letter_queue_size

# 2. Why are messages failing?
curl https://monitoring/api/fallback/dead_letter_reasons
# Common: "max_retries_exceeded", "invalid_message_format"

# 3. Which service being messaged?
curl https://monitoring/api/fallback/dead_letter_services
# Example: sms_service, email_service, etc.

# 4. How old are these failures?
curl https://monitoring/api/fallback/dead_letter_age
```

### 6.3 Root Cause Analysis

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| DLQ growing; service working | Message corrupted | Fix message format; retry |
| DLQ growing; service down | Retried but service never recovered | Wait for service recovery; manual retry |
| DLQ growing; different endpoint | Endpoint changed/removed | Update fallback code; redeploy |
| DLQ growing continuously | Fundamental issue | Investigate root cause; may need data cleanup |

### 6.4 Actions

**Option A: Service temporarily down (likely)**
```
1. Check if downstream service is up
2. If not up: wait for recovery
3. Once up: manually retry DLQ messages
4. Use: curl -X POST /admin/fallback/dead_letter_retry?queue=sms
5. Monitor as messages are reprocessed
```

**Option B: Message format issue**
```
1. Sample a DLQ message: curl https://monitoring/api/fallback/dead_letter_sample
2. Check if valid format
3. If corrupted: delete and investigate why
4. If format changed: update processing code
5. Redeploy and retry
```

**Option C: Endpoint configuration error**
```
1. Check fallback config: cat /etc/config/fallback.yaml
2. Verify endpoint URL is correct
3. Verify retry limits reasonable
4. Fix configuration
5. Redeploy; retry DLQ
```

**Option D: Manual recovery**
```bash
# Export DLQ messages for manual processing
curl https://monitoring/api/fallback/export_dlq?format=csv > dlq_export.csv

# Manually process (e.g., send SMS via alternative provider)
python scripts/manual_send_sms.py dlq_export.csv

# Clear DLQ once processed
curl -X POST /admin/fallback/dead_letter_clear?queue=sms
```

### 6.5 Post-Incident

1. Investigate why DLQ reached critical size
2. Increase processing capacity
3. Add alerting for DLQ growth earlier
4. Consider immediate retry (vs. eventual) for critical messages
5. Document in runbook

---

## 7. Half-Open State Stuck

### 7.1 Symptom

Alert: "Circuit breaker stuck in HALF_OPEN for > 10 minutes"

### 7.2 Diagnosis

```bash
# 1. How long in HALF_OPEN?
curl https://monitoring/api/circuit_breaker/{service}/time_in_half_open
# Should be < 30 seconds normally

# 2. Are probes running?
curl https://monitoring/api/circuit_breaker/{service}/probe_history
# Should see recent probe attempts

# 3. Probe success rate?
curl https://monitoring/api/circuit_breaker/{service}/probe_success_rate
# Should see some successes eventually

# 4. What are probes returning?
curl https://monitoring/api/circuit_breaker/{service}/probe_results?limit=10
# Check recent probe responses
```

### 7.3 Root Cause Analysis

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| HALF_OPEN; no probe success | Service still not recovered | Wait; will eventually close or reopen |
| HALF_OPEN; probe success rate increasing | Service recovering | Wait; should close within 60s |
| HALF_OPEN; probes not running | Probe scheduler stuck | Restart circuit breaker process |
| HALF_OPEN; probe config wrong | Wrong endpoint/timeout | Fix probe config; restart |

### 7.4 Actions

**Option A: Service slowly recovering**
```
1. Confirm service is coming back online
2. Check service latency improving
3. Wait for probes to succeed (usually 30-60s)
4. Circuit will close automatically
5. Monitor error rate during traffic ramp-up
```

**Option B: Service won't recover**
```
1. If > 10 min in HALF_OPEN: service won't recover
2. SSH into service: ssh {service}
3. Check logs for persistent issues
4. Restart service if needed
5. If still failing: escalate to owner; may need manual fix
```

**Option C: Probe scheduler stuck**
```
1. Check if circuit breaker process running
2. ps aux | grep circuit_breaker
3. If not running: restart
4. systemctl restart circuit_breaker
5. Should immediately transition to CLOSED or reopen
```

**Option D: Probe configuration wrong**
```
1. Check probe config: cat /etc/config/circuit_breaker.yaml
2. Verify probe endpoint is correct
3. Verify probe timeout reasonable
4. Fix configuration
5. Restart circuit breaker; should probe correctly now
```

### 7.5 Emergency: Force Close

If stuck > 20 minutes and service is actually healthy:

```bash
# Force circuit to CLOSED
curl -X POST /admin/circuit-breaker/{service}/force_close

# THEN monitor closely
# If errors spike: service wasn't ready; reopen
# If healthy: problem was probe config
```

---

## 8. Key Metrics to Watch

```
While troubleshooting, monitor these in real-time:

resiliency.circuit_breaker.state
  Should be 0 (CLOSED) after fix

resiliency.circuit_breaker.failure_rate
  Should trend downward

resiliency.timeout.rate_percent
  Should be < 1%

resiliency.retry.success_rate
  Should be > 90%

resiliency.fallback.queue_size
  Should be stable or decreasing

resiliency.fallback.dead_letter_count
  Should be stable or decreasing
```

---

## 9. Escalation Path

```
Issue severity: WARNING
├─ On-call engineer investigates
├─ If not resolved in 15 min: escalate to Tech Lead

Issue severity: CRITICAL
├─ Page on-call engineer immediately
├─ Tech Lead notified
├─ If not resolved in 10 min: page Engineering Manager
└─ If not resolved in 20 min: page CTO
```

---

## 10. Links & References

- RES-1 through RES-4: Policy documents
- FALL-1 & FALL-2: Fallback guidelines
- OBS-1: Metrics & alerts (what to monitor)
- Dashboards:
  - `/monitoring/dashboards/resiliency-overview`
  - `/monitoring/dashboards/resiliency/{service}`
  - `/monitoring/dashboards/fallback-status`

---

**Document Owner**: Infrastructure/On-Call Team  
**Last Review**: 2026-06-22  
**Next Review**: 2026-09-22  
**Last Updated**: 2026-06-22
