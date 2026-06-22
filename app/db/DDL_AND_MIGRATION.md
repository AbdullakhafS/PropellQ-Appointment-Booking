# DDL and Migration Documentation

**Date:** 2026-06-22  
**Version:** 1.0  
**Status:** Production Deployment Guide  

---

## 1. Overview

This document provides:
1. Complete DDL artifacts for production deployment
2. Migration strategy for upgrading from current schema
3. Rollback procedures for incident recovery
4. Operational deployment notes for various environments
5. Growth and scaling guidance

---

## 2. DDL Artifacts

### 2.1 Complete Production Schema (schema_v1_production.sql)

The complete production schema is maintained in: [`schema_v1_production.sql`](schema_v1_production.sql)

**Key Features:**
- 16 core tables (specialties, providers, appointments, patient_profiles, etc.)
- 50+ indexes optimized for hot-path queries
- Explicit PK/FK/Check/Unique constraints for data integrity
- Soft-delete pattern (is_active) for archival support
- Comprehensive inline documentation

**Table Count:** 16  
**Index Count:** 30+  
**Constraint Count:** 50+  

---

## 3. Migration Strategy

### 3.1 Migration Scenario: Current → Production Schema

**Current State:**
- Legacy schema_v0.sql with basic tables and minimal constraints

**Target State:**
- schema_v1_production.sql with enhanced constraints and indexes

**Migration Type:** **In-Place Upgrade with Compatibility Layer**

---

### 3.2 Migration Phases

#### Phase 1: Validation and Backup (Pre-Migration)

```bash
# 1. Verify current schema version
SELECT * FROM pragma_user_version;
# Expected output: 0 (or current version)

# 2. Database integrity check
PRAGMA integrity_check;
# Expected: ok

# 3. Backup production database
cp appointment_booking.db appointment_booking.db.backup.$(date +%Y%m%d_%H%M%S)

# 4. Validate backup
sqlite3 appointment_booking.db.backup.YYYYMMDD_HHMMSS ".tables"

# 5. Record baseline metrics
SELECT COUNT(*) as total_appointments FROM appointments;
SELECT COUNT(*) as total_providers FROM providers;
SELECT COUNT(*) as total_patients FROM patient_profiles;
```

**Exit Criteria:**
- [ ] Backup created and verified
- [ ] Database integrity check passes
- [ ] Baseline row counts recorded

---

#### Phase 2: Add New Tables and Constraints (Safe Operations)

```sql
-- This phase adds missing tables without modifying existing schema
-- Safe for read traffic during deployment

-- 1. Enable foreign key enforcement
PRAGMA foreign_keys = ON;

-- 2. Add any new tables introduced in v1
--    (Only if not already present; schema_v1 has all current tables)
--    Skipped if all tables exist

-- 3. Verify all tables exist
SELECT COUNT(*) FROM sqlite_master WHERE type='table' 
       AND name IN ('specialties', 'providers', 'appointments', ...);
```

**Rollback (if needed):**
```sql
-- Phase 2 is safe to rollback (no modifications to existing data)
-- Simply do not apply subsequent phases
```

---

#### Phase 3: Add Missing Indexes (Minimal Performance Impact)

```sql
-- Add indexes from schema_v1_production.sql
-- These are applied incrementally to minimize lock contention

-- 1. Pause background jobs to reduce write load
-- 2. Create each index in sequence with COMMIT between each
-- 3. Monitor disk space during index creation

CREATE INDEX IF NOT EXISTS idx_appointments_specialty_date
    ON appointments (specialty_id, appointment_date, start_time, id);
COMMIT;

CREATE INDEX IF NOT EXISTS idx_appointments_status_date
    ON appointments (status, appointment_date, start_time, id);
COMMIT;

-- ... (continue for all indexes)

-- 4. Verify all indexes created
SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';
```

**Performance Impact:**
- Write latency increase: ~5-10% per index created
- Read latency improvement: ~50-70% for indexed queries
- Storage increase: ~150 MB per 1M appointments
- Duration: 2-4 hours depending on data size

**Rollback:**
```sql
-- Drop indexes if needed (fast operation)
DROP INDEX IF EXISTS idx_appointments_specialty_date;
-- Repeat for each index

-- Original queries will still work (slower, using table scans)
```

---

#### Phase 4: Validate Constraints and Consistency

```sql
-- 1. Verify referential integrity (FK constraints)
PRAGMA foreign_key_check;
# Expected: (no rows = success)

-- 2. Verify unique constraints
SELECT email, COUNT(*) as count FROM patient_profiles GROUP BY email HAVING count > 1;
# Expected: (no rows = all emails unique)

-- 3. Verify check constraints by sampling
SELECT COUNT(*) FROM appointments WHERE status NOT IN ('available', 'booked', 'cancelled');
# Expected: 0

-- 4. Sample validation (spot-check)
SELECT COUNT(*) FROM appointments WHERE provider_id IS NULL;
# Expected: 0 (all appointments have provider)

-- 5. Update pragma_user_version to signal completion
PRAGMA user_version = 1;
```

**Exit Criteria:**
- [ ] Foreign key check passes
- [ ] Unique constraint check passes
- [ ] Check constraints pass
- [ ] pragma_user_version updated to 1

---

#### Phase 5: Post-Migration Validation

```sql
-- 1. Run ANALYZE to update query planner statistics
ANALYZE;

-- 2. Test representative queries from QUERY_PLAN_ANALYSIS.md
SELECT * FROM appointments 
WHERE status = 'available' 
  AND specialty_id = 1 
  AND appointment_date = '2026-07-15'
ORDER BY start_time LIMIT 20;

-- 3. Verify benchmark latencies (compare to baseline)
-- Run benchmark.py --mode benchmark if test database available

-- 4. Monitor application error rates (1 hour post-migration)
-- Alert if error rate increases > 2%
```

---

### 3.3 Rollback Procedure (If Migration Fails)

**Scenario:** Migration detected critical issue; rollback to pre-migration state.

**Steps:**

1. **Stop application servers** (prevent new connections)
   ```bash
   systemctl stop app-server
   ```

2. **Restore from backup**
   ```bash
   cp appointment_booking.db.backup.YYYYMMDD_HHMMSS appointment_booking.db
   ```

3. **Verify restoration**
   ```sql
   PRAGMA integrity_check;
   SELECT COUNT(*) FROM appointments;
   # Should match baseline from Phase 1
   ```

4. **Restart application**
   ```bash
   systemctl start app-server
   ```

5. **Monitor for 5 minutes** (error logs, latency metrics)

6. **Post-mortem:**
   - [ ] Identify root cause of migration failure
   - [ ] Update migration script or schema
   - [ ] Plan corrective action with architecture review
   - [ ] Re-attempt migration with fixes

**RTO (Recovery Time Objective):** < 15 minutes  
**RPO (Recovery Point Objective):** 0 (no data loss; backup restores to pre-migration state)

---

## 4. Deployment Strategies for Different Environments

### 4.1 Development Environment

**Objective:** Rapid iteration and testing; data loss acceptable

```bash
# Full schema reset
rm appointment_booking.db
python benchmark.py --mode generate  # Generate fresh test data
python benchmark.py --mode benchmark # Validate indexes
```

**Frequency:** Daily or per-feature  
**Risk:** Low (isolated; no production impact)

---

### 4.2 Staging Environment

**Objective:** Full UAT with production-like data and load

```bash
# 1. Backup production database
pg_dump appointment_booking.db > staging.sql

# 2. Apply to staging
sqlite3 staging_db.db < staging.sql

# 3. Run migration (schema_v1)
sqlite3 staging_db.db < schema_v1_production.sql

# 4. Validate
python benchmark.py --mode benchmark

# 5. Load testing (simulate 24-hour workload)
# ... (run load test suite)

# 6. Manual QA (2-4 hours)
# - Test all critical workflows
# - Verify data integrity
# - Check performance metrics
```

**Duration:** 4-6 hours  
**Frequency:** 1x per sprint (or before major deployment)  
**Risk:** Medium (staging data; not production)

---

### 4.3 Production Deployment

**Objective:** Zero-downtime deployment; minimal user impact

**Deployment Window:** Off-peak (e.g., 2 AM - 4 AM in target timezone)

```bash
# Deployment checklist
- [ ] All testing passed in staging
- [ ] Runbook review complete
- [ ] Oncall engineer assigned
- [ ] Rollback procedure tested
- [ ] Customer communication (if applicable)

# 1. Pre-deployment: Health check
curl https://api.propellq.com/health
# Expected: 200 OK, system_status: "healthy"

# 2. Phase 1-3: Backup and migration (2 hours)
# See Phase 1-3 above

# 4. Phase 4-5: Validation (30 minutes)
# See Phase 4-5 above

# 5. Post-deployment: Monitoring (1 hour minimum)
# - Error rate: should remain < 0.1%
# - Latency p95: should improve or stay flat
# - Index utilization: confirm indexes used by queries
# - Alert if any metric deviates > 5%

# 6. Gradual traffic ramp
# - Ramp to 10% of normal traffic (5 min)
# - Ramp to 50% of normal traffic (5 min)
# - Ramp to 100% of normal traffic (5 min)
# - Monitor for 15 minutes
```

**Success Criteria:**
- [ ] No deployment errors
- [ ] Error rate remains < 0.1%
- [ ] Latency p95 within ±5% of baseline
- [ ] All indexes actively used by queries
- [ ] No customer-facing issues reported

**Failure Triggers for Rollback:**
- Error rate exceeds 2%
- Latency p95 increases > 50%
- Database integrity check fails
- Queries show unexpected behavior

---

## 5. Operational Guidance

### 5.1 Maintenance Schedule

| Task | Frequency | Duration | Risk |
|---|---|---|---|
| ANALYZE (update statistics) | Weekly | 5 min | Low |
| REINDEX | Monthly | 10 min | Low |
| Backup | Daily (automated) | — | Low |
| Integrity check | Weekly | 5 min | Low |
| Growth monitoring | Weekly | 5 min | Low |

---

### 5.2 Growth and Scaling Guidance

#### Current Scale (Baseline)
- 1,000,000 appointments
- 100,000 providers
- 50,000 patient profiles
- Database size: ~500 MB (with indexes)

#### Growth Triggers

**At 5M Appointments (5x scale):**
- Index size: ~750 MB
- Action: Monitor disk space; consider partitioning by date
- New indexes: Add time-series aggregation tables for dashboard

**At 10M Appointments (10x scale):**
- Recommend partitioning by appointment_date (monthly partitions)
- Archive old appointments to separate table (> 2 years old)
- Scaling architecture: Consider sharding by geography or provider cluster

**At 50M+ Appointments (50x+ scale):**
- Migrate to distributed database (PostgreSQL sharding or multi-node cluster)
- Implement read replicas for analytics
- Consider event streaming (Kafka) for real-time syncing

---

### 5.3 Monitoring and Alerting

**Metrics to Monitor:**

```sql
-- Daily health check query
SELECT 
    (SELECT COUNT(*) FROM appointments) as appointment_count,
    (SELECT COUNT(*) FROM patient_profiles) as patient_count,
    (SELECT COUNT(*) FROM appointment_reservations WHERE status='active') as active_reservations,
    (SELECT COUNT(*) FROM calendar_sync_queue WHERE status='pending') as pending_syncs,
    (SELECT COUNT(*) FROM manual_review_queue WHERE status='open') as open_reviews,
    (SELECT CAST((page_count * page_size)/1024/1024 as INT) FROM pragma_page_count(), pragma_page_size()) as db_size_mb
;
```

**Alerting Thresholds:**
- DB size exceeds 2 GB: Investigate growth; plan archival
- Pending syncs > 10,000: Escalation; check sync worker health
- Open reviews > 100: Customer impact; prioritize resolution
- Query p95 latency > 200ms: Performance regression; check indexes

---

## 6. Version Management

### 6.1 Schema Versioning

**Versioning Scheme:** `v{major}.{minor}.{patch}`

**Current Version:** v1.0.0 (Production Release)

**Upgrade Path:**
- v0.x → v1.0.0: See Migration Strategy (Section 3)
- v1.0.0 → v1.1.0: Additive changes only (new tables/columns, no existing changes)
- v1.1.0 → v2.0.0: Major architectural changes (may require downtime)

### 6.2 Change Log

| Version | Date | Changes | Migration Type | Risk |
|---|---|---|---|---|
| 0.1.0 | 2026-01-15 | Initial schema | — | — |
| 0.2.0 | 2026-02-01 | Added calendar_sync_queue | Additive | Low |
| 0.3.0 | 2026-03-15 | Added manual_review_queue | Additive | Low |
| 1.0.0 | 2026-06-22 | Enhanced constraints, indexes, documentation | In-place upgrade | Medium |

---

## 7. Data Archival Strategy

### 7.1 Retention Policy

| Table | Retention Period | Archival Strategy |
|---|---|---|
| appointments | 3 years | Move to archive_appointments table |
| reminder_log | 1 year | Move to archive_reminder_log table |
| booking_events | 2 years | Move to archive_booking_events table |
| calendar_sync_audit | 2 years | Move to archive_calendar_sync_audit table |
| confirmation_deliveries | 1 year | Delete (email not needed for compliance) |

### 7.2 Archival Process

```sql
-- Monthly archival job (run at end of month)
BEGIN TRANSACTION;

-- Move old appointment records to archive table
INSERT INTO archive_appointments 
SELECT * FROM appointments 
WHERE created_at < date('now', '-' || (SELECT value FROM config WHERE key='retention_days') || ' days')
  AND status IN ('cancelled')  -- Only archive cancelled/completed appointments

-- Delete from active table
DELETE FROM appointments 
WHERE id IN (SELECT id FROM archive_appointments WHERE created_at < ...);

COMMIT;
```

---

## 8. Troubleshooting Guide

### Issue: Migration Fails with FK Constraint Error

**Symptom:** "FOREIGN KEY constraint failed" during Phase 4

**Root Cause:** Orphaned records exist (e.g., appointments.provider_id referencing non-existent provider)

**Resolution:**
```sql
-- Find orphaned records
SELECT * FROM appointments WHERE provider_id NOT IN (SELECT id FROM providers);

-- Option 1: Delete orphaned records
DELETE FROM appointments WHERE provider_id NOT IN (SELECT id FROM providers);

-- Option 2: Repair by updating provider_id
UPDATE appointments SET provider_id = 1 WHERE provider_id NOT IN (SELECT id FROM providers);

-- Re-run migration Phase 4
```

---

### Issue: Slow Query After Migration

**Symptom:** Query latency increased; p95 > 150ms

**Root Cause:** Index not being used; query planner needs updated statistics

**Resolution:**
```sql
-- Run ANALYZE to update statistics
ANALYZE;

-- Check query plan
EXPLAIN QUERY PLAN SELECT ... (your slow query);

-- If still showing SCAN instead of SEARCH, check:
-- 1. Index exists: SELECT * FROM sqlite_master WHERE type='index' AND name='idx_...';
-- 2. Index column order matches query predicates
-- 3. Re-create index if needed: DROP INDEX idx_...; CREATE INDEX ... ;
```

---

### Issue: Database Size Exceeds Disk Quota

**Symptom:** "Disk I/O error" or "Out of space" errors

**Root Cause:** Database and indexes have grown; disk space exhausted

**Resolution:**
```bash
# 1. Check disk space
df -h /var/data/

# 2. Archive old data (see Section 7)
sqlite3 appointment_booking.db < archive_job.sql

# 3. Vacuum database to reclaim space
sqlite3 appointment_booking.db "VACUUM;"

# 4. Monitor with: SELECT COUNT(*) FROM appointments WHERE created_at > date('now', '-90 days');
```

---

## 9. Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-22 | AI Assistant | Initial DDL and migration documentation; 5-phase migration strategy; rollback procedures; growth guidance |

