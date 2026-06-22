# DOC-2: DDL and Migration Documentation

**Task ID:** DOC-2  
**Parent:** TASK-104  
**Category:** Governance and Documentation  
**Points:** 2  
**Status:** Planned (after GOV-2 approval)  
**Created:** 2026-06-22

---

## Objective

Document final DDL, deployment procedures, and migration strategy for production deployment.

---

## Inputs

- GOV-2 approval notes
- PERF-2 final tuned schema
- INDEX-2 final index list
- Deployment environment specs

---

## Outputs

- [ ] Approved final DDL (version-controlled)
- [ ] Forward migration script (V001__init.sql)
- [ ] Rollback migration script (rollback_001.sql)
- [ ] Deployment runbook
- [ ] Growth/partitioning strategy

---

## Acceptance Criteria

1. **DDL Artifact:**
   - [ ] Complete CREATE TABLE statements for all 10 tables
   - [ ] All PRIMARY, FOREIGN, UNIQUE, CHECK constraints
   - [ ] All 13-15 indexes
   - [ ] Comments explaining complex constraints
   - [ ] Version number and date in header

2. **Migration Scripts:**
   - [ ] Forward script: All CREATE TABLE/INDEX statements
   - [ ] Rollback script: DROP TABLE/INDEX in reverse order
   - [ ] Transaction safety: All wrapped in transactions
   - [ ] Tested on staging environment

3. **Deployment Runbook:**
   - [ ] Pre-deployment checks (backups, downtime window)
   - [ ] Migration execution steps
   - [ ] Post-deployment validation
   - [ ] Rollback procedure
   - [ ] Estimated runtime (typically 2-5 minutes)

4. **Growth Strategy:**
   - [ ] Partitioning triggers documented
   - [ ] Index maintenance schedule
   - [ ] Archive/retention policies

---

## Implementation Details

### Final DDL Structure

**File:** `schema_v001.sql`
```sql
-- ============================================================================
-- Appointment Booking System - Production Schema v1.0
-- Created: 2026-06-22
-- Author: Database Architecture Team
-- Description: Core operational schema for patient bookings, clinical data
-- ============================================================================

USE appointment_db;

-- ============================================================================
-- PATIENT - Core patient identity and demographics
-- ============================================================================
CREATE TABLE patient (
  patient_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  mrn VARCHAR(50) NOT NULL,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  dob DATE NOT NULL,
  gender CHAR(1) NOT NULL DEFAULT 'X',
  email VARCHAR(255),
  phone_primary VARCHAR(20) NOT NULL,
  phone_secondary VARCHAR(20),
  address_street VARCHAR(255),
  address_city VARCHAR(100),
  address_state CHAR(2),
  address_zip VARCHAR(10),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  UNIQUE KEY idx_patient_mrn (mrn),
  UNIQUE KEY idx_patient_email (email),
  KEY idx_patient_phone (phone_primary),
  
  CHECK (gender IN ('M', 'F', 'O', 'X')),
  CHECK (dob < CURDATE())
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- PROVIDER - Clinician/staff identity
-- ============================================================================
CREATE TABLE provider (
  provider_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  npi VARCHAR(20) NOT NULL UNIQUE,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  specialty_id BIGINT NOT NULL,
  license_number VARCHAR(50),
  email VARCHAR(255),
  phone VARCHAR(20),
  is_active BOOLEAN DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  UNIQUE KEY idx_provider_npi (npi),
  KEY idx_provider_specialty (specialty_id),
  
  FOREIGN KEY (specialty_id) REFERENCES specialty(specialty_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ... (additional tables follow same pattern)
```

### Migration Script Template

**File:** `V001__init.sql` (Flyway naming convention)
```sql
-- Flyway Migration: V001__init.sql
-- Version: 1.0
-- Timestamp: 2026-06-22
-- Description: Initial schema with all tables, constraints, indexes

BEGIN;

-- Create all tables (in order respecting FK dependencies)
-- 1. Reference tables first (SPECIALTY, CLINIC, APPOINTMENT_TYPE)
-- 2. Master tables next (PATIENT, PROVIDER)
-- 3. Transactional tables last (APPOINTMENT, INTAKE, DOCUMENT, CODING)
-- 4. Audit table (AUDIT_LOG)

CREATE TABLE specialty (...);
CREATE TABLE clinic (...);
CREATE TABLE appointment_type (...);
-- ... rest of tables

-- Create all indexes
CREATE INDEX idx_patient_status_time ON appointment (patient_id, appointment_status, scheduled_start_time);
-- ... rest of indexes

COMMIT;
```

### Deployment Runbook

**Pre-Deployment:**
1. Backup production database (full backup + binary logs)
2. Schedule maintenance window (2-5 minutes downtime, off-peak hours)
3. Notify stakeholders: appointment booking service will be unavailable
4. Verify rollback script tested on staging

**Deployment Steps:**
1. Stop appointment service (or put in read-only mode)
2. Execute migration script: `mysql appointment_db < V001__init.sql`
3. Verify: Check that all tables, indexes created
4. Resume service

**Post-Deployment Validation:**
```sql
-- Verify all tables exist
SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'appointment_db';  -- Should be 10

-- Verify all indexes exist
SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
WHERE TABLE_SCHEMA = 'appointment_db' AND INDEX_NAME != 'PRIMARY';  -- Should be 13-15

-- Verify constraints
SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
WHERE CONSTRAINT_SCHEMA = 'appointment_db' AND CONSTRAINT_TYPE = 'FOREIGN KEY';  -- Should be 15+

-- Verify data integrity
SELECT COUNT(*) FROM appointment;  -- Should be > 0 if data migrated
```

**Rollback Procedure:**
```sql
-- If deployment fails, execute rollback script
mysql appointment_db < rollback_001.sql

-- This will:
-- 1. Drop all tables in reverse dependency order
-- 2. Return to previous schema state
-- 3. Restore database from pre-deployment backup if needed
```

### Growth Strategy

**Partitioning Plan**
```
- APPOINTMENT table: Partition by RANGE (YEAR(scheduled_start_time))
  - Yearly partitions for retention, archive
  - Create new partition quarterly for next year
  - Drop old partitions after 3+ year retention

- AUDIT_LOG table: Partition by RANGE (MONTH(created_at))
  - Monthly partitions for easier rotation
  - Archive to S3 after 1 year (prod), 90 days (dev)

- Trigger: Automatic partition creation when needed
```

**Index Maintenance Schedule**
```
- Daily: ANALYZE TABLE to update statistics
- Weekly: Check for unused indexes, slow queries
- Monthly: Review index fragmentation, consider REBUILD
- Quarterly: Archive old audit_log data
```

---

## Success Metrics

- [ ] DDL complete and version-controlled
- [ ] Migration scripts tested on staging
- [ ] Rollback procedure documented and tested
- [ ] Deployment runbook clear and validated
- [ ] Estimated runtime < 5 minutes

---

## Definition of Done

- [ ] Final DDL committed to version control
- [ ] Deployment runbook peer-reviewed
- [ ] Migration tested end-to-end on staging
- [ ] Rollback procedure verified
- [ ] Ready for GOV-2 approval

---

## Next Task

→ GOV-2: Architecture Review and Compatibility Notes
