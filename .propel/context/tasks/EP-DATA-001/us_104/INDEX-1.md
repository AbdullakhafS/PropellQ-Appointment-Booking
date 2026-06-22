# INDEX-1: Hot-Path Index Candidate Design

**Task ID:** INDEX-1  
**Parent:** TASK-104  
**Category:** Indexing and Query  
**Points:** 5  
**Status:** Planned (can parallel with GOV-1)  
**Created:** 2026-06-22

---

## Objective

Identify and design indexes for critical operational queries (booking, schedule lookup, queue, profile timeline) using leftmost prefix principle and covering index strategy.

---

## Inputs

- SCHEMA-2 DDL
- Query patterns from booking, queue, profile, intake flows
- Expected transaction volumes
- Cardinality analysis

---

## Outputs

- [ ] Read/write path matrix (10+ operational queries)
- [ ] Index candidates with predicate/join/orderby patterns
- [ ] Hot-path vs. optional classification
- [ ] Estimated latency impact for each index
- [ ] Write-path cost analysis

---

## Acceptance Criteria

1. **Hot-Path Query Identification:**
   - [ ] 4+ critical queries identified (booking, schedule, queue, profile)
   - [ ] Expected volume documented (requests/hour)
   - [ ] Latency targets specified (5-50ms p95 range)

2. **Index Design:**
   - [ ] Compound indexes match WHERE clause (leftmost prefix)
   - [ ] Covering indexes include SELECT columns when possible
   - [ ] Rationale documented for each index

3. **Candidate List:**
   - [ ] 10-15 index candidates identified
   - [ ] Mandatory (hot path) vs. optional classified
   - [ ] Estimated improvement to latency

4. **Impact Analysis:**
   - [ ] Write latency cost estimated (insert/update/delete overhead)
   - [ ] Storage overhead calculated
   - [ ] Maintenance burden assessed

---

## Implementation Details

### Hot-Path Queries

**Query 1: Patient Appointment Lookup (Tier 1 - Very Hot)**
```sql
SELECT appointment_id, scheduled_start_time, provider_id, appointment_status
FROM appointment
WHERE patient_id = ? AND appointment_status IN ('scheduled', 'confirmed')
ORDER BY scheduled_start_time ASC
LIMIT 10;
```
- **Index Candidate:** `(patient_id, appointment_status, scheduled_start_time DESC)`
- **Volume:** 10,000/hour
- **Target p95:** 5ms
- **Rationale:** Leftmost: patient_id (WHERE), then appointment_status (WHERE), then scheduled_start_time (ORDER BY)

**Query 2: Provider Daily Schedule (Tier 1 - Very Hot)**
```sql
SELECT appointment_id, scheduled_start_time, scheduled_end_time, patient_id
FROM appointment
WHERE provider_id = ? AND DATE(scheduled_start_time) = ?
ORDER BY scheduled_start_time ASC;
```
- **Index Candidate:** `(provider_id, scheduled_start_time, appointment_status)`
- **Volume:** 1,000/hour
- **Target p95:** 10ms

**Query 3: Clinic Queue (Tier 1 - Very Hot)**
```sql
SELECT appointment_id, patient_id, scheduled_start_time
FROM appointment
WHERE clinic_id = ? AND appointment_status IN ('in-progress', 'confirmed')
  AND DATE(scheduled_start_time) = CURDATE()
ORDER BY scheduled_start_time ASC;
```
- **Index Candidate:** `(clinic_id, scheduled_start_time, appointment_status)`
- **Volume:** 500/hour
- **Target p95:** 15ms

**Query 4: Patient Profile Timeline (Tier 2 - Medium)**
```sql
SELECT a.appointment_id, a.scheduled_start_time, a.appointment_status,
       i.intake_id, i.status, d.document_id, d.document_type
FROM appointment a
LEFT JOIN intake i ON a.appointment_id = i.appointment_id
LEFT JOIN document d ON a.appointment_id = d.appointment_id
WHERE a.patient_id = ?
ORDER BY a.scheduled_start_time DESC;
```
- **Indexes:** `appointment(patient_id, scheduled_start_time DESC)`, `intake(appointment_id)`, `document(appointment_id)`
- **Target p95:** 50ms

### Supporting Indexes

| Index | Columns | Rationale | Tier |
|---|---|---|---|
| idx_patient_mrn | patient (mrn) | Emergency lookup | Hot |
| idx_patient_email | patient (email) | Account lookup | Hot |
| idx_patient_phone | patient (phone_primary) | Phone-based search | Hot |
| idx_intake_status | intake (patient_id, status, submitted_at DESC) | Pending intake review | Medium |
| idx_document_patient | document (patient_id) | Patient documents | Medium |
| idx_document_type | document (document_type) | Document filtering | Medium |
| idx_coding_appointment | coding (appointment_id) | Codes per appointment | Medium |
| idx_coding_lookup | coding (code_system, code_value) | Code search | Optional |
| idx_appointment_status | appointment (appointment_status, scheduled_start_time) | Analytics | Optional |
| idx_audit_entity | audit_log (entity_type, entity_id, created_at DESC) | Compliance query | Low |

---

## Success Metrics

- [ ] 10+ index candidates identified
- [ ] Hot-path queries analyzed and documented
- [ ] Estimated latency improvements >50% for hot paths
- [ ] Write-path cost acceptable (<10% overhead)

---

## Definition of Done

- [ ] Query matrix complete
- [ ] Index candidates with rationale documented
- [ ] Peer-reviewed by backend team
- [ ] Ready to proceed to INDEX-2

---

## Next Task

→ INDEX-2: Index Rationalization and Cleanup
