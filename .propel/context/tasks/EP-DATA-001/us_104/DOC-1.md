# DOC-1: Data Model Glossary and ERD Updates

**Task ID:** DOC-1  
**Parent:** TASK-104  
**Category:** Governance and Documentation  
**Points:** 4  
**Status:** Planned (after SCHEMA-3)  
**Created:** 2026-06-22

---

## Objective

Document all entities and columns with business meaning, validation rules, and relationships for stakeholder reference.

---

## Inputs

- SCHEMA-3 final DDL
- INDEX-2 index definitions
- Business requirements from US-104
- Query analysis from PERF-2

---

## Outputs

- [ ] Data model glossary (100+ column definitions with business context)
- [ ] Entity-relationship diagram (Mermaid or PlantUML)
- [ ] Column metadata (type, constraints, validation, example values)
- [ ] Service-facing contract documentation
- [ ] Integration guide for services

---

## Acceptance Criteria

1. **Glossary Completeness:**
   - [ ] All 8 entities documented with purpose
   - [ ] 100+ columns with business meaning
   - [ ] Validation rules documented
   - [ ] Status enum values explained
   - [ ] Required vs. optional fields documented

2. **Entity-Relationship Diagram:**
   - [ ] All tables shown
   - [ ] All foreign keys shown with cardinality
   - [ ] Crow's foot notation or UML cardinality
   - [ ] Color-coded by aggregate (patient, appointment, clinical)

3. **Column Metadata:**
   - [ ] Data type and size
   - [ ] Nullable/required status
   - [ ] Validation constraints
   - [ ] Example values
   - [ ] Search/index guidance

4. **Service Integration:**
   - [ ] API contract for each entity
   - [ ] Common queries documented
   - [ ] Access patterns explained

---

## Implementation Details

### Data Model Glossary Template

**PATIENT Entity**
```
Purpose: Core patient identity and demographics
Primary Key: patient_id (BIGINT)
Indexes: idx_patient_mrn, idx_patient_email, idx_patient_phone

Columns:
- patient_id (BIGINT, AUTO_INCREMENT, PK)
  Medical record internal identifier
  Example: 123456
  Unique Index: PRIMARY

- mrn (VARCHAR(50), UNIQUE, NOT NULL)
  Medical Record Number - national patient identifier per organization
  Business: Uniquely identifies patient in medical system
  Validation: Must be alphanumeric, 1-50 characters
  Example: MRN-0123456
  Index: idx_patient_mrn (UNIQUE)

- first_name (VARCHAR(100), NOT NULL)
  Patient given name
  Example: John
  Validation: 1-100 characters, letters/hyphens/apostrophes allowed

- last_name (VARCHAR(100), NOT NULL)
  Patient surname
  Example: Doe
  Validation: 1-100 characters, letters/hyphens/apostrophes allowed

- dob (DATE, NOT NULL)
  Date of birth
  Business: Used for age calculation, identification, scheduling
  Example: 1985-05-15
  Validation: Must be in past, reasonable age (18-110 years)

- gender (CHAR(1), CHECK IN ('M','F','O','X'), NOT NULL)
  Biological/social gender identity
  M = Male, F = Female, O = Other, X = Prefer not to say
  Example: M

- email (VARCHAR(255), UNIQUE, NULL)
  Patient email address
  Business: Primary contact for appointments, notifications
  Example: john.doe@example.com
  Validation: Valid email format, max 255 chars
  Index: idx_patient_email (UNIQUE)
  Note: Can be NULL if patient prefers phone/mail communication

- phone_primary (VARCHAR(20), NOT NULL)
  Patient primary phone number
  Business: Contact for appointment reminders, clinical calls
  Example: 555-0123
  Validation: 10-20 characters, digits and hyphens
  Index: idx_patient_phone

- created_at (DATETIME, NOT NULL, DEFAULT CURRENT_TIMESTAMP)
  Record creation timestamp
  Audit trail: When patient was registered

- updated_at (DATETIME, NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)
  Record last modification timestamp
  Audit trail: When patient data was last updated
```

### Entity-Relationship Diagram (Mermaid)

```mermaid
erDiagram
    PATIENT ||--o{ APPOINTMENT : books
    PATIENT ||--o{ INTAKE : completes
    PATIENT ||--o{ DOCUMENT : has
    APPOINTMENT }o--|| PROVIDER : "with"
    APPOINTMENT }o--|| CLINIC : "at"
    APPOINTMENT }o--|| APPOINTMENT_TYPE : "is"
    APPOINTMENT ||--o{ INTAKE : triggers
    APPOINTMENT ||--o{ CODING : diagnoses
    APPOINTMENT ||--o{ DOCUMENT : attachments
    PROVIDER }o--|| SPECIALTY : has
    AUDIT_LOG }o--|| PATIENT : logs

    PATIENT {
        bigint patient_id PK
        string mrn UK "unique per org"
        string first_name
        string last_name
        date dob
        char gender
        string email UK
        string phone_primary
        datetime created_at
        datetime updated_at
    }

    APPOINTMENT {
        bigint appointment_id PK
        bigint patient_id FK
        bigint provider_id FK
        bigint clinic_id FK
        bigint appointment_type_id FK
        datetime scheduled_start_time
        datetime scheduled_end_time
        string appointment_status
        datetime created_at
    }

    PROVIDER {
        bigint provider_id PK
        string npi UK
        string first_name
        string last_name
        bigint specialty_id FK
        string license_number
    }

    CLINIC {
        bigint clinic_id PK
        string name UK
        string address
        string phone
    }

    APPOINTMENT_TYPE {
        bigint appointment_type_id PK
        string code UK
        string name
        int duration_minutes
    }

    SPECIALTY {
        bigint specialty_id PK
        string code UK
        string name
    }

    INTAKE {
        bigint intake_id PK
        bigint patient_id FK
        bigint appointment_id FK NULL
        string form_type
        string status
        datetime submitted_at
    }

    DOCUMENT {
        bigint document_id PK
        bigint patient_id FK
        bigint appointment_id FK NULL
        string document_type
        string file_path
        datetime upload_timestamp
    }

    CODING {
        bigint coding_id PK
        bigint appointment_id FK
        string code_system
        string code_value UK "composite"
        string code_description
        string coding_type
    }

    AUDIT_LOG {
        bigint audit_id PK
        string entity_type
        bigint entity_id
        string action
        bigint actor_id
        datetime created_at
    }
```

### Service-Facing Contract

**Patient Service API**
```
GET /patients/{patient_id}
  Returns: PATIENT entity
  Fields: patient_id, mrn, first_name, last_name, dob, gender, email, phone_primary
  Example: {"patient_id": 123, "mrn": "MRN-0123456", "first_name": "John", ...}

PUT /patients/{patient_id}
  Updates: email, phone_primary, last_name (other fields immutable)
  Idempotency: Keyed by mrn per organization
  Validation: Email must be unique; phone must be valid format
```

---

## Success Metrics

- [ ] 8+ entities documented
- [ ] 100+ columns with business meaning
- [ ] ERD diagram complete and accurate
- [ ] Service contracts documented
- [ ] 100% peer review approval

---

## Definition of Done

- [ ] Glossary document published
- [ ] ERD diagram rendered
- [ ] Service contracts documented
- [ ] Examples provided for all columns
- [ ] Ready for DOC-2

---

## Next Task

→ DOC-2: DDL and Migration Documentation
