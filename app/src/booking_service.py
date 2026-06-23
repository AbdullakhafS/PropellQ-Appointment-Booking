from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet

from src.search_service import TIME_OF_DAY

BASE_DIR = Path(__file__).resolve().parents[1]
GENERATED_DIR = BASE_DIR / "generated"
PDF_DIR = GENERATED_DIR / "confirmations"

DEFAULT_PATIENT_ID = 1
DEFAULT_TIMEZONE = "America/Chicago"
MAX_CONFIRMATION_RETRIES = 3
CONFIRMATION_RETRY_DELAYS_SECONDS = [1, 5, 30]
MAX_REMINDER_RETRIES = 3
SYNC_MAX_RETRIES = 3
SYNC_BACKOFF_SECONDS = [5, 30, 300]
REMINDER_WINDOWS = {
    "48h": timedelta(hours=48),
    "24h": timedelta(hours=24),
    "2h": timedelta(hours=2),
}
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.calendarList.readonly",
    "https://www.googleapis.com/auth/calendar.settings.readonly",
]
OUTLOOK_SCOPES = [
    "Calendars.ReadWrite",
    "offline_access",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def get_patient_profile(connection: sqlite3.Connection, patient_id: int = DEFAULT_PATIENT_ID) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM patient_profiles WHERE id = ?",
        [patient_id],
    ).fetchone()
    return dict(row) if row else {}


def get_staff_queue(
    connection: sqlite3.Connection,
    provider_ids: list[int] | None = None,
) -> dict[str, Any]:
    """
    Return today's booked appointments scoped to *provider_ids* (task_045_001).

    When *provider_ids* is ``None`` (admin bypass), all of today's booked
    appointments are returned.  When it is an empty list the caller has no
    active assignments and an empty queue is returned immediately.
    """
    today = date.today().isoformat()

    if provider_ids is not None and len(provider_ids) == 0:
        return {"items": [], "total": 0}

    if provider_ids is None:
        rows = connection.execute(
            """
            SELECT a.*, p.name AS provider_name
            FROM appointments a
            JOIN providers p ON p.id = a.provider_id
            WHERE a.appointment_date = ?
              AND a.status = 'booked'
            ORDER BY a.start_time
            """,
            [today],
        ).fetchall()
    else:
        placeholders = ",".join("?" * len(provider_ids))
        rows = connection.execute(
            f"""
            SELECT a.*, p.name AS provider_name
            FROM appointments a
            JOIN providers p ON p.id = a.provider_id
            WHERE a.appointment_date = ?
              AND a.status = 'booked'
              AND a.provider_id IN ({placeholders})
            ORDER BY a.start_time
            """,
            [today, *provider_ids],
        ).fetchall()

    items = [dict(row) for row in rows]
    return {"items": items, "total": len(items)}



def get_patient_session(connection: sqlite3.Connection, patient_id: int = DEFAULT_PATIENT_ID) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM patient_sessions WHERE patient_profile_id = ?",
        [patient_id],
    ).fetchone()
    return dict(row) if row else {}


def dashboard_metrics(connection: sqlite3.Connection) -> dict[str, Any]:
    appointment_counts = connection.execute(
        "SELECT status, COUNT(*) AS count FROM appointments GROUP BY status"
    ).fetchall()
    deliveries = connection.execute(
        "SELECT status, COUNT(*) AS count FROM confirmation_deliveries GROUP BY status"
    ).fetchall()
    reminders = connection.execute(
        "SELECT delivery_status, COUNT(*) AS count FROM reminder_log GROUP BY delivery_status"
    ).fetchall()
    reminders_by_type = connection.execute(
        """
        SELECT reminder_type, delivery_status, COUNT(*) AS count
        FROM reminder_log
        GROUP BY reminder_type, delivery_status
        """
    ).fetchall()
    sync = connection.execute(
        "SELECT status, COUNT(*) AS count FROM calendar_sync_queue GROUP BY status"
    ).fetchall()
    sync_failed = connection.execute(
        "SELECT calendar_type, COUNT(*) AS count FROM calendar_sync_queue WHERE status = 'failed' GROUP BY calendar_type"
    ).fetchall()

    reminder_breakdown: dict[str, dict[str, int]] = {}
    for row in reminders_by_type:
        rtype = row["reminder_type"]
        reminder_breakdown.setdefault(rtype, {})
        reminder_breakdown[rtype][row["delivery_status"]] = row["count"]

    return {
        "appointments": {row["status"]: row["count"] for row in appointment_counts},
        "confirmations": {row["status"]: row["count"] for row in deliveries},
        "reminders": {row["delivery_status"]: row["count"] for row in reminders},
        "remindersByWindow": reminder_breakdown,
        "calendarSync": {row["status"]: row["count"] for row in sync},
        "calendarSyncFailedByProvider": {row["calendar_type"]: row["count"] for row in sync_failed},
    }


def get_integration_state(connection: sqlite3.Connection, patient_id: int = DEFAULT_PATIENT_ID) -> dict[str, Any]:
    session = get_patient_session(connection, patient_id)
    return {
        "google": {
            "status": session.get("google_auth_status", "revoked"),
            "connected": session.get("google_auth_status") == "authorized",
            "calendarId": session.get("google_calendar_id"),
        },
        "outlook": {
            "status": session.get("outlook_auth_status", "revoked"),
            "connected": session.get("outlook_auth_status") == "authorized",
            "calendarId": session.get("outlook_calendar_id"),
        },
    }


def _derive_fernet() -> Fernet:
    secret = os.getenv("PROPELLQ_TOKEN_SECRET", "propellq-demo-secret")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_token(token: str) -> str:
    return _derive_fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(token: str | None) -> str | None:
    if not token:
        return None
    return _derive_fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def _appointment_local_start(appointment: dict[str, Any], timezone_name: str | None = None) -> datetime:
    zone = ZoneInfo(timezone_name or appointment.get("patient_timezone") or appointment.get("appointment_timezone") or DEFAULT_TIMEZONE)
    local_value = datetime.combine(
        date.fromisoformat(appointment["appointment_date"]),
        time.fromisoformat(appointment["start_time"]),
        tzinfo=zone,
    )
    return local_value.astimezone(timezone.utc)


def _appointment_local_end(appointment: dict[str, Any], timezone_name: str | None = None) -> datetime:
    zone = ZoneInfo(timezone_name or appointment.get("patient_timezone") or appointment.get("appointment_timezone") or DEFAULT_TIMEZONE)
    local_value = datetime.combine(
        date.fromisoformat(appointment["appointment_date"]),
        time.fromisoformat(appointment["end_time"]),
        tzinfo=zone,
    )
    return local_value.astimezone(timezone.utc)


def build_calendar_payload(
    connection: sqlite3.Connection,
    filters: dict[str, Any],
    view_mode: str,
    anchor_date: str | None,
) -> dict[str, Any]:
    anchor = date.fromisoformat(anchor_date) if anchor_date else date.today()
    if view_mode == "week":
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=13)
    else:
        start = anchor.replace(day=1)
        start = start - timedelta(days=start.weekday())
        end = start + timedelta(days=41)

    where_clauses = [
        "a.appointment_date >= ?",
        "a.appointment_date <= ?",
        "p.is_active = 1",
        "s.is_active = 1",
    ]
    values: list[Any] = [start.isoformat(), end.isoformat()]

    if filters.get("provider"):
        where_clauses.append("LOWER(p.name) LIKE ?")
        values.append(f"%{filters['provider'].lower()}%")
    if filters.get("specialty"):
        where_clauses.append("LOWER(s.name) = ?")
        values.append(filters["specialty"].lower())
    if filters.get("time_of_day"):
        start_time, end_time = TIME_OF_DAY[filters["time_of_day"]]
        where_clauses.append("a.start_time BETWEEN ? AND ?")
        values.extend([start_time, end_time])

    sql = f"""
        SELECT
            a.id,
            a.appointment_date,
            a.start_time,
            a.end_time,
            a.location,
            a.status,
            a.duration_minutes,
            a.appointment_timezone,
            p.id AS provider_id,
            p.name AS provider_name,
            p.credentials,
            p.photo_url,
            p.review_count,
            p.bio,
            s.name AS specialty
        FROM appointments a
        INNER JOIN providers p ON p.id = a.provider_id
        INNER JOIN specialties s ON s.id = a.specialty_id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY a.appointment_date ASC, a.start_time ASC, a.id ASC
    """
    rows = [dict(row) for row in connection.execute(sql, values).fetchall()]

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["appointment_date"], []).append(row)

    days = []
    current = start
    while current <= end:
        day_key = current.isoformat()
        days.append(
            {
                "date": day_key,
                "dayLabel": current.strftime("%a"),
                "dayNumber": current.day,
                "isCurrentMonth": current.month == anchor.month,
                "slots": grouped.get(day_key, []),
            }
        )
        current += timedelta(days=1)

    return {
        "view": view_mode,
        "anchorDate": anchor.isoformat(),
        "rangeStart": start.isoformat(),
        "rangeEnd": end.isoformat(),
        "timezone": DEFAULT_TIMEZONE,
        "utcFooter": "Times shown in patient local timezone; sync stored in UTC.",
        "days": days,
    }


def get_appointment_details(connection: sqlite3.Connection, appointment_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            a.*,
            p.name AS provider_name,
            p.credentials,
            p.photo_url,
            p.review_count,
            p.bio,
            s.name AS specialty
        FROM appointments a
        INNER JOIN providers p ON p.id = a.provider_id
        INNER JOIN specialties s ON s.id = a.specialty_id
        WHERE a.id = ?
        """,
        [appointment_id],
    ).fetchone()
    return dict(row) if row else None


def expire_stale_reservations(connection: sqlite3.Connection) -> None:
    now = to_iso(utc_now())
    stale_rows = connection.execute(
        "SELECT appointment_id FROM appointment_reservations WHERE status = 'active' AND expires_at < ?",
        [now],
    ).fetchall()

    connection.execute(
        "UPDATE appointment_reservations SET status = 'expired' WHERE status = 'active' AND expires_at < ?",
        [now],
    )

    for row in stale_rows:
        connection.execute(
            """
            UPDATE appointments
            SET checkout_status = 'expired', reservation_token = NULL
            WHERE id = ? AND checkout_status = 'reserved'
            """,
            [row["appointment_id"]],
        )
    connection.commit()


def create_checkout_reservation(
    connection: sqlite3.Connection,
    appointment_id: int,
    payload: dict[str, Any],
    patient_id: int = DEFAULT_PATIENT_ID,
) -> tuple[int, dict[str, Any]]:
    expire_stale_reservations(connection)
    idempotency_key = payload.get("idempotencyKey") or uuid.uuid4().hex
    existing = connection.execute(
        """
        SELECT * FROM appointment_reservations
        WHERE appointment_id = ? AND idempotency_key = ? AND status = 'active'
        """,
        [appointment_id, idempotency_key],
    ).fetchone()
    if existing:
        appointment = get_appointment_details(connection, appointment_id)
        return 200, {
            "reservationId": existing["id"],
            "reservationToken": existing["reservation_token"],
            "expiresAt": existing["expires_at"],
            "appointment": appointment,
        }

    appointment = get_appointment_details(connection, appointment_id)
    if appointment is None or appointment["status"] != "available":
        return 409, {"code": "UNAVAILABLE_SLOT", "message": "Selected slot is no longer available."}

    active = connection.execute(
        "SELECT COUNT(*) AS count FROM appointment_reservations WHERE appointment_id = ? AND status = 'active'",
        [appointment_id],
    ).fetchone()["count"]
    if active > 0:
        return 409, {"code": "RESERVED", "message": "Another patient is checking out this slot."}

    expires_at = utc_now() + timedelta(seconds=60)
    reservation_token = uuid.uuid4().hex
    preferred_slot_id = payload.get("preferredSlotId")

    with connection:
        connection.execute(
            """
            INSERT INTO appointment_reservations(
                appointment_id,
                patient_profile_id,
                reservation_token,
                idempotency_key,
                expires_at,
                preferred_slot_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                appointment_id,
                patient_id,
                reservation_token,
                idempotency_key,
                to_iso(expires_at),
                preferred_slot_id,
            ),
        )
        connection.execute(
            """
            UPDATE appointments
            SET checkout_status = 'reserved',
                reservation_expires_at = ?,
                reservation_token = ?,
                version = version + 1
            WHERE id = ?
            """,
            [to_iso(expires_at), reservation_token, appointment_id],
        )
        connection.execute(
            """
            INSERT INTO booking_events(appointment_id, event_type, correlation_id, payload_json)
            VALUES (?, 'reservation_created', ?, ?)
            """,
            (appointment_id, uuid.uuid4().hex, json.dumps(payload)),
        )

    return 200, {
        "reservationToken": reservation_token,
        "expiresAt": to_iso(expires_at),
        "appointment": appointment,
        "preferredSlotId": preferred_slot_id,
    }


def finalize_booking(
    connection: sqlite3.Connection,
    reservation_token: str,
    payload: dict[str, Any],
    patient_id: int = DEFAULT_PATIENT_ID,
) -> tuple[int, dict[str, Any]]:
    expire_stale_reservations(connection)
    reservation = connection.execute(
        "SELECT * FROM appointment_reservations WHERE reservation_token = ?",
        [reservation_token],
    ).fetchone()
    if reservation is None:
        return 410, {"code": "RESERVATION_EXPIRED", "message": "Reservation has expired."}

    reservation_data = dict(reservation)
    if reservation_data["status"] == "confirmed":
        appointment = get_appointment_details(connection, reservation_data["appointment_id"])
        return 200, {"appointment": appointment, "reservationToken": reservation_token}

    if reservation_data["status"] != "active" or parse_iso(reservation_data["expires_at"]) < utc_now():
        return 410, {"code": "RESERVATION_EXPIRED", "message": "Reservation has expired."}

    appointment = get_appointment_details(connection, reservation_data["appointment_id"])
    if appointment is None or appointment["status"] != "available":
        return 409, {"code": "UNAVAILABLE_SLOT", "message": "Selected slot is no longer available."}

    patient_profile = get_patient_profile(connection, patient_id)
    channels = payload.get("reminderChannels") or json.loads(patient_profile.get("reminder_channels", "[]"))
    correlation_id = uuid.uuid4().hex
    preferred_slot_id = payload.get("preferredSlotId") or reservation_data.get("preferred_slot_id")
    preferred_window = utc_now() + timedelta(hours=24) if preferred_slot_id else None
    idempotency_key = payload.get("idempotencyKey") or uuid.uuid4().hex
    if connection.execute(
        "SELECT COUNT(*) AS count FROM booking_events WHERE event_type = 'booking_confirmed' AND correlation_id = ?",
        [idempotency_key],
    ).fetchone()["count"]:
        appointment = get_appointment_details(connection, reservation_data["appointment_id"])
        return 200, {"appointment": appointment, "reservationToken": reservation_token}

    with connection:
        connection.execute(
            """
            UPDATE patient_profiles
            SET first_name = ?,
                last_name = ?,
                email = ?,
                phone = ?,
                preferred_timezone = ?,
                reminder_channels = ?
            WHERE id = ?
            """,
            (
                payload.get("firstName") or patient_profile["first_name"],
                payload.get("lastName") or patient_profile["last_name"],
                payload.get("email") or patient_profile["email"],
                payload.get("phone") or patient_profile["phone"],
                payload.get("timezone") or patient_profile["preferred_timezone"],
                json.dumps(channels),
                patient_id,
            ),
        )
        connection.execute(
            """
            UPDATE appointments
            SET status = 'booked',
                checkout_status = 'confirmed',
                patient_first_name = ?,
                patient_last_name = ?,
                patient_email = ?,
                patient_phone = ?,
                patient_timezone = ?,
                patient_notes = ?,
                preferred_slot_id = ?,
                preferred_window_expires_at = ?,
                reservation_expires_at = NULL,
                reservation_token = NULL,
                version = version + 1
            WHERE id = ?
            """,
            (
                payload.get("firstName") or patient_profile["first_name"],
                payload.get("lastName") or patient_profile["last_name"],
                payload.get("email") or patient_profile["email"],
                payload.get("phone") or patient_profile["phone"],
                payload.get("timezone") or patient_profile["preferred_timezone"],
                payload.get("notes"),
                preferred_slot_id,
                to_iso(preferred_window) if preferred_window else None,
                reservation_data["appointment_id"],
            ),
        )
        connection.execute(
            "UPDATE appointment_reservations SET status = 'confirmed', confirmed_at = ? WHERE id = ?",
            [to_iso(utc_now()), reservation_data["id"]],
        )
        connection.execute(
            """
            INSERT INTO booking_events(reservation_id, appointment_id, event_type, correlation_id, payload_json)
            VALUES (?, ?, 'booking_confirmed', ?, ?)
            """,
            (
                reservation_data["id"],
                reservation_data["appointment_id"],
                idempotency_key,
                json.dumps(payload),
            ),
        )

    appointment = get_appointment_details(connection, reservation_data["appointment_id"])
    enqueue_confirmation_delivery(connection, appointment)
    enqueue_sync_actions(connection, appointment)

    return 200, {
        "appointment": appointment,
        "reservationToken": reservation_token,
        "channels": channels,
        "correlationId": correlation_id,
    }


def enqueue_confirmation_delivery(connection: sqlite3.Connection, appointment: dict[str, Any]) -> None:
    exists = connection.execute(
        "SELECT COUNT(*) AS count FROM confirmation_deliveries WHERE appointment_id = ? AND status IN ('queued', 'sent')",
        [appointment["id"]],
    ).fetchone()["count"]
    if exists:
        return

    connection.execute(
        """
        INSERT INTO confirmation_deliveries(appointment_id, recipient_email, status)
        VALUES (?, ?, 'queued')
        """,
        [appointment["id"], appointment.get("patient_email") or "alex.morgan@example.com"],
    )
    connection.commit()


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_simple_pdf(output_path: Path, title: str, lines: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text_lines = [title, *lines]
    commands = ["BT", "/F1 16 Tf", "50 770 Td"]
    first = True
    for line in text_lines:
        if not first:
            commands.append("0 -22 Td")
        commands.append(f"({_escape_pdf_text(line)}) Tj")
        first = False
    commands.append("ET")
    content_stream = "\n".join(commands).encode("utf-8")

    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
    )
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(
        f"5 0 obj << /Length {len(content_stream)} >> stream\n".encode("utf-8")
        + content_stream
        + b"\nendstream endobj\n"
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("utf-8"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("utf-8"))
    pdf.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode(
            "utf-8"
        )
    )
    output_path.write_bytes(pdf)


def _deliver_confirmation(delivery: dict[str, Any]) -> str:
    pdf_path = PDF_DIR / f"appointment-{delivery['appointment_id']}.pdf"
    _write_simple_pdf(
        pdf_path,
        "PropellQ Appointment Confirmation",
        [
            f"Patient: {delivery['patient_first_name'] or 'Alex'}",
            f"Provider: {delivery['provider_name']}",
            f"Date: {delivery['appointment_date']} at {delivery['start_time']}",
            f"Location: {delivery['location']}",
            "Manage booking: https://propellq.example.com/manage-booking",
        ],
    )
    return str(pdf_path)


def process_confirmation_queue(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT cd.*, a.patient_first_name, a.patient_email, a.appointment_date, a.start_time,
               a.location, p.name AS provider_name
        FROM confirmation_deliveries cd
        INNER JOIN appointments a ON a.id = cd.appointment_id
        INNER JOIN providers p ON p.id = a.provider_id
        WHERE cd.status = 'queued'
        ORDER BY cd.queued_at ASC
        """
    ).fetchall()

    processed = 0
    failed = 0
    escalated = 0
    for row in rows:
        delivery = dict(row)
        try:
            pdf_path = _deliver_confirmation(delivery)
            external_id = f"email-{uuid.uuid4().hex[:12]}"
            connection.execute(
                """
                UPDATE confirmation_deliveries
                SET status = 'sent',
                    attachment_path = ?,
                    external_message_id = ?,
                    sent_at = ?
                WHERE id = ?
                """,
                [pdf_path, external_id, to_iso(utc_now()), delivery["id"]],
            )
            connection.execute(
                "UPDATE appointments SET confirmation_sent_at = ? WHERE id = ?",
                [to_iso(utc_now()), delivery["appointment_id"]],
            )
            processed += 1
        except Exception as exc:
            new_retry_count = delivery["retry_count"] + 1
            if new_retry_count >= MAX_CONFIRMATION_RETRIES:
                connection.execute(
                    """
                    UPDATE confirmation_deliveries
                    SET status = 'failed',
                        retry_count = ?,
                        failure_reason = ?
                    WHERE id = ?
                    """,
                    [new_retry_count, str(exc)[:512], delivery["id"]],
                )
                escalated += 1
            else:
                connection.execute(
                    """
                    UPDATE confirmation_deliveries
                    SET retry_count = ?,
                        failure_reason = ?
                    WHERE id = ?
                    """,
                    [new_retry_count, str(exc)[:512], delivery["id"]],
                )
                failed += 1
    connection.commit()
    return {"processed": processed, "failed": failed, "escalated": escalated}


def resend_confirmation(connection: sqlite3.Connection, appointment_id: int) -> tuple[int, dict[str, Any]]:
    appointment = get_appointment_details(connection, appointment_id)
    if appointment is None:
        return 404, {"code": "APPOINTMENT_NOT_FOUND", "message": "Appointment not found."}
    if appointment.get("checkout_status") != "confirmed":
        return 400, {"code": "INVALID_STATE", "message": "Confirmation can only be resent for confirmed appointments."}

    existing = connection.execute(
        "SELECT * FROM confirmation_deliveries WHERE appointment_id = ? ORDER BY id DESC LIMIT 1",
        [appointment_id],
    ).fetchone()
    if existing and dict(existing)["status"] in ("queued", "sent"):
        return 200, {"message": "Confirmation is already queued or delivered.", "appointmentId": appointment_id}

    connection.execute(
        """
        INSERT INTO confirmation_deliveries(appointment_id, recipient_email, status, retry_count)
        VALUES (?, ?, 'queued', 0)
        """,
        [appointment_id, appointment.get("patient_email") or "alex.morgan@example.com"],
    )
    connection.commit()
    return 200, {"message": "Confirmation re-queued for delivery.", "appointmentId": appointment_id}



def _send_reminder(appointment: dict[str, Any], reminder_key: str, channel: str) -> str:
    """Format and simulate sending a reminder. Returns external_message_id."""
    patient_name = appointment.get("patient_first_name") or "Patient"
    appt_date = appointment["appointment_date"]
    appt_time = appointment["start_time"]
    provider_name = appointment["provider_name"]
    manage_url = "https://propellq.example.com/manage"
    if channel == "sms":
        body = (
            f"Reminder: {appt_date} {appt_time} w/ {provider_name}. "
            f"Manage: {manage_url}"
        )
        if len(body) > 160:
            body = body[:157] + "..."
    else:
        body = (
            f"Hi {patient_name}, your PropellQ appointment on {appt_date} at "
            f"{appt_time} with {provider_name} is coming up. Manage booking: {manage_url}"
        )
    # Simulate delivery (in production, calls SMS/email provider API)
    del body  # suppress unused warning; send is simulated
    return f"{channel}-{uuid.uuid4().hex[:10]}"


def process_due_reminders(connection: sqlite3.Connection, reference_time: datetime | None = None) -> dict[str, Any]:
    now = reference_time or utc_now()
    patient = get_patient_profile(connection, DEFAULT_PATIENT_ID)
    appointments = [
        dict(row)
        for row in connection.execute(
            """
            SELECT a.*, p.name AS provider_name
            FROM appointments a
            INNER JOIN providers p ON p.id = a.provider_id
            WHERE a.checkout_status = 'confirmed' AND a.status = 'booked'
            """
        ).fetchall()
    ]
    channels = json.loads(patient.get("reminder_channels", "[]"))
    sent = 0
    skipped = 0
    failed = 0

    for appointment in appointments:
        if patient.get("do_not_disturb"):
            skipped += 1
            continue

        appointment_start = _appointment_local_start(appointment, patient.get("preferred_timezone"))
        for reminder_key, delta in REMINDER_WINDOWS.items():
            due_time = appointment_start - delta
            already_sent_field = f"reminder_sent_{reminder_key}_at"
            if appointment.get(already_sent_field):
                continue
            if not (due_time <= now <= due_time + timedelta(minutes=15)):
                continue
            for channel in channels:
                prior_failures = connection.execute(
                    """
                    SELECT COUNT(*) AS count FROM reminder_log
                    WHERE appointment_id = ? AND reminder_type = ? AND channel = ?
                      AND delivery_status = 'failed'
                    """,
                    [appointment["id"], reminder_key, channel],
                ).fetchone()["count"]
                if prior_failures >= MAX_REMINDER_RETRIES:
                    # Max retries exhausted — mark done to prevent infinite loop
                    connection.execute(
                        f"UPDATE appointments SET {already_sent_field} = ? WHERE id = ?",
                        [to_iso(now), appointment["id"]],
                    )
                    failed += 1
                    continue
                try:
                    external_id = _send_reminder(appointment, reminder_key, channel)
                    connection.execute(
                        """
                        INSERT INTO reminder_log(
                            appointment_id,
                            patient_profile_id,
                            reminder_type,
                            channel,
                            delivery_status,
                            retry_count,
                            sent_at,
                            external_message_id,
                            correlation_id
                        )
                        VALUES (?, ?, ?, ?, 'sent', ?, ?, ?, ?)
                        """,
                        (
                            appointment["id"],
                            DEFAULT_PATIENT_ID,
                            reminder_key,
                            channel,
                            prior_failures,
                            to_iso(now),
                            external_id,
                            uuid.uuid4().hex,
                        ),
                    )
                    connection.execute(
                        f"UPDATE appointments SET {already_sent_field} = ? WHERE id = ?",
                        [to_iso(now), appointment["id"]],
                    )
                    sent += 1
                except Exception as exc:
                    new_count = prior_failures + 1
                    connection.execute(
                        """
                        INSERT INTO reminder_log(
                            appointment_id,
                            patient_profile_id,
                            reminder_type,
                            channel,
                            delivery_status,
                            retry_count,
                            failure_reason,
                            correlation_id
                        )
                        VALUES (?, ?, ?, ?, 'failed', ?, ?, ?)
                        """,
                        (
                            appointment["id"],
                            DEFAULT_PATIENT_ID,
                            reminder_key,
                            channel,
                            new_count,
                            str(exc)[:512],
                            uuid.uuid4().hex,
                        ),
                    )
                    if new_count >= MAX_REMINDER_RETRIES:
                        connection.execute(
                            f"UPDATE appointments SET {already_sent_field} = ? WHERE id = ?",
                            [to_iso(now), appointment["id"]],
                        )
                    failed += 1
    connection.commit()
    return {"sent": sent, "skipped": skipped, "failed": failed}


def process_preferred_swaps(connection: sqlite3.Connection, reference_time: datetime | None = None) -> dict[str, Any]:
    now = reference_time or utc_now()
    rows = [
        dict(row)
        for row in connection.execute(
            """
            SELECT * FROM appointments
            WHERE status = 'booked' AND preferred_slot_id IS NOT NULL AND preferred_window_expires_at IS NOT NULL
            """
        ).fetchall()
    ]
    completed = 0
    skipped = 0
    for current in rows:
        expires_at = parse_iso(current["preferred_window_expires_at"])
        if expires_at and expires_at < now:
            connection.execute(
                """
                INSERT INTO preferred_slot_swap_history(
                    appointment_id, original_slot_id, status, reason_code, correlation_id
                )
                VALUES (?, ?, 'skipped', 'window_expired', ?)
                """,
                (current["id"], current["id"], uuid.uuid4().hex),
            )
            skipped += 1
            continue

        preferred = get_appointment_details(connection, current["preferred_slot_id"])
        if preferred is None or preferred["status"] != "available":
            connection.execute(
                """
                INSERT INTO preferred_slot_swap_history(
                    appointment_id, original_slot_id, new_slot_id, status, reason_code, correlation_id
                )
                VALUES (?, ?, ?, 'skipped', 'preferred_unavailable', ?)
                """,
                (current["id"], current["id"], current["preferred_slot_id"], uuid.uuid4().hex),
            )
            skipped += 1
            continue

        correlation_id = uuid.uuid4().hex
        with connection:
            connection.execute(
                """
                UPDATE appointments
                SET status = 'available',
                    checkout_status = 'searching',
                    patient_first_name = NULL,
                    patient_last_name = NULL,
                    patient_email = NULL,
                    patient_phone = NULL,
                    patient_timezone = NULL,
                    patient_notes = NULL,
                    preferred_slot_id = NULL,
                    preferred_window_expires_at = NULL,
                    version = version + 1
                WHERE id = ?
                """,
                [current["id"]],
            )
            connection.execute(
                """
                UPDATE appointments
                SET status = 'booked',
                    checkout_status = 'confirmed',
                    patient_first_name = ?,
                    patient_last_name = ?,
                    patient_email = ?,
                    patient_phone = ?,
                    patient_timezone = ?,
                    patient_notes = ?,
                    preferred_slot_id = NULL,
                    preferred_window_expires_at = NULL,
                    version = version + 1
                WHERE id = ?
                """,
                (
                    current["patient_first_name"],
                    current["patient_last_name"],
                    current["patient_email"],
                    current["patient_phone"],
                    current["patient_timezone"],
                    current["patient_notes"],
                    preferred["id"],
                ),
            )
            connection.execute(
                """
                INSERT INTO preferred_slot_swap_history(
                    appointment_id,
                    original_slot_id,
                    new_slot_id,
                    status,
                    reason_code,
                    correlation_id
                )
                VALUES (?, ?, ?, 'completed', 'preferred_slot_opened', ?)
                """,
                (current["id"], current["id"], preferred["id"], correlation_id),
            )
        connection.execute(
            """
            INSERT INTO reminder_log(
                appointment_id,
                patient_profile_id,
                reminder_type,
                channel,
                delivery_status,
                retry_count,
                sent_at,
                external_message_id,
                correlation_id
            )
            VALUES (?, ?, 'swap', 'email', 'sent', 0, ?, ?, ?)
            """,
            (preferred["id"], DEFAULT_PATIENT_ID, to_iso(now), f"swap-{uuid.uuid4().hex[:10]}", correlation_id),
        )
        completed += 1
    connection.commit()
    return {"completed": completed, "skipped": skipped}


def authorize_provider(connection: sqlite3.Connection, provider: str, patient_id: int = DEFAULT_PATIENT_ID) -> str:
    nonce = uuid.uuid4().hex
    connection.execute(
        "UPDATE patient_sessions SET oauth_state_nonce = ?, updated_at = ? WHERE patient_profile_id = ?",
        [nonce, to_iso(utc_now()), patient_id],
    )
    connection.commit()
    return f"/api/auth/{provider}/callback?state={nonce}&code=mock-{provider}-code"


def complete_provider_authorization(
    connection: sqlite3.Connection,
    provider: str,
    state: str,
    code: str | None,
    error: str | None,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> tuple[bool, str]:
    session = get_patient_session(connection, patient_id)
    if not session or session.get("oauth_state_nonce") != state:
        return False, "state_invalid"

    if error or not code:
        connection.execute(
            f"UPDATE patient_sessions SET {provider}_auth_status = 'error', updated_at = ? WHERE patient_profile_id = ?",
            [to_iso(utc_now()), patient_id],
        )
        connection.commit()
        return False, "access_denied"

    encrypted = encrypt_token(f"{provider}:{code}:{uuid.uuid4().hex}")
    calendar_id = "primary" if provider == "google" else "default-calendar"
    connection.execute(
        f"""
        UPDATE patient_sessions
        SET {provider}_refresh_token = ?,
            {provider}_access_token_expires_at = ?,
            {provider}_calendar_id = ?,
            {provider}_auth_status = 'authorized',
            oauth_state_nonce = NULL,
            updated_at = ?
        WHERE patient_profile_id = ?
        """,
        [encrypted, to_iso(utc_now() + timedelta(days=30)), calendar_id, to_iso(utc_now()), patient_id],
    )
    connection.commit()
    return True, "authorized"


def disconnect_provider(connection: sqlite3.Connection, provider: str, patient_id: int = DEFAULT_PATIENT_ID) -> None:
    connection.execute(
        f"""
        UPDATE patient_sessions
        SET {provider}_refresh_token = NULL,
            {provider}_access_token_expires_at = NULL,
            {provider}_calendar_id = NULL,
            {provider}_auth_status = 'revoked',
            updated_at = ?
        WHERE patient_profile_id = ?
        """,
        [to_iso(utc_now()), patient_id],
    )
    connection.execute(
        "UPDATE appointments SET sync_status = 'revoked' WHERE sync_status = 'pending'"
    )
    connection.commit()


def enqueue_sync_actions(connection: sqlite3.Connection, appointment: dict[str, Any]) -> None:
    integrations = get_integration_state(connection)
    for provider, details in integrations.items():
        if not details["connected"]:
            continue
        idempotency_key = f"create-{provider}-{appointment['id']}-{appointment['version']}"
        exists = connection.execute(
            """
            SELECT COUNT(*) AS count FROM calendar_sync_queue
            WHERE appointment_id = ? AND action = 'create' AND calendar_type = ? AND idempotency_key = ?
            """,
            [appointment["id"], provider, idempotency_key],
        ).fetchone()["count"]
        if exists:
            continue
        connection.execute(
            """
            INSERT INTO calendar_sync_queue(appointment_id, action, calendar_type, idempotency_key, payload_json)
            VALUES (?, 'create', ?, ?, ?)
            """,
            [appointment["id"], provider, idempotency_key, json.dumps({"source": "booking"})],
        )
    if integrations["google"]["connected"] or integrations["outlook"]["connected"]:
        connection.execute(
            "UPDATE appointments SET sync_status = 'pending' WHERE id = ?",
            [appointment["id"]],
        )
    connection.commit()


def process_calendar_sync_queue(connection: sqlite3.Connection, reference_time: datetime | None = None) -> dict[str, Any]:
    now = reference_time or utc_now()
    rows = [
        dict(row)
        for row in connection.execute(
            """
            SELECT * FROM calendar_sync_queue
            WHERE status = 'pending' AND scheduled_retry_at <= ?
            ORDER BY created_at ASC
            """,
            [to_iso(now)],
        ).fetchall()
    ]
    processed = 0
    failed = 0
    for queue_item in rows:
        appointment = get_appointment_details(connection, queue_item["appointment_id"])
        if appointment is None:
            continue
        provider = queue_item["calendar_type"]
        external_event_id = f"{provider}-{appointment['id']}"
        try:
            with connection:
                connection.execute(
                    "UPDATE calendar_sync_queue SET status = 'processing', updated_at = ? WHERE id = ?",
                    [to_iso(now), queue_item["id"]],
                )
                existing_event = connection.execute(
                    """
                    SELECT id FROM provider_external_events
                    WHERE appointment_id = ? AND calendar_type = ?
                    """,
                    [appointment["id"], provider],
                ).fetchone()
                if existing_event:
                    connection.execute(
                        """
                        UPDATE provider_external_events
                        SET external_event_id = ?,
                            starts_at = ?,
                            ends_at = ?,
                            status = 'active',
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            external_event_id,
                            to_iso(_appointment_local_start(appointment)),
                            to_iso(_appointment_local_end(appointment)),
                            to_iso(now),
                            existing_event["id"],
                        ),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO provider_external_events(
                            appointment_id,
                            provider_id,
                            calendar_type,
                            external_event_id,
                            starts_at,
                            ends_at,
                            status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, 'active')
                        """,
                        (
                            appointment["id"],
                            appointment["provider_id"],
                            provider,
                            external_event_id,
                            to_iso(_appointment_local_start(appointment)),
                            to_iso(_appointment_local_end(appointment)),
                        ),
                    )
                event_column = "google_event_id" if provider == "google" else "outlook_event_id"
                connection.execute(
                    f"UPDATE appointments SET {event_column} = ?, last_synced_at = ?, sync_status = 'synced' WHERE id = ?",
                    [external_event_id, to_iso(now), appointment["id"]],
                )
                connection.execute(
                    "UPDATE calendar_sync_queue SET status = 'synced', updated_at = ? WHERE id = ?",
                    [to_iso(now), queue_item["id"]],
                )
                connection.execute(
                    """
                    INSERT INTO calendar_sync_audit(
                        appointment_id,
                        calendar_type,
                        external_event_id,
                        action,
                        result,
                        details_json
                    )
                    VALUES (?, ?, ?, ?, 'success', ?)
                    """,
                    (
                        appointment["id"],
                        provider,
                        external_event_id,
                        queue_item["action"],
                        json.dumps({"sloSeconds": 10}),
                    ),
                )
            processed += 1
        except Exception as exc:
            new_retry_count = queue_item["retry_count"] + 1
            if new_retry_count >= SYNC_MAX_RETRIES:
                connection.execute(
                    "UPDATE calendar_sync_queue SET status = 'failed', retry_count = ?, last_error = ?, updated_at = ? WHERE id = ?",
                    [new_retry_count, str(exc)[:512], to_iso(now), queue_item["id"]],
                )
                connection.execute(
                    """
                    INSERT INTO calendar_sync_audit(
                        appointment_id, calendar_type, external_event_id, action, result, details_json
                    )
                    VALUES (?, ?, ?, ?, 'failure', ?)
                    """,
                    (
                        appointment["id"],
                        provider,
                        external_event_id,
                        queue_item["action"],
                        json.dumps({"error": str(exc)[:512], "retries": new_retry_count}),
                    ),
                )
            else:
                backoff = SYNC_BACKOFF_SECONDS[min(new_retry_count - 1, len(SYNC_BACKOFF_SECONDS) - 1)]
                next_retry_at = now + timedelta(seconds=backoff)
                connection.execute(
                    """
                    UPDATE calendar_sync_queue
                    SET status = 'pending',
                        retry_count = ?,
                        last_error = ?,
                        scheduled_retry_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    [new_retry_count, str(exc)[:512], to_iso(next_retry_at), to_iso(now), queue_item["id"]],
                )
            failed += 1
    connection.commit()
    return {"processed": processed, "failed": failed}


def run_pull_reconciliation(connection: sqlite3.Connection, reference_time: datetime | None = None) -> dict[str, Any]:
    now = reference_time or utc_now()
    rows = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM provider_external_events WHERE status IN ('deleted', 'rescheduled')"
        ).fetchall()
    ]
    handled = 0
    for row in rows:
        if row["status"] == "deleted":
            connection.execute(
                "UPDATE appointments SET status = 'cancelled', checkout_status = 'cancelled', last_synced_at = ? WHERE id = ?",
                [to_iso(now), row["appointment_id"]],
            )
        else:
            connection.execute(
                """
                INSERT INTO manual_review_queue(appointment_id, review_type, details_json)
                VALUES (?, 'external_reschedule', ?)
                """,
                [row["appointment_id"], json.dumps({"calendarType": row["calendar_type"]})],
            )
            connection.execute(
                "UPDATE appointments SET sync_status = 'manual_review', last_synced_at = ? WHERE id = ?",
                [to_iso(now), row["appointment_id"]],
            )
        handled += 1
    connection.commit()
    return {"handled": handled}


# ---------------------------------------------------------------------------
# EP-006: Patient Dashboard service functions (US-053 through US-058)
# ---------------------------------------------------------------------------

_RESCHEDULE_CUTOFF = timedelta(hours=24)
_CANCEL_CUTOFF = timedelta(hours=2)


def get_patient_upcoming_appointments(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """US-054 BE-1/BE-2 — Future booked appointments with action eligibility flags."""
    today = date.today().isoformat()
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

    now = utc_now()
    items = []
    for row in rows:
        appt = dict(row)
        try:
            appt_start = _appointment_local_start(appt)
            delta = appt_start - now
            appt["can_reschedule"] = delta >= _RESCHEDULE_CUTOFF
            appt["can_cancel"] = delta >= _CANCEL_CUTOFF
        except Exception:
            appt["can_reschedule"] = False
            appt["can_cancel"] = False
        items.append(appt)

    return {"items": items, "total": len(items)}


def get_patient_appointment_history(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """US-055 BE-1/BE-2 — Past booked appointments with release policy filter."""
    today = date.today().isoformat()
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
        # Release policy: notes only available when confirmation was delivered and
        # a signed confirmation PDF was generated (indicated by attachment_path).
        delivery = connection.execute(
            "SELECT attachment_path FROM confirmation_deliveries WHERE appointment_id = ? AND status = 'sent' LIMIT 1",
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


def get_patient_health_profile(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """US-056 BE-1/BE-2 — Structured patient health profile with version metadata."""
    rows = connection.execute(
        """
        SELECT element_type, display_value, status, source_document_id, updated_at
        FROM clinical_profile_elements
        WHERE patient_id = ?
        ORDER BY element_type, updated_at DESC
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
            "label": row["display_value"],
            "status": row["status"],
            "last_updated": row["updated_at"],
        }
        etype = (row["element_type"] or "").lower()
        if etype == "medication":
            medications.append(entry)
        elif etype == "allergy":
            allergies.append(entry)
        elif etype in ("diagnosis", "icd10"):
            diagnoses.append(entry)
        elif etype in ("chronic_condition", "chronic"):
            chronic_conditions.append(entry)
        elif etype == "alert":
            alerts.append(entry)

    last_updated = to_iso(utc_now())
    if rows:
        timestamps = [r["updated_at"] for r in rows if r["updated_at"]]
        if timestamps:
            last_updated = max(timestamps)

    version_row = connection.execute(
        "SELECT MAX(rowid) AS v FROM clinical_profile_elements WHERE patient_id = ?",
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


def get_patient_documents(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """US-057 BE-3 — Patient document list with processing status."""
    rows = connection.execute(
        """
        SELECT d.id, d.file_name, d.file_type, d.upload_status,
               d.created_at, cdp.status AS processing_status
        FROM clinical_documents d
        LEFT JOIN clinical_document_processing cdp ON cdp.document_id = d.id
        WHERE d.patient_id = ?
        ORDER BY d.created_at DESC
        """,
        [patient_id],
    ).fetchall()

    items = []
    for row in rows:
        items.append({
            "id": row["id"],
            "file_name": row["file_name"],
            "file_type": row["file_type"],
            "upload_status": row["upload_status"],
            "processing_status": row["processing_status"] or "pending",
            "uploaded_at": row["created_at"],
        })

    return {"items": items, "total": len(items)}


def get_notification_preferences(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """US-058 BE-1 — Retrieve patient notification channel preferences."""
    profile = get_patient_profile(connection, patient_id)
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
        "in_app": True,  # Always on; controlled by client opt-in
        "do_not_disturb": bool(profile.get("do_not_disturb", 0)),
    }


def set_notification_preferences(
    connection: sqlite3.Connection,
    patient_id: int,
    prefs: dict[str, Any],
) -> dict[str, Any]:
    """US-058 BE-1 — Persist notification channel preferences for opt-out enforcement."""
    channels: list[str] = []
    if prefs.get("email", True):
        channels.append("email")
    if prefs.get("sms", True):
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
    """US-058 BE-2 — Check if a given notification channel is enabled for this patient."""
    prefs = get_notification_preferences(connection, patient_id)
    if prefs.get("do_not_disturb"):
        return False
    return bool(prefs.get(channel, False))


def get_patient_dashboard(
    connection: sqlite3.Connection,
    patient_id: int = DEFAULT_PATIENT_ID,
) -> dict[str, Any]:
    """US-053 BE-1/BE-2 — Aggregate dashboard payload with partial-update metadata."""
    upcoming = get_patient_upcoming_appointments(connection, patient_id)
    profile = get_patient_profile(connection, patient_id)
    prefs = get_notification_preferences(connection, patient_id)
    documents = get_patient_documents(connection, patient_id)

    recent_activity: list[dict[str, Any]] = []
    history = connection.execute(
        """
        SELECT a.appointment_date, a.start_time, p.name AS provider_name, a.status
        FROM appointments a
        JOIN providers p ON p.id = a.provider_id
        WHERE a.appointment_date < ?
          AND a.status = 'booked'
        ORDER BY a.appointment_date DESC, a.start_time DESC
        LIMIT 5
        """,
        [date.today().isoformat()],
    ).fetchall()
    for row in history:
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
        "last_updated": to_iso(utc_now()),
    }


def get_admin_operational_metrics(
    connection: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
    provider_id: int | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """US-060 BE-1/BE-2/BE-3 — Admin operational KPI metrics with filter support."""
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

    total_row = connection.execute(
        f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql}",
        params,
    ).fetchone()
    total = int(total_row["cnt"] or 0)

    booked_row = connection.execute(
        f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql} {'AND' if where else 'WHERE'} a.status = 'booked'",
        params,
    ).fetchone()
    booked = int(booked_row["cnt"] or 0)

    cancelled_row = connection.execute(
        f"SELECT COUNT(*) AS cnt FROM appointments a {where_sql} {'AND' if where else 'WHERE'} a.status = 'cancelled'",
        params,
    ).fetchone()
    cancelled = int(cancelled_row["cnt"] or 0)

    utilization_rate = round(booked / total * 100, 1) if total > 0 else 0.0
    no_show_rate = round(cancelled / total * 100, 1) if total > 0 else 0.0

    wait_row = connection.execute(
        f"""
        SELECT AVG(duration_minutes) AS avg_wait
        FROM appointments a
        {where_sql}
        {'AND' if where else 'WHERE'} a.status = 'booked'
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
        "last_updated": to_iso(utc_now()),
    }