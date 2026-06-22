# INDEX-2: Index Rationalization and Cleanup

**Task ID:** INDEX-2  
**Parent:** TASK-104  
**Category:** Indexing and Query  
**Points:** 3  
**Status:** Planned (parallel with PERF-2)  
**Created:** 2026-06-22

---

## Objective

Remove overlapping and unused indexes, finalize approved index list, and establish monitoring for index effectiveness.

---

## Inputs

- PERF-2 tuning results
- Query plans showing actual index usage
- INDEX-1 candidates

---

## Outputs

- [ ] Final approved index list (13-15 indexes)
- [ ] Unused index detection procedure
- [ ] Index overlap analysis
- [ ] PERFORMANCE_SCHEMA monitoring queries
- [ ] Index maintenance plan

---

## Acceptance Criteria

1. **Index Rationalization:**
   - [ ] Mandatory hot-path indexes retained
   - [ ] Overlapping single-column indexes removed if compound exists
   - [ ] Unused indexes dropped
   - [ ] Final count: 13-15 production indexes

2. **Unused Detection:**
   - [ ] Query provided to find unused indexes
   - [ ] Monitoring schedule established (daily/weekly)

3. **Overlap Analysis:**
   - [ ] Single-column indexes vs. prefix of compound identified
   - [ ] Redundant indexes documented and removed

4. **Monitoring Strategy:**
   - [ ] PERFORMANCE_SCHEMA queries for index usage
   - [ ] Slow query log configuration

---

## Implementation Details

### Index Rationalization Process

**Step 1: Collect Index Usage Stats**
```sql
-- Get index usage statistics
SELECT 
  OBJECT_SCHEMA,
  OBJECT_NAME,
  INDEX_NAME,
  COUNT_READ,
  COUNT_WRITE,
  COUNT_DELETE,
  COUNT_INSERT,
  (COUNT_READ + COUNT_WRITE + COUNT_DELETE + COUNT_INSERT) as total_ops
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE OBJECT_SCHEMA = 'appointment_db'
ORDER BY total_ops DESC;
```

**Step 2: Identify Unused Indexes**
```sql
-- Find indexes with zero reads in last 24 hours
SELECT 
  OBJECT_SCHEMA,
  OBJECT_NAME,
  INDEX_NAME
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE OBJECT_SCHEMA = 'appointment_db'
  AND COUNT_READ = 0
  AND INDEX_NAME != 'PRIMARY'
ORDER BY OBJECT_NAME;
```

**Step 3: Detect Overlapping Indexes**
```sql
-- Example: If we have idx_patient_email and idx_patient_email_status,
-- the first is covered by the second (leftmost prefix rule)
-- Solution: Drop idx_patient_email, keep idx_patient_email_status
```

**Step 4: Drop Unused/Overlapping Indexes**
```sql
-- Example removals (if confirmed unused)
DROP INDEX idx_old_unused_index ON appointment;
DROP INDEX idx_redundant_prefix ON patient;
```

### Approved Index List (Final)

| Index Name | Table | Columns | Type | Rationale |
|---|---|---|---|---|
| idx_patient_status_time | appointment | (patient_id, appointment_status, scheduled_start_time) | Hot | Patient appointment lookup |
| idx_provider_time | appointment | (provider_id, scheduled_start_time) | Hot | Provider schedule |
| idx_clinic_time | appointment | (clinic_id, scheduled_start_time, appointment_status) | Hot | Clinic queue |
| idx_patient_mrn | patient | (mrn) | Hot | Emergency lookup |
| idx_patient_email | patient | (email) | Hot | Account login |
| idx_patient_phone | patient | (phone_primary) | Medium | Contact search |
| idx_intake_status | intake | (patient_id, status, submitted_at DESC) | Medium | Pending intake |
| idx_document_patient | document | (patient_id) | Medium | Patient documents |
| idx_document_type | document | (document_type) | Medium | Document filtering |
| idx_coding_appointment | coding | (appointment_id) | Medium | Codes per appointment |
| idx_provider_npi | provider | (npi) | Hot | NPI lookup |
| idx_appointment_status | appointment | (appointment_status, scheduled_start_time) | Optional | Analytics |
| idx_audit_entity | audit_log | (entity_type, entity_id, created_at DESC) | Low | Compliance |

### Monitoring Plan

**Daily Index Health Check:**
```sql
-- Run daily to monitor index effectiveness
SELECT 
  OBJECT_SCHEMA,
  OBJECT_NAME,
  INDEX_NAME,
  COUNT_READ,
  COUNT_WRITE,
  COUNT_READ / GREATEST(COUNT_WRITE, 1) as read_write_ratio
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE OBJECT_SCHEMA = 'appointment_db'
  AND COUNT_READ > 0
ORDER BY COUNT_READ DESC;
```

**Slow Query Detection:**
```sql
-- Configure slow query log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.010; -- 10ms threshold
SET GLOBAL log_queries_not_using_indexes = 'ON';

-- Review slow queries
SELECT * FROM mysql.slow_log
WHERE start_time > DATE_SUB(NOW(), INTERVAL 1 DAY)
ORDER BY query_time DESC;
```

---

## Success Metrics

- [ ] 13-15 approved indexes in final list
- [ ] 0 unused indexes retained
- [ ] 0 overlapping indexes retained
- [ ] Monitoring queries established
- [ ] Index maintenance runbook created

---

## Definition of Done

- [ ] Unused/overlapping indexes dropped
- [ ] Final index list documented
- [ ] Monitoring strategy in place
- [ ] Ready for DOC-1 and DOC-2

---

## Next Task

→ DOC-1: Data Model Glossary and ERD Updates
