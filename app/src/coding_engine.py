"""EP-003 Coding Engine — TASK-025 through TASK-030.

Covers:
- Allergy-drug interaction check (US-025)
- ICD-10 code suggestion engine (US-026)
- CPT code suggestion engine (US-027)
- Code verification UI backend (US-028)
- Confidence score thresholds (US-029)
- Conflict resolution backend (US-030)
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default threshold values
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLD_ICD10: float = 0.70
DEFAULT_THRESHOLD_CPT: float = 0.75

# ---------------------------------------------------------------------------
# TASK-025: Allergy-drug interaction rules
# Each tuple: (allergen_pattern, drug_pattern, severity, clinical_impact)
# ---------------------------------------------------------------------------

_ALLERGY_DRUG_RULES: list[tuple[str, str, str, str]] = [
    # Beta-lactam family
    ("penicillin", "amoxicillin", "high", "Amoxicillin is a penicillin-class beta-lactam; contraindicated in penicillin allergy."),
    ("penicillin", "ampicillin", "high", "Ampicillin is a penicillin-class antibiotic; contraindicated in penicillin allergy."),
    ("penicillin", "piperacillin", "high", "Piperacillin is a penicillin; contraindicated in penicillin allergy."),
    ("penicillin", "dicloxacillin", "high", "Dicloxacillin is a penicillin; contraindicated in penicillin allergy."),
    # Cephalosporins — partial cross-reactivity with penicillin
    ("penicillin", "cephalexin", "medium", "Potential cross-reactivity between penicillin and first-generation cephalosporins (~1–2%)."),
    ("penicillin", "cefazolin", "medium", "Potential cross-reactivity between penicillin and first-generation cephalosporins."),
    ("penicillin", "ceftriaxone", "low", "Low-level cross-reactivity between penicillin and third-generation cephalosporins."),
    # Sulfonamide family
    ("sulfa", "sulfamethoxazole", "high", "Sulfamethoxazole is a sulfonamide; contraindicated in sulfa allergy."),
    ("sulfa", "trimethoprim", "medium", "TMP-SMX contains sulfonamide component; caution in sulfa allergy."),
    ("sulfa", "furosemide", "low", "Furosemide contains a sulfonamide moiety; monitor in sulfa allergy."),
    ("sulfa", "hydrochlorothiazide", "low", "HCT contains a sulfonamide moiety; monitor in sulfa allergy."),
    # NSAID cross-reactivity
    ("aspirin", "ibuprofen", "medium", "Cross-reactive NSAID; may trigger aspirin-sensitive respiratory disease."),
    ("aspirin", "naproxen", "medium", "Cross-reactive NSAID; may trigger aspirin-sensitive respiratory disease."),
    ("aspirin", "diclofenac", "medium", "Diclofenac may cross-react in aspirin-sensitive patients."),
    ("aspirin", "celecoxib", "low", "COX-2 selective agents are generally safe in aspirin allergy but monitor closely."),
    # Fluoroquinolone class
    ("ciprofloxacin", "levofloxacin", "medium", "Fluoroquinolone class cross-reactivity; use alternative if allergy documented."),
    ("ciprofloxacin", "moxifloxacin", "medium", "Fluoroquinolone class cross-reactivity; use alternative if allergy documented."),
    # Opioid cross-reactivity
    ("codeine", "morphine", "medium", "Opioid class cross-reactivity; alternative opioid class may be needed."),
    ("codeine", "oxycodone", "low", "Low cross-reactivity among opioids; individual monitoring recommended."),
    # Statins (myopathy allergy)
    ("statin", "simvastatin", "medium", "Prior statin intolerance may indicate class-effect risk."),
    ("statin", "atorvastatin", "medium", "Prior statin intolerance may indicate class-effect risk."),
    # Contrast media
    ("contrast", "iodine", "high", "Iodine allergy with contrast media exposure carries anaphylaxis risk."),
    # Latex — some cross-reactive foods/medications
    ("latex", "amoxicillin", "low", "Latex allergy rarely cross-reacts with certain medications; monitor."),
]

# ---------------------------------------------------------------------------
# TASK-026: ICD-10 code mapping rules
# Each tuple: (diagnosis_pattern, icd10_code, description, base_confidence)
# ---------------------------------------------------------------------------

_ICD10_RULES: list[tuple[str, str, str, float]] = [
    ("hypertension", "I10", "Essential (primary) hypertension", 0.92),
    ("diabetes mellitus type 1|type 1 diabetes", "E10.9", "Type 1 diabetes mellitus without complications", 0.91),
    ("diabetes mellitus type 2|type 2 diabetes|diabetes mellitus", "E11.9", "Type 2 diabetes mellitus without complications", 0.90),
    ("heart failure", "I50.9", "Heart failure, unspecified", 0.88),
    ("chronic kidney disease|ckd", "N18.9", "Chronic kidney disease, unspecified", 0.85),
    ("asthma", "J45.909", "Unspecified asthma, uncomplicated", 0.87),
    ("copd|chronic obstructive pulmonary disease", "J44.1", "Chronic obstructive pulmonary disease with acute exacerbation", 0.85),
    ("major depressive disorder|depression", "F32.9", "Major depressive disorder, single episode, unspecified", 0.83),
    ("anxiety disorder|anxiety", "F41.9", "Anxiety disorder, unspecified", 0.82),
    ("hypothyroidism", "E03.9", "Hypothyroidism, unspecified", 0.89),
    ("hyperthyroidism", "E05.90", "Hyperthyroidism, unspecified, without thyrotoxic crisis", 0.87),
    ("atrial fibrillation", "I48.91", "Unspecified atrial fibrillation", 0.90),
    ("coronary artery disease", "I25.10", "Atherosclerotic heart disease of native coronary artery without angina pectoris", 0.86),
    ("osteoporosis", "M81.0", "Age-related osteoporosis without current pathological fracture", 0.84),
    ("osteoarthritis", "M19.90", "Unspecified osteoarthritis, unspecified site", 0.82),
    ("rheumatoid arthritis", "M06.9", "Rheumatoid arthritis, unspecified", 0.85),
    ("gerd|gastroesophageal reflux|reflux", "K21.0", "Gastro-esophageal reflux disease with esophagitis", 0.84),
    ("obesity", "E66.9", "Obesity, unspecified", 0.88),
    ("dyslipidemia|hyperlipidemia|hypercholesterolemia", "E78.5", "Hyperlipidemia, unspecified", 0.87),
    ("anemia", "D64.9", "Anaemia, unspecified", 0.82),
    ("migraine", "G43.909", "Migraine, unspecified, not intractable, without status migrainosus", 0.84),
    ("epilepsy|seizure disorder", "G40.909", "Epilepsy, unspecified, not intractable, without status epilepticus", 0.83),
    ("parkinson|parkinson's disease", "G20", "Parkinson's disease", 0.88),
    ("alzheimer|dementia", "G30.9", "Alzheimer's disease, unspecified", 0.86),
    ("stroke|cerebrovascular accident|cva", "I63.9", "Cerebral infarction, unspecified", 0.85),
    ("transient ischemic attack|tia", "G45.9", "Transient cerebral ischaemic attack, unspecified", 0.84),
    ("peripheral artery disease|pad", "I73.9", "Peripheral vascular disease, unspecified", 0.82),
    ("sleep apnea|obstructive sleep apnea|osa", "G47.33", "Obstructive sleep apnea (adult)", 0.88),
    ("chronic pain", "G89.29", "Other chronic pain", 0.75),
    ("fibromyalgia", "M79.3", "Panniculitis", 0.72),
    ("lupus|systemic lupus erythematosus|sle", "M32.9", "Systemic lupus erythematosus, unspecified", 0.85),
    ("multiple sclerosis|ms", "G35", "Multiple sclerosis", 0.87),
    ("atrial flutter", "I48.3", "Typical atrial flutter", 0.88),
    ("pneumonia", "J18.9", "Pneumonia, unspecified organism", 0.82),
    ("urinary tract infection|uti", "N39.0", "Urinary tract infection, site not specified", 0.83),
]

# ---------------------------------------------------------------------------
# TASK-027: CPT code mapping rules
# Each tuple: (trigger_pattern, cpt_code, description, base_confidence)
# Triggers are medication classes or procedure keywords from clinical text.
# ---------------------------------------------------------------------------

_CPT_RULES: list[tuple[str, str, str, float]] = [
    # Evaluation & Management
    ("office visit|established patient|follow.up", "99213", "Office or other outpatient visit, established patient, moderate complexity", 0.80),
    ("new patient|initial visit|first visit", "99203", "Office or other outpatient visit, new patient, moderate complexity", 0.80),
    ("annual exam|preventive|wellness visit", "99395", "Periodic comprehensive preventive medicine evaluation, 18-39 years", 0.82),
    # Cardiac
    ("ecg|electrocardiogram|ekg", "93000", "Electrocardiogram, routine ECG with at least 12 leads; with interpretation and report", 0.88),
    ("echocardiogram|echo", "93306", "Echocardiography, transthoracic, real-time with image documentation", 0.85),
    ("stress test|exercise stress", "93015", "Cardiovascular stress test using maximal or submaximal treadmill", 0.83),
    ("cardiac catheterization|coronary angiography", "93454", "Catheter placement in coronary artery(s) for coronary angiography", 0.82),
    ("atrial fibrillation|cardioversion", "92960", "Cardioversion, elective, electrical conversion of arrhythmia; external", 0.80),
    # Respiratory
    ("pulmonary function|spirometry|pfts", "94010", "Spirometry, including graphic record, total and timed vital capacity, expiratory flow rate measurement(s)", 0.86),
    ("inhaler|nebulizer treatment|bronchodilator treatment", "94640", "Pressurized or nonpressurized inhalation treatment for acute airway obstruction", 0.78),
    # Endocrine/Metabolic
    ("hemoglobin a1c|hba1c|glycosylated hemoglobin", "83036", "Hemoglobin; glycosylated (A1C)", 0.92),
    ("glucose|blood sugar|diabetes monitoring", "82947", "Glucose; quantitative, blood (except reagent strip)", 0.88),
    ("lipid panel|cholesterol panel", "80061", "Lipid panel", 0.90),
    ("thyroid function|tsh|thyroid panel", "84443", "Thyroid stimulating hormone (TSH)", 0.89),
    # Renal
    ("renal function|creatinine|bmp|cmp|metabolic panel", "80048", "Basic metabolic panel", 0.88),
    ("urinalysis|urine culture", "81003", "Urinalysis, automated, without microscopy", 0.87),
    ("dialysis|hemodialysis", "90935", "Hemodialysis procedure with single evaluation", 0.82),
    # Coagulation
    ("warfarin|anticoagulation monitoring|inr|pt|prothrombin", "85610", "Prothrombin time", 0.91),
    ("heparin|enoxaparin|anticoagulation therapy", "85730", "Thromboplastin time, partial (PTT); plasma or whole blood", 0.83),
    # Imaging
    ("chest x.ray|cxr", "71046", "Radiologic examination, chest; 2 views", 0.87),
    ("mri brain|brain mri", "70553", "MRI brain with and without contrast", 0.83),
    ("ct scan|computed tomography", "74177", "CT abdomen and pelvis, with contrast", 0.76),
    # Injections / Procedures
    ("injection|administration|infusion", "96372", "Therapeutic, prophylactic, or diagnostic injection; subcutaneous or intramuscular", 0.77),
    ("chemotherapy|chemo infusion", "96413", "Chemotherapy administration, intravenous infusion technique; up to 1 hour", 0.82),
    ("physical therapy|physiotherapy|pt session", "97110", "Therapeutic procedure, 15 minutes; therapeutic exercises", 0.80),
    ("colonoscopy", "45378", "Colonoscopy, flexible; diagnostic, including collection of specimen(s)", 0.88),
    ("biopsy", "11102", "Tangential biopsy of skin; single lesion", 0.75),
    ("vaccination|immunization|flu shot|vaccine", "90471", "Immunization administration", 0.85),
    # Lab
    ("complete blood count|cbc", "85025", "Blood count; complete (CBC), automated (Hgb, Hct, RBC, WBC and platelet count)", 0.92),
    ("comprehensive metabolic|liver function|lft", "80053", "Comprehensive metabolic panel", 0.89),
    ("urine drug screen", "80307", "Drug test, presumptive, any number of drug classes", 0.83),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize(text: str) -> str:
    return text.lower().strip()


def _get_threshold(connection: sqlite3.Connection, code_type: str) -> float:
    """Return effective threshold for a code type, falling back to defaults."""
    row = connection.execute(
        "SELECT threshold_value FROM clinical_threshold_config WHERE code_type=?",
        (code_type,),
    ).fetchone()
    if row:
        return row["threshold_value"]
    row = connection.execute(
        "SELECT threshold_value FROM clinical_threshold_config WHERE code_type='all'",
    ).fetchone()
    if row:
        return row["threshold_value"]
    return DEFAULT_THRESHOLD_ICD10 if code_type == "icd10" else DEFAULT_THRESHOLD_CPT


def _seed_thresholds_if_empty(connection: sqlite3.Connection) -> None:
    """Seed default threshold config rows if not present."""
    existing = connection.execute(
        "SELECT COUNT(*) AS c FROM clinical_threshold_config"
    ).fetchone()["c"]
    if existing == 0:
        with connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO clinical_threshold_config (code_type, threshold_value, updated_by, updated_at)
                VALUES (?, ?, 'system', ?)
                """,
                [
                    ("icd10", DEFAULT_THRESHOLD_ICD10, _utc_now_iso()),
                    ("cpt", DEFAULT_THRESHOLD_CPT, _utc_now_iso()),
                ],
            )


# ---------------------------------------------------------------------------
# TASK-025: Allergy-drug interaction check
# ---------------------------------------------------------------------------


def detect_allergy_drug_conflicts(
    connection: sqlite3.Connection,
    patient_id: int,
) -> tuple[int, dict[str, Any]]:
    """Cross-reference patient allergies against current medications.

    Degrades gracefully on error (BE-2 / AC-3).
    """
    try:
        return _run_allergy_drug_detection(connection, patient_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Allergy-drug detection unavailable for patient %d: %s", patient_id, exc)
        return 200, {
            "patientId": patient_id,
            "conflicts": [],
            "degraded": True,
            "degradedReason": "Allergy-drug interaction service temporarily unavailable.",
        }


def _run_allergy_drug_detection(
    connection: sqlite3.Connection,
    patient_id: int,
) -> tuple[int, dict[str, Any]]:
    allergy_rows = connection.execute(
        """
        SELECT element_value, normalized_value
        FROM clinical_profile_elements
        WHERE patient_id=? AND element_type='allergy' AND is_active=1
        """,
        (patient_id,),
    ).fetchall()

    med_rows = connection.execute(
        """
        SELECT element_value, normalized_value
        FROM clinical_profile_elements
        WHERE patient_id=? AND element_type='medication' AND is_active=1
        """,
        (patient_id,),
    ).fetchall()

    allergies = [
        {"raw": r["element_value"], "normalized": _normalize(r["normalized_value"] or r["element_value"])}
        for r in allergy_rows
    ]
    medications = [
        {"raw": r["element_value"], "normalized": _normalize(r["normalized_value"] or r["element_value"])}
        for r in med_rows
    ]

    conflicts: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    now = _utc_now_iso()

    for rule in _ALLERGY_DRUG_RULES:
        allergen_pat, drug_pat, severity, impact = rule
        matched_allergy = next(
            (a for a in allergies if re.search(allergen_pat, a["normalized"])), None
        )
        matched_med = next(
            (m for m in medications if re.search(drug_pat, m["normalized"])), None
        )
        if matched_allergy and matched_med:
            key = (matched_allergy["normalized"], matched_med["normalized"])
            if key not in seen:
                seen.add(key)
                conflicts.append(
                    {
                        "allergen": matched_allergy["raw"],
                        "allergenNormalized": matched_allergy["normalized"],
                        "medication": matched_med["raw"],
                        "medicationNormalized": matched_med["normalized"],
                        "severity": severity,
                        "clinicalImpact": impact,
                        "source": "rule_engine_v1",
                    }
                )

    with connection:
        connection.execute(
            "DELETE FROM clinical_allergy_drug_conflicts WHERE patient_id=? AND resolved_at IS NULL",
            (patient_id,),
        )
        for c in conflicts:
            connection.execute(
                """
                INSERT INTO clinical_allergy_drug_conflicts
                    (patient_id, allergen, allergen_normalized, medication, medication_normalized,
                     severity, clinical_impact, source, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    c["allergen"],
                    c["allergenNormalized"],
                    c["medication"],
                    c["medicationNormalized"],
                    c["severity"],
                    c["clinicalImpact"],
                    c["source"],
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


# ---------------------------------------------------------------------------
# TASK-026 + TASK-027: ICD-10 and CPT code suggestion engine
# ---------------------------------------------------------------------------


def generate_code_suggestions(
    connection: sqlite3.Connection,
    patient_id: int,
    code_type: str = "all",
    clinical_text: str = "",
) -> tuple[int, dict[str, Any]]:
    """Generate ICD-10 and/or CPT code suggestions for a patient.

    Args:
        code_type: 'icd10', 'cpt', or 'all'.
        clinical_text: Free-text clinical note to augment profile data.
    """
    _seed_thresholds_if_empty(connection)

    suggestions: list[dict[str, Any]] = []
    now = _utc_now_iso()

    if code_type in ("icd10", "all"):
        suggestions += _generate_icd10_suggestions(connection, patient_id, clinical_text, now)

    if code_type in ("cpt", "all"):
        suggestions += _generate_cpt_suggestions(connection, patient_id, clinical_text, now)

    return 200, {
        "patientId": patient_id,
        "suggestionsGenerated": len(suggestions),
        "icd10Count": sum(1 for s in suggestions if s["codeType"] == "icd10"),
        "cptCount": sum(1 for s in suggestions if s["codeType"] == "cpt"),
        "reviewRequiredCount": sum(1 for s in suggestions if s["reviewRequired"]),
        "autoAcceptedCount": sum(1 for s in suggestions if s["autoAccepted"]),
        "suggestions": suggestions,
        "generatedAt": now,
    }


def _generate_icd10_suggestions(
    connection: sqlite3.Connection,
    patient_id: int,
    clinical_text: str,
    now: str,
) -> list[dict[str, Any]]:
    threshold = _get_threshold(connection, "icd10")

    diagnosis_rows = connection.execute(
        """
        SELECT element_value, normalized_value
        FROM clinical_profile_elements
        WHERE patient_id=? AND element_type='diagnosis' AND is_active=1
        """,
        (patient_id,),
    ).fetchall()

    search_corpus = (
        " ".join(r["element_value"] for r in diagnosis_rows) + " " + clinical_text
    ).lower()

    suggestions: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for rule in _ICD10_RULES:
        pattern, code, description, base_conf = rule
        if code in seen_codes:
            continue
        if re.search(pattern, search_corpus):
            seen_codes.add(code)
            review_required = base_conf < threshold
            auto_accepted = base_conf >= threshold
            suggestion = _persist_suggestion(
                connection, patient_id, "icd10", code, description,
                base_conf, search_corpus[:300], review_required, auto_accepted, now,
            )
            suggestions.append(suggestion)

    return suggestions


def _generate_cpt_suggestions(
    connection: sqlite3.Connection,
    patient_id: int,
    clinical_text: str,
    now: str,
) -> list[dict[str, Any]]:
    threshold = _get_threshold(connection, "cpt")

    med_rows = connection.execute(
        """
        SELECT element_value FROM clinical_profile_elements
        WHERE patient_id=? AND element_type='medication' AND is_active=1
        """,
        (patient_id,),
    ).fetchall()

    search_corpus = (
        " ".join(r["element_value"] for r in med_rows) + " " + clinical_text
    ).lower()

    suggestions: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for rule in _CPT_RULES:
        pattern, code, description, base_conf = rule
        if code in seen_codes:
            continue
        if re.search(pattern, search_corpus):
            seen_codes.add(code)
            review_required = base_conf < threshold
            auto_accepted = base_conf >= threshold
            suggestion = _persist_suggestion(
                connection, patient_id, "cpt", code, description,
                base_conf, search_corpus[:300], review_required, auto_accepted, now,
            )
            suggestions.append(suggestion)

    return suggestions


def _persist_suggestion(
    connection: sqlite3.Connection,
    patient_id: int,
    code_type: str,
    code: str,
    description: str,
    confidence: float,
    evidence_text: str,
    review_required: bool,
    auto_accepted: bool,
    now: str,
) -> dict[str, Any]:
    with connection:
        # Skip if suggestion for this patient/code_type/code already exists (avoid duplicates on re-run)
        existing = connection.execute(
            "SELECT id, status FROM clinical_code_suggestions WHERE patient_id=? AND code_type=? AND code=?",
            (patient_id, code_type, code),
        ).fetchone()
        if existing:
            return {
                "id": existing["id"],
                "codeType": code_type,
                "code": code,
                "description": description,
                "confidenceScore": confidence,
                "evidenceText": evidence_text[:200],
                "reviewRequired": review_required,
                "autoAccepted": auto_accepted,
                "status": existing["status"],
            }

        cursor = connection.execute(
            """
            INSERT INTO clinical_code_suggestions
                (patient_id, code_type, code, description, confidence_score, evidence_text,
                 review_required, auto_accepted, status, source, suggested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'rule_engine_v1', ?)
            """,
            (
                patient_id,
                code_type,
                code,
                description,
                confidence,
                evidence_text,
                int(review_required),
                int(auto_accepted),
                "accepted" if auto_accepted else "pending",
                now,
            ),
        )
        suggestion_id = cursor.lastrowid

    return {
        "id": suggestion_id,
        "codeType": code_type,
        "code": code,
        "description": description,
        "confidenceScore": confidence,
        "evidenceText": evidence_text[:200],
        "reviewRequired": review_required,
        "autoAccepted": auto_accepted,
        "status": "accepted" if auto_accepted else "pending",
    }


def get_suggestions(
    connection: sqlite3.Connection,
    patient_id: int,
    code_type: str | None = None,
    review_only: bool = False,
) -> tuple[int, dict[str, Any]]:
    """Return suggestions for a patient, optionally filtered."""
    conditions = ["patient_id=?"]
    params: list[Any] = [patient_id]

    if code_type in ("icd10", "cpt"):
        conditions.append("code_type=?")
        params.append(code_type)

    if review_only:
        conditions.append("review_required=1")
        conditions.append("status='pending'")

    where = " AND ".join(conditions)
    rows = connection.execute(
        f"""
        SELECT id, code_type, code, description, confidence_score, evidence_text,
               review_required, auto_accepted, status, reviewer_id, reviewed_at,
               override_code, override_description, rejection_reason, suggested_at
        FROM clinical_code_suggestions
        WHERE {where}
        ORDER BY review_required DESC, confidence_score ASC, suggested_at DESC
        """,
        params,
    ).fetchall()

    items = [
        {
            "id": r["id"],
            "codeType": r["code_type"],
            "code": r["code"],
            "description": r["description"],
            "confidenceScore": r["confidence_score"],
            "evidenceText": r["evidence_text"],
            "reviewRequired": bool(r["review_required"]),
            "autoAccepted": bool(r["auto_accepted"]),
            "status": r["status"],
            "reviewerId": r["reviewer_id"],
            "reviewedAt": r["reviewed_at"],
            "overrideCode": r["override_code"],
            "overrideDescription": r["override_description"],
            "rejectionReason": r["rejection_reason"],
            "suggestedAt": r["suggested_at"],
        }
        for r in rows
    ]
    return 200, {"patientId": patient_id, "suggestions": items, "total": len(items)}


# ---------------------------------------------------------------------------
# TASK-028: Code verification — accept/reject/override
# ---------------------------------------------------------------------------


def review_code_suggestion(
    connection: sqlite3.Connection,
    suggestion_id: int,
    patient_id: int,
    action: str,
    reviewer_id: str,
    override_code: str | None = None,
    override_description: str | None = None,
    rejection_reason: str | None = None,
    decision_metadata: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Accept, reject, or override a code suggestion (AC-1, AC-3, AC-4)."""
    valid_actions = {"accept", "reject", "override"}
    if action not in valid_actions:
        return 400, {
            "code": "VALIDATION_ERROR",
            "message": f"action must be one of: {', '.join(sorted(valid_actions))}",
        }

    if action == "override" and not override_code:
        return 400, {
            "code": "VALIDATION_ERROR",
            "message": "override_code is required for override action.",
        }

    row = connection.execute(
        "SELECT id, status, patient_id FROM clinical_code_suggestions WHERE id=? AND patient_id=?",
        (suggestion_id, patient_id),
    ).fetchone()

    if row is None:
        return 404, {"code": "NOT_FOUND", "message": "Suggestion not found."}

    prev_status = row["status"]
    new_status = {"accept": "accepted", "reject": "rejected", "override": "overridden"}[action]
    now = _utc_now_iso()

    with connection:
        connection.execute(
            """
            UPDATE clinical_code_suggestions
            SET status=?, reviewer_id=?, reviewed_at=?,
                override_code=?, override_description=?, rejection_reason=?
            WHERE id=?
            """,
            (
                new_status,
                reviewer_id,
                now,
                override_code,
                override_description,
                rejection_reason,
                suggestion_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO clinical_code_review_audit
                (suggestion_id, patient_id, action, reviewer_id,
                 override_code, override_description, rejection_reason,
                 previous_status, new_status, decision_metadata, acted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                suggestion_id,
                patient_id,
                action,
                reviewer_id,
                override_code,
                override_description,
                rejection_reason,
                prev_status,
                new_status,
                json.dumps(decision_metadata) if decision_metadata else None,
                now,
            ),
        )

    return 200, {
        "suggestionId": suggestion_id,
        "action": action,
        "previousStatus": prev_status,
        "newStatus": new_status,
        "reviewerId": reviewer_id,
        "reviewedAt": now,
    }


# ---------------------------------------------------------------------------
# TASK-029: Confidence threshold configuration
# ---------------------------------------------------------------------------


def get_thresholds(connection: sqlite3.Connection) -> tuple[int, dict[str, Any]]:
    """Return current threshold configuration."""
    _seed_thresholds_if_empty(connection)
    rows = connection.execute(
        "SELECT code_type, threshold_value, updated_by, updated_at FROM clinical_threshold_config"
    ).fetchall()
    thresholds = {r["code_type"]: {"value": r["threshold_value"], "updatedBy": r["updated_by"], "updatedAt": r["updated_at"]} for r in rows}
    return 200, {"thresholds": thresholds}


def update_threshold(
    connection: sqlite3.Connection,
    code_type: str,
    new_value: float,
    updated_by: str,
    role: str,
) -> tuple[int, dict[str, Any]]:
    """Update a confidence threshold. Authorized roles: admin, coder (SEC-1)."""
    allowed_roles = {"admin", "coder", "clinical_admin"}
    if role not in allowed_roles:
        return 403, {
            "code": "FORBIDDEN",
            "message": f"Role '{role}' is not authorized to modify thresholds. Requires: {', '.join(sorted(allowed_roles))}.",
        }

    if code_type not in ("icd10", "cpt", "all"):
        return 400, {
            "code": "VALIDATION_ERROR",
            "message": "code_type must be 'icd10', 'cpt', or 'all'.",
        }

    if not (0.0 <= new_value <= 1.0):
        return 400, {
            "code": "VALIDATION_ERROR",
            "message": "threshold_value must be between 0.0 and 1.0.",
        }

    _seed_thresholds_if_empty(connection)
    now = _utc_now_iso()

    existing = connection.execute(
        "SELECT threshold_value FROM clinical_threshold_config WHERE code_type=?",
        (code_type,),
    ).fetchone()
    old_value = existing["threshold_value"] if existing else None

    with connection:
        connection.execute(
            """
            INSERT INTO clinical_threshold_config (code_type, threshold_value, updated_by, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(code_type) DO UPDATE SET threshold_value=excluded.threshold_value,
                updated_by=excluded.updated_by, updated_at=excluded.updated_at
            """,
            (code_type, new_value, updated_by, now),
        )
        connection.execute(
            """
            INSERT INTO clinical_threshold_history (code_type, old_value, new_value, changed_by, changed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (code_type, old_value, new_value, updated_by, now),
        )

    return 200, {
        "codeType": code_type,
        "previousValue": old_value,
        "newValue": new_value,
        "updatedBy": updated_by,
        "updatedAt": now,
    }


def get_threshold_history(connection: sqlite3.Connection, code_type: str | None = None) -> tuple[int, dict[str, Any]]:
    """Return threshold change history."""
    if code_type:
        rows = connection.execute(
            "SELECT * FROM clinical_threshold_history WHERE code_type=? ORDER BY changed_at DESC",
            (code_type,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM clinical_threshold_history ORDER BY changed_at DESC"
        ).fetchall()

    history = [
        {
            "id": r["id"],
            "codeType": r["code_type"],
            "oldValue": r["old_value"],
            "newValue": r["new_value"],
            "changedBy": r["changed_by"],
            "changedAt": r["changed_at"],
        }
        for r in rows
    ]
    return 200, {"history": history}


# ---------------------------------------------------------------------------
# TASK-030: Conflict resolution
# ---------------------------------------------------------------------------


def get_conflict_queue(
    connection: sqlite3.Connection,
    patient_id: int | None = None,
) -> tuple[int, dict[str, Any]]:
    """Return unresolved conflicts from both medication and allergy-drug tables."""
    conditions_med = ["resolved_at IS NULL"]
    conditions_allergy = ["resolved_at IS NULL"]
    params_med: list[Any] = []
    params_allergy: list[Any] = []

    if patient_id is not None:
        conditions_med.append("patient_id=?")
        conditions_allergy.append("patient_id=?")
        params_med.append(patient_id)
        params_allergy.append(patient_id)

    med_rows = connection.execute(
        f"""
        SELECT id, patient_id, conflict_type AS type, severity,
               medication_a AS version_a, medication_b AS version_b,
               clinical_impact, source, detected_at,
               'clinical_medication_conflicts' AS conflict_table
        FROM clinical_medication_conflicts
        WHERE {' AND '.join(conditions_med)}
        ORDER BY severity DESC, detected_at DESC
        """,
        params_med,
    ).fetchall()

    allergy_rows = connection.execute(
        f"""
        SELECT id, patient_id, 'allergy_drug_interaction' AS type, severity,
               allergen AS version_a, medication AS version_b,
               clinical_impact, source, detected_at,
               'clinical_allergy_drug_conflicts' AS conflict_table
        FROM clinical_allergy_drug_conflicts
        WHERE {' AND '.join(conditions_allergy)}
        ORDER BY severity DESC, detected_at DESC
        """,
        params_allergy,
    ).fetchall()

    def _row_to_dict(r: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": r["id"],
            "patientId": r["patient_id"],
            "conflictType": r["type"],
            "severity": r["severity"],
            "versionA": r["version_a"],
            "versionB": r["version_b"],
            "clinicalImpact": r["clinical_impact"],
            "source": r["source"],
            "detectedAt": r["detected_at"],
            "conflictTable": r["conflict_table"],
        }

    items = [_row_to_dict(r) for r in med_rows] + [_row_to_dict(r) for r in allergy_rows]
    items.sort(key=lambda x: ("high", "medium", "low").index(x["severity"]) if x["severity"] in ("high", "medium", "low") else 3)

    return 200, {
        "conflicts": items,
        "total": len(items),
        "highCount": sum(1 for i in items if i["severity"] == "high"),
        "mediumCount": sum(1 for i in items if i["severity"] == "medium"),
        "lowCount": sum(1 for i in items if i["severity"] == "low"),
    }


def resolve_conflict(
    connection: sqlite3.Connection,
    conflict_id: int,
    conflict_table: str,
    patient_id: int,
    action: str,
    reviewer_id: str,
    chosen_value: str | None = None,
    merge_value: str | None = None,
    resolution_note: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Resolve a conflict with audit logging (BE-1, BE-2, AC-3, AC-4)."""
    valid_tables = {"clinical_medication_conflicts", "clinical_allergy_drug_conflicts"}
    if conflict_table not in valid_tables:
        return 400, {
            "code": "VALIDATION_ERROR",
            "message": f"conflict_table must be one of: {', '.join(sorted(valid_tables))}",
        }

    valid_actions = {"resolve", "merge", "discard"}
    if action not in valid_actions:
        return 400, {
            "code": "VALIDATION_ERROR",
            "message": f"action must be one of: {', '.join(sorted(valid_actions))}",
        }

    row = connection.execute(
        f"SELECT id, patient_id FROM {conflict_table} WHERE id=? AND patient_id=?",
        (conflict_id, patient_id),
    ).fetchone()

    if row is None:
        return 404, {"code": "NOT_FOUND", "message": "Conflict not found."}

    existing_resolution = connection.execute(
        "SELECT id FROM clinical_conflict_resolutions WHERE conflict_id=? AND conflict_table=?",
        (conflict_id, conflict_table),
    ).fetchone()

    if existing_resolution:
        return 409, {"code": "CONFLICT", "message": "This conflict has already been resolved."}

    version_a: str | None = None
    version_b: str | None = None

    conflict_detail = connection.execute(
        f"SELECT * FROM {conflict_table} WHERE id=?",
        (conflict_id,),
    ).fetchone()

    if conflict_detail:
        if conflict_table == "clinical_medication_conflicts":
            version_a = conflict_detail["medication_a"]
            version_b = conflict_detail["medication_b"]
        else:
            version_a = conflict_detail["allergen"]
            version_b = conflict_detail["medication"]

    now = _utc_now_iso()

    with connection:
        connection.execute(
            f"UPDATE {conflict_table} SET resolved_at=?, resolution_note=? WHERE id=?",
            (now, resolution_note, conflict_id),
        )
        connection.execute(
            """
            INSERT INTO clinical_conflict_resolutions
                (conflict_id, conflict_table, patient_id, action, chosen_value, merge_value,
                 reviewer_id, resolution_note, version_a_snapshot, version_b_snapshot, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conflict_id,
                conflict_table,
                patient_id,
                action,
                chosen_value,
                merge_value,
                reviewer_id,
                resolution_note,
                version_a,
                version_b,
                now,
            ),
        )

    return 200, {
        "conflictId": conflict_id,
        "conflictTable": conflict_table,
        "action": action,
        "reviewerId": reviewer_id,
        "resolvedAt": now,
        "versionASnapshot": version_a,
        "versionBSnapshot": version_b,
    }
