# Query Plan Analysis and Latency Tuning Report

**Date:** 2026-06-22  
**Version:** 1.0  
**Status:** Production Validation Framework  

---

## 1. Query Plan Methodology

### 1.1 Analysis Framework

Each hot-path query is evaluated using the following criteria:

| Criterion | Method | Target | Validation |
|---|---|---|---|
| **Index Utilization** | EXPLAIN QUERY PLAN | Query must use index, not full table scan | No table scan for primary predicate |
| **Rows Scanned** | Query cost estimate | Estimated rows ≤ 10% of table size | Validate against cardinality |
| **Row Selectivity** | Predicate analysis | First predicate filters ≥ 90% of rows | Plan shows efficient narrowing |
| **Latency Baseline** | Benchmark execution | Actual p95 latency vs. SLA | Captured in benchmark_results.json |
| **Mixed Workload** | Concurrent R/W test | Write latency increase ≤ 10% | No index contention observed |

### 1.2 Expected Query Plan Format

```
SQLite EXPLAIN QUERY PLAN output:
0|0|0|SEARCH appointments USING idx_appointments_specialty_date (specialty_id=? AND appointment_date=? AND start_time>?)
```

**Plan Component Breakdown:**
- `SEARCH`: Uses index (good); `SCAN` means full table scan (bad)
- `idx_appointments_specialty_date`: Index name being used
- `(specialty_id=? AND appointment_date=?)`: Covered predicates
- Filter predicates in WHERE clause completed by row-level filtering

---

## 2. Hot-Path Query Plans

### 2.1 Query: Appointment Availability Search (CRITICAL)

**Business Context:** Find available slots by specialty and date for booking search.

**SQL:**
```sql
SELECT * FROM appointments 
WHERE status = 'available' 
  AND specialty_id = ? 
  AND appointment_date = ?
ORDER BY start_time 
LIMIT 20;
```

**Expected Plan:**
```
0|0|0|SEARCH appointments USING idx_appointments_specialty_date (specialty_id=? AND appointment_date=?)
1|0|0|USE TEMP B-TREE FOR ORDER BY
```

**Analysis:**
- **Index:** `idx_appointments_specialty_date(specialty_id, appointment_date, start_time, id)`
- **Coverage:** Predicates ✓, ORDER BY ✓, row limit ✓
- **Estimated Rows:** 50-200 per query (1M appointments / 10k days / 500 providers ≈ 200 rows per day-provider combo)
- **Selectivity:** specialty_id (1/100k providers) → appointment_date (1/90 days) = 0.0001% initial filter
- **Latency Target:** 100ms p95

**Validation Steps:**
1. Run EXPLAIN for multiple date/specialty combinations
2. Verify start_time is covered in index
3. Confirm no hash/sort needed post-index
4. Benchmark 1000x iterations; capture p95

**Possible Issues and Remediation:**
- **Issue:** Query plan shows SCAN instead of SEARCH
  - **Cause:** Index not being selected (cost estimate issue)
  - **Fix:** Verify index exists; run ANALYZE to update statistics
  
- **Issue:** p95 latency > 100ms
  - **Cause:** Index column order suboptimal; too many rows returned
  - **Fix:** Reorder index as `(specialty_id, appointment_date, start_time)` and re-benchmark

---

### 2.2 Query: Reservation State Check (CRITICAL)

**Business Context:** Verify active reservation exists during checkout.

**SQL:**
```sql
SELECT * FROM appointment_reservations 
WHERE appointment_id = ? 
  AND status = 'active' 
  AND expires_at > CURRENT_TIMESTAMP 
LIMIT 1;
```

**Expected Plan:**
```
0|0|0|SEARCH appointment_reservations USING idx_reservations_active (status=? AND expires_at>?)
```

**Analysis:**
- **Index:** `idx_reservations_active(status, expires_at, appointment_id)`
- **Coverage:** Predicates ✓, early row termination ✓
- **Estimated Rows:** 1 (uniqueness of active reservation per appointment)
- **Selectivity:** status = 'active' (assume 30% of 300k reservations = 90k); expires_at > now (age-weighted, ~70% active)
- **Latency Target:** 50ms p95

**Validation Steps:**
1. Verify index predicate order matches query predicates
2. Confirm LIMIT 1 causes early termination
3. Benchmark 1000x iterations

**Possible Issues and Remediation:**
- **Issue:** expires_at comparison triggers full scan despite index
  - **Cause:** Query planner unable to use index for timestamp range
  - **Fix:** Ensure timestamp column type matches (TEXT ISO 8601); verify CURRENT_TIMESTAMP() is index-friendly

---

### 2.3 Query: Calendar Sync Queue Dequeue (CRITICAL)

**Business Context:** Fetch pending sync jobs for background workers.

**SQL:**
```sql
SELECT * FROM calendar_sync_queue 
WHERE status = 'pending' 
  AND scheduled_retry_at <= CURRENT_TIMESTAMP 
  AND retry_count < 3
ORDER BY created_at 
LIMIT 100;
```

**Expected Plan:**
```
0|0|0|SEARCH calendar_sync_queue USING idx_calendar_sync_queue_dequeue (status=? AND scheduled_retry_at<=?)
1|0|0|USE TEMP B-TREE FOR ORDER BY
```

**Analysis:**
- **Index:** `idx_calendar_sync_queue_dequeue(status, scheduled_retry_at, calendar_type, retry_count)`
- **Coverage:** status ✓, scheduled_retry_at ✓; retry_count used for row filtering
- **Estimated Rows:** 50-200 pending jobs at any time (assuming 100k sync queue entries with 0.1% pending)
- **Selectivity:** status = 'pending' (10%) → scheduled_retry_at <= now (varies; ~5-10% pending & ready)
- **Latency Target:** 100ms p95

**Validation Steps:**
1. Confirm index covers status and scheduled_retry_at
2. Verify retry_count < 3 filters efficiently on already-narrow set
3. Benchmark dequeue operation with concurrent workers

---

### 2.4 Query: Patient Profile Lookup (CRITICAL)

**Business Context:** Resolve patient during login or profile load.

**SQL:**
```sql
SELECT * FROM patient_profiles 
WHERE email = ?;
```

**Expected Plan:**
```
0|0|0|SEARCH patient_profiles USING idx_patient_profiles_email (email=?)
```

**Analysis:**
- **Index:** `idx_patient_profiles_email(email)`; UNIQUE constraint ensures single result
- **Coverage:** email ✓; unique index guarantees O(1) lookup
- **Estimated Rows:** 1 (uniqueness constraint)
- **Selectivity:** 100% (unique key)
- **Latency Target:** 50ms p95

**Validation Steps:**
1. Confirm UNIQUE constraint on email
2. Verify index used directly (not filtered post-hoc)
3. Benchmark 1000x random email lookups

---

### 2.5 Query: Reminder Audit Trail (OPERATIONAL)

**Business Context:** Fetch reminder delivery history for customer support.

**SQL:**
```sql
SELECT * FROM reminder_log 
WHERE appointment_id = ? 
  AND reminder_type IN ('48h', '24h', '2h')
ORDER BY created_at DESC 
LIMIT 10;
```

**Expected Plan:**
```
0|0|0|SEARCH reminder_log USING idx_reminder_log_lookup (appointment_id=? AND reminder_type=?)
1|0|0|USE TEMP B-TREE FOR ORDER BY
```

**Analysis:**
- **Index:** `idx_reminder_log_lookup(appointment_id, patient_profile_id, reminder_type, channel, delivery_status, created_at)`
- **Coverage:** appointment_id ✓, reminder_type ✓; ORDER BY DESC may need in-memory sort
- **Estimated Rows:** 3-10 reminder events per appointment (based on data generation)
- **Selectivity:** appointment_id (1/1M) → reminder_type IN (...) (3/4 = 75%)
- **Latency Target:** 100ms p95

**Validation Steps:**
1. Verify appointment_id narrows to few rows
2. Check IN clause performance
3. Confirm ORDER BY DESC uses index or minimal sort

---

### 2.6 Query: Provider Availability Timeline (OPERATIONAL)

**Business Context:** Fetch provider's available appointments over a date range.

**SQL:**
```sql
SELECT * FROM appointments 
WHERE provider_id = ? 
  AND status = 'available' 
  AND appointment_date BETWEEN ? AND ?
ORDER BY start_time;
```

**Expected Plan:**
```
0|0|0|SEARCH appointments USING idx_appointments_provider_date (provider_id=? AND appointment_date>=? AND appointment_date<=?)
1|0|0|USE TEMP B-TREE FOR ORDER BY
```

**Analysis:**
- **Index:** `idx_appointments_provider_date(provider_id, appointment_date, start_time, id)`
- **Coverage:** provider_id ✓, appointment_date range ✓, start_time ORDER BY ✓
- **Estimated Rows:** 100-500 (provider × 30-day window with 2-3 slots/hour)
- **Selectivity:** provider_id (1/100k) → date range (30/90) → status filter post-index
- **Latency Target:** 100ms p95

**Validation Steps:**
1. Verify index uses BETWEEN efficiently
2. Confirm start_time in ORDER BY is covered by index
3. Benchmark with various date ranges

---

## 3. Index Effectiveness Validation Checklist

### 3.1 Pre-Deployment Validation

- [ ] All mandatory indexes created and verified in production schema
- [ ] EXPLAIN QUERY PLAN for each hot-path query shows index usage
- [ ] No queries show full table scan for critical predicates
- [ ] Benchmark results (p50/p95/p99) stored in benchmark_results.json
- [ ] All SLA targets (100ms, 50ms) met or exceeded
- [ ] Query plans captured as baseline for future regression testing

### 3.2 Post-Deployment Validation

- [ ] Production database queries show same index plans as benchmark
- [ ] Real workload latencies match benchmark predictions (±20%)
- [ ] No index contention or lock waits observed in monitoring
- [ ] Index space usage within expected bounds
- [ ] Write latency increase acceptable (< 10% slowdown on inserts)

---

## 4. Benchmark Execution Guide

### 4.1 Generate Representative Dataset

```bash
cd app/db
python benchmark.py --mode generate
# Output: benchmark_test.db (created with 1M appointments, 100k providers, etc.)
```

### 4.2 Run Query Benchmarks

```bash
python benchmark.py --mode benchmark
# Output: benchmark_results.json with p50/p95/p99 latencies
```

### 4.3 Analyze Query Plans

```bash
python benchmark.py --mode analyze
# Output: EXPLAIN QUERY PLAN output for each hot path
```

### 4.4 Cleanup Test Database

```bash
python benchmark.py --mode cleanup
# Removes benchmark_test.db and benchmark_results.json
```

---

## 5. Results Interpretation

### 5.1 Example Results JSON

```json
{
  "timestamp": "2026-06-22T10:15:00",
  "config": {
    "specialties_count": 10000,
    "providers_count": 100000,
    "appointments_count": 1000000,
    "reservations_per_appointment": 0.3,
    "reminder_events_per_appointment": 3
  },
  "results": {
    "availability_search": {
      "p50_ms": 8.5,
      "p95_ms": 18.3,
      "p99_ms": 25.1,
      "sla_target_ms": 100,
      "sla_status": "PASS"
    },
    "reservation_check": {
      "p50_ms": 2.1,
      "p95_ms": 4.8,
      "p99_ms": 7.2,
      "sla_target_ms": 50,
      "sla_status": "PASS"
    }
  }
}
```

### 5.2 Interpreting Metrics

- **p50_ms:** Median latency; typical performance for 50% of queries
- **p95_ms:** 95th percentile latency; SLA target threshold
- **p99_ms:** 99th percentile; captures outliers and worst-case
- **sla_status:** PASS if p95 ≤ target; FAIL if p95 > target

### 5.3 SLA Failure Remediation

**If SLA Status = FAIL:**

1. **Check Query Plan:** EXPLAIN QUERY PLAN to verify index is used
2. **Verify Index Exists:** Query sqlite_master table
3. **Run ANALYZE:** Update statistics for query planner
4. **Reorder Index Columns:** Adjust column order to match predicate order
5. **Increase Benchmark Iterations:** Run 1000+ iterations to exclude noise
6. **Check Database Size:** Ensure benchmark dataset matches expected cardinality

---

## 6. Next Steps

### 6.1 Integration with CI/CD

- Integrate benchmark.py into nightly CI pipeline
- Generate baseline results for each schema version
- Alert if p95 latencies regress > 10% vs. previous baseline
- Archive results for trend analysis

### 6.2 Production Monitoring

- Implement APM instrumentation for hot-path queries
- Monitor real-world p95 latencies vs. benchmark predictions
- Capture EXPLAIN QUERY PLAN from production periodically
- Alert if production latencies exceed SLA targets

---

## 7. Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-06-22 | Initial query plan analysis framework; 6 hot-path queries; SLA validation checklist |

