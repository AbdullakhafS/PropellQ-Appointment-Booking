# QA-1 through QA-5: Testing and Validation Suite

**Task ID:** QA-1, QA-2, QA-3, QA-4, QA-5  
**Parent:** TASK-104  
**Category:** Testing and Validation  
**Total Points:** 8  
**Status:** Planned (run in parallel during final phase)  
**Created:** 2026-06-22

---

## Overview

Comprehensive QA validation suite covering data integrity, performance, uniqueness, naming consistency, and index effectiveness. All 5 tests should run in parallel during the final validation phase.

---

## QA-1: Integrity Constraint Validation (2 pts)

**Objective:** Validate that PK/FK/CHECK constraints work correctly for data integrity.

**Inputs:** SCHEMA-2 and SCHEMA-3 DDL with constraints  
**Outputs:** Test execution results, pass/fail report

### Test Cases

**Positive Tests (should succeed):**
1. Insert valid patient record → SUCCESS
2. Insert appointment with valid FK (patient_id exists) → SUCCESS
3. Insert appointment with valid appointment_status → SUCCESS
4. Update appointment with valid data → SUCCESS

**Negative Tests (should fail):**
1. Insert duplicate PK → ERROR 1062 (Duplicate entry)
2. Insert appointment with non-existent patient_id → ERROR 1452 (FK constraint)
3. Insert appointment with invalid status → ERROR 3819 (Check constraint)
4. Delete patient with existing appointments (RESTRICT) → ERROR 1451 (FK child exists)

### Execution Procedure

```sql
-- TEST 1: Primary Key constraint
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary)
  VALUES ('MRN-001', 'John', 'Doe', '1990-01-01', 'M', '555-0000');
INSERT INTO patient (patient_id, mrn, first_name, last_name, dob, gender, phone_primary)
  VALUES (1, 'MRN-002', 'Jane', 'Doe', '1991-01-01', 'F', '555-1111');
-- Expected: Second insert fails (PK duplicate)

-- TEST 2: Foreign Key constraint
INSERT INTO appointment (patient_id, provider_id, clinic_id, appointment_type_id, 
  scheduled_start_time, scheduled_end_time, appointment_status)
  VALUES (999999, 1, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'scheduled');
-- Expected: Fails (patient_id 999999 doesn't exist)

-- TEST 3: Check constraint
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary)
  VALUES ('MRN-003', 'Bob', 'Smith', CURDATE() + INTERVAL 1 DAY, 'M', '555-2222');
-- Expected: Fails (dob is in future)

-- TEST 4: Cascade behavior
INSERT INTO patient VALUES (...);  -- patient_id = 100
INSERT INTO appointment VALUES (..., patient_id = 100, ...);
DELETE FROM patient WHERE patient_id = 100;  -- Should cascade delete appointments
-- Expected: Appointment also deleted
```

**Success Criteria:**
- [ ] All positive tests pass
- [ ] All negative tests fail with expected error codes
- [ ] Cascade/restrict behavior works correctly

---

## QA-2: Latency Budget Validation (2 pts)

**Objective:** Confirm all queries meet p95 latency targets under load.

**Inputs:** PERF-2 benchmark results, latency targets  
**Outputs:** Latency report, pass/fail verdict

### Latency Targets

| Query | Tier | Target p95 | Actual p95 | Pass? |
|---|---|---|---|---|
| Patient appointment lookup | Hot | 5ms | ? | ? |
| Provider daily schedule | Hot | 10ms | ? | ? |
| Clinic queue | Hot | 15ms | ? | ? |
| Patient profile timeline | Medium | 50ms | ? | ? |

### Execution Procedure

```python
import time
import mysql.connector

def benchmark_query(query, iterations=1000, params=None):
    latencies = []
    for _ in range(iterations):
        start = time.time()
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)
    
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    
    return p50, p95, p99

# Run benchmarks
q1_p50, q1_p95, q1_p99 = benchmark_query("SELECT ... FROM appointment WHERE patient_id = ?", 1000, (12345,))

print(f"Query 1 p95: {q1_p95}ms (target: 5ms) {'PASS' if q1_p95 < 5 else 'FAIL'}")
```

**Success Criteria:**
- [ ] Hot Query 1: p95 < 5ms ✅
- [ ] Hot Query 2: p95 < 10ms ✅
- [ ] Hot Query 3: p95 < 15ms ✅
- [ ] Medium Query 4: p95 < 50ms ✅

---

## QA-3: Duplicate Prevention Validation (1 pt)

**Objective:** Validate uniqueness constraints prevent duplicates.

**Inputs:** SCHEMA-3 unique constraints  
**Outputs:** Test execution results

### Test Cases

```sql
-- TEST 1: Duplicate MRN
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary)
  VALUES ('MRN-DUPLICATE', 'John', 'Doe', '1990-01-01', 'M', '555-0000');
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary)
  VALUES ('MRN-DUPLICATE', 'Jane', 'Smith', '1991-01-01', 'F', '555-1111');
-- Expected: ERROR 1062 (Duplicate entry 'MRN-DUPLICATE' for key 'idx_patient_mrn')

-- TEST 2: Duplicate email
INSERT INTO patient (mrn, email, first_name, last_name, dob, gender, phone_primary)
  VALUES ('MRN-1', 'duplicate@example.com', 'John', 'Doe', '1990-01-01', 'M', '555-0000');
INSERT INTO patient (mrn, email, first_name, last_name, dob, gender, phone_primary)
  VALUES ('MRN-2', 'duplicate@example.com', 'Jane', 'Doe', '1991-01-01', 'F', '555-1111');
-- Expected: ERROR 1062

-- TEST 3: Duplicate NPI
INSERT INTO provider (npi, first_name, last_name, specialty_id) VALUES ('123456789', 'Dr.', 'Smith', 1);
INSERT INTO provider (npi, first_name, last_name, specialty_id) VALUES ('123456789', 'Dr.', 'Jones', 2);
-- Expected: ERROR 1062

-- TEST 4: Duplicate coding in appointment
INSERT INTO coding (appointment_id, code_system, code_value, code_description, coding_type)
  VALUES (100, 'ICD10', 'E11.9', 'Type 2 Diabetes', 'diagnosis');
INSERT INTO coding (appointment_id, code_system, code_value, code_description, coding_type)
  VALUES (100, 'ICD10', 'E11.9', 'Type 2 Diabetes without complications', 'diagnosis');
-- Expected: ERROR 1062 (duplicate composite key)

-- TEST 5: NULL handling - multiple NULLs allowed
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary, email)
  VALUES ('MRN-3', 'John', 'Doe', '1990-01-01', 'M', '555-2222', NULL);
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary, email)
  VALUES ('MRN-4', 'Jane', 'Doe', '1991-01-01', 'F', '555-3333', NULL);
-- Expected: SUCCESS (NULLs don't count as duplicates)
```

**Success Criteria:**
- [ ] Duplicate MRN rejected ✅
- [ ] Duplicate email rejected ✅
- [ ] Duplicate NPI rejected ✅
- [ ] Duplicate coding rejected ✅
- [ ] Multiple NULLs allowed ✅

---

## QA-4: Naming/Semantics Review Validation (1 pt)

**Objective:** Validate naming conventions applied consistently.

**Inputs:** GOV-1 naming rules, DDL artifacts  
**Outputs:** Naming audit report

### Audit Checklist

```sql
-- Verify table names (all singular, lowercase)
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'appointment_db' AND TABLE_NAME RLIKE '^[a-z_]+$'
ORDER BY TABLE_NAME;
-- Expected: All 8+ tables follow pattern

-- Verify FK naming (all follow {table}_id pattern)
SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME 
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE CONSTRAINT_SCHEMA = 'appointment_db' AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, COLUMN_NAME;
-- Expected: All FK columns named {referenced_table}_id

-- Verify boolean naming (all use is_* or has_*)
SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'appointment_db' 
  AND COLUMN_TYPE = 'tinyint(1)'  -- MySQL BOOLEAN type
ORDER BY TABLE_NAME, COLUMN_NAME;
-- Expected: All boolean columns start with is_ or has_

-- Verify timestamp naming (all use *_at suffix)
SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'appointment_db'
  AND COLUMN_TYPE IN ('datetime', 'timestamp')
  AND COLUMN_NAME LIKE '%_at' OR COLUMN_NAME LIKE 'timestamp'
ORDER BY TABLE_NAME, COLUMN_NAME;
-- Expected: All timestamps end in _at (created_at, updated_at, submitted_at)

-- Verify index naming (all follow idx_* pattern)
SELECT TABLE_NAME, INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'appointment_db' AND INDEX_NAME != 'PRIMARY'
ORDER BY TABLE_NAME, INDEX_NAME;
-- Expected: All non-PK indexes start with idx_
```

**Success Criteria:**
- [ ] 100% tables singular and lowercase ✅
- [ ] 100% FKs follow {table}_id pattern ✅
- [ ] 100% booleans use is_* or has_* ✅
- [ ] 100% timestamps use *_at suffix ✅
- [ ] 100% indexes follow naming convention ✅

---

## QA-5: Index Effectiveness Validation (2 pts)

**Objective:** Verify retained indexes are used and removed indexes don't regress performance.

**Inputs:** INDEX-2 final index list, PERF-2 query plans  
**Outputs:** Index usage report, regression test results

### Index Usage Verification

```sql
-- Verify hot queries use intended indexes
EXPLAIN FORMAT=JSON
SELECT appointment_id, scheduled_start_time, provider_id
FROM appointment
WHERE patient_id = 12345 AND appointment_status IN ('scheduled', 'confirmed')
ORDER BY scheduled_start_time ASC
LIMIT 10;

-- Expected output shows: "type": "range", "index": "idx_patient_status_time"

-- Verify no full-table scans
SELECT * FROM performance_schema.events_statements_summary_by_digest
WHERE DIGEST_TEXT LIKE '%appointment%' AND DIGEST_TEXT NOT LIKE '%CREATE%'
ORDER BY SUM_TIMER_WAIT DESC;
-- Expected: No queries with "type": "ALL"

-- Collect index usage statistics
SELECT 
  OBJECT_SCHEMA,
  OBJECT_NAME,
  INDEX_NAME,
  COUNT_READ,
  COUNT_WRITE,
  (COUNT_READ / GREATEST(COUNT_WRITE, 1)) as read_write_ratio
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE OBJECT_SCHEMA = 'appointment_db' AND INDEX_NAME != 'PRIMARY'
ORDER BY COUNT_READ DESC;
```

**Regression Testing**

```python
def regression_test():
    """Compare query latencies before/after index changes"""
    
    baseline = {
        'q1_p95': 4.2,  # Before PERF-2 tuning
        'q2_p95': 9.5,
        'q3_p95': 13.8,
        'q4_p95': 48.2
    }
    
    current = benchmark_all_queries()  # Run after INDEX-2 cleanup
    
    # Verify no regressions (allow 10% variance)
    for query_name in baseline:
        old_latency = baseline[query_name]
        new_latency = current[query_name]
        
        # Regression if latency increased by >10%
        if new_latency > old_latency * 1.1:
            print(f"❌ REGRESSION: {query_name} {old_latency}ms → {new_latency}ms")
            return False
        else:
            print(f"✅ OK: {query_name} {old_latency}ms → {new_latency}ms")
    
    return True
```

**Success Criteria:**
- [ ] All hot queries use intended indexes ✅
- [ ] No full-table scans detected ✅
- [ ] Index usage stats show 80%+ read ratio for hot indexes ✅
- [ ] No latency regression (>10% increase) ✅
- [ ] Query plans stable across 3 runs ✅

---

## Execution Summary

**Parallel Execution:**
```
Start Phase 4 (QA): All 5 tests run simultaneously

QA-1 (Integrity):      2 hours   [████████  ]
QA-2 (Latency):        3 hours   [███████████  ]
QA-3 (Duplicates):     1 hour    [██████  ]
QA-4 (Naming):         30 mins   [███  ]
QA-5 (Indexes):        2 hours   [████████  ]

All tests should complete within 3 hours
```

**Success Criteria (All 5 required):**
- [ ] QA-1: 100% pass rate (all constraints working)
- [ ] QA-2: 100% pass rate (all latency targets met)
- [ ] QA-3: 100% pass rate (all duplicates prevented)
- [ ] QA-4: 100% pass rate (all naming consistent)
- [ ] QA-5: 100% pass rate (all indexes effective)

---

## Definition of Done

- [ ] All 5 QA tests completed
- [ ] 100% pass rate on all tests
- [ ] QA report generated and reviewed
- [ ] Ready for production deployment

---

**NEXT:** TASK-104 Complete ✅
