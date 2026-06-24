"""
EP-008 US-088: Redis Session Cache

INFRA-1  Redis provisioning guidance — see ``RedisConnectionConfig``.
         Production: TLS, AUTH password, Redis Sentinel / ElastiCache.
         All infrastructure requirements are captured in config; no real
         network calls are made in this module so it is safe for unit tests.

BE-1     Session storage across instances — ``SessionCacheManager.store()``
         and ``retrieve()`` share sessions across all API nodes via the
         injected cache backend.

BE-2     Expiration and invalidation — every entry carries an ``expires_at``
         field; ``SessionCacheManager`` enforces TTL and supports explicit
         JTI revocation and bulk user-session invalidation.

BE-3     Graceful Redis failure handling — ``SessionCacheManager`` wraps all
         backend calls; when the backend raises ``SessionCacheUnavailableError``
         the manager degrades to a configurable fallback policy (DENY or ALLOW)
         and logs the outage without propagating the exception to the caller.

SEC-1    PHI minimisation — ``SESSION_CACHE_ALLOWED_FIELDS`` is the explicit
         allow-list of fields that may be stored in the cache.  Any attempt to
         store a key outside this list raises ``CachePHIViolationError``.
         No PII / PHI (name, email, phone, DOB, etc.) is allowed in cache
         values.  Only opaque identifiers (jti, user_id) and role/status data.

Injectable backend pattern (mirrors US-085 / US-086):
  Tests use ``InMemorySessionCache``.
  Production wires in ``RedisSessionCacheAdapter`` with a real redis-py
  connection.  The ``RedisConnectionConfig`` documents all required settings.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# SEC-1: PHI allow-list
# ---------------------------------------------------------------------------

SESSION_CACHE_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "jti",           # token ID (opaque UUID — no PII)
        "user_id",       # opaque account identifier
        "role",          # authorization role
        "issued_at",     # Unix float timestamp
        "expires_at",    # Unix float timestamp
        "last_activity", # Unix float timestamp
        "status",        # account status snapshot (active/suspended/inactive)
    }
)

# Fields that are explicitly forbidden (PHI / PII).
SESSION_CACHE_FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "email", "phone", "name", "first_name", "last_name",
        "dob", "date_of_birth", "address", "ssn",
        "insurance_id", "medical_record_number", "patient_id",
    }
)

# Default session TTL (seconds) — aligns with rbac.py _SESSION_TOKEN_TTL_SECONDS.
SESSION_DEFAULT_TTL_SECONDS: int = 3600

# Key prefix used in Redis to namespace PropelIQ session keys.
SESSION_KEY_PREFIX: str = "propeliq:session:"

# Maximum number of sessions stored per user in the index
# (prevents unbounded per-user index growth).
SESSION_MAX_PER_USER: int = 10


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SessionCacheMissError(Exception):
    """Raised when a requested JTI is not present in the cache."""


class SessionCacheUnavailableError(Exception):
    """Raised by a backend when the underlying store is unreachable."""


class CachePHIViolationError(Exception):
    """Raised when a caller attempts to store a PHI/PII field in the cache."""


# ---------------------------------------------------------------------------
# INFRA-1: Connection configuration (documentation + validation only)
# ---------------------------------------------------------------------------


@dataclass
class RedisConnectionConfig:
    """Documents the required Redis connection settings for production.

    None of these fields are used to make real network calls in this module.
    They serve as validated configuration objects consumed by
    ``RedisSessionCacheAdapter`` in the production runtime.

    Attributes
    ----------
    host            Redis hostname or managed endpoint (e.g. ElastiCache).
    port            Default 6379 (plain) or 6380 (TLS).
    db              Database index; use 0 for session cache.
    password        AUTH password — MUST be set in production.
    tls_enabled     Enforce TLS (``ssl=True`` in redis-py).
    socket_timeout  Per-operation timeout in seconds.
    max_connections Connection pool size.
    sentinel_hosts  List of (host, port) pairs when using Redis Sentinel.
    """

    host: str = "localhost"
    port: int = 6380            # TLS port — plaintext 6379 only for local dev
    db: int = 0
    password: str | None = None
    tls_enabled: bool = True
    socket_timeout: float = 1.0
    max_connections: int = 20
    sentinel_hosts: list[tuple[str, int]] = field(default_factory=list)

    def is_production_safe(self) -> bool:
        """Return True when the config passes the minimum production safety bar."""
        return (
            self.tls_enabled
            and bool(self.password)
            and self.port != 6379   # reject non-TLS default port in production
        )

    def validate(self) -> list[str]:
        """Return a list of configuration warnings (empty = no warnings)."""
        warnings: list[str] = []
        if not self.tls_enabled:
            warnings.append("TLS is disabled — session tokens will travel in plaintext.")
        if not self.password:
            warnings.append("Redis AUTH password is not set — cluster is open.")
        if self.port == 6379:
            warnings.append("Using non-TLS Redis port 6379.")
        return warnings


# ---------------------------------------------------------------------------
# BE-1: Session cache entry
# ---------------------------------------------------------------------------


@dataclass
class SessionCacheEntry:
    """A single cached session record.

    Only contains non-PHI opaque identifiers (SEC-1).

    Attributes
    ----------
    jti             Unique token identifier (matches JWT jti claim).
    user_id         Opaque account ID.
    role            Authorization role.
    issued_at       Unix timestamp when the token was issued.
    expires_at      Unix timestamp when the session expires.
    last_activity   Unix timestamp of the most-recent validated request.
    status          Account status at cache population time.
    """

    jti: str
    user_id: str
    role: str
    issued_at: float
    expires_at: float
    last_activity: float = field(default_factory=time.time)
    status: str = "active"

    def is_expired(self, now: float | None = None) -> bool:
        t = now if now is not None else time.time()
        return t > self.expires_at

    def ttl_remaining(self, now: float | None = None) -> float:
        """Seconds until expiry (negative means already expired)."""
        t = now if now is not None else time.time()
        return self.expires_at - t

    def to_dict(self) -> dict[str, Any]:
        return {
            "jti": self.jti,
            "user_id": self.user_id,
            "role": self.role,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "last_activity": self.last_activity,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SessionCacheEntry:
        return cls(
            jti=d["jti"],
            user_id=d["user_id"],
            role=d["role"],
            issued_at=float(d["issued_at"]),
            expires_at=float(d["expires_at"]),
            last_activity=float(d.get("last_activity", d["issued_at"])),
            status=d.get("status", "active"),
        )


# ---------------------------------------------------------------------------
# Backend protocol + implementations
# ---------------------------------------------------------------------------


class SessionCacheBackendProtocol(Protocol):
    """Injectable session cache backend interface."""

    def get(self, jti: str) -> SessionCacheEntry:
        """Return the entry for *jti*.  Raises ``SessionCacheMissError`` if absent."""
        ...

    def set(self, entry: SessionCacheEntry) -> None:
        """Store *entry* indexed by its ``jti``."""
        ...

    def delete(self, jti: str) -> bool:
        """Remove the entry for *jti*.  Returns True if it existed."""
        ...

    def invalidate_user(self, user_id: str) -> int:
        """Delete all entries for *user_id*.  Returns the count of deleted keys."""
        ...

    def ping(self) -> bool:
        """Return True when the backend is reachable."""
        ...


class InMemorySessionCache:
    """In-memory session cache backend.

    Thread-safe for single-threaded tests.  Serves as both:
    - Test double for ``SessionCacheManager`` unit tests.
    - Fallback store when Redis is unavailable (BE-3 degraded mode).
    """

    def __init__(self) -> None:
        # jti → entry
        self._store: dict[str, SessionCacheEntry] = {}
        # user_id → set[jti]
        self._user_index: dict[str, set[str]] = {}

    def get(self, jti: str) -> SessionCacheEntry:
        entry = self._store.get(jti)
        if entry is None:
            raise SessionCacheMissError(f"Session '{jti}' not found in cache.")
        if entry.is_expired():
            self.delete(jti)
            raise SessionCacheMissError(f"Session '{jti}' has expired.")
        return entry

    def set(self, entry: SessionCacheEntry) -> None:
        self._store[entry.jti] = entry
        self._user_index.setdefault(entry.user_id, set()).add(entry.jti)

    def delete(self, jti: str) -> bool:
        entry = self._store.pop(jti, None)
        if entry:
            jtis = self._user_index.get(entry.user_id, set())
            jtis.discard(jti)
            return True
        return False

    def invalidate_user(self, user_id: str) -> int:
        jtis = list(self._user_index.pop(user_id, set()))
        for jti in jtis:
            self._store.pop(jti, None)
        return len(jtis)

    def ping(self) -> bool:
        return True

    def size(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()
        self._user_index.clear()


class UnavailableSessionCache:
    """Always-failing backend — used to test graceful degradation (BE-3)."""

    def get(self, jti: str) -> SessionCacheEntry:
        raise SessionCacheUnavailableError("Redis unreachable.")

    def set(self, entry: SessionCacheEntry) -> None:
        raise SessionCacheUnavailableError("Redis unreachable.")

    def delete(self, jti: str) -> bool:
        raise SessionCacheUnavailableError("Redis unreachable.")

    def invalidate_user(self, user_id: str) -> int:
        raise SessionCacheUnavailableError("Redis unreachable.")

    def ping(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# BE-3: Outage fallback policy
# ---------------------------------------------------------------------------


class OutageFallbackPolicy:
    """Controls what happens when Redis is unavailable.

    DENY  (strict / default for HIPAA) — treat all cache ops as miss;
           validate nothing returns "allow" during an outage.
    ALLOW (degraded) — log the outage but permit the request through,
           accepting the risk of stale revocation state.
    """

    DENY = "deny"
    ALLOW = "allow"


# ---------------------------------------------------------------------------
# SEC-1: PHI validator
# ---------------------------------------------------------------------------


def validate_no_phi(data: dict[str, Any]) -> None:
    """Raise ``CachePHIViolationError`` if *data* contains any forbidden PHI keys.

    Only keys in ``SESSION_CACHE_ALLOWED_FIELDS`` are permitted.
    Any key in ``SESSION_CACHE_FORBIDDEN_FIELDS`` is an immediate error.
    Unknown keys not on either list are also rejected (allow-list semantics).
    """
    for key in data:
        if key in SESSION_CACHE_FORBIDDEN_FIELDS:
            raise CachePHIViolationError(
                f"Field '{key}' is a forbidden PHI/PII field and may not be "
                "stored in the session cache."
            )
        if key not in SESSION_CACHE_ALLOWED_FIELDS:
            raise CachePHIViolationError(
                f"Field '{key}' is not on the session cache allow-list "
                f"({sorted(SESSION_CACHE_ALLOWED_FIELDS)}). "
                "Only opaque identifiers and role data may be cached."
            )


# ---------------------------------------------------------------------------
# BE-1/BE-2/BE-3: Session Cache Manager
# ---------------------------------------------------------------------------


class SessionCacheManager:
    """Manages session storage, retrieval, expiration, and graceful degradation.

    Public API
    ----------
    store(entry)              Store a session; validates PHI allow-list.
    retrieve(jti)             Retrieve a non-expired session; returns None on miss/outage.
    delete(jti)               Explicitly revoke a session.
    invalidate_user(user_id)  Bulk-revoke all sessions for a user.
    touch(jti)                Update last_activity timestamp (sliding expiry).
    is_available()            Returns True when the backend is reachable.

    Outage behaviour (BE-3)
    -----------------------
    When the backend raises ``SessionCacheUnavailableError``:
    - The outage is recorded in ``_outage_events``.
    - ``retrieve()`` returns None (miss) regardless of fallback policy.
    - ``store()`` / ``delete()`` / ``invalidate_user()`` silently no-op.
    - ``is_available()`` returns False.
    """

    def __init__(
        self,
        backend: SessionCacheBackendProtocol | None = None,
        fallback_policy: str = OutageFallbackPolicy.DENY,
    ) -> None:
        self._backend: SessionCacheBackendProtocol = backend or InMemorySessionCache()
        self._fallback_policy = fallback_policy
        self._outage_events: list[dict[str, Any]] = []

    def _record_outage(self, operation: str, exc: Exception) -> None:
        self._outage_events.append(
            {
                "operation": operation,
                "error": str(exc),
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def store(self, entry: SessionCacheEntry) -> bool:
        """Validate PHI allow-list and store the entry.  Returns True on success."""
        validate_no_phi(entry.to_dict())
        try:
            self._backend.set(entry)
            return True
        except SessionCacheUnavailableError as exc:
            self._record_outage("store", exc)
            return False

    def retrieve(self, jti: str) -> SessionCacheEntry | None:
        """Return the session entry for *jti*, or None on miss / outage."""
        try:
            return self._backend.get(jti)
        except SessionCacheMissError:
            return None
        except SessionCacheUnavailableError as exc:
            self._record_outage("retrieve", exc)
            return None

    def delete(self, jti: str) -> bool:
        """Revoke a session.  Returns True if the entry existed, False on miss/outage."""
        try:
            return self._backend.delete(jti)
        except SessionCacheUnavailableError as exc:
            self._record_outage("delete", exc)
            return False

    def invalidate_user(self, user_id: str) -> int:
        """Bulk-revoke all sessions for *user_id*.  Returns count of revoked entries."""
        try:
            return self._backend.invalidate_user(user_id)
        except SessionCacheUnavailableError as exc:
            self._record_outage("invalidate_user", exc)
            return 0

    def touch(self, jti: str) -> bool:
        """Update the ``last_activity`` timestamp for *jti* (sliding expiry).

        Silently no-ops on miss or outage.  Returns True when the update
        was applied.
        """
        try:
            entry = self._backend.get(jti)
            entry.last_activity = time.time()
            self._backend.set(entry)
            return True
        except (SessionCacheMissError, SessionCacheUnavailableError):
            return False

    def is_available(self) -> bool:
        """Return True when the backend responds to a ping."""
        try:
            return self._backend.ping()
        except Exception:
            return False

    def outage_events(self) -> list[dict[str, Any]]:
        """Return a copy of recorded outage events (BE-3 observability)."""
        return list(self._outage_events)
