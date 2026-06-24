"""
EP-007 US-079: MFA Support (TOTP)

task_079_001 — Policy: Staff/Admin require TOTP MFA; enrollment and recovery defined.
task_079_002 — Enrollment: TOTP secret generation, provisioning URI, code verification.
task_079_003 — Recovery: single-use backup codes with secure hashed storage.
task_079_004 — Enforcement: policy gate blocks login until MFA setup and challenge complete.

TOTP algorithm (RFC 6238 / RFC 4226):
  Secret  — 160-bit random, base32-encoded (20 bytes → 32 base32 chars).
  Counter — floor(Unix time / TOTP_PERIOD).  Period is 30 seconds.
  HOTP    — HMAC-SHA1(key, 8-byte big-endian counter), dynamic truncation,
            mod 10^TOTP_DIGITS.
  Drift   — ±1 counter step (90-second window) accepted to handle clock skew.

Backup codes (task_079_003):
  10 single-use codes, 8 characters each (alphanumeric).
  Only the SHA-256 hash is stored — plaintext is returned once at generation
  time and never retained.  A second redemption attempt of any code is denied.

Secrets policy (task_079_001):
  MFA secrets are excluded from all log output and API responses.
  The provisioning URI uses only the base32 secret — no raw bytes are exposed.
"""
from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import logging
import secrets
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# task_079_001: MFA policy constants
# ---------------------------------------------------------------------------

MFA_REQUIRED_ROLES: frozenset[str] = frozenset({"staff", "admin"})
MFA_EXEMPT_ROLES: frozenset[str] = frozenset({"patient"})

TOTP_PERIOD: int = 30          # seconds per counter step (RFC 6238 default)
TOTP_DIGITS: int = 6           # code length
TOTP_ALGORITHM: str = "SHA1"   # HMAC algorithm
TOTP_DRIFT: int = 1            # accepted ± counter steps for clock skew
TOTP_SECRET_BYTES: int = 20    # 160-bit secret (RFC 4226 recommended)
TOTP_ISSUER: str = "PropelIQ"

BACKUP_CODE_COUNT: int = 10
BACKUP_CODE_LENGTH: int = 8    # characters (alphanumeric)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MfaError(Exception):
    """Base for all MFA-related errors."""


class MfaNotEnrolledError(MfaError):
    """Raised when MFA verification is attempted without enrollment."""


class MfaAlreadyEnrolledError(MfaError):
    """Raised when re-enrollment is attempted on an already-enrolled user."""


class MfaCodeInvalidError(MfaError):
    """Raised when a TOTP or backup code is invalid or expired."""


class MfaBackupCodeConsumedError(MfaError):
    """Raised when a backup code has already been used."""


class MfaLoginBlockedError(MfaError):
    """Raised when policy requires MFA but setup or challenge is incomplete."""


# ---------------------------------------------------------------------------
# task_079_002: TOTP engine (RFC 6238, stdlib-only)
# ---------------------------------------------------------------------------


def _hotp(key: bytes, counter: int) -> str:
    """Compute an HOTP value for *counter* using HMAC-SHA1.

    Returns a zero-padded ``TOTP_DIGITS``-digit string.
    """
    msg = struct.pack(">Q", counter)
    mac = _hmac.new(key, msg, hashlib.sha1).digest()
    offset = mac[19] & 0x0F
    code_int = struct.unpack(">I", mac[offset: offset + 4])[0] & 0x7FFFFFFF
    return str(code_int % (10 ** TOTP_DIGITS)).zfill(TOTP_DIGITS)


def _totp_key_bytes(secret_b32: str) -> bytes:
    """Decode a base32 secret string into raw key bytes."""
    return base64.b32decode(secret_b32.upper().replace(" ", ""))


def generate_totp_secret() -> str:
    """Generate a cryptographically random TOTP secret (base32-encoded)."""
    raw = secrets.token_bytes(TOTP_SECRET_BYTES)
    return base64.b32encode(raw).decode("ascii")


def get_totp_code(secret_b32: str, timestamp: float | None = None) -> str:
    """Return the current TOTP code for *secret_b32*.

    Useful for test fixtures that need a known-valid code.
    """
    ts = timestamp if timestamp is not None else time.time()
    counter = int(ts) // TOTP_PERIOD
    key = _totp_key_bytes(secret_b32)
    return _hotp(key, counter)


def verify_totp_code(secret_b32: str, code: str, timestamp: float | None = None) -> bool:
    """Return True if *code* is valid for *secret_b32* within the drift window.

    Accepts ``TOTP_DRIFT`` counter steps in either direction to accommodate
    clock skew between authenticator apps and the server.
    """
    if not code or not code.strip().isdigit():
        return False
    ts = timestamp if timestamp is not None else time.time()
    counter = int(ts) // TOTP_PERIOD
    key = _totp_key_bytes(secret_b32)
    candidate = code.strip().zfill(TOTP_DIGITS)
    for drift in range(-TOTP_DRIFT, TOTP_DRIFT + 1):
        if _hmac.compare_digest(_hotp(key, counter + drift), candidate):
            return True
    return False


def build_provisioning_uri(secret_b32: str, account_label: str, issuer: str = TOTP_ISSUER) -> str:
    """Return an ``otpauth://totp/`` URI suitable for QR-code generation.

    The URI conforms to the Google Authenticator Key URI format.
    No raw key bytes appear in the URI — only the base32 secret.
    """
    label = account_label.replace(" ", "%20")
    return (
        f"otpauth://totp/{issuer}:{label}"
        f"?secret={secret_b32}"
        f"&issuer={issuer}"
        f"&algorithm={TOTP_ALGORITHM}"
        f"&digits={TOTP_DIGITS}"
        f"&period={TOTP_PERIOD}"
    )


# ---------------------------------------------------------------------------
# task_079_002: Enrollment store and service
# ---------------------------------------------------------------------------


@dataclass
class MfaEnrollmentRecord:
    """Persisted MFA enrollment state for a single user.

    Fields
    ------
    user_id       Opaque user account identifier.
    secret_b32    Base32 TOTP secret — stored server-side only, never returned
                  in API responses after initial enrollment (task_079_004).
    enrolled_at   UTC ISO-8601 timestamp of successful enrollment confirmation.
    is_enrolled   True once the user has confirmed a valid TOTP code.
    """

    user_id: str
    secret_b32: str
    enrolled_at: str | None = None
    is_enrolled: bool = False


class MfaEnrollmentStore:
    """In-memory store for TOTP enrollment records.

    Production deployments should replace this with a persistent, encrypted
    store (e.g. encrypted column in the user database).
    """

    def __init__(self) -> None:
        self._records: dict[str, MfaEnrollmentRecord] = {}

    def get(self, user_id: str) -> MfaEnrollmentRecord | None:
        return self._records.get(user_id)

    def upsert(self, record: MfaEnrollmentRecord) -> None:
        self._records[user_id := record.user_id] = record

    def delete(self, user_id: str) -> None:
        self._records.pop(user_id, None)

    def is_enrolled(self, user_id: str) -> bool:
        rec = self._records.get(user_id)
        return rec is not None and rec.is_enrolled


class MfaEnrollmentService:
    """TOTP enrollment and verification service (task_079_002).

    ``begin_enrollment`` — generates a new secret and provisioning URI.
    ``confirm_enrollment`` — verifies the first TOTP code and marks user enrolled.
    ``verify_login`` — verifies a TOTP code during a login challenge.
    """

    def __init__(self, store: MfaEnrollmentStore | None = None) -> None:
        self._store = store or MfaEnrollmentStore()

    def begin_enrollment(self, user_id: str, account_label: str) -> dict[str, Any]:
        """Start TOTP enrollment.  Returns provisioning data; never includes raw bytes.

        If the user already has a completed enrollment, raises
        ``MfaAlreadyEnrolledError``.  Pending (unconfirmed) enrollments are
        replaced so the user can restart setup.
        """
        existing = self._store.get(user_id)
        if existing and existing.is_enrolled:
            raise MfaAlreadyEnrolledError(
                f"User '{user_id}' is already enrolled in MFA."
            )
        secret = generate_totp_secret()
        record = MfaEnrollmentRecord(user_id=user_id, secret_b32=secret)
        self._store.upsert(record)
        uri = build_provisioning_uri(secret, account_label)
        logger.info("MFA_ENROLL_BEGIN | user_id=%s", user_id)
        return {
            "user_id": user_id,
            "provisioning_uri": uri,
            "algorithm": TOTP_ALGORITHM,
            "digits": TOTP_DIGITS,
            "period": TOTP_PERIOD,
            "issuer": TOTP_ISSUER,
            # secret_b32 returned ONLY during enrollment setup so the user
            # can configure their authenticator app.  Not re-exposed after
            # confirm_enrollment completes.
            "secret_b32": secret,
        }

    def confirm_enrollment(
        self,
        user_id: str,
        code: str,
        timestamp: float | None = None,
    ) -> bool:
        """Confirm enrollment by verifying the first TOTP code.

        Returns ``True`` on success; raises on failure.
        """
        record = self._store.get(user_id)
        if record is None:
            raise MfaNotEnrolledError(f"No pending enrollment found for user '{user_id}'.")
        if not verify_totp_code(record.secret_b32, code, timestamp):
            raise MfaCodeInvalidError("Enrollment confirmation failed: invalid TOTP code.")
        record.is_enrolled = True
        record.enrolled_at = datetime.now(timezone.utc).isoformat()
        # Clear the secret from the returned data — future access requires
        # the stored record only.
        self._store.upsert(record)
        logger.info("MFA_ENROLL_CONFIRMED | user_id=%s", user_id)
        return True

    def verify_login(
        self,
        user_id: str,
        code: str,
        timestamp: float | None = None,
    ) -> bool:
        """Verify a TOTP code during login (post-password challenge).

        Returns ``True`` on success; raises ``MfaNotEnrolledError`` or
        ``MfaCodeInvalidError`` on failure.
        """
        record = self._store.get(user_id)
        if record is None or not record.is_enrolled:
            raise MfaNotEnrolledError(
                f"User '{user_id}' does not have MFA enrolled."
            )
        if not verify_totp_code(record.secret_b32, code, timestamp):
            logger.warning("MFA_VERIFY_FAILED | user_id=%s", user_id)
            raise MfaCodeInvalidError(
                "Invalid or expired authentication code. Please try again."
            )
        logger.info("MFA_VERIFY_SUCCESS | user_id=%s", user_id)
        return True

    def is_enrolled(self, user_id: str) -> bool:
        return self._store.is_enrolled(user_id)

    def get_enrollment(self, user_id: str) -> MfaEnrollmentRecord | None:
        return self._store.get(user_id)

    def reset_enrollment(self, user_id: str) -> None:
        """Remove enrollment record (admin-initiated recovery, task_079_003)."""
        self._store.delete(user_id)
        logger.info("MFA_ENROLL_RESET | user_id=%s", user_id)


# ---------------------------------------------------------------------------
# task_079_003: Backup codes — single-use, hashed storage
# ---------------------------------------------------------------------------


def _hash_backup_code(plaintext: str) -> str:
    """Return SHA-256 hex digest of a backup code for secure storage."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


@dataclass
class BackupCode:
    """A single backup code record.

    Only the SHA-256 hash is stored.  The plaintext is returned once at
    generation time and is never reconstructable from this record.
    """

    code_hash: str
    used: bool = False
    used_at: str | None = None


class MfaBackupCodeStore:
    """In-memory store for per-user backup code sets (task_079_003)."""

    def __init__(self) -> None:
        # Maps user_id → list of BackupCode records
        self._codes: dict[str, list[BackupCode]] = {}

    def set_codes(self, user_id: str, codes: list[BackupCode]) -> None:
        self._codes[user_id] = codes

    def get_codes(self, user_id: str) -> list[BackupCode]:
        return list(self._codes.get(user_id, []))

    def has_codes(self, user_id: str) -> bool:
        return bool(self._codes.get(user_id))

    def mark_used(self, user_id: str, code_hash: str) -> None:
        for code in self._codes.get(user_id, []):
            if code.code_hash == code_hash:
                code.used = True
                code.used_at = datetime.now(timezone.utc).isoformat()


class MfaBackupCodeService:
    """Backup code generation and redemption (task_079_003).

    Codes are single-use: redeeming a code marks it consumed.  Any subsequent
    redemption of the same code is rejected and logged as a security event.
    """

    def __init__(self, store: MfaBackupCodeStore | None = None) -> None:
        self._store = store or MfaBackupCodeStore()

    @staticmethod
    def _generate_code() -> str:
        """Generate one random 8-character alphanumeric backup code."""
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # omit O, I, 0, 1 for legibility
        return "".join(secrets.choice(alphabet) for _ in range(BACKUP_CODE_LENGTH))

    def generate(self, user_id: str) -> list[str]:
        """Generate a new set of backup codes for *user_id*.

        Returns the plaintext codes exactly once — they are not stored in
        plaintext.  The hashed versions are saved in the backup code store.
        Any previous codes for the user are invalidated.
        """
        plaintexts = [self._generate_code() for _ in range(BACKUP_CODE_COUNT)]
        records = [BackupCode(code_hash=_hash_backup_code(p)) for p in plaintexts]
        self._store.set_codes(user_id, records)
        logger.info("MFA_BACKUP_CODES_GENERATED | user_id=%s count=%d", user_id, BACKUP_CODE_COUNT)
        return plaintexts

    def redeem(self, user_id: str, plaintext_code: str) -> bool:
        """Redeem a backup code for *user_id*.

        Raises ``MfaBackupCodeConsumedError`` when the code has already been
        used; raises ``MfaCodeInvalidError`` when the code is not found.

        Returns ``True`` on success and marks the code as consumed.
        """
        target_hash = _hash_backup_code(plaintext_code.strip().upper())
        codes = self._store.get_codes(user_id)
        for code in codes:
            if _hmac.compare_digest(code.code_hash, target_hash):
                if code.used:
                    logger.warning(
                        "MFA_BACKUP_CODE_REUSE_ATTEMPT | user_id=%s", user_id
                    )
                    raise MfaBackupCodeConsumedError(
                        "This backup code has already been used and cannot be reused."
                    )
                self._store.mark_used(user_id, target_hash)
                logger.info("MFA_BACKUP_CODE_REDEEMED | user_id=%s", user_id)
                return True
        raise MfaCodeInvalidError("Invalid backup code.")

    def remaining_count(self, user_id: str) -> int:
        """Return the number of unused backup codes remaining for *user_id*."""
        return sum(1 for c in self._store.get_codes(user_id) if not c.used)

    def has_any_codes(self, user_id: str) -> bool:
        return self._store.has_codes(user_id)


# ---------------------------------------------------------------------------
# task_079_004: MFA policy enforcer — login gate
# ---------------------------------------------------------------------------


class MfaPolicyEnforcer:
    """Role-based MFA enforcement gate (task_079_001 / task_079_004).

    ``check_login_allowed`` must be called after password verification and
    before issuing a session token.  It enforces:
    1. Roles in ``MFA_REQUIRED_ROLES`` must be enrolled.
    2. Enrolled users must complete the TOTP (or backup code) challenge.

    The session-level MFA challenge completion is tracked via
    ``record_challenge_passed`` / ``is_challenge_passed`` so the enforcer
    can distinguish "enrolled but not yet challenged this session" from
    "enrolled and challenge completed".
    """

    def __init__(self, enrollment_service: MfaEnrollmentService | None = None) -> None:
        self._enrollment = enrollment_service or MfaEnrollmentService()
        # Maps user_id → challenge completion flag for the current session.
        # In production, this state lives in the session store/token claims.
        self._challenge_passed: dict[str, bool] = {}

    @staticmethod
    def requires_mfa(role: str) -> bool:
        """Return True when *role* is subject to the MFA enforcement policy."""
        return role in MFA_REQUIRED_ROLES

    def is_enrolled(self, user_id: str) -> bool:
        return self._enrollment.is_enrolled(user_id)

    def record_challenge_passed(self, user_id: str) -> None:
        """Mark that *user_id* has successfully completed the MFA challenge."""
        self._challenge_passed[user_id] = True

    def is_challenge_passed(self, user_id: str) -> bool:
        return self._challenge_passed.get(user_id, False)

    def clear_challenge(self, user_id: str) -> None:
        """Clear the challenge state (e.g. on logout or session expiry)."""
        self._challenge_passed.pop(user_id, None)

    def check_login_allowed(
        self,
        user_id: str,
        role: str,
    ) -> tuple[bool, str]:
        """Return ``(True, "")`` when the user may receive a session token.

        Returns ``(False, reason)`` in two blocking cases:
        - MFA_SETUP_REQUIRED    — role requires MFA but user is not enrolled.
        - MFA_CHALLENGE_REQUIRED — enrolled but TOTP challenge not yet passed.
        """
        if not self.requires_mfa(role):
            return True, ""

        if not self.is_enrolled(user_id):
            return (
                False,
                "MFA_SETUP_REQUIRED: MFA enrollment is required for this account. "
                "Please enroll using an authenticator app before logging in.",
            )

        if not self.is_challenge_passed(user_id):
            return (
                False,
                "MFA_CHALLENGE_REQUIRED: Please complete the MFA verification step.",
            )

        return True, ""

    def status(self, user_id: str, role: str) -> dict[str, Any]:
        """Return a non-sensitive MFA status summary for *user_id*."""
        return {
            "user_id": user_id,
            "role": role,
            "mfa_required": self.requires_mfa(role),
            "enrolled": self.is_enrolled(user_id),
            "challenge_passed": self.is_challenge_passed(user_id),
        }


# ---------------------------------------------------------------------------
# Module-level singletons (single-process convenience)
# ---------------------------------------------------------------------------

_MFA_ENROLLMENT_STORE: MfaEnrollmentStore = MfaEnrollmentStore()
_MFA_ENROLLMENT_SERVICE: MfaEnrollmentService = MfaEnrollmentService(_MFA_ENROLLMENT_STORE)
_MFA_BACKUP_STORE: MfaBackupCodeStore = MfaBackupCodeStore()
_MFA_BACKUP_SERVICE: MfaBackupCodeService = MfaBackupCodeService(_MFA_BACKUP_STORE)
_MFA_POLICY: MfaPolicyEnforcer = MfaPolicyEnforcer(_MFA_ENROLLMENT_SERVICE)
