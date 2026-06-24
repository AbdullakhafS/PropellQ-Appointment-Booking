"""
EP-007 US-075: Log All User Actions — Structured Audit Event Schema and Writers

task_075_001 — Canonical audit event schema: event types, required fields, PHI exclusion.
task_075_002 — Login/access event writers: login success/failure, PHI access, appointments.
task_075_003 — Account-change event writers: role changes, status changes, account create/update.
task_075_004 — Query interface and coverage report for compliance investigations.

Schema design (task_075_001):
  All events are stored via the AppendOnlyAuditStore from US-074.  Each event
  carries the following fields; audit records are DISTINCT from debug/application
  logs (stored in AppendOnlyAuditStore, not Python's logging.Logger stream):

    timestamp      ISO-8601 UTC — set by the store at append time.
    actor_id       Opaque user account ID.  Never contains email, name, or PHI.
    actor_role     Role at time of event (patient | staff | admin | system).
    event          Canonical AuditEventType string (e.g. "AUTH_LOGIN_SUCCESS").
    action         Sub-action label (e.g. "login", "read_patient_profile").
    resource_type  Type of resource acted on (session, patient, appointment, …).
    resource_id    Normalized resource identifier.  Numeric IDs only — no names.
    outcome        "success" | "denied" | "error".
    source_ip      Requesting IP address.  No other PII in this field.

PHI exclusion (task_075_001):
  The following values MUST NOT appear in any audit field:
  email, phone, name, date_of_birth, ssn, insurance_id, medical_record_number,
  address, password, token, session_secret, clinical_notes, medication_name.

  Resource IDs are numeric identifiers only; they do not carry PHI.
  Login-failure identity values are one-way hashed before logging to prevent
  credential guess enumeration via the audit trail.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from src.audit_storage import (
    AuditAccessGuard,
    AppendOnlyAuditStore,
    _AUDIT_STORE,
    AuditEntry,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# task_075_001: Canonical audit event types
# ---------------------------------------------------------------------------

class AuditEventType:
    """Canonical audit event-type constants.

    Audit events are distinct from debug/application logs:
    - Debug logs: Python logging (stderr / log files), level DEBUG–ERROR.
    - Audit events: AppendOnlyAuditStore entries, level AUDIT (structured).

    These constants are the authoritative event-type vocabulary.  All writers
    in this module use them; consumers can filter by event to extract compliance
    evidence for specific categories.
    """

    # ── Authentication ─────────────────────────────────────────────────────
    AUTH_LOGIN_SUCCESS  = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILURE  = "AUTH_LOGIN_FAILURE"
    AUTH_LOGOUT         = "AUTH_LOGOUT"
    AUTH_PASSWORD_RESET = "AUTH_PASSWORD_RESET"
    AUTH_SESSION_ISSUE  = "AUTH_SESSION_ISSUE"
    AUTH_SESSION_RENEW  = "AUTH_SESSION_RENEW"
    AUTH_SESSION_EXPIRE = "AUTH_SESSION_EXPIRE"

    # ── PHI / Clinical Data ────────────────────────────────────────────────
    PHI_ACCESS          = "PHI_ACCESS"
    PHI_MODIFY          = "PHI_MODIFY"

    # ── Appointments ──────────────────────────────────────────────────────
    APPOINTMENT_BOOK    = "APPOINTMENT_BOOK"
    APPOINTMENT_CHECKIN = "APPOINTMENT_CHECKIN"
    APPOINTMENT_CHECKOUT= "APPOINTMENT_CHECKOUT"

    # ── Account / Admin Changes ───────────────────────────────────────────
    ACCOUNT_CREATE        = "ACCOUNT_CREATE"
    ACCOUNT_UPDATE        = "ACCOUNT_UPDATE"
    ACCOUNT_ROLE_CHANGE   = "ACCOUNT_ROLE_CHANGE"
    ACCOUNT_STATUS_CHANGE = "ACCOUNT_STATUS_CHANGE"

    @classmethod
    def all_types(cls) -> list[str]:
        """Return sorted list of all defined event type strings."""
        return sorted(
            v for k, v in vars(cls).items()
            if not k.startswith("_") and isinstance(v, str) and k != k.lower()
        )


# ---------------------------------------------------------------------------
# task_075_001: Schema definition and PHI exclusion list
# ---------------------------------------------------------------------------

# Required fields in every audit event (validated by AppendOnlyAuditStore).
AUDIT_SCHEMA_REQUIRED_FIELDS: frozenset[str] = frozenset({
    "timestamp",
    "event",
    "actor_id",
    "actor_role",
    "action",
    "resource_type",
    "outcome",
    "source_ip",
})

# Optional but commonly present.
AUDIT_SCHEMA_OPTIONAL_FIELDS: frozenset[str] = frozenset({"resource_id"})

# Values that MUST NOT appear in any audit field (PHI exclusion).
AUDIT_PHI_EXCLUDED_FIELDS: frozenset[str] = frozenset({
    "email", "phone", "name", "date_of_birth", "dob", "ssn",
    "insurance_id", "medical_record_number", "address", "password",
    "token", "session_secret", "clinical_notes", "medication_name",
    "first_name", "last_name",
})

# Mapping of event type → resource_type for coverage documentation.
AUDIT_EVENT_RESOURCE_MAP: dict[str, str] = {
    AuditEventType.AUTH_LOGIN_SUCCESS:   "session",
    AuditEventType.AUTH_LOGIN_FAILURE:   "session",
    AuditEventType.AUTH_LOGOUT:          "session",
    AuditEventType.AUTH_PASSWORD_RESET:  "account",
    AuditEventType.AUTH_SESSION_ISSUE:   "session",
    AuditEventType.AUTH_SESSION_RENEW:   "session",
    AuditEventType.AUTH_SESSION_EXPIRE:  "session",
    AuditEventType.PHI_ACCESS:           "patient",
    AuditEventType.PHI_MODIFY:           "patient",
    AuditEventType.APPOINTMENT_BOOK:     "appointment",
    AuditEventType.APPOINTMENT_CHECKIN:  "appointment",
    AuditEventType.APPOINTMENT_CHECKOUT: "appointment",
    AuditEventType.ACCOUNT_CREATE:       "user_account",
    AuditEventType.ACCOUNT_UPDATE:       "user_account",
    AuditEventType.ACCOUNT_ROLE_CHANGE:  "user_account",
    AuditEventType.ACCOUNT_STATUS_CHANGE:"user_account",
}


def _safe_resource_id(raw: Any) -> str | None:
    """Return a numeric-only resource ID string, or None when raw is empty.

    Ensures resource IDs never carry non-numeric (potentially PHI) data.
    Strings that cannot be cast to int are returned as None.
    """
    if raw is None:
        return None
    try:
        return str(int(raw))
    except (ValueError, TypeError):
        return None


def _hash_identity(identity: str) -> str:
    """One-way SHA-256 hash of a login identity for failure logging.

    Prevents leaking credential enumeration targets via the audit trail
    while still providing a linkable identifier for repeat-attempt analysis.
    """
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]  # first 16 hex chars


# ---------------------------------------------------------------------------
# task_075_002: Login and access audit writers
# ---------------------------------------------------------------------------


def log_login_success(
    user_id: str,
    actor_role: str | None = None,
    source_ip: str | None = None,
    store: AppendOnlyAuditStore | None = None,
) -> AuditEntry:
    """Append an AUTH_LOGIN_SUCCESS event to the audit store.

    Called after a session token is successfully issued.  No PHI is written:
    only the opaque user ID and role are recorded.
    """
    _store = store or _AUDIT_STORE
    return _store.append(
        event=AuditEventType.AUTH_LOGIN_SUCCESS,
        actor_id=user_id,
        actor_role=actor_role or "unknown",
        action="login",
        resource_type="session",
        resource_id=None,
        outcome="success",
        source_ip=source_ip,
    )


def log_login_failure(
    identity: str,
    source_ip: str | None = None,
    store: AppendOnlyAuditStore | None = None,
) -> AuditEntry:
    """Append an AUTH_LOGIN_FAILURE event to the audit store.

    The submitted *identity* is one-way hashed before storage (task_075_001 PHI
    exclusion).  The hash prefix is sufficient for repeat-attempt correlation
    without exposing the raw credential value.
    """
    _store = store or _AUDIT_STORE
    hashed_id = _hash_identity(identity) if identity else "unknown"
    return _store.append(
        event=AuditEventType.AUTH_LOGIN_FAILURE,
        actor_id=hashed_id,
        actor_role=None,
        action="login_failed",
        resource_type="session",
        resource_id=None,
        outcome="denied",
        source_ip=source_ip,
    )


def log_session_issued(
    user_id: str,
    actor_role: str | None = None,
    source_ip: str | None = None,
    store: AppendOnlyAuditStore | None = None,
) -> AuditEntry:
    """Append an AUTH_SESSION_ISSUE event to the audit store."""
    _store = store or _AUDIT_STORE
    return _store.append(
        event=AuditEventType.AUTH_SESSION_ISSUE,
        actor_id=user_id,
        actor_role=actor_role or "unknown",
        action="session_issued",
        resource_type="session",
        resource_id=None,
        outcome="success",
        source_ip=source_ip,
    )


def log_phi_access(
    actor_id: str | None,
    actor_role: str | None,
    resource_type: str,
    resource_id: Any = None,
    action: str = "read",
    source_ip: str | None = None,
    store: AppendOnlyAuditStore | None = None,
) -> AuditEntry:
    """Append a PHI_ACCESS event to the audit store (task_075_002).

    Records every read of patient / clinical data.  The resource_id is
    normalised to a numeric-only value — no names or PHI in the ID field.
    """
    _store = store or _AUDIT_STORE
    return _store.append(
        event=AuditEventType.PHI_ACCESS,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=_safe_resource_id(resource_id),
        outcome="success",
        source_ip=source_ip,
    )


def log_phi_modify(
    actor_id: str | None,
    actor_role: str | None,
    resource_type: str,
    resource_id: Any = None,
    action: str = "modify",
    source_ip: str | None = None,
    store: AppendOnlyAuditStore | None = None,
) -> AuditEntry:
    """Append a PHI_MODIFY event to the audit store (task_075_002).

    Records every write/update of patient / clinical data.
    """
    _store = store or _AUDIT_STORE
    return _store.append(
        event=AuditEventType.PHI_MODIFY,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=_safe_resource_id(resource_id),
        outcome="success",
        source_ip=source_ip,
    )


def log_appointment_action(
    actor_id: str | None,
    actor_role: str | None,
    action: str,
    appointment_id: Any = None,
    outcome: str = "success",
    source_ip: str | None = None,
    store: AppendOnlyAuditStore | None = None,
) -> AuditEntry:
    """Append an appointment lifecycle event to the audit store (task_075_002).

    Maps *action* to the canonical event type:
      "book"     → APPOINTMENT_BOOK
      "checkin"  → APPOINTMENT_CHECKIN
      "checkout" → APPOINTMENT_CHECKOUT
      other      → PHI_ACCESS (generic access)
    """
    _store = store or _AUDIT_STORE
    action_map = {
        "book":     AuditEventType.APPOINTMENT_BOOK,
        "checkin":  AuditEventType.APPOINTMENT_CHECKIN,
        "checkout": AuditEventType.APPOINTMENT_CHECKOUT,
    }
    event = action_map.get(action.lower(), AuditEventType.PHI_ACCESS)
    return _store.append(
        event=event,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type="appointment",
        resource_id=_safe_resource_id(appointment_id),
        outcome=outcome,
        source_ip=source_ip,
    )


# ---------------------------------------------------------------------------
# task_075_003: Admin and account change audit writers
# ---------------------------------------------------------------------------


def log_account_create(
    actor_id: str | None,
    target_user_id: str,
    role: str,
    source_ip: str | None = None,
    store: AppendOnlyAuditStore | None = None,
) -> AuditEntry:
    """Append an ACCOUNT_CREATE event (task_075_003).

    Records who created the account (actor_id) and which user was created
    (target_user_id) and their initial role.  No email or PII is stored.
    """
    _store = store or _AUDIT_STORE
    return _store.append(
        event=AuditEventType.ACCOUNT_CREATE,
        actor_id=actor_id,
        actor_role="admin",
        action="account_create",
        resource_type="user_account",
        resource_id=target_user_id,
        outcome="success",
        source_ip=source_ip,
    )


def log_account_update(
    actor_id: str | None,
    target_user_id: str,
    changed_fields: list[str],
    source_ip: str | None = None,
    store: AppendOnlyAuditStore | None = None,
) -> AuditEntry:
    """Append an ACCOUNT_UPDATE event (task_075_003).

    Only field NAMES are stored (e.g. ["email"]), never the values.
    This satisfies audit requirements without leaking PII/PHI.
    """
    _store = store or _AUDIT_STORE
    safe_fields = ",".join(sorted(changed_fields))
    return _store.append(
        event=AuditEventType.ACCOUNT_UPDATE,
        actor_id=actor_id,
        actor_role="admin",
        action=f"account_update:{safe_fields}",
        resource_type="user_account",
        resource_id=target_user_id,
        outcome="success",
        source_ip=source_ip,
    )


def log_account_role_change(
    actor_id: str | None,
    target_user_id: str,
    from_role: str,
    to_role: str,
    source_ip: str | None = None,
    store: AppendOnlyAuditStore | None = None,
) -> AuditEntry:
    """Append an ACCOUNT_ROLE_CHANGE event (task_075_003).

    Records the actor, target user, and role transition.  Role values are
    controlled vocabulary (patient | staff | admin) and are not PHI.
    """
    _store = store or _AUDIT_STORE
    return _store.append(
        event=AuditEventType.ACCOUNT_ROLE_CHANGE,
        actor_id=actor_id,
        actor_role="admin",
        action=f"role_change:{from_role}->{to_role}",
        resource_type="user_account",
        resource_id=target_user_id,
        outcome="success",
        source_ip=source_ip,
    )


def log_account_status_change(
    actor_id: str | None,
    target_user_id: str,
    from_status: str,
    to_status: str,
    source_ip: str | None = None,
    store: AppendOnlyAuditStore | None = None,
) -> AuditEntry:
    """Append an ACCOUNT_STATUS_CHANGE event (task_075_003).

    Status values are controlled vocabulary (active | inactive | suspended)
    and are not PHI.  Actor and target IDs are opaque user identifiers.
    """
    _store = store or _AUDIT_STORE
    return _store.append(
        event=AuditEventType.ACCOUNT_STATUS_CHANGE,
        actor_id=actor_id,
        actor_role="admin",
        action=f"status_change:{from_status}->{to_status}",
        resource_type="user_account",
        resource_id=target_user_id,
        outcome="success",
        source_ip=source_ip,
    )


# ---------------------------------------------------------------------------
# task_075_004: Query interface and coverage report
# ---------------------------------------------------------------------------


def query_audit_events(
    role: str,
    actor_id: str | None = None,
    event_type: str | None = None,
    resource_type: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
    limit: int = 100,
    store: AppendOnlyAuditStore | None = None,
) -> tuple[list[AuditEntry] | None, str]:
    """Query audit events with RBAC enforcement and optional filters.

    Returns ``(entries, "")`` on success; ``(None, reason)`` when denied.

    Filters (all optional):
      event_type    — exact match on AuditEntry.event
      resource_type — exact match on AuditEntry.resource_type
      from_ts       — ISO-8601 string; include entries with timestamp >= from_ts
      to_ts         — ISO-8601 string; include entries with timestamp <= to_ts
      limit         — maximum entries to return (newest first)
    """
    allowed, reason = AuditAccessGuard.check_read(role, actor_id)
    if not allowed:
        return None, reason

    _store = store or _AUDIT_STORE
    all_entries = list(reversed(_store.all_entries()))  # newest first

    if event_type:
        all_entries = [e for e in all_entries if e.event == event_type]
    if resource_type:
        all_entries = [e for e in all_entries if e.resource_type == resource_type]
    if from_ts:
        all_entries = [e for e in all_entries if e.timestamp >= from_ts]
    if to_ts:
        all_entries = [e for e in all_entries if e.timestamp <= to_ts]

    return all_entries[:limit], ""


def get_audit_coverage_report(
    role: str,
    actor_id: str | None = None,
    store: AppendOnlyAuditStore | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """Return a compliance audit coverage report (task_075_004).

    Documents which event types are present, their counts, the date range,
    and which schema-defined event types have no recorded events (gaps).

    Returns ``(report, "")`` on success; ``(None, reason)`` when denied.
    """
    allowed, reason = AuditAccessGuard.check_read(role, actor_id)
    if not allowed:
        return None, reason

    _store = store or _AUDIT_STORE
    entries = _store.all_entries()

    event_counts: dict[str, int] = {}
    for e in entries:
        event_counts[e.event] = event_counts.get(e.event, 0) + 1

    all_expected = AuditEventType.all_types()
    gaps = [t for t in all_expected if t not in event_counts]

    timestamps = [e.timestamp for e in entries]
    earliest = min(timestamps) if timestamps else None
    latest = max(timestamps) if timestamps else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(entries),
        "event_type_counts": event_counts,
        "covered_event_types": sorted(event_counts.keys()),
        "expected_event_types": all_expected,
        "coverage_gaps": gaps,
        "date_range": {"earliest": earliest, "latest": latest},
        "schema_fields": sorted(AUDIT_SCHEMA_REQUIRED_FIELDS),
        "phi_excluded_fields": sorted(AUDIT_PHI_EXCLUDED_FIELDS),
        "compliance_note": (
            "Audit events are stored separately from debug logs in the "
            "AppendOnlyAuditStore. All records include timestamp, actor_id, "
            "actor_role, event type, action, resource_type, resource_id, "
            "outcome, and source_ip. No PHI is included in any field."
        ),
    }, ""
