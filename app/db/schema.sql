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

CREATE TABLE IF NOT EXISTS lifecycle_policy_versions (
    id INTEGER PRIMARY KEY,
    policy_name TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('archive', 'purge')),
    retention_days INTEGER NOT NULL,
    archive_after_days INTEGER NOT NULL DEFAULT 0,
    immutable_retention_days INTEGER NOT NULL DEFAULT 0,
    timezone_name TEXT NOT NULL DEFAULT 'UTC',
    owner_email TEXT NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'approved' CHECK (approval_status IN ('draft', 'pending', 'approved', 'rejected')),
    approved_by TEXT,
    effective_from TEXT NOT NULL,
    version_label TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (policy_name, version_label)
);

CREATE TABLE IF NOT EXISTS lifecycle_subjects (
    id INTEGER PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    record_key TEXT NOT NULL,
    record_type TEXT NOT NULL DEFAULT 'record',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    archive_after_at TEXT NOT NULL,
    purge_after_at TEXT NOT NULL,
    immutable_until TEXT NOT NULL,
    archive_status TEXT NOT NULL DEFAULT 'active' CHECK (archive_status IN ('active', 'archived', 'purged', 'held')),
    legal_hold INTEGER NOT NULL DEFAULT 0,
    hold_reason TEXT,
    hold_expires_at TEXT,
    policy_version TEXT NOT NULL,
    archived_at TEXT,
    purged_at TEXT,
    archive_location TEXT,
    retrieval_role TEXT,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (dataset_name, record_key)
);

CREATE TABLE IF NOT EXISTS lifecycle_archive_entries (
    id INTEGER PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    record_key TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    archived_at TEXT NOT NULL,
    retention_expires_at TEXT NOT NULL,
    archive_checksum TEXT NOT NULL,
    retrieval_allowed_roles TEXT NOT NULL DEFAULT '["compliance", "auditor"]',
    retrieved_at TEXT,
    retrieval_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (dataset_name, record_key)
);

CREATE TABLE IF NOT EXISTS lifecycle_execution_runs (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE,
    job_name TEXT NOT NULL,
    dataset_name TEXT,
    policy_version TEXT,
    dry_run INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'partial')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    operator_identity TEXT NOT NULL,
    retries INTEGER NOT NULL DEFAULT 0,
    backoff_seconds INTEGER NOT NULL DEFAULT 0,
    details_json TEXT
);

CREATE TABLE IF NOT EXISTS lifecycle_execution_events (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('archive', 'purge', 'hold_skip', 'immutability_block', 'retrieval', 'retry', 'dead_letter', 'alert')),
    dataset_name TEXT NOT NULL,
    record_key TEXT,
    status TEXT NOT NULL CHECK (status IN ('success', 'skipped', 'blocked', 'failed', 'retried')),
    reason TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lifecycle_alerts (
    id INTEGER PRIMARY KEY,
    run_id TEXT,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    backoff_seconds INTEGER NOT NULL DEFAULT 0,
    incident_target TEXT,
    runbook_link TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_quality_rules (
    id INTEGER PRIMARY KEY,
    rule_code TEXT NOT NULL UNIQUE,
    domain_name TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('completeness', 'validity', 'duplicate', 'consistency', 'referential')),
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    enforcement_mode TEXT NOT NULL DEFAULT 'observe' CHECK (enforcement_mode IN ('observe', 'warn', 'block')),
    owner_team TEXT NOT NULL,
    rationale TEXT NOT NULL,
    version_label TEXT NOT NULL,
    runbook_link TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (domain_name, rule_name, version_label)
);

CREATE TABLE IF NOT EXISTS data_quality_runs (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE,
    scope_name TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    enforcement_mode TEXT NOT NULL CHECK (enforcement_mode IN ('observe', 'warn', 'block')),
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'blocked', 'failed')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    evaluated_records INTEGER NOT NULL DEFAULT 0,
    violation_count INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    critical_count INTEGER NOT NULL DEFAULT 0,
    blocked_count INTEGER NOT NULL DEFAULT 0,
    report_path TEXT,
    trend_date TEXT NOT NULL,
    owner_team TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_quality_violations (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    rule_code TEXT NOT NULL,
    domain_name TEXT NOT NULL,
    record_key TEXT,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    message TEXT NOT NULL,
    details_json TEXT,
    owner_team TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'triaged', 'resolved', 'ignored')),
    detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    FOREIGN KEY (run_id) REFERENCES data_quality_runs (run_id) ON DELETE CASCADE,
    FOREIGN KEY (rule_code) REFERENCES data_quality_rules (rule_code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS data_quality_quarantine (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    domain_name TEXT NOT NULL,
    record_key TEXT,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    quarantine_status TEXT NOT NULL DEFAULT 'flagged' CHECK (quarantine_status IN ('flagged', 'reviewing', 'cleared', 'blocked')),
    reason TEXT NOT NULL,
    payload_json TEXT,
    owner_team TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    triaged_at TEXT,
    triage_notes TEXT,
    FOREIGN KEY (run_id) REFERENCES data_quality_runs (run_id) ON DELETE CASCADE
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

CREATE INDEX IF NOT EXISTS idx_lifecycle_subjects_due_archive
    ON lifecycle_subjects (dataset_name, archive_status, archive_after_at, legal_hold, policy_version);

CREATE INDEX IF NOT EXISTS idx_lifecycle_subjects_due_purge
    ON lifecycle_subjects (dataset_name, archive_status, purge_after_at, legal_hold, immutable_until);

CREATE INDEX IF NOT EXISTS idx_lifecycle_archive_lookup
    ON lifecycle_archive_entries (dataset_name, record_key, archived_at);

CREATE INDEX IF NOT EXISTS idx_lifecycle_runs_status
    ON lifecycle_execution_runs (job_name, status, started_at);

CREATE INDEX IF NOT EXISTS idx_lifecycle_events_run
    ON lifecycle_execution_events (run_id, event_type, status, created_at);

CREATE INDEX IF NOT EXISTS idx_data_quality_runs_stage
    ON data_quality_runs (stage_name, status, trend_date, created_at);

CREATE INDEX IF NOT EXISTS idx_data_quality_violations_rule
    ON data_quality_violations (rule_code, severity, status, detected_at);

-- ============================================================
-- EP-003: Clinical Intelligence Platform
-- ============================================================

CREATE TABLE IF NOT EXISTS clinical_documents (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx')),
    storage_path TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    upload_timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    uploaded_by TEXT NOT NULL DEFAULT 'patient',
    FOREIGN KEY (patient_id) REFERENCES patient_profiles (id)
);

CREATE TABLE IF NOT EXISTS clinical_document_processing (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'processing', 'complete', 'failed')),
    review_required INTEGER NOT NULL DEFAULT 0,
    failure_reason TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES clinical_documents (id)
);

CREATE TABLE IF NOT EXISTS clinical_extracted_entities (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('medication', 'allergy', 'diagnosis', 'date', 'other')),
    entity_value TEXT NOT NULL,
    normalized_value TEXT,
    unit TEXT,
    date_context TEXT,
    confidence_score REAL NOT NULL DEFAULT 0.0,
    source_text TEXT,
    extraction_model TEXT NOT NULL DEFAULT 'rule_engine_v1',
    extracted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES clinical_documents (id),
    FOREIGN KEY (patient_id) REFERENCES patient_profiles (id)
);

CREATE TABLE IF NOT EXISTS clinical_profile_elements (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    element_type TEXT NOT NULL CHECK (element_type IN ('medication', 'allergy', 'diagnosis', 'demographics', 'intake_field', 'date')),
    element_value TEXT NOT NULL,
    normalized_value TEXT,
    source_type TEXT NOT NULL CHECK (source_type IN ('intake', 'document')),
    source_id INTEGER NOT NULL,
    confidence_score REAL,
    extracted_at TEXT,
    aggregated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (patient_id) REFERENCES patient_profiles (id)
);

CREATE TABLE IF NOT EXISTS clinical_medication_conflicts (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    conflict_type TEXT NOT NULL CHECK (conflict_type IN ('drug_drug_interaction', 'duplicate_therapy')),
    severity TEXT NOT NULL CHECK (severity IN ('high', 'medium', 'low')),
    medication_a TEXT NOT NULL,
    medication_b TEXT NOT NULL,
    clinical_impact TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'rule_engine_v1',
    detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    resolution_note TEXT,
    FOREIGN KEY (patient_id) REFERENCES patient_profiles (id)
);

CREATE INDEX IF NOT EXISTS idx_clinical_documents_patient
    ON clinical_documents (patient_id, upload_timestamp);

CREATE INDEX IF NOT EXISTS idx_clinical_doc_processing_status
    ON clinical_document_processing (status, document_id);

CREATE INDEX IF NOT EXISTS idx_clinical_entities_patient_type
    ON clinical_extracted_entities (patient_id, entity_type, extracted_at);

CREATE INDEX IF NOT EXISTS idx_clinical_profile_elements_patient
    ON clinical_profile_elements (patient_id, element_type, is_active);

CREATE INDEX IF NOT EXISTS idx_clinical_conflicts_patient
    ON clinical_medication_conflicts (patient_id, severity, detected_at);

-- ============================================================
-- EP-003: Coding Engine (TASK-025 through TASK-030)
-- ============================================================

CREATE TABLE IF NOT EXISTS clinical_allergy_drug_conflicts (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    allergen TEXT NOT NULL,
    allergen_normalized TEXT NOT NULL,
    medication TEXT NOT NULL,
    medication_normalized TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('high', 'medium', 'low')),
    clinical_impact TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'rule_engine_v1',
    detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    resolution_note TEXT,
    FOREIGN KEY (patient_id) REFERENCES patient_profiles (id)
);

CREATE TABLE IF NOT EXISTS clinical_code_suggestions (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    code_type TEXT NOT NULL CHECK (code_type IN ('icd10', 'cpt')),
    code TEXT NOT NULL,
    description TEXT NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    evidence_text TEXT,
    review_required INTEGER NOT NULL DEFAULT 0 CHECK (review_required IN (0, 1)),
    auto_accepted INTEGER NOT NULL DEFAULT 0 CHECK (auto_accepted IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected', 'overridden')),
    reviewer_id TEXT,
    reviewed_at TEXT,
    override_code TEXT,
    override_description TEXT,
    rejection_reason TEXT,
    source TEXT NOT NULL DEFAULT 'rule_engine_v1',
    suggested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient_profiles (id)
);

CREATE TABLE IF NOT EXISTS clinical_code_review_audit (
    id INTEGER PRIMARY KEY,
    suggestion_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('accept', 'reject', 'override')),
    reviewer_id TEXT NOT NULL,
    override_code TEXT,
    override_description TEXT,
    rejection_reason TEXT,
    previous_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    decision_metadata TEXT,
    acted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (suggestion_id) REFERENCES clinical_code_suggestions (id)
);

CREATE TABLE IF NOT EXISTS clinical_threshold_config (
    id INTEGER PRIMARY KEY,
    code_type TEXT NOT NULL UNIQUE CHECK (code_type IN ('icd10', 'cpt', 'all')),
    threshold_value REAL NOT NULL CHECK (threshold_value >= 0.0 AND threshold_value <= 1.0),
    updated_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clinical_threshold_history (
    id INTEGER PRIMARY KEY,
    code_type TEXT NOT NULL,
    old_value REAL,
    new_value REAL NOT NULL,
    changed_by TEXT NOT NULL,
    changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clinical_conflict_resolutions (
    id INTEGER PRIMARY KEY,
    conflict_id INTEGER NOT NULL,
    conflict_table TEXT NOT NULL DEFAULT 'clinical_medication_conflicts',
    patient_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('resolve', 'merge', 'discard')),
    chosen_value TEXT,
    merge_value TEXT,
    reviewer_id TEXT NOT NULL,
    resolution_note TEXT,
    version_a_snapshot TEXT,
    version_b_snapshot TEXT,
    resolved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient_profiles (id)
);

CREATE INDEX IF NOT EXISTS idx_allergy_drug_conflicts_patient
    ON clinical_allergy_drug_conflicts (patient_id, severity, detected_at);

CREATE INDEX IF NOT EXISTS idx_code_suggestions_patient_type
    ON clinical_code_suggestions (patient_id, code_type, status, review_required);

CREATE INDEX IF NOT EXISTS idx_code_suggestions_review_queue
    ON clinical_code_suggestions (review_required, status, suggested_at);

CREATE INDEX IF NOT EXISTS idx_conflict_resolutions_conflict
    ON clinical_conflict_resolutions (conflict_id, conflict_table);

CREATE INDEX IF NOT EXISTS idx_data_quality_violations_domain
    ON data_quality_violations (domain_name, severity, detected_at);

CREATE INDEX IF NOT EXISTS idx_data_quality_quarantine_status
    ON data_quality_quarantine (quarantine_status, severity, created_at);

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

-- ============================================================================
-- BACKUP AND RESTORE AUTOMATION SCHEMA (TASK-108)
-- ============================================================================

CREATE TABLE IF NOT EXISTS backup_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_name TEXT NOT NULL UNIQUE,
    dataset_name TEXT NOT NULL,
    backup_type TEXT NOT NULL CHECK (backup_type IN ('full', 'incremental')),
    schedule_cron TEXT NOT NULL,
    retention_days INTEGER NOT NULL CHECK (retention_days > 0),
    retention_tiers TEXT NOT NULL DEFAULT '{"hot": 7, "warm": 30, "cold": 365}',
    encryption_enabled INTEGER NOT NULL DEFAULT 1 CHECK (encryption_enabled IN (0, 1)),
    encryption_algorithm TEXT NOT NULL DEFAULT 'AES-256-GCM',
    kms_key_id TEXT,
    compression_enabled INTEGER NOT NULL DEFAULT 1 CHECK (compression_enabled IN (0, 1)),
    compression_algorithm TEXT NOT NULL DEFAULT 'zstd',
    storage_location TEXT NOT NULL,
    access_role_id TEXT NOT NULL,
    owner_team TEXT NOT NULL,
    rpo_target_minutes INTEGER NOT NULL CHECK (rpo_target_minutes > 0),
    rto_target_minutes INTEGER NOT NULL CHECK (rto_target_minutes > 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (dataset_name, backup_type)
);

CREATE TABLE IF NOT EXISTS backup_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL UNIQUE,
    policy_id INTEGER NOT NULL,
    policy_name TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    backup_type TEXT NOT NULL CHECK (backup_type IN ('full', 'incremental')),
    status TEXT NOT NULL CHECK (status IN ('scheduled', 'running', 'succeeded', 'failed', 'cancelled')),
    backup_location TEXT,
    backup_size_bytes INTEGER CHECK (backup_size_bytes >= 0),
    backup_checksum TEXT,
    data_currency_point TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER CHECK (duration_ms >= 0),
    rows_backed_up INTEGER CHECK (rows_backed_up >= 0),
    compression_ratio REAL CHECK (compression_ratio > 0),
    encryption_status TEXT CHECK (encryption_status IN ('unencrypted', 'encrypted', 'key_rotation_pending')),
    verification_status TEXT CHECK (verification_status IN ('not_verified', 'verified', 'failed')),
    error_message TEXT,
    operator_identity TEXT,
    artifact_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (policy_id) REFERENCES backup_policies (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS restore_drills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drill_id TEXT NOT NULL UNIQUE,
    drill_name TEXT NOT NULL,
    policy_id INTEGER NOT NULL,
    dataset_name TEXT NOT NULL,
    target_backup_execution_id TEXT NOT NULL,
    drill_schedule_next_run TEXT,
    frequency_days INTEGER NOT NULL CHECK (frequency_days > 0),
    isolated_environment_name TEXT NOT NULL,
    restore_point_type TEXT NOT NULL CHECK (restore_point_type IN ('full', 'pitr', 'snapshot')),
    rpo_target_minutes INTEGER NOT NULL,
    rto_target_minutes INTEGER NOT NULL,
    last_drill_date TEXT,
    last_drill_status TEXT CHECK (last_drill_status IN ('pending', 'passed', 'failed', 'partial')),
    last_drill_rto_minutes INTEGER,
    last_drill_rpo_accuracy_percent REAL CHECK (last_drill_rpo_accuracy_percent >= 0 AND last_drill_rpo_accuracy_percent <= 100),
    drill_owner_email TEXT NOT NULL,
    approval_status TEXT NOT NULL CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    approved_by TEXT,
    approved_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (policy_id) REFERENCES backup_policies (id) ON DELETE RESTRICT,
    UNIQUE (drill_name, dataset_name)
);

CREATE TABLE IF NOT EXISTS restore_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    drill_id TEXT,
    backup_execution_id TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    restore_type TEXT NOT NULL CHECK (restore_type IN ('drill', 'emergency', 'point_in_time')),
    restore_target_environment TEXT NOT NULL,
    restore_point_timestamp TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('initiated', 'in_progress', 'completed', 'failed', 'rolled_back')),
    initiated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    rolled_back_at TEXT,
    duration_ms INTEGER CHECK (duration_ms >= 0),
    rpo_achieved_minutes INTEGER,
    rto_achieved_minutes INTEGER,
    rows_restored INTEGER CHECK (rows_restored >= 0),
    integrity_check_passed INTEGER CHECK (integrity_check_passed IN (0, 1)),
    operator_identity TEXT NOT NULL,
    approver_identity TEXT,
    rationale TEXT,
    verified_by_role TEXT CHECK (verified_by_role IN ('dba', 'ops', 'compliance', 'none')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (event_id)
);

CREATE TABLE IF NOT EXISTS restore_verification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verification_id TEXT NOT NULL UNIQUE,
    restore_event_id TEXT NOT NULL,
    verification_type TEXT NOT NULL CHECK (verification_type IN ('row_count', 'checksum', 'referential', 'critical_query', 'schema')),
    verification_target_table TEXT,
    expected_result TEXT,
    actual_result TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'passed', 'failed', 'skipped')),
    failure_reason TEXT,
    verified_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (restore_event_id) REFERENCES restore_events (event_id) ON DELETE CASCADE,
    UNIQUE (restore_event_id, verification_type, verification_target_table)
);

CREATE TABLE IF NOT EXISTS backup_audit_trail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT NOT NULL UNIQUE,
    action_type TEXT NOT NULL CHECK (action_type IN ('backup_initiated', 'backup_completed', 'backup_failed', 'restore_initiated', 'restore_completed', 'restore_failed', 'drill_scheduled', 'drill_completed', 'approval_given', 'access_granted', 'encryption_rotated', 'retention_policy_changed')),
    resource_type TEXT NOT NULL CHECK (resource_type IN ('backup', 'restore_event', 'drill', 'policy')),
    resource_id TEXT NOT NULL,
    actor_identity TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action_details TEXT,
    approval_status TEXT CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    approver_identity TEXT,
    approver_notes TEXT,
    compliance_context TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (audit_id)
);

CREATE TABLE IF NOT EXISTS backup_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL UNIQUE,
    backup_execution_id TEXT,
    restore_event_id TEXT,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('backup_missed', 'backup_failed', 'restore_failed', 'restore_incomplete', 'rpo_exceeded', 'rto_exceeded', 'encryption_key_expiring', 'storage_quota_exceeded', 'verification_failed')),
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    message TEXT NOT NULL,
    affected_dataset TEXT NOT NULL,
    incident_target TEXT,
    runbook_link TEXT,
    retry_backoff_seconds INTEGER,
    retry_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'resolved')),
    acknowledged_by TEXT,
    acknowledged_at TEXT,
    resolved_at TEXT,
    resolution_notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (alert_id)
);

CREATE TABLE IF NOT EXISTS drill_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL UNIQUE,
    drill_id TEXT NOT NULL,
    drill_date TEXT NOT NULL,
    drill_outcome TEXT NOT NULL CHECK (drill_outcome IN ('success', 'partial_success', 'failure')),
    drill_duration_minutes INTEGER NOT NULL CHECK (drill_duration_minutes > 0),
    rpo_achieved_minutes INTEGER,
    rto_achieved_minutes INTEGER,
    rpo_target_minutes INTEGER NOT NULL,
    rto_target_minutes INTEGER NOT NULL,
    rpo_target_met INTEGER CHECK (rpo_target_met IN (0, 1)),
    rto_target_met INTEGER CHECK (rto_target_met IN (0, 1)),
    integrity_checks_passed INTEGER CHECK (integrity_checks_passed IN (0, 1)),
    critical_queries_validated INTEGER CHECK (critical_queries_validated IN (0, 1)),
    blockers TEXT,
    remediation_actions TEXT,
    executed_by TEXT NOT NULL,
    approved_by TEXT,
    approved_at TEXT,
    report_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (report_id)
);

-- ============================================================================
-- BACKUP INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_backup_executions_policy
    ON backup_executions (policy_id, status, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_backup_executions_dataset
    ON backup_executions (dataset_name, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_backup_executions_status
    ON backup_executions (status, completed_at, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_restore_events_drill
    ON restore_events (drill_id, status, completed_at DESC);

CREATE INDEX IF NOT EXISTS idx_restore_events_dataset
    ON restore_events (dataset_name, status, initiated_at DESC);

CREATE INDEX IF NOT EXISTS idx_restore_verification_event
    ON restore_verification (restore_event_id, verification_type, status);

CREATE INDEX IF NOT EXISTS idx_drill_reports_drill
    ON drill_reports (drill_id, drill_date DESC);

CREATE INDEX IF NOT EXISTS idx_drill_reports_outcome
    ON drill_reports (drill_outcome, drill_date DESC);

CREATE INDEX IF NOT EXISTS idx_backup_audit_trail_resource
    ON backup_audit_trail (resource_type, resource_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_backup_audit_trail_actor
    ON backup_audit_trail (actor_identity, action_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_backup_alerts_status
    ON backup_alerts (status, severity, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_backup_alerts_dataset
    ON backup_alerts (affected_dataset, alert_type, status);
