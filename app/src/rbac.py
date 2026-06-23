"""
EP-005 US-043/US-044/US-045/US-046: Role-Based Access Control (RBAC)

Covers:
  task_043_001 — RBAC permission matrix (Patient / Staff / Admin)
  task_043_002 — Central authorization middleware
  task_043_003 — Ownership and assignment scoping rules
  task_044_001 — Patient appointment ownership filtering
  task_044_002 — Patient profile/intake ownership enforcement
  task_045_001 — Assignment-scoped staff queue access
  task_045_002 — Minimum-necessary patient detail for staff workflows
  task_045_003 — Staff access action logging with assignment context
  task_046_001 — Admin-only access for management endpoints
  task_046_002 — Role/status change operations with audit metadata
  task_046_003 — Admin audit log read-only access with filters
"""
from __future__ import annotations

import base64
import csv
import hashlib
import hmac as _hmac
import io
import json
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# task_043_001: RBAC Permission Matrix
# ---------------------------------------------------------------------------

ROLES = ("patient", "staff", "admin")

# Maps action → set of roles that are allowed to perform it.
# Versioned matrix — update this table to change the policy.
PERMISSION_MATRIX: dict[str, set[str]] = {
    # ── Appointments ──────────────────────────────────────────────────────
    "appointments:search":    {"patient", "staff", "admin"},
    "appointments:view":      {"patient", "staff", "admin"},
    "appointments:book":      {"patient", "staff", "admin"},
    "appointments:checkout":  {"patient", "staff", "admin"},
    "appointments:resend":    {"staff", "admin"},
    # ── Calendar ──────────────────────────────────────────────────────────
    "calendar:read":          {"patient", "staff", "admin"},
    # ── Integrations ──────────────────────────────────────────────────────
    "integrations:connect":   {"patient", "admin"},
    "integrations:disconnect": {"patient", "admin"},
    # ── Clinical (EP-003) ─────────────────────────────────────────────────
    "clinical:view_profile":       {"staff", "admin"},
    "clinical:upload_document":    {"staff", "admin"},
    "clinical:process_document":   {"staff", "admin"},
    "clinical:view_conflicts":     {"staff", "admin"},
    "clinical:code_review":        {"staff", "admin"},
    "clinical:manage_thresholds":  {"admin"},
    "clinical:view_allergy_conflicts": {"staff", "admin"},
    "clinical:view_suggestions":   {"staff", "admin"},
    "clinical:generate_suggestions": {"staff", "admin"},
    "clinical:resolve_conflict":   {"staff", "admin"},
    # ── Admin ─────────────────────────────────────────────────────────────
    "admin:dashboard":  {"admin"},
    "admin:ops_jobs":   {"admin"},
    "admin:audit_logs": {"staff", "admin"},
    # ── Staff operations (EP-005 US-045) ──────────────────────────────────
    "staff:queue_view": {"staff", "admin"},
    "staff:checkin":    {"staff", "admin"},
    # ── Admin management (EP-005 US-046) ──────────────────────────────────
    "admin:user_management": {"admin"},
    "admin:change_log":      {"admin"},
}


def get_permission_matrix() -> dict[str, list[str]]:
    """Return the versioned matrix as a JSON-serialisable dict."""
    return {action: sorted(roles) for action, roles in PERMISSION_MATRIX.items()}


def check_permission(role: str, action: str) -> bool:
    """Return True if *role* is allowed to perform *action*."""
    allowed = PERMISSION_MATRIX.get(action, set())
    return role in allowed


# ---------------------------------------------------------------------------
# task_050_001: Endpoint-Permission Coverage Matrix
# ---------------------------------------------------------------------------
# Maps "METHOD /api/path/{id}" → {permission, scoping} for every API route.
# ``permission: None``  → public endpoint (no role check required).
# ``scoping``           → one of "public" | "none" | "patient_ownership" |
#                         "staff_assignment" | "appointment_ownership" | "signed_url"

ENDPOINT_PERMISSION_MAP: dict[str, dict[str, str | None]] = {
    # ── Appointment search & browsing ──────────────────────────────────────
    "GET /api/appointments/search":                  {"permission": None,                              "scoping": "public"},
    "GET /api/appointments/specialties":             {"permission": None,                              "scoping": "public"},
    "GET /api/providers/suggest":                    {"permission": None,                              "scoping": "public"},
    "GET /api/appointments/calendar":                {"permission": "appointments:search",             "scoping": "public"},
    "GET /api/appointments/{id}":                    {"permission": "appointments:view",               "scoping": "appointment_ownership"},
    "GET /api/providers/{id}":                       {"permission": None,                              "scoping": "public"},
    # ── Appointment lifecycle ──────────────────────────────────────────────
    "POST /api/appointments/{id}/checkout":          {"permission": "appointments:checkout",           "scoping": "patient_ownership"},
    "POST /api/appointments/book":                   {"permission": "appointments:book",               "scoping": "patient_ownership"},
    "POST /api/appointments/{id}/book":              {"permission": "appointments:book",               "scoping": "none"},
    "POST /api/appointments/{id}/resend-confirmation": {"permission": "appointments:resend",           "scoping": "none"},
    # ── Patient profile & integrations ────────────────────────────────────
    "GET /api/patient/profile":                      {"permission": "appointments:view",               "scoping": "patient_ownership"},
    "GET /api/integrations/status":                  {"permission": "integrations:connect",            "scoping": "patient_ownership"},
    "GET /api/auth/{provider}/authorize":            {"permission": "integrations:connect",            "scoping": "none"},
    "GET /api/auth/{provider}/callback":             {"permission": "integrations:connect",            "scoping": "none"},
    "POST /api/auth/{provider}/disconnect":          {"permission": "integrations:disconnect",         "scoping": "none"},
    # ── Password reset (US-049) — unauthenticated ─────────────────────────
    "POST /api/auth/password-reset/request":         {"permission": None,                              "scoping": "public"},
    "POST /api/auth/password-reset/confirm":         {"permission": None,                              "scoping": "public"},
    # ── Admin operational jobs ─────────────────────────────────────────────
    "POST /api/jobs/process-confirmations":          {"permission": "admin:ops_jobs",                  "scoping": "none"},
    "POST /api/jobs/process-reminders":              {"permission": "admin:ops_jobs",                  "scoping": "none"},
    "POST /api/jobs/process-swaps":                  {"permission": "admin:ops_jobs",                  "scoping": "none"},
    "POST /api/jobs/process-calendar-sync":          {"permission": "admin:ops_jobs",                  "scoping": "none"},
    "POST /api/jobs/reconcile-calendar-sync":        {"permission": "admin:ops_jobs",                  "scoping": "none"},
    # ── Dashboard & metrics ────────────────────────────────────────────────
    "GET /api/dashboard/metrics":                    {"permission": "admin:dashboard",                 "scoping": "none"},
    "GET /api/metrics/search":                       {"permission": None,                              "scoping": "public"},
    # ── RBAC & audit endpoints ─────────────────────────────────────────────
    "GET /api/auth/me":                              {"permission": None,                              "scoping": "none"},
    "GET /api/rbac/permissions":                     {"permission": "admin:audit_logs",                "scoping": "none"},
    "GET /api/rbac/audit-log":                       {"permission": "admin:audit_logs",                "scoping": "none"},
    # ── Clinical Intelligence (EP-003) ────────────────────────────────────
    "POST /api/clinical/documents/upload":           {"permission": "clinical:upload_document",        "scoping": "none"},
    "GET /api/clinical/documents/{id}/status":       {"permission": "clinical:view_profile",           "scoping": "none"},
    "POST /api/clinical/documents/{id}/process":     {"permission": "clinical:process_document",       "scoping": "none"},
    "GET /api/clinical/documents/{id}/signed-url":   {"permission": "clinical:view_profile",           "scoping": "none"},
    "GET /api/clinical/documents/{id}/preview":      {"permission": "clinical:view_profile",           "scoping": "signed_url"},
    "GET /api/clinical/patients/{id}/profile":       {"permission": "clinical:view_profile",           "scoping": "patient_ownership"},
    "POST /api/clinical/patients/{id}/aggregate":    {"permission": "clinical:process_document",       "scoping": "none"},
    "GET /api/clinical/patients/{id}/conflicts":     {"permission": "clinical:view_conflicts",         "scoping": "none"},
    "GET /api/clinical/elements/{id}/source":        {"permission": "clinical:view_profile",           "scoping": "none"},
    "GET /api/clinical/patients/{id}/allergy-conflicts": {"permission": "clinical:view_allergy_conflicts", "scoping": "none"},
    "GET /api/clinical/patients/{id}/suggestions":   {"permission": "clinical:view_suggestions",       "scoping": "none"},
    "POST /api/clinical/patients/{id}/suggestions":  {"permission": "clinical:generate_suggestions",   "scoping": "none"},
    "POST /api/coding/suggestions/{id}/review":      {"permission": "clinical:code_review",            "scoping": "none"},
    "GET /api/clinical/thresholds":                  {"permission": "clinical:view_profile",           "scoping": "none"},
    "PUT /api/clinical/thresholds":                  {"permission": "clinical:manage_thresholds",      "scoping": "none"},
    "GET /api/clinical/thresholds/history":          {"permission": "admin:audit_logs",                "scoping": "none"},
    "GET /api/clinical/conflicts/queue":             {"permission": "clinical:view_conflicts",         "scoping": "none"},
    "POST /api/clinical/conflicts/{id}/resolve":     {"permission": "clinical:resolve_conflict",       "scoping": "none"},
    # ── Admin user management (US-046/047/048) ────────────────────────────
    "POST /api/admin/users":                         {"permission": "admin:user_management",           "scoping": "none"},
    "GET /api/admin/users":                          {"permission": "admin:user_management",           "scoping": "none"},
    "GET /api/admin/users/{id}":                     {"permission": "admin:user_management",           "scoping": "none"},
    "PATCH /api/admin/users/{id}":                   {"permission": "admin:user_management",           "scoping": "none"},
    "PATCH /api/admin/users/{id}/role":              {"permission": "admin:user_management",           "scoping": "none"},
    "PATCH /api/admin/users/{id}/status":            {"permission": "admin:user_management",           "scoping": "none"},
    "GET /api/admin/change-log":                     {"permission": "admin:change_log",                "scoping": "none"},
    # ── Staff queue & check-in (US-045) ───────────────────────────────────
    "GET /api/staff/queue":                          {"permission": "staff:queue_view",                "scoping": "staff_assignment"},
    "GET /api/staff/patients/{id}/detail":           {"permission": "staff:queue_view",                "scoping": "staff_assignment"},
    "POST /api/staff/appointments/{id}/checkin":     {"permission": "staff:checkin",                   "scoping": "staff_assignment"},
    "GET /api/staff/access-log":                     {"permission": "admin:audit_logs",                "scoping": "none"},
    # ── Session token (US-051) ────────────────────────────────────────────
    "POST /api/auth/session":                        {"permission": None,                              "scoping": "public"},
    "GET /api/auth/session/schema":                  {"permission": None,                              "scoping": "public"},
    # ── Audit log viewer (US-052) ─────────────────────────────────────────
    "GET /api/admin/change-log/entry/{id}":          {"permission": "admin:change_log",                "scoping": "none"},
    "GET /api/admin/change-log/export":              {"permission": "admin:change_log",                "scoping": "none"},
}


def get_endpoint_permission_map() -> dict[str, dict[str, str | None]]:
    """Return the endpoint-permission coverage matrix (task_050_001, read-only copy)."""
    return dict(ENDPOINT_PERMISSION_MAP)


# ---------------------------------------------------------------------------
# task_043_002: Central Authorization Middleware
# ---------------------------------------------------------------------------

# In-process audit log (queryable via API; bounded to last 2 000 entries).
_AUDIT_LOG: list[dict[str, Any]] = []
_AUDIT_LOG_MAX = 2000


# Compiled once at module level — replaces numeric path segments in log entries.
_PATH_ID_RE = re.compile(r"/\d+")


def _normalize_endpoint_pattern(endpoint: str) -> str:
    """Replace numeric path segments with ``{id}`` for searchable, non-leaking logs."""
    return _PATH_ID_RE.sub("/{id}", endpoint)


def log_denied_event(
    role: str,
    action: str,
    endpoint: str,
    method: str = "",
    *,
    actor_id: str | None = None,
    reason: str | None = None,
) -> None:
    """Record a denied authorization event (task_050_003).

    ``actor_id`` — the requesting actor (admin-id, staff-id, or ``patient:<N>``).
    ``reason``   — human-readable denial reason; must not contain PII.

    Numeric resource IDs in *endpoint* are normalised to ``{id}`` so that
    audit entries are searchable and do not leak protected resource identifiers.
    """
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "action": action,
        "endpoint": _normalize_endpoint_pattern(endpoint),
        "method": method,
        "outcome": "denied",
    }
    if actor_id is not None:
        entry["actor_id"] = actor_id
    if reason is not None:
        entry["reason"] = reason
    _AUDIT_LOG.append(entry)
    if len(_AUDIT_LOG) > _AUDIT_LOG_MAX:
        del _AUDIT_LOG[: len(_AUDIT_LOG) - _AUDIT_LOG_MAX]
    logger.warning(
        "RBAC denied | role=%s action=%s endpoint=%s method=%s actor=%s",
        role, action, endpoint, method, actor_id,
    )


def get_audit_log(limit: int = 100) -> list[dict[str, Any]]:
    """Return the most-recent *limit* audit entries (newest first)."""
    return list(reversed(_AUDIT_LOG[-limit:]))


def get_actor_id_from_environ(environ: dict[str, Any]) -> str | None:
    """Return the first available actor identifier from standard request headers.

    Checks ``X-Admin-Id``, ``X-Staff-Id``, and ``X-Patient-Id`` in priority
    order.  Returns ``None`` when no identity header is present.
    """
    admin = (environ.get("HTTP_X_ADMIN_ID") or "").strip()
    if admin:
        return admin
    staff = (environ.get("HTTP_X_STAFF_ID") or "").strip()
    if staff:
        return staff
    patient = str(environ.get("HTTP_X_PATIENT_ID") or "").strip()
    if patient and patient not in ("0", ""):
        return f"patient:{patient}"
    return None


def get_role_from_environ(environ: dict[str, Any]) -> str:
    """
    Extract the caller role from the WSGI environ (task_051_002).

    Checks in priority order:
    1. ``Authorization: Bearer <token>`` — if a valid signed session token is
       present its ``role`` claim is used.  Invalid/expired tokens fall
       through to the legacy header so the web-layer 401 middleware fires
       before any permission check.
    2. ``X-Role`` header — legacy / test mode fallback (least privilege when
       value is absent or unknown).
    """
    auth_header = (environ.get("HTTP_AUTHORIZATION") or "").strip()
    if auth_header.lower().startswith("bearer "):
        token_str = auth_header[7:].strip()
        claims = validate_session_token(token_str)
        if claims:
            role = claims.get("role", "patient")
            return role if role in ROLES else "patient"
        # Token present but invalid — web middleware returns 401 before here
        return "patient"
    header_value = (environ.get("HTTP_X_ROLE") or "").strip().lower()
    return header_value if header_value in ROLES else "patient"


def require_permission(
    environ: dict[str, Any],
    action: str,
) -> tuple[str, str] | None:
    """
    Central authorization check.

    Returns ``None`` when the request is authorised.
    Returns ``(role, error_message)`` when it is denied; the caller is
    responsible for returning a 403 response and should call
    ``log_denied_event`` (this function logs automatically).

    Usage in a handler::

        denial = require_permission(environ, "admin:dashboard")
        if denial:
            role, msg = denial
            return _json_response(start_response, 403, {"success": False,
                "error": {"code": "FORBIDDEN", "message": msg}})
    """
    role = get_role_from_environ(environ)
    if check_permission(role, action):
        return None

    endpoint = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "")
    actor_id = get_actor_id_from_environ(environ)
    msg = f"Role '{role}' is not authorised to perform '{action}'."
    log_denied_event(role, action, endpoint, method, actor_id=actor_id, reason=msg)
    return role, msg


# ---------------------------------------------------------------------------
# task_043_003: Ownership and Assignment Scoping Rules
# ---------------------------------------------------------------------------

def check_resource_scope(
    role: str,
    requesting_patient_id: int | None,
    resource_patient_id: int | None,
) -> bool:
    """
    Fine-grained data scoping on top of role checks.

    Rules
    -----
    * ``admin``   — can access any patient's resources.
    * ``staff``   — can access any patient's resources (assignment assumed
                    by the caller layer; extend here when team tables exist).
    * ``patient`` — can only access their *own* records
                    (requesting_patient_id must equal resource_patient_id).
    """
    if role in ("admin", "staff"):
        return True
    if role == "patient":
        return requesting_patient_id == resource_patient_id
    return False


def require_resource_scope(
    environ: dict[str, Any],
    resource_patient_id: int | None,
) -> tuple[str, str] | None:
    """
    Verify ownership / scoping after a permission check has passed.

    Reads ``X-Patient-Id`` header as the requesting patient identity.
    Returns ``None`` when scoping is satisfied, or ``(role, message)``
    when it is violated (and logs the denial).
    """
    role = get_role_from_environ(environ)
    if role in ("admin", "staff"):
        return None  # staff / admin are not scoped to a single patient

    try:
        requesting_id = int(environ.get("HTTP_X_PATIENT_ID") or 0)
    except (ValueError, TypeError):
        requesting_id = 0

    if check_resource_scope(role, requesting_id, resource_patient_id):
        return None

    endpoint = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "")
    actor_id = get_actor_id_from_environ(environ)
    log_denied_event(
        role, "resource:scope", endpoint, method,
        actor_id=actor_id, reason="Patient ownership check failed.",
    )
    return (
        role,
        f"Role 'patient' may only access their own records "
        f"(requested patient_id={resource_patient_id}).",
    )


# ---------------------------------------------------------------------------
# task_044_001/002: Patient ownership helpers for appointments & profile
# ---------------------------------------------------------------------------

def get_patient_id_from_environ(environ: dict[str, Any]) -> int:
    """Return the patient ID from the ``X-Patient-Id`` request header (default 0)."""
    try:
        return int(environ.get("HTTP_X_PATIENT_ID") or 0)
    except (ValueError, TypeError):
        return 0


def check_appointment_ownership(
    role: str,
    requesting_patient_id: int,
    appointment: dict[str, Any],
    owner_patient_id: int,
) -> bool:
    """
    Return True if the caller may access the given appointment.

    Rules
    -----
    * ``admin`` / ``staff`` — unrestricted access to any appointment.
    * ``patient``
        - May always view **available** slots (needed for booking browsing).
        - May only view **booked/confirmed** appointments that belong to
          them (``requesting_patient_id == owner_patient_id``).
    """
    if role in ("admin", "staff"):
        return True
    if role == "patient":
        status = appointment.get("status", "")
        checkout = appointment.get("checkout_status", "")
        if status == "available" and checkout not in ("reserved", "confirmed"):
            return True
        return requesting_patient_id == owner_patient_id
    return False


def require_appointment_ownership(
    environ: dict[str, Any],
    appointment: dict[str, Any],
    owner_patient_id: int,
) -> tuple[str, str] | None:
    """
    Verify caller can access ``appointment``.

    Returns ``None`` when allowed, or ``(role, message)`` when denied
    (and logs the denial event).
    """
    role = get_role_from_environ(environ)
    requesting_id = get_patient_id_from_environ(environ)
    if check_appointment_ownership(role, requesting_id, appointment, owner_patient_id):
        return None

    endpoint = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "")
    actor_id = get_actor_id_from_environ(environ)
    log_denied_event(
        role, "appointments:ownership", endpoint, method,
        actor_id=actor_id, reason="Appointment ownership check failed.",
    )
    return (
        role,
        "Access denied: patients may only view their own appointments.",
    )


# ---------------------------------------------------------------------------
# task_045_001/002/003: Staff Assignment Scoping, Minimum-Necessary Detail,
#                       and Staff Action Audit Logging
# ---------------------------------------------------------------------------

# In-memory staff assignment store: maps staff_id (str) → frozenset of provider IDs.
# Seeded via set_staff_assignment() — typically in test setup or an admin API.
_STAFF_ASSIGNMENTS: dict[str, frozenset[int]] = {}

# In-memory staff access log (bounded to last 2 000 entries).
_STAFF_ACCESS_LOG: list[dict[str, Any]] = []
_STAFF_ACCESS_LOG_MAX = 2000

# Patient profile / appointment fields that are NOT required for check-in or
# visit operations and must be stripped from staff-facing detail responses
# (minimum-necessary principle, task_045_002).
_STAFF_EXCLUDED_PATIENT_FIELDS: frozenset[str] = frozenset(
    {
        "reminder_channels",
        "do_not_disturb",
        "patient_email",
        "patient_phone",
        "patient_notes",
    }
)


def get_staff_id_from_environ(environ: dict[str, Any]) -> str | None:
    """Return the staff ID from the ``X-Staff-Id`` request header (None if absent)."""
    value = (environ.get("HTTP_X_STAFF_ID") or "").strip()
    return value if value else None


def get_staff_assigned_providers(staff_id: str) -> frozenset[int]:
    """Return the set of provider IDs currently assigned to *staff_id*."""
    return _STAFF_ASSIGNMENTS.get(staff_id, frozenset())


def set_staff_assignment(staff_id: str, provider_ids: list[int]) -> None:
    """Register (or replace) the provider assignment for *staff_id*."""
    _STAFF_ASSIGNMENTS[staff_id] = frozenset(provider_ids)


def check_staff_assignment(
    staff_id: str | None,
    provider_id: int | None = None,
) -> bool:
    """
    Return True when *staff_id* has at least one active assignment.

    If *provider_id* is given, also assert that the staff member is
    specifically assigned to that provider.
    """
    if not staff_id:
        return False
    assigned = get_staff_assigned_providers(staff_id)
    if not assigned:
        return False
    if provider_id is None:
        return True
    return provider_id in assigned


def require_staff_assignment(
    environ: dict[str, Any],
    provider_id: int | None = None,
) -> tuple[str, str] | None:
    """
    Verify the requesting staff member has an active assignment.

    When *provider_id* is supplied, also verify they are assigned to that
    specific provider.  Admins bypass this check.

    Returns ``None`` when authorised, ``(role, message)`` when denied (and
    logs the denial via ``log_denied_event``).
    """
    role = get_role_from_environ(environ)
    if role == "admin":
        return None

    if role != "staff":
        endpoint = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "")
        actor_id = get_actor_id_from_environ(environ)
        msg = f"Role '{role}' is not authorised for staff operations."
        log_denied_event(
            role, "staff:assignment_required", endpoint, method,
            actor_id=actor_id, reason=msg,
        )
        return role, msg

    staff_id = get_staff_id_from_environ(environ)
    if not check_staff_assignment(staff_id, provider_id):
        endpoint = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "")
        actor_id = get_actor_id_from_environ(environ)
        log_denied_event(
            role, "staff:assignment_required", endpoint, method,
            actor_id=actor_id, reason="Staff assignment check failed.",
        )
        if provider_id is not None:
            return role, f"Staff member is not assigned to provider {provider_id}."
        return role, "Staff member has no active assignment."

    return None


def filter_staff_patient_detail(data: dict[str, Any]) -> dict[str, Any]:
    """
    Return a copy of *data* with sensitive non-operational fields removed.

    Enforces the minimum-necessary principle for staff check-in / visit
    workflows (task_045_002): callers receive only the fields they need to
    identify the patient and complete the visit, with private contact and
    preference data excluded.
    """
    return {k: v for k, v in data.items() if k not in _STAFF_EXCLUDED_PATIENT_FIELDS}


def log_staff_access_event(
    staff_id: str | None,
    action: str,
    provider_id: int | None,
    resource: str,
    outcome: str = "success",
) -> None:
    """
    Record a staff access or check-in action (task_045_003).

    Entries capture actor (staff_id), assignment scope (provider_id),
    action name, resource path, outcome, and UTC timestamp.
    """
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "staff_id": staff_id,
        "action": action,
        "provider_id": provider_id,
        "resource": resource,
        "outcome": outcome,
    }
    _STAFF_ACCESS_LOG.append(entry)
    if len(_STAFF_ACCESS_LOG) > _STAFF_ACCESS_LOG_MAX:
        del _STAFF_ACCESS_LOG[: len(_STAFF_ACCESS_LOG) - _STAFF_ACCESS_LOG_MAX]
    logger.info(
        "STAFF access | staff_id=%s action=%s provider_id=%s resource=%s outcome=%s",
        staff_id,
        action,
        provider_id,
        resource,
        outcome,
    )


def get_staff_access_log(limit: int = 100) -> list[dict[str, Any]]:
    """Return the most-recent *limit* staff access log entries (newest first)."""
    return list(reversed(_STAFF_ACCESS_LOG[-limit:]))


# ---------------------------------------------------------------------------
# task_046_001/002/003: Admin User Management, Role/Status Changes, Change Log
# ---------------------------------------------------------------------------

# Valid account statuses for user lifecycle operations.
VALID_STATUSES: tuple[str, ...] = ("active", "inactive", "suspended")

# In-memory user registry: maps user_id (str) → user record dict.
# Seeded via register_user() — represents system accounts (staff + admin).
_USER_REGISTRY: dict[str, dict[str, Any]] = {}

# Bounded admin change audit log (role assignments, status changes).
_ADMIN_CHANGE_LOG: list[dict[str, Any]] = []
_ADMIN_CHANGE_LOG_MAX = 2000


def get_admin_id_from_environ(environ: dict[str, Any]) -> str | None:
    """Return the admin actor ID from the ``X-Admin-Id`` request header."""
    value = (environ.get("HTTP_X_ADMIN_ID") or "").strip()
    return value if value else None


def register_user(
    user_id: str,
    role: str,
    email: str,
    status: str = "active",
) -> dict[str, Any]:
    """
    Add or replace a user in the registry.

    Used for test seeding and admin-initiated account creation.
    Raises ``ValueError`` for unknown role or status values.
    """
    if role not in ROLES:
        raise ValueError(f"Unknown role '{role}'.")
    if status not in VALID_STATUSES:
        raise ValueError(f"Unknown status '{status}'.")
    entry: dict[str, Any] = {
        "id": user_id,
        "role": role,
        "status": status,
        "email": email,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _USER_REGISTRY[user_id] = entry
    return entry


def get_user(user_id: str) -> dict[str, Any] | None:
    """Look up a user record by ID."""
    return _USER_REGISTRY.get(user_id)


def list_users() -> list[dict[str, Any]]:
    """Return all registered user records."""
    return list(_USER_REGISTRY.values())


def assign_user_role(
    actor_id: str | None,
    user_id: str,
    new_role: str,
    reason: str = "",
) -> tuple[bool, str]:
    """
    Change the role of a registered user and append a change log entry
    (task_046_002).

    Returns ``(True, message)`` on success, ``(False, error)`` on failure.
    """
    if new_role not in ROLES:
        return False, f"Unknown role '{new_role}'."
    user = _USER_REGISTRY.get(user_id)
    if user is None:
        return False, f"User '{user_id}' not found."
    previous_role = user["role"]
    user["role"] = new_role
    _record_admin_change(actor_id, "admin:role_assigned", user_id, previous_role, new_role, reason)
    revoke_user_tokens(user_id)  # task_051_003: invalidate stale tokens on role change
    return True, f"Role updated to '{new_role}'."


def set_user_status(
    actor_id: str | None,
    user_id: str,
    new_status: str,
    reason: str = "",
) -> tuple[bool, str]:
    """
    Activate, deactivate, or suspend a registered user and append a change
    log entry (task_046_002).

    Returns ``(True, message)`` on success, ``(False, error)`` on failure.
    """
    if new_status not in VALID_STATUSES:
        return False, f"Unknown status '{new_status}'. Must be one of {VALID_STATUSES}."
    user = _USER_REGISTRY.get(user_id)
    if user is None:
        return False, f"User '{user_id}' not found."
    previous_status = user["status"]
    user["status"] = new_status
    _record_admin_change(actor_id, "admin:status_changed", user_id, previous_status, new_status, reason)
    revoke_user_tokens(user_id)  # task_051_003: invalidate tokens on status change
    return True, f"Status updated to '{new_status}'."


def _record_admin_change(
    actor_id: str | None,
    action: str,
    target_user_id: str,
    previous_value: Any,
    new_value: Any,
    reason: str,
) -> None:
    """Append a structured entry to the bounded admin change log."""
    entry: dict[str, Any] = {
        "entry_id":       str(uuid.uuid4()),
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "actor":          actor_id,
        "action":         action,
        "target_user_id": target_user_id,
        "previous_value": previous_value,
        "new_value":      new_value,
        "reason":         reason,
    }
    _ADMIN_CHANGE_LOG.append(entry)
    if len(_ADMIN_CHANGE_LOG) > _ADMIN_CHANGE_LOG_MAX:
        del _ADMIN_CHANGE_LOG[: len(_ADMIN_CHANGE_LOG) - _ADMIN_CHANGE_LOG_MAX]
    logger.info(
        "ADMIN change | actor=%s action=%s target=%s %s→%s",
        actor_id,
        action,
        target_user_id,
        previous_value,
        new_value,
    )


def get_admin_change_log(
    actor: str | None = None,
    action: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
    limit: int = 100,
    *,
    target_user: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return filtered admin change log entries, newest first (task_046_003).

    Filters
    -------
    actor       — return only entries where ``entry["actor"] == actor``
    action      — return only entries matching this action name
    target_user — return only entries where ``target_user_id == target_user``
    from_ts     — ISO-8601 string; include entries with timestamp >= from_ts
    to_ts       — ISO-8601 string; include entries with timestamp <= to_ts
    limit       — maximum number of entries to return
    """
    entries: list[dict[str, Any]] = list(reversed(_ADMIN_CHANGE_LOG))
    if actor:
        entries = [e for e in entries if e.get("actor") == actor]
    if action:
        entries = [e for e in entries if e.get("action") == action]
    if target_user:
        entries = [e for e in entries if e.get("target_user_id") == target_user]
    if from_ts:
        entries = [e for e in entries if e["timestamp"] >= from_ts]
    if to_ts:
        entries = [e for e in entries if e["timestamp"] <= to_ts]
    return entries[:limit]


# =============================================================================
# EP-005 US-048: User lifecycle helpers (task_048_001 – task_048_004)
# =============================================================================

# Fields that admins may update via the general update API.
_UPDATABLE_FIELDS: frozenset[str] = frozenset({"email"})

# Regex for a minimal email sanity check (not RFC-5321 complete, sufficient
# for admin-controlled data entry).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def record_admin_event(
    actor_id: str | None,
    action: str,
    target_user_id: str,
    previous_value: Any,
    new_value: Any,
    reason: str = "",
) -> None:
    """Public wrapper around ``_record_admin_change`` for external callers."""
    _record_admin_change(actor_id, action, target_user_id, previous_value, new_value, reason)


def update_user(
    actor_id: str | None,
    user_id: str,
    updates: dict[str, Any],
    reason: str = "",
) -> tuple[bool, Any]:
    """
    Apply allowed profile-field updates to a registered user (task_048_002).

    Only fields listed in ``_UPDATABLE_FIELDS`` (currently ``email``) are
    accepted.  Role and status have dedicated functions.

    Returns ``(True, updated_user_dict)`` on success, ``(False, error_message)``
    on failure.
    """
    user = _USER_REGISTRY.get(user_id)
    if user is None:
        return False, f"User '{user_id}' not found."

    unknown = set(updates) - _UPDATABLE_FIELDS
    if unknown:
        return False, f"Non-updatable fields: {', '.join(sorted(unknown))}. Use dedicated endpoints for role/status."

    if not updates:
        return False, "No updatable fields provided."

    previous_snapshot: dict[str, Any] = {k: user[k] for k in updates if k in user}
    new_snapshot: dict[str, Any] = {}

    if "email" in updates:
        new_email = (updates["email"] or "").strip()
        if not new_email:
            return False, "'email' must not be empty."
        if not _EMAIL_RE.match(new_email):
            return False, "Invalid email address format."
        user["email"] = new_email
        new_snapshot["email"] = new_email

    _record_admin_change(actor_id, "admin:user_updated", user_id, previous_snapshot, new_snapshot, reason)
    return True, dict(user)


def check_user_login_allowed(user_id: str) -> tuple[bool, str]:
    """
    Determine whether a registered user may make authenticated API calls
    (task_048_003).

    Returns ``(True, "")`` when access is permitted.
    Returns ``(False, reason)`` when the user exists but is inactive or
    suspended.  Unknown user IDs are *not* blocked here — the absence from
    the registry means the user was never explicitly deactivated, which is
    the expected state for demo/seeded identities.
    """
    user = _USER_REGISTRY.get(user_id)
    if user is None:
        return True, ""  # unregistered — allow (default-open for backward compat)
    status = user.get("status", "active")
    if status == "inactive":
        return False, f"Account '{user_id}' is deactivated. Contact an administrator."
    if status == "suspended":
        return False, f"Account '{user_id}' is suspended pending review."
    return True, ""


# =============================================================================
# EP-005 US-049: Password Reset Flow (task_049_001 – task_049_004)
# =============================================================================

# ---------------------------------------------------------------------------
# Bounded in-process stores (replace with persistent/distributed store in prod)
# ---------------------------------------------------------------------------

# Maps token_value → {user_id, expires_at, issued_at, used}
_RESET_TOKEN_STORE: dict[str, dict[str, Any]] = {}

# Maps user_id → current active (unused) token for old-token invalidation.
_USER_ACTIVE_TOKEN: dict[str, str] = {}

# Sliding-window rate limit store: key → list of ISO-8601 request timestamps.
_RATE_LIMIT_STORE: dict[str, list[str]] = {}

# Simulated outbound security notification log (email in production).
_SECURITY_NOTIFICATIONS: list[dict[str, Any]] = []
_SECURITY_NOTIFICATIONS_MAX = 2000

# Password reset security event audit log.
_PASSWORD_RESET_AUDIT_LOG: list[dict[str, Any]] = []
_PASSWORD_RESET_AUDIT_LOG_MAX = 2000

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

_RESET_TOKEN_TTL_SECONDS: int = 900     # 15 minutes
_RATE_LIMIT_MAX_REQUESTS: int = 5       # per window per rate-limit key
_RATE_LIMIT_WINDOW_SECONDS: int = 3600  # 1 hour rolling window
_PASSWORD_MIN_LENGTH: int = 8

# ---------------------------------------------------------------------------
# Internal helpers (task_049_002 / task_049_004)
# ---------------------------------------------------------------------------


def _hash_password(password: str) -> str:
    """Return a PBKDF2-HMAC-SHA256 salted hash as ``'salt_hex:hash_hex'``."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{dk.hex()}"


def _check_password_policy(password: str) -> str | None:
    """Return an error message when *password* violates policy, else ``None``."""
    if not password:
        return "Password must not be empty."
    if len(password) < _PASSWORD_MIN_LENGTH:
        return f"Password must be at least {_PASSWORD_MIN_LENGTH} characters."
    return None


def _is_rate_limited(key: str) -> bool:
    """
    Sliding-window rate-limit check and recorder for *key*.

    Records the current request.  Returns ``True`` when the request count
    inside the window has already reached ``_RATE_LIMIT_MAX_REQUESTS``
    (blocking the caller).  Returns ``False`` and records the attempt
    otherwise (allowing the caller to proceed).
    """
    now = datetime.now(timezone.utc)
    window_start = now.timestamp() - _RATE_LIMIT_WINDOW_SECONDS
    timestamps = _RATE_LIMIT_STORE.get(key, [])
    recent = [
        ts for ts in timestamps
        if datetime.fromisoformat(ts).timestamp() >= window_start
    ]
    if len(recent) >= _RATE_LIMIT_MAX_REQUESTS:
        _RATE_LIMIT_STORE[key] = recent  # persist pruned list
        return True
    recent.append(now.isoformat())
    _RATE_LIMIT_STORE[key] = recent
    return False


def _log_password_security_event(
    event_type: str,
    user_id: str | None,
    source_ip: str | None,
    details: dict[str, Any],
) -> None:
    """Append a password-reset security event to the bounded audit log."""
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "source_ip": source_ip,
        **details,
    }
    _PASSWORD_RESET_AUDIT_LOG.append(entry)
    if len(_PASSWORD_RESET_AUDIT_LOG) > _PASSWORD_RESET_AUDIT_LOG_MAX:
        del _PASSWORD_RESET_AUDIT_LOG[
            : len(_PASSWORD_RESET_AUDIT_LOG) - _PASSWORD_RESET_AUDIT_LOG_MAX
        ]
    logger.info(
        "PASSWORD_RESET | event=%s user=%s ip=%s",
        event_type,
        user_id,
        source_ip,
    )


def _dispatch_security_notification(
    user_id: str,
    email: str,
    event_type: str,
) -> None:
    """Record a simulated security notification in the bounded notification log."""
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "to": email,
        "user_id": user_id,
        "event_type": event_type,
    }
    _SECURITY_NOTIFICATIONS.append(entry)
    if len(_SECURITY_NOTIFICATIONS) > _SECURITY_NOTIFICATIONS_MAX:
        del _SECURITY_NOTIFICATIONS[
            : len(_SECURITY_NOTIFICATIONS) - _SECURITY_NOTIFICATIONS_MAX
        ]
    logger.info(
        "SECURITY_NOTIFICATION | user=%s type=%s to=%s",
        user_id,
        event_type,
        email,
    )


# ---------------------------------------------------------------------------
# Public API (task_049_001 / task_049_002 / task_049_003 / task_049_004)
# ---------------------------------------------------------------------------

def request_password_reset(
    email_or_id: str,
    source_ip: str | None = None,
) -> dict[str, Any]:
    """
    Handle a password reset request (task_049_001 / task_049_004).

    Privacy-safe: always returns the same generic message regardless of
    whether an account exists, so callers cannot enumerate accounts.

    Rate-limited per source IP and per submitted identity.  When an active
    account is found the previous unused token (if any) is invalidated, a new
    high-entropy one-time token is issued, and a simulated notification is
    dispatched.

    Returns a dict with:

    ``message``
        Generic string safe to show the end-user.
    ``token``
        The newly issued reset token (``None`` when no token was generated).
    ``rate_limited``
        ``True`` when the call was blocked by rate limiting.
    """
    _GENERIC_MSG = (
        "If an account with that identity exists, a reset link has been sent."
    )

    # 1. Rate-limit by source IP (cheapest check; no user lookup needed).
    if source_ip and _is_rate_limited(f"ip:{source_ip}"):
        _log_password_security_event(
            "reset_rate_limited", None, source_ip, {"reason": "ip_rate_limit"}
        )
        return {"message": _GENERIC_MSG, "token": None, "rate_limited": True}

    # 2. Rate-limit by submitted identity (uniform key regardless of account
    #    existence — prevents using rate-limit timing to enumerate accounts).
    identity_key = f"identity:{email_or_id.lower()}"
    if _is_rate_limited(identity_key):
        _log_password_security_event(
            "reset_rate_limited", None, source_ip, {"reason": "identity_rate_limit"}
        )
        return {"message": _GENERIC_MSG, "token": None, "rate_limited": True}

    # 3. Locate the user account (active only; inactive/suspended receive no token).
    user: dict[str, Any] | None = None
    found_user_id: str | None = None

    candidate = _USER_REGISTRY.get(email_or_id)
    if candidate and candidate.get("status") == "active":
        user = candidate
        found_user_id = email_or_id

    if found_user_id is None:
        for uid, u in _USER_REGISTRY.items():
            if (
                u.get("email", "").lower() == email_or_id.lower()
                and u.get("status") == "active"
            ):
                user = u
                found_user_id = uid
                break

    if user is None or found_user_id is None:
        _log_password_security_event(
            "reset_no_user", None, source_ip, {"identity": email_or_id}
        )
        return {"message": _GENERIC_MSG, "token": None, "rate_limited": False}

    # 4. Invalidate any prior unused token for this user (task_049_002).
    old_token = _USER_ACTIVE_TOKEN.get(found_user_id)
    if old_token and old_token in _RESET_TOKEN_STORE:
        del _RESET_TOKEN_STORE[old_token]

    # 5. Issue a new cryptographically secure one-time token.
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.fromtimestamp(
        now.timestamp() + _RESET_TOKEN_TTL_SECONDS, tz=timezone.utc
    ).isoformat()
    _RESET_TOKEN_STORE[token] = {
        "user_id": found_user_id,
        "expires_at": expires_at,
        "issued_at": now.isoformat(),
        "used": False,
    }
    _USER_ACTIVE_TOKEN[found_user_id] = token

    # 6. Dispatch notification and record audit event (task_049_004).
    _dispatch_security_notification(
        found_user_id, user.get("email", ""), "password_reset_requested"
    )
    _log_password_security_event(
        "reset_token_issued", found_user_id, source_ip, {"expires_at": expires_at}
    )

    return {"message": _GENERIC_MSG, "token": token, "rate_limited": False}


def confirm_password_reset(token: str, new_password: str) -> tuple[bool, str]:
    """
    Validate *token*, enforce password policy, and update credentials
    atomically (task_049_003).

    Returns ``(True, user_id)`` on success.  The token is destroyed
    immediately and cannot be reused.

    Returns ``(False, error_message)`` for all failure cases.  Error messages
    for invalid/expired tokens are intentionally identical to prevent token
    enumeration.
    """
    _INVALID_TOKEN_MSG = "Invalid or expired reset token."

    # Validate token existence.
    entry = _RESET_TOKEN_STORE.get(token)
    if entry is None:
        _log_password_security_event("reset_confirm_invalid_token", None, None, {})
        return False, _INVALID_TOKEN_MSG

    # Guard: belt-and-suspenders check for already-used tokens.
    if entry.get("used"):
        _log_password_security_event(
            "reset_confirm_reused_token", entry.get("user_id"), None, {}
        )
        return False, _INVALID_TOKEN_MSG

    # Check expiry.
    now = datetime.now(timezone.utc)
    expires_at = datetime.fromisoformat(entry["expires_at"])
    if now > expires_at:
        del _RESET_TOKEN_STORE[token]
        expired_user_id = entry.get("user_id", "")
        _USER_ACTIVE_TOKEN.pop(expired_user_id, None)
        _log_password_security_event(
            "reset_confirm_expired_token", expired_user_id, None, {}
        )
        return False, _INVALID_TOKEN_MSG

    user_id = entry["user_id"]
    user = _USER_REGISTRY.get(user_id)
    if user is None:
        return False, _INVALID_TOKEN_MSG

    # Enforce password policy before committing any state change.
    policy_error = _check_password_policy(new_password)
    if policy_error:
        return False, policy_error

    # Atomic update: store hash, invalidate token, clean up index.
    user["password_hash"] = _hash_password(new_password)
    del _RESET_TOKEN_STORE[token]
    _USER_ACTIVE_TOKEN.pop(user_id, None)

    # Notify user and record audit event (task_049_004).
    _dispatch_security_notification(
        user_id, user.get("email", ""), "password_reset_completed"
    )
    _log_password_security_event("reset_confirm_success", user_id, None, {})

    return True, user_id


def get_password_reset_audit_log(limit: int = 100) -> list[dict[str, Any]]:
    """Return the most-recent *limit* password reset security events (newest first)."""
    return list(reversed(_PASSWORD_RESET_AUDIT_LOG[-limit:]))


def get_security_notifications(limit: int = 100) -> list[dict[str, Any]]:
    """Return the most-recent *limit* security notification records (newest first)."""
    return list(reversed(_SECURITY_NOTIFICATIONS[-limit:]))


# =============================================================================
# EP-005 US-051: Session Token Claims (task_051_001 – task_051_004)
# =============================================================================

# ---------------------------------------------------------------------------
# task_051_001: Token Claims Schema
# ---------------------------------------------------------------------------

# Canonical claims schema — living documentation and validation target.
# All fields carry non-PHI identifiers only.
SESSION_TOKEN_CLAIMS_SCHEMA: dict[str, str] = {
    "jti":         "Unique token ID (UUID4) — enables per-token revocation.",
    "sub":         "Subject: opaque user account ID (no PII/PHI).",
    "role":        "Authorization role: one of patient | staff | admin.",
    "permissions": "Snapshot of role-level allowed actions at issuance time.",
    "iss":         "Issuer: 'propeliq'.",
    "aud":         "Audience: 'propeliq-api'.",
    "iat":         "Issued-at: Unix timestamp (integer seconds since epoch).",
    "exp":         "Expiry: Unix timestamp (integer). Default TTL: 3600 s.",
}

# Fields that MUST NOT appear in a session token payload (PHI exclusion list).
TOKEN_PHI_EXCLUSION_LIST: frozenset[str] = frozenset(
    {
        "email", "phone", "name", "dob", "date_of_birth",
        "patient_id", "address", "ssn", "insurance_id",
        "medical_record_number", "first_name", "last_name",
    }
)

# ---------------------------------------------------------------------------
# Configuration constants (task_051_001 / task_051_002)
# ---------------------------------------------------------------------------

TOKEN_ISSUER: str = "propeliq"
TOKEN_AUDIENCE: str = "propeliq-api"
_SESSION_TOKEN_TTL_SECONDS: int = 3600  # 1 hour

# Signing secret — override via SESSION_TOKEN_SECRET env var in production.
# The default is intentionally weak and signals a misconfiguration.
_TOKEN_SECRET: bytes = (
    os.environ.get("SESSION_TOKEN_SECRET", "propeliq-dev-secret-CHANGE-IN-PROD")
).encode("utf-8")

# ---------------------------------------------------------------------------
# In-process revocation stores (task_051_003)
# Swap for Redis / DB set in production.
# ---------------------------------------------------------------------------

# Set of revoked token JTIs — any token whose JTI appears here is rejected.
_REVOKED_TOKEN_JTIS: set[str] = set()

# Maps user_id → set of active token JTIs for bulk revocation on role change.
_USER_SESSION_INDEX: dict[str, set[str]] = {}

# ---------------------------------------------------------------------------
# Encoding / signing helpers (task_051_002 internals)
# ---------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    """Base64url-encode *data* without padding characters."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Decode a base64url string (with or without padding)."""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _sign_payload(payload_b64: str) -> str:
    """Return HMAC-SHA256 hex digest over the base64url-encoded payload."""
    return _hmac.new(
        _TOKEN_SECRET, payload_b64.encode("utf-8"), hashlib.sha256
    ).hexdigest()


# ---------------------------------------------------------------------------
# task_051_001: Schema accessor
# ---------------------------------------------------------------------------


def get_session_token_schema() -> dict[str, str]:
    """Return the canonical session token claims schema (read-only copy)."""
    return dict(SESSION_TOKEN_CLAIMS_SCHEMA)


# ---------------------------------------------------------------------------
# task_051_002: Token issuance
# ---------------------------------------------------------------------------


def issue_session_token(user_id: str, role: str | None = None) -> dict[str, Any]:
    """Issue a signed, PHI-free session token for *user_id* (task_051_002).

    Payload is HMAC-SHA256 signed.  Token format::

        <base64url(json(claims))>.<hmac_sha256_hex>

    The token is registered in the user session index so it can be bulk-revoked
    by :func:`revoke_user_tokens` when the user's role or status changes.

    Returns a dict with:

    ``token``       — the opaque signed token string.
    ``jti``         — token ID (UUID4, for revocation tracking).
    ``expires_at``  — ISO-8601 expiry timestamp.
    ``claims``      — the full claims dict (for inspection / tests).
    """
    user = _USER_REGISTRY.get(user_id)
    effective_role = role or (user.get("role") if user else None) or "patient"
    if effective_role not in ROLES:
        effective_role = "patient"

    now = datetime.now(timezone.utc)
    iat = int(now.timestamp())
    exp = iat + _SESSION_TOKEN_TTL_SECONDS
    jti = str(uuid.uuid4())

    permissions: list[str] = sorted(
        action for action, allowed in PERMISSION_MATRIX.items()
        if effective_role in allowed
    )

    claims: dict[str, Any] = {
        "jti":         jti,
        "sub":         user_id,
        "role":        effective_role,
        "permissions": permissions,
        "iss":         TOKEN_ISSUER,
        "aud":         TOKEN_AUDIENCE,
        "iat":         iat,
        "exp":         exp,
    }

    payload_b64 = _b64url_encode(
        json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    sig = _sign_payload(payload_b64)
    token_str = f"{payload_b64}.{sig}"

    # Register in session index for revocation
    _USER_SESSION_INDEX.setdefault(user_id, set()).add(jti)

    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
    logger.info("SESSION_TOKEN issued | sub=%s role=%s jti=%s", user_id, effective_role, jti)
    return {
        "token":      token_str,
        "jti":        jti,
        "expires_at": expires_at,
        "claims":     claims,
    }


# ---------------------------------------------------------------------------
# task_051_002: Token validation
# ---------------------------------------------------------------------------


def validate_session_token(token: str) -> dict[str, Any] | None:
    """Validate a session token: signature, expiry, revocation, iss/aud.

    Returns the claims dict on success; ``None`` on any failure.

    All failure branches return ``None`` (no information leakage about
    *which* check failed to the caller).
    """
    if not token:
        return None

    parts = token.split(".")
    if len(parts) != 2:
        return None

    payload_b64, sig = parts

    # Constant-time comparison prevents timing-based token enumeration.
    expected_sig = _sign_payload(payload_b64)
    if not _hmac.compare_digest(sig, expected_sig):
        return None

    try:
        claims: dict[str, Any] = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None

    # Validate issuer and audience
    if claims.get("iss") != TOKEN_ISSUER or claims.get("aud") != TOKEN_AUDIENCE:
        return None

    # Check expiry
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts > claims.get("exp", 0):
        return None

    # Check per-token revocation
    jti = claims.get("jti")
    if jti and jti in _REVOKED_TOKEN_JTIS:
        return None

    return claims


# ---------------------------------------------------------------------------
# task_051_002: Bearer token claims extractor
# ---------------------------------------------------------------------------


def get_bearer_token_claims(
    environ: dict[str, Any],
) -> tuple[dict[str, Any] | None, bool]:
    """Extract and validate the Bearer token from the Authorization header.

    Returns
    -------
    ``(claims, True)``  — a valid token is present.
    ``(None, True)``    — a token is present but invalid/expired.
    ``(None, False)``   — no Bearer token header found.
    """
    auth_header = (environ.get("HTTP_AUTHORIZATION") or "").strip()
    if not auth_header.lower().startswith("bearer "):
        return None, False
    token_str = auth_header[7:].strip()
    claims = validate_session_token(token_str)
    return claims, True


# ---------------------------------------------------------------------------
# task_051_003: Token invalidation on role / status change
# ---------------------------------------------------------------------------


def revoke_user_tokens(user_id: str) -> int:
    """Revoke all active session tokens for *user_id* (task_051_003).

    Called automatically by :func:`assign_user_role` and
    :func:`set_user_status` whenever a user's authorization context changes.
    Any request bearing a stale token will receive a 401 Unauthorized because
    :func:`validate_session_token` rejects JTIs in ``_REVOKED_TOKEN_JTIS``.

    Returns the number of tokens revoked.
    """
    active_jtis = _USER_SESSION_INDEX.pop(user_id, set())
    for jti in active_jtis:
        _REVOKED_TOKEN_JTIS.add(jti)
    count = len(active_jtis)
    if count:
        logger.info("SESSION_TOKEN revoked | sub=%s count=%d", user_id, count)
    return count


def get_active_token_count(user_id: str) -> int:
    """Return the number of non-revoked active tokens for *user_id* (test helper)."""
    active_jtis = _USER_SESSION_INDEX.get(user_id, set())
    return sum(1 for jti in active_jtis if jti not in _REVOKED_TOKEN_JTIS)


# =============================================================================
# EP-005 US-052: Admin Audit Log Viewer (task_052_001 – task_052_004)
# =============================================================================

# Sensitive sub-keys within previous_value / new_value that must be masked
# in detail views and exports (task_052_003 / task_052_004).
_AUDIT_SENSITIVE_KEYS: frozenset[str] = frozenset({"email", "phone", "password_hash"})


def mask_audit_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *entry* with sensitive sub-field values masked (task_052_003).

    Keys listed in ``_AUDIT_SENSITIVE_KEYS`` inside ``previous_value`` and
    ``new_value`` (when those are dicts) are replaced with ``"***"``.
    Non-dict values pass through unchanged.
    """
    def _mask(value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        return {k: "***" if k in _AUDIT_SENSITIVE_KEYS else v for k, v in value.items()}

    masked = dict(entry)
    if "previous_value" in masked:
        masked["previous_value"] = _mask(masked["previous_value"])
    if "new_value" in masked:
        masked["new_value"] = _mask(masked["new_value"])
    return masked


def get_admin_change_log_entry(entry_id: str) -> dict[str, Any] | None:
    """Return a single audit entry by its ``entry_id``, or ``None`` if not found (task_052_003)."""
    for entry in _ADMIN_CHANGE_LOG:
        if entry.get("entry_id") == entry_id:
            return dict(entry)
    return None


def query_admin_change_log(
    actor: str | None = None,
    action: str | None = None,
    target_user: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Paginated, filtered audit log query with total count (task_052_001 / task_052_002).

    Returns a dict with:

    ``entries``   — page of matching entries (newest first).
    ``total``     — total matching count across all pages.
    ``page``      — requested page number (1-based).
    ``page_size`` — entries per page (capped at 500).
    ``pages``     — total number of pages.
    ``filters``   — echo of the applied filter values.
    """
    entries: list[dict[str, Any]] = list(reversed(_ADMIN_CHANGE_LOG))
    if actor:
        entries = [e for e in entries if e.get("actor") == actor]
    if action:
        entries = [e for e in entries if e.get("action") == action]
    if target_user:
        entries = [e for e in entries if e.get("target_user_id") == target_user]
    if from_ts:
        entries = [e for e in entries if e.get("timestamp", "") >= from_ts]
    if to_ts:
        entries = [e for e in entries if e.get("timestamp", "") <= to_ts]

    total = len(entries)
    page = max(1, page)
    page_size = max(1, min(page_size, 500))
    pages = max(1, (total + page_size - 1) // page_size) if total else 1
    start = (page - 1) * page_size
    paged = entries[start : start + page_size]

    return {
        "entries":   paged,
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     pages,
        "filters": {
            "actor":       actor,
            "action":      action,
            "target_user": target_user,
            "from_ts":     from_ts,
            "to_ts":       to_ts,
        },
    }


def export_admin_change_log(
    actor: str | None = None,
    action: str | None = None,
    target_user: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
    fmt: str = "json",
) -> tuple[bytes, str, str]:
    """Export filtered audit log as CSV or JSON bytes (task_052_004).

    Sensitive sub-fields are masked before export.  Returns a tuple of
    ``(content_bytes, content_type, filename)``.
    """
    result = query_admin_change_log(
        actor=actor, action=action, target_user=target_user,
        from_ts=from_ts, to_ts=to_ts,
        page=1, page_size=10_000,   # fetch all matching entries
    )
    entries = [mask_audit_entry(e) for e in result["entries"]]
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if fmt == "csv":
        buf = io.StringIO()
        fieldnames = [
            "entry_id", "timestamp", "actor", "action",
            "target_user_id", "previous_value", "new_value", "reason",
        ]
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for e in entries:
            row = dict(e)
            # Stringify complex values so they fit in a CSV cell
            if isinstance(row.get("previous_value"), dict):
                row["previous_value"] = json.dumps(row["previous_value"])
            if isinstance(row.get("new_value"), dict):
                row["new_value"] = json.dumps(row["new_value"])
            writer.writerow(row)
        content = buf.getvalue().encode("utf-8")
        filename = f"audit_log_{timestamp_str}.csv"
        return content, "text/csv", filename
    else:
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total":       len(entries),
            "entries":     entries,
        }
        content = json.dumps(payload, indent=2).encode("utf-8")
        filename = f"audit_log_{timestamp_str}.json"
        return content, "application/json", filename


