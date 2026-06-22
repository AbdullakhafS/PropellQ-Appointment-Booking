PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS specialties (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    credentials TEXT NOT NULL,
    specialty_id INTEGER NOT NULL,
    photo_url TEXT,
    review_count INTEGER NOT NULL DEFAULT 0,
    bio TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (specialty_id) REFERENCES specialties (id)
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY,
    provider_id INTEGER NOT NULL,
    specialty_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('available', 'booked', 'cancelled')),
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    appointment_timezone TEXT NOT NULL DEFAULT 'America/Chicago',
    preferred_slot_id INTEGER,
    preferred_window_expires_at TEXT,
    reservation_expires_at TEXT,
    reservation_token TEXT,
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
    version INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES providers (id),
    FOREIGN KEY (specialty_id) REFERENCES specialties (id),
    FOREIGN KEY (preferred_slot_id) REFERENCES appointments (id)
);

CREATE TABLE IF NOT EXISTS patient_profiles (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    preferred_timezone TEXT NOT NULL DEFAULT 'America/Chicago',
    reminder_channels TEXT NOT NULL DEFAULT '["sms","email"]',
    do_not_disturb INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS appointment_reservations (
    id INTEGER PRIMARY KEY,
    appointment_id INTEGER NOT NULL,
    patient_profile_id INTEGER NOT NULL,
    reservation_token TEXT NOT NULL UNIQUE,
    idempotency_key TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'confirmed', 'cancelled')),
    expires_at TEXT NOT NULL,
    preferred_slot_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TEXT,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id),
    FOREIGN KEY (patient_profile_id) REFERENCES patient_profiles (id),
    FOREIGN KEY (preferred_slot_id) REFERENCES appointments (id)
);

CREATE TABLE IF NOT EXISTS booking_events (
    id INTEGER PRIMARY KEY,
    reservation_id INTEGER,
    appointment_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reservation_id) REFERENCES appointment_reservations (id),
    FOREIGN KEY (appointment_id) REFERENCES appointments (id)
);

CREATE TABLE IF NOT EXISTS confirmation_deliveries (
    id INTEGER PRIMARY KEY,
    appointment_id INTEGER NOT NULL,
    recipient_email TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'sent', 'failed')),
    retry_count INTEGER NOT NULL DEFAULT 0,
    template_version TEXT NOT NULL DEFAULT 'v1',
    attachment_path TEXT,
    external_message_id TEXT,
    failure_reason TEXT,
    queued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id)
);

CREATE TABLE IF NOT EXISTS reminder_log (
    id INTEGER PRIMARY KEY,
    appointment_id INTEGER NOT NULL,
    patient_profile_id INTEGER NOT NULL,
    reminder_type TEXT NOT NULL CHECK (reminder_type IN ('48h', '24h', '2h', 'swap')),
    channel TEXT NOT NULL CHECK (channel IN ('sms', 'email')),
    delivery_status TEXT NOT NULL CHECK (delivery_status IN ('queued', 'sent', 'failed', 'skipped')),
    retry_count INTEGER NOT NULL DEFAULT 0,
    sent_at TEXT,
    external_message_id TEXT,
    failure_reason TEXT,
    correlation_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id),
    FOREIGN KEY (patient_profile_id) REFERENCES patient_profiles (id)
);

CREATE TABLE IF NOT EXISTS preferred_slot_swap_history (
    id INTEGER PRIMARY KEY,
    appointment_id INTEGER NOT NULL,
    original_slot_id INTEGER NOT NULL,
    new_slot_id INTEGER,
    status TEXT NOT NULL CHECK (status IN ('completed', 'skipped', 'failed')),
    reason_code TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id),
    FOREIGN KEY (original_slot_id) REFERENCES appointments (id),
    FOREIGN KEY (new_slot_id) REFERENCES appointments (id)
);

CREATE TABLE IF NOT EXISTS patient_sessions (
    id INTEGER PRIMARY KEY,
    patient_profile_id INTEGER NOT NULL,
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
    FOREIGN KEY (patient_profile_id) REFERENCES patient_profiles (id)
);

CREATE TABLE IF NOT EXISTS calendar_sync_queue (
    id INTEGER PRIMARY KEY,
    appointment_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete', 'pull_reconcile')),
    calendar_type TEXT NOT NULL CHECK (calendar_type IN ('google', 'outlook')),
    idempotency_key TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    scheduled_retry_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'synced', 'failed', 'manual_review')),
    last_error TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id),
    UNIQUE (appointment_id, action, calendar_type, idempotency_key)
);

CREATE TABLE IF NOT EXISTS calendar_sync_audit (
    id INTEGER PRIMARY KEY,
    appointment_id INTEGER NOT NULL,
    calendar_type TEXT NOT NULL CHECK (calendar_type IN ('google', 'outlook')),
    external_event_id TEXT,
    action TEXT NOT NULL,
    result TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id)
);

CREATE TABLE IF NOT EXISTS manual_review_queue (
    id INTEGER PRIMARY KEY,
    appointment_id INTEGER NOT NULL,
    review_type TEXT NOT NULL CHECK (review_type IN ('calendar_conflict', 'external_reschedule', 'sync_failure')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    details_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id)
);

CREATE TABLE IF NOT EXISTS provider_calendar_state (
    id INTEGER PRIMARY KEY,
    provider_id INTEGER NOT NULL,
    calendar_type TEXT NOT NULL CHECK (calendar_type IN ('google', 'outlook')),
    last_sync_watermark TEXT,
    webhook_enabled INTEGER NOT NULL DEFAULT 0,
    webhook_secret TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES providers (id)
);

CREATE TABLE IF NOT EXISTS provider_external_events (
    id INTEGER PRIMARY KEY,
    appointment_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,
    calendar_type TEXT NOT NULL CHECK (calendar_type IN ('google', 'outlook')),
    external_event_id TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deleted', 'rescheduled')),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id),
    FOREIGN KEY (provider_id) REFERENCES providers (id)
);

CREATE INDEX IF NOT EXISTS idx_appointments_status_date
    ON appointments (status, appointment_date, start_time, id);

CREATE INDEX IF NOT EXISTS idx_appointments_specialty_date
    ON appointments (specialty_id, appointment_date, start_time, id);

CREATE INDEX IF NOT EXISTS idx_appointments_provider_date
    ON appointments (provider_id, appointment_date, start_time, id);

CREATE INDEX IF NOT EXISTS idx_appointments_checkout_status
    ON appointments (checkout_status, reservation_expires_at, appointment_date, start_time);

CREATE INDEX IF NOT EXISTS idx_appointments_sync_status
    ON appointments (sync_status, last_synced_at, google_event_id, outlook_event_id);

CREATE INDEX IF NOT EXISTS idx_appointments_preferred_window
    ON appointments (preferred_window_expires_at, preferred_slot_id, status);

CREATE INDEX IF NOT EXISTS idx_providers_name
    ON providers (name);

CREATE INDEX IF NOT EXISTS idx_specialties_name
    ON specialties (name);

CREATE INDEX IF NOT EXISTS idx_patient_profiles_email
    ON patient_profiles (email);

CREATE INDEX IF NOT EXISTS idx_reservations_active
    ON appointment_reservations (status, expires_at, appointment_id);

CREATE INDEX IF NOT EXISTS idx_confirmation_deliveries_status
    ON confirmation_deliveries (status, queued_at, appointment_id);

CREATE INDEX IF NOT EXISTS idx_reminder_log_lookup
    ON reminder_log (appointment_id, patient_profile_id, reminder_type, channel, delivery_status, created_at);

CREATE INDEX IF NOT EXISTS idx_swap_history_lookup
    ON preferred_slot_swap_history (appointment_id, status, created_at);

CREATE INDEX IF NOT EXISTS idx_patient_sessions_auth
    ON patient_sessions (patient_profile_id, google_auth_status, outlook_auth_status);

CREATE INDEX IF NOT EXISTS idx_calendar_sync_queue_dequeue
    ON calendar_sync_queue (status, scheduled_retry_at, calendar_type, retry_count);

CREATE INDEX IF NOT EXISTS idx_calendar_sync_audit_lookup
    ON calendar_sync_audit (appointment_id, calendar_type, created_at);

CREATE INDEX IF NOT EXISTS idx_manual_review_queue_status
    ON manual_review_queue (status, review_type, created_at);

CREATE INDEX IF NOT EXISTS idx_provider_external_events_lookup
    ON provider_external_events (calendar_type, external_event_id, status, updated_at);
