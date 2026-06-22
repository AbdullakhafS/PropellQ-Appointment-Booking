# SCHEMA-3: Uniqueness and Duplicate Prevention

**Task ID:** SCHEMA-3  
**Parent:** TASK-104  
**Category:** Data Modeling  
**Points:** 4  
**Status:** Planned (after SCHEMA-2)  
**Created:** 2026-06-22

---

## Objective

Add UNIQUE constraints to prevent duplicate records in identity fields and composite uniqueness scenarios.

---

## Inputs

- SCHEMA-2: DDL with PKs and FKs
- Duplicate-risk entity analysis
- Business rules for uniqueness scopes

---

## Outputs

- [ ] UNIQUE constraints for all duplicate-risk columns
- [ ] Composite unique key definitions
- [ ] Test cases verifying duplicate rejection
- [ ] NULL handling verification (multiple NULLs allowed)

---

## Acceptance Criteria

1. **Single-Column Uniqueness:**
   - [ ] MRN unique per organization
   - [ ] Email unique (account lookup)
   - [ ] NPI unique (national standard)
   - [ ] Appointment_Type code unique

2. **Composite Uniqueness:**
   - [ ] Coding: (appointment_id, code_system, code_value, coding_type)
   - [ ] Prevents duplicate diagnosis/procedure per appointment

3. **NULL Handling:**
   - [ ] Multiple NULLs allowed in unique constraint
   - [ ] Test: Multiple patients with NULL email succeeds

4. **Test Coverage:**
   - [ ] Duplicate insert fails with ERROR 1062
   - [ ] Duplicate update fails with ERROR 1062
   - [ ] Concurrent duplicate attempts handled correctly

---

## Implementation Details

### Unique Constraint Examples

```sql
-- Single-column uniqueness
ALTER TABLE patient ADD UNIQUE KEY idx_mrn (mrn);
ALTER TABLE patient ADD UNIQUE KEY idx_email (email);
ALTER TABLE provider ADD UNIQUE KEY idx_npi (npi);
ALTER TABLE appointment_type ADD UNIQUE KEY idx_code (code);

-- Composite uniqueness (prevent duplicate coding)
ALTER TABLE coding ADD UNIQUE KEY unique_coding_per_appointment 
  (appointment_id, code_system, code_value, coding_type);
```

### Test Cases

```sql
-- TEST 1: Duplicate MRN
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary)
  VALUES ('A123', 'John', 'Doe', '1990-01-01', 'M', '555-0000');
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary)
  VALUES ('A123', 'Jane', 'Doe', '1991-01-01', 'F', '555-1111');
-- ERROR 1062: Duplicate entry 'A123' for key 'idx_mrn'

-- TEST 2: Duplicate email
INSERT INTO patient (mrn, email, first_name, last_name, dob, gender, phone_primary)
  VALUES ('A234', 'john@example.com', 'John', 'Smith', '1985-01-01', 'M', '555-2222');
INSERT INTO patient (mrn, email, first_name, last_name, dob, gender, phone_primary)
  VALUES ('B234', 'john@example.com', 'Jane', 'Smith', '1986-01-01', 'F', '555-3333');
-- ERROR 1062: Duplicate entry 'john@example.com' for key 'idx_email'

-- TEST 3: Multiple NULLs allowed
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary, email)
  VALUES ('C123', 'John', 'Doe', '1990-01-01', 'M', '555-0000', NULL);
INSERT INTO patient (mrn, first_name, last_name, dob, gender, phone_primary, email)
  VALUES ('C456', 'Jane', 'Doe', '1991-01-01', 'F', '555-1111', NULL);
-- SUCCESS: Multiple patients can have NULL email

-- TEST 4: Duplicate coding in appointment
INSERT INTO coding (appointment_id, code_system, code_value, code_description, coding_type)
  VALUES (123, 'ICD10', 'E11.9', 'Type 2 Diabetes', 'diagnosis');
INSERT INTO coding (appointment_id, code_system, code_value, code_description, coding_type)
  VALUES (123, 'ICD10', 'E11.9', 'Type 2 Diabetes without complications', 'diagnosis');
-- ERROR 1062: Duplicate entry '123-ICD10-E11.9-diagnosis'
```

---

## Success Metrics

- [ ] 4+ single-column UNIQUE constraints
- [ ] 1+ composite UNIQUE constraint
- [ ] 100% test pass rate (duplicates rejected)
- [ ] NULL handling correct

---

## Definition of Done

- [ ] All UNIQUE constraints implemented
- [ ] Test suite 100% passing
- [ ] Peer-reviewed and approved
- [ ] Ready for INDEX-1 (indexing tasks)

---

## Next Task

→ INDEX-1: Hot-Path Index Candidate Design
