"""EP-003 Clinical Intelligence Platform.

Covers TASK-019 through TASK-024:
- Document upload and processing pipeline (US-020)
- Structured data extraction from PDF/DOCX (US-021)
- Patient data aggregation into unified profile (US-019)
- Medication conflict detection (US-024)
- Document source traceability (US-023)
- 360-degree patient profile API (US-022)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_MIME_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"pdf", "docx"})
MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB

_SIGNED_URL_SECRET: str = "propellq-dev-secret-not-for-prod"
_SIGNED_URL_TTL_SECONDS: int = 3600

# ---------------------------------------------------------------------------
# Known drug-interaction rules (rule_engine_v1)
# Each tuple: (med_a_normalized, med_b_normalized, severity, impact_text)
# ---------------------------------------------------------------------------
_DRUG_INTERACTION_RULES: list[tuple[str, str, str, str]] = [
    ("warfarin", "aspirin", "high", "Increased bleeding risk when combined."),
    ("warfarin", "ibuprofen", "high", "NSAIDs potentiate anticoagulant effect; major bleed risk."),
    ("warfarin", "naproxen", "high", "NSAIDs potentiate anticoagulant effect; major bleed risk."),
    ("warfarin", "clopidogrel", "high", "Dual antiplatelet/anticoagulant combination; elevated hemorrhage risk."),
    ("metformin", "alcohol", "medium", "Risk of lactic acidosis with heavy alcohol use."),
    ("lisinopril", "potassium", "medium", "Hyperkalemia risk; monitor electrolytes."),
    ("simvastatin", "amiodarone", "high", "Myopathy/rhabdomyolysis risk; dose-limiting interaction."),
    ("simvastatin", "clarithromycin", "high", "CYP3A4 inhibition increases statin exposure; myopathy risk."),
    ("ssri", "tramadol", "high", "Serotonin syndrome risk."),
    ("fluoxetine", "tramadol", "high", "Serotonin syndrome risk."),
    ("sertraline", "tramadol", "high", "Serotonin syndrome risk."),
    ("methotrexate", "nsaid", "high", "Reduced renal clearance of methotrexate; toxicity risk."),
    ("methotrexate", "ibuprofen", "high", "Reduced renal clearance of methotrexate; toxicity risk."),
    ("digoxin", "amiodarone", "high", "Amiodarone elevates digoxin levels; toxicity risk."),
    ("clopidogrel", "omeprazole", "medium", "CYP2C19 inhibition reduces clopidogrel activation."),
    ("lithium", "ibuprofen", "high", "NSAIDs reduce lithium clearance; toxicity risk."),
    ("lithium", "naproxen", "high", "NSAIDs reduce lithium clearance; toxicity risk."),
    ("cipro", "antacid", "low", "Chelation reduces ciprofloxacin absorption; separate doses."),
    ("ciprofloxacin", "antacid", "low", "Chelation reduces ciprofloxacin absorption; separate doses."),
]

# Therapeutic equivalents whose co-prescribing flags duplicate therapy
_DUPLICATE_THERAPY_GROUPS: list[tuple[str, list[str]]] = [
    ("statin", ["simvastatin", "atorvastatin", "rosuvastatin", "lovastatin", "pravastatin"]),
    ("ssri", ["fluoxetine", "sertraline", "escitalopram", "paroxetine", "citalopram"]),
    ("nsaid", ["ibuprofen", "naproxen", "diclofenac", "celecoxib", "aspirin"]),
    ("ace_inhibitor", ["lisinopril", "enalapril", "ramipril", "benazepril", "captopril"]),
    ("proton_pump_inhibitor", ["omeprazole", "pantoprazole", "lansoprazole", "esomeprazole"]),
    ("anticoagulant", ["warfarin", "apixaban", "rivaroxaban", "dabigatran"]),
    ("beta_blocker", ["metoprolol", "atenolol", "carvedilol", "propranolol", "bisoprolol"]),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_medication(name: str) -> str:
    """Lower-case, strip trailing dosage/strength tokens."""
    name = name.lower().strip()
    name = re.sub(r"\s*\d+\s*(mg|mcg|ml|g|iu|%|units?)\b.*", "", name).strip()
    return name


def _validate_upload(
    file_name: str,
    content_type: str,
    file_size: int,
    file_data: bytes,
) -> list[str]:
    errors: list[str] = []
    ext = Path(file_name).suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        errors.append(
            f"Unsupported file extension '.{ext}'. Accepted types: PDF, DOCX."
        )
    detected_type = ALLOWED_MIME_TYPES.get(content_type.split(";")[0].strip())
    if detected_type is None:
        errors.append(
            f"Unsupported content type '{content_type}'. Accepted: application/pdf, "
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document."
        )
    if file_size > MAX_FILE_SIZE_BYTES:
        errors.append(
            f"File size {file_size} bytes exceeds the 20 MB limit."
        )
    if not file_data:
        errors.append("File content is empty.")
    # Minimal magic-byte check for PDF
    if ext == "pdf" and file_data and not file_data[:4] == b"%PDF":
        errors.append("File does not appear to be a valid PDF.")
    return errors


# ---------------------------------------------------------------------------
# TASK-020 BE-1 / BE-2 / BE-3: Upload, queue, and status tracking
# ---------------------------------------------------------------------------


def upload_document(
    connection: sqlite3.Connection,
    patient_id: int,
    file_name: str,
    content_type: str,
    file_data: bytes,
    storage_base_path: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    """Validate and store an uploaded document, enqueue processing.

    Returns (http_status_code, response_body).
    """
    file_size = len(file_data)
    errors = _validate_upload(file_name, content_type, file_size, file_data)
    if errors:
        return 400, {
            "code": "VALIDATION_ERROR",
            "message": errors[0],
            "details": errors,
        }

    ext = Path(file_name).suffix.lstrip(".").lower()
    doc_id_str = str(uuid.uuid4())
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(file_name).name)
    storage_path = f"documents/{patient_id}/{doc_id_str}/{safe_name}"

    if storage_base_path:
        full_path = storage_base_path / storage_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(file_data)

    with connection:
        cursor = connection.execute(
            """
            INSERT INTO clinical_documents
                (patient_id, file_name, file_type, storage_path, file_size_bytes, upload_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, file_name, ext, storage_path, file_size, _utc_now_iso()),
        )
        document_id = cursor.lastrowid
        connection.execute(
            """
            INSERT INTO clinical_document_processing (document_id, status, created_at)
            VALUES (?, 'uploaded', ?)
            """,
            (document_id, _utc_now_iso()),
        )

    return 201, {
        "documentId": document_id,
        "storagePath": storage_path,
        "status": "uploaded",
        "message": "Document uploaded successfully. Processing queued.",
    }


def get_document_status(
    connection: sqlite3.Connection,
    document_id: int,
    patient_id: int,
) -> tuple[int, dict[str, Any]]:
    """Return processing status for a document. Enforces patient scoping."""
    row = connection.execute(
        """
        SELECT d.id, d.file_name, d.file_type, d.upload_timestamp,
               p.status, p.review_required, p.failure_reason,
               p.started_at, p.completed_at
        FROM clinical_documents d
        JOIN clinical_document_processing p ON p.document_id = d.id
        WHERE d.id = ? AND d.patient_id = ?
        """,
        (document_id, patient_id),
    ).fetchone()

    if row is None:
        return 404, {"code": "NOT_FOUND", "message": "Document not found."}

    return 200, {
        "documentId": row["id"],
        "fileName": row["file_name"],
        "fileType": row["file_type"],
        "uploadedAt": row["upload_timestamp"],
        "processingStatus": row["status"],
        "reviewRequired": bool(row["review_required"]),
        "failureReason": row["failure_reason"],
        "startedAt": row["started_at"],
        "completedAt": row["completed_at"],
    }


# ---------------------------------------------------------------------------
# TASK-021: Structured data extraction
# ---------------------------------------------------------------------------

_MEDICATION_PATTERN = re.compile(
    r"\b(aspirin|ibuprofen|metformin|lisinopril|atorvastatin|simvastatin|rosuvastatin|"
    r"warfarin|clopidogrel|amlodipine|metoprolol|omeprazole|pantoprazole|lansoprazole|"
    r"amoxicillin|azithromycin|ciprofloxacin|clarithromycin|fluoxetine|sertraline|"
    r"escitalopram|paroxetine|citalopram|tramadol|naproxen|diclofenac|celecoxib|"
    r"amiodarone|digoxin|lithium|methotrexate|prednisone|prednisolone|hydrochlorothiazide|"
    r"furosemide|spironolactone|allopurinol|colchicine|levothyroxine|insulin|glipizide|"
    r"gabapentin|pregabalin|duloxetine|venlafaxine|quetiapine|risperidone|apixaban|"
    r"rivaroxaban|dabigatran|enoxaparin|benazepril|ramipril|enalapril|captopril|"
    r"losartan|valsartan|candesartan|atenolol|carvedilol|bisoprolol|propranolol)"
    r"(?:\s+\d+\s*(?:mg|mcg|ml|g|iu|units?|%))?",
    re.IGNORECASE,
)

_ALLERGY_PATTERN = re.compile(
    r"(?:allerg(?:ic|y|ies)\s+to|adverse\s+reaction\s+to|intolerant\s+to)\s+"
    r"([a-zA-Z][a-zA-Z0-9\s,()/-]{2,60}?)(?:[.\n;]|$)",
    re.IGNORECASE,
)

_DIAGNOSIS_PATTERN = re.compile(
    r"\b(hypertension|diabetes(?:\s+mellitus)?(?:\s+type\s+[12])?|heart\s+failure|"
    r"chronic\s+kidney\s+disease|asthma|copd|depression|anxiety(?:\s+disorder)?|"
    r"hypothyroidism|hyperthyroidism|atrial\s+fibrillation|coronary\s+artery\s+disease|"
    r"osteoporosis|osteoarthritis|rheumatoid\s+arthritis|gerd|obesity|dyslipidemia|"
    r"hyperlipidemia|hypercholesterolemia|anemia|migraine|epilepsy|parkinson|alzheimer|"
    r"dementia|stroke|tia|peripheral\s+artery\s+disease|sleep\s+apnea|"
    r"type\s+[12]\s+diabetes|chronic\s+pain|fibromyalgia|lupus|multiple\s+sclerosis)\b",
    re.IGNORECASE,
)

_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)

_ELEMENT_TYPE_TO_TAB: dict[str, str] = {
    "medication": "medications",
    "allergy": "allergies",
    "diagnosis": "diagnoses",
    "date": "dates",
    "other": "other",
    "demographics": "other",
    "intake_field": "other",
}


def _extract_entities_from_text(
    text: str,
    document_id: int,
    patient_id: int,
) -> list[dict[str, Any]]:
    """Rule-based extraction returning a list of entity dicts."""
    entities: list[dict[str, Any]] = []
    now = _utc_now_iso()
    seen: set[tuple[str, str]] = set()

    def add(entity_type: str, raw_value: str, confidence: float, source_text: str) -> None:
        key = (entity_type, raw_value.lower().strip())
        if key in seen:
            return
        seen.add(key)
        entities.append(
            {
                "document_id": document_id,
                "patient_id": patient_id,
                "entity_type": entity_type,
                "entity_value": raw_value.strip(),
                "normalized_value": _normalize_medication(raw_value) if entity_type == "medication" else raw_value.lower().strip(),
                "confidence_score": confidence,
                "source_text": source_text[:200],
                "extraction_model": "rule_engine_v1",
                "extracted_at": now,
            }
        )

    for match in _MEDICATION_PATTERN.finditer(text):
        add("medication", match.group(0), 0.85, match.group(0))

    for match in _ALLERGY_PATTERN.finditer(text):
        add("allergy", match.group(1), 0.80, match.group(0))

    for match in _DIAGNOSIS_PATTERN.finditer(text):
        add("diagnosis", match.group(0), 0.78, match.group(0))

    for match in _DATE_PATTERN.finditer(text):
        add("date", match.group(0), 0.95, match.group(0))

    return entities


def process_document(
    connection: sqlite3.Connection,
    document_id: int,
    document_text: str,
) -> dict[str, Any]:
    """Run extraction pipeline for a document and store results.

    Marks document processing status accordingly.
    """
    now = _utc_now_iso()
    with connection:
        connection.execute(
            "UPDATE clinical_document_processing SET status='processing', started_at=? WHERE document_id=?",
            (now, document_id),
        )

    try:
        row = connection.execute(
            "SELECT patient_id FROM clinical_documents WHERE id=?",
            (document_id,),
        ).fetchone()

        if row is None:
            raise ValueError(f"Document {document_id} not found.")

        patient_id = row["patient_id"]
        entities = _extract_entities_from_text(document_text, document_id, patient_id)

        with connection:
            for entity in entities:
                connection.execute(
                    """
                    INSERT INTO clinical_extracted_entities
                        (document_id, patient_id, entity_type, entity_value, normalized_value,
                         confidence_score, source_text, extraction_model, extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity["document_id"],
                        entity["patient_id"],
                        entity["entity_type"],
                        entity["entity_value"],
                        entity["normalized_value"],
                        entity["confidence_score"],
                        entity["source_text"],
                        entity["extraction_model"],
                        entity["extracted_at"],
                    ),
                )
            connection.execute(
                """
                UPDATE clinical_document_processing
                SET status='complete', completed_at=?
                WHERE document_id=?
                """,
                (_utc_now_iso(), document_id),
            )

        return {"documentId": document_id, "entitiesExtracted": len(entities), "status": "complete"}

    except Exception as exc:  # noqa: BLE001
        logger.exception("Extraction failed for document %d: %s", document_id, exc)
        reason = str(exc)[:500]
        with connection:
            connection.execute(
                """
                UPDATE clinical_document_processing
                SET status='failed', review_required=1, failure_reason=?, completed_at=?
                WHERE document_id=?
                """,
                (reason, _utc_now_iso(), document_id),
            )
        return {"documentId": document_id, "entitiesExtracted": 0, "status": "failed", "failureReason": reason}


# ---------------------------------------------------------------------------
# TASK-019: Patient Data Aggregation into Unified Profile
# ---------------------------------------------------------------------------


def aggregate_patient_profile(
    connection: sqlite3.Connection,
    patient_id: int,
    intake_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge intake data and extracted entities into clinical_profile_elements.

    Intake data takes priority over document-extracted data (deduplication).
    Returns summary of aggregated element counts.
    """
    now = _utc_now_iso()

    with connection:
        connection.execute(
            "UPDATE clinical_profile_elements SET is_active=0 WHERE patient_id=?",
            (patient_id,),
        )

    upserted = 0

    if intake_data:
        _INTAKE_KEY_TO_TYPE: dict[str, str] = {
            "medications": "medication",
            "allergies": "allergy",
            "diagnoses": "diagnosis",
        }
        for field_key in ("medications", "allergies", "diagnoses"):
            items = intake_data.get(field_key, [])
            if isinstance(items, str):
                items = [i.strip() for i in items.split(",") if i.strip()]
            element_type = _INTAKE_KEY_TO_TYPE[field_key]
            for item in items:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO clinical_profile_elements
                            (patient_id, element_type, element_value, normalized_value,
                             source_type, source_id, confidence_score, extracted_at, aggregated_at, is_active)
                        VALUES (?, ?, ?, ?, 'intake', ?, 1.0, ?, ?, 1)
                        """,
                        (
                            patient_id,
                            element_type,
                            item,
                            item.lower().strip(),
                            patient_id,
                            now,
                            now,
                        ),
                    )
                    upserted += 1

    entity_rows = connection.execute(
        """
        SELECT e.entity_type, e.entity_value, e.normalized_value,
               e.document_id, e.confidence_score, e.extracted_at
        FROM clinical_extracted_entities e
        WHERE e.patient_id = ?
        ORDER BY e.confidence_score DESC
        """,
        (patient_id,),
    ).fetchall()

    intake_norm_values: set[tuple[str, str]] = set()
    existing = connection.execute(
        """
        SELECT element_type, normalized_value
        FROM clinical_profile_elements
        WHERE patient_id=? AND source_type='intake' AND is_active=1
        """,
        (patient_id,),
    ).fetchall()
    for row in existing:
        intake_norm_values.add((row["element_type"], (row["normalized_value"] or "").lower().strip()))

    for row in entity_rows:
        key = (row["entity_type"], (row["normalized_value"] or "").lower().strip())
        if key in intake_norm_values:
            continue

        with connection:
            connection.execute(
                """
                INSERT INTO clinical_profile_elements
                    (patient_id, element_type, element_value, normalized_value,
                     source_type, source_id, confidence_score, extracted_at, aggregated_at, is_active)
                VALUES (?, ?, ?, ?, 'document', ?, ?, ?, ?, 1)
                """,
                (
                    patient_id,
                    row["entity_type"],
                    row["entity_value"],
                    row["normalized_value"],
                    row["document_id"],
                    row["confidence_score"],
                    row["extracted_at"],
                    now,
                ),
            )
            upserted += 1
            intake_norm_values.add(key)

    return {
        "patientId": patient_id,
        "elementsAggregated": upserted,
        "aggregatedAt": now,
    }


# ---------------------------------------------------------------------------
# TASK-022 BE-1: 360° profile API
# ---------------------------------------------------------------------------


def get_360_profile(
    connection: sqlite3.Connection,
    patient_id: int,
) -> tuple[int, dict[str, Any]]:
    """Aggregate and return the 360-degree patient profile."""
    patient = connection.execute(
        "SELECT * FROM patient_profiles WHERE id=?",
        (patient_id,),
    ).fetchone()

    if patient is None:
        return 404, {"code": "NOT_FOUND", "message": "Patient not found."}

    tabs: dict[str, list[dict[str, Any]]] = {
        "medications": [],
        "allergies": [],
        "diagnoses": [],
        "dates": [],
        "other": [],
    }

    elements = connection.execute(
        """
        SELECT id, element_type, element_value, normalized_value,
               source_type, source_id, confidence_score, extracted_at, aggregated_at
        FROM clinical_profile_elements
        WHERE patient_id=? AND is_active=1
        ORDER BY element_type, aggregated_at DESC
        """,
        (patient_id,),
    ).fetchall()

    for el in elements:
        entry = {
            "id": el["id"],
            "value": el["element_value"],
            "normalizedValue": el["normalized_value"],
            "sourceType": el["source_type"],
            "sourceId": el["source_id"],
            "confidenceScore": el["confidence_score"],
            "extractedAt": el["extracted_at"],
            "aggregatedAt": el["aggregated_at"],
        }
        tab = _ELEMENT_TYPE_TO_TAB.get(el["element_type"], "other")
        tabs.setdefault(tab, []).append(entry)

    documents = connection.execute(
        """
        SELECT d.id, d.file_name, d.file_type, d.upload_timestamp,
               p.status AS processing_status
        FROM clinical_documents d
        JOIN clinical_document_processing p ON p.document_id = d.id
        WHERE d.patient_id = ?
        ORDER BY d.upload_timestamp DESC
        """,
        (patient_id,),
    ).fetchall()

    doc_list = [
        {
            "id": d["id"],
            "fileName": d["file_name"],
            "fileType": d["file_type"],
            "uploadedAt": d["upload_timestamp"],
            "processingStatus": d["processing_status"],
        }
        for d in documents
    ]

    overview = {
        "patientId": patient["id"],
        "firstName": patient["first_name"],
        "lastName": patient["last_name"],
        "email": patient["email"],
        "phone": patient["phone"],
        "preferredTimezone": patient["preferred_timezone"],
        "documents": doc_list,
    }

    return 200, {
        "overview": overview,
        "medications": tabs.get("medications", []),
        "allergies": tabs.get("allergies", []),
        "diagnoses": tabs.get("diagnoses", []),
    }


# ---------------------------------------------------------------------------
# TASK-023 BE-1 / BE-2: Source reference API and signed document access
# ---------------------------------------------------------------------------


def get_source_metadata(
    connection: sqlite3.Connection,
    element_id: int,
    patient_id: int,
) -> tuple[int, dict[str, Any]]:
    """Return source metadata for a profile element (AC-1, AC-2)."""
    row = connection.execute(
        """
        SELECT pe.id, pe.element_type, pe.element_value, pe.source_type,
               pe.source_id, pe.confidence_score, pe.extracted_at,
               d.file_name, d.file_type, d.storage_path
        FROM clinical_profile_elements pe
        LEFT JOIN clinical_documents d
            ON pe.source_type = 'document' AND d.id = pe.source_id
        WHERE pe.id = ? AND pe.patient_id = ?
        """,
        (element_id, patient_id),
    ).fetchone()

    if row is None:
        return 404, {"code": "NOT_FOUND", "message": "Profile element not found."}

    result: dict[str, Any] = {
        "elementId": row["id"],
        "elementType": row["element_type"],
        "elementValue": row["element_value"],
        "sourceType": row["source_type"],
        "sourceId": row["source_id"],
        "confidenceScore": row["confidence_score"],
        "extractedAt": row["extracted_at"],
    }

    if row["source_type"] == "document" and row["file_name"]:
        result["documentName"] = row["file_name"]
        result["documentType"] = row["file_type"]

    return 200, result


def generate_signed_document_url(
    connection: sqlite3.Connection,
    document_id: int,
    patient_id: int,
) -> tuple[int, dict[str, Any]]:
    """Generate a time-limited signed URL for secure document preview (AC-3, SEC-1)."""
    row = connection.execute(
        "SELECT id, file_name, storage_path FROM clinical_documents WHERE id=? AND patient_id=?",
        (document_id, patient_id),
    ).fetchone()

    if row is None:
        return 404, {"code": "NOT_FOUND", "message": "Document not found."}

    expires_at = int(time.time()) + _SIGNED_URL_TTL_SECONDS
    payload = f"{document_id}:{patient_id}:{expires_at}"
    signature = hmac.new(
        _SIGNED_URL_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    signed_url = (
        f"/api/clinical/documents/{document_id}/preview"
        f"?patient={patient_id}&expires={expires_at}&sig={signature}"
    )

    return 200, {
        "documentId": document_id,
        "fileName": row["file_name"],
        "signedUrl": signed_url,
        "expiresAt": expires_at,
        "ttlSeconds": _SIGNED_URL_TTL_SECONDS,
    }


def validate_signed_url(
    document_id: int,
    patient_id: int,
    expires_at: int,
    signature: str,
) -> bool:
    """Verify a signed URL signature and expiry (SEC-1)."""
    if int(time.time()) > expires_at:
        return False
    payload = f"{document_id}:{patient_id}:{expires_at}"
    expected = hmac.new(
        _SIGNED_URL_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# TASK-024: Medication conflict detection
# ---------------------------------------------------------------------------


def detect_medication_conflicts(
    connection: sqlite3.Connection,
    patient_id: int,
) -> tuple[int, dict[str, Any]]:
    """Detect drug-drug interactions and duplicate therapies.

    Degrades gracefully on any error (BE-3): returns empty conflict list
    with a degraded-state flag rather than blocking profile access.
    """
    try:
        return _run_conflict_detection(connection, patient_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Conflict detection unavailable for patient %d: %s", patient_id, exc)
        return 200, {
            "patientId": patient_id,
            "conflicts": [],
            "degraded": True,
            "degradedReason": "Conflict detection service temporarily unavailable.",
        }


def _run_conflict_detection(
    connection: sqlite3.Connection,
    patient_id: int,
) -> tuple[int, dict[str, Any]]:
    med_elements = connection.execute(
        """
        SELECT element_value, normalized_value
        FROM clinical_profile_elements
        WHERE patient_id=? AND element_type='medication' AND is_active=1
        """,
        (patient_id,),
    ).fetchall()

    normalized_meds = [
        {
            "raw": row["element_value"],
            "normalized": _normalize_medication(row["element_value"]),
        }
        for row in med_elements
    ]

    conflicts: list[dict[str, Any]] = []
    seen_conflict_keys: set[tuple[str, str]] = set()

    # --- Drug-drug interaction detection (BE-1) ---
    for rule in _DRUG_INTERACTION_RULES:
        rule_a, rule_b, severity, impact = rule
        found_a = next((m for m in normalized_meds if rule_a in m["normalized"]), None)
        found_b = next((m for m in normalized_meds if rule_b in m["normalized"]), None)
        if found_a and found_b:
            key = tuple(sorted([found_a["normalized"], found_b["normalized"]]))
            if key not in seen_conflict_keys:
                seen_conflict_keys.add(key)
                conflicts.append(
                    {
                        "conflictType": "drug_drug_interaction",
                        "severity": severity,
                        "medicationA": found_a["raw"],
                        "medicationB": found_b["raw"],
                        "clinicalImpact": impact,
                        "source": "rule_engine_v1",
                    }
                )

    # --- Duplicate therapy detection (BE-2) ---
    for group_name, group_members in _DUPLICATE_THERAPY_GROUPS:
        found_in_group = [
            m for m in normalized_meds
            if any(member in m["normalized"] for member in group_members)
        ]
        if len(found_in_group) > 1:
            for i in range(len(found_in_group)):
                for j in range(i + 1, len(found_in_group)):
                    med_a = found_in_group[i]
                    med_b = found_in_group[j]
                    key = tuple(sorted([med_a["normalized"], med_b["normalized"]]))
                    if key not in seen_conflict_keys:
                        seen_conflict_keys.add(key)
                        conflicts.append(
                            {
                                "conflictType": "duplicate_therapy",
                                "severity": "medium",
                                "medicationA": med_a["raw"],
                                "medicationB": med_b["raw"],
                                "clinicalImpact": (
                                    f"Both medications belong to the same therapeutic class "
                                    f"({group_name.replace('_', ' ')}). Duplicate therapy increases "
                                    "adverse effect risk and cost without additional benefit."
                                ),
                                "source": "rule_engine_v1",
                            }
                        )

    # Persist newly detected conflicts (idempotent - clear unresolved and re-insert)
    now = _utc_now_iso()
    with connection:
        connection.execute(
            "DELETE FROM clinical_medication_conflicts WHERE patient_id=? AND resolved_at IS NULL",
            (patient_id,),
        )
        for conflict in conflicts:
            connection.execute(
                """
                INSERT INTO clinical_medication_conflicts
                    (patient_id, conflict_type, severity, medication_a, medication_b,
                     clinical_impact, source, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    conflict["conflictType"],
                    conflict["severity"],
                    conflict["medicationA"],
                    conflict["medicationB"],
                    conflict["clinicalImpact"],
                    conflict["source"],
                    now,
                ),
            )

    return 200, {
        "patientId": patient_id,
        "conflicts": conflicts,
        "conflictCount": len(conflicts),
        "highCount": sum(1 for c in conflicts if c["severity"] == "high"),
        "mediumCount": sum(1 for c in conflicts if c["severity"] == "medium"),
        "lowCount": sum(1 for c in conflicts if c["severity"] == "low"),
        "degraded": False,
        "detectedAt": now,
    }
