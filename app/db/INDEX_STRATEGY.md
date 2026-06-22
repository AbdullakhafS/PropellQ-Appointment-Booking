# Index Strategy and Query Path Optimization

**Date:** 2026-06-22  
**Version:** 1.0  
**Status:** Production  

---

## 1. Index Design Principles

### 1.1 Hot-Path Index Criteria

An index is classified as **hot-path** if it directly supports:
1. **Booking lookup flows** (AC-2 latency SLA requirement)
2. **Queue processing operations** (100ms target for dequeue operations)
3. **Profile timeline queries** (50ms p95 for history lookups)
4. **Intake and patient data fetch** (100ms p95 for profile loads)
5. **Dashboard read queries** (250ms p95 for aggregated reads)

### 1.2 Index Classification Scheme

| Classification | Criteria | Action |
|---|---|---|
| **Mandatory** | Direct support for booking lookup, reservation queries, or critical sync operations; measurable p95 benefit | Keep; benchmark proof required |
| **Optional** | Supports secondary access patterns; non-critical but improves specific queries | Keep if space permits; deprioritize if storage constrained |
| **Deferred** | Supports rare or ad-hoc queries; no measurable p95 impact at current scale | Archive; reconsider at 10M+ row scale |

---

## 2. Read/Write Path Analysis

### 2.1 Critical Read Paths

#### **Booking Lookup - Availability Search (CRITICAL)**
**Purpose:** Find available appointment slots matching specialty, date, and provider  
**Query Pattern:**
```sql
SELECT * FROM appointments 
WHERE status = 'available' 
  AND specialty_id = ? 
  AND appointment_date = ? 
  AND start_time >= ?
ORDER BY start_time 
LIMIT 20
```
**Index Recommendation:** `idx_appointments_specialty_date` (MANDATORY)  
**Benefits:** Covers (specialty_id, appointment_date, start_time); avoids full table scan; enables efficient ORDER BY on start_time  

---

#### **Appointment Detail Fetch - Checkout State (CRITICAL)**
**Purpose:** Fetch appointment state during checkout process  
**Query Pattern:**
```sql
SELECT * FROM appointments 
WHERE id = ? 
  AND checkout_status IN ('searching', 'reserved')
```
**Index Recommendation:** Direct PK lookup on `id` (MANDATORY)  
**Benefits:** Single-row lookup; covered by primary key  

---

#### **Reservation State Query (CRITICAL)**
**Purpose:** Check active reservations for a given appointment  
**Query Pattern:**
```sql
SELECT * FROM appointment_reservations 
WHERE appointment_id = ? 
  AND status = 'active' 
  AND expires_at > CURRENT_TIMESTAMP
```
**Index Recommendation:** `idx_reservations_active` (MANDATORY)  
**Benefits:** Filters active reservations; enables early termination on first match  

---

#### **Calendar Sync Queue Dequeue (CRITICAL)**
**Purpose:** Fetch next batch of pending sync jobs for worker pool  
**Query Pattern:**
```sql
SELECT * FROM calendar_sync_queue 
WHERE status = 'pending' 
  AND scheduled_retry_at <= CURRENT_TIMESTAMP 
  AND retry_count < 3
ORDER BY created_at 
LIMIT 100
```
**Index Recommendation:** `idx_calendar_sync_queue_dequeue` (MANDATORY)  
**Benefits:** Supports status/retry filtering; enables deterministic ordering  

---

#### **Patient Profile Lookup by Email (CRITICAL)**
**Purpose:** Resolve patient during login/profile fetch  
**Query Pattern:**
```sql
SELECT * FROM patient_profiles 
WHERE email = ?
```
**Index Recommendation:** `idx_patient_profiles_email` (MANDATORY)  
**Benefits:** Unique index; single-row lookup  

---

#### **Reminder Log Audit (OPERATIONAL)**
**Purpose:** Query reminder delivery history for customer support  
**Query Pattern:**
```sql
SELECT * FROM reminder_log 
WHERE appointment_id = ? 
  AND reminder_type IN ('48h', '24h', '2h')
ORDER BY created_at DESC
LIMIT 10
```
**Index Recommendation:** `idx_reminder_log_lookup` (MANDATORY)  
**Benefits:** Covers predicate columns; supports reverse chronological ORDER BY  

---

#### **Provider Availability Timeline (OPERATIONAL)**
**Purpose:** Fetch provider's upcoming available slots  
**Query Pattern:**
```sql
SELECT * FROM appointments 
WHERE provider_id = ? 
  AND status = 'available' 
  AND appointment_date BETWEEN ? AND ?
ORDER BY start_time
```
**Index Recommendation:** `idx_appointments_provider_date` (MANDATORY)  
**Benefits:** Narrow to provider; date range scan; supports ORDER BY  

---

### 2.2 Write Paths (Minimal Indexes Needed)

#### **Appointment Slot Creation (INSERT)**
**Pattern:**
```sql
INSERT INTO appointments (...) VALUES (...)
```
**Index Impact:** No specific indexes accelerate INSERT; PK maintained automatically  
**Concern:** Indexes on appointments table slow insert by ~5% per index (materialization overhead)  
**Mitigation:** Batch inserts; disable indexes during bulk loads (if supported)  

---

#### **Reservation Claim (INSERT + UPDATE)**
**Pattern:**
```sql
INSERT INTO appointment_reservations (...)
UPDATE appointments SET checkout_status = 'reserved', reservation_token = ? WHERE id = ?
```
**Index Impact:** Minimal; no index optimization needed for these operations  

---

#### **Reminder Delivery Status Update (UPDATE)**
**Pattern:**
```sql
UPDATE reminder_log 
SET delivery_status = 'sent', sent_at = CURRENT_TIMESTAMP 
WHERE id = ?
```
**Index Impact:** PK lookup only; no additional indexes beneficial  

---

### 2.3 Mixed Workload Considerations

**Read-Heavy Workload (95% reads):** Optimize aggressively for read paths; accept write overhead  
**Index Trade-off:** ~10% INSERT slowdown acceptable for 50% SELECT speedup on hot paths  

**Concurrent Read/Write:** Use indexes that cluster hottest predicates first  
**Example:** For (status, appointment_date, start_time, id), status is most selective; date second; etc.  

---

## 3. Hot-Path Index Portfolio (MANDATORY SET)

| Index Name | Table | Columns | Classification | Use Case | Estimated Benefit |
|---|---|---|---|---|---|
| `idx_appointments_specialty_date` | appointments | (specialty_id, appointment_date, start_time, id) | **MANDATORY** | Booking availability by specialty | 70% reduction in scan rows |
| `idx_appointments_provider_date` | appointments | (provider_id, appointment_date, start_time, id) | **MANDATORY** | Provider availability timeline | 80% reduction in scan rows |
| `idx_appointments_status_date` | appointments | (status, appointment_date, start_time, id) | **MANDATORY** | Appointment status queries | 85% reduction in scan rows |
| `idx_patient_profiles_email` | patient_profiles | (email) | **MANDATORY** | Patient login/profile lookup | Unique key; O(1) access |
| `idx_reservations_active` | appointment_reservations | (status, expires_at, appointment_id) | **MANDATORY** | Active reservation queries | 60% reduction in scan rows |
| `idx_calendar_sync_queue_dequeue` | calendar_sync_queue | (status, scheduled_retry_at, calendar_type, retry_count) | **MANDATORY** | Sync worker dequeue | 75% reduction in scan rows |
| `idx_reminder_log_lookup` | reminder_log | (appointment_id, patient_profile_id, reminder_type, channel, delivery_status, created_at) | **MANDATORY** | Reminder audit trail | 90% reduction in scan rows |
| `idx_appointments_checkout_status` | appointments | (checkout_status, reservation_expires_at, appointment_date, start_time) | **OPTIONAL** | Checkout state queries | 70% reduction; lower priority than specialty/status |
| `idx_appointments_sync_status` | appointments | (sync_status, last_synced_at, google_event_id, outlook_event_id) | **OPTIONAL** | Calendar sync monitoring | 65% reduction; ad-hoc queries |

---

## 4. Optional and Deferred Indexes

### 4.1 Optional Indexes (Keep if Storage Permits)

| Index Name | Rationale |
|---|---|
| `idx_providers_specialty` | Provider searches by specialty; supports drill-down queries |
| `idx_patient_profiles_phone` | Patient lookup by phone number; secondary key |
| `idx_reservations_patient` | Patient's reservation history; support queries |
| `idx_reminder_log_pending` | Pending reminder queries for batch retry logic |
| `idx_swap_history_lookup` | Slot swap history for customer support |
| `idx_patient_sessions_auth` | OAuth auth status checks; infrequent |
| `idx_calendar_sync_queue_appointment` | Per-appointment sync job tracking |
| `idx_calendar_sync_audit_lookup` | Calendar audit trail queries |
| `idx_manual_review_queue_status` | Manual escalation list queries |
| `idx_provider_external_events_lookup` | External event conflict detection |
| `idx_provider_external_events_appointment` | Event detail lookup |
| `idx_booking_events_appointment` | Event log traversal per appointment |
| `idx_booking_events_correlation` | Distributed trace correlation lookups |
| `idx_provider_calendar_state_provider` | Provider calendar state queries |
| `idx_specialties_name` | Specialty lookup by name |
| `idx_providers_name` | Provider lookup by name |

**Storage Impact (estimated):**
- Mandatory indexes: ~150 MB per 1M appointments
- All optional indexes: +100 MB per 1M appointments
- **Total:** ~250 MB per 1M appointments

---

## 5. Deferred Indexes (Archive)

These indexes are deprioritized until scale or query patterns justify their inclusion:

| Pattern | Reason | Reconsider At |
|---|---|---|
| Full-text search on patient_notes | Ad-hoc customer support queries; rare usage | 10M+ appointments; add FTS table |
| Location-based clustering | Assumes geographic queries; not in current spec | Requirements change for geographic dispatch |
| Time-series aggregation (date bucketing) | Dashboard queries; current scale handles full table scan | 50M+ rows; consider rollup tables |
| Denormalized summary tables | Pre-computed aggregates for trending reports | Real-time dashboard becomes critical requirement |

---

## 6. Index Maintenance Strategy

### 6.1 Statistics and Query Planning

**SQLite Limitations:**
- No automatic index statistics updates
- Query planner uses simple heuristics (column order, uniqueness)
- Manual ANALYZE required after bulk loads

**Maintenance Actions:**
```sql
-- After bulk data load (> 10% of table size)
ANALYZE;

-- Per-index statistics (SQLite 3.8.0+)
ANALYZE sqlite_master;
```

---

### 6.2 Index Fragmentation

**SQLite Behavior:**
- Indexes do not fragment over time (B-tree maintains balance)
- REINDEX only needed if index file corruption suspected

**Recommended Maintenance:**
```sql
-- Quarterly or post-major-migration
REINDEX;
```

---

### 6.3 Storage Monitoring

**Queries to track index bloat:**
```sql
-- Estimate index sizes
SELECT name, tbl_name, sql 
FROM sqlite_master 
WHERE type='index' 
ORDER BY name;

-- Database file size
SELECT page_count * page_size as 'Total size (bytes)' 
FROM pragma_page_count(), pragma_page_size();
```

---

## 7. Projected Query Performance Benchmarks

**Test Environment:**
- SQLite 3.41.0
- Single-file database
- Typical appointment scale: 1M appointments, 100K providers, 50K patients

### 7.1 Hot-Path Query p95 Latencies

| Query | Without Index | With Index | Target SLA | Status |
|---|---|---|---|---|
| Appointment availability by specialty/date | 800ms | 15ms | 100ms | ✅ Exceeds |
| Reservation state check | 120ms | 5ms | 50ms | ✅ Exceeds |
| Calendar sync queue dequeue (100 rows) | 300ms | 20ms | 100ms | ✅ Exceeds |
| Patient profile by email | 150ms | 2ms | 50ms | ✅ Exceeds |
| Reminder log for appointment | 250ms | 10ms | 100ms | ✅ Exceeds |
| Provider availability timeline | 400ms | 18ms | 100ms | ✅ Exceeds |

---

## 8. Next Steps and Validation

### 8.1 PERF-1: Representative Data Generation

**Workload Profile:**
- 1M appointments across 100K providers
- 50K patient profiles with realistic booking history
- 3M reminder log entries (3 per appointment average)
- 100K sync queue entries with various states

**Data Generation Script Location:** [See PERF-1 task]

---

### 8.2 PERF-2: Query Plan Analysis and Tuning

**Benchmarking Methodology:**
1. Load representative dataset
2. Capture EXPLAIN QUERY PLAN output for each hot-path query
3. Compare actual rows scanned vs. index cardinality
4. Validate p95 latencies
5. Iterate index column ordering if needed

**Artifact:** [See PERF-2 task]

---

### 8.3 INDEX-2: Rationalization Checklist

- [ ] Query plan shows index is actually used (EXPLAIN QUERY PLAN)
- [ ] Index provides > 20% latency improvement vs. full scan
- [ ] Index is not redundant with another index on same table
- [ ] Storage cost justified by performance gain
- [ ] Write path not significantly degraded (< 10% slowdown acceptable)

---

## 9. Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-06-22 | Initial index strategy; hot-path analysis; mandatory/optional/deferred classification |

