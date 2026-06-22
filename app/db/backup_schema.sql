-- Backup and Restore Automation Schema Extensions
-- Version: 1.0
-- Purpose: Track backup policies, execution, restore drills, and recovery evidence
-- Status: Production
--
-- DESIGN PRINCIPLES:
-- 1. Immutable audit trail for all backup/restore operations
-- 2. Enforce encryption and access control at schema level
-- 3. Track RPO/RTO metrics for compliance reporting
-- 4. Support monthly drill automation and evidence capture
--
-- TABLES:
--   - backup_policies: Define backup schedules, retention, encryption
--   - backup_executions: Immutable log of backup runs with success metrics
--   - restore_drills: Monthly scheduled restore exercises
--   - restore_events: Point-in-time restore operations and outcomes
--   - restore_verification: Integrity checks and critical query validation
--   - backup_audit_trail: Access and approval logs for backups/restores
--

PRAGMA foreign_keys = ON;

-- ============================================================================
-- BACKUP POLICIES AND SCHEDULING
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

-- ============================================================================
-- BACKUP EXECUTION AND METRICS
-- ============================================================================

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

-- ============================================================================
-- RESTORE DRILLS AND EXERCISES
-- ============================================================================

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

-- ============================================================================
-- RESTORE EVENTS AND OPERATIONS
-- ============================================================================

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

-- ============================================================================
-- RESTORE VERIFICATION AND VALIDATION
-- ============================================================================

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

-- ============================================================================
-- AUDIT AND COMPLIANCE TRAIL
-- ============================================================================

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

-- ============================================================================
-- BACKUP ALERTS AND INCIDENT TRACKING
-- ============================================================================

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

-- ============================================================================
-- RECOVERY DRILL REPORTS AND EVIDENCE
-- ============================================================================

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
-- INDEXES FOR PERFORMANCE
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
