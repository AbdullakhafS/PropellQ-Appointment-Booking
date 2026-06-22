# SCHEMA-2: Constraint Strategy (PK/FK/Check)

**Task ID:** SCHEMA-2  
**Parent:** TASK-104  
**Category:** Data Modeling  
**Points:** 4  
**Status:** Planned (after SCHEMA-1)  
**Created:** 2026-06-22

---

## Objective

Add explicit PRIMARY KEY, FOREIGN KEY, and CHECK constraints to all entities for enforcing data integrity and preventing invalid states.

---

## Inputs

- SCHEMA-1: Entity definitions and relationships
- Cardinality matrix
- Business rules for valid states

---

## Outputs

- [ ] Complete DDL with PKs, FKs, CHECKs for all tables
- [ ] Cascade/restrict behavior documented
- [ ] Test cases for constraint violations
- [ ] Service-layer error handling guidance

---

## Acceptance Criteria

1. **Primary Keys:**
   - [ ] All tables have explicit PK (BIGINT AUTO_INCREMENT)
   - [ ] Single-column PKs (no composite keys)
   - [ ] PK column named `{table}_id`

2. **Foreign Keys:**
   - [ ] 15+ FK relationships defined
   - [ ] ON DELETE behavior specified (RESTRICT/CASCADE/SET NULL)
   - [ ] FKs prevent orphaned records appropriately

3. **Check Constraints:**
   - [ ] Enum constraints (status, gender, priority)
   - [ ] Timing constraints (end_time > start_time)
   - [ ] Range constraints (bounded numeric fields)

4. **Testing:**
   - [ ] Positive: Valid inserts succeed
   - [ ] Negative: Constraint violations fail (ERROR 1062, 1451, 3819)

---

## Implementation Details

### Primary Key Pattern

```sql
CREATE TABLE {entity} (
  {entity}_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ...
);
```

### Foreign Key Pattern

```sql
-- Restrictive (prevent delete if children exist)
ALTER TABLE appointment ADD FOREIGN KEY (patient_id) 
  REFERENCES patient(patient_id) ON DELETE RESTRICT;

-- Cascading (delete children with parent)
ALTER TABLE coding ADD FOREIGN KEY (appointment_id) 
  REFERENCES appointment(appointment_id) ON DELETE CASCADE;

-- Set to NULL (preserve children, orphan reference)
ALTER TABLE intake ADD FOREIGN KEY (appointment_id) 
  REFERENCES appointment(appointment_id) ON DELETE SET NULL;
```

### Check Constraint Examples

```sql
-- Timing constraint
ALTER TABLE appointment ADD CHECK (scheduled_end_time > scheduled_start_time);

-- Enum constraint
ALTER TABLE patient ADD CHECK (gender IN ('M', 'F', 'O', 'X'));

-- Status workflow
ALTER TABLE appointment ADD CHECK 
  (actual_end_time IS NULL OR actual_start_time IS NOT NULL);
```

---

## Success Metrics

- [ ] 10+ PK constraints created
- [ ] 15+ FK constraints with ON DELETE behavior
- [ ] 8+ CHECK constraints for business rules
- [ ] All constraint tests pass (positive + negative)

---

## Definition of Done

- [ ] DDL peer-reviewed
- [ ] All constraints tested
- [ ] FK cascade behavior validated
- [ ] Ready to proceed to SCHEMA-3

---

## Next Task

→ SCHEMA-3: Uniqueness and Duplicate Prevention
