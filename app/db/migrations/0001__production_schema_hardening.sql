-- Production Schema for PropellQ Appointment Booking Platform
-- Version: 1.0
-- Date: 2026-06-22
-- Status: Production
-- 
-- DESIGN PRINCIPLES:
-- 1. Explicit PK/FK/Check/Unique constraints enforce data integrity at database level
-- 2. Uniqueness constraints prevent duplicates for business-critical fields
-- 3. Check constraints enforce domain-valid states
-- 4. Soft-delete pattern (is_active) preserves historical referential integrity
-- 5. Denormalization (patient fields, specialty_id) optimizes critical query paths
-- 6. Self-referential relationships enable slot swapping and preference tracking
--
-- FOREIGN KEY ENFORCEMENT:
-- Foreign keys are enabled globally at pragma level. All FK relationships use
-- RESTRICT (default SQLite behavior) unless cascade is specified.
--

PRAGMA foreign_keys = ON;

-- ============================================================================
-- REFERENCE DATA DOMAIN - Specialties and Provider Profiles
-- ============================================================================

-- Table: specialties
-- Purpose: Clinical specialties (Cardiology, Dermatology, etc.)
-- Cardinality: 1 Specialty → Many Providers, Many Appointments
-- Constraints:
--   - PK: id (auto-increment)
--   - UNIQUE: name (prevent duplicate specialty definitions)
--   - is_active (soft-delete support)
CREATE TABLE IF NOT EXISTS specialties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: providers
-- Purpose: Clinician/provider information and credentials
-- Cardinality: 1 Provider → Many Appointments
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: specialty_id → specialties.id (provider belongs to specialty)
--   - is_active (soft-delete support)
CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    credentials TEXT NOT NULL,
    specialty_id INTEGER NOT NULL,
    photo_url TEXT,
    review_count INTEGER NOT NULL DEFAULT 0 CHECK (review_count >= 0),
    bio TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (specialty_id) REFERENCES specialties (id) ON DELETE RESTRICT
);

-- ============================================================================
-- BOOKING CORE DOMAIN - Appointments and Reservations
-- ============================================================================

-- Table: appointments
-- Purpose: Appointment slots, booking state, provider integration
-- Cardinality: 1 Appointment → 1 Provider, Many Reservations
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: provider_id → providers.id
--   - FK: specialty_id → specialties.id (denormalized for performance)
--   - FK: preferred_slot_id → appointments.id (self-ref for slot swaps)
--   - CHECK: status IN ('available', 'booked', 'cancelled')
--   - CHECK: checkout_status IN ('searching', 'reserved', 'confirmed', 'expired', 'cancelled')
--   - CHECK: sync_status IN ('not_connected', 'pending', 'synced', 'failed', 'manual_review', 'revoked')
--   - UNIQUE: reservation_token (idempotency key for reservation claims)
--   - version (optimistic lock for concurrent updates)
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL,
    specialty_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('available', 'booked', 'cancelled')),
    duration_minutes INTEGER NOT NULL DEFAULT 30 CHECK (duration_minutes > 0),
    appointment_timezone TEXT NOT NULL DEFAULT 'America/Chicago',
    preferred_slot_id INTEGER,
    preferred_window_expires_at TEXT,
    reservation_expires_at TEXT,
    reservation_token TEXT UNIQUE,
    patient_first_name TEXT,
    patient_last_name TEXT,
    patient_email TEXT,
    patient_phone TEXT,
    patient_timezone TEXT,
    patient_notes TEXT,
    checkout_status TEXT NOT NULL DEFAULT 'searching' CHECK (checkout_status IN ('searching', 'reserved', 'confirmed', 'expired', 'cancelled')),
    confirmation_sent_at TEXT,
    reminder_sent_48h_at TEXT,
    reminder_sent_24h_at TEXT,
    reminder_sent_2h_at TEXT,
    google_event_id TEXT,
    outlook_event_id TEXT,
    last_synced_at TEXT,
    sync_status TEXT NOT NULL DEFAULT 'not_connected' CHECK (sync_status IN ('not_connected', 'pending', 'synced', 'failed', 'manual_review', 'revoked')),
    version INTEGER NOT NULL DEFAULT 0 CHECK (version >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE RESTRICT,
    FOREIGN KEY (specialty_id) REFERENCES specialties (id) ON DELETE RESTRICT,
    FOREIGN KEY (preferred_slot_id) REFERENCES appointments (id) ON DELETE SET NULL
);

-- Table: patient_profiles
-- Purpose: Patient master identity, contact, and notification preferences
-- Cardinality: 1 Patient Profile → Many Reservations, 1 Patient Session
-- Constraints:
--   - PK: id (auto-increment)
--   - UNIQUE: email (prevent duplicate patient identities; business requirement)
--   - UNIQUE: phone (prevent duplicate patient identities; business requirement)
--   - do_not_disturb (binary flag)
--   - Composite natural key: (email, phone) for uniqueness validation
CREATE TABLE IF NOT EXISTS patient_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL UNIQUE,
    preferred_timezone TEXT NOT NULL DEFAULT 'America/Chicago',
    reminder_channels TEXT NOT NULL DEFAULT '["sms","email"]',
    do_not_disturb INTEGER NOT NULL DEFAULT 0 CHECK (do_not_disturb IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: appointment_reservations
-- Purpose: Captures reservation state, idempotency, and patient binding
-- Cardinality: 1 Appointment Reservation → 1 Appointment, 1 Patient Profile
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: appointment_id → appointments.id
--   - FK: patient_profile_id → patient_profiles.id
--   - FK: preferred_slot_id → appointments.id (nullable for slot swaps)
--   - UNIQUE: reservation_token (idempotency key; prevents duplicate reservations)
--   - status CHECK
--   - Composite natural key: (appointment_id, patient_profile_id) for duplicate prevention
--     Enforced via application logic and idempotency_key validation
CREATE TABLE IF NOT EXISTS appointment_reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    patient_profile_id INTEGER NOT NULL,
    reservation_token TEXT NOT NULL UNIQUE,
    idempotency_key TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'confirmed', 'cancelled')),
    expires_at TEXT NOT NULL,
    preferred_slot_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TEXT,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE RESTRICT,
    FOREIGN KEY (patient_profile_id) REFERENCES patient_profiles (id) ON DELETE RESTRICT,
    FOREIGN KEY (preferred_slot_id) REFERENCES appointments (id) ON DELETE SET NULL
);

-- ============================================================================
-- COMMUNICATION DOMAIN - Events, Confirmations, Reminders
-- ============================================================================

-- Table: booking_events
-- Purpose: Event log for booking state transitions and diagnostics
-- Cardinality: 1 Booking Event → 1 Appointment
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: appointment_id → appointments.id (required)
--   - FK: reservation_id → appointment_reservations.id (optional, nullable)
--   - event_type NOT NULL (domain event identifier)
--   - correlation_id NOT NULL (distributed tracing)
CREATE TABLE IF NOT EXISTS booking_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER,
    appointment_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reservation_id) REFERENCES appointment_reservations (id) ON DELETE SET NULL,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE
);

-- Table: confirmation_deliveries
-- Purpose: Email delivery tracking for booking confirmations
-- Cardinality: 1 Confirmation Delivery → 1 Appointment
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: appointment_id → appointments.id
--   - status CHECK ('queued', 'sent', 'failed')
--   - retry_count >= 0
CREATE TABLE IF NOT EXISTS confirmation_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    recipient_email TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'sent', 'failed')),
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    template_version TEXT NOT NULL DEFAULT 'v1',
    attachment_path TEXT,
    external_message_id TEXT,
    failure_reason TEXT,
    queued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE
);

-- Table: reminder_log
-- Purpose: Track reminder notifications sent to patients
-- Cardinality: 1 Reminder Log → 1 Appointment, 1 Patient Profile
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: appointment_id → appointments.id
--   - FK: patient_profile_id → patient_profiles.id
--   - reminder_type CHECK
--   - channel CHECK
--   - delivery_status CHECK
--   - correlation_id (for distributed tracing)
CREATE TABLE IF NOT EXISTS reminder_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    patient_profile_id INTEGER NOT NULL,
    reminder_type TEXT NOT NULL CHECK (reminder_type IN ('48h', '24h', '2h', 'swap')),
    channel TEXT NOT NULL CHECK (channel IN ('sms', 'email')),
    delivery_status TEXT NOT NULL CHECK (delivery_status IN ('queued', 'sent', 'failed', 'skipped')),
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    sent_at TEXT,
    external_message_id TEXT,
    failure_reason TEXT,
    correlation_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE,
    FOREIGN KEY (patient_profile_id) REFERENCES patient_profiles (id) ON DELETE CASCADE
);

-- ============================================================================
-- SLOT OPTIMIZATION DOMAIN - Slot Swaps and Preferences
-- ============================================================================

-- Table: preferred_slot_swap_history
-- Purpose: Track patient-initiated slot changes and swap outcomes
-- Cardinality: 1 Preferred Slot Swap History → 1 Appointment
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: appointment_id → appointments.id (original booked appointment)
--   - FK: original_slot_id → appointments.id
--   - FK: new_slot_id → appointments.id (nullable if swap failed)
--   - status CHECK
--   - reason_code NOT NULL
--   - correlation_id (for distributed tracing)
CREATE TABLE IF NOT EXISTS preferred_slot_swap_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    original_slot_id INTEGER NOT NULL,
    new_slot_id INTEGER,
    status TEXT NOT NULL CHECK (status IN ('completed', 'skipped', 'failed')),
    reason_code TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE,
    FOREIGN KEY (original_slot_id) REFERENCES appointments (id) ON DELETE RESTRICT,
    FOREIGN KEY (new_slot_id) REFERENCES appointments (id) ON DELETE SET NULL
);

-- ============================================================================
-- CALENDAR INTEGRATION DOMAIN - OAuth Sessions and Sync Operations
-- ============================================================================

-- Table: patient_sessions
-- Purpose: OAuth credentials and calendar integration state per patient
-- Cardinality: 1 Patient Session → 1 Patient Profile
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: patient_profile_id → patient_profiles.id
--   - google_auth_status CHECK
--   - outlook_auth_status CHECK
--   - Tokens are encrypted in transit (application responsibility)
CREATE TABLE IF NOT EXISTS patient_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_profile_id INTEGER NOT NULL UNIQUE,
    google_refresh_token TEXT,
    google_access_token_expires_at TEXT,
    google_calendar_id TEXT,
    google_auth_status TEXT NOT NULL DEFAULT 'revoked' CHECK (google_auth_status IN ('revoked', 'authorized', 'error')),
    outlook_refresh_token TEXT,
    outlook_access_token_expires_at TEXT,
    outlook_calendar_id TEXT,
    outlook_auth_status TEXT NOT NULL DEFAULT 'revoked' CHECK (outlook_auth_status IN ('revoked', 'authorized', 'error')),
    oauth_state_nonce TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_profile_id) REFERENCES patient_profiles (id) ON DELETE CASCADE
);

-- Table: calendar_sync_queue
-- Purpose: Queue for asynchronous calendar sync operations
-- Cardinality: 1 Calendar Sync Queue → 1 Appointment
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: appointment_id → appointments.id
--   - action CHECK
--   - calendar_type CHECK
--   - idempotency_key NOT NULL
--   - status CHECK
--   - UNIQUE (appointment_id, action, calendar_type, idempotency_key)
--     Prevents duplicate sync jobs for same appointment/action/calendar combination
CREATE TABLE IF NOT EXISTS calendar_sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete', 'pull_reconcile')),
    calendar_type TEXT NOT NULL CHECK (calendar_type IN ('google', 'outlook')),
    idempotency_key TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    scheduled_retry_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'synced', 'failed', 'manual_review')),
    last_error TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE,
    UNIQUE (appointment_id, action, calendar_type, idempotency_key)
);

-- Table: calendar_sync_audit
-- Purpose: Immutable audit trail of calendar sync operations
-- Cardinality: 1 Calendar Sync Audit → 1 Appointment
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: appointment_id → appointments.id
--   - calendar_type CHECK
--   - action NOT NULL
--   - result NOT NULL (success/failure outcome)
CREATE TABLE IF NOT EXISTS calendar_sync_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    calendar_type TEXT NOT NULL CHECK (calendar_type IN ('google', 'outlook')),
    external_event_id TEXT,
    action TEXT NOT NULL,
    result TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE
);

-- Table: manual_review_queue
-- Purpose: Escalation queue for sync conflicts and exceptional conditions
-- Cardinality: 1 Manual Review Queue → 1 Appointment
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: appointment_id → appointments.id
--   - review_type CHECK
--   - status CHECK
CREATE TABLE IF NOT EXISTS manual_review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    review_type TEXT NOT NULL CHECK (review_type IN ('calendar_conflict', 'external_reschedule', 'sync_failure')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    details_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE
);

-- Table: provider_calendar_state
-- Purpose: Provider calendar integration state and sync metadata
-- Cardinality: 1 Provider Calendar State → 1 Provider
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: provider_id → providers.id
--   - calendar_type CHECK
--   - webhook_enabled (binary flag)
CREATE TABLE IF NOT EXISTS provider_calendar_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL,
    calendar_type TEXT NOT NULL CHECK (calendar_type IN ('google', 'outlook')),
    last_sync_watermark TEXT,
    webhook_enabled INTEGER NOT NULL DEFAULT 0 CHECK (webhook_enabled IN (0, 1)),
    webhook_secret TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE CASCADE,
    UNIQUE (provider_id, calendar_type)
);

-- Table: provider_external_events
-- Purpose: Snapshot of external calendar events blocking appointment slots
-- Cardinality: 1 Provider External Event → 1 Appointment, 1 Provider
-- Constraints:
--   - PK: id (auto-increment)
--   - FK: appointment_id → appointments.id
--   - FK: provider_id → providers.id
--   - calendar_type CHECK
--   - external_event_id NOT NULL
--   - status CHECK
CREATE TABLE IF NOT EXISTS provider_external_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,
    calendar_type TEXT NOT NULL CHECK (calendar_type IN ('google', 'outlook')),
    external_event_id TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deleted', 'rescheduled')),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE,
    FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE CASCADE,
    UNIQUE (calendar_type, external_event_id, provider_id)
);

-- ============================================================================
-- INDEXES - Performance Optimization for Critical Query Paths
-- ============================================================================

-- Appointment availability lookups (hot path)
CREATE INDEX IF NOT EXISTS idx_appointments_status_date
    ON appointments (status, appointment_date, start_time, id);

CREATE INDEX IF NOT EXISTS idx_appointments_specialty_date
    ON appointments (specialty_id, appointment_date, start_time, id);

CREATE INDEX IF NOT EXISTS idx_appointments_provider_date
    ON appointments (provider_id, appointment_date, start_time, id);

-- Checkout and reservation state lookups
CREATE INDEX IF NOT EXISTS idx_appointments_checkout_status
    ON appointments (checkout_status, reservation_expires_at, appointment_date, start_time);

-- Calendar sync state lookups
CREATE INDEX IF NOT EXISTS idx_appointments_sync_status
    ON appointments (sync_status, last_synced_at, google_event_id, outlook_event_id);

-- Slot preference and swap lookups
CREATE INDEX IF NOT EXISTS idx_appointments_preferred_window
    ON appointments (preferred_window_expires_at, preferred_slot_id, status);

-- Reference data lookups
CREATE INDEX IF NOT EXISTS idx_providers_name
    ON providers (name);

CREATE INDEX IF NOT EXISTS idx_providers_specialty
    ON providers (specialty_id, is_active);

CREATE INDEX IF NOT EXISTS idx_specialties_name
    ON specialties (name);

-- Patient lookups
CREATE INDEX IF NOT EXISTS idx_patient_profiles_email
    ON patient_profiles (email);

CREATE INDEX IF NOT EXISTS idx_patient_profiles_phone
    ON patient_profiles (phone);

-- Reservation state queries
CREATE INDEX IF NOT EXISTS idx_reservations_active
    ON appointment_reservations (status, expires_at, appointment_id);

CREATE INDEX IF NOT EXISTS idx_reservations_patient
    ON appointment_reservations (patient_profile_id, status, created_at);

-- Confirmation delivery queue
CREATE INDEX IF NOT EXISTS idx_confirmation_deliveries_status
    ON confirmation_deliveries (status, queued_at, appointment_id);

-- Reminder log queries
CREATE INDEX IF NOT EXISTS idx_reminder_log_lookup
    ON reminder_log (appointment_id, patient_profile_id, reminder_type, channel, delivery_status, created_at);

CREATE INDEX IF NOT EXISTS idx_reminder_log_pending
    ON reminder_log (delivery_status, reminder_type, created_at);

-- Slot swap history
CREATE INDEX IF NOT EXISTS idx_swap_history_lookup
    ON preferred_slot_swap_history (appointment_id, status, created_at);

-- Patient session lookups
CREATE INDEX IF NOT EXISTS idx_patient_sessions_auth
    ON patient_sessions (patient_profile_id, google_auth_status, outlook_auth_status);

-- Calendar sync queue (dequeue operations)
CREATE INDEX IF NOT EXISTS idx_calendar_sync_queue_dequeue
    ON calendar_sync_queue (status, scheduled_retry_at, calendar_type, retry_count);

CREATE INDEX IF NOT EXISTS idx_calendar_sync_queue_appointment
    ON calendar_sync_queue (appointment_id, status, created_at);

-- Calendar audit trails
CREATE INDEX IF NOT EXISTS idx_calendar_sync_audit_lookup
    ON calendar_sync_audit (appointment_id, calendar_type, created_at);

-- Manual review escalations
CREATE INDEX IF NOT EXISTS idx_manual_review_queue_status
    ON manual_review_queue (status, review_type, created_at);

-- Provider external events lookups
CREATE INDEX IF NOT EXISTS idx_provider_external_events_lookup
    ON provider_external_events (calendar_type, external_event_id, status, updated_at);

CREATE INDEX IF NOT EXISTS idx_provider_external_events_appointment
    ON provider_external_events (appointment_id, provider_id, status);

-- Booking events audit trail
CREATE INDEX IF NOT EXISTS idx_booking_events_appointment
    ON booking_events (appointment_id, event_type, created_at);

CREATE INDEX IF NOT EXISTS idx_booking_events_correlation
    ON booking_events (correlation_id, created_at);

-- Provider calendar state
CREATE INDEX IF NOT EXISTS idx_provider_calendar_state_provider
    ON provider_calendar_state (provider_id, calendar_type);

