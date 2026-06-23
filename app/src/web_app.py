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
            return _handle_appointment_details(start_response, selected_db, int(appointment_match.group(1)))

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
            return _handle_patient_profile(start_response, selected_db)

        if method == "GET" and path == "/api/integrations/status":
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

        if method == "POST" and path == "/api/jobs/process-confirmations":
            return _handle_process_confirmations(start_response, selected_db)

        resend_match = re.match(r"^/api/appointments/(\d+)/resend-confirmation$", path)
        if method == "POST" and resend_match:
            return _handle_resend_confirmation(start_response, selected_db, int(resend_match.group(1)))

        if method == "POST" and path == "/api/jobs/process-reminders":
            return _handle_process_reminders(start_response, selected_db)

        if method == "POST" and path == "/api/jobs/process-swaps":
            return _handle_process_swaps(start_response, selected_db)

        if method == "POST" and path == "/api/jobs/process-calendar-sync":
            return _handle_process_calendar_sync(start_response, selected_db)

        if method == "POST" and path == "/api/jobs/reconcile-calendar-sync":
            return _handle_reconcile_sync(start_response, selected_db)

        if method == "GET" and path == "/api/dashboard/metrics":
            return _handle_dashboard_metrics(start_response, selected_db)

        if method == "GET" and path == "/api/metrics/search":
            return _json_response(start_response, 200, {"success": True, "data": metrics.snapshot()})

        # --- EP-003: Clinical Intelligence Platform ---
        if method == "POST" and path == "/api/clinical/documents/upload":
            return _handle_clinical_upload(environ, start_response, selected_db)

        clinical_doc_status_match = re.match(r"^/api/clinical/documents/(\d+)/status$", path)
        if method == "GET" and clinical_doc_status_match:
            return _handle_clinical_doc_status(environ, start_response, selected_db, int(clinical_doc_status_match.group(1)))

        clinical_doc_process_match = re.match(r"^/api/clinical/documents/(\d+)/process$", path)
        if method == "POST" and clinical_doc_process_match:
            return _handle_clinical_doc_process(environ, start_response, selected_db, int(clinical_doc_process_match.group(1)))

        clinical_doc_signed_url_match = re.match(r"^/api/clinical/documents/(\d+)/signed-url$", path)
        if method == "GET" and clinical_doc_signed_url_match:
            return _handle_clinical_signed_url(environ, start_response, selected_db, int(clinical_doc_signed_url_match.group(1)))

        clinical_doc_preview_match = re.match(r"^/api/clinical/documents/(\d+)/preview$", path)
        if method == "GET" and clinical_doc_preview_match:
            return _handle_clinical_doc_preview(environ, start_response, selected_db, int(clinical_doc_preview_match.group(1)))

        clinical_profile_match = re.match(r"^/api/clinical/patients/(\d+)/profile$", path)
        if method == "GET" and clinical_profile_match:
            return _handle_clinical_profile(start_response, selected_db, int(clinical_profile_match.group(1)))

        clinical_aggregate_match = re.match(r"^/api/clinical/patients/(\d+)/aggregate$", path)
        if method == "POST" and clinical_aggregate_match:
            return _handle_clinical_aggregate(environ, start_response, selected_db, int(clinical_aggregate_match.group(1)))

        clinical_conflicts_match = re.match(r"^/api/clinical/patients/(\d+)/conflicts$", path)
        if method == "GET" and clinical_conflicts_match:
            return _handle_clinical_conflicts(start_response, selected_db, int(clinical_conflicts_match.group(1)))

        clinical_element_source_match = re.match(r"^/api/clinical/elements/(\d+)/source$", path)
        if method == "GET" and clinical_element_source_match:
            return _handle_clinical_element_source(environ, start_response, selected_db, int(clinical_element_source_match.group(1)))

        # --- EP-003: Coding Engine (TASK-025 through TASK-030) ---
        clinical_allergy_conflicts_match = re.match(r"^/api/clinical/patients/(\d+)/allergy-conflicts$", path)
        if method == "GET" and clinical_allergy_conflicts_match:
            return _handle_allergy_conflicts(start_response, selected_db, int(clinical_allergy_conflicts_match.group(1)))

        clinical_suggest_match = re.match(r"^/api/clinical/patients/(\d+)/suggestions$", path)
        if method == "GET" and clinical_suggest_match:
            return _handle_get_suggestions(environ, start_response, selected_db, int(clinical_suggest_match.group(1)))
        if method == "POST" and clinical_suggest_match:
            return _handle_generate_suggestions(environ, start_response, selected_db, int(clinical_suggest_match.group(1)))

        coding_review_match = re.match(r"^/api/coding/suggestions/(\d+)/review$", path)
        if method == "POST" and coding_review_match:
            return _handle_code_review(environ, start_response, selected_db, int(coding_review_match.group(1)))

        if method == "GET" and path == "/api/clinical/thresholds":
            return _handle_get_thresholds(start_response, selected_db)

        if method == "PUT" and path == "/api/clinical/thresholds":
            return _handle_update_threshold(environ, start_response, selected_db)

        if method == "GET" and path == "/api/clinical/thresholds/history":
            return _handle_threshold_history(environ, start_response, selected_db)

        if method == "GET" and path == "/api/clinical/conflicts/queue":
            return _handle_conflict_queue(environ, start_response, selected_db)

        conflict_resolve_match = re.match(r"^/api/clinical/conflicts/(\d+)/resolve$", path)
        if method == "POST" and conflict_resolve_match:
            return _handle_resolve_conflict(environ, start_response, selected_db, int(conflict_resolve_match.group(1)))

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


def _handle_appointment_details(start_response, db_path: Path, appointment_id: int):
    with get_connection(db_path) as connection:
        data = get_appointment_details(connection, appointment_id)
    if data is None:
        return _json_response(
            start_response,
            404,
            {"success": False, "error": {"code": "APPOINTMENT_NOT_FOUND", "message": "Appointment not found"}},
        )
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
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        410: "Gone",
    }
    return text.get(status_code, "OK")


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
