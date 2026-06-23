"""Tests for EP-003 Clinical Intelligence Platform (TASK-019 through TASK-024)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src import db
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
from src.web_app import create_app


class FakeInput:
    def __init__(self, data: bytes):
        self._data = data

    def read(self, n=-1):
        return self._data


def _make_pdf_bytes() -> bytes:
    return b"%PDF-1.4 fake content: Patient takes warfarin 5mg and aspirin 81mg daily. Allergic to penicillin. Diagnosis: hypertension."


def _make_docx_bytes() -> bytes:
    # Minimal fake DOCX (not a real DOCX, used for type-validation only)
    return b"PK\x03\x04fake docx content: metformin 500mg, lisinopril 10mg."


class UploadAndProcessingTests(unittest.TestCase):
    """TASK-020: Document upload pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "clinical.db"
        db.initialize_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except PermissionError:
            pass

    def _conn(self):
        return db.get_connection(self.db_path)

    # QA-1: Accept PDF upload
    def test_pdf_upload_success(self):
        with self._conn() as conn:
            status, data = upload_document(
                conn, 1, "report.pdf", "application/pdf", _make_pdf_bytes()
            )
        self.assertEqual(status, 201)
        self.assertIn("documentId", data)
        self.assertEqual(data["status"], "uploaded")

    # QA-1: Accept DOCX upload
    def test_docx_upload_success(self):
        with self._conn() as conn:
            status, data = upload_document(
                conn,
                1,
                "notes.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                b"PK\x03\x04docx bytes here for test",
            )
        self.assertEqual(status, 201)
        self.assertEqual(data["status"], "uploaded")

    # QA-3: Reject unsupported file type
    def test_unsupported_file_type_rejected(self):
        with self._conn() as conn:
            status, data = upload_document(
                conn, 1, "image.jpg", "image/jpeg", b"\xff\xd8\xff fake jpg"
            )
        self.assertEqual(status, 400)
        self.assertIn("code", data)
        self.assertEqual(data["code"], "VALIDATION_ERROR")

    # QA-3: Reject invalid extension even with valid MIME
    def test_invalid_extension_rejected(self):
        with self._conn() as conn:
            status, data = upload_document(
                conn, 1, "report.txt", "application/pdf", _make_pdf_bytes()
            )
        self.assertEqual(status, 400)

    # QA-3: Reject oversized file
    def test_oversized_file_rejected(self):
        big_data = b"%PDF" + b"x" * (21 * 1024 * 1024)
        with self._conn() as conn:
            status, data = upload_document(
                conn, 1, "big.pdf", "application/pdf", big_data
            )
        self.assertEqual(status, 400)
        self.assertIn("20 MB", data.get("details", [""])[0] if data.get("details") else data.get("message", ""))

    # QA-3: Empty file rejected
    def test_empty_file_rejected(self):
        with self._conn() as conn:
            status, data = upload_document(
                conn, 1, "empty.pdf", "application/pdf", b""
            )
        self.assertEqual(status, 400)

    # QA-2: Status transitions
    def test_processing_status_transitions(self):
        with self._conn() as conn:
            _, upload_data = upload_document(
                conn, 1, "lab.pdf", "application/pdf", _make_pdf_bytes()
            )
            doc_id = upload_data["documentId"]

            status, status_data = get_document_status(conn, doc_id, 1)
        self.assertEqual(status, 200)
        self.assertEqual(status_data["processingStatus"], "uploaded")

    # Authorization: status not accessible for wrong patient
    def test_document_status_not_found_for_wrong_patient(self):
        with self._conn() as conn:
            _, upload_data = upload_document(
                conn, 1, "secure.pdf", "application/pdf", _make_pdf_bytes()
            )
            doc_id = upload_data["documentId"]
            status, data = get_document_status(conn, doc_id, 999)
        self.assertEqual(status, 404)


class ExtractionTests(unittest.TestCase):
    """TASK-021: Structured data extraction."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "extraction.db"
        db.initialize_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except PermissionError:
            pass

    def _conn(self):
        return db.get_connection(self.db_path)

    def _upload_and_process(self, text: str) -> int:
        with self._conn() as conn:
            _, data = upload_document(conn, 1, "doc.pdf", "application/pdf", _make_pdf_bytes())
            doc_id = data["documentId"]
            process_document(conn, doc_id, text)
        return doc_id

    # QA-1: Medications extracted from document text
    def test_medication_entities_extracted(self):
        doc_text = "Patient takes warfarin 5mg and aspirin 81mg daily."
        doc_id = self._upload_and_process(doc_text)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT entity_type, entity_value FROM clinical_extracted_entities WHERE document_id=?",
                (doc_id,),
            ).fetchall()
        types = [r["entity_type"] for r in rows]
        self.assertIn("medication", types)

    # QA-2: Confidence scores present and in range
    def test_confidence_scores_present_and_valid(self):
        doc_text = "Diagnosis: hypertension. Allergic to penicillin."
        doc_id = self._upload_and_process(doc_text)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT confidence_score FROM clinical_extracted_entities WHERE document_id=?",
                (doc_id,),
            ).fetchall()
        for row in rows:
            self.assertGreaterEqual(row["confidence_score"], 0.0)
            self.assertLessEqual(row["confidence_score"], 1.0)

    # QA-3: Failure flagged with review_required
    def test_process_document_failure_flags_review(self):
        with self._conn() as conn:
            _, data = upload_document(conn, 1, "fail.pdf", "application/pdf", _make_pdf_bytes())
            doc_id = data["documentId"]
            # Force failure by using a non-existent document ID in process call
            result = process_document(conn, 99999, "some text")
        self.assertEqual(result["status"], "failed")
        self.assertIn("failureReason", result)

    # QA-3: Processing status set to complete on success
    def test_processing_status_complete_on_success(self):
        doc_id = self._upload_and_process("Patient takes metformin 500mg and lisinopril 10mg.")
        with self._conn() as conn:
            _, status_data = get_document_status(conn, doc_id, 1)
        self.assertEqual(status_data["processingStatus"], "complete")

    # QA-2: Extraction timestamps persisted
    def test_extraction_timestamps_persisted(self):
        doc_id = self._upload_and_process("aspirin 81mg daily")
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT extracted_at FROM clinical_extracted_entities WHERE document_id=?",
                (doc_id,),
            ).fetchall()
        for row in rows:
            self.assertIsNotNone(row["extracted_at"])


class AggregationTests(unittest.TestCase):
    """TASK-019: Patient data aggregation."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "aggregation.db"
        db.initialize_database(cls.db_path)
        # Upload + process a document
        with db.get_connection(cls.db_path) as conn:
            _, data = upload_document(conn, 1, "intake.pdf", "application/pdf", _make_pdf_bytes())
            process_document(
                conn,
                data["documentId"],
                "Patient takes warfarin 5mg and aspirin 81mg. Allergic to sulfa drugs. Diagnosis: hypertension.",
            )

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except PermissionError:
            pass

    def _conn(self):
        return db.get_connection(self.db_path)

    # QA-1: Profile completeness when both intake and document data are present
    def test_aggregation_merges_intake_and_document_data(self):
        intake = {"medications": ["metoprolol 25mg"], "allergies": ["latex"], "diagnoses": ["diabetes type 2"]}
        with self._conn() as conn:
            result = aggregate_patient_profile(conn, 1, intake)
        self.assertGreater(result["elementsAggregated"], 0)

    # QA-1: Deduplication — intake takes priority
    def test_deduplication_intake_wins(self):
        intake = {"medications": ["warfarin 5mg"], "allergies": [], "diagnoses": []}
        with self._conn() as conn:
            aggregate_patient_profile(conn, 1, intake)
            rows = conn.execute(
                "SELECT source_type, normalized_value FROM clinical_profile_elements "
                "WHERE patient_id=1 AND element_type='medication' AND is_active=1",
            ).fetchall()
        # warfarin should appear exactly once with intake source type winning
        warfarin_rows = [r for r in rows if "warfarin" in (r["normalized_value"] or "")]
        intake_sources = [r for r in warfarin_rows if r["source_type"] == "intake"]
        document_sources = [r for r in warfarin_rows if r["source_type"] == "document"]
        self.assertGreater(len(intake_sources), 0)
        self.assertEqual(len(document_sources), 0)

    # QA-2: Source metadata preserved through aggregation
    def test_provenance_preserved(self):
        with self._conn() as conn:
            aggregate_patient_profile(conn, 1)
            rows = conn.execute(
                "SELECT source_type, source_id FROM clinical_profile_elements WHERE patient_id=1 AND is_active=1",
            ).fetchall()
        for row in rows:
            self.assertIn(row["source_type"], ("intake", "document"))
            self.assertIsNotNone(row["source_id"])

    # QA-2: Idempotent re-run does not duplicate
    def test_idempotent_reaggregation(self):
        with self._conn() as conn:
            aggregate_patient_profile(conn, 1)
            count1 = conn.execute(
                "SELECT COUNT(*) AS c FROM clinical_profile_elements WHERE patient_id=1 AND is_active=1"
            ).fetchone()["c"]
            aggregate_patient_profile(conn, 1)
            count2 = conn.execute(
                "SELECT COUNT(*) AS c FROM clinical_profile_elements WHERE patient_id=1 AND is_active=1"
            ).fetchone()["c"]
        self.assertEqual(count1, count2)


class ProfileUITests(unittest.TestCase):
    """TASK-022: 360° patient profile API."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "profile_ui.db"
        db.initialize_database(cls.db_path)
        with db.get_connection(cls.db_path) as conn:
            _, data = upload_document(conn, 1, "history.pdf", "application/pdf", _make_pdf_bytes())
            process_document(
                conn,
                data["documentId"],
                "warfarin 5mg, aspirin 81mg. Allergic to penicillin. Diagnosis: hypertension, diabetes.",
            )
            aggregate_patient_profile(conn, 1)
        cls.app = create_app(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except PermissionError:
            pass

    def _request(self, method, path, body=None):
        payload = json.dumps(body or {}).encode("utf-8")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path.split("?", 1)[0],
            "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
            "CONTENT_LENGTH": str(len(payload)) if method == "POST" else "0",
            "wsgi.input": FakeInput(payload),
        }
        meta = {}

        def start_response(status, headers):
            meta["status"] = status

        chunks = self.__class__.app(environ, start_response)
        return meta["status"], json.loads(b"".join(chunks).decode("utf-8"))

    # QA-1: All tabs render via API
    def test_profile_api_returns_all_tabs(self):
        status, payload = self._request("GET", "/api/clinical/patients/1/profile")
        self.assertTrue(status.startswith("200"))
        self.assertIn("overview", payload["data"])
        self.assertIn("medications", payload["data"])
        self.assertIn("allergies", payload["data"])
        self.assertIn("diagnoses", payload["data"])

    # QA-2: Source attribution present
    def test_profile_items_have_source_attribution(self):
        status, payload = self._request("GET", "/api/clinical/patients/1/profile")
        self.assertTrue(status.startswith("200"))
        for tab in ("medications", "allergies", "diagnoses"):
            for item in payload["data"].get(tab, []):
                self.assertIn("sourceType", item)
                self.assertIn(item["sourceType"], ("intake", "document"))

    # Profile not found for non-existent patient
    def test_profile_not_found(self):
        status, payload = self._request("GET", "/api/clinical/patients/99999/profile")
        self.assertTrue(status.startswith("404"))


class SourceTraceabilityTests(unittest.TestCase):
    """TASK-023: Source traceability."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "traceability.db"
        db.initialize_database(cls.db_path)
        with db.get_connection(cls.db_path) as conn:
            _, data = upload_document(conn, 1, "scan.pdf", "application/pdf", _make_pdf_bytes())
            cls.doc_id = data["documentId"]
            process_document(conn, cls.doc_id, "warfarin 5mg and aspirin 81mg. Allergic to sulfa.")
            aggregate_patient_profile(conn, 1)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except PermissionError:
            pass

    def _conn(self):
        return db.get_connection(self.db_path)

    # QA-1: Source metadata for document-sourced item
    def test_source_metadata_returned_for_element(self):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id FROM clinical_profile_elements WHERE patient_id=1 AND source_type='document' AND is_active=1 LIMIT 1"
            ).fetchall()
            if not rows:
                self.skipTest("No document-sourced elements present")
            element_id = rows[0]["id"]
            status, data = get_source_metadata(conn, element_id, 1)
        self.assertEqual(status, 200)
        self.assertIn("sourceType", data)
        self.assertIn("confidenceScore", data)

    # QA-2: Signed URL generation
    def test_signed_url_generated(self):
        with self._conn() as conn:
            status, data = generate_signed_document_url(conn, self.__class__.doc_id, 1)
        self.assertEqual(status, 200)
        self.assertIn("signedUrl", data)
        self.assertIn("expiresAt", data)
        self.assertGreater(data["ttlSeconds"], 0)

    # QA-2: Signed URL validates correctly
    def test_signed_url_validates(self):
        with self._conn() as conn:
            _, data = generate_signed_document_url(conn, self.__class__.doc_id, 1)
        valid = validate_signed_url(
            self.__class__.doc_id, 1, data["expiresAt"], data["signedUrl"].split("sig=")[1]
        )
        self.assertTrue(valid)

    # QA-2: Tampered signature rejected
    def test_tampered_signature_rejected(self):
        valid = validate_signed_url(
            self.__class__.doc_id, 1, int(__import__("time").time()) + 3600, "fakesignature"
        )
        self.assertFalse(valid)

    # QA-2: Expired URL rejected
    def test_expired_url_rejected(self):
        valid = validate_signed_url(
            self.__class__.doc_id, 1, int(__import__("time").time()) - 1, "anysig"
        )
        self.assertFalse(valid)

    # Element not accessible for wrong patient
    def test_element_source_not_found_wrong_patient(self):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id FROM clinical_profile_elements WHERE patient_id=1 AND is_active=1 LIMIT 1"
            ).fetchall()
            if not rows:
                self.skipTest("No elements present")
            element_id = rows[0]["id"]
            status, _ = get_source_metadata(conn, element_id, 999)
        self.assertEqual(status, 404)


class ConflictDetectionTests(unittest.TestCase):
    """TASK-024: Medication conflict detection."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "conflicts.db"
        db.initialize_database(cls.db_path)
        with db.get_connection(cls.db_path) as conn:
            _, data = upload_document(conn, 1, "meds.pdf", "application/pdf", _make_pdf_bytes())
            process_document(
                conn,
                data["documentId"],
                "Patient takes warfarin 5mg daily. Also takes aspirin 81mg. simvastatin 20mg and atorvastatin 40mg.",
            )
            aggregate_patient_profile(conn, 1)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except PermissionError:
            pass

    def _conn(self):
        return db.get_connection(self.db_path)

    # QA-1: Known drug-drug interaction pair is flagged
    def test_warfarin_aspirin_interaction_detected(self):
        with self._conn() as conn:
            status, data = detect_medication_conflicts(conn, 1)
        self.assertEqual(status, 200)
        conflict_types = [c["conflictType"] for c in data["conflicts"]]
        self.assertIn("drug_drug_interaction", conflict_types)
        meds_involved = [(c["medicationA"].lower(), c["medicationB"].lower()) for c in data["conflicts"]]
        found = any(
            ("warfarin" in a or "warfarin" in b) and ("aspirin" in a or "aspirin" in b)
            for a, b in meds_involved
        )
        self.assertTrue(found, "warfarin + aspirin interaction should be detected")

    # QA-1: Duplicate therapy flagged
    def test_duplicate_statin_therapy_detected(self):
        with self._conn() as conn:
            status, data = detect_medication_conflicts(conn, 1)
        self.assertEqual(status, 200)
        dup_types = [c["conflictType"] for c in data["conflicts"]]
        self.assertIn("duplicate_therapy", dup_types)

    # QA-1: Severity metadata present on each conflict
    def test_conflict_severity_metadata_present(self):
        with self._conn() as conn:
            _, data = detect_medication_conflicts(conn, 1)
        for conflict in data["conflicts"]:
            self.assertIn(conflict["severity"], ("high", "medium", "low"))
            self.assertIn("medicationA", conflict)
            self.assertIn("medicationB", conflict)
            self.assertIn("clinicalImpact", conflict)

    # QA-3: Graceful failure when detection unavailable
    def test_graceful_failure_on_detection_error(self):
        """Simulate a broken connection by calling with a closed connection."""
        import sqlite3
        broken_conn = sqlite3.connect(":memory:")
        broken_conn.row_factory = sqlite3.Row
        broken_conn.close()
        status, data = detect_medication_conflicts(broken_conn, 1)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("degraded"), "Should return degraded state on error")
        self.assertEqual(data["conflicts"], [])

    # Conflicts persist to DB
    def test_conflicts_persisted_to_db(self):
        with self._conn() as conn:
            detect_medication_conflicts(conn, 1)
            rows = conn.execute(
                "SELECT * FROM clinical_medication_conflicts WHERE patient_id=1"
            ).fetchall()
        self.assertGreater(len(rows), 0)

    # No conflicts for patient with no medications
    def test_no_conflicts_for_empty_medication_list(self):
        with db.get_connection(self.db_path) as conn:
            status, data = detect_medication_conflicts(conn, 999)
        self.assertEqual(status, 200)
        self.assertEqual(data["conflicts"], [])
        self.assertFalse(data.get("degraded"))


class ClinicalAPIIntegrationTests(unittest.TestCase):
    """Full API integration tests through WSGI app."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "api_integration.db"
        db.initialize_database(cls.db_path)
        cls.app = create_app(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except PermissionError:
            pass

    def _request(self, method, path, body=None, content_type="application/json", raw_body=None):
        if raw_body is not None:
            payload = raw_body
        else:
            payload = json.dumps(body or {}).encode("utf-8")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path.split("?", 1)[0],
            "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
            "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": str(len(payload)) if method == "POST" else "0",
            "wsgi.input": FakeInput(payload),
        }
        meta = {}

        def start_response(status, headers):
            meta["status"] = status

        chunks = self.__class__.app(environ, start_response)
        return meta["status"], json.loads(b"".join(chunks).decode("utf-8"))

    def test_upload_pdf_via_api(self):
        pdf = _make_pdf_bytes()
        status, payload = self._request(
            "POST",
            "/api/clinical/documents/upload?fileName=test.pdf&patientId=1",
            content_type="application/pdf",
            raw_body=pdf,
        )
        self.assertTrue(status.startswith("201"))
        self.assertIn("documentId", payload["data"])

    def test_upload_unsupported_type_via_api(self):
        status, payload = self._request(
            "POST",
            "/api/clinical/documents/upload?fileName=image.jpg&patientId=1",
            content_type="image/jpeg",
            raw_body=b"\xff\xd8\xff jpg content",
        )
        self.assertTrue(status.startswith("400"))
        self.assertFalse(payload["success"])

    def test_document_status_via_api(self):
        pdf = _make_pdf_bytes()
        _, upload = self._request(
            "POST",
            "/api/clinical/documents/upload?fileName=status_test.pdf&patientId=1",
            content_type="application/pdf",
            raw_body=pdf,
        )
        doc_id = upload["data"]["documentId"]
        status, payload = self._request("GET", f"/api/clinical/documents/{doc_id}/status?patientId=1")
        self.assertTrue(status.startswith("200"))
        self.assertIn("processingStatus", payload["data"])

    def test_conflicts_endpoint_via_api(self):
        status, payload = self._request("GET", "/api/clinical/patients/1/conflicts")
        self.assertTrue(status.startswith("200"))
        self.assertIn("conflicts", payload["data"])

    def test_clinical_profile_endpoint_returns_tabs(self):
        status, payload = self._request("GET", "/api/clinical/patients/1/profile")
        self.assertTrue(status.startswith("200"))
        self.assertIn("medications", payload["data"])
        self.assertIn("allergies", payload["data"])
        self.assertIn("diagnoses", payload["data"])

    def test_unknown_clinical_route_returns_404(self):
        status, payload = self._request("GET", "/api/clinical/unknown-endpoint")
        self.assertTrue(status.startswith("404"))


if __name__ == "__main__":
    unittest.main()
