# PERF-2: Query Plan and Latency Tuning

**Task ID:** PERF-2  
**Parent:** TASK-104  
**Category:** Indexing and Query  
**Points:** 6  
**Status:** Planned (parallel with INDEX-2)  
**Created:** 2026-06-22

---

## Objective

Iterate on schema and indexes to ensure all critical queries meet latency targets, with no regression in write performance.

---

## Inputs

- PERF-1 baseline benchmark results
- INDEX-1 index candidates
- Latency targets (5-50ms p95 range)
- Query plans from PERF-1

---

## Outputs

- [ ] Optimized query plans (EXPLAIN output before/after)
- [ ] Index modifications applied and tested
- [ ] Mixed workload validation (read + write concurrent)
- [ ] Final latency report with p50/p95/p99
- [ ] Query plan snapshots saved for regression detection

---

## Acceptance Criteria

1. **Query Latency Targets:**
   - [ ] **Hot Query 1 (patient lookup):** p95 < 5ms
   - [ ] **Hot Query 2 (provider schedule):** p95 < 10ms
   - [ ] **Hot Query 3 (clinic queue):** p95 < 15ms
   - [ ] **Medium Query 4 (patient profile):** p95 < 50ms

2. **No Write Regression:**
   - [ ] Insert latency: p95 < 10ms
   - [ ] Update latency: p95 < 15ms
   - [ ] Delete latency: p95 < 10ms

3. **Plan Stability:**
   - [ ] Query plans stable across 3 benchmark runs
   - [ ] No unexpected full-table scans
   - [ ] Index usage consistent

4. **Concurrent Workload:**
   - [ ] 1000 concurrent readers + 50 concurrent writers
   - [ ] No timeout failures
   - [ ] p95 latencies maintained under load

---

## Implementation Details

### Query Tuning Process

**Step 1: Analyze Baseline Plans**
```sql
EXPLAIN ANALYZE
SELECT appointment_id, scheduled_start_time, provider_id, appointment_status
FROM appointment
WHERE patient_id = 12345 AND appointment_status IN ('scheduled', 'confirmed')
ORDER BY scheduled_start_time ASC
LIMIT 10;

-- Expected BEFORE: Full table scan or insufficient index
-- type: ALL, rows: 500000, Extra: Using where; Using filesort
```

**Step 2: Apply Index from INDEX-1**
```sql
ALTER TABLE appointment ADD INDEX idx_patient_status_time
  (patient_id, appointment_status, scheduled_start_time);

ANALYZE TABLE appointment;
```

**Step 3: Verify Query Plan**
```sql
EXPLAIN ANALYZE ...same query...

-- Expected AFTER: Index range scan
-- type: range, rows: ~100, Extra: Using index; Using where
-- Latency improvement: 200ms → 3ms
```

### Tuning Template

For each hot query:

| Query | Baseline (ms) | Optimized (ms) | Index Added | Improvement |
|---|---|---|---|---|
| Patient appointments | 150 | 4 | (patient_id, status, time) | 97.3% |
| Provider schedule | 250 | 9 | (provider_id, time) | 96.4% |
| Clinic queue | 180 | 12 | (clinic_id, time, status) | 93.3% |
| Patient profile | 400 | 48 | Covering (patient_id, time) | 88.0% |

### Mixed Workload Benchmark

```python
import concurrent.futures
import time

def read_workload():
    """Simulate patient query load"""
    for _ in range(100):
        patient_id = random.randint(1, 100000)
        # Execute patient appointment query
        
def write_workload():
    """Simulate appointment creation"""
    for _ in range(10):
        # Execute appointment insert
        pass

# Run concurrent workload
with concurrent.futures.ThreadPoolExecutor(max_workers=1050) as executor:
    read_futures = [executor.submit(read_workload) for _ in range(1000)]
    write_futures = [executor.submit(write_workload) for _ in range(50)]
    
    # Measure latencies and collect results
```

### Performance Monitoring

```sql
-- Check index usage during benchmark
SELECT OBJECT_SCHEMA, OBJECT_NAME, INDEX_NAME, COUNT_READ, COUNT_WRITE, COUNT_DELETE
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE OBJECT_SCHEMA = 'appointment_db'
ORDER BY COUNT_READ DESC;

-- Verify query plans are using indexes
EXPLAIN FORMAT=JSON
SELECT ... FROM appointment WHERE patient_id = ? ...;

-- Check for slow queries (if query_time > 50ms)
SELECT * FROM performance_schema.events_statements_summary_by_digest
WHERE DIGEST_TEXT LIKE '%appointment%'
ORDER BY SUM_TIMER_WAIT DESC;
```

---

## Success Metrics

- [ ] All 4 hot queries meet p95 latency targets
- [ ] Query plans stable (same plan on repeated runs)
- [ ] Write performance: <10ms p95 for insert, <15ms for update
- [ ] 1000 concurrent users sustained without errors
- [ ] 50+ concurrent writes don't block reads

---

## Definition of Done

- [ ] All query latency targets met
- [ ] Write performance verified (no regression)
- [ ] Query plans captured and stored
- [ ] Concurrent workload validation passed
- [ ] Ready for INDEX-2 cleanup

---

## Next Task

→ INDEX-2: Index Rationalization and Cleanup
