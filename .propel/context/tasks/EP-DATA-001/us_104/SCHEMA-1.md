# SCHEMA-1: Canonical Entity Model Finalization

**Task ID:** SCHEMA-1  
**Parent:** TASK-104  
**Category:** Data Modeling  
**Points:** 4  
**Status:** Ready to Start  
**Created:** 2026-06-22

---

## 1. Objective

Define and normalize core entities (patient, appointment, provider, intake, document, coding, audit_log) with clear business ownership, documented relationships, and no unnecessary denormalization.

---

## 2. Inputs

- US-104 user story requirements
- Existing database patterns from similar systems
- Data flow diagrams (if available)
- Business domain requirements

---

## 3. Outputs

**Deliverables:**
- [ ] Entity definitions document (patient, appointment, provider, clinic, appointment_type, specialty, intake, document, coding, audit_log)
- [ ] Normalized schema design with ownership per aggregate
- [ ] Entity-relationship diagram (draft with cardinality)
- [ ] Cardinality matrix (1:N, N:1, 0:N, M:N relationships)
- [ ] Data dictionary with business context for each entity

---

## 4. Acceptance Criteria

1. **Entity Definitions:**
   - [ ] All 8 core entities defined with clear business purpose
   - [ ] Each entity has primary domain/aggregate assignment
   - [ ] No cross-cutting concerns (no mixing patient + appointment concerns in single entity)

2. **Normalization:**
   - [ ] 3NF normalization applied (no transitive dependencies)
   - [ ] Any denormalization explicitly justified
   - [ ] Foreign key relationships identified

3. **Cardinality:**
   - [ ] Cardinality matrix shows all relationships
   - [ ] Optionality clear (1:N vs 0:N)
   - [ ] Example: Patient → Appointment (1:N), Appointment → Intake (0:N)

4. **Entity-Relationship Diagram:**
   - [ ] ER diagram drawn (Mermaid or PlantUML)
   - [ ] All tables and relationships shown
   - [ ] Cardinality notations included (crow's foot or UML)

---

## 5. Implementation Details

### Entity Scope

**Core Entities:**

| Entity | Purpose | Sample Fields |
|---|---|---|
| PATIENT | Core identity, demographics | patient_id, MRN, name, DOB, email, phone |
| APPOINTMENT | Booking reservation | appointment_id, patient_id, provider_id, scheduled_time, status |
| PROVIDER | Clinician/staff identity | provider_id, NPI, name, specialty, license |
| APPOINTMENT_TYPE | Taxonomy of appointment types | code, name, duration, requirements |
| SPECIALTY | Medical specialty reference | specialty_id, code, name |
| CLINIC | Physical location | clinic_id, name, address, phone |
| INTAKE | Pre-appointment form | intake_id, patient_id, form_type, status, submitted_at |
| DOCUMENT | Clinical/admin files | document_id, patient_id, type, file_path, upload_timestamp |
| CODING | Clinical codes (ICD10, CPT, SNOMED) | coding_id, appointment_id, code_system, code_value |
| AUDIT_LOG | Compliance trail | audit_id, entity_type, entity_id, action, actor_id, timestamp |

### Relationships

**Patient (Hub):**
- Patient → Appointment (1:N): One patient books many appointments
- Patient → Intake (1:N): One patient completes many forms
- Patient → Document (1:N): One patient has many documents

**Appointment (Core):**
- Appointment → Provider (N:1): Many appointments per provider
- Appointment → Clinic (N:1): Many appointments per clinic
- Appointment → Appointment_Type (N:1): Maps to type
- Appointment → Intake (0:N): May trigger intake
- Appointment → Document (0:N): May attach documents
- Appointment → Coding (1:N): Has diagnoses/procedures

**Provider (Supply Side):**
- Provider → Specialty (N:1): Provider has one specialty

---

## 6. Success Metrics

- [ ] 8+ core entities defined
- [ ] 10+ relationships documented with cardinality
- [ ] 0 cycles in relationship graph (acyclic design)
- [ ] 90%+ of columns avoid transitive dependencies (3NF)
- [ ] ERD diagram reviewable and correct

---

## 7. Definition of Done

- [ ] Entity definitions reviewed by backend lead
- [ ] ER diagram drawn and validated
- [ ] Cardinality matrix complete
- [ ] All deliverables peer-reviewed
- [ ] Ready to proceed to SCHEMA-2

---

## Next Task

→ SCHEMA-2: Constraint Strategy (PK/FK/Check)
