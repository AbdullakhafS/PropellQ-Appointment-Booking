from __future__ import annotations

import os
import struct
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ---------------------------------------------------------------------------
# Wire format for encrypted payloads stored on disk
#
#   [16 bytes]  magic marker
#   [4 bytes BE] key_id length (uint32)
#   [N bytes]   key_id (UTF-8)
#   [12 bytes]  nonce (AES-GCM 96-bit)
#   [rest]      ciphertext + GCM authentication tag
#
# Key material is NEVER included in the payload.  The key_id is a pointer
# that callers use to look up the key from the key store.
# ---------------------------------------------------------------------------

_MAGIC = b"PROPELIQ_ENC_V1\n"
_NONCE_SIZE = 12  # 96-bit nonce recommended for AES-GCM
_KEY_SIZE = 32    # 256-bit key for AES-256-GCM


class KeyStatus(str, Enum):
    ACTIVE = "active"
    ROTATED = "rotated"
    REVOKED = "revoked"


@dataclass(frozen=True)
class EncryptionKeyMetadata:
    """Metadata about an encryption key.  Raw key material is never stored here."""

    key_id: str
    algorithm: str
    created_at: datetime
    rotated_at: datetime | None
    status: KeyStatus


@dataclass(frozen=True)
class EncryptedPayload:
    """Serializable encrypted payload.  Key material is NOT included."""

    key_id: str
    nonce: bytes
    ciphertext: bytes

    def to_bytes(self) -> bytes:
        """Serialize to the PROPELIQ binary wire format."""
        key_id_bytes = self.key_id.encode("utf-8")
        return (
            _MAGIC
            + struct.pack(">I", len(key_id_bytes))
            + key_id_bytes
            + self.nonce
            + self.ciphertext
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "EncryptedPayload":
        """Deserialize from the PROPELIQ binary wire format."""
        if not data.startswith(_MAGIC):
            raise ValueError("Not a valid PROPELIQ encrypted payload")
        offset = len(_MAGIC)
        (key_id_len,) = struct.unpack_from(">I", data, offset)
        offset += 4
        key_id = data[offset: offset + key_id_len].decode("utf-8")
        offset += key_id_len
        nonce = data[offset: offset + _NONCE_SIZE]
        offset += _NONCE_SIZE
        ciphertext = data[offset:]
        return cls(key_id=key_id, nonce=nonce, ciphertext=ciphertext)


class KeyStore:
    """Abstract key store interface.

    Production implementations should back this with an HSM or cloud KMS
    (AWS KMS, Azure Key Vault, GCP Cloud KMS).  Raw key material must never
    leave the key store boundary in production deployments.
    """

    def generate_key(self) -> EncryptionKeyMetadata:
        raise NotImplementedError

    def get_active_key_id(self) -> str:
        raise NotImplementedError

    def get_raw_key(self, key_id: str) -> bytes:
        """Return raw key bytes for the given key_id (32 bytes for AES-256)."""
        raise NotImplementedError

    def rotate_key(self) -> EncryptionKeyMetadata:
        """Generate a new active key.  Old key remains available for decryption."""
        raise NotImplementedError

    def get_key_metadata(self, key_id: str) -> EncryptionKeyMetadata:
        raise NotImplementedError

    def list_key_metadata(self) -> list[EncryptionKeyMetadata]:
        raise NotImplementedError


class InMemoryKeyStore(KeyStore):
    """In-memory key store for development and testing.

    Replace with an HSM/KMS-backed implementation in production.
    Raw key material is stored only in the private ``_keys`` dict and is
    never co-located with encrypted ciphertext.
    """

    def __init__(self) -> None:
        self._keys: dict[str, bytes] = {}
        self._metadata: dict[str, EncryptionKeyMetadata] = {}
        self._active_key_id: str | None = None

    def generate_key(self) -> EncryptionKeyMetadata:
        key_id = uuid.uuid4().hex
        raw_key = AESGCM.generate_key(bit_length=256)
        now = datetime.now(tz=timezone.utc)
        meta = EncryptionKeyMetadata(
            key_id=key_id,
            algorithm="AES-256-GCM",
            created_at=now,
            rotated_at=None,
            status=KeyStatus.ACTIVE,
        )
        self._keys[key_id] = raw_key
        self._metadata[key_id] = meta
        if self._active_key_id is None:
            self._active_key_id = key_id
        return meta

    def get_active_key_id(self) -> str:
        if self._active_key_id is None:
            meta = self.generate_key()
            self._active_key_id = meta.key_id
        return self._active_key_id

    def get_raw_key(self, key_id: str) -> bytes:
        if key_id not in self._keys:
            raise LookupError(f"Encryption key not found: {key_id}")
        return self._keys[key_id]

    def rotate_key(self) -> EncryptionKeyMetadata:
        """Mark the current active key as ROTATED and promote a new key.

        The rotated key is retained so that previously encrypted payloads
        can still be decrypted.  Only the active key ID changes.
        """
        now = datetime.now(tz=timezone.utc)
        if self._active_key_id is not None:
            old_meta = self._metadata[self._active_key_id]
            self._metadata[self._active_key_id] = EncryptionKeyMetadata(
                key_id=old_meta.key_id,
                algorithm=old_meta.algorithm,
                created_at=old_meta.created_at,
                rotated_at=now,
                status=KeyStatus.ROTATED,
            )
        new_key_id = uuid.uuid4().hex
        new_raw_key = AESGCM.generate_key(bit_length=256)
        new_meta = EncryptionKeyMetadata(
            key_id=new_key_id,
            algorithm="AES-256-GCM",
            created_at=now,
            rotated_at=None,
            status=KeyStatus.ACTIVE,
        )
        self._keys[new_key_id] = new_raw_key
        self._metadata[new_key_id] = new_meta
        self._active_key_id = new_key_id
        return new_meta

    def get_key_metadata(self, key_id: str) -> EncryptionKeyMetadata:
        if key_id not in self._metadata:
            raise LookupError(f"Key metadata not found: {key_id}")
        return self._metadata[key_id]

    def list_key_metadata(self) -> list[EncryptionKeyMetadata]:
        return list(self._metadata.values())


class EncryptionEngine:
    """AES-256-GCM encryption engine.

    Key material is retrieved from the key store only at encrypt/decrypt time
    and is never persisted alongside ciphertext.
    """

    ALGORITHM = "AES-256-GCM"

    def __init__(self, key_store: KeyStore) -> None:
        self.key_store = key_store

    def encrypt(
        self,
        plaintext: bytes,
        associated_data: bytes | None = None,
    ) -> EncryptedPayload:
        """Encrypt *plaintext* with the current active key."""
        key_id = self.key_store.get_active_key_id()
        raw_key = self.key_store.get_raw_key(key_id)
        nonce = os.urandom(_NONCE_SIZE)
        aesgcm = AESGCM(raw_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        return EncryptedPayload(key_id=key_id, nonce=nonce, ciphertext=ciphertext)

    def decrypt(
        self,
        payload: EncryptedPayload,
        associated_data: bytes | None = None,
    ) -> bytes:
        """Decrypt *payload* using the key referenced in the payload."""
        raw_key = self.key_store.get_raw_key(payload.key_id)
        aesgcm = AESGCM(raw_key)
        return aesgcm.decrypt(payload.nonce, payload.ciphertext, associated_data)

    def encrypt_file(self, path: "os.PathLike[str]") -> str:
        """Encrypt a file in-place.  Returns the key_id used.

        The plaintext file is overwritten with PROPELIQ binary format.
        Key material is never written to disk.
        """
        import pathlib

        file_path = pathlib.Path(path)
        plaintext = file_path.read_bytes()
        payload = self.encrypt(plaintext)
        file_path.write_bytes(payload.to_bytes())
        return payload.key_id

    def decrypt_file(self, path: "os.PathLike[str]") -> bytes:
        """Decrypt a PROPELIQ-encrypted file.  Returns plaintext bytes."""
        import pathlib

        data = pathlib.Path(path).read_bytes()
        payload = EncryptedPayload.from_bytes(data)
        return self.decrypt(payload)

    def is_encrypted_file(self, path: "os.PathLike[str]") -> bool:
        """Return True if the file starts with the PROPELIQ magic marker."""
        import pathlib

        file_path = pathlib.Path(path)
        if not file_path.exists() or file_path.stat().st_size < len(_MAGIC):
            return False
        return file_path.read_bytes()[: len(_MAGIC)] == _MAGIC

    def get_file_key_id(self, path: "os.PathLike[str]") -> str | None:
        """Extract key_id from an encrypted file without decrypting the content."""
        import pathlib

        try:
            data = pathlib.Path(path).read_bytes()
            payload = EncryptedPayload.from_bytes(data)
            return payload.key_id
        except (ValueError, struct.error):
            return None
