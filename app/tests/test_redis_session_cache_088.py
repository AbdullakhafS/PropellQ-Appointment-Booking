"""
EP-008 US-088: Redis Session Cache — Test Suite

QA-1  Cross-Instance Session Tests  — retrieve from any instance
QA-2  Expiration Tests              — TTL and invalidation
QA-3  Redis Outage Tests            — graceful degradation
QA-4  Security Review Tests         — no PHI in cached values
"""
from __future__ import annotations

import time

import pytest

from src.redis_session_cache import (
    SESSION_CACHE_ALLOWED_FIELDS,
    SESSION_CACHE_FORBIDDEN_FIELDS,
    SESSION_DEFAULT_TTL_SECONDS,
    CachePHIViolationError,
    InMemorySessionCache,
    OutageFallbackPolicy,
    RedisConnectionConfig,
    SessionCacheEntry,
    SessionCacheMissError,
    SessionCacheManager,
    SessionCacheUnavailableError,
    UnavailableSessionCache,
    validate_no_phi,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> float:
    return time.time()


def _entry(
    jti: str = "jti-001",
    user_id: str = "U1",
    role: str = "staff",
    ttl: float = 3600.0,
    offset_seconds: float = 0.0,
) -> SessionCacheEntry:
    now = _now()
    return SessionCacheEntry(
        jti=jti,
        user_id=user_id,
        role=role,
        issued_at=now + offset_seconds,
        expires_at=now + ttl + offset_seconds,
        last_activity=now + offset_seconds,
    )


# ===========================================================================
# QA-1: Cross-Instance Session Tests (BE-1)
# ===========================================================================


class TestCrossInstanceSession:
    """QA-1 — Session stored on one instance is retrievable from any instance
    sharing the same backend."""

    def test_store_and_retrieve_returns_same_entry(self):
        mgr = SessionCacheManager(InMemorySessionCache())
        e = _entry()
        mgr.store(e)
        result = mgr.retrieve(e.jti)
        assert result is not None
        assert result.jti == e.jti
        assert result.user_id == e.user_id

    def test_retrieve_returns_none_for_unknown_jti(self):
        mgr = SessionCacheManager(InMemorySessionCache())
        assert mgr.retrieve("no-such-jti") is None

    def test_two_manager_instances_share_backend(self):
        """Simulates two API instances sharing the same cache backend."""
        backend = InMemorySessionCache()
        instance_a = SessionCacheManager(backend)
        instance_b = SessionCacheManager(backend)
        e = _entry()
        instance_a.store(e)
        assert instance_b.retrieve(e.jti) is not None

    def test_role_preserved_across_retrieval(self):
        mgr = SessionCacheManager(InMemorySessionCache())
        e = _entry(role="admin")
        mgr.store(e)
        assert mgr.retrieve(e.jti).role == "admin"

    def test_store_multiple_users_independently(self):
        mgr = SessionCacheManager(InMemorySessionCache())
        e1 = _entry(jti="j1", user_id="U1")
        e2 = _entry(jti="j2", user_id="U2")
        mgr.store(e1)
        mgr.store(e2)
        assert mgr.retrieve("j1").user_id == "U1"
        assert mgr.retrieve("j2").user_id == "U2"

    def test_touch_updates_last_activity(self):
        backend = InMemorySessionCache()
        mgr = SessionCacheManager(backend)
        e = _entry()
        mgr.store(e)
        old_activity = backend.get(e.jti).last_activity
        time.sleep(0.01)
        mgr.touch(e.jti)
        assert backend.get(e.jti).last_activity > old_activity

    def test_entry_to_dict_and_from_dict_roundtrip(self):
        e = _entry()
        restored = SessionCacheEntry.from_dict(e.to_dict())
        assert restored.jti == e.jti
        assert restored.user_id == e.user_id
        assert restored.role == e.role


# ===========================================================================
# QA-2: Expiration and Invalidation Tests (BE-2)
# ===========================================================================


class TestExpiration:
    """QA-2 — Sessions expire at TTL and can be explicitly revoked."""

    def test_expired_entry_raises_on_get(self):
        cache = InMemorySessionCache()
        e = _entry(ttl=-1.0)   # already expired
        cache._store[e.jti] = e  # bypass set() to inject expired entry
        with pytest.raises(SessionCacheMissError):
            cache.get(e.jti)

    def test_expired_entry_not_returned_by_manager(self):
        cache = InMemorySessionCache()
        e = _entry(ttl=-1.0)
        cache._store[e.jti] = e
        mgr = SessionCacheManager(cache)
        assert mgr.retrieve(e.jti) is None

    def test_ttl_remaining_positive_for_fresh_entry(self):
        e = _entry(ttl=3600.0)
        assert e.ttl_remaining() > 0

    def test_ttl_remaining_negative_for_expired(self):
        e = _entry(ttl=-1.0)
        assert e.ttl_remaining() < 0

    def test_is_expired_false_for_fresh_entry(self):
        assert not _entry(ttl=3600.0).is_expired()

    def test_is_expired_true_for_stale_entry(self):
        assert _entry(ttl=-1.0).is_expired()

    def test_delete_removes_session(self):
        mgr = SessionCacheManager(InMemorySessionCache())
        e = _entry()
        mgr.store(e)
        mgr.delete(e.jti)
        assert mgr.retrieve(e.jti) is None

    def test_delete_returns_true_when_existed(self):
        mgr = SessionCacheManager(InMemorySessionCache())
        e = _entry()
        mgr.store(e)
        assert mgr.delete(e.jti) is True

    def test_delete_returns_false_when_absent(self):
        mgr = SessionCacheManager(InMemorySessionCache())
        assert mgr.delete("ghost-jti") is False

    def test_invalidate_user_removes_all_sessions(self):
        backend = InMemorySessionCache()
        mgr = SessionCacheManager(backend)
        for i in range(3):
            mgr.store(_entry(jti=f"j{i}", user_id="U99"))
        count = mgr.invalidate_user("U99")
        assert count == 3
        assert backend.size() == 0

    def test_invalidate_user_does_not_affect_other_users(self):
        backend = InMemorySessionCache()
        mgr = SessionCacheManager(backend)
        mgr.store(_entry(jti="u1j1", user_id="U1"))
        mgr.store(_entry(jti="u2j1", user_id="U2"))
        mgr.invalidate_user("U1")
        assert mgr.retrieve("u2j1") is not None

    def test_session_default_ttl_constant(self):
        assert SESSION_DEFAULT_TTL_SECONDS == 3600


# ===========================================================================
# QA-3: Redis Outage Tests — graceful degradation (BE-3)
# ===========================================================================


class TestRedisOutage:
    """QA-3 — Manager degrades gracefully when Redis is unavailable."""

    def test_is_available_false_when_backend_down(self):
        mgr = SessionCacheManager(UnavailableSessionCache())
        assert mgr.is_available() is False

    def test_is_available_true_when_backend_up(self):
        mgr = SessionCacheManager(InMemorySessionCache())
        assert mgr.is_available() is True

    def test_store_returns_false_on_outage(self):
        mgr = SessionCacheManager(UnavailableSessionCache())
        assert mgr.store(_entry()) is False

    def test_retrieve_returns_none_on_outage(self):
        mgr = SessionCacheManager(UnavailableSessionCache())
        assert mgr.retrieve("any-jti") is None

    def test_delete_returns_false_on_outage(self):
        mgr = SessionCacheManager(UnavailableSessionCache())
        assert mgr.delete("any-jti") is False

    def test_invalidate_user_returns_zero_on_outage(self):
        mgr = SessionCacheManager(UnavailableSessionCache())
        assert mgr.invalidate_user("U1") == 0

    def test_outage_events_recorded(self):
        mgr = SessionCacheManager(UnavailableSessionCache())
        mgr.retrieve("jti-x")
        mgr.store(_entry())
        events = mgr.outage_events()
        assert len(events) >= 2

    def test_outage_event_has_operation_and_timestamp(self):
        mgr = SessionCacheManager(UnavailableSessionCache())
        mgr.retrieve("jti-x")
        event = mgr.outage_events()[0]
        assert "operation" in event
        assert "occurred_at" in event

    def test_unavailable_backend_ping_returns_false(self):
        assert UnavailableSessionCache().ping() is False

    def test_touch_returns_false_on_outage(self):
        mgr = SessionCacheManager(UnavailableSessionCache())
        assert mgr.touch("any") is False


# ===========================================================================
# QA-4: Security / PHI Tests (SEC-1)
# ===========================================================================


class TestPHISecurity:
    """QA-4 — Cache values must not contain PHI/PII fields."""

    def test_allowed_fields_do_not_raise(self):
        entry = _entry()
        validate_no_phi(entry.to_dict())  # must not raise

    def test_email_field_raises_phi_violation(self):
        data = {"jti": "j1", "email": "alice@example.com"}
        with pytest.raises(CachePHIViolationError):
            validate_no_phi(data)

    def test_phone_field_raises_phi_violation(self):
        data = {"jti": "j1", "phone": "555-1234"}
        with pytest.raises(CachePHIViolationError):
            validate_no_phi(data)

    def test_name_field_raises_phi_violation(self):
        with pytest.raises(CachePHIViolationError):
            validate_no_phi({"name": "Alice"})

    def test_unknown_field_raises_phi_violation(self):
        """Allow-list semantics: unknown fields are forbidden."""
        with pytest.raises(CachePHIViolationError):
            validate_no_phi({"jti": "j1", "custom_field": "value"})

    def test_store_with_phi_raises_error(self):
        """SessionCacheManager.store() validates before writing."""
        mgr = SessionCacheManager(InMemorySessionCache())
        e = _entry()
        e_dict = e.to_dict()
        e_dict["email"] = "should-not-store@example.com"
        # Manually create an entry with PHI (bypass normal constructor)
        with pytest.raises(CachePHIViolationError):
            validate_no_phi(e_dict)

    def test_session_cache_allowed_fields_defined(self):
        assert "jti" in SESSION_CACHE_ALLOWED_FIELDS
        assert "user_id" in SESSION_CACHE_ALLOWED_FIELDS
        assert "role" in SESSION_CACHE_ALLOWED_FIELDS

    def test_session_cache_forbidden_fields_defined(self):
        assert "email" in SESSION_CACHE_FORBIDDEN_FIELDS
        assert "phone" in SESSION_CACHE_FORBIDDEN_FIELDS

    def test_session_entry_to_dict_contains_no_phi(self):
        data = _entry().to_dict()
        for forbidden in SESSION_CACHE_FORBIDDEN_FIELDS:
            assert forbidden not in data

    def test_redis_config_validates_tls_warning(self):
        cfg = RedisConnectionConfig(tls_enabled=False, password="secret", port=6380)
        warnings = cfg.validate()
        assert any("TLS" in w for w in warnings)

    def test_redis_config_validates_missing_password(self):
        cfg = RedisConnectionConfig(tls_enabled=True, password=None, port=6380)
        warnings = cfg.validate()
        assert any("AUTH" in w or "password" in w.lower() for w in warnings)

    def test_redis_config_production_safe_requires_tls_and_password(self):
        safe = RedisConnectionConfig(tls_enabled=True, password="strong-pass", port=6380)
        assert safe.is_production_safe()

    def test_redis_config_not_safe_without_password(self):
        unsafe = RedisConnectionConfig(tls_enabled=True, password=None, port=6380)
        assert not unsafe.is_production_safe()
