"""EP-006: Patient Dashboard & Admin Operational Dashboard service functions.

Covers US-053 through US-058 and US-060.
Intentionally avoids importing zoneinfo so this module is safe to import
on Windows environments where the zoneinfo C extension has known instabilities.
Action eligibility (can_reschedule / can_cancel) is computed via date arithmetic
on ISO date strings without timezone conversion.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any

DEFAULT_PATIENT_ID = 1

# Cut-off rules (by calendar day, not exact wall-clock time, to avoid zoneinfo)
_RESCHEDULE_DAYS_AHEAD = 1   # appointment must be at least 1 full day away
_CANCEL_DAYS_AHEAD = 0       # appointment must be at least today (same-day cancel disabled)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _today() -> str:
    return date.today().isoformat()


def _days_until(appt_date_str: str) -> int:
    """Calendar days from today until *appt_date_str*."""
    try:
        appt_date = date.fromisoformat(appt_date_str)
        return (appt_date - date.today()).days
    except (ValueError, TypeError):
        return -1


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_patient_profile(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM patient_profiles WHERE id = ?",
        [patient_id],
    ).fetchone()
    return dict(row) if row else {}


# ---------------------------------------------------------------------------
# US-054: Upcoming Appointments with Action Eligibility
# ---------------------------------------------------------------------------

def get_patient_upcoming_appointments(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """Return future booked appointments with can_reschedule / can_cancel flags."""
    today = _today()
    rows = connection.execute(
        """
        SELECT a.*, p.name AS provider_name, s.name AS specialty
        FROM appointments a
        JOIN providers p ON p.id = a.provider_id
        JOIN specialties s ON s.id = a.specialty_id
        WHERE a.appointment_date >= ?
          AND a.status = 'booked'
        ORDER BY a.appointment_date ASC, a.start_time ASC
        """,
        [today],
    ).fetchall()

    items = []
    for row in rows:
        appt = dict(row)
        days_ahead = _days_until(appt["appointment_date"])
        appt["can_reschedule"] = days_ahead >= _RESCHEDULE_DAYS_AHEAD + 1
        appt["can_cancel"] = days_ahead > _CANCEL_DAYS_AHEAD
        items.append(appt)

    return {"items": items, "total": len(items)}


# ---------------------------------------------------------------------------
# US-055: Past Appointments with Release Policy Filter
# ---------------------------------------------------------------------------

def get_patient_appointment_history(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """Return past booked appointments with notes release policy metadata."""
    today = _today()
    rows = connection.execute(
        """
        SELECT a.*, p.name AS provider_name, s.name AS specialty
        FROM appointments a
        JOIN providers p ON p.id = a.provider_id
        JOIN specialties s ON s.id = a.specialty_id
        WHERE a.appointment_date < ?
          AND a.status = 'booked'
        ORDER BY a.appointment_date DESC, a.start_time DESC
        """,
        [today],
    ).fetchall()

    items = []
    for row in rows:
        appt = dict(row)
        delivery = connection.execute(
            """SELECT attachment_path FROM confirmation_deliveries
               WHERE appointment_id = ? AND status = 'sent' LIMIT 1""",
            [appt["id"]],
        ).fetchone()
        if delivery and delivery["attachment_path"]:
            appt["notes_available"] = True
            appt["notes_url"] = f"/api/patient/appointments/{appt['id']}/notes"
        else:
            appt["notes_available"] = False
            appt["notes_url"] = None
            appt["notes_unavailable_reason"] = "Clinical notes have not been released yet."
        items.append(appt)

    return {"items": items, "total": len(items)}


# ---------------------------------------------------------------------------
# US-056: Personal Health Profile with Version Metadata
# ---------------------------------------------------------------------------

def get_patient_health_profile(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """Return structured health profile sections with version/timestamp metadata."""
    rows = connection.execute(
        """
        SELECT element_type, element_value, is_active, aggregated_at
        FROM clinical_profile_elements
        WHERE patient_id = ? AND is_active = 1
        ORDER BY element_type, aggregated_at DESC
        """,
        [patient_id],
    ).fetchall()

    medications: list[dict[str, Any]] = []
    allergies: list[dict[str, Any]] = []
    diagnoses: list[dict[str, Any]] = []
    chronic_conditions: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []

    for row in rows:
        entry = {
            "label": row["element_value"],
            "status": "active" if row["is_active"] else "inactive",
            "last_updated": row["aggregated_at"],
        }
        etype = (row["element_type"] or "").lower()
        if etype == "medication":
            medications.append(entry)
        elif etype == "allergy":
            allergies.append(entry)
        elif etype == "diagnosis":
            diagnoses.append(entry)
        # demographics / intake_field / date types are not shown in health profile cards

    timestamps = [r["aggregated_at"] for r in rows if r["aggregated_at"]]
    last_updated = max(timestamps) if timestamps else _utc_now_iso()

    version_row = connection.execute(
        "SELECT MAX(rowid) AS v FROM clinical_profile_elements WHERE patient_id = ? AND is_active = 1",
        [patient_id],
    ).fetchone()
    version = int(version_row["v"] or 0)

    return {
        "patient_id": patient_id,
        "medications": medications,
        "allergies": allergies,
        "diagnoses": diagnoses,
        "chronic_conditions": chronic_conditions,
        "alerts": alerts,
        "version": version,
        "last_updated": last_updated,
    }


# ---------------------------------------------------------------------------
# US-057: Patient Documents List (BE-3)
# ---------------------------------------------------------------------------

def get_patient_documents(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """Return patient document list with processing status."""
    rows = connection.execute(
        """
        SELECT d.id, d.file_name, d.file_type, d.upload_timestamp,
               cdp.status AS processing_status
        FROM clinical_documents d
        LEFT JOIN clinical_document_processing cdp ON cdp.document_id = d.id
        WHERE d.patient_id = ?
        ORDER BY d.upload_timestamp DESC
        """,
        [patient_id],
    ).fetchall()

    items = [
        {
            "id": row["id"],
            "file_name": row["file_name"],
            "file_type": row["file_type"],
            "processing_status": row["processing_status"] or "pending",
            "uploaded_at": row["upload_timestamp"],
        }
        for row in rows
    ]
    return {"items": items, "total": len(items)}


# ---------------------------------------------------------------------------
# US-058: Notification Preference Management (BE-1, BE-2)
# ---------------------------------------------------------------------------

def get_notification_preferences(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """Retrieve patient notification channel preferences."""
    profile = _get_patient_profile(connection, patient_id)
    channels: list[str] = []
    raw = profile.get("reminder_channels")
    if raw:
        try:
            channels = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            channels = []

    return {
        "patient_id": patient_id,
        "email": "email" in channels,
        "sms": "sms" in channels,
        "in_app": bool(profile),
        "do_not_disturb": bool(profile.get("do_not_disturb", 0)),
    }


def set_notification_preferences(
    connection: sqlite3.Connection,
    patient_id: int,
    prefs: dict[str, Any],
) -> dict[str, Any]:
    """Persist notification channel preferences."""
    channels: list[str] = []
    if prefs.get("email", False):
        channels.append("email")
    if prefs.get("sms", False):
        channels.append("sms")
    do_not_disturb = 1 if prefs.get("do_not_disturb", False) else 0
    with connection:
        connection.execute(
            "UPDATE patient_profiles SET reminder_channels = ?, do_not_disturb = ? WHERE id = ?",
            [json.dumps(channels), do_not_disturb, patient_id],
        )
    return get_notification_preferences(connection, patient_id)


def is_notification_allowed(
    connection: sqlite3.Connection,
    patient_id: int,
    channel: str,
) -> bool:
    """Check whether a notification channel is enabled for a patient (opt-out enforcement)."""
    prefs = get_notification_preferences(connection, patient_id)
    if prefs.get("do_not_disturb"):
        return False
    return bool(prefs.get(channel, False))


# ---------------------------------------------------------------------------
# US-053: Patient Dashboard Aggregate (BE-1, BE-2)
# ---------------------------------------------------------------------------

def get_patient_dashboard(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """Aggregate dashboard payload with partial-update metadata."""
    upcoming = get_patient_upcoming_appointments(connection, patient_id)
    profile = _get_patient_profile(connection, patient_id)
    prefs = get_notification_preferences(connection, patient_id)
    documents = get_patient_documents(connection, patient_id)

    recent_activity: list[dict[str, Any]] = []
    history_rows = connection.execute(
        """
        SELECT a.appointment_date, p.name AS provider_name
        FROM appointments a
        JOIN providers p ON p.id = a.provider_id
        WHERE a.appointment_date < ?
          AND a.status = 'booked'
        ORDER BY a.appointment_date DESC
        LIMIT 5
        """,
        [_today()],
    ).fetchall()
    for row in history_rows:
        recent_activity.append({
            "type": "appointment",
            "date": row["appointment_date"],
            "description": f"Visit with {row['provider_name']}",
        })

    unread_notifications = sum(
        1 for doc in documents["items"] if doc["processing_status"] == "pending"
    )

    return {
        "upcoming_count": upcoming["total"],
        "upcoming_next": upcoming["items"][0] if upcoming["items"] else None,
        "recent_activity": recent_activity,
        "profile_summary": {
            "name": f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip(),
            "email": profile.get("email", ""),
        },
        "notification_prefs": prefs,
        "documents_count": documents["total"],
        "unread_notifications": unread_notifications,
        "last_updated": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# US-060: Admin Operational Dashboard (BE-1, BE-2, BE-3)
# ---------------------------------------------------------------------------

def get_admin_operational_metrics(
    connection: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
    provider_id: int | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Admin KPI metrics with optional filter support."""
    where: list[str] = []
    params: list[Any] = []

    if date_from:
        where.append("a.appointment_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("a.appointment_date <= ?")
        params.append(date_to)
    if provider_id:
        where.append("a.provider_id = ?")
        params.append(provider_id)
    if location:
        where.append("LOWER(a.location) LIKE ?")
        params.append(f"%{location.lower()}%")

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    and_or_where = "AND" if where else "WHERE"

    total = int(
        connection.execute(
            f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql}", params
        ).fetchone()["cnt"] or 0
    )
    booked = int(
        connection.execute(
            f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql} {and_or_where} a.status = 'booked'",
            params,
        ).fetchone()["cnt"] or 0
    )
    cancelled = int(
        connection.execute(
            f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql} {and_or_where} a.status = 'cancelled'",
            params,
        ).fetchone()["cnt"] or 0
    )

    utilization_rate = round(booked / total * 100, 1) if total > 0 else 0.0
    no_show_rate = round(cancelled / total * 100, 1) if total > 0 else 0.0

    wait_row = connection.execute(
        f"""
        SELECT AVG(duration_minutes) AS avg_wait
        FROM appointments a
        {where_sql} {and_or_where} a.status = 'booked'
        """,
        params,
    ).fetchone()
    avg_wait_minutes = round(float(wait_row["avg_wait"] or 0), 1)

    by_provider_rows = connection.execute(
        f"""
        SELECT p.name AS provider_name, COUNT(*) AS cnt
        FROM appointments a
        JOIN providers p ON p.id = a.provider_id
        {where_sql}
        GROUP BY p.id, p.name
        ORDER BY cnt DESC
        LIMIT 10
        """,
        params,
    ).fetchall()

    return {
        "total_appointments": total,
        "booked": booked,
        "cancelled": cancelled,
        "utilization_rate": utilization_rate,
        "no_show_rate": no_show_rate,
        "avg_wait_minutes": avg_wait_minutes,
        "by_provider": [
            {"provider": r["provider_name"], "count": r["cnt"]} for r in by_provider_rows
        ],
        "filters_applied": {
            "date_from": date_from,
            "date_to": date_to,
            "provider_id": provider_id,
            "location": location,
        },
        "last_updated": _utc_now_iso(),
    }


# ===========================================================================
# EP-006 US-061 through US-069: Admin Analytics Extension
# ===========================================================================

import csv as _csv
import io as _io


def _build_filters(
    date_from: str | None,
    date_to: str | None,
    provider_id: int | None,
    location: str | None,
) -> tuple[list[str], list[Any]]:
    """Shared WHERE clause builder for admin analytics endpoints."""
    where: list[str] = []
    params: list[Any] = []
    if date_from:
        where.append("a.appointment_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("a.appointment_date <= ?")
        params.append(date_to)
    if provider_id:
        where.append("a.provider_id = ?")
        params.append(provider_id)
    if location:
        where.append("LOWER(a.location) LIKE ?")
        params.append(f"%{location.lower()}%")
    return where, params


# ---------------------------------------------------------------------------
# US-061: No-Show Rate and Trends (BE-1, BE-2)
# ---------------------------------------------------------------------------

def get_no_show_metrics(
    connection: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
    provider_id: int | None = None,
) -> dict[str, Any]:
    """No-show (cancelled) rate with per-date trend and prior-period comparison."""
    where, params = _build_filters(date_from, date_to, provider_id, None)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    ext = "AND" if where else "WHERE"

    total = int(connection.execute(
        f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql}", params
    ).fetchone()["cnt"] or 0)

    missed = int(connection.execute(
        f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql} {ext} a.status = 'cancelled'",
        params,
    ).fetchone()["cnt"] or 0)

    rate = round(missed / total * 100, 1) if total > 0 else 0.0

    trend_rows = connection.execute(
        f"""
        SELECT a.appointment_date AS period, COUNT(*) AS no_shows
        FROM appointments a
        {where_sql} {ext} a.status = 'cancelled'
        GROUP BY a.appointment_date
        ORDER BY a.appointment_date
        """,
        params,
    ).fetchall()
    trend = [{"period": r["period"], "value": r["no_shows"]} for r in trend_rows]

    # Prior-period symmetric window for delta calculation
    prior_rate = 0.0
    delta = 0.0
    if date_from and date_to:
        try:
            d0 = date.fromisoformat(date_from)
            d1 = date.fromisoformat(date_to)
            span = max((d1 - d0).days, 1)
            p_from = (d0 - timedelta(days=span)).isoformat()
            p_to = (d0 - timedelta(days=1)).isoformat()
            pp: list[Any] = [p_from, p_to]
            pw = "WHERE a.appointment_date >= ? AND a.appointment_date <= ?"
            if provider_id:
                pp.append(provider_id)
                pw += " AND a.provider_id = ?"
            pt = int(connection.execute(
                f"SELECT COUNT(*) AS cnt FROM appointments a {pw}", pp
            ).fetchone()["cnt"] or 0)
            pm = int(connection.execute(
                f"SELECT COUNT(*) AS cnt FROM appointments a {pw} AND a.status = 'cancelled'", pp
            ).fetchone()["cnt"] or 0)
            prior_rate = round(pm / pt * 100, 1) if pt > 0 else 0.0
            delta = round(rate - prior_rate, 1)
        except (ValueError, TypeError):
            pass

    return {
        "rate": rate,
        "count": missed,
        "missed": missed,
        "total": total,
        "prior_period_rate": prior_rate,
        "delta": delta,
        "trend": trend,
        "filters_applied": {
            "date_from": date_from,
            "date_to": date_to,
            "provider_id": provider_id,
        },
        "last_updated": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# US-062: Average Wait Time Metrics (BE-1, BE-2)
# ---------------------------------------------------------------------------

_DEFAULT_WAIT_THRESHOLD = 30  # minutes


def get_wait_time_metrics(
    connection: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
    provider_id: int | None = None,
    location: str | None = None,
    threshold_minutes: int = _DEFAULT_WAIT_THRESHOLD,
) -> dict[str, Any]:
    """Average and P95 wait-time with configurable threshold warning."""
    where, params = _build_filters(date_from, date_to, provider_id, location)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    ext = "AND" if where else "WHERE"

    rows = connection.execute(
        f"""
        SELECT a.duration_minutes, a.appointment_date
        FROM appointments a
        {where_sql} {ext} a.status = 'booked' AND a.duration_minutes IS NOT NULL
        """,
        params,
    ).fetchall()

    durations = [r["duration_minutes"] for r in rows if r["duration_minutes"] is not None]
    avg_wait = round(sum(durations) / len(durations), 1) if durations else 0.0
    sorted_d = sorted(durations)
    p95_idx = int(len(sorted_d) * 0.95) if sorted_d else 0
    p95_wait = sorted_d[min(p95_idx, len(sorted_d) - 1)] if sorted_d else 0

    threshold_exceeded = avg_wait > threshold_minutes

    trend_rows = connection.execute(
        f"""
        SELECT a.appointment_date AS period, AVG(a.duration_minutes) AS avg_wait
        FROM appointments a
        {where_sql} {ext} a.status = 'booked' AND a.duration_minutes IS NOT NULL
        GROUP BY a.appointment_date
        ORDER BY a.appointment_date
        """,
        params,
    ).fetchall()
    trend = [
        {"period": r["period"], "value": round(float(r["avg_wait"] or 0), 1)}
        for r in trend_rows
    ]

    return {
        "avg_wait_minutes": avg_wait,
        "p95_wait_minutes": p95_wait,
        "threshold_minutes": threshold_minutes,
        "threshold_exceeded": threshold_exceeded,
        "trend": trend,
        "sample_count": len(durations),
        "filters_applied": {
            "date_from": date_from,
            "date_to": date_to,
            "provider_id": provider_id,
            "location": location,
        },
        "last_updated": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# US-063: Appointment Utilization Analytics (BE-1)
# ---------------------------------------------------------------------------

def get_utilization_metrics(
    connection: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
    provider_id: int | None = None,
    specialty_id: int | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Booked vs available utilization analytics with provider/specialty breakdown."""
    where: list[str] = []
    params: list[Any] = []
    if date_from:
        where.append("a.appointment_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("a.appointment_date <= ?")
        params.append(date_to)
    if provider_id:
        where.append("a.provider_id = ?")
        params.append(provider_id)
    if specialty_id:
        where.append("a.specialty_id = ?")
        params.append(specialty_id)
    if location:
        where.append("LOWER(a.location) LIKE ?")
        params.append(f"%{location.lower()}%")

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    ext = "AND" if where else "WHERE"

    total = int(connection.execute(
        f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql}", params
    ).fetchone()["cnt"] or 0)

    booked = int(connection.execute(
        f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql} {ext} a.status = 'booked'",
        params,
    ).fetchone()["cnt"] or 0)

    available = int(connection.execute(
        f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql} {ext} a.status = 'available'",
        params,
    ).fetchone()["cnt"] or 0)

    utilization_rate = round(booked / total * 100, 1) if total > 0 else 0.0

    by_provider_rows = connection.execute(
        f"""
        SELECT p.id AS provider_id, p.name AS provider_name,
               COUNT(*) AS total,
               SUM(CASE WHEN a.status = 'booked' THEN 1 ELSE 0 END) AS booked
        FROM appointments a
        JOIN providers p ON p.id = a.provider_id
        {where_sql}
        GROUP BY p.id, p.name
        ORDER BY booked DESC
        LIMIT 10
        """,
        params,
    ).fetchall()
    by_provider = [
        {
            "provider_id": r["provider_id"],
            "provider": r["provider_name"],
            "total": r["total"],
            "booked": int(r["booked"] or 0),
            "utilization_rate": round(int(r["booked"] or 0) / r["total"] * 100, 1) if r["total"] > 0 else 0.0,
        }
        for r in by_provider_rows
    ]

    by_specialty_rows = connection.execute(
        f"""
        SELECT s.name AS specialty,
               COUNT(*) AS total,
               SUM(CASE WHEN a.status = 'booked' THEN 1 ELSE 0 END) AS booked
        FROM appointments a
        JOIN specialties s ON s.id = a.specialty_id
        {where_sql}
        GROUP BY s.id, s.name
        ORDER BY booked DESC
        """,
        params,
    ).fetchall()
    by_specialty = [
        {
            "specialty": r["specialty"],
            "total": r["total"],
            "booked": int(r["booked"] or 0),
            "utilization_rate": round(int(r["booked"] or 0) / r["total"] * 100, 1) if r["total"] > 0 else 0.0,
        }
        for r in by_specialty_rows
    ]

    return {
        "utilization_rate": utilization_rate,
        "booked": booked,
        "available": available,
        "total": total,
        "by_provider": by_provider,
        "by_specialty": by_specialty,
        "filters_applied": {
            "date_from": date_from,
            "date_to": date_to,
            "provider_id": provider_id,
            "specialty_id": specialty_id,
            "location": location,
        },
        "last_updated": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# US-064: Intake Completion Rates (BE-1, BE-2)
# ---------------------------------------------------------------------------

_INTAKE_COMPLETION_THRESHOLD = 70  # % below which low_completion_flag is True


def get_intake_completion_metrics(
    connection: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
    provider_id: int | None = None,
) -> dict[str, Any]:
    """Intake form completion rate: patients with intake elements vs scheduled visits."""
    appt_where = ["a.status = 'booked'"]
    appt_params: list[Any] = []
    if date_from:
        appt_where.append("a.appointment_date >= ?")
        appt_params.append(date_from)
    if date_to:
        appt_where.append("a.appointment_date <= ?")
        appt_params.append(date_to)
    if provider_id:
        appt_where.append("a.provider_id = ?")
        appt_params.append(provider_id)

    total = int(connection.execute(
        f"SELECT COUNT(*) AS cnt FROM appointments a WHERE {' AND '.join(appt_where)}",
        appt_params,
    ).fetchone()["cnt"] or 0)

    patients_with_intake = int(connection.execute(
        """SELECT COUNT(DISTINCT patient_id) AS cnt
           FROM clinical_profile_elements
           WHERE source_type = 'intake' AND is_active = 1"""
    ).fetchone()["cnt"] or 0)

    completed = min(patients_with_intake, total)
    rate = round(completed / total * 100, 1) if total > 0 else 0.0
    low_completion_flag = rate < _INTAKE_COMPLETION_THRESHOLD

    return {
        "completion_rate": rate,
        "completed": completed,
        "total": total,
        "low_completion_flag": low_completion_flag,
        "threshold": _INTAKE_COMPLETION_THRESHOLD,
        "filters_applied": {
            "date_from": date_from,
            "date_to": date_to,
            "provider_id": provider_id,
        },
        "last_updated": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# US-065: Insurance Verification Status Metrics (BE-1, BE-2)
# ---------------------------------------------------------------------------

def get_insurance_verification_metrics(
    connection: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
    provider_id: int | None = None,
    status_filter: str | None = None,
) -> dict[str, Any]:
    """Insurance verification metrics derived from appointment checkout_status.

    Mapping: confirmed → verified; reserved/searching → pending;
             expired/cancelled → failed (needs action).
    """
    where, params = _build_filters(date_from, date_to, provider_id, None)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    ext = "AND" if where else "WHERE"

    verified = int(connection.execute(
        f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql} {ext} a.checkout_status = 'confirmed'",
        params,
    ).fetchone()["cnt"] or 0)

    pending = int(connection.execute(
        f"""SELECT COUNT(*) AS cnt FROM appointments a {where_sql}
            {ext} a.checkout_status IN ('reserved', 'searching')""",
        params,
    ).fetchone()["cnt"] or 0)

    failed = int(connection.execute(
        f"""SELECT COUNT(*) AS cnt FROM appointments a {where_sql}
            {ext} a.checkout_status IN ('expired', 'cancelled')""",
        params,
    ).fetchone()["cnt"] or 0)

    total = verified + pending + failed
    issue_flag = (pending + failed) > 0

    return {
        "verified": verified,
        "pending": pending,
        "failed": failed,
        "total": total,
        "issue_flag": issue_flag,
        "filters_applied": {
            "date_from": date_from,
            "date_to": date_to,
            "provider_id": provider_id,
            "status_filter": status_filter,
        },
        "last_updated": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# US-066: AI-Human Agreement Rate (BE-1, BE-2)
# ---------------------------------------------------------------------------

def get_agreement_rate_metrics(
    connection: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
    provider_id: int | None = None,
) -> dict[str, Any]:
    """AI-human agreement rate from clinical code review audit outcomes."""
    where: list[str] = []
    params: list[Any] = []
    if date_from:
        where.append("cra.acted_at >= ?")
        params.append(date_from)
    if date_to:
        where.append("cra.acted_at <= ?")
        params.append(date_to)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    rows = connection.execute(
        f"""
        SELECT cra.action, cs.code_type, COUNT(*) AS cnt
        FROM clinical_code_review_audit cra
        JOIN clinical_code_suggestions cs ON cs.id = cra.suggestion_id
        {where_sql}
        GROUP BY cra.action, cs.code_type
        """,
        params,
    ).fetchall()

    total_reviewed = 0
    agreed = 0
    by_cat: dict[str, dict[str, int]] = {}
    for row in rows:
        cnt = row["cnt"]
        action = row["action"]
        code_type = row["code_type"]
        total_reviewed += cnt
        if action == "accept":
            agreed += cnt
        cat = by_cat.setdefault(code_type, {"agreed": 0, "disagreed": 0, "total": 0})
        cat["total"] += cnt
        if action == "accept":
            cat["agreed"] += cnt
        else:
            cat["disagreed"] += cnt

    agreement_rate = round(agreed / total_reviewed * 100, 1) if total_reviewed > 0 else 0.0

    auto_row = connection.execute(
        "SELECT COUNT(*) AS cnt FROM clinical_code_suggestions WHERE auto_accepted = 1 AND status = 'accepted'"
    ).fetchone()
    auto_accepted = int(auto_row["cnt"] or 0)

    trend_rows = connection.execute(
        f"""
        SELECT DATE(cra.acted_at) AS period,
               SUM(CASE WHEN cra.action = 'accept' THEN 1 ELSE 0 END) AS agreed,
               COUNT(*) AS total
        FROM clinical_code_review_audit cra
        JOIN clinical_code_suggestions cs ON cs.id = cra.suggestion_id
        {where_sql}
        GROUP BY DATE(cra.acted_at)
        ORDER BY DATE(cra.acted_at)
        """,
        params,
    ).fetchall()
    trend = [
        {
            "period": r["period"],
            "value": round(r["agreed"] / r["total"] * 100, 1) if r["total"] > 0 else 0.0,
        }
        for r in trend_rows
    ]

    by_category = [
        {
            "category": cat,
            "agreed": vals["agreed"],
            "disagreed": vals["disagreed"],
            "total": vals["total"],
            "agreement_rate": round(vals["agreed"] / vals["total"] * 100, 1) if vals["total"] > 0 else 0.0,
        }
        for cat, vals in by_cat.items()
    ]

    return {
        "agreement_rate": agreement_rate,
        "reviewed": total_reviewed,
        "agreed": agreed,
        "auto_accepted": auto_accepted,
        "trend": trend,
        "by_category": by_category,
        "filters_applied": {
            "date_from": date_from,
            "date_to": date_to,
            "provider_id": provider_id,
        },
        "last_updated": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# US-068: Filter Options for Dashboard Dropdowns (BE-2)
# ---------------------------------------------------------------------------

def get_filter_options(connection: sqlite3.Connection) -> dict[str, Any]:
    """Return provider, specialty, and location options for filter dropdowns."""
    providers = connection.execute(
        "SELECT id, name, credentials FROM providers WHERE is_active = 1 ORDER BY name"
    ).fetchall()
    specialties = connection.execute(
        "SELECT id, name FROM specialties WHERE is_active = 1 ORDER BY name"
    ).fetchall()
    location_rows = connection.execute(
        "SELECT DISTINCT location FROM appointments ORDER BY location"
    ).fetchall()
    return {
        "providers": [
            {"id": r["id"], "name": r["name"], "credentials": r["credentials"]}
            for r in providers
        ],
        "specialties": [{"id": r["id"], "name": r["name"]} for r in specialties],
        "locations": [r["location"] for r in location_rows if r["location"]],
    }


# ---------------------------------------------------------------------------
# US-069: CSV Export (BE-1, BE-2, BE-3)
# ---------------------------------------------------------------------------

def export_operational_metrics_csv(
    connection: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
    provider_id: int | None = None,
    location: str | None = None,
) -> bytes:
    """Generate a UTF-8 CSV export of appointments matching the active filters."""
    where, params = _build_filters(date_from, date_to, provider_id, location)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    rows = connection.execute(
        f"""
        SELECT a.id, a.appointment_date, a.start_time, a.end_time, a.location,
               a.status, a.duration_minutes, a.checkout_status,
               p.name AS provider_name, s.name AS specialty
        FROM appointments a
        JOIN providers p ON p.id = a.provider_id
        JOIN specialties s ON s.id = a.specialty_id
        {where_sql}
        ORDER BY a.appointment_date ASC, a.start_time ASC
        """,
        params,
    ).fetchall()

    buf = _io.StringIO()
    writer = _csv.writer(buf)
    writer.writerow([
        "ID", "Date", "Start Time", "End Time", "Location",
        "Status", "Duration (min)", "Checkout Status",
        "Provider", "Specialty",
    ])
    for row in rows:
        writer.writerow([
            row["id"], row["appointment_date"], row["start_time"], row["end_time"],
            row["location"], row["status"], row["duration_minutes"],
            row["checkout_status"], row["provider_name"], row["specialty"],
        ])

    return buf.getvalue().encode("utf-8")
