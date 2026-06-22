# GOV-1: Naming and Semantic Standardization

**Task ID:** GOV-1  
**Parent:** TASK-104  
**Category:** Governance and Documentation  
**Points:** 3  
**Status:** Planned (parallel with INDEX-1)  
**Created:** 2026-06-22

---

## Objective

Enforce consistent naming conventions and semantic patterns across all schema objects.

---

## Inputs

- SCHEMA-3 DDL
- Project SQL standards
- Index candidates from INDEX-1

---

## Outputs

- [ ] Naming conventions document
- [ ] Semantic patterns guide
- [ ] Schema object audit report
- [ ] Correction recommendations

---

## Acceptance Criteria

1. **Table Naming:**
   - [ ] All tables singular: `patient`, `appointment`, not `patients`
   - [ ] All lowercase, snake_case
   - [ ] No abbreviations (use `appointment_type`, not `apt_type`)

2. **Column Naming:**
   - [ ] All lowercase, snake_case
   - [ ] Foreign keys: `{referenced_table}_id` (e.g., `patient_id`, `provider_id`)
   - [ ] Boolean: `is_*` or `has_*` prefix (e.g., `is_confirmed`, `has_document`)
   - [ ] Timestamps: `*_at` suffix (e.g., `created_at`, `updated_at`, `submitted_at`)
   - [ ] Status: `*_status` suffix (e.g., `appointment_status`)

3. **Index Naming:**
   - [ ] Unique index: `idx_{table}_{columns}` (e.g., `idx_patient_mrn`, `idx_appointment_status_time`)
   - [ ] Primary key: `PRIMARY`
   - [ ] Foreign key: Implicit from constraint name

4. **Semantic Consistency:**
   - [ ] Enum values consistent (e.g., use 'scheduled', 'confirmed', not 'pending', 'confirmed')
   - [ ] Data types consistent (dates as DATE, timestamps as DATETIME, durations as INT/TIME)

---

## Implementation Details

### Naming Standards

**Table Names**
```sql
-- Good
patient, appointment, provider, clinic, appointment_type, specialty, intake, document, coding, audit_log

-- Bad
patients, Patient, APPOINTMENT, apt, appt_typ, doc, clinical_coding
```

**Column Names**
```sql
-- Foreign Keys
patient_id, provider_id, clinic_id, appointment_type_id  -- NOT patientId, patient_fk

-- Booleans
is_confirmed, is_active, has_document, has_intake  -- NOT confirmed, active, document_flag

-- Timestamps
created_at, updated_at, submitted_at, scheduled_start_time, scheduled_end_time  -- NOT create_date, update_ts, submittedTime

-- Statuses
appointment_status, document_status, intake_status  -- NOT state, condition, phase
```

**Index Names**
```sql
-- Hot path indexes
idx_patient_status_time
idx_provider_time
idx_clinic_time

-- Identity lookups
idx_patient_mrn
idx_patient_email
idx_provider_npi

-- Not recommended
idx_1, idx_patient_appointment_lookup, idx_appt_status
```

### Semantic Patterns

**Status Enums**
```sql
-- Appointments: scheduled, confirmed, in-progress, completed, cancelled, no-show
-- Intakes: pending, submitted, completed, cancelled
-- Documents: uploaded, processing, ready, error
-- Patients: active, inactive, archived

-- NOT: pending, approved, rejected, done, fail (inconsistent)
```

**Data Types**
```sql
-- Dates: DATE (for birthdates, appointment date only)
-- Timestamps: DATETIME (for audit trail, exact moment)
-- Durations: INT MINUTES or TIME (for appointment length)

-- NOT: VARCHAR for dates, mixing DATE/DATETIME without reason
```

### Audit Checklist

```sql
-- Run these queries to verify compliance

-- 1. Check table names (all singular, lowercase)
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'appointment_db'
ORDER BY TABLE_NAME;

-- 2. Check for non-snake_case columns
SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'appointment_db'
  AND COLUMN_NAME RLIKE '[A-Z]'  -- Has uppercase
ORDER BY TABLE_NAME, COLUMN_NAME;

-- 3. Check FK naming
SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'appointment_db'
ORDER BY CONSTRAINT_NAME;

-- 4. Check index naming
SELECT TABLE_NAME, INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'appointment_db'
  AND INDEX_NAME != 'PRIMARY'
ORDER BY TABLE_NAME, INDEX_NAME;
```

---

## Success Metrics

- [ ] 100% table names singular and lowercase
- [ ] 100% columns snake_case
- [ ] 100% foreign keys follow `{table}_id` pattern
- [ ] 100% booleans use `is_*` or `has_*`
- [ ] 100% timestamps use `*_at` suffix
- [ ] 100% statuses use `*_status` suffix
- [ ] 100% indexes follow naming convention

---

## Definition of Done

- [ ] Naming standards document published
- [ ] Schema audit completed
- [ ] All corrections applied
- [ ] Peer-reviewed and approved
- [ ] Ready for GOV-2

---

## Next Task

→ GOV-2: Architecture Review and Compatibility Notes
