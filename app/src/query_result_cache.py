"""
EP-008 US-091: Query Result Caching (Redis)

BE-1    Read-heavy query caching — ``QueryResultCache.get()`` / ``set()``
        wrap any callable that produces a serialisable result.  Approved
        query patterns are listed in ``CACHED_QUERY_PATTERNS``; only those
        patterns may be stored.  The cache key is derived from the pattern
        name and the caller-supplied parameters.

BE-2    Invalidation strategy — ``QueryResultCache.invalidate()`` removes one
        entry by key; ``invalidate_pattern()`` evicts every key belonging to a
        named pattern; ``invalidate_table()`` evicts all entries whose pattern
        maps to a given table.  TTL-based expiry is enforced on every ``get()``.

BE-3    Graceful fallback — when the backend raises
        ``CacheBackendUnavailableError`` every operation silently no-ops and
        the caller falls back to the database.  The manager records each outage
        event for operational review.

OPS-1   Hit / miss monitoring — every ``get()`` increments either the hit or
        miss counter for the pattern name.  ``CacheMetrics.hit_ratio()``
        exposes the running ratio.  ``CacheMetrics.summary()`` returns the
        full diagnostic snapshot used for dashboards.

INFRA-1 Cache namespace and security — ``CacheNamespaceConfig`` holds the
        Redis namespace prefix, per-pattern TTLs, and access config.  All
        keys follow the pattern::

            propeliq:qcache:<pattern_name>:<hex_digest_of_params>

        No PHI may appear in cache values or keys (same allow-list contract
        as US-088).

Injectable backend pattern:
  Tests use ``InMemoryQueryCache``.
  Production wires in a ``RedisQueryCacheAdapter`` with a real redis-py
  connection.  ``UnavailableQueryCache`` simulates Redis downtime.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol


# ---------------------------------------------------------------------------
# Constants (INFRA-1)
# ---------------------------------------------------------------------------

CACHE_KEY_PREFIX: str = "propeliq:qcache:"

# Default TTLs per approved query pattern (seconds).
DEFAULT_TTL_SECONDS: int = 300          # 5 minutes generic
SLOT_SEARCH_TTL_SECONDS: int = 60       # slot availability — shorter TTL
PROVIDER_LIST_TTL_SECONDS: int = 600    # provider catalogue — longer TTL
SPECIALTY_TTL_SECONDS: int = 3600       # specialty list — rarely changes

# Maximum number of outage events kept in memory.
MAX_OUTAGE_EVENTS: int = 200


# ---------------------------------------------------------------------------
# Approved query patterns (BE-1 allow-list)
# ---------------------------------------------------------------------------

#: Mapping: pattern_name → {table, default_ttl, description}
CACHED_QUERY_PATTERNS: dict[str, dict[str, Any]] = {
    "available_slots": {
        "table": "appointments",
        "default_ttl": SLOT_SEARCH_TTL_SECONDS,
        "description": "Search available appointment slots by date/provider",
    },
    "provider_list": {
        "table": "providers",
        "default_ttl": PROVIDER_LIST_TTL_SECONDS,
        "description": "Active provider catalogue (specialty-filtered)",
    },
    "specialty_list": {
        "table": "specialties",
        "default_ttl": SPECIALTY_TTL_SECONDS,
        "description": "Full specialty catalogue",
    },
    "patient_profile": {
        "table": "patient_profiles",
        "default_ttl": DEFAULT_TTL_SECONDS,
        "description": "Patient profile by ID (non-PHI summary fields only)",
    },
    "appointment_summary": {
        "table": "appointments",
        "default_ttl": DEFAULT_TTL_SECONDS,
        "description": "Single appointment summary (non-PHI fields)",
    },
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CacheBackendUnavailableError(Exception):
    """Raised by a backend when the underlying store is unreachable."""


class CachePatternNotApprovedError(Exception):
    """Raised when a caller tries to cache a query pattern not in the allow-list."""


class CachePHIViolationError(Exception):
    """Raised when a cached value contains a forbidden PHI/PII field."""


# ---------------------------------------------------------------------------
# PHI allow-list (mirrors US-088 — only opaque IDs and non-PHI metadata)
# ---------------------------------------------------------------------------

CACHE_VALUE_ALLOWED_FIELDS: frozenset[str] = frozenset({
    "id", "appointment_id", "provider_id", "specialty_id",
    "appointment_date", "start_time", "end_time", "location",
    "status", "duration_minutes", "name", "specialty_name",
    "is_active", "credentials", "slot_count", "available_count",
})

CACHE_VALUE_FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    "email", "phone", "first_name", "last_name", "dob", "date_of_birth",
    "address", "ssn", "insurance_id", "medical_record_number",
    "patient_email", "patient_phone",
})


def validate_cache_value_no_phi(value: Any) -> None:
    """Raise CachePHIViolationError if *value* contains PHI/PII fields.

    Only validates dict-type values (row-level); list values are checked
    element-by-element.
    """
    if isinstance(value, list):
        for item in value:
            validate_cache_value_no_phi(item)
        return
    if not isinstance(value, dict):
        return
    for key in value:
        if key in CACHE_VALUE_FORBIDDEN_FIELDS:
            raise CachePHIViolationError(
                f"Cache value contains forbidden PHI/PII field: '{key}'"
            )


# ---------------------------------------------------------------------------
# Cache entry
# ---------------------------------------------------------------------------


@dataclass
class CacheEntry:
    """A single cached query result.

    Attributes
    ----------
    pattern_name    Approved query pattern this entry belongs to.
    cache_key       Full Redis key (prefix + pattern + param digest).
    value           The serialisable query result (list[dict] or dict).
    stored_at       Unix timestamp when the entry was stored.
    expires_at      Unix timestamp when the entry expires.
    hit_count       Number of times this entry has been served.
    """

    pattern_name: str
    cache_key: str
    value: Any
    stored_at: float
    expires_at: float
    hit_count: int = 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def ttl_remaining(self) -> float:
        return self.expires_at - time.time()

    def touch(self) -> None:
        self.hit_count += 1


# ---------------------------------------------------------------------------
# Backend Protocol
# ---------------------------------------------------------------------------


class QueryCacheBackendProtocol(Protocol):
    """Abstraction over a Redis (or in-memory) query cache store."""

    def get(self, key: str) -> CacheEntry | None: ...
    def set(self, entry: CacheEntry) -> None: ...
    def delete(self, key: str) -> bool: ...
    def keys_for_pattern(self, pattern_name: str) -> list[str]: ...
    def ping(self) -> bool: ...
    def clear(self) -> None: ...


# ---------------------------------------------------------------------------
# In-memory backend (test double + fallback)
# ---------------------------------------------------------------------------


class InMemoryQueryCache:
    """Thread-unsafe in-memory cache backend for tests and local dev.

    Expired entries are lazily evicted on ``get()``.
    """

    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}

    def get(self, key: str) -> CacheEntry | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._store[key]
            return None
        return entry

    def set(self, entry: CacheEntry) -> None:
        self._store[entry.cache_key] = entry

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def keys_for_pattern(self, pattern_name: str) -> list[str]:
        return [k for k, e in self._store.items() if e.pattern_name == pattern_name]

    def ping(self) -> bool:
        return True

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# Unavailable backend (simulates Redis downtime — BE-3)
# ---------------------------------------------------------------------------


class UnavailableQueryCache:
    """Always raises CacheBackendUnavailableError — simulates Redis outage."""

    def get(self, key: str) -> CacheEntry | None:
        raise CacheBackendUnavailableError("Redis unreachable.")

    def set(self, entry: CacheEntry) -> None:
        raise CacheBackendUnavailableError("Redis unreachable.")

    def delete(self, key: str) -> bool:
        raise CacheBackendUnavailableError("Redis unreachable.")

    def keys_for_pattern(self, pattern_name: str) -> list[str]:
        raise CacheBackendUnavailableError("Redis unreachable.")

    def ping(self) -> bool:
        return False

    def clear(self) -> None:
        raise CacheBackendUnavailableError("Redis unreachable.")


# ---------------------------------------------------------------------------
# OPS-1: Metrics
# ---------------------------------------------------------------------------


@dataclass
class PatternMetrics:
    """Hit/miss counters for a single query pattern."""

    pattern_name: str
    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    phi_violations: int = 0

    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_name": self.pattern_name,
            "hits": self.hits,
            "misses": self.misses,
            "invalidations": self.invalidations,
            "phi_violations": self.phi_violations,
            "hit_ratio": round(self.hit_ratio(), 4),
        }


class CacheMetrics:
    """Aggregate hit/miss monitoring for all patterns (OPS-1).

    Usage::

        metrics = CacheMetrics()
        metrics.record_hit("available_slots")
        metrics.record_miss("available_slots")
        print(metrics.hit_ratio("available_slots"))   # 0.5
        print(metrics.summary())
    """

    def __init__(self) -> None:
        self._patterns: dict[str, PatternMetrics] = {}

    def _ensure(self, pattern_name: str) -> PatternMetrics:
        if pattern_name not in self._patterns:
            self._patterns[pattern_name] = PatternMetrics(pattern_name)
        return self._patterns[pattern_name]

    def record_hit(self, pattern_name: str) -> None:
        self._ensure(pattern_name).hits += 1

    def record_miss(self, pattern_name: str) -> None:
        self._ensure(pattern_name).misses += 1

    def record_invalidation(self, pattern_name: str, count: int = 1) -> None:
        self._ensure(pattern_name).invalidations += count

    def record_phi_violation(self, pattern_name: str) -> None:
        self._ensure(pattern_name).phi_violations += 1

    def hit_ratio(self, pattern_name: str) -> float:
        pm = self._patterns.get(pattern_name)
        return pm.hit_ratio() if pm else 0.0

    def total_hits(self) -> int:
        return sum(p.hits for p in self._patterns.values())

    def total_misses(self) -> int:
        return sum(p.misses for p in self._patterns.values())

    def overall_hit_ratio(self) -> float:
        t = self.total_hits() + self.total_misses()
        return self.total_hits() / t if t > 0 else 0.0

    def summary(self) -> dict[str, Any]:
        return {
            "total_hits": self.total_hits(),
            "total_misses": self.total_misses(),
            "overall_hit_ratio": round(self.overall_hit_ratio(), 4),
            "patterns": {
                name: pm.to_dict()
                for name, pm in self._patterns.items()
            },
        }

    def pattern_names(self) -> list[str]:
        return list(self._patterns.keys())


# ---------------------------------------------------------------------------
# INFRA-1: Namespace configuration
# ---------------------------------------------------------------------------


@dataclass
class CacheNamespaceConfig:
    """Redis namespace and security configuration for query result caches.

    Attributes
    ----------
    namespace_prefix    Redis key prefix (e.g. ``"propeliq:qcache:"``)
    default_ttl         Fallback TTL when the pattern has no explicit TTL.
    max_value_size_kb   Reject values larger than this (guards against cache
                        pollution with large result sets).
    tls_enabled         Production requirement: TLS to Redis.
    auth_password       Production requirement: AUTH password.
    """

    namespace_prefix: str = CACHE_KEY_PREFIX
    default_ttl: int = DEFAULT_TTL_SECONDS
    max_value_size_kb: int = 512
    tls_enabled: bool = True
    auth_password: str | None = None

    def is_production_safe(self) -> bool:
        return self.tls_enabled and bool(self.auth_password)

    def validate(self) -> list[str]:
        warnings: list[str] = []
        if not self.tls_enabled:
            warnings.append("TLS is disabled — enable TLS for production Redis.")
        if not self.auth_password:
            warnings.append("AUTH password not set — Redis is unauthenticated.")
        return warnings


# ---------------------------------------------------------------------------
# Key builder (INFRA-1)
# ---------------------------------------------------------------------------


def build_cache_key(
    pattern_name: str,
    params: dict[str, Any],
    prefix: str = CACHE_KEY_PREFIX,
) -> str:
    """Build a deterministic cache key from pattern name + parameter dict.

    Key format::
        propeliq:qcache:<pattern_name>:<sha256_hex_of_sorted_json_params>
    """
    serialised = json.dumps(params, sort_keys=True, default=str)
    digest = hashlib.sha256(serialised.encode()).hexdigest()[:16]
    return f"{prefix}{pattern_name}:{digest}"


# ---------------------------------------------------------------------------
# BE-1 / BE-2 / BE-3: QueryResultCache
# ---------------------------------------------------------------------------


class QueryResultCache:
    """Redis-backed (or in-memory) query result cache (BE-1 / BE-2 / BE-3).

    Usage::

        cache   = QueryResultCache(InMemoryQueryCache())
        results = cache.get_or_set(
            "available_slots",
            {"date": "2026-07-01", "specialty_id": 3},
            loader=lambda: db.query("SELECT …"),
        )

    All BE-3 Redis outages are silently caught; the ``loader`` is always
    called as fallback so the caller never receives an error due to cache
    unavailability.

    PHI check (BE-1): values produced by ``loader`` are validated against
    ``CACHE_VALUE_FORBIDDEN_FIELDS`` before storage.  A ``CachePHIViolationError``
    is raised and the value is never written to cache.
    """

    def __init__(
        self,
        backend: QueryCacheBackendProtocol,
        metrics: CacheMetrics | None = None,
        config: CacheNamespaceConfig | None = None,
    ) -> None:
        self._backend = backend
        self._metrics = metrics or CacheMetrics()
        self._config = config or CacheNamespaceConfig()
        self._outage_events: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # BE-1: Read path
    # ------------------------------------------------------------------

    def get(
        self,
        pattern_name: str,
        params: dict[str, Any],
    ) -> Any | None:
        """Return cached value for *pattern_name* + *params*, or None on miss."""
        _assert_pattern_approved(pattern_name)
        key = build_cache_key(pattern_name, params, self._config.namespace_prefix)
        try:
            entry = self._backend.get(key)
        except CacheBackendUnavailableError as exc:
            self._record_outage("get", str(exc))
            return None
        if entry is None:
            self._metrics.record_miss(pattern_name)
            return None
        entry.touch()
        self._metrics.record_hit(pattern_name)
        return entry.value

    def set(
        self,
        pattern_name: str,
        params: dict[str, Any],
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Store *value* for *pattern_name* + *params*.

        Returns True on success, False on backend outage.
        Raises ``CachePHIViolationError`` if the value contains PHI.
        """
        _assert_pattern_approved(pattern_name)
        validate_cache_value_no_phi(value)
        key = build_cache_key(pattern_name, params, self._config.namespace_prefix)
        effective_ttl = ttl if ttl is not None else (
            CACHED_QUERY_PATTERNS[pattern_name]["default_ttl"]
        )
        now = time.time()
        entry = CacheEntry(
            pattern_name=pattern_name,
            cache_key=key,
            value=value,
            stored_at=now,
            expires_at=now + effective_ttl,
        )
        try:
            self._backend.set(entry)
        except CacheBackendUnavailableError as exc:
            self._record_outage("set", str(exc))
            return False
        return True

    def get_or_set(
        self,
        pattern_name: str,
        params: dict[str, Any],
        loader: Callable[[], Any],
        ttl: int | None = None,
    ) -> Any:
        """Return cached value, or call *loader*, cache its result, and return it.

        Always calls *loader* when the backend is unavailable (BE-3 fallback).
        """
        cached = self.get(pattern_name, params)
        if cached is not None:
            return cached
        value = loader()
        # Attempt to cache (silently no-ops on outage or PHI violation)
        try:
            self.set(pattern_name, params, value, ttl=ttl)
        except CachePHIViolationError:
            self._metrics.record_phi_violation(pattern_name)
        return value

    # ------------------------------------------------------------------
    # BE-2: Invalidation
    # ------------------------------------------------------------------

    def invalidate(self, pattern_name: str, params: dict[str, Any]) -> bool:
        """Evict the single entry identified by *pattern_name* + *params*."""
        _assert_pattern_approved(pattern_name)
        key = build_cache_key(pattern_name, params, self._config.namespace_prefix)
        try:
            removed = self._backend.delete(key)
        except CacheBackendUnavailableError as exc:
            self._record_outage("invalidate", str(exc))
            return False
        if removed:
            self._metrics.record_invalidation(pattern_name)
        return removed

    def invalidate_pattern(self, pattern_name: str) -> int:
        """Evict all entries for *pattern_name*.  Returns the count evicted."""
        _assert_pattern_approved(pattern_name)
        try:
            keys = self._backend.keys_for_pattern(pattern_name)
        except CacheBackendUnavailableError as exc:
            self._record_outage("invalidate_pattern", str(exc))
            return 0
        count = 0
        for key in keys:
            try:
                if self._backend.delete(key):
                    count += 1
            except CacheBackendUnavailableError:
                break
        self._metrics.record_invalidation(pattern_name, count)
        return count

    def invalidate_table(self, table: str) -> int:
        """Evict all entries whose approved pattern maps to *table*."""
        total = 0
        for pattern_name, meta in CACHED_QUERY_PATTERNS.items():
            if meta["table"] == table:
                total += self.invalidate_pattern(pattern_name)
        return total

    # ------------------------------------------------------------------
    # BE-3 / OPS-1: Availability and observability
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        try:
            return self._backend.ping()
        except CacheBackendUnavailableError:
            return False

    def outage_events(self) -> list[dict[str, Any]]:
        return list(self._outage_events)

    def metrics(self) -> CacheMetrics:
        return self._metrics

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_outage(self, operation: str, detail: str) -> None:
        event = {
            "operation": operation,
            "detail": detail,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
        self._outage_events.append(event)
        if len(self._outage_events) > MAX_OUTAGE_EVENTS:
            self._outage_events = self._outage_events[-MAX_OUTAGE_EVENTS:]


# ---------------------------------------------------------------------------
# Internal guard
# ---------------------------------------------------------------------------


def _assert_pattern_approved(pattern_name: str) -> None:
    if pattern_name not in CACHED_QUERY_PATTERNS:
        raise CachePatternNotApprovedError(
            f"Query pattern '{pattern_name}' is not in the approved cache list. "
            f"Approved patterns: {sorted(CACHED_QUERY_PATTERNS)}"
        )
