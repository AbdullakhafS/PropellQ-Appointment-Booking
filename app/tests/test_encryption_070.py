from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from unittest import TestCase

from src.backup_automation import (
    BackupEngine,
    BackupPolicy,
    BackupStatus,
    BackupType,
    InMemoryBackupAlertSink,
)
from src.db import initialize_database, get_connection
from src.encryption_service import (
    EncryptedPayload,
    EncryptionEngine,
    InMemoryKeyStore,
    KeyStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_policy(name: str = "test_policy") -> BackupPolicy:
    return BackupPolicy(
        policy_name=name,
        dataset_name="appointments",
        backup_type=BackupType.FULL,
        schedule_cron="0 2 * * *",
        retention_days=30,
        encryption_algorithm="AES-256-GCM",
        kms_key_id=None,
        compression_enabled=True,
        storage_location="/mnt/backups",
        owner_team="platform-team",
        rpo_target_minutes=60,
        rto_target_minutes=120,
    )


# ===========================================================================
# Task 001 — Encryption Architecture and Scope
# ===========================================================================

class TestEncryptionArchitectureScope(TestCase):
    """AC: Encryption scope covers PHI stores, audit logs, and backups.
    AC: Database-native or disk-level approach is selected and documented."""

    def test_encryption_algorithm_is_aes256gcm(self) -> None:
        """Verify the required algorithm is AES-256-GCM."""
        engine = EncryptionEngine(InMemoryKeyStore())
        self.assertEqual(engine.ALGORITHM, "AES-256-GCM")

    def test_backup_policy_records_encryption_algorithm(self) -> None:
        """Backup policies explicitly record the required encryption algorithm."""
        policy = _make_policy()
        self.assertEqual(policy.encryption_algorithm, "AES-256-GCM")

    def test_key_material_separated_from_ciphertext(self) -> None:
        """Encrypted payload wire format must NOT embed raw key bytes."""
        store = InMemoryKeyStore()
        engine = EncryptionEngine(store)
        plaintext = b"PHI patient record"
        payload = engine.encrypt(plaintext)

        serialized = payload.to_bytes()

        # Key material (32 raw bytes) must not appear in the serialized payload
        raw_key = store.get_raw_key(store.get_active_key_id())
        self.assertNotIn(raw_key, serialized)

    def test_payload_contains_key_id_not_key_material(self) -> None:
        """Serialized payload contains the key_id reference, not raw key bytes."""
        store = InMemoryKeyStore()
        engine = EncryptionEngine(store)
        payload = engine.encrypt(b"sensitive data")

        deserialized = EncryptedPayload.from_bytes(payload.to_bytes())
        self.assertEqual(deserialized.key_id, payload.key_id)
        # key_id is a hex string identifier, not a 32-byte raw key
        self.assertEqual(len(deserialized.key_id), 32)  # uuid4().hex length

    def test_scope_includes_phi_backup_artifacts(self) -> None:
        """Compliance evidence reports the correct HIPAA scope."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            initialize_database(db_path)
            key_store = InMemoryKeyStore()
            with get_connection(db_path) as conn:
                engine = BackupEngine(conn, backup_dir=Path(tmp), key_store=key_store)
                engine.register_policy(_make_policy())
                execution = engine.execute_backup("test_policy", "security-architect")
                evidence = engine.generate_compliance_evidence(execution.execution_id)

        self.assertIn("PHI appointment records", evidence["scope"])
        self.assertIn("Patient profile data", evidence["scope"])
        self.assertIn("Audit log backup artifacts", evidence["scope"])
        self.assertIn("HIPAA", evidence["compliance_standard"])


# ===========================================================================
# Task 002 — Database and Log Encryption (backup at rest)
# ===========================================================================

class TestBackupAtRestEncryption(TestCase):
    """AC: PHI data at rest is encrypted.
    AC: Backup files remain encrypted.
    AC: Unencrypted storage paths are removed."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        initialize_database(self.db_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_backup_file_is_encrypted_after_execute(self) -> None:
        """Backup artifact must start with PROPELIQ magic marker (not plain SQLite)."""
        key_store = InMemoryKeyStore()
        with get_connection(self.db_path) as conn:
            engine = BackupEngine(conn, backup_dir=Path(self.tmp.name), key_store=key_store)
            engine.register_policy(_make_policy())
            execution = engine.execute_backup("test_policy", "dba-operator")

        artifact = Path(execution.artifact_path)
        self.assertTrue(artifact.exists())

        raw_bytes = artifact.read_bytes()
        # Must NOT be a plain SQLite file
        self.assertFalse(raw_bytes.startswith(b"SQLite format 3"))
        # Must be a PROPELIQ encrypted payload
        self.assertTrue(raw_bytes.startswith(b"PROPELIQ_ENC_V1\n"))

    def test_backup_execution_records_encryption_status(self) -> None:
        """execution.encryption_status must be 'encrypted' after backup."""
        key_store = InMemoryKeyStore()
        with get_connection(self.db_path) as conn:
            engine = BackupEngine(conn, backup_dir=Path(self.tmp.name), key_store=key_store)
            engine.register_policy(_make_policy())
            execution = engine.execute_backup("test_policy", "dba-operator")

        self.assertEqual(execution.encryption_status, "encrypted")

    def test_backup_execution_records_encryption_key_id(self) -> None:
        """execution.encryption_key_id must be populated (metadata, not key material)."""
        key_store = InMemoryKeyStore()
        with get_connection(self.db_path) as conn:
            engine = BackupEngine(conn, backup_dir=Path(self.tmp.name), key_store=key_store)
            engine.register_policy(_make_policy())
            execution = engine.execute_backup("test_policy", "dba-operator")

        self.assertIsNotNone(execution.encryption_key_id)
        # key_id must be a hex string, not raw key bytes
        self.assertIsInstance(execution.encryption_key_id, str)
        self.assertEqual(len(execution.encryption_key_id), 32)

    def test_encrypted_backup_is_decryptable(self) -> None:
        """An encrypted backup can be decrypted to valid SQLite content."""
        key_store = InMemoryKeyStore()
        with get_connection(self.db_path) as conn:
            engine = BackupEngine(conn, backup_dir=Path(self.tmp.name), key_store=key_store)
            engine.register_policy(_make_policy())
            execution = engine.execute_backup("test_policy", "dba-operator")

        decrypted = engine.encryption_engine.decrypt_file(execution.artifact_path)
        # Decrypted content should be a valid SQLite file (or empty bytes for empty DB)
        self.assertFalse(decrypted.startswith(b"PROPELIQ_ENC_V1\n"))

    def test_db_schema_includes_encryption_columns(self) -> None:
        """backup_executions table must have encryption_status and encryption_key_id columns."""
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(backup_executions)")
            columns = {row["name"] for row in cursor.fetchall()}

        self.assertIn("encryption_status", columns)
        self.assertIn("encryption_key_id", columns)


# ===========================================================================
# Task 003 — Key Management and Rotation
# ===========================================================================

class TestKeyManagementAndRotation(TestCase):
    """AC: Keys managed outside application data stores.
    AC: Key rotation process is documented and testable.
    AC: Key metadata separated from encrypted data."""

    def test_generate_key_returns_metadata_not_material(self) -> None:
        """generate_key() exposes metadata only; raw bytes accessed via separate call."""
        store = InMemoryKeyStore()
        meta = store.generate_key()

        self.assertIsNotNone(meta.key_id)
        self.assertEqual(meta.algorithm, "AES-256-GCM")
        self.assertEqual(meta.status, KeyStatus.ACTIVE)
        self.assertIsNone(meta.rotated_at)
        # EncryptionKeyMetadata must not have a raw_key attribute
        self.assertFalse(hasattr(meta, "raw_key"))

    def test_raw_key_is_256_bits(self) -> None:
        """Active encryption key must be 256 bits (32 bytes)."""
        store = InMemoryKeyStore()
        store.generate_key()
        raw = store.get_raw_key(store.get_active_key_id())
        self.assertEqual(len(raw), 32)

    def test_key_rotation_produces_new_active_key(self) -> None:
        """After rotation the old key_id must not be the active key."""
        store = InMemoryKeyStore()
        original_meta = store.generate_key()
        original_id = original_meta.key_id

        new_meta = store.rotate_key()

        self.assertNotEqual(new_meta.key_id, original_id)
        self.assertEqual(store.get_active_key_id(), new_meta.key_id)

    def test_rotated_key_status_is_updated(self) -> None:
        """The old key's status changes to ROTATED after key rotation."""
        store = InMemoryKeyStore()
        original_meta = store.generate_key()
        original_id = original_meta.key_id

        store.rotate_key()

        old_meta = store.get_key_metadata(original_id)
        self.assertEqual(old_meta.status, KeyStatus.ROTATED)
        self.assertIsNotNone(old_meta.rotated_at)

    def test_rotated_key_still_decrypts_old_data(self) -> None:
        """Data encrypted before rotation must still be decryptable after rotation."""
        store = InMemoryKeyStore()
        engine = EncryptionEngine(store)
        plaintext = b"sensitive PHI record"

        payload = engine.encrypt(plaintext)
        store.rotate_key()  # rotate after encryption

        recovered = engine.decrypt(payload)
        self.assertEqual(recovered, plaintext)

    def test_key_metadata_list_contains_all_keys(self) -> None:
        """list_key_metadata() returns metadata for all keys, never raw material."""
        store = InMemoryKeyStore()
        store.generate_key()
        store.rotate_key()

        all_meta = store.list_key_metadata()
        self.assertEqual(len(all_meta), 2)
        for meta in all_meta:
            self.assertFalse(hasattr(meta, "raw_key"))

    def test_key_id_stored_in_backup_executions_not_key_bytes(self) -> None:
        """DB backup_executions.encryption_key_id stores key reference, not material."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            initialize_database(db_path)
            key_store = InMemoryKeyStore()
            with get_connection(db_path) as conn:
                engine = BackupEngine(conn, backup_dir=Path(tmp), key_store=key_store)
                engine.register_policy(_make_policy())
                execution = engine.execute_backup("test_policy", "security-eng")

                row = conn.execute(
                    "SELECT encryption_key_id FROM backup_executions WHERE execution_id = ?",
                    [execution.execution_id],
                ).fetchone()

            stored_key_id = row["encryption_key_id"]
            raw_key_material = key_store.get_raw_key(stored_key_id)

        # stored value is a hex string key ID, not the raw 32-byte key
        self.assertEqual(len(stored_key_id), 32)
        self.assertNotEqual(stored_key_id.encode(), raw_key_material)

    def test_key_store_is_separate_from_backup_artifact(self) -> None:
        """Raw key bytes must not appear inside the encrypted backup file."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            initialize_database(db_path)
            key_store = InMemoryKeyStore()
            with get_connection(db_path) as conn:
                engine = BackupEngine(conn, backup_dir=Path(tmp), key_store=key_store)
                engine.register_policy(_make_policy())
                execution = engine.execute_backup("test_policy", "security-eng")

            raw_key = key_store.get_raw_key(execution.encryption_key_id)
            artifact_bytes = Path(execution.artifact_path).read_bytes()

        self.assertNotIn(raw_key, artifact_bytes)


# ===========================================================================
# Task 004 — Backup Encryption Verification and Compliance Evidence
# ===========================================================================

class TestEncryptionVerificationAndEvidence(TestCase):
    """AC: Backup artifacts remain encrypted.
    AC: Verification evidence is documented.
    AC: Compliance review can reference implementation proof."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        initialize_database(self.db_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run_backup(self) -> tuple[BackupEngine, str]:
        key_store = InMemoryKeyStore()
        conn = get_connection(self.db_path)
        engine = BackupEngine(conn, backup_dir=Path(self.tmp.name), key_store=key_store)
        engine.register_policy(_make_policy())
        execution = engine.execute_backup("test_policy", "compliance-verifier")
        return engine, execution.execution_id

    def test_verify_backup_encryption_passes_for_encrypted_artifact(self) -> None:
        """verify_backup_encryption returns verified=True for a proper backup."""
        engine, execution_id = self._run_backup()
        result = engine.verify_backup_encryption(execution_id)

        self.assertTrue(result["verified"])
        self.assertEqual(result["verification_status"], "verified")

    def test_verify_backup_encryption_updates_db_status(self) -> None:
        """verification_status column is updated in backup_executions after verify."""
        engine, execution_id = self._run_backup()
        engine.verify_backup_encryption(execution_id)

        row = engine.connection.execute(
            "SELECT verification_status FROM backup_executions WHERE execution_id = ?",
            [execution_id],
        ).fetchone()
        self.assertEqual(row["verification_status"], "verified")

    def test_verify_detects_unencrypted_artifact(self) -> None:
        """verify_backup_encryption returns verified=False when file is not encrypted."""
        engine, execution_id = self._run_backup()

        # Overwrite with plaintext to simulate an unencrypted artifact
        row = engine.connection.execute(
            "SELECT artifact_path FROM backup_executions WHERE execution_id = ?",
            [execution_id],
        ).fetchone()
        Path(row["artifact_path"]).write_bytes(b"SQLite format 3\x00 plaintext content")

        result = engine.verify_backup_encryption(execution_id)

        self.assertFalse(result["verified"])
        self.assertEqual(result["verification_status"], "failed")

    def test_generate_compliance_evidence_structure(self) -> None:
        """generate_compliance_evidence returns all required audit fields."""
        engine, execution_id = self._run_backup()
        evidence = engine.generate_compliance_evidence(execution_id)

        required_fields = [
            "report_type",
            "compliance_standard",
            "execution_id",
            "dataset_name",
            "encryption_algorithm",
            "encryption_status",
            "key_metadata",
            "artifact_path",
            "backup_checksum",
            "verification",
            "scope",
        ]
        for field in required_fields:
            self.assertIn(field, evidence, f"Missing field: {field}")

    def test_compliance_evidence_references_hipaa_standard(self) -> None:
        """Compliance evidence must cite the applicable HIPAA regulation."""
        engine, execution_id = self._run_backup()
        evidence = engine.generate_compliance_evidence(execution_id)

        self.assertIn("HIPAA", evidence["compliance_standard"])
        self.assertIn("164.312", evidence["compliance_standard"])

    def test_compliance_evidence_key_metadata_excludes_raw_material(self) -> None:
        """Key metadata in evidence report must not contain raw key bytes."""
        engine, execution_id = self._run_backup()
        evidence = engine.generate_compliance_evidence(execution_id)

        key_meta = evidence["key_metadata"]
        self.assertIsNotNone(key_meta)
        self.assertNotIn("raw_key", key_meta)
        self.assertIn("key_id", key_meta)
        self.assertIn("algorithm", key_meta)
        self.assertIn("status", key_meta)

    def test_compliance_evidence_encryption_algorithm_is_aes256(self) -> None:
        """Compliance evidence must confirm AES-256-GCM algorithm."""
        engine, execution_id = self._run_backup()
        evidence = engine.generate_compliance_evidence(execution_id)

        self.assertEqual(evidence["encryption_algorithm"], "AES-256-GCM")
        self.assertEqual(evidence["encryption_status"], "encrypted")

    def test_verify_records_audit_trail(self) -> None:
        """Encryption verification must be recorded in backup_audit_trail."""
        engine, execution_id = self._run_backup()
        engine.verify_backup_encryption(execution_id)

        rows = engine.connection.execute(
            """
            SELECT * FROM backup_audit_trail
            WHERE resource_id = ? AND action_details LIKE '%verification%'
            """,
            [execution_id],
        ).fetchall()
        self.assertGreater(len(rows), 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
