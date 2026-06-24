"""
EP-008 US-087: Stateless API — No Local Storage

BE-1   Local session persistence audit and classification.
       ``StatelessAuditRunner`` scans registered ``StateEntry`` objects and
       raises ``ForbiddenLocalStateError`` when any use ``LOCAL_DISK`` storage.
       In-memory (per-instance) stores are flagged as transient but not
       forbidden — they are acceptable for read caches and per-request state.

BE-2   Cross-instance auth consistency.
       ``CrossInstanceTokenValidator`` validates session tokens without
       consulting a per-instance store.  The current PropelIQ implementation
       uses opaque UUID tokens backed by an in-memory store; this module
       documents the approved migration path to HMAC-signed tokens that
       achieve true per-instance stateless validation.

BE-3   Shared state classification.
       ``StateStorageType`` enumeration distinguishes between LOCAL_DISK
       (forbidden), IN_MEMORY (transient/acceptable), DATABASE (approved),
       and EXTERNAL_CACHE (approved).  The ``StatelessAuditRunner`` separates
       these into ``violations``, ``transient``, and ``approved`` buckets.

DOC-1  See STATELESSNESS_GUIDE.md for prohibited patterns and approved
       alternatives.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Storage classification
# ---------------------------------------------------------------------------


class StateStorageType(str, Enum):
    """Where a unit of application state is persisted (BE-3).

    IN_MEMORY     Per-instance dict / list.  Acceptable for read caches and
                  per-request ephemeral computation; lost on restart / scale.
    DATABASE      Shared relational or document database.  Approved for
                  persistent state visible across all instances.
    EXTERNAL_CACHE  Shared in-memory cache (Redis / Valkey / Memcached).
                  Approved for shared ephemeral / session state with TTL.
    LOCAL_DISK    Local filesystem write.  FORBIDDEN — breaks statelessness;
                  data is not visible to other instances.
    """

    IN_MEMORY = "in_memory"
    DATABASE = "database"
    EXTERNAL_CACHE = "external_cache"
    LOCAL_DISK = "local_disk"   # FORBIDDEN


APPROVED_STORAGE_TYPES: frozenset[StateStorageType] = frozenset(
    {StateStorageType.DATABASE, StateStorageType.EXTERNAL_CACHE}
)
FORBIDDEN_STORAGE_TYPES: frozenset[StateStorageType] = frozenset(
    {StateStorageType.LOCAL_DISK}
)
TRANSIENT_STORAGE_TYPES: frozenset[StateStorageType] = frozenset(
    {StateStorageType.IN_MEMORY}
)


# ---------------------------------------------------------------------------
# BE-1: Exceptions
# ---------------------------------------------------------------------------


class ForbiddenLocalStateError(Exception):
    """Raised when a ``StatelessAuditRunner`` detects LOCAL_DISK state entries.

    Every LOCAL_DISK entry is a statelessness violation; fix by migrating to
    DATABASE or EXTERNAL_CACHE storage.
    """


# ---------------------------------------------------------------------------
# BE-3: State entry description
# ---------------------------------------------------------------------------


@dataclass
class StateEntry:
    """Describes a single unit of application state for audit purposes.

    Attributes
    ----------
    name            Unique identifier for this state entry.
    storage_type    Where the state lives (see ``StateStorageType``).
    owner_module    Python module that owns or creates this state.
    is_shared       True if the state is visible to all instances.
                    Should be True only for DATABASE and EXTERNAL_CACHE types.
    description     Free-text explanation of what this state holds.
    """

    name: str
    storage_type: StateStorageType
    owner_module: str
    is_shared: bool
    description: str = ""


# ---------------------------------------------------------------------------
# BE-1: Audit report + runner
# ---------------------------------------------------------------------------


@dataclass
class StatelessAuditReport:
    """Snapshot result of one audit run.

    Attributes
    ----------
    entries     All registered ``StateEntry`` objects.
    violations  Entries with FORBIDDEN (LOCAL_DISK) storage types.
    approved    Entries with approved shared storage types (DATABASE / CACHE).
    transient   Entries with IN_MEMORY storage (per-instance; not shared).
    audited_at  ISO-8601 UTC timestamp when the audit ran.
    """

    entries: list[StateEntry]
    violations: list[StateEntry]
    approved: list[StateEntry]
    transient: list[StateEntry]
    audited_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def is_compliant(self) -> bool:
        """True if no violations were found."""
        return len(self.violations) == 0

    def summary(self) -> dict[str, Any]:
        return {
            "compliant": self.is_compliant,
            "total_entries": len(self.entries),
            "violations": len(self.violations),
            "approved_shared_state": len(self.approved),
            "transient_in_memory": len(self.transient),
            "audited_at": self.audited_at,
        }


class StatelessAuditRunner:
    """Registers ``StateEntry`` objects and audits them for statelessness violations.

    Typical usage::

        runner = StatelessAuditRunner()

        # Register all known state stores in your application
        runner.register(StateEntry(
            name="session_store",
            storage_type=StateStorageType.IN_MEMORY,
            owner_module="src.web_app",
            is_shared=False,
            description="Per-instance session UUID store",
        ))
        runner.register(StateEntry(
            name="appointments",
            storage_type=StateStorageType.DATABASE,
            owner_module="src.booking_service",
            is_shared=True,
            description="SQLite appointment records",
        ))

        report = runner.audit()
        assert report.is_compliant          # no LOCAL_DISK violations
        runner.assert_no_violations()       # raises ForbiddenLocalStateError if any
    """

    def __init__(self) -> None:
        self._entries: list[StateEntry] = []

    def register(self, entry: StateEntry) -> None:
        """Add a state entry to the registry."""
        self._entries.append(entry)

    def entries(self) -> list[StateEntry]:
        """Return all registered entries."""
        return list(self._entries)

    def audit(self) -> StatelessAuditReport:
        """Run the audit and return a ``StatelessAuditReport``."""
        violations = [
            e for e in self._entries
            if e.storage_type in FORBIDDEN_STORAGE_TYPES
        ]
        approved = [
            e for e in self._entries
            if e.storage_type in APPROVED_STORAGE_TYPES and e.is_shared
        ]
        transient = [
            e for e in self._entries
            if e.storage_type in TRANSIENT_STORAGE_TYPES
        ]
        return StatelessAuditReport(
            entries=list(self._entries),
            violations=violations,
            approved=approved,
            transient=transient,
        )

    def assert_no_violations(self) -> None:
        """Raise ``ForbiddenLocalStateError`` if any LOCAL_DISK entries exist."""
        report = self.audit()
        if not report.is_compliant:
            names = [e.name for e in report.violations]
            raise ForbiddenLocalStateError(
                f"Statelessness violation: {len(report.violations)} forbidden "
                f"LOCAL_DISK state entries found: {names}. "
                "Migrate to DATABASE or EXTERNAL_CACHE storage."
            )


# ---------------------------------------------------------------------------
# BE-2: Cross-instance token validation
# ---------------------------------------------------------------------------


class CrossInstanceTokenValidator:
    """Validates session tokens without per-instance store lookups (BE-2).

    In the current PropelIQ implementation, session tokens are opaque UUIDs
    stored in ``InMemorySessionStore`` (per-instance).  This class documents
    the migration path to signed tokens that can be validated on any instance
    without consulting a shared store.

    For cross-instance auth consistency today, the application must either:
      a) Use a shared database / Redis session store, OR
      b) Migrate to signed tokens (HMAC-SHA256 or JWT) with embedded claims.

    ``validate_stateless`` demonstrates option (b): given a pre-parsed payload
    (from a signed token), it verifies the claim structure without any store
    lookup.  This is the target state for full statelessness.
    """

    def validate_stateless(self, token: str, payload: dict[str, Any]) -> bool:
        """Validate token claims without querying a per-instance session store.

        Parameters
        ----------
        token       The raw token string (opaque UUID or signed token).
        payload     Pre-parsed/verified claims dict.  Must contain at minimum
                    ``user_id`` (or ``sub``) and ``role``.

        Returns True if the payload represents a valid active session.

        In the target state (HMAC-signed tokens), ``payload`` is the decoded
        and signature-verified body — no external lookup is required.
        """
        if not token or not payload:
            return False
        user_id = payload.get("user_id") or payload.get("sub")
        role = payload.get("role")
        return bool(user_id and role)

    def describe_migration(self) -> dict[str, Any]:
        """Describe the steps to migrate from per-instance to stateless auth."""
        return {
            "current_state": (
                "Opaque UUID tokens in per-instance InMemorySessionStore. "
                "Token validation requires the instance that created the session."
            ),
            "target_state": (
                "HMAC-SHA256 signed tokens with embedded claims (user_id, role, exp). "
                "Any instance validates any token using only the shared signing key."
            ),
            "migration_steps": [
                "1. Embed user_id, role, and exp (expiry) in the token payload.",
                "2. Sign the payload with HMAC-SHA256 using a key from env/secrets manager.",
                "3. On validation: verify HMAC signature + check exp; no store lookup.",
                "4. Store revoked tokens in shared DB or Redis with TTL for logout support.",
                "5. Rotate signing key via key versioning (include kid in token header).",
            ],
            "benefits": [
                "Any instance validates any token without shared in-memory state.",
                "Horizontal scaling without sticky sessions.",
                "Token validation survives instance restart.",
                "Revocation list is the only shared state required.",
            ],
        }

    def is_migration_complete(self) -> bool:
        """Returns False — migration is planned but not yet complete.

        Update to True once HMAC-signed tokens replace opaque UUIDs.
        """
        return False


# ---------------------------------------------------------------------------
# BE-3 / DOC-1: Statelessness policy reference
# ---------------------------------------------------------------------------


class StatelessnessPolicy:
    """Documents the statelessness contract for the PropelIQ API (DOC-1).

    Prohibited and approved patterns are machine-readable for use in automated
    architecture checks and documentation generation.
    """

    PROHIBITED_PATTERNS: list[str] = [
        "Writing user session data to local filesystem",
        "Storing session tokens in instance-local dict without shared backing",
        "Writing uploaded files to local disk without shared storage (S3/NFS)",
        "Caching per-user preferences in module-level dict across requests",
        "Persisting workflow state in a local SQLite file not accessible to peers",
    ]

    APPROVED_PATTERNS: list[str] = [
        "Reading from shared SQLite/PostgreSQL database (is_shared=True)",
        "Per-request in-memory computation (never persisted across requests)",
        "HMAC-SHA256 / JWT signed tokens with embedded claims (no server store)",
        "Redis/Valkey for shared ephemeral state with TTL-backed keys",
        "Shared object storage (S3/Azure Blob) for uploaded files",
        "Audit events written to shared database (not local log file)",
    ]

    def is_pattern_approved(self, description: str) -> bool:
        """Return True when the described pattern matches a known-approved pattern.

        Case-insensitive substring match against ``APPROVED_PATTERNS``.
        Returns False if it also matches a prohibited pattern (prohibited wins).
        """
        lower = description.lower()
        for prohibited in self.PROHIBITED_PATTERNS:
            if prohibited.lower() in lower or lower in prohibited.lower():
                return False
        for approved in self.APPROVED_PATTERNS:
            if approved.lower() in lower or lower in approved.lower():
                return True
        return False


# ---------------------------------------------------------------------------
# Module-level audit runner (pre-populated with known PropelIQ state entries)
# ---------------------------------------------------------------------------

_PROPELIQ_AUDIT = StatelessAuditRunner()
"""Pre-populated audit runner with known PropelIQ state entries (BE-1/BE-3).

Entries reflect the current (brownfield) state of the application.
Transient IN_MEMORY stores are acceptable; no LOCAL_DISK entries should exist.
"""

_PROPELIQ_AUDIT.register(StateEntry(
    name="session_store",
    storage_type=StateStorageType.IN_MEMORY,
    owner_module="src.web_app",
    is_shared=False,
    description="Per-instance session UUID store (migration target: HMAC tokens)",
))
_PROPELIQ_AUDIT.register(StateEntry(
    name="appointments",
    storage_type=StateStorageType.DATABASE,
    owner_module="src.booking_service",
    is_shared=True,
    description="SQLite appointment records — shared via file path env var",
))
_PROPELIQ_AUDIT.register(StateEntry(
    name="audit_log",
    storage_type=StateStorageType.DATABASE,
    owner_module="src.audit_storage",
    is_shared=True,
    description="Append-only audit event store in SQLite",
))
_PROPELIQ_AUDIT.register(StateEntry(
    name="mfa_enrollment_store",
    storage_type=StateStorageType.IN_MEMORY,
    owner_module="src.mfa_service",
    is_shared=False,
    description="Per-instance MFA enrollment state (migration target: shared DB)",
))
_PROPELIQ_AUDIT.register(StateEntry(
    name="mfa_backup_code_store",
    storage_type=StateStorageType.IN_MEMORY,
    owner_module="src.mfa_service",
    is_shared=False,
    description="Per-instance MFA backup code hashes (migration target: shared DB)",
))
_PROPELIQ_AUDIT.register(StateEntry(
    name="admin_change_log",
    storage_type=StateStorageType.IN_MEMORY,
    owner_module="src.web_app",
    is_shared=False,
    description="Per-instance admin operation log (migration target: audit DB)",
))
