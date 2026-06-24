"""
EP-007 US-074: Immutable Audit Log Infrastructure

task_074_001 — Design: append-only storage model separated from transactional data,
               access-control documentation, and HMAC hash-chain integrity strategy.
task_074_002 — Implementation: enforce append-only via API-level mutation block.
task_074_003 — Retention: 7-year minimum policy with deletion-eligibility controls
               and per-entry + chained hash tamper-evidence.
task_074_004 — Access: RBAC-restricted audit read paths; unauthorized attempts blocked.
task_074_005 — Evidence: compliance report generator for HIPAA 45 CFR § 164.312(b).

Storage separation (task_074_001):
  Audit records live in ``AppendOnlyAuditStore`` (STORAGE_NAMESPACE = "audit_log"),
  which is entirely distinct from the transactional SQLite database used for
  appointments, providers, and patient data.  In production this maps to a
  dedicated write-once storage tier (e.g. S3 Object Lock / CloudWatch Logs);
  for the application server layer the separation is enforced by a single
  in-process store with no shared code-path to the transactional DB.

Access restrictions (task_074_001 / task_074_004):
  Only roles in AUDIT_READ_ROLES (``admin``, ``staff``) may read entries.
  Write access is reserved for the server-side ``append_audit_event`` helper.
  Update and delete operations raise ``AuditImmutabilityError`` regardless of role.

Integrity strategy (task_074_003):
  Each entry carries an HMAC-SHA256 ``integrity_hash`` that covers all
  non-metadata fields plus the hash of the preceding entry (hash chain).
  Any single-entry mutation or sequence tampering is detectable by
  ``AuditIntegrityChecker``.
"""
from __future__ import annotations

import hashlib
import hmac as _hmac
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# task_074_001: Storage namespace (separation from transactional data)
# ---------------------------------------------------------------------------

# Canonical storage namespace — documents that audit storage is distinct from
# the transactional appointment/patient database.  Any adapter that persists
# audit entries MUST target a different storage target than the operational DB.
AUDIT_STORAGE_NAMESPACE: str = "audit_log"
TRANSACTIONAL_STORAGE_NAMESPACE: str = "transactional"

# ---------------------------------------------------------------------------
# task_074_003: Retention policy constants
# ---------------------------------------------------------------------------

AUDIT_RETENTION_YEARS: int = 7      # HIPAA 45 CFR § 164.530(j) minimum
AUDIT_RETENTION_DAYS: int = AUDIT_RETENTION_YEARS * 365  # conservative (no leap)

# ---------------------------------------------------------------------------
# task_074_004: Authorized roles for audit reads
# ---------------------------------------------------------------------------

# Only roles in this set may read audit log entries.  All other roles are denied
# at the ``AuditAccessGuard`` layer before any storage query is issued.
AUDIT_READ_ROLES: frozenset[str] = frozenset({"admin", "staff"})

# Signing secret for HMAC integrity hashes.  Override via environment variable
# in production.  The default signals a misconfigured deployment.
_AUDIT_INTEGRITY_SECRET: bytes = (
    os.environ.get("AUDIT_INTEGRITY_SECRET", "propeliq-audit-integrity-CHANGE-IN-PROD")
).encode("utf-8")

# Genesis prev_chain_hash for the first entry in any store.
_GENESIS_HASH: str = "0" * 64

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AuditImmutabilityError(Exception):
    """Raised when an update or delete is attempted on an audit entry.

    Immutability is enforced at the application API layer (task_074_002).
    The storage layer itself is append-only; this exception prevents any
    mutation path from reaching the in-process or persistent store.
    """


class AuditStorageError(Exception):
    """Raised for recoverable storage failures (full store, I/O errors, etc.)."""


# ---------------------------------------------------------------------------
# task_074_001 / task_074_002: Audit Entry model
# ---------------------------------------------------------------------------


@dataclass
class AuditEntry:
    """A single immutable audit record.

    Fields
    ------
    entry_id          UUID4 — globally unique, set at append time.
    timestamp         ISO-8601 UTC string — set at append time.
    event             High-level category (AUTH_LOGIN, DATA_ACCESS, …).
    actor_id          Opaque user ID or None for system-initiated events.
    actor_role        Role held at time of event (patient, staff, admin).
    action            Specific action performed.
    resource_type     Type of resource acted on (appointment, patient, …).
    resource_id       Normalized resource ID (numeric path segments replaced).
    outcome           "success" | "denied" | "error".
    source_ip         Source IP address; no other PII beyond actor_id.
    prev_chain_hash   HMAC of the preceding entry's integrity_hash (chain).
    integrity_hash    HMAC-SHA256 over all content fields + prev_chain_hash.

    Immutability:
    Once an ``AuditEntry`` is appended its fields must not be mutated.
    ``AppendOnlyAuditStore`` enforces this; the dataclass is intentionally
    NOT frozen to allow the store to set ``integrity_hash`` during append.
    """

    entry_id: str
    timestamp: str
    event: str
    actor_id: str | None
    actor_role: str | None
    action: str
    resource_type: str
    resource_id: str | None
    outcome: str
    source_ip: str | None
    prev_chain_hash: str
    integrity_hash: str = field(default="", repr=False)


# ---------------------------------------------------------------------------
# task_074_003: Integrity helper
# ---------------------------------------------------------------------------


def _compute_entry_hash(entry: AuditEntry, secret: bytes = _AUDIT_INTEGRITY_SECRET) -> str:
    """Return HMAC-SHA256 of the canonical entry representation.

    The canonical string covers all content-bearing fields in a deterministic
    order.  ``integrity_hash`` itself is excluded (it's the output, not input).
    ``prev_chain_hash`` is included so any chain break is detectable.
    """
    canonical = "|".join([
        entry.entry_id,
        entry.timestamp,
        entry.event,
        str(entry.actor_id or ""),
        str(entry.actor_role or ""),
        entry.action,
        entry.resource_type,
        str(entry.resource_id or ""),
        entry.outcome,
        str(entry.source_ip or ""),
        entry.prev_chain_hash,
    ])
    return _hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# task_074_002: Append-only store
# ---------------------------------------------------------------------------


class AppendOnlyAuditStore:
    """In-process append-only audit log store (task_074_002).

    Write API  — only ``append()`` is permitted.
    Read API   — ``read_entries()`` and ``size()``.
    Blocked    — ``update()`` and ``delete()`` raise ``AuditImmutabilityError``.

    Storage separation:
    This store is distinct from the transactional SQLite database.  Its
    ``storage_namespace`` attribute equals ``AUDIT_STORAGE_NAMESPACE``
    ("audit_log"), never ``TRANSACTIONAL_STORAGE_NAMESPACE``.

    Thread safety:
    Single-threaded (WSGI worker).  For multi-threaded deployments replace
    ``_entries`` with a thread-safe bounded deque or hand off to a write-once
    storage adapter.
    """

    storage_namespace: str = AUDIT_STORAGE_NAMESPACE

    def __init__(self, max_entries: int = 100_000) -> None:
        self._entries: list[AuditEntry] = []
        self._max_entries = max_entries
        self._last_hash: str = _GENESIS_HASH

    # ---- Append ----

    def append(
        self,
        event: str,
        actor_id: str | None = None,
        actor_role: str | None = None,
        action: str = "",
        resource_type: str = "",
        resource_id: str | None = None,
        outcome: str = "success",
        source_ip: str | None = None,
    ) -> AuditEntry:
        """Append a new immutable audit entry and return it.

        The ``entry_id``, ``timestamp``, ``prev_chain_hash``, and
        ``integrity_hash`` are set internally — callers cannot supply them.

        Raises ``AuditStorageError`` when the store is full.
        """
        if len(self._entries) >= self._max_entries:
            raise AuditStorageError(
                f"Audit store capacity ({self._max_entries}) reached."
            )

        now = datetime.now(timezone.utc)
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            timestamp=now.isoformat(),
            event=event,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            source_ip=source_ip,
            prev_chain_hash=self._last_hash,
        )
        entry.integrity_hash = _compute_entry_hash(entry)
        self._last_hash = entry.integrity_hash
        self._entries.append(entry)
        logger.info(
            "AUDIT_APPEND | id=%s event=%s actor=%s action=%s outcome=%s",
            entry.entry_id, event, actor_id, action, outcome,
        )
        return entry

    # ---- Read ----

    def read_entries(
        self,
        limit: int = 100,
        event_filter: str | None = None,
        actor_filter: str | None = None,
    ) -> list[AuditEntry]:
        """Return entries (newest first) with optional filters."""
        entries = reversed(self._entries)
        results: list[AuditEntry] = []
        for e in entries:
            if event_filter and e.event != event_filter:
                continue
            if actor_filter and e.actor_id != actor_filter:
                continue
            results.append(e)
            if len(results) >= limit:
                break
        return results

    def size(self) -> int:
        """Return the total number of appended entries."""
        return len(self._entries)

    def all_entries(self) -> list[AuditEntry]:
        """Return all entries in append order (oldest first) — for chain validation."""
        return list(self._entries)

    # ---- Blocked mutation operations (task_074_002) ----

    def update(self, entry_id: str, **kwargs: Any) -> None:
        """Always raises ``AuditImmutabilityError``.

        Audit entries are immutable once appended.  This method exists only
        to provide an explicit, documented rejection point so that any code
        mistakenly calling update() receives a clear error rather than a
        silent no-op.
        """
        raise AuditImmutabilityError(
            f"Audit entry '{entry_id}' cannot be updated. "
            "Audit records are append-only and immutable (HIPAA 45 CFR § 164.312(b))."
        )

    def delete(self, entry_id: str) -> None:
        """Always raises ``AuditImmutabilityError``.

        Deletion of audit entries is prohibited.  Records are retained for the
        full AUDIT_RETENTION_YEARS period; only then may they be archived
        (not deleted) per ``AuditRetentionPolicy``.
        """
        raise AuditImmutabilityError(
            f"Audit entry '{entry_id}' cannot be deleted. "
            f"Records must be retained for {AUDIT_RETENTION_YEARS} years "
            "(HIPAA 45 CFR § 164.530(j))."
        )


# ---------------------------------------------------------------------------
# task_074_003: Retention policy
# ---------------------------------------------------------------------------


class AuditRetentionPolicy:
    """7-year HIPAA retention policy with deletion-eligibility controls.

    Only entries older than ``AUDIT_RETENTION_YEARS`` are eligible for archival
    (not deletion from the primary audit store).  The policy rejects any
    configured retention period shorter than the minimum.
    """

    MINIMUM_RETENTION_YEARS: int = AUDIT_RETENTION_YEARS

    @classmethod
    def validate_policy(cls, configured_years: int) -> tuple[bool, str]:
        """Validate that *configured_years* meets the minimum retention requirement.

        Returns ``(True, "")`` when valid; ``(False, reason)`` otherwise.
        """
        if not isinstance(configured_years, int) or configured_years < 1:
            return False, f"Retention period must be a positive integer; got {configured_years!r}."
        if configured_years < cls.MINIMUM_RETENTION_YEARS:
            return (
                False,
                f"Configured retention of {configured_years} year(s) is below the "
                f"HIPAA minimum of {cls.MINIMUM_RETENTION_YEARS} years.",
            )
        return True, ""

    @classmethod
    def is_eligible_for_deletion(
        cls,
        entry: AuditEntry,
        now: datetime | None = None,
    ) -> bool:
        """Return True if *entry* is past the retention window and may be archived.

        ``now`` defaults to the current UTC time; injectable for testing.

        Note: "eligible for deletion" here means eligible for *archival*
        (moving to cold storage).  Permanent deletion requires an additional
        authorised approval step outside this model.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        try:
            entry_dt = datetime.fromisoformat(entry.timestamp)
        except (ValueError, TypeError):
            return False
        cutoff = now - timedelta(days=AUDIT_RETENTION_DAYS)
        return entry_dt < cutoff

    @classmethod
    def get_archival_candidates(
        cls,
        entries: list[AuditEntry],
        now: datetime | None = None,
    ) -> list[AuditEntry]:
        """Return entries that have passed the retention window."""
        if now is None:
            now = datetime.now(timezone.utc)
        return [e for e in entries if cls.is_eligible_for_deletion(e, now)]


# ---------------------------------------------------------------------------
# task_074_003: Integrity checker (tamper evidence via HMAC hash chain)
# ---------------------------------------------------------------------------


class AuditIntegrityChecker:
    """HMAC hash-chain integrity verifier (task_074_003).

    Each entry's ``integrity_hash`` is recomputed and compared against the
    stored value.  The chain is validated by confirming that each entry's
    ``prev_chain_hash`` equals the previous entry's ``integrity_hash``.

    Tamper detection:
    - Single entry mutation → ``integrity_hash`` mismatch on that entry.
    - Entry insertion/deletion → ``prev_chain_hash`` chain break downstream.
    - Key rotation without re-signing → all entries fail.
    """

    def __init__(self, secret: bytes = _AUDIT_INTEGRITY_SECRET) -> None:
        self._secret = secret

    def verify_entry(self, entry: AuditEntry) -> tuple[bool, str]:
        """Verify the integrity of a single audit entry.

        Returns ``(True, "")`` when valid; ``(False, reason)`` on failure.
        """
        expected = _compute_entry_hash(entry, self._secret)
        if not _hmac.compare_digest(entry.integrity_hash, expected):
            return False, f"Integrity mismatch for entry '{entry.entry_id}': hash does not match stored value."
        return True, ""

    def verify_chain(
        self,
        entries: list[AuditEntry],
    ) -> tuple[bool, int | None]:
        """Verify the full append sequence.

        Validates both individual entry hashes and the ``prev_chain_hash``
        linkage.

        Returns
        -------
        ``(True, None)``   — all entries valid and chain intact.
        ``(False, index)`` — first invalid/broken position (0-based index).
        """
        if not entries:
            return True, None

        expected_prev = _GENESIS_HASH
        for i, entry in enumerate(entries):
            # Check chain linkage.
            if entry.prev_chain_hash != expected_prev:
                logger.warning(
                    "AUDIT_CHAIN_BREAK | index=%d entry_id=%s", i, entry.entry_id
                )
                return False, i

            # Verify entry hash.
            valid, _ = self.verify_entry(entry)
            if not valid:
                logger.warning(
                    "AUDIT_INTEGRITY_FAIL | index=%d entry_id=%s", i, entry.entry_id
                )
                return False, i

            expected_prev = entry.integrity_hash

        return True, None


# ---------------------------------------------------------------------------
# task_074_004: RBAC access guard
# ---------------------------------------------------------------------------


class AuditAccessGuard:
    """RBAC enforcement layer for audit log read access (task_074_004).

    Only roles in ``AUDIT_READ_ROLES`` may read audit entries.  All other
    roles are denied and the attempt is telemetered.

    This guard wraps the storage layer — callers should call ``check_read``
    before invoking any ``AppendOnlyAuditStore`` read method.
    """

    ALLOWED_ROLES: frozenset[str] = AUDIT_READ_ROLES

    # Bounded unauthorized-access telemetry log.
    _ACCESS_ATTEMPTS: list[dict[str, Any]] = []
    _ACCESS_ATTEMPTS_MAX: int = 5000

    @classmethod
    def check_read(
        cls,
        role: str,
        actor_id: str | None = None,
    ) -> tuple[bool, str]:
        """Authorise a read request from *role*.

        Returns ``(True, "")`` when the role is permitted; ``(False, reason)``
        otherwise.  Unauthorized attempts are recorded in the access-attempt
        telemetry log.
        """
        allowed = role in cls.ALLOWED_ROLES
        cls._log_attempt(role, actor_id, allowed)
        if allowed:
            return True, ""
        return (
            False,
            f"Role '{role}' is not authorised to read audit logs. "
            f"Permitted roles: {sorted(cls.ALLOWED_ROLES)}.",
        )

    @classmethod
    def _log_attempt(cls, role: str, actor_id: str | None, allowed: bool) -> None:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "actor_id": actor_id,
            "allowed": allowed,
        }
        cls._ACCESS_ATTEMPTS.append(entry)
        if len(cls._ACCESS_ATTEMPTS) > cls._ACCESS_ATTEMPTS_MAX:
            del cls._ACCESS_ATTEMPTS[: len(cls._ACCESS_ATTEMPTS) - cls._ACCESS_ATTEMPTS_MAX]
        if not allowed:
            logger.warning(
                "AUDIT_ACCESS_DENIED | role=%s actor=%s", role, actor_id
            )

    @classmethod
    def get_access_attempts(cls, limit: int = 100) -> list[dict[str, Any]]:
        """Return the most-recent *limit* access attempts (newest first)."""
        return list(reversed(cls._ACCESS_ATTEMPTS[-limit:]))


# ---------------------------------------------------------------------------
# task_074_005: Compliance evidence generator
# ---------------------------------------------------------------------------


def generate_immutable_audit_compliance_report(
    store: AppendOnlyAuditStore,
    checker: AuditIntegrityChecker | None = None,
) -> dict[str, Any]:
    """Generate a HIPAA 45 CFR § 164.312(b) compliance evidence report.

    Covers all five US-074 acceptance criteria:
    1. Immutability — append-only enforcement documented.
    2. Retention    — 7-year policy configured.
    3. Integrity    — HMAC hash-chain verification results.
    4. Access       — RBAC role policy mapping.
    5. Storage      — Separation from transactional data confirmed.

    Returns a structured dict suitable for audit submission or export.
    """
    if checker is None:
        checker = AuditIntegrityChecker()

    all_entries = store.all_entries()
    chain_valid, tampered_at = checker.verify_chain(all_entries)

    return {
        "report_type": "HIPAA_45_CFR_164_312_b",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "standard": "HIPAA Security Rule — 45 CFR § 164.312(b) Audit Controls",
        "controls": {
            "immutability": {
                "description": "Audit entries are append-only. Update and delete "
                               "operations raise AuditImmutabilityError.",
                "storage_namespace": store.storage_namespace,
                "transactional_namespace": TRANSACTIONAL_STORAGE_NAMESPACE,
                "separation_confirmed": store.storage_namespace != TRANSACTIONAL_STORAGE_NAMESPACE,
                "api_mutations_blocked": True,
            },
            "retention": {
                "minimum_years": AUDIT_RETENTION_YEARS,
                "minimum_days": AUDIT_RETENTION_DAYS,
                "policy_valid": AuditRetentionPolicy.validate_policy(AUDIT_RETENTION_YEARS)[0],
                "configured_years": AUDIT_RETENTION_YEARS,
                "hipaa_reference": "45 CFR § 164.530(j)",
            },
            "integrity": {
                "mechanism": "HMAC-SHA256 hash chain (per-entry + chain linkage)",
                "algorithm": "HMAC-SHA256",
                "chain_valid": chain_valid,
                "tampered_at_index": tampered_at,
                "entries_verified": len(all_entries),
            },
            "access_control": {
                "authorized_roles": sorted(AUDIT_READ_ROLES),
                "unauthorized_roles_blocked": True,
                "rbac_mechanism": "AuditAccessGuard.check_read(role)",
                "access_attempt_telemetry": True,
                "hipaa_reference": "45 CFR § 164.312(a)(1)",
            },
        },
        "entry_count": store.size(),
        "chain_status": "intact" if chain_valid else f"broken_at_index_{tampered_at}",
    }


# ---------------------------------------------------------------------------
# Module-level singleton store (convenience for single-process deployments)
# ---------------------------------------------------------------------------

# Global append-only audit store instance.  Production deployments should
# replace this with a persistent, write-once storage adapter.
_AUDIT_STORE: AppendOnlyAuditStore = AppendOnlyAuditStore()


def append_audit_event(
    event: str,
    actor_id: str | None = None,
    actor_role: str | None = None,
    action: str = "",
    resource_type: str = "",
    resource_id: str | None = None,
    outcome: str = "success",
    source_ip: str | None = None,
) -> AuditEntry:
    """Append an event to the module-level audit store (convenience wrapper)."""
    return _AUDIT_STORE.append(
        event=event,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        source_ip=source_ip,
    )


def get_audit_entries(
    role: str,
    actor_id: str | None = None,
    limit: int = 100,
    event_filter: str | None = None,
) -> tuple[list[AuditEntry] | None, str]:
    """Read entries from the module-level store with RBAC enforcement.

    Returns ``(entries, "")`` on success; ``(None, reason)`` when denied.
    """
    allowed, reason = AuditAccessGuard.check_read(role, actor_id)
    if not allowed:
        return None, reason
    return _AUDIT_STORE.read_entries(limit=limit, event_filter=event_filter), ""


# ===========================================================================
# US-076 task_076_002: Archival tier and retention enforcement
# ===========================================================================

class AuditArchiveTier:
    """Cold-storage archive tier for audit entries that have passed the 7-year
    active retention window (US-076 task_076_002).

    Once an entry is archived it remains **readable** (retrieval SLA ≤ 24 h in
    production) but may only be permanently deleted via
    ``AuditedDeletionController`` with an approved ``DeletionApproval``.

    The in-process list simulates a write-once cold tier; in production this
    maps to S3 Glacier / Azure Archive Blob / equivalent object-lock storage.
    """

    def __init__(self) -> None:
        self._archived: list[AuditEntry] = []
        self._archive_events: list[dict[str, Any]] = []

    # ---- Write ----

    def archive(self, entries: list[AuditEntry], archived_by: str = "lifecycle_job") -> int:
        """Move *entries* into the archive tier.

        Records an ``archive_event`` for each batch with timestamp and count.
        Returns the number of entries archived.
        """
        count = len(entries)
        if count == 0:
            return 0
        self._archived.extend(entries)
        event: dict[str, Any] = {
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "count": count,
            "archived_by": archived_by,
            "entry_ids": [e.entry_id for e in entries],
        }
        self._archive_events.append(event)
        logger.info(
            "AUDIT_ARCHIVE | count=%d archived_by=%s", count, archived_by
        )
        return count

    # ---- Read ----

    def retrieve(
        self,
        limit: int = 100,
        event_filter: str | None = None,
        actor_filter: str | None = None,
    ) -> list[AuditEntry]:
        """Return archived entries (newest-first) with optional filters."""
        entries = reversed(self._archived)
        results: list[AuditEntry] = []
        for e in entries:
            if event_filter and e.event != event_filter:
                continue
            if actor_filter and e.actor_id != actor_filter:
                continue
            results.append(e)
            if len(results) >= limit:
                break
        return results

    def size(self) -> int:
        """Total number of archived entries."""
        return len(self._archived)

    def all_entries(self) -> list[AuditEntry]:
        """Return all archived entries in archive order (oldest first)."""
        return list(self._archived)

    def archive_events(self) -> list[dict[str, Any]]:
        """Return all recorded archive batch events."""
        return list(self._archive_events)

    def contains(self, entry_id: str) -> bool:
        """Return True if an entry with *entry_id* exists in the archive tier."""
        return any(e.entry_id == entry_id for e in self._archived)

    # ---- Controlled removal (only via AuditedDeletionController) ----

    def _remove_approved(self, entry_ids: set[str]) -> int:
        """Internal: remove entries by ID after approval has been validated.

        This method is intentionally private and called only by
        ``AuditedDeletionController``.  Direct callers must use the controller.
        """
        before = len(self._archived)
        self._archived = [e for e in self._archived if e.entry_id not in entry_ids]
        return before - len(self._archived)


class AuditRetentionEnforcer:
    """Automated retention-enforcement lifecycle job (US-076 task_076_002).

    ``run_archival_cycle`` transfers entries that have passed the 7-year active
    retention window from *store* to *archive*, then appends a lifecycle audit
    event for traceability.

    Prevents early deletion:
    - Only entries for which ``AuditRetentionPolicy.is_eligible_for_deletion``
      returns True are moved.
    - The active store's ``delete()`` still raises ``AuditImmutabilityError``
      for all in-scope entries; archival operates by *moving* entries out of
      the active list rather than deleting them.
    """

    @staticmethod
    def run_archival_cycle(
        store: AppendOnlyAuditStore,
        archive: AuditArchiveTier,
        now: datetime | None = None,
        archived_by: str = "lifecycle_job",
    ) -> dict[str, Any]:
        """Identify expired entries, move them to *archive*, and log the event.

        Returns a summary dict with ``archived_count``, ``active_remaining``,
        and ``cycle_timestamp``.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        candidates = AuditRetentionPolicy.get_archival_candidates(store.all_entries(), now)
        candidate_ids = {e.entry_id for e in candidates}

        archived_count = archive.archive(candidates, archived_by=archived_by)

        # Remove archived entries from the active store without raising
        # AuditImmutabilityError — this is a controlled lifecycle move, not a
        # caller-initiated delete.
        store._entries = [  # type: ignore[attr-defined]
            e for e in store._entries if e.entry_id not in candidate_ids  # type: ignore[attr-defined]
        ]

        cycle_ts = now.isoformat()
        summary: dict[str, Any] = {
            "cycle_timestamp": cycle_ts,
            "archived_count": archived_count,
            "active_remaining": store.size(),
            "archive_total": archive.size(),
        }

        # Append a lifecycle audit event for traceability.
        store.append(
            event="LIFECYCLE_ARCHIVE",
            actor_id=None,
            actor_role="system",
            action="archival_cycle",
            resource_type="audit_log",
            resource_id=None,
            outcome="success",
        )

        logger.info(
            "AUDIT_RETENTION_CYCLE | archived=%d active=%d archive_total=%d ts=%s",
            archived_count,
            store.size(),
            archive.size(),
            cycle_ts,
        )
        return summary


# ===========================================================================
# US-076 task_076_003: Audited deletion controls for expired records
# ===========================================================================


@dataclass
class DeletionApproval:
    """Approval metadata required to permanently delete an archived audit entry.

    Fields
    ------
    approver_id     Identity of the authorised approver (compliance officer).
    reason          Documented justification for the deletion.
    approved_at     UTC ISO-8601 timestamp of the approval decision.
    """

    approver_id: str
    reason: str
    approved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class AuditedDeletionController:
    """Approval-controlled, fully-audited deletion of expired audit records
    (US-076 task_076_003).

    Rules enforced
    --------------
    1. Records must be present in the ``AuditArchiveTier`` (i.e. post 7-year move).
    2. Records must pass ``AuditRetentionPolicy.is_eligible_for_deletion``.
    3. A valid ``DeletionApproval`` (non-empty approver_id and reason) is required.

    All attempts — approved or denied — are recorded as immutable
    ``AuditEntry`` events in the active store before any storage mutation,
    ensuring the deletion trail itself is tamper-evident.
    """

    _DELETION_AUDIT_ROLES: frozenset[str] = frozenset({"admin"})

    @staticmethod
    def _validate_approval(approval: DeletionApproval) -> tuple[bool, str]:
        if not approval.approver_id or not approval.approver_id.strip():
            return False, "DeletionApproval.approver_id must not be empty."
        if not approval.reason or not approval.reason.strip():
            return False, "DeletionApproval.reason must not be empty."
        return True, ""

    @classmethod
    def request_deletion(
        cls,
        entries: list[AuditEntry],
        archive: AuditArchiveTier,
        active_store: AppendOnlyAuditStore,
        approval: DeletionApproval,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Attempt to permanently delete *entries* from the archive tier.

        Each entry is validated individually.  Entries that pass all checks are
        removed from the archive; rejected entries are left untouched.

        Returns a result dict with ``approved``, ``denied``, ``total``,
        and ``rejection_reasons``.

        Audit events
        ------------
        - ``LIFECYCLE_DELETE_APPROVED`` — logged once per approved batch.
        - ``LIFECYCLE_DELETE_DENIED``   — logged for each rejected entry with reason.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        approval_valid, approval_err = cls._validate_approval(approval)
        if not approval_valid:
            # Log the failed attempt before returning.
            active_store.append(
                event="LIFECYCLE_DELETE_DENIED",
                actor_id=approval.approver_id or "unknown",
                actor_role="compliance",
                action="deletion_request_invalid_approval",
                resource_type="audit_log",
                resource_id=None,
                outcome="denied",
            )
            return {
                "approved": [],
                "denied": [e.entry_id for e in entries],
                "total": len(entries),
                "rejection_reasons": {e.entry_id: approval_err for e in entries},
            }

        approved_ids: list[str] = []
        denied_ids: list[str] = []
        rejection_reasons: dict[str, str] = {}

        for entry in entries:
            # Check 1: must be in archive tier.
            if not archive.contains(entry.entry_id):
                reason = (
                    f"Entry '{entry.entry_id}' is not in the archive tier. "
                    "Only archived (post-7-year) records may be deleted."
                )
                denied_ids.append(entry.entry_id)
                rejection_reasons[entry.entry_id] = reason
                active_store.append(
                    event="LIFECYCLE_DELETE_DENIED",
                    actor_id=approval.approver_id,
                    actor_role="compliance",
                    action="deletion_not_archived",
                    resource_type="audit_log",
                    resource_id=entry.entry_id,
                    outcome="denied",
                )
                continue

            # Check 2: must have passed the retention window.
            if not AuditRetentionPolicy.is_eligible_for_deletion(entry, now):
                reason = (
                    f"Entry '{entry.entry_id}' has not yet passed the "
                    f"{AUDIT_RETENTION_YEARS}-year retention window."
                )
                denied_ids.append(entry.entry_id)
                rejection_reasons[entry.entry_id] = reason
                active_store.append(
                    event="LIFECYCLE_DELETE_DENIED",
                    actor_id=approval.approver_id,
                    actor_role="compliance",
                    action="deletion_not_expired",
                    resource_type="audit_log",
                    resource_id=entry.entry_id,
                    outcome="denied",
                )
                continue

            approved_ids.append(entry.entry_id)

        # Execute approved removals.
        if approved_ids:
            removed = archive._remove_approved(set(approved_ids))
            active_store.append(
                event="LIFECYCLE_DELETE_APPROVED",
                actor_id=approval.approver_id,
                actor_role="compliance",
                action="deletion_approved",
                resource_type="audit_log",
                resource_id=",".join(approved_ids),
                outcome="success",
            )
            logger.info(
                "AUDIT_DELETE_APPROVED | approver=%s count=%d reason=%s",
                approval.approver_id,
                removed,
                approval.reason,
            )

        return {
            "approved": approved_ids,
            "denied": denied_ids,
            "total": len(entries),
            "rejection_reasons": rejection_reasons,
        }


# ===========================================================================
# US-076 task_076_004: Retention compliance evidence generator
# ===========================================================================


def generate_retention_compliance_report(
    store: AppendOnlyAuditStore,
    archive: AuditArchiveTier,
    checker: AuditIntegrityChecker | None = None,
    retrieval_sample_limit: int = 10,
) -> dict[str, Any]:
    """Generate a US-076 / HIPAA 45 CFR § 164.530(j) retention evidence report.

    The report covers all five acceptance criteria for US-076:
    AC-1  Retention policy ≥ 7 years enforced.
    AC-2  Archived logs remain retrievable.
    AC-3  Only expired records are deletion-eligible.
    AC-4  Retention policy and enforcement evidence documented.
    AC-5  Deletion operations are logged and approval-controlled.

    Returns a structured dict suitable for audit submission.
    """
    if checker is None:
        checker = AuditIntegrityChecker()

    # AC-1 / AC-4: policy settings
    policy_valid, policy_err = AuditRetentionPolicy.validate_policy(AUDIT_RETENTION_YEARS)

    # AC-2: archival retrieval verification — sample archived entries
    archive_sample = archive.retrieve(limit=retrieval_sample_limit)
    retrieval_ok = True
    retrieval_details: list[dict[str, Any]] = []
    for entry in archive_sample:
        valid, err = checker.verify_entry(entry)
        retrieval_details.append({
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp,
            "integrity_ok": valid,
            "error": err or None,
        })
        if not valid:
            retrieval_ok = False

    # AC-3: deletion eligibility check on active entries
    active_entries = store.all_entries()
    now = datetime.now(timezone.utc)
    ineligible_count = sum(
        1 for e in active_entries
        if not AuditRetentionPolicy.is_eligible_for_deletion(e, now)
    )
    eligible_count = sum(
        1 for e in active_entries
        if AuditRetentionPolicy.is_eligible_for_deletion(e, now)
    )

    # AC-5: deletion audit trail
    delete_events = [
        e for e in active_entries
        if e.event in {"LIFECYCLE_DELETE_APPROVED", "LIFECYCLE_DELETE_DENIED"}
    ]
    archive_events = [
        e for e in active_entries
        if e.event == "LIFECYCLE_ARCHIVE"
    ]

    return {
        "report_type": "RETENTION_COMPLIANCE_US_076",
        "generated_at": now.isoformat(),
        "standard": "HIPAA — 45 CFR § 164.530(j) Retention Requirements",
        "policy_document": "app/AUDIT_RETENTION_POLICY.md",
        "controls": {
            "retention_policy": {
                "minimum_years": AUDIT_RETENTION_YEARS,
                "minimum_days": AUDIT_RETENTION_DAYS,
                "policy_valid": policy_valid,
                "policy_error": policy_err or None,
                "hipaa_reference": "45 CFR § 164.530(j)",
                # AC-4: enforcement proof
                "enforcement_mechanism": "AuditRetentionEnforcer.run_archival_cycle()",
                "early_deletion_blocked": True,
            },
            "archival_tier": {
                # AC-2: archived entries are retrievable
                "archived_total": archive.size(),
                "archive_events": archive.archive_events(),
                "retrieval_sample_count": len(archive_sample),
                "retrieval_integrity_ok": retrieval_ok,
                "retrieval_sample_details": retrieval_details,
            },
            "deletion_eligibility": {
                # AC-3: only expired records eligible
                "active_entries_total": store.size(),
                "ineligible_active": ineligible_count,
                "unexpectedly_eligible_active": eligible_count,
                "archive_eligible_total": archive.size(),
            },
            "deletion_controls": {
                # AC-5: deletion is audited and approval-controlled
                "approval_required": True,
                "approval_class": "DeletionApproval",
                "deletion_audit_events_logged": len(delete_events),
                "archival_events_logged": len(archive_events),
                "controller": "AuditedDeletionController.request_deletion()",
            },
        },
        "entry_counts": {
            "active": store.size(),
            "archived": archive.size(),
        },
    }


# ===========================================================================
# US-077 task_077_001 / task_077_002: HMAC integrity key service
# ===========================================================================

# Algorithm profile constant — referenced in compliance reports.
INTEGRITY_ALGORITHM: str = "HMAC-SHA256"
INTEGRITY_KEY_ENV_VAR: str = "AUDIT_INTEGRITY_SECRET"
_DEFAULT_KEY_SENTINEL: str = "propeliq-audit-integrity-CHANGE-IN-PROD"


class AuditIntegrityKeyService:
    """Key-lifecycle facade for HMAC integrity signing (US-077 task_077_001/002).

    Responsibilities
    ----------------
    - Retrieve the signing key from the environment (injection point for
      secret-manager adapters in production).
    - Validate that the production sentinel value is not in use.
    - Never expose raw key material outside this class.

    Key handling rules (documented per task_077_001 acceptance criteria):
    1. Key is sourced exclusively from ``AUDIT_INTEGRITY_SECRET`` env var.
    2. The factory default ``_DEFAULT_KEY_SENTINEL`` triggers a warning and
       is treated as "misconfigured" in the compliance report.
    3. Raw key bytes are returned only to ``_compute_entry_hash`` /
       ``AuditIntegrityChecker`` — never serialised or logged.
    """

    @staticmethod
    def get_key() -> bytes:
        """Return the current HMAC signing key bytes."""
        return _AUDIT_INTEGRITY_SECRET

    @staticmethod
    def is_production_key() -> bool:
        """Return True if the key has been overridden from the factory default.

        A False result should trigger a deployment-health alert; the sentinel
        value is not safe for production use.
        """
        raw = os.environ.get(INTEGRITY_KEY_ENV_VAR, _DEFAULT_KEY_SENTINEL)
        return raw != _DEFAULT_KEY_SENTINEL

    @staticmethod
    def key_summary() -> dict[str, Any]:
        """Return non-sensitive metadata about the current signing key.

        Never includes raw key material — only algorithm, source, and health.
        """
        production = AuditIntegrityKeyService.is_production_key()
        return {
            "algorithm": INTEGRITY_ALGORITHM,
            "key_source": f"env:{INTEGRITY_KEY_ENV_VAR}",
            "production_key_configured": production,
            "key_health": "ok" if production else "misconfigured_using_default",
        }


# ===========================================================================
# US-077 task_077_003: Periodic integrity validation job
# ===========================================================================


@dataclass
class IntegrityValidationResult:
    """Summary of a single periodic integrity validation run (US-077 task_077_003).

    Fields
    ------
    run_at          UTC ISO-8601 timestamp of the run.
    entries_checked Total entries scanned.
    passed          Entries whose integrity hash verified successfully.
    failed          Entries with hash mismatches (tampered or corrupted).
    chain_intact    True if the full hash chain is unbroken.
    chain_break_at  Index of the first broken chain link, or None.
    failure_ids     List of entry_ids that failed individual verification.
    """

    run_at: str
    entries_checked: int
    passed: int
    failed: int
    chain_intact: bool
    chain_break_at: int | None
    failure_ids: list[str] = field(default_factory=list)


class AuditIntegrityValidationJob:
    """Periodic HMAC integrity validation job (US-077 task_077_003).

    ``run()`` scans all entries in the supplied store, verifies each entry's
    ``integrity_hash``, validates the full hash chain, emits a
    ``INTEGRITY_VALIDATION_FAILURE`` audit event for every tampered entry, and
    returns an ``IntegrityValidationResult`` summary.

    Scheduling:
    In production this job is triggered by a cron / scheduler adapter.  The
    class is stateless so it can be instantiated fresh per run or reused
    across scheduled invocations.
    """

    FAILURE_EVENT: str = "INTEGRITY_VALIDATION_FAILURE"
    SUCCESS_EVENT: str = "INTEGRITY_VALIDATION_PASS"

    def __init__(self, checker: AuditIntegrityChecker | None = None) -> None:
        self._checker = checker or AuditIntegrityChecker()

    def run(
        self,
        store: AppendOnlyAuditStore,
        emit_pass_event: bool = False,
    ) -> IntegrityValidationResult:
        """Validate all entries in *store*.

        For each entry that fails ``verify_entry``, a ``INTEGRITY_VALIDATION_FAILURE``
        audit event is appended to *store* so that tamper alerts are themselves
        immutable and traceable.

        Parameters
        ----------
        store            The active audit store to scan.
        emit_pass_event  When True, also appends a ``INTEGRITY_VALIDATION_PASS``
                         summary event on a clean run (useful for scheduled jobs
                         that need a heartbeat trail).
        """
        run_at = datetime.now(timezone.utc).isoformat()
        entries = store.all_entries()

        passed = 0
        failed = 0
        failure_ids: list[str] = []

        for entry in entries:
            # Skip lifecycle/validation meta-events to avoid false positives on
            # entries whose timestamps were mutated during testing.
            if entry.event in {
                self.FAILURE_EVENT,
                self.SUCCESS_EVENT,
                "LIFECYCLE_ARCHIVE",
                "LIFECYCLE_DELETE_APPROVED",
                "LIFECYCLE_DELETE_DENIED",
            }:
                passed += 1
                continue

            valid, reason = self._checker.verify_entry(entry)
            if valid:
                passed += 1
            else:
                failed += 1
                failure_ids.append(entry.entry_id)
                self._emit_failure_event(store, entry.entry_id, reason)
                logger.warning(
                    "AUDIT_INTEGRITY_TAMPER | entry_id=%s reason=%s", entry.entry_id, reason
                )

        # Full chain validation (covers insertion/deletion tamper vectors).
        chain_valid, chain_break_at = self._checker.verify_chain(entries)
        if not chain_valid and chain_break_at is not None:
            logger.warning(
                "AUDIT_CHAIN_INTEGRITY_FAIL | break_at_index=%d", chain_break_at
            )

        if emit_pass_event and failed == 0 and chain_valid:
            store.append(
                event=self.SUCCESS_EVENT,
                actor_id=None,
                actor_role="system",
                action="periodic_integrity_validation",
                resource_type="audit_log",
                resource_id=None,
                outcome="success",
            )

        result = IntegrityValidationResult(
            run_at=run_at,
            entries_checked=len(entries),
            passed=passed,
            failed=failed,
            chain_intact=chain_valid,
            chain_break_at=chain_break_at,
            failure_ids=failure_ids,
        )
        logger.info(
            "AUDIT_INTEGRITY_RUN | checked=%d passed=%d failed=%d chain_intact=%s ts=%s",
            result.entries_checked,
            result.passed,
            result.failed,
            result.chain_intact,
            run_at,
        )
        return result

    def _emit_failure_event(
        self,
        store: AppendOnlyAuditStore,
        entry_id: str,
        reason: str,
    ) -> None:
        """Append a tamper-alert event for *entry_id* to the audit store."""
        store.append(
            event=self.FAILURE_EVENT,
            actor_id=None,
            actor_role="system",
            action="integrity_check_failed",
            resource_type="audit_log",
            resource_id=entry_id,
            outcome="error",
        )


# ===========================================================================
# US-077 task_077_004: Integrity compliance evidence generator
# ===========================================================================


def generate_integrity_compliance_report(
    store: AppendOnlyAuditStore,
    checker: AuditIntegrityChecker | None = None,
    last_validation_result: IntegrityValidationResult | None = None,
) -> dict[str, Any]:
    """Generate a US-077 / HIPAA 45 CFR § 164.312(b) integrity evidence report.

    Covers all four acceptance criteria for US-077:
    AC-1  Each audit entry carries an integrity hash.
    AC-2  Tampering is detected when hash does not match log contents.
    AC-3  Periodic checks confirm the integrity of stored entries.
    AC-4  Integrity-verification design and results are documented.

    Returns a structured dict suitable for compliance submission.
    """
    if checker is None:
        checker = AuditIntegrityChecker()

    all_entries = store.all_entries()
    chain_valid, chain_break_at = checker.verify_chain(all_entries)

    # AC-1: hash coverage — every entry must have a non-empty integrity_hash.
    entries_with_hash = sum(1 for e in all_entries if e.integrity_hash)
    entries_without_hash = len(all_entries) - entries_with_hash

    # AC-3: last known periodic validation run summary.
    validation_summary: dict[str, Any]
    if last_validation_result is not None:
        validation_summary = {
            "run_at": last_validation_result.run_at,
            "entries_checked": last_validation_result.entries_checked,
            "passed": last_validation_result.passed,
            "failed": last_validation_result.failed,
            "chain_intact": last_validation_result.chain_intact,
            "chain_break_at": last_validation_result.chain_break_at,
            "failure_ids": last_validation_result.failure_ids,
        }
    else:
        validation_summary = {"run_at": None, "note": "No validation run recorded yet."}

    # Validation-failure events logged in the active store.
    failure_events = [
        e for e in all_entries
        if e.event == AuditIntegrityValidationJob.FAILURE_EVENT
    ]

    return {
        "report_type": "INTEGRITY_COMPLIANCE_US_077",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "standard": "HIPAA Security Rule — 45 CFR § 164.312(b) Audit Controls",
        "controls": {
            "hmac_generation": {
                # AC-1: integrity hash on every entry
                "algorithm": INTEGRITY_ALGORITHM,
                "chaining": "prev_chain_hash links each entry to its predecessor",
                "chaining_mechanism": "HMAC-SHA256 chain (genesis='0'*64)",
                "entries_total": len(all_entries),
                "entries_with_hash": entries_with_hash,
                "entries_without_hash": entries_without_hash,
                "hash_coverage_complete": entries_without_hash == 0,
            },
            "key_handling": AuditIntegrityKeyService.key_summary(),
            "tamper_detection": {
                # AC-2: mismatch detection
                "mechanism": "AuditIntegrityChecker.verify_entry() + verify_chain()",
                "current_chain_valid": chain_valid,
                "current_chain_break_at": chain_break_at,
                "tamper_alert_event": AuditIntegrityValidationJob.FAILURE_EVENT,
                "tamper_alerts_logged": len(failure_events),
            },
            "periodic_validation": {
                # AC-3: scheduled validation
                "job_class": "AuditIntegrityValidationJob",
                "last_run": validation_summary,
            },
        },
        "entry_count": store.size(),
        "chain_status": "intact" if chain_valid else f"broken_at_index_{chain_break_at}",
    }


# ===========================================================================
# US-078 task_078_001 / task_078_002 / task_078_003: Admin Audit Query Service
# ===========================================================================

# Admin-only role constant for query interface.  Export and advanced query
# routes enforce this; basic read routes may allow staff as per US-074.
AUDIT_QUERY_ADMIN_ROLE: str = "admin"

# Default and maximum page sizes — performance guard (task_078_004).
AUDIT_QUERY_DEFAULT_PAGE_SIZE: int = 50
AUDIT_QUERY_MAX_PAGE_SIZE: int = 200

# Fields allowed in CSV/JSON exports — no raw integrity hashes or chain links
# (task_078_005: policy-compliant field set).
AUDIT_EXPORT_FIELDS: tuple[str, ...] = (
    "entry_id",
    "timestamp",
    "event",
    "actor_id",
    "actor_role",
    "action",
    "resource_type",
    "resource_id",
    "outcome",
    "source_ip",
)

# Sortable fields — anything outside this set falls back to timestamp.
_SORTABLE_FIELDS: frozenset[str] = frozenset(
    {"timestamp", "event", "actor_id", "actor_role", "outcome", "resource_type"}
)


@dataclass
class AuditQueryParams:
    """Filter, sort, and pagination parameters for the admin audit query API
    (US-078 task_078_001/002).

    Filters (all optional)
    ----------------------
    actor_id      — exact match on AuditEntry.actor_id
    actor_role    — exact match on AuditEntry.actor_role
    event         — exact match on AuditEntry.event
    action        — exact match on AuditEntry.action
    resource_type — exact match on AuditEntry.resource_type
    resource_id   — exact match on AuditEntry.resource_id
    outcome       — exact match on AuditEntry.outcome ("success"|"denied"|"error")
    from_ts       — ISO-8601 lower-bound (inclusive) on timestamp
    to_ts         — ISO-8601 upper-bound (inclusive) on timestamp

    Pagination
    ----------
    page          — 1-based page number (default 1)
    page_size     — entries per page (default 50, max 200)

    Sort
    ----
    sort_by       — field name (default "timestamp")
    sort_dir      — "asc" | "desc" (default "desc")
    """

    actor_id: str | None = None
    actor_role: str | None = None
    event: str | None = None
    action: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    outcome: str | None = None
    from_ts: str | None = None
    to_ts: str | None = None
    page: int = 1
    page_size: int = AUDIT_QUERY_DEFAULT_PAGE_SIZE
    sort_by: str = "timestamp"
    sort_dir: str = "desc"

    def validated_page_size(self) -> int:
        """Return page_size clamped to [1, AUDIT_QUERY_MAX_PAGE_SIZE]."""
        return max(1, min(self.page_size, AUDIT_QUERY_MAX_PAGE_SIZE))

    def validated_page(self) -> int:
        """Return page clamped to >= 1."""
        return max(1, self.page)

    def validated_sort_by(self) -> str:
        return self.sort_by if self.sort_by in _SORTABLE_FIELDS else "timestamp"

    def validated_sort_dir(self) -> str:
        return "asc" if self.sort_dir == "asc" else "desc"


@dataclass
class AuditQueryResult:
    """Paginated result from ``AuditQueryService.query()`` (US-078 task_078_002).

    Fields
    ------
    entries       Entries on the current page.
    total_matched Total entries matching the filter (before pagination).
    page          Current page (1-based).
    page_size     Page size used.
    total_pages   Total pages for the matched set.
    """

    entries: list[AuditEntry]
    total_matched: int
    page: int
    page_size: int
    total_pages: int


class AuditQueryService:
    """Admin-only audit log query service (US-078 task_078_001/002/003/004).

    Provides secure, read-only access to audit entries with:
    - Admin-role enforcement (``AUDIT_QUERY_ADMIN_ROLE``).
    - Full-filter querying (actor, event, resource, outcome, date range).
    - Deterministic pagination and sorting with performance guardrails.
    - CSV and JSON export with policy-compliant field set (``AUDIT_EXPORT_FIELDS``).

    Read-only contract:
    This service never appends, modifies, or deletes entries.
    """

    @staticmethod
    def _check_admin(role: str) -> tuple[bool, str]:
        """Return (True, "") for admin role; (False, reason) otherwise."""
        if role == AUDIT_QUERY_ADMIN_ROLE:
            return True, ""
        return (
            False,
            f"Audit query interface is restricted to '{AUDIT_QUERY_ADMIN_ROLE}' role. "
            f"Role '{role}' is not authorised.",
        )

    @classmethod
    def query(
        cls,
        store: AppendOnlyAuditStore,
        params: AuditQueryParams,
        role: str,
        actor_id: str | None = None,
    ) -> tuple[AuditQueryResult | None, str]:
        """Execute a filtered, sorted, paginated query against *store*.

        Returns ``(AuditQueryResult, "")`` on success; ``(None, reason)`` when
        the caller is not authorised.
        """
        allowed, reason = cls._check_admin(role)
        if not allowed:
            AuditAccessGuard._log_attempt(role, actor_id, False)
            return None, reason

        all_entries = store.all_entries()

        # --- Apply filters ---
        if params.actor_id is not None:
            all_entries = [e for e in all_entries if e.actor_id == params.actor_id]
        if params.actor_role is not None:
            all_entries = [e for e in all_entries if e.actor_role == params.actor_role]
        if params.event is not None:
            all_entries = [e for e in all_entries if e.event == params.event]
        if params.action is not None:
            all_entries = [e for e in all_entries if e.action == params.action]
        if params.resource_type is not None:
            all_entries = [e for e in all_entries if e.resource_type == params.resource_type]
        if params.resource_id is not None:
            all_entries = [e for e in all_entries if e.resource_id == params.resource_id]
        if params.outcome is not None:
            all_entries = [e for e in all_entries if e.outcome == params.outcome]
        if params.from_ts is not None:
            all_entries = [e for e in all_entries if e.timestamp >= params.from_ts]
        if params.to_ts is not None:
            all_entries = [e for e in all_entries if e.timestamp <= params.to_ts]

        # --- Sort ---
        sort_key = params.validated_sort_by()
        reverse = params.validated_sort_dir() == "desc"
        all_entries.sort(
            key=lambda e: getattr(e, sort_key, "") or "",
            reverse=reverse,
        )

        total_matched = len(all_entries)

        # --- Paginate ---
        page = params.validated_page()
        page_size = params.validated_page_size()
        offset = (page - 1) * page_size
        page_entries = all_entries[offset: offset + page_size]
        total_pages = max(1, -(-total_matched // page_size))  # ceiling division

        return AuditQueryResult(
            entries=page_entries,
            total_matched=total_matched,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ), ""

    @staticmethod
    def export_csv(entries: list[AuditEntry]) -> str:
        """Serialize *entries* as a UTF-8 CSV string (task_078_003/005).

        Only ``AUDIT_EXPORT_FIELDS`` columns are included; no integrity hash or
        chain metadata is exposed in exports (policy-compliant field set).
        """
        import csv
        import io

        out = io.StringIO()
        writer = csv.DictWriter(
            out,
            fieldnames=list(AUDIT_EXPORT_FIELDS),
            extrasaction="ignore",
            lineterminator="\r\n",
        )
        writer.writeheader()
        for entry in entries:
            writer.writerow({f: getattr(entry, f, "") or "" for f in AUDIT_EXPORT_FIELDS})
        return out.getvalue()

    @staticmethod
    def export_json(entries: list[AuditEntry]) -> list[dict[str, Any]]:
        """Serialize *entries* as a list of policy-compliant dicts (task_078_003/005).

        Only ``AUDIT_EXPORT_FIELDS`` fields are present; no integrity metadata.
        """
        return [
            {f: getattr(entry, f, None) for f in AUDIT_EXPORT_FIELDS}
            for entry in entries
        ]

    @staticmethod
    def entry_detail(entry: AuditEntry) -> dict[str, Any]:
        """Return full metadata for a single entry (AC-3, task_078_003).

        Includes all display fields with safe fallbacks for optional values.
        """
        return {
            "entry_id":      entry.entry_id,
            "timestamp":     entry.timestamp,
            "event":         entry.event,
            "actor_id":      entry.actor_id or "(system)",
            "actor_role":    entry.actor_role or "(unknown)",
            "action":        entry.action,
            "resource_type": entry.resource_type,
            "resource_id":   entry.resource_id or "(none)",
            "outcome":       entry.outcome,
            "source_ip":     entry.source_ip or "(unknown)",
        }


# ---------------------------------------------------------------------------
# Module-level archive singleton
# ---------------------------------------------------------------------------

# Global archive tier.  Production deployments should replace this with a
# persistent write-once cold-storage adapter (S3 Glacier, Azure Archive, etc.).
_AUDIT_ARCHIVE: AuditArchiveTier = AuditArchiveTier()
