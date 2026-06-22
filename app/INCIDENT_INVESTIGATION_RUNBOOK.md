# Incident Investigation Runbook (DOC-1)

**Task**: TASK-099: Implement Centralized Logging with Correlation IDs  
**Component**: DOC-1 - Incident Investigation Runbook  
**Date**: 2026-06-22

## Quick Reference

**Common Investigation Commands**:

```python
# All events for a correlation ID (AC-2)
QueryBuilder()\
  .with_correlation_id("550e8400-e29b-41d4-a716-446655440000")\
  .sort_by_time_asc()

# Production errors in last hour (AC-5)
IncidentQuery.production_errors(minutes=60)

# Service failures (AC-5)
IncidentQuery.service_failures("booking_service", hours=1)

# Timeline reconstruction (AC-2)
TimelineBuilder(correlation_id).build()
```

---

## 1. Incident Triage

### Step 1: Obtain Correlation ID

**From Error Response**:
```json
{
  "success": false,
  "error": {
    "code": "SERVICE_UNAVAILABLE"
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-06-22T10:30:00Z"
}
```

**From User Report**:
- Ask for "Request ID" or "Ref #" from user
- Often shown in error message
- Example: "Error REF: 550e8400-e29b-41d4"

**From Alert System**:
- Embedded in incident ticket
- Or search recent errors by service/time

**From Logs**:
```
First search for similar error message in last 5 minutes
Look for correlation_id in matching entries
```

### Step 2: Extract Basic Info

Once you have correlation ID `CORR_ID`:

```python
# Get all events
query = QueryBuilder()\
  .with_correlation_id(CORR_ID)\
  .with_last_hours(1)\
  .sort_by_time_asc()

# Look for:
# - First event (request entry point)
# - Last event (response or error)
# - Any ERROR/CRITICAL entries
# - Timing of each service transition
```

### Step 3: Identify Scope

From initial events, note:

- **Affected Service**: Which service generated error
- **User/Account**: From `actor` field
- **Route/Operation**: From `route` field
- **Time Window**: When did it occur
- **Severity**: ERROR, CRITICAL, WARNING

---

## 2. Investigation Workflow

### Phase 1: Timeline Reconstruction (AC-2)

**Goal**: Understand the sequence of events

**Query**:
```python
QueryBuilder()\
  .with_correlation_id(CORR_ID)\
  .sort_by_time_asc()\
  .to_query_dict()
```

**Analyze**:
1. **Request start**: First log entry with source=API
2. **Service calls**: Trace through each service transition
3. **Database operations**: Look for slow queries
4. **Error location**: First ERROR/CRITICAL entry
5. **Request end**: Final response (success or failure)

**Example Timeline**:
```
10:30:00.001  API                Request start
10:30:00.050  booking_service    Fetching appointment
10:30:00.120  database           Query appointment
10:30:00.150  database           Connection timeout
10:30:00.160  booking_service    Retry attempt 1
10:30:00.500  booking_service    Retry attempt 2 (failed)
10:30:02.000  API                Response: 503 error
```

### Phase 2: Root Cause Analysis

**Find first ERROR**:
```python
query = QueryBuilder()\
  .with_correlation_id(CORR_ID)\
  .with_error_only()\
  .limit(1)\
  .sort_by_time_asc()
```

**Extract Details**:
- Error message
- Error code
- Service where error originated
- Associated context (user, operation, etc.)

**Check Common Issues**:

| Issue | Check | Query |
|-------|-------|-------|
| **Database Timeout** | Connection pool | Search for "timeout" in db logs |
| **Service Degradation** | Sister service logs | Look for cascading failures |
| **Resource Exhaustion** | Memory/CPU | Check ops metrics |
| **Configuration Change** | Recent deployments | Check timestamp vs deploy times |

### Phase 3: Impact Assessment (AC-5)

**How many users affected?**
```python
QueryBuilder()\
  .with_service(affected_service)\
  .with_error_only()\
  .with_last_minutes(30)\
  .to_query_dict()
```

**Calculate**:
- Total errors in last 30 minutes
- Affected user count (distinct `actor` values)
- Success rate for affected service

**Severity Matrix**:

| Affected | Duration | Severity |
|----------|----------|----------|
| 1-5 users | <5 min | P4 (Low) |
| 5-50 users | 5-30 min | P3 (Medium) |
| 50-500 users | >30 min | P2 (High) |
| >500 users | Any | P1 (Critical) |

---

## 3. Common Investigation Patterns

### Pattern 1: Cross-Service Timeout

**Symptom**: Service A times out calling Service B

**Investigation**:
```python
# Get timeline for correlation
timeline_query = QueryBuilder()\
  .with_correlation_id(CORR_ID)\
  .sort_by_time_asc()

# Look for duration_ms in logs
# If duration_ms approaches timeout threshold (e.g., 30s)
# Check Service B logs around same time

# Query Service B for same time window
service_b_errors = QueryBuilder()\
  .with_service("service_b")\
  .with_error_only()\
  .with_time_range(start_time, end_time)
```

**Resolution Path**:
1. Check Service B availability
2. Review Service B error logs
3. Check database connection pool
4. Increase timeout if Service B is legitimately slow

### Pattern 2: Cascading Failure

**Symptom**: One service fails, causing errors in other services

**Investigation**:
```python
# Get parent service errors
parent_errors = QueryBuilder()\
  .with_service("parent_service")\
  .with_error_only()\
  .with_last_minutes(10)

# For each error, check dependent service
for error in parent_errors:
  child_query = QueryBuilder()\
    .with_parent_id(error['correlation_id'])\
    .with_error_only()
```

**Resolution Path**:
1. Fix the first (root) service
2. Dependent services recover automatically
3. Monitor for recovery completion

### Pattern 3: Slow Query Performance

**Symptom**: High latency in specific operation

**Investigation**:
```python
# Find slow requests
slow_requests = QueryBuilder()\
  .with_source("DATABASE")\
  .with_last_hours(1)\
  .to_query_dict()
# Filter manually for duration_ms > 1000ms

# Or search by correlation if known
timeline = QueryBuilder()\
  .with_correlation_id(CORR_ID)\
  .sort_by_time_asc()
# Look for duration_ms values
```

**Resolution Path**:
1. Identify slow query from logs
2. Run EXPLAIN PLAN in database
3. Add index if needed
4. Or optimize query logic

### Pattern 4: Deployment-Related Issue

**Symptom**: Errors started after deployment

**Investigation**:
```python
# Errors in last hour
errors = QueryBuilder()\
  .with_environment("production")\
  .with_error_only()\
  .with_last_hours(1)

# Group by timestamp to find sudden spike
# If spike correlates with deployment time, likely cause

# Check deployed service logs
deployed_service_logs = QueryBuilder()\
  .with_service("newly_deployed")\
  .with_severity_min("WARNING")\
  .with_last_minutes(30)
```

**Resolution Path**:
1. Review deployment changelog
2. Check for configuration mistakes
3. Verify database migrations completed
4. Rollback if needed

---

## 4. Query Library (SEARCH-1, AC-5)

### User-Focused Queries

**All transactions for a user** (AC-5):
```python
QueryBuilder()\
  .with_actor("user_123")\
  .with_last_hours(24)\
  .sort_by_time_desc()
```

**Failed operations for user**:
```python
QueryBuilder()\
  .with_actor("user_123")\
  .with_failures_only()\
  .with_last_hours(24)
```

### Service-Focused Queries

**Service health check** (AC-5):
```python
QueryBuilder()\
  .with_service("booking_service")\
  .with_last_hours(1)\
  .to_query_dict()

# Count: total, success, failure
# Calculate: success rate
```

**Service dependency chain**:
```python
# All services called from booking_service
QueryBuilder()\
  .with_service("booking_service")\
  .with_last_minutes(10)\
  .to_query_dict()
# Look at parent_id fields to trace dependencies
```

### Time-Based Queries

**Peak error times**:
```python
QueryBuilder()\
  .with_environment("production")\
  .with_error_only()\
  .with_last_hours(24)\
  .sort_by_time_desc()
# Group results by hour to find problematic time window
```

**Before/after change**:
```python
# Before change (2 hours before)
before = QueryBuilder()\
  .with_time_range(start - 2h, start)

# After change (2 hours after)
after = QueryBuilder()\
  .with_time_range(start, start + 2h)

# Compare metrics: success rate, latency, error types
```

### Environment-Specific Queries

**Production errors only** (AC-5):
```python
IncidentQuery.production_errors(minutes=30)
```

**Cross-environment comparison**:
```python
# Same operation in different environments
for env in ["development", "staging", "production"]:
  QueryBuilder()\
    .with_environment(env)\
    .with_route("/api/appointments/book")\
    .with_last_hours(1)
```

---

## 5. Debugging Checklist

### Pre-Investigation

- [ ] Gather correlation ID
- [ ] Note incident time
- [ ] Confirm affected service
- [ ] Check if ongoing or resolved

### Timeline Phase

- [ ] Retrieve all events for correlation ID (AC-2)
- [ ] Verify request start and end
- [ ] Identify all services involved
- [ ] Note timing of each transition

### Root Cause Phase

- [ ] Find first ERROR/CRITICAL log entry
- [ ] Extract error message and code
- [ ] Check for timeouts or resource limits
- [ ] Verify external service availability
- [ ] Check recent deployments/config changes

### Resolution Phase

- [ ] Implement fix
- [ ] Deploy to staging/production
- [ ] Monitor for recovery (new correlation IDs succeed)
- [ ] Update incident ticket with summary

### Post-Incident

- [ ] Document in runbook if new pattern
- [ ] Add monitoring/alerting if needed
- [ ] Schedule postmortem if P1/P2 severity
- [ ] Archive logs for audit trail

---

## 6. Advanced Techniques

### Tracing Distributed Transactions

**Multi-hop tracing** (AC-2):
```python
# Start with user-facing correlation
corr_id = "550e8400-e29b-41d4-a716-446655440000"

# Get all events
events = query(correlation_id=corr_id)

# For each child call, follow parent_id
for event in events:
  if event['parent_id']:
    child_events = query(parent_id=event['parent_id'])
```

### Performance Profiling

**Identify slowest service in chain**:
```python
# Get timeline
timeline = TimelineBuilder(corr_id).build()

# Find event with max duration_ms
slowest = max(timeline['events'], 
              key=lambda e: e.get('duration_ms', 0))

# Investigate that service specifically
```

### Comparing Incident Patterns

**Find similar incidents**:
```python
# Get first error from incident
incident_error = get_first_error(corr_id)

# Find similar errors
similar = QueryBuilder()\
  .with_service(incident_error['service'])\
  .with_severity_min("ERROR")\
  .with_last_hours(24)\
  .to_query_dict()

# Compare patterns and frequency
```

---

## 7. Emergency Procedures

### Immediate Incident Response

**For P1 (Critical) Incidents**:

1. **Declare Incident** (within 2 minutes)
   - Page on-call incident commander
   - Post to #incidents channel
   - Include correlation ID

2. **Triage** (within 5 minutes)
   - Extract correlation ID
   - Determine affected service
   - Check cascade to other services

3. **Mitigation** (within 15 minutes)
   - Apply quick fix or rollback
   - Verify recovery in logs
   - Confirm success rate restored

### Debug Mode Activation

**For hard-to-reproduce issues**:

1. **Request approval** from tech lead
2. **Enable debug logging** for affected service
3. **Duration**: Maximum 2 hours
4. **Manual revocation** required after
5. **All debug logs** retained for 48 hours

### Log Access for Investigation

**Requesting unredacted logs**:

1. File incident ticket with justification
2. Get security team approval
3. Access granted for 48 hours
4. All access logged in audit trail

---

## 8. Troubleshooting

### Issue: Can't Find Correlation ID

**Solutions**:
- Check error response in application
- Search logs by timestamp and user
- Ask user for approximate time
- Check alert system for correlation ID

### Issue: No Logs for Correlation ID

**Possible Causes**:
- Request failed before logging
- Correlation ID was regenerated
- Logs deleted (past retention window)
- Access denied for this user/service

**Actions**:
- Check if request reached API at all
- Look for time window before correlation ID was generated
- Request log retention extension if needed

### Issue: Timeline Has Gaps

**Common Causes**:
- Different correlation IDs in child calls
- External service not propagating ID
- Async operations not included

**Actions**:
- Check parent_id for related events
- Look for separate log entries from external service
- Search by user_id if available

---

## Next Steps

1. **For Common Issues**: Reference patterns in Section 3
2. **For New Patterns**: Add to runbook and update query library
3. **For Escalation**: Page incident commander with correlation ID
4. **For Long-Term**: File ticket to add monitoring/alerting

---

**Need Help?**
- Tech Lead: tech-lead@propellq.com
- On-Call: Check #oncall Slack channel
- Security Questions: security@propellq.com
