from __future__ import annotations

import json
import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import parse_qs

from src.booking_service import (
    authorize_provider,
    build_calendar_payload,
    complete_provider_authorization,
    create_checkout_reservation,
    dashboard_metrics,
    disconnect_provider,
    finalize_booking,
    get_appointment_details,
    get_integration_state,
    get_patient_profile,
    get_staff_queue,
    process_calendar_sync_queue,
    process_confirmation_queue,
    process_due_reminders,
    process_preferred_swaps,
    resend_confirmation,
    run_pull_reconciliation,
)
from src.clinical_intelligence import (
    aggregate_patient_profile,
    detect_medication_conflicts,
    generate_signed_document_url,
    get_360_profile,
    get_document_status,
    get_source_metadata,
    process_document,
    upload_document,
    validate_signed_url,
)
from src.coding_engine import (
    detect_allergy_drug_conflicts,
    generate_code_suggestions,
    get_conflict_queue,
    get_suggestions,
    get_threshold_history,
    get_thresholds,
    resolve_conflict,
    review_code_suggestion,
    update_threshold,
)
from src.db import DEFAULT_DB_PATH, initialize_database, get_connection
from src.rbac import (
    assign_user_role,
    check_user_login_allowed,
    confirm_password_reset,
    export_admin_change_log,
    filter_staff_patient_detail,
    get_admin_change_log,
    get_admin_change_log_entry,
    get_admin_id_from_environ,
    get_audit_log,
    get_bearer_token_claims,
    get_password_reset_audit_log,
    get_patient_id_from_environ,
    get_permission_matrix,
    get_role_from_environ,
    get_security_notifications,
    get_session_token_schema,
    get_staff_access_log,
    get_staff_assigned_providers,
    get_staff_id_from_environ,
    get_user,
    issue_session_token,
    list_users,
    log_staff_access_event,
    mask_audit_entry,
    query_admin_change_log,
    record_admin_event,
    register_user,
    request_password_reset,
    require_appointment_ownership,
    require_permission,
    require_resource_scope,
    require_staff_assignment,
    set_user_status,
    update_user,
    validate_session_token,
)
from src.search_service import (
    book_appointment,
    get_provider,
    list_specialties,
    parse_filters,
    search_appointments,
    suggest_providers,
)

BASE_DIR = Path(__file__).resolve().parents[1]
PUBLIC_DIR = BASE_DIR / "public"


@dataclass
class SearchMetrics:
    total_queries: int = 0
    empty_results: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    def record(self, latency_ms: float, result_count: int) -> None:
        self.total_queries += 1
        if result_count == 0:
            self.empty_results += 1
        self.latencies_ms.append(latency_ms)
        if len(self.latencies_ms) > 2000:
            self.latencies_ms = self.latencies_ms[-1000:]

    def snapshot(self) -> dict[str, Any]:
        if not self.latencies_ms:
            return {
                "totalQueries": self.total_queries,
                "emptyResults": self.empty_results,
                "emptyResultRate": 0,
                "p95LatencyMs": 0,
                "averageLatencyMs": 0,
                "alertBreached": False,
            }

        ordered = sorted(self.latencies_ms)
        p95_index = max(0, int(len(ordered) * 0.95) - 1)
        p95 = round(ordered[p95_index], 2)
        avg = round(sum(self.latencies_ms) / len(self.latencies_ms), 2)
        empty_rate = round((self.empty_results / max(1, self.total_queries)) * 100, 2)

        return {
            "totalQueries": self.total_queries,
            "emptyResults": self.empty_results,
            "emptyResultRate": empty_rate,
            "p95LatencyMs": p95,
            "averageLatencyMs": avg,
            "alertBreached": p95 > 2000,
        }


def create_app(db_path: Path | None = None):
    selected_db = db_path or DEFAULT_DB_PATH
    initialize_database(selected_db)
    metrics = SearchMetrics()

    def app(environ, start_response):
        started_at = perf_counter()
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")

        # --- EP-005 US-048 task_048_003: Deactivation login block ---
        # For any authenticated API call, verify the requesting user's account
        # is active.  We check whichever identity header is present and
        # registered in the user registry.  Unknown IDs pass through so that
        # demo/seed identities (which are never registered) continue to work.
        if path.startswith("/api/"):
            _uid_to_check = (
                environ.get("HTTP_X_ADMIN_ID")
                or environ.get("HTTP_X_STAFF_ID")
            )
            if _uid_to_check:
                _login_ok, _login_msg = check_user_login_allowed(_uid_to_check)
                if not _login_ok:
                    return _json_response(
                        start_response, 403,
                        {"success": False, "error": {"code": "ACCOUNT_DEACTIVATED", "message": _login_msg}},
                    )

        # --- EP-005 US-051 task_051_002: Bearer token 401 enforcement ---
        # If an Authorization: Bearer header is present, the token MUST be
        # valid.  An invalid / expired token returns 401 before any route
        # matching occurs.  Requests without a Bearer header continue to
        # use the legacy X-Role header (backward compatibility).
        if path.startswith("/api/"):
            _bearer_claims, _bearer_present = get_bearer_token_claims(environ)
            if _bearer_present and _bearer_claims is None:
                return _json_response(
                    start_response, 401,
                    {"success": False, "error": {"code": "UNAUTHORIZED", "message": "Invalid or expired session token."}},
                )

        if method == "GET" and path == "/api/appointments/search":
            return _handle_search(environ, start_response, selected_db, metrics, started_at)

        if method == "GET" and path == "/api/appointments/specialties":
            return _handle_specialties(start_response, selected_db)

        if method == "GET" and path == "/api/providers/suggest":
            return _handle_provider_suggest(environ, start_response, selected_db)

        if method == "GET" and path == "/api/appointments/calendar":
            return _handle_calendar(environ, start_response, selected_db)

        appointment_match = re.match(r"^/api/appointments/(\d+)$", path)
        if method == "GET" and appointment_match:
            return _handle_appointment_details(environ, start_response, selected_db, int(appointment_match.group(1)))

        provider_match = re.match(r"^/api/providers/(\d+)$", path)
        if method == "GET" and provider_match:
            return _handle_provider_details(start_response, selected_db, int(provider_match.group(1)))

        checkout_match = re.match(r"^/api/appointments/(\d+)/checkout$", path)
        if method == "POST" and checkout_match:
            return _handle_checkout(environ, start_response, selected_db, int(checkout_match.group(1)))

        if method == "POST" and path == "/api/appointments/book":
            return _handle_finalize_booking(environ, start_response, selected_db)

        book_match = re.match(r"^/api/appointments/(\d+)/book$", path)
        if method == "POST" and book_match:
            return _handle_book_appointment(start_response, selected_db, int(book_match.group(1)))

        if method == "GET" and path == "/api/patient/profile":
            # task_050_002: explicit permission assertion before ownership scope check
            denial = require_permission(environ, "appointments:view")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            scope_denial = require_resource_scope(environ, _DEFAULT_PATIENT_ID)
            if scope_denial:
                _, msg = scope_denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_patient_profile(start_response, selected_db)

        if method == "GET" and path == "/api/integrations/status":
            scope_denial = require_resource_scope(environ, _DEFAULT_PATIENT_ID)
            if scope_denial:
                _, msg = scope_denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_integration_status(start_response, selected_db)

        auth_authorize_match = re.match(r"^/api/auth/(google|outlook)/authorize$", path)
        if method == "GET" and auth_authorize_match:
            return _handle_auth_authorize(start_response, selected_db, auth_authorize_match.group(1))

        auth_callback_match = re.match(r"^/api/auth/(google|outlook)/callback$", path)
        if method == "GET" and auth_callback_match:
            return _handle_auth_callback(environ, start_response, selected_db, auth_callback_match.group(1))

        auth_disconnect_match = re.match(r"^/api/auth/(google|outlook)/disconnect$", path)
        if method == "POST" and auth_disconnect_match:
            return _handle_auth_disconnect(start_response, selected_db, auth_disconnect_match.group(1))

        # --- EP-005 US-049: Password reset flow ---
        if method == "POST" and path == "/api/auth/password-reset/request":
            return _handle_password_reset_request(environ, start_response)

        if method == "POST" and path == "/api/auth/password-reset/confirm":
            return _handle_password_reset_confirm(environ, start_response)

        # --- EP-005 US-051: Session token issuance and schema ---
        if method == "POST" and path == "/api/auth/session":
            return _handle_session_token_issue(environ, start_response)

        if method == "GET" and path == "/api/auth/session/schema":
            return _json_response(
                start_response, 200,
                {"success": True, "data": get_session_token_schema()},
            )

        if method == "POST" and path == "/api/jobs/process-confirmations":
            denial = require_permission(environ, "admin:ops_jobs")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_process_confirmations(start_response, selected_db)

        resend_match = re.match(r"^/api/appointments/(\d+)/resend-confirmation$", path)
        if method == "POST" and resend_match:
            denial = require_permission(environ, "appointments:resend")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_resend_confirmation(start_response, selected_db, int(resend_match.group(1)))

        if method == "POST" and path == "/api/jobs/process-reminders":
            denial = require_permission(environ, "admin:ops_jobs")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_process_reminders(start_response, selected_db)

        if method == "POST" and path == "/api/jobs/process-swaps":
            denial = require_permission(environ, "admin:ops_jobs")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_process_swaps(start_response, selected_db)

        if method == "POST" and path == "/api/jobs/process-calendar-sync":
            denial = require_permission(environ, "admin:ops_jobs")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_process_calendar_sync(start_response, selected_db)

        if method == "POST" and path == "/api/jobs/reconcile-calendar-sync":
            denial = require_permission(environ, "admin:ops_jobs")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_reconcile_sync(start_response, selected_db)

        if method == "GET" and path == "/api/dashboard/metrics":
            denial = require_permission(environ, "admin:dashboard")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_dashboard_metrics(start_response, selected_db)

        if method == "GET" and path == "/api/metrics/search":
            return _json_response(start_response, 200, {"success": True, "data": metrics.snapshot()})

        # --- EP-005: RBAC endpoints ---
        if method == "GET" and path == "/api/auth/me":
            return _handle_rbac_me(environ, start_response)

        if method == "GET" and path == "/api/rbac/permissions":
            return _handle_rbac_permissions(environ, start_response)

        if method == "GET" and path == "/api/rbac/audit-log":
            return _handle_rbac_audit_log(environ, start_response)

        # --- EP-003: Clinical Intelligence Platform ---
        if method == "POST" and path == "/api/clinical/documents/upload":
            denial = require_permission(environ, "clinical:upload_document")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_clinical_upload(environ, start_response, selected_db)

        clinical_doc_status_match = re.match(r"^/api/clinical/documents/(\d+)/status$", path)
        if method == "GET" and clinical_doc_status_match:
            denial = require_permission(environ, "clinical:view_profile")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_clinical_doc_status(environ, start_response, selected_db, int(clinical_doc_status_match.group(1)))

        clinical_doc_process_match = re.match(r"^/api/clinical/documents/(\d+)/process$", path)
        if method == "POST" and clinical_doc_process_match:
            denial = require_permission(environ, "clinical:process_document")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_clinical_doc_process(environ, start_response, selected_db, int(clinical_doc_process_match.group(1)))

        clinical_doc_signed_url_match = re.match(r"^/api/clinical/documents/(\d+)/signed-url$", path)
        if method == "GET" and clinical_doc_signed_url_match:
            denial = require_permission(environ, "clinical:view_profile")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_clinical_signed_url(environ, start_response, selected_db, int(clinical_doc_signed_url_match.group(1)))

        clinical_doc_preview_match = re.match(r"^/api/clinical/documents/(\d+)/preview$", path)
        if method == "GET" and clinical_doc_preview_match:
            denial = require_permission(environ, "clinical:view_profile")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_clinical_doc_preview(environ, start_response, selected_db, int(clinical_doc_preview_match.group(1)))

        clinical_profile_match = re.match(r"^/api/clinical/patients/(\d+)/profile$", path)
        if method == "GET" and clinical_profile_match:
            patient_id = int(clinical_profile_match.group(1))
            denial = require_permission(environ, "clinical:view_profile")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            scope_denial = require_resource_scope(environ, patient_id)
            if scope_denial:
                _, msg = scope_denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_clinical_profile(start_response, selected_db, patient_id)

        clinical_aggregate_match = re.match(r"^/api/clinical/patients/(\d+)/aggregate$", path)
        if method == "POST" and clinical_aggregate_match:
            denial = require_permission(environ, "clinical:process_document")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_clinical_aggregate(environ, start_response, selected_db, int(clinical_aggregate_match.group(1)))

        clinical_conflicts_match = re.match(r"^/api/clinical/patients/(\d+)/conflicts$", path)
        if method == "GET" and clinical_conflicts_match:
            denial = require_permission(environ, "clinical:view_conflicts")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_clinical_conflicts(start_response, selected_db, int(clinical_conflicts_match.group(1)))

        clinical_element_source_match = re.match(r"^/api/clinical/elements/(\d+)/source$", path)
        if method == "GET" and clinical_element_source_match:
            denial = require_permission(environ, "clinical:view_profile")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_clinical_element_source(environ, start_response, selected_db, int(clinical_element_source_match.group(1)))

        # --- EP-003: Coding Engine (TASK-025 through TASK-030) ---
        clinical_allergy_conflicts_match = re.match(r"^/api/clinical/patients/(\d+)/allergy-conflicts$", path)
        if method == "GET" and clinical_allergy_conflicts_match:
            denial = require_permission(environ, "clinical:view_allergy_conflicts")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_allergy_conflicts(start_response, selected_db, int(clinical_allergy_conflicts_match.group(1)))

        clinical_suggest_match = re.match(r"^/api/clinical/patients/(\d+)/suggestions$", path)
        if method == "GET" and clinical_suggest_match:
            denial = require_permission(environ, "clinical:view_suggestions")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_get_suggestions(environ, start_response, selected_db, int(clinical_suggest_match.group(1)))
        if method == "POST" and clinical_suggest_match:
            denial = require_permission(environ, "clinical:generate_suggestions")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_generate_suggestions(environ, start_response, selected_db, int(clinical_suggest_match.group(1)))

        coding_review_match = re.match(r"^/api/coding/suggestions/(\d+)/review$", path)
        if method == "POST" and coding_review_match:
            denial = require_permission(environ, "clinical:code_review")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_code_review(environ, start_response, selected_db, int(coding_review_match.group(1)))

        if method == "GET" and path == "/api/clinical/thresholds":
            denial = require_permission(environ, "clinical:view_profile")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_get_thresholds(start_response, selected_db)

        if method == "PUT" and path == "/api/clinical/thresholds":
            denial = require_permission(environ, "clinical:manage_thresholds")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_update_threshold(environ, start_response, selected_db)

        if method == "GET" and path == "/api/clinical/thresholds/history":
            denial = require_permission(environ, "admin:audit_logs")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_threshold_history(environ, start_response, selected_db)

        if method == "GET" and path == "/api/clinical/conflicts/queue":
            denial = require_permission(environ, "clinical:view_conflicts")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_conflict_queue(environ, start_response, selected_db)

        conflict_resolve_match = re.match(r"^/api/clinical/conflicts/(\d+)/resolve$", path)
        if method == "POST" and conflict_resolve_match:
            denial = require_permission(environ, "clinical:resolve_conflict")
            if denial:
                _, msg = denial
                return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
            return _handle_resolve_conflict(environ, start_response, selected_db, int(conflict_resolve_match.group(1)))

        # --- EP-005 US-046/047: Admin user management and change log ---
        if method == "POST" and path == "/api/admin/users":
            return _handle_admin_create_user(environ, start_response)

        if method == "GET" and path == "/api/admin/users":
            return _handle_admin_list_users(environ, start_response)

        admin_user_match = re.match(r"^/api/admin/users/([^/]+)$", path)
        if method == "GET" and admin_user_match:
            return _handle_admin_get_user(environ, start_response, admin_user_match.group(1))
        if method == "PATCH" and admin_user_match:
            return _handle_admin_update_user(environ, start_response, admin_user_match.group(1))

        admin_role_match = re.match(r"^/api/admin/users/([^/]+)/role$", path)
        if method == "PATCH" and admin_role_match:
            return _handle_admin_assign_role(environ, start_response, admin_role_match.group(1))

        admin_status_match = re.match(r"^/api/admin/users/([^/]+)/status$", path)
        if method == "PATCH" and admin_status_match:
            return _handle_admin_set_status(environ, start_response, admin_status_match.group(1))

        if method == "GET" and path == "/api/admin/change-log":
            return _handle_admin_change_log(environ, start_response)

        # --- EP-005 US-052: Audit log entry detail and export ---
        audit_entry_match = re.match(r"^/api/admin/change-log/entry/([^/]+)$", path)
        if method == "GET" and audit_entry_match:
            return _handle_audit_log_entry(environ, start_response, audit_entry_match.group(1))

        if method == "GET" and path == "/api/admin/change-log/export":
            return _handle_audit_log_export(environ, start_response)

        # --- EP-005 US-045: Staff assignment-scoped queue and check-in ---
        if method == "GET" and path == "/api/staff/queue":
            return _handle_staff_queue(environ, start_response, selected_db)

        staff_patient_detail_match = re.match(r"^/api/staff/patients/(\d+)/detail$", path)
        if method == "GET" and staff_patient_detail_match:
            return _handle_staff_patient_detail(
                environ, start_response, selected_db, int(staff_patient_detail_match.group(1))
            )

        staff_checkin_match = re.match(r"^/api/staff/appointments/(\d+)/checkin$", path)
        if method == "POST" and staff_checkin_match:
            return _handle_staff_checkin(
                environ, start_response, selected_db, int(staff_checkin_match.group(1))
            )

        if method == "GET" and path == "/api/staff/access-log":
            return _handle_staff_access_log(environ, start_response)

        if path.startswith("/api/"):
            return _json_response(
                start_response,
                404,
                {
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "API route not found",
                    },
                },
            )

        return _serve_static(path, start_response)

    return app


def _handle_search(environ, start_response, db_path: Path, metrics: SearchMetrics, started_at: float):
    query_params = _flat_query_params(environ.get("QUERY_STRING", ""))

    with get_connection(db_path) as connection:
        validated = parse_filters(query_params, connection)
        if validated.errors:
            return _json_response(
                start_response,
                400,
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid search parameters",
                        "details": validated.errors,
                    },
                },
            )

        results = search_appointments(connection, validated.data)

    elapsed_ms = (perf_counter() - started_at) * 1000
    metrics.record(elapsed_ms, len(results["items"]))

    return _json_response(
        start_response,
        200,
        {
            "success": True,
            "data": results,
            "meta": {
                "latencyMs": round(elapsed_ms, 2),
            },
        },
    )


def _handle_specialties(start_response, db_path: Path):
    with get_connection(db_path) as connection:
        rows = list_specialties(connection)
    return _json_response(start_response, 200, {"success": True, "data": rows})


def _handle_provider_suggest(environ, start_response, db_path: Path):
    params = _flat_query_params(environ.get("QUERY_STRING", ""))
    query = (params.get("query") or "").strip()
    if len(query) < 2:
        return _json_response(start_response, 200, {"success": True, "data": []})

    with get_connection(db_path) as connection:
        rows = suggest_providers(connection, query)
    return _json_response(start_response, 200, {"success": True, "data": rows})


def _handle_calendar(environ, start_response, db_path: Path):
    query_params = _flat_query_params(environ.get("QUERY_STRING", ""))
    with get_connection(db_path) as connection:
        validated = parse_filters(query_params, connection)
        if validated.errors:
            return _json_response(
                start_response,
                400,
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid calendar parameters",
                        "details": validated.errors,
                    },
                },
            )
        data = build_calendar_payload(
            connection,
            validated.data,
            query_params.get("view", "month"),
            query_params.get("anchorDate"),
        )
    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_appointment_details(environ, start_response, db_path: Path, appointment_id: int):
    with get_connection(db_path) as connection:
        data = get_appointment_details(connection, appointment_id)
    if data is None:
        return _json_response(
            start_response,
            404,
            {"success": False, "error": {"code": "APPOINTMENT_NOT_FOUND", "message": "Appointment not found"}},
        )
    # task_044_001: enforce patient ownership for booked appointments
    ownership_denial = require_appointment_ownership(environ, data, _DEFAULT_PATIENT_ID)
    if ownership_denial:
        _, msg = ownership_denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_provider_details(start_response, db_path: Path, provider_id: int):
    with get_connection(db_path) as connection:
        data = get_provider(connection, provider_id)

    if data is None:
        return _json_response(
            start_response,
            404,
            {
                "success": False,
                "error": {
                    "code": "PROVIDER_NOT_FOUND",
                    "message": "Provider not found",
                },
            },
        )

    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_book_appointment(start_response, db_path: Path, appointment_id: int):
    with get_connection(db_path) as connection:
        booked = book_appointment(connection, appointment_id)

    if not booked:
        return _json_response(
            start_response,
            409,
            {
                "success": False,
                "error": {
                    "code": "UNAVAILABLE_SLOT",
                    "message": "Selected appointment slot is no longer available",
                },
            },
        )

    return _json_response(
        start_response,
        200,
        {"success": True, "data": {"appointmentId": appointment_id, "status": "booked"}},
    )


def _handle_checkout(environ, start_response, db_path: Path, appointment_id: int):
    payload = _read_json_body(environ)
    with get_connection(db_path) as connection:
        status_code, data = create_checkout_reservation(connection, appointment_id, payload)
    success = status_code == 200
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_finalize_booking(environ, start_response, db_path: Path):
    payload = _read_json_body(environ)
    reservation_token = payload.get("reservationToken")
    if not reservation_token:
        return _json_response(
            start_response,
            400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "reservationToken is required"}},
        )
    with get_connection(db_path) as connection:
        status_code, data = finalize_booking(connection, reservation_token, payload)
    success = status_code == 200
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_patient_profile(start_response, db_path: Path):
    with get_connection(db_path) as connection:
        profile = get_patient_profile(connection)
    return _json_response(start_response, 200, {"success": True, "data": profile})


def _handle_integration_status(start_response, db_path: Path):
    with get_connection(db_path) as connection:
        data = get_integration_state(connection)
    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_auth_authorize(start_response, db_path: Path, provider: str):
    with get_connection(db_path) as connection:
        redirect_url = authorize_provider(connection, provider)
    return _json_response(
        start_response,
        200,
        {
            "success": True,
            "data": {
                "provider": provider,
                "authorizeUrl": redirect_url,
                "message": f"PropellQ will request access to manage your {provider.title()} calendar events.",
            },
        },
    )


def _handle_auth_callback(environ, start_response, db_path: Path, provider: str):
    params = _flat_query_params(environ.get("QUERY_STRING", ""))
    with get_connection(db_path) as connection:
        success, state = complete_provider_authorization(
            connection,
            provider,
            params.get("state", ""),
            params.get("code"),
            params.get("error"),
        )
        integration = get_integration_state(connection)
    if success:
        return _json_response(
            start_response,
            200,
            {
                "success": True,
                "data": {
                    "provider": provider,
                    "status": state,
                    "integration": integration,
                    "message": f"{provider.title()} Calendar connected! Appointments will be added automatically.",
                },
            },
        )
    return _json_response(
        start_response,
        400,
        {
            "success": False,
            "error": {
                "code": state.upper(),
                "message": f"{provider.title()} Calendar authorization failed. Please try again or contact support.",
            },
        },
    )


def _handle_auth_disconnect(start_response, db_path: Path, provider: str):
    with get_connection(db_path) as connection:
        disconnect_provider(connection, provider)
        integration = get_integration_state(connection)
    return _json_response(
        start_response,
        200,
        {"success": True, "data": {"provider": provider, "integration": integration}},
    )


# ---------------------------------------------------------------------------
# EP-003 Clinical Intelligence handlers
# ---------------------------------------------------------------------------

_DEFAULT_CLINICAL_PATIENT_ID = 1  # Single-patient demo environment
_DEFAULT_PATIENT_ID = _DEFAULT_CLINICAL_PATIENT_ID  # alias for US-044 ownership checks


def _handle_clinical_upload(environ, start_response, db_path: Path):
    content_type = environ.get("CONTENT_TYPE", "application/octet-stream")
    content_length = int(environ.get("CONTENT_LENGTH", 0) or 0)
    file_data = environ["wsgi.input"].read(content_length)

    query_params = _flat_query_params(environ.get("QUERY_STRING", ""))
    file_name = query_params.get("fileName", "upload.pdf")
    try:
        patient_id = int(query_params.get("patientId", str(_DEFAULT_CLINICAL_PATIENT_ID)))
    except ValueError:
        patient_id = _DEFAULT_CLINICAL_PATIENT_ID

    if patient_id <= 0:
        return _json_response(
            start_response,
            400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "patientId must be a positive integer."}},
        )

    with get_connection(db_path) as connection:
        status_code, data = upload_document(connection, patient_id, file_name, content_type, file_data)

    success = status_code < 400
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_clinical_doc_status(environ, start_response, db_path: Path, document_id: int):
    query_params = _flat_query_params(environ.get("QUERY_STRING", ""))
    try:
        patient_id = int(query_params.get("patientId", str(_DEFAULT_CLINICAL_PATIENT_ID)))
    except ValueError:
        patient_id = _DEFAULT_CLINICAL_PATIENT_ID

    with get_connection(db_path) as connection:
        status_code, data = get_document_status(connection, document_id, patient_id)

    success = status_code < 400
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_clinical_doc_process(environ, start_response, db_path: Path, document_id: int):
    payload = _read_json_body(environ)
    document_text = payload.get("text", "")
    if not document_text:
        return _json_response(
            start_response,
            400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "text field is required for processing."}},
        )

    with get_connection(db_path) as connection:
        result = process_document(connection, document_id, document_text)

    return _json_response(start_response, 200, {"success": True, "data": result})


def _handle_clinical_signed_url(environ, start_response, db_path: Path, document_id: int):
    query_params = _flat_query_params(environ.get("QUERY_STRING", ""))
    try:
        patient_id = int(query_params.get("patientId", str(_DEFAULT_CLINICAL_PATIENT_ID)))
    except ValueError:
        patient_id = _DEFAULT_CLINICAL_PATIENT_ID

    with get_connection(db_path) as connection:
        status_code, data = generate_signed_document_url(connection, document_id, patient_id)

    success = status_code < 400
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_clinical_doc_preview(environ, start_response, db_path: Path, document_id: int):
    params = _flat_query_params(environ.get("QUERY_STRING", ""))
    try:
        patient_id = int(params.get("patient", str(_DEFAULT_CLINICAL_PATIENT_ID)))
        expires_at = int(params.get("expires", "0"))
    except ValueError:
        return _json_response(
            start_response,
            400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Invalid preview URL parameters."}},
        )
    signature = params.get("sig", "")

    if not validate_signed_url(document_id, patient_id, expires_at, signature):
        return _json_response(
            start_response,
            403,
            {"success": False, "error": {"code": "FORBIDDEN", "message": "Document preview URL is invalid or expired."}},
        )

    with get_connection(db_path) as connection:
        status_code, data = get_document_status(connection, document_id, patient_id)

    success = status_code < 400
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_clinical_profile(start_response, db_path: Path, patient_id: int):
    with get_connection(db_path) as connection:
        status_code, data = get_360_profile(connection, patient_id)

    success = status_code < 400
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_clinical_aggregate(environ, start_response, db_path: Path, patient_id: int):
    payload = _read_json_body(environ)
    intake_data = payload.get("intakeData")

    with get_connection(db_path) as connection:
        result = aggregate_patient_profile(connection, patient_id, intake_data)

    return _json_response(start_response, 200, {"success": True, "data": result})


def _handle_clinical_conflicts(start_response, db_path: Path, patient_id: int):
    with get_connection(db_path) as connection:
        status_code, data = detect_medication_conflicts(connection, patient_id)

    success = status_code < 400
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_clinical_element_source(environ, start_response, db_path: Path, element_id: int):
    query_params = _flat_query_params(environ.get("QUERY_STRING", ""))
    try:
        patient_id = int(query_params.get("patientId", str(_DEFAULT_CLINICAL_PATIENT_ID)))
    except ValueError:
        patient_id = _DEFAULT_CLINICAL_PATIENT_ID

    with get_connection(db_path) as connection:
        status_code, data = get_source_metadata(connection, element_id, patient_id)

    success = status_code < 400
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_process_confirmations(start_response, db_path: Path):
    with get_connection(db_path) as connection:
        data = process_confirmation_queue(connection)
    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_resend_confirmation(start_response, db_path: Path, appointment_id: int):
    with get_connection(db_path) as connection:
        status_code, data = resend_confirmation(connection, appointment_id)
    success = status_code == 200
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_process_reminders(start_response, db_path: Path):
    with get_connection(db_path) as connection:
        data = process_due_reminders(connection)
    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_process_swaps(start_response, db_path: Path):
    with get_connection(db_path) as connection:
        data = process_preferred_swaps(connection)
    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_process_calendar_sync(start_response, db_path: Path):
    with get_connection(db_path) as connection:
        data = process_calendar_sync_queue(connection)
    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_reconcile_sync(start_response, db_path: Path):
    with get_connection(db_path) as connection:
        data = run_pull_reconciliation(connection)
    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_dashboard_metrics(start_response, db_path: Path):
    with get_connection(db_path) as connection:
        data = dashboard_metrics(connection)
    return _json_response(start_response, 200, {"success": True, "data": data})


def _serve_static(path: str, start_response):
    requested = "index.html" if path in ("", "/") else path.lstrip("/")
    target = (PUBLIC_DIR / requested).resolve()

    if not str(target).startswith(str(PUBLIC_DIR.resolve())):
        return _plain_response(start_response, 403, b"Forbidden", "text/plain")

    if not target.exists() or target.is_dir():
        target = PUBLIC_DIR / "index.html"

    content = target.read_bytes()
    mime_type, _ = mimetypes.guess_type(target.name)
    return _plain_response(start_response, 200, content, mime_type or "text/html")


# ---------------------------------------------------------------------------
# EP-005: RBAC API handlers
# ---------------------------------------------------------------------------

def _handle_rbac_me(environ, start_response):
    role = get_role_from_environ(environ)
    matrix = get_permission_matrix()
    permissions = [action for action, roles in matrix.items() if role in roles]
    data: dict[str, Any] = {"role": role, "permissions": permissions}
    # EP-005 US-051 task_051_002: include non-PHI token claims when authenticated
    # via Bearer token so the client can inspect its session context.
    bearer_claims, bearer_present = get_bearer_token_claims(environ)
    if bearer_present and bearer_claims:
        data["token_claims"] = {
            "jti": bearer_claims.get("jti"),
            "sub": bearer_claims.get("sub"),
            "iat": bearer_claims.get("iat"),
            "exp": bearer_claims.get("exp"),
        }
    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_rbac_permissions(environ, start_response):
    denial = require_permission(environ, "admin:audit_logs")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
    return _json_response(start_response, 200, {"success": True, "data": get_permission_matrix()})


def _handle_rbac_audit_log(environ, start_response):
    denial = require_permission(environ, "admin:audit_logs")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
    from urllib.parse import parse_qs as _pqs
    qs = _pqs(environ.get("QUERY_STRING", ""))
    try:
        limit = int((qs.get("limit") or ["100"])[0])
    except (ValueError, TypeError):
        limit = 100
    return _json_response(start_response, 200, {"success": True, "data": get_audit_log(limit)})


# ---------------------------------------------------------------------------
# EP-005 US-045: Staff queue, patient detail, check-in, and access-log handlers
# ---------------------------------------------------------------------------

def _handle_staff_queue(environ, start_response, db_path: Path):
    """task_045_001 — Return assignment-scoped same-day appointment queue."""
    denial = require_permission(environ, "staff:queue_view")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    assignment_denial = require_staff_assignment(environ)
    if assignment_denial:
        _, msg = assignment_denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    role = get_role_from_environ(environ)
    staff_id = get_staff_id_from_environ(environ)
    provider_ids: list[int] | None = (
        list(get_staff_assigned_providers(staff_id)) if role == "staff" else None
    )

    with get_connection(db_path) as connection:
        data = get_staff_queue(connection, provider_ids)

    log_staff_access_event(staff_id, "staff:queue_view", None, "/api/staff/queue")
    return _json_response(start_response, 200, {"success": True, "data": data})


def _handle_staff_patient_detail(environ, start_response, db_path: Path, patient_id: int):
    """task_045_002 — Return minimum-necessary patient detail for check-in workflows."""
    denial = require_permission(environ, "staff:queue_view")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    assignment_denial = require_staff_assignment(environ)
    if assignment_denial:
        _, msg = assignment_denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    with get_connection(db_path) as connection:
        profile = get_patient_profile(connection, patient_id)

    if not profile:
        return _json_response(
            start_response,
            404,
            {"success": False, "error": {"code": "NOT_FOUND", "message": "Patient not found"}},
        )

    role = get_role_from_environ(environ)
    if role == "staff":
        profile = filter_staff_patient_detail(profile)

    staff_id = get_staff_id_from_environ(environ)
    log_staff_access_event(
        staff_id, "staff:patient_detail", None, f"/api/staff/patients/{patient_id}/detail"
    )
    return _json_response(start_response, 200, {"success": True, "data": profile})


def _handle_staff_checkin(environ, start_response, db_path: Path, appointment_id: int):
    """task_045_001/003 — Check in a patient; enforce provider assignment and log the action."""
    denial = require_permission(environ, "staff:checkin")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    with get_connection(db_path) as connection:
        appointment = get_appointment_details(connection, appointment_id)

    if appointment is None:
        return _json_response(
            start_response,
            404,
            {"success": False, "error": {"code": "NOT_FOUND", "message": "Appointment not found"}},
        )

    provider_id: int | None = appointment.get("provider_id")
    assignment_denial = require_staff_assignment(environ, provider_id)
    if assignment_denial:
        staff_id = get_staff_id_from_environ(environ)
        log_staff_access_event(
            staff_id,
            "staff:checkin",
            provider_id,
            f"/api/staff/appointments/{appointment_id}/checkin",
            outcome="denied",
        )
        _, msg = assignment_denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    staff_id = get_staff_id_from_environ(environ)
    log_staff_access_event(
        staff_id,
        "staff:checkin",
        provider_id,
        f"/api/staff/appointments/{appointment_id}/checkin",
    )
    return _json_response(
        start_response,
        200,
        {"success": True, "data": {"appointmentId": appointment_id, "checkedIn": True}},
    )


def _handle_staff_access_log(environ, start_response):
    """task_045_003 — Return staff access log entries (admin-only)."""
    denial = require_permission(environ, "admin:audit_logs")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
    from urllib.parse import parse_qs as _pqs
    qs = _pqs(environ.get("QUERY_STRING", ""))
    try:
        limit = int((qs.get("limit") or ["100"])[0])
    except (ValueError, TypeError):
        limit = 100
    return _json_response(start_response, 200, {"success": True, "data": get_staff_access_log(limit)})


# ---------------------------------------------------------------------------
# EP-005 US-046: Admin user management and change log handlers
# ---------------------------------------------------------------------------

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _handle_admin_create_user(environ, start_response):
    """task_048_001 — Create a new user account (admin-only)."""
    denial = require_permission(environ, "admin:user_management")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    payload = _read_json_body(environ)
    user_id = (payload.get("userId") or "").strip()
    email = (payload.get("email") or "").strip()
    role = (payload.get("role") or "").strip()
    status = (payload.get("status") or "active").strip()

    missing = [f for f, v in [("userId", user_id), ("email", email), ("role", role)] if not v]
    if missing:
        return _json_response(
            start_response, 400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": f"Missing required fields: {', '.join(missing)}"}},
        )

    if not _EMAIL_PATTERN.match(email):
        return _json_response(
            start_response, 400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Invalid email address"}},
        )

    if get_user(user_id) is not None:
        return _json_response(
            start_response, 409,
            {"success": False, "error": {"code": "CONFLICT", "message": f"User '{user_id}' already exists"}},
        )

    try:
        user = register_user(user_id, role, email, status)
    except ValueError as exc:
        return _json_response(
            start_response, 400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(exc)}},
        )

    actor_id = get_admin_id_from_environ(environ)
    record_admin_event(actor_id, "admin:user_created", user_id, None, {"role": role, "status": status, "email": email}, "")
    return _json_response(start_response, 201, {"success": True, "data": user})


def _handle_admin_list_users(environ, start_response):
    """task_046_001 — List all registered users (admin-only)."""
    denial = require_permission(environ, "admin:user_management")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
    return _json_response(start_response, 200, {"success": True, "data": list_users()})


def _handle_admin_get_user(environ, start_response, user_id: str):
    """task_046_001 — Retrieve a single user record (admin-only)."""
    denial = require_permission(environ, "admin:user_management")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})
    user = get_user(user_id)
    if user is None:
        return _json_response(
            start_response, 404,
            {"success": False, "error": {"code": "NOT_FOUND", "message": f"User '{user_id}' not found"}},
        )
    return _json_response(start_response, 200, {"success": True, "data": user})


def _handle_admin_update_user(environ, start_response, user_id: str):
    """task_048_002 — Update allowed profile fields for a user (admin-only)."""
    denial = require_permission(environ, "admin:user_management")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    payload = _read_json_body(environ)
    reason = (payload.pop("reason", "") or "").strip()
    updates = {k: v for k, v in payload.items() if v is not None}

    actor_id = get_admin_id_from_environ(environ)
    success, result = update_user(actor_id, user_id, updates, reason)
    if not success:
        status_code = 404 if "not found" in str(result) else 400
        return _json_response(
            start_response, status_code,
            {"success": False, "error": {"code": "BAD_REQUEST", "message": result}},
        )
    return _json_response(start_response, 200, {"success": True, "data": result})


def _handle_admin_assign_role(environ, start_response, user_id: str):
    """task_046_002 — Assign a new role to a user with audit logging (admin-only)."""
    denial = require_permission(environ, "admin:user_management")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    payload = _read_json_body(environ)
    new_role = (payload.get("role") or "").strip()
    reason = (payload.get("reason") or "").strip()

    if not new_role:
        return _json_response(
            start_response, 400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "'role' is required"}},
        )

    actor_id = get_admin_id_from_environ(environ)
    success, message = assign_user_role(actor_id, user_id, new_role, reason)
    if not success:
        status_code = 404 if "not found" in message else 400
        return _json_response(
            start_response, status_code,
            {"success": False, "error": {"code": "BAD_REQUEST", "message": message}},
        )
    return _json_response(start_response, 200, {"success": True, "data": {"userId": user_id, "role": new_role, "message": message}})


def _handle_admin_set_status(environ, start_response, user_id: str):
    """task_046_002 — Change a user's account status with audit logging (admin-only)."""
    denial = require_permission(environ, "admin:user_management")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    payload = _read_json_body(environ)
    new_status = (payload.get("status") or "").strip()
    reason = (payload.get("reason") or "").strip()

    if not new_status:
        return _json_response(
            start_response, 400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "'status' is required"}},
        )

    actor_id = get_admin_id_from_environ(environ)
    success, message = set_user_status(actor_id, user_id, new_status, reason)
    if not success:
        status_code = 404 if "not found" in message else 400
        return _json_response(
            start_response, status_code,
            {"success": False, "error": {"code": "BAD_REQUEST", "message": message}},
        )
    return _json_response(
        start_response, 200,
        {"success": True, "data": {"userId": user_id, "status": new_status, "message": message}},
    )


# ---------------------------------------------------------------------------
# EP-005 US-049: Password reset handlers
# ---------------------------------------------------------------------------


def _handle_password_reset_request(environ, start_response):
    """task_049_001 — Privacy-safe password reset request (always generic response)."""
    payload = _read_json_body(environ)
    identity = (payload.get("identity") or "").strip()
    if not identity:
        return _json_response(
            start_response, 400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Field 'identity' is required."}},
        )
    source_ip = (
        environ.get("HTTP_X_FORWARDED_FOR") or environ.get("REMOTE_ADDR") or None
    )
    result = request_password_reset(identity, source_ip)
    # Always return 200 with generic message — never reveal account existence or
    # rate-limit status to the caller (privacy-safe per task_049_001).
    return _json_response(start_response, 200, {"success": True, "message": result["message"]})


def _handle_password_reset_confirm(environ, start_response):
    """task_049_003 — Validate token, enforce password policy, update credentials."""
    payload = _read_json_body(environ)
    token = (payload.get("token") or "").strip()
    new_password = payload.get("new_password") or ""

    if not token:
        return _json_response(
            start_response, 400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Field 'token' is required."}},
        )
    if not new_password:
        return _json_response(
            start_response, 400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Field 'new_password' is required."}},
        )

    ok, result = confirm_password_reset(token, new_password)
    if not ok:
        return _json_response(
            start_response, 400,
            {"success": False, "error": {"code": "RESET_FAILED", "message": result}},
        )
    return _json_response(
        start_response, 200,
        {"success": True, "message": "Password has been reset successfully."},
    )


# ---------------------------------------------------------------------------
# EP-005 US-051: Session token handler
# ---------------------------------------------------------------------------


def _handle_session_token_issue(environ, start_response):
    """task_051_002 — Issue a signed session token for a registered user.

    Accepts ``{"user_id": "<id>"}`` in the request body.
    Returns the token, JTI, and expiry (no PHI in response).
    """
    payload = _read_json_body(environ)
    user_id = (payload.get("user_id") or "").strip()
    if not user_id:
        return _json_response(
            start_response, 400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Field 'user_id' is required."}},
        )
    result = issue_session_token(user_id)
    return _json_response(
        start_response, 200,
        {
            "success": True,
            "data": {
                "token":      result["token"],
                "jti":        result["jti"],
                "expires_at": result["expires_at"],
            },
        },
    )


def _handle_admin_change_log(environ, start_response):
    """task_046_003 / task_052_001 / task_052_002 — Paginated, filterable admin change log."""

    denial = require_permission(environ, "admin:change_log")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    qs = _flat_query_params(environ.get("QUERY_STRING", ""))

    def _qs_int(key: str, default: int) -> int:
        try:
            return int(qs.get(key, default))
        except (ValueError, TypeError):
            return default

    result = query_admin_change_log(
        actor=qs.get("actor") or None,
        action=qs.get("action") or None,
        target_user=qs.get("target_user") or None,
        from_ts=qs.get("from") or None,
        to_ts=qs.get("to") or None,
        page=_qs_int("page", 1),
        page_size=_qs_int("page_size", 50),
    )
    return _json_response(start_response, 200, {"success": True, "data": result})


# ---------------------------------------------------------------------------
# EP-005 US-052: Audit log entry detail and export handlers
# ---------------------------------------------------------------------------


def _handle_audit_log_entry(environ, start_response, entry_id: str):
    """task_052_003 — Return masked detail view for a single audit entry."""
    denial = require_permission(environ, "admin:change_log")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    entry = get_admin_change_log_entry(entry_id)
    if entry is None:
        return _json_response(
            start_response, 404,
            {"success": False, "error": {"code": "NOT_FOUND", "message": f"Audit entry '{entry_id}' not found."}},
        )
    return _json_response(start_response, 200, {"success": True, "data": mask_audit_entry(entry)})


def _handle_audit_log_export(environ, start_response):
    """task_052_004 — Export filtered audit log as CSV or JSON download."""
    denial = require_permission(environ, "admin:change_log")
    if denial:
        _, msg = denial
        return _json_response(start_response, 403, {"success": False, "error": {"code": "FORBIDDEN", "message": msg}})

    qs = _flat_query_params(environ.get("QUERY_STRING", ""))
    fmt = qs.get("format", "json").lower()
    if fmt not in ("csv", "json"):
        fmt = "json"

    content, content_type, filename = export_admin_change_log(
        actor=qs.get("actor") or None,
        action=qs.get("action") or None,
        target_user=qs.get("target_user") or None,
        from_ts=qs.get("from") or None,
        to_ts=qs.get("to") or None,
        fmt=fmt,
    )
    return _download_response(start_response, content, content_type, filename)


def _json_response(start_response, status_code: int, payload: dict[str, Any]):
    body = json.dumps(payload).encode("utf-8")
    status_text = f"{status_code} {_status_text(status_code)}"
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ]
    start_response(status_text, headers)
    return [body]


def _plain_response(start_response, status_code: int, body: bytes, content_type: str):
    status_text = f"{status_code} {_status_text(status_code)}"
    headers = [
        ("Content-Type", f"{content_type}; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ]
    start_response(status_text, headers)
    return [body]


def _status_text(status_code: int) -> str:
    text = {
        200: "OK",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        410: "Gone",
    }
    return text.get(status_code, "OK")


def _download_response(
    start_response,
    body: bytes,
    content_type: str,
    filename: str,
):
    """Return a file-download response with Content-Disposition attachment header."""
    status_text = "200 OK"
    headers = [
        ("Content-Type", f"{content_type}; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Content-Disposition", f'attachment; filename="{filename}"'),
        ("Cache-Control", "no-store"),
    ]
    start_response(status_text, headers)
    return [body]


def _read_json_body(environ) -> dict[str, Any]:
    size = int(environ.get("CONTENT_LENGTH") or 0)
    if size <= 0:
        return {}
    payload = environ["wsgi.input"].read(size).decode("utf-8")
    if not payload:
        return {}
    return json.loads(payload)


def _flat_query_params(query_string: str) -> dict[str, str]:
    parsed = parse_qs(query_string, keep_blank_values=False)
    return {key: values[0] for key, values in parsed.items() if values}


# ---------------------------------------------------------------------------
# EP-003 Coding Engine handlers (TASK-025 through TASK-030)
# ---------------------------------------------------------------------------


def _handle_allergy_conflicts(start_response, db_path: Path, patient_id: int):
    with get_connection(db_path) as connection:
        status_code, data = detect_allergy_drug_conflicts(connection, patient_id)
    success = status_code < 400
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_get_suggestions(environ, start_response, db_path: Path, patient_id: int):
    params = _flat_query_params(environ.get("QUERY_STRING", ""))
    code_type = params.get("codeType")
    review_only = params.get("reviewOnly", "").lower() in ("1", "true")
    with get_connection(db_path) as connection:
        status_code, data = get_suggestions(connection, patient_id, code_type, review_only)
    return _json_response(start_response, status_code, {"success": True, "data": data})


def _handle_generate_suggestions(environ, start_response, db_path: Path, patient_id: int):
    payload = _read_json_body(environ)
    code_type = payload.get("codeType", "all")
    clinical_text = payload.get("clinicalText", "")
    with get_connection(db_path) as connection:
        status_code, data = generate_code_suggestions(connection, patient_id, code_type, clinical_text)
    return _json_response(start_response, status_code, {"success": True, "data": data})


def _handle_code_review(environ, start_response, db_path: Path, suggestion_id: int):
    payload = _read_json_body(environ)
    action = payload.get("action", "")
    reviewer_id = (payload.get("reviewerId") or "anonymous").strip()
    override_code = payload.get("overrideCode")
    override_description = payload.get("overrideDescription")
    rejection_reason = payload.get("rejectionReason")
    decision_metadata = payload.get("decisionMetadata")

    try:
        patient_id = int(payload.get("patientId", str(_DEFAULT_CLINICAL_PATIENT_ID)))
    except (ValueError, TypeError):
        patient_id = _DEFAULT_CLINICAL_PATIENT_ID

    with get_connection(db_path) as connection:
        status_code, data = review_code_suggestion(
            connection,
            suggestion_id,
            patient_id,
            action,
            reviewer_id,
            override_code,
            override_description,
            rejection_reason,
            decision_metadata,
        )
    success = status_code < 400
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_get_thresholds(start_response, db_path: Path):
    with get_connection(db_path) as connection:
        status_code, data = get_thresholds(connection)
    return _json_response(start_response, status_code, {"success": True, "data": data})


def _handle_update_threshold(environ, start_response, db_path: Path):
    payload = _read_json_body(environ)
    code_type = payload.get("codeType", "")
    new_value = payload.get("thresholdValue")
    updated_by = (payload.get("updatedBy") or "anonymous").strip()
    role = (payload.get("role") or "").strip()

    if new_value is None:
        return _json_response(
            start_response,
            400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "thresholdValue is required."}},
        )
    try:
        new_value = float(new_value)
    except (TypeError, ValueError):
        return _json_response(
            start_response,
            400,
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "thresholdValue must be a number."}},
        )

    with get_connection(db_path) as connection:
        status_code, data = update_threshold(connection, code_type, new_value, updated_by, role)
    success = status_code < 400
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )


def _handle_threshold_history(environ, start_response, db_path: Path):
    params = _flat_query_params(environ.get("QUERY_STRING", ""))
    code_type = params.get("codeType")
    with get_connection(db_path) as connection:
        status_code, data = get_threshold_history(connection, code_type)
    return _json_response(start_response, status_code, {"success": True, "data": data})


def _handle_conflict_queue(environ, start_response, db_path: Path):
    params = _flat_query_params(environ.get("QUERY_STRING", ""))
    patient_id_str = params.get("patientId")
    try:
        patient_id = int(patient_id_str) if patient_id_str else None
    except ValueError:
        patient_id = None
    with get_connection(db_path) as connection:
        status_code, data = get_conflict_queue(connection, patient_id)
    return _json_response(start_response, status_code, {"success": True, "data": data})


def _handle_resolve_conflict(environ, start_response, db_path: Path, conflict_id: int):
    payload = _read_json_body(environ)
    conflict_table = payload.get("conflictTable", "clinical_medication_conflicts")
    action = payload.get("action", "")
    reviewer_id = (payload.get("reviewerId") or "anonymous").strip()
    chosen_value = payload.get("chosenValue")
    merge_value = payload.get("mergeValue")
    resolution_note = payload.get("resolutionNote")

    try:
        patient_id = int(payload.get("patientId", str(_DEFAULT_CLINICAL_PATIENT_ID)))
    except (ValueError, TypeError):
        patient_id = _DEFAULT_CLINICAL_PATIENT_ID

    with get_connection(db_path) as connection:
        status_code, data = resolve_conflict(
            connection,
            conflict_id,
            conflict_table,
            patient_id,
            action,
            reviewer_id,
            chosen_value,
            merge_value,
            resolution_note,
        )
    success = status_code < 400
    return _json_response(
        start_response,
        status_code,
        {"success": success, "data": data} if success else {"success": False, "error": data},
    )
