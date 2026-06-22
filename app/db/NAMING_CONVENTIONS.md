# SQL Naming Conventions and Semantic Standardization

**Date:** 2026-06-22  
**Version:** 1.0  
**Status:** Production Standard  

---

## 1. Overview

Consistent naming conventions ensure maintainability, reduce ambiguity, and enable effective tooling. This document establishes mandatory naming patterns for the PropellQ Appointment Booking schema across all artifacts: tables, columns, constraints, indexes, and stored procedures.

---

## 2. General Principles

| Principle | Rule | Example |
|-----------|------|---------|
| **Descriptiveness** | Use full English words; avoid abbreviations | `appointment_reservations` ✓ not `appt_res` ✗ |
| **Consistency** | Use same term across all contexts | `appointment_id` (not `appt_id` or `app_id`) |
| **Clarity** | Prioritize clarity over brevity | `confirmation_sent_at` ✓ not `conf_sent` ✗ |
| **Case Sensitivity** | Use lowercase with underscores (snake_case) | `patient_timezone` not `PatientTimezone` |
| **Reserved Words** | Avoid SQL reserved words | `order`, `group`, `user`, `comment` are reserved |
| **Prefixes/Suffixes** | Use meaningful prefixes; standardize suffixes | Prefix by domain; suffix by type (_id, _at, _count) |

---

## 3. Naming Patterns

### 3.1 Table Naming

**Pattern:** `[domain_]entity_[category]` (plural form)

| Table | Domain | Entity | Category | Rule |
|---|---|---|---|---|
| `specialties` | reference | specialty | — | Plural noun; domain-agnostic |
| `providers` | reference | provider | — | Plural noun |
| `appointments` | booking | appointment | — | Plural noun |
| `appointment_reservations` | booking | appointment | reservations | Compound entity; join concept |
| `patient_profiles` | booking | patient | profiles | Scoped entity; profile is context |
| `booking_events` | communication | booking | events | Domain prefix disambiguates |
| `confirmation_deliveries` | communication | confirmation | deliveries | Type-scoped entity |
| `reminder_log` | communication | reminder | log | Log table (singular for aggregates) |
| `calendar_sync_queue` | integration | calendar | sync_queue | Queue table; functional scope |
| `provider_calendar_state` | integration | provider | calendar_state | State machine table |
| `patient_sessions` | integration | patient | sessions | Session/authentication table |

**Validation Checklist:**
- [ ] Table name is plural (except aggregate tables: _log, _queue, _state)
- [ ] Table name uses lowercase snake_case
- [ ] Table name is descriptive (≥2 words preferred)
- [ ] No SQL reserved words in table name
- [ ] Related tables share common prefixes (e.g., `calendar_*`)

---

### 3.2 Column Naming

#### 3.2.1 Identifier Columns

**Pattern:** `[table_name_singular]_id` for foreign keys; `id` for primary keys

| Column | Table | Meaning | Rule |
|---|---|---|---|
| `id` | any | Primary key | Always named `id`; auto-increment INTEGER |
| `provider_id` | appointments | FK to provider | FK = singular table name + _id |
| `specialty_id` | appointments | FK to specialty | FK = singular table name + _id |
| `appointment_id` | appointment_reservations | FK to appointment | FK = singular table name + _id |
| `patient_profile_id` | appointment_reservations | FK to patient | FK uses entity name (patient_profile) |

**Foreign Key Naming Rule:**
- FK column = `[referenced_table_singular]_id`
- Exception: Long table names use entity abbreviation consistently
  - `appointment_id` not `appt_id` (use full word for FKs)
  - `patient_profile_id` (use full entity name if table uses full name)

---

#### 3.2.2 Timestamp Columns

**Pattern:** `[event_or_state]_at` or `[event_or_state]_timestamp`

| Column | Meaning | Type | Rule |
|---|---|---|---|
| `created_at` | Entity creation | TEXT (ISO 8601) | Immutable; all tables |
| `updated_at` | Last modification | TEXT (ISO 8601) | Mutable; set on every update |
| `confirmation_sent_at` | Email confirmation sent | TEXT (ISO 8601) | Event timestamp; nullable |
| `reminder_sent_48h_at` | 48h reminder sent | TEXT (ISO 8601) | Event timestamp; nullable |
| `expires_at` | Expiration deadline | TEXT (ISO 8601) | Lifecycle boundary |
| `scheduled_retry_at` | Next retry time | TEXT (ISO 8601) | Queue table; ordering key |
| `last_synced_at` | Last sync operation | TEXT (ISO 8601) | State tracking |

**Timestamp Format:**
- All timestamps stored as TEXT in ISO 8601 format: `YYYY-MM-DDTHH:MM:SS`
- UTC timestamps preferred (document timezone policy if local used)
- Never use Unix epoch or other formats
- Always NOT NULL with DEFAULT CURRENT_TIMESTAMP for created_at/updated_at

---

#### 3.2.3 State/Status Columns

**Pattern:** `[entity_]status` or `[lifecycle_phase]_status`

| Column | Table | Allowed Values | Rule |
|---|---|---|---|
| `status` | appointments | 'available', 'booked', 'cancelled' | Core entity lifecycle |
| `checkout_status` | appointments | 'searching', 'reserved', 'confirmed', 'expired', 'cancelled' | Process phase tracking |
| `sync_status` | appointments | 'not_connected', 'pending', 'synced', 'failed', 'manual_review', 'revoked' | External integration state |
| `delivery_status` | reminder_log | 'queued', 'sent', 'failed', 'skipped' | Communication outcome |
| `auth_status` | patient_sessions | 'revoked', 'authorized', 'error' | OAuth state |

**Status Naming Rules:**
- Use lowercase, snake_case for multi-word states
- Document all allowed values in CHECK constraint comment
- Include meaningful terminal states (e.g., 'manual_review' for escalation)
- Avoid ambiguous states (e.g., 'pending' should clarify pending for what?)

---

#### 3.2.4 Flag/Boolean Columns

**Pattern:** `[entity_][verb]` (e.g., `is_active`, `has_permission`)

| Column | Type | Values | Rule |
|---|---|---|---|
| `is_active` | INTEGER | 0 (false), 1 (true) | Default 1; soft-delete marker |
| `do_not_disturb` | INTEGER | 0 (false), 1 (true) | Preference flag |
| `webhook_enabled` | INTEGER | 0 (false), 1 (true) | Feature flag |

**Boolean Column Rules:**
- Use INTEGER (0/1) not TEXT ('true'/'false') for SQLite compatibility
- Always include CHECK constraint (value IN (0, 1))
- Prefix with `is_`, `has_`, `do_`, etc. for clarity
- Default to 0 (false) unless business logic requires otherwise

---

#### 3.2.5 Count/Metric Columns

**Pattern:** `[entity]_[metric]_count`

| Column | Meaning | Type | Rule |
|---|---|---|---|
| `review_count` | Provider reviews | INTEGER | Denormalized metric; >= 0 |
| `retry_count` | Sync/delivery retry attempts | INTEGER | Queue tracking; >= 0 |

**Count Column Rules:**
- Add CHECK constraint (value >= 0)
- Never null; default 0
- Include documentation for incrementation logic

---

#### 3.2.6 Reference and Provenance Columns

**Pattern:** `[external_system]_[entity]_id` or `[system]_id`

| Column | Meaning | Rule |
|---|---|---|
| `google_event_id` | Google Calendar event ID | External system prefix |
| `outlook_event_id` | Outlook Calendar event ID | External system prefix |
| `external_message_id` | Email service provider ID | Generic prefix for multiple providers |
| `correlation_id` | Distributed trace correlation | Observability reference |
| `idempotency_key` | Client idempotency key | Deduplication reference |

**Reference Column Rules:**
- Prefix with external system name (google_, outlook_, external_)
- Make nullable if optional integration
- Document external system and ID format (UUID, numeric, etc.)

---

### 3.3 Constraint Naming

#### 3.3.1 Primary Key Constraints

**Pattern:** PRIMARY KEY (implicit; id column is PK)

```sql
-- SQLite auto-generates as sqlite_autoindex_<table>_1
-- No explicit naming needed in SQLite
id INTEGER PRIMARY KEY AUTOINCREMENT
```

---

#### 3.3.2 Foreign Key Constraints

**Pattern:** FOREIGN KEY (column_name) REFERENCES target_table (target_column)

```sql
-- Named implicitly by SQLite
FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE RESTRICT

-- Rules:
-- - Explicit naming not required in SQLite
-- - Document cascade behavior (RESTRICT, CASCADE, SET NULL) in schema comments
-- - ON DELETE RESTRICT: Prevents deletion of parent if children exist (default, recommended)
-- - ON DELETE CASCADE: Automatically delete children (use sparingly)
-- - ON DELETE SET NULL: Null out FK on parent delete (for optional relationships)
```

---

#### 3.3.3 Unique Constraints

**Pattern:** UNIQUE (column_name) or composite UNIQUE (col1, col2, ...)

```sql
-- Single column
email TEXT NOT NULL UNIQUE

-- Composite (for duplicate prevention)
UNIQUE (appointment_id, action, calendar_type, idempotency_key)

-- Rules:
-- - Single-column UNIQUE inferred from UNIQUE keyword
-- - Composite UNIQUE declared at table level
-- - Document business reason (e.g., "prevents duplicate sync jobs")
```

---

#### 3.3.4 Check Constraints

**Pattern:** CHECK (column_name IN (value1, value2, ...)) or comparison expression

```sql
-- Enumeration check
status TEXT NOT NULL CHECK (status IN ('available', 'booked', 'cancelled'))

-- Range check
review_count INTEGER NOT NULL DEFAULT 0 CHECK (review_count >= 0)

-- Boolean check
is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))

-- Rules:
-- - Name constraints implicitly (SQLite doesn't support explicit names)
-- - Document allowed values in inline comment
-- - Use for domain validation (states, ranges, boolean flags)
-- - Always include in schema documentation
```

---

### 3.4 Index Naming

**Pattern:** `idx_[table_name]_[purpose_or_columns]`

| Index | Table | Columns | Purpose |
|---|---|---|---|
| `idx_appointments_status_date` | appointments | (status, appointment_date, start_time, id) | Availability search by status/date |
| `idx_appointments_specialty_date` | appointments | (specialty_id, appointment_date, start_time, id) | Booking by specialty |
| `idx_patient_profiles_email` | patient_profiles | (email) | Patient lookup by email |
| `idx_calendar_sync_queue_dequeue` | calendar_sync_queue | (status, scheduled_retry_at, ...) | Worker dequeue operation |
| `idx_reservations_active` | appointment_reservations | (status, expires_at, appointment_id) | Active reservation queries |

**Index Naming Rules:**
- Prefix with `idx_`
- Include table name (singular or plural consistently)
- Describe purpose or list key columns in order
- Avoid overly long names (keep < 40 characters)
- Use underscore-separated lowercase

---

### 3.5 Stored Procedure and Function Naming

**Pattern (if using SQLite with custom functions):** `[domain]_[verb]_[noun]`

Examples (hypothetical; SQLite does not support native stored procedures):
- `booking_create_reservation()`
- `calendar_sync_appointment()`
- `reminder_send_notification()`

**Rules:**
- Verb-noun pattern for clarity
- Domain prefix to group related functions
- Document parameters and return value

---

## 4. Semantic Standardization

### 4.1 Null Handling Policy

| Scenario | Rule | Example |
|---|---|---|
| **Core attributes** | NOT NULL | `provider_id`, `email`, `status` |
| **Optional attributes** | NULL allowed | `bio`, `photo_url`, `patient_notes` |
| **Audit trail** | NOT NULL; DEFAULT NOW() | `created_at` |
| **Event timestamps** | NULL allowed | `confirmation_sent_at` (null until event occurs) |
| **External IDs** | NULL allowed | `google_event_id` (null if not synced) |
| **Soft delete marker** | NOT NULL; DEFAULT 1 | `is_active` |

### 4.2 Default Values

| Column | Default | Reasoning |
|---|---|---|
| `created_at` | CURRENT_TIMESTAMP | Automatic capture |
| `updated_at` | CURRENT_TIMESTAMP | Automatic capture (requires trigger in SQLite) |
| `is_active` | 1 | Entities active by default |
| `status` | 'searching' (appointments) or 'active' (reservations) | Initial state |
| `version` | 0 | Optimistic lock start |
| `retry_count` | 0 | Initial attempt |
| `review_count` | 0 | No reviews initially |

### 4.3 Denormalization Patterns

| Denormalized Field | Source | Reason | Update Strategy |
|---|---|---|---|
| `appointments.specialty_id` | providers.specialty_id | Query efficiency (avoid joins) | Maintain on appointment creation |
| `appointments.patient_*` | patient_profiles.* | Capture state at booking time | Immutable; don't update on profile changes |
| `appointment_reservations.preferred_slot_id` | appointments.id | Efficient swap lookups | Set at reservation creation |

**Denormalization Rules:**
- Only denormalize if measurable query performance improvement
- Document source table and update frequency
- Freeze denormalized data (don't update if source changes)
- Include integrity checks in application logic

### 4.4 Soft-Delete Semantics

**Pattern:** `is_active` INTEGER CHECK (is_active IN (0, 1)) NOT NULL DEFAULT 1

| Operation | SQL | Semantics |
|---|---|---|
| **Active records** | `WHERE is_active = 1` | Include in all queries by default |
| **Archived records** | `WHERE is_active = 0` | Hidden from normal operations |
| **Delete (logical)** | `UPDATE ... SET is_active = 0` | Soft delete; preserves referential integrity |
| **Delete (permanent)** | `DELETE FROM ...` | Hard delete; use sparingly for GDPR purges |

**Soft Delete Benefits:**
- Preserves historical referential integrity
- Enables undelete if needed
- Supports audit trails
- Simplifies data recovery

---

## 5. Validation Checklist

### 5.1 Column Naming Compliance

- [ ] All columns use lowercase snake_case
- [ ] Foreign keys named `[table_singular]_id`
- [ ] Timestamps end with `_at`
- [ ] Status columns use consistent naming pattern
- [ ] Boolean flags start with `is_`, `has_`, `do_`
- [ ] No SQL reserved words used
- [ ] External IDs prefixed with system name (google_, outlook_)

### 5.2 Constraint Documentation

- [ ] All CHECK constraints document allowed values
- [ ] All FOREIGN KEY relationships document cascade behavior
- [ ] All UNIQUE constraints explain duplicate prevention purpose
- [ ] All defaults documented (why this value?)
- [ ] Null/Not-Null policy documented

### 5.3 Index Naming

- [ ] All indexes prefixed with `idx_`
- [ ] Index names describe purpose or list key columns
- [ ] No index names exceed 40 characters
- [ ] Index naming consistent with query patterns they support

---

## 6. Migration and Backward Compatibility

### 6.1 Renaming Strategy

If renaming columns or tables post-deployment:

1. **Create alias table/view** with new name (SELECT * FROM old_name)
2. **Update application code** to use new names
3. **Run dual-write migration** (write to both old and new for grace period)
4. **Migrate historical data** (backfill new column from old)
5. **Remove alias/old column** (after all queries migrated)

### 6.2 Documentation Updates

When changing naming conventions:
- [ ] Update this document with new standard
- [ ] Add migration guide (from old name → new name)
- [ ] Update schema comments
- [ ] Update ERD and glossary
- [ ] Notifyall teams (data, analytics, dev)

---

## 7. Glossary of Terms

| Term | Definition | Examples |
|---|---|---|
| **Entity** | Core domain concept (table) | Appointment, Provider, Patient Profile |
| **Attribute** | Property of entity (column) | appointment_date, status, is_active |
| **Aggregate** | Denormalized summary (table) | reminder_log, booking_events |
| **State Machine** | Lifecycle tracking (column) | status, checkout_status, sync_status |
| **Soft Delete** | Logical deletion (is_active) | is_active = 0 means archived |
| **Deduplication** | Prevents duplicates (unique, idempotency_key) | reservation_token ensures 1 active per appointment |
| **Denormalization** | Redundant data for performance | specialty_id in appointments (avoid join) |

---

## 8. Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-06-22 | Initial naming conventions and semantic standards document |

