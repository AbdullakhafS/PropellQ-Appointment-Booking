# PERF-1: Representative Dataset and Benchmark Harness

**Task ID:** PERF-1  
**Parent:** TASK-104  
**Category:** Indexing and Query  
**Points:** 6  
**Status:** Planned (after INDEX-1)  
**Created:** 2026-06-22

---

## Objective

Generate realistic test data volumes and create reproducible benchmark suite for performance validation and tuning.

---

## Inputs

- SCHEMA-3 final DDL
- Cardinality estimates (100K patients, 500K appointments, 2M documents)
- Expected query patterns from booking/queue/profile flows
- Latency targets (5-50ms p95)

---

## Outputs

- [ ] SQL data generation script (reproducible, idempotent)
- [ ] Benchmark query suite (5-10 critical queries)
- [ ] Baseline measurements (p50/p95/p99 latencies)
- [ ] Mixed workload benchmark (concurrent read + write)
- [ ] Benchmark documentation and execution playbook

---

## Acceptance Criteria

1. **Test Data Generation:**
   - [ ] 100K patients generated with realistic distributions
   - [ ] 500K appointments distributed across 180-day window
   - [ ] 2M documents distributed across appointments
   - [ ] Clinics, providers, specialties with realistic cardinality
   - [ ] Script is idempotent (can reset and regenerate)

2. **Benchmark Suite:**
   - [ ] 5+ hot-path queries included
   - [ ] Each query runs 100+ iterations
   - [ ] Mix of read + write operations
   - [ ] Sequential and concurrent workload variants

3. **Baseline Metrics:**
   - [ ] p50, p95, p99 latencies captured
   - [ ] Row scans and memory usage recorded
   - [ ] Query plans captured with EXPLAIN ANALYZE

4. **Workload Validation:**
   - [ ] 1000 concurrent read connections sustained
   - [ ] Write throughput measured (inserts/sec)
   - [ ] No timeout failures in baseline

---

## Implementation Details

### Data Generation Script

```sql
-- Generate 100K patients
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary, email, created_at)
SELECT 
  CONCAT('MRN-', LPAD(seq, 7, '0')) as mrn,
  SUBSTRING(MD5(RAND()),1,10) as first_name,
  SUBSTRING(MD5(RAND()),1,15) as last_name,
  DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 20000) DAY) as dob,
  ELT(FLOOR(1 + RAND() * 3), 'M', 'F', 'O') as gender,
  CONCAT('555-', LPAD(FLOOR(RAND() * 10000), 4, '0')) as phone_primary,
  CONCAT('user-', seq, '@example.com') as email,
  DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 365) DAY) as created_at
FROM (SELECT @row := @row + 1 as seq FROM 
  (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t1,
  (SELECT @row:=0) t2 LIMIT 100000) t;

-- Generate 500K appointments
INSERT INTO appointment (patient_id, provider_id, clinic_id, appointment_type_id, 
  scheduled_start_time, scheduled_end_time, appointment_status, created_at)
SELECT 
  FLOOR(RAND() * 100000) + 1 as patient_id,
  FLOOR(RAND() * 50) + 1 as provider_id,
  FLOOR(RAND() * 5) + 1 as clinic_id,
  FLOOR(RAND() * 20) + 1 as appointment_type_id,
  DATE_ADD(CURDATE(), INTERVAL FLOOR(RAND() * 180) DAY) as scheduled_start_time,
  DATE_ADD(CURDATE(), INTERVAL FLOOR(RAND() * 180) DAY) as scheduled_end_time,
  ELT(FLOOR(1 + RAND() * 5), 'scheduled', 'confirmed', 'completed', 'cancelled', 'no-show') as appointment_status,
  DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 365) DAY) as created_at
FROM (SELECT 1 FROM 
  (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t1,
  (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t2 LIMIT 500000) t;

-- Generate 2M documents
INSERT INTO document (patient_id, appointment_id, document_type, file_path, upload_timestamp)
SELECT 
  FLOOR(RAND() * 100000) + 1 as patient_id,
  FLOOR(RAND() * 500000) + 1 as appointment_id,
  ELT(FLOOR(1 + RAND() * 5), 'medical_record', 'lab_result', 'imaging', 'form', 'note') as document_type,
  CONCAT('/documents/', UUID(), '.pdf') as file_path,
  DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 365) DAY) as upload_timestamp
FROM (SELECT 1 FROM 
  (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t1,
  (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t2,
  (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t3 LIMIT 2000000) t;
```

### Benchmark Query Suite

**Benchmark 1: Patient Appointment Lookup**
```sql
SELECT appointment_id, scheduled_start_time, provider_id, appointment_status
FROM appointment
WHERE patient_id = ? AND appointment_status IN ('scheduled', 'confirmed')
ORDER BY scheduled_start_time ASC
LIMIT 10;
```

**Benchmark 2: Provider Daily Schedule**
```sql
SELECT appointment_id, scheduled_start_time, patient_id
FROM appointment
WHERE provider_id = ? AND DATE(scheduled_start_time) = ?
ORDER BY scheduled_start_time ASC;
```

**Benchmark 3: Clinic Queue**
```sql
SELECT appointment_id, patient_id, scheduled_start_time
FROM appointment
WHERE clinic_id = ? AND appointment_status IN ('in-progress', 'confirmed')
ORDER BY scheduled_start_time ASC;
```

**Benchmark 4: Patient Profile Timeline**
```sql
SELECT a.appointment_id, a.scheduled_start_time, a.appointment_status,
       COUNT(d.document_id) as document_count
FROM appointment a
LEFT JOIN document d ON a.appointment_id = d.appointment_id
WHERE a.patient_id = ?
GROUP BY a.appointment_id
ORDER BY a.scheduled_start_time DESC
LIMIT 50;
```

### Execution Playbook

1. **Generate Test Data:** Run data generation script (15-20 min runtime)
2. **Run ANALYZE TABLE:** Update statistics for all tables
3. **Execute Baselines:** Run each query 100+ times, capture latencies
4. **Record Query Plans:** `EXPLAIN ANALYZE` before any optimization
5. **Mixed Workload:** Concurrent readers (1000 connections) + concurrent writers

---

## Success Metrics

- [ ] Test data generation completes in <20 minutes
- [ ] Baseline p95 latencies captured for all queries
- [ ] Query plans captured with EXPLAIN ANALYZE
- [ ] 1000 concurrent connections sustained without timeout
- [ ] Reproducible results (±10% variance on repeated runs)

---

## Definition of Done

- [ ] Data generation script complete and tested
- [ ] Benchmark queries running 100+ iterations
- [ ] Baseline metrics documented
- [ ] Query plans captured
- [ ] Ready for PERF-2 tuning phase

---

## Next Task

→ PERF-2: Query Plan and Latency Tuning
