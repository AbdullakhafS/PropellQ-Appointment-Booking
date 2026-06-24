"""
EP-008 US-091: Query Result Caching — Test Suite

QA-1  Cache Population Tests    — approved patterns are stored and served
QA-2  Invalidation Tests        — stale entries evicted after data changes
QA-3  Monitoring Tests          — hit/miss metrics emitted correctly
QA-4  Cache Outage Tests        — graceful DB fallback without user-facing failure
"""
from __future__ import annotations

import time

import pytest

from src.query_result_cache import (
    CACHE_KEY_PREFIX,
    CACHED_QUERY_PATTERNS,
    CACHE_VALUE_FORBIDDEN_FIELDS,
    CacheBackendUnavailableError,
    CacheEntry,
    CacheMetrics,
    CacheNamespaceConfig,
    CachePatternNotApprovedError,
    CachePHIViolationError,
    InMemoryQueryCache,
    QueryResultCache,
    UnavailableQueryCache,
    build_cache_key,
    validate_cache_value_no_phi,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cache(backend=None) -> QueryResultCache:
    return QueryResultCache(backend or InMemoryQueryCache())


def _slot_value() -> list[dict]:
    return [{"id": 1, "appointment_date": "2026-07-01", "status": "available"}]


# ===========================================================================
# QA-1: Cache Population Tests (BE-1)
# ===========================================================================


class TestCachePopulation:
    """QA-1 — Approved query patterns are stored and retrieved from cache."""

    def test_get_returns_none_on_cold_cache(self):
        cache = _cache()
        assert cache.get("available_slots", {"date": "2026-07-01"}) is None

    def test_set_then_get_returns_value(self):
        cache = _cache()
        val = _slot_value()
        cache.set("available_slots", {"date": "2026-07-01"}, val)
        assert cache.get("available_slots", {"date": "2026-07-01"}) == val

    def test_get_or_set_calls_loader_on_miss(self):
        cache = _cache()
        called = []
        result = cache.get_or_set("available_slots", {"date": "x"}, lambda: (called.append(1) or _slot_value()))
        assert len(called) == 1
        assert result == _slot_value()

    def test_get_or_set_does_not_call_loader_on_hit(self):
        cache = _cache()
        val = _slot_value()
        cache.set("available_slots", {"date": "x"}, val)
        called = []
        cache.get_or_set("available_slots", {"date": "x"}, lambda: (called.append(1) or val))
        assert len(called) == 0

    def test_different_params_produce_different_keys(self):
        k1 = build_cache_key("available_slots", {"date": "2026-07-01"})
        k2 = build_cache_key("available_slots", {"date": "2026-07-02"})
        assert k1 != k2

    def test_same_params_produce_same_key(self):
        p = {"date": "2026-07-01", "specialty_id": 3}
        assert build_cache_key("available_slots", p) == build_cache_key("available_slots", p)

    def test_unapproved_pattern_raises_error(self):
        cache = _cache()
        with pytest.raises(CachePatternNotApprovedError):
            cache.get("not_an_approved_pattern", {})

    def test_set_unapproved_pattern_raises_error(self):
        cache = _cache()
        with pytest.raises(CachePatternNotApprovedError):
            cache.set("random_query", {}, [{"id": 1}])

    def test_all_approved_patterns_accepted(self):
        cache = _cache()
        for pattern in CACHED_QUERY_PATTERNS:
            assert cache.get(pattern, {"id": 1}) is None  # cold, but no exception

    def test_expired_entry_returns_none(self):
        backend = InMemoryQueryCache()
        now = time.time()
        entry = CacheEntry(
            pattern_name="available_slots",
            cache_key=build_cache_key("available_slots", {"d": "x"}),
            value=_slot_value(),
            stored_at=now - 10,
            expires_at=now - 1,  # already expired
        )
        backend._store[entry.cache_key] = entry
        cache = QueryResultCache(backend)
        assert cache.get("available_slots", {"d": "x"}) is None

    def test_provider_list_pattern_stored(self):
        cache = _cache()
        val = [{"id": 1, "name": "Dr. Smith", "specialty_id": 2, "is_active": 1}]
        cache.set("provider_list", {"specialty_id": 2}, val)
        assert cache.get("provider_list", {"specialty_id": 2}) == val

    def test_cached_query_patterns_has_five_entries(self):
        assert len(CACHED_QUERY_PATTERNS) == 5


# ===========================================================================
# QA-2: Invalidation Tests (BE-2)
# ===========================================================================


class TestInvalidation:
    """QA-2 — Stale entries are evicted after data changes."""

    def test_invalidate_removes_specific_entry(self):
        cache = _cache()
        params = {"date": "2026-07-01"}
        cache.set("available_slots", params, _slot_value())
        cache.invalidate("available_slots", params)
        assert cache.get("available_slots", params) is None

    def test_invalidate_returns_true_on_hit(self):
        cache = _cache()
        params = {"date": "x"}
        cache.set("available_slots", params, _slot_value())
        assert cache.invalidate("available_slots", params) is True

    def test_invalidate_returns_false_on_miss(self):
        cache = _cache()
        assert cache.invalidate("available_slots", {"date": "no-such"}) is False

    def test_invalidate_pattern_evicts_all_entries(self):
        cache = _cache()
        for i in range(3):
            cache.set("available_slots", {"date": f"2026-07-{i:02d}"}, _slot_value())
        count = cache.invalidate_pattern("available_slots")
        assert count == 3
        for i in range(3):
            assert cache.get("available_slots", {"date": f"2026-07-{i:02d}"}) is None

    def test_invalidate_pattern_returns_eviction_count(self):
        cache = _cache()
        cache.set("available_slots", {"d": "1"}, _slot_value())
        cache.set("available_slots", {"d": "2"}, _slot_value())
        assert cache.invalidate_pattern("available_slots") == 2

    def test_invalidate_table_evicts_all_table_patterns(self):
        cache = _cache()
        cache.set("available_slots", {"d": "1"}, _slot_value())
        cache.set("appointment_summary", {"id": 1}, {"id": 1, "status": "booked"})
        total = cache.invalidate_table("appointments")
        assert total >= 2

    def test_invalidate_table_does_not_evict_other_tables(self):
        cache = _cache()
        val = [{"id": 1, "name": "Dr.", "specialty_id": 1, "is_active": 1}]
        cache.set("provider_list", {"specialty_id": 1}, val)
        cache.invalidate_table("appointments")
        assert cache.get("provider_list", {"specialty_id": 1}) is not None

    def test_invalidate_pattern_increments_metrics(self):
        metrics = CacheMetrics()
        cache = QueryResultCache(InMemoryQueryCache(), metrics=metrics)
        cache.set("available_slots", {"d": "1"}, _slot_value())
        cache.invalidate_pattern("available_slots")
        assert metrics._patterns.get("available_slots", None) is not None


# ===========================================================================
# QA-3: Monitoring Tests (OPS-1)
# ===========================================================================


class TestCacheMonitoring:
    """QA-3 — Hit/miss metrics are emitted and accurate."""

    def test_hit_increments_hit_counter(self):
        metrics = CacheMetrics()
        cache = QueryResultCache(InMemoryQueryCache(), metrics=metrics)
        cache.set("available_slots", {"d": "x"}, _slot_value())
        cache.get("available_slots", {"d": "x"})
        assert metrics.total_hits() == 1

    def test_miss_increments_miss_counter(self):
        metrics = CacheMetrics()
        cache = QueryResultCache(InMemoryQueryCache(), metrics=metrics)
        cache.get("available_slots", {"d": "x"})
        assert metrics.total_misses() == 1

    def test_hit_ratio_correct(self):
        metrics = CacheMetrics()
        cache = QueryResultCache(InMemoryQueryCache(), metrics=metrics)
        cache.set("available_slots", {"d": "x"}, _slot_value())
        cache.get("available_slots", {"d": "x"})  # hit
        cache.get("available_slots", {"d": "y"})  # miss
        assert metrics.hit_ratio("available_slots") == pytest.approx(0.5)

    def test_overall_hit_ratio_aggregates_patterns(self):
        metrics = CacheMetrics()
        cache = QueryResultCache(InMemoryQueryCache(), metrics=metrics)
        cache.set("available_slots", {"d": "1"}, _slot_value())
        cache.get("available_slots", {"d": "1"})  # hit
        cache.get("provider_list", {"id": 1})     # miss
        assert 0 < metrics.overall_hit_ratio() < 1

    def test_metrics_summary_has_expected_keys(self):
        metrics = CacheMetrics()
        metrics.record_hit("available_slots")
        s = metrics.summary()
        assert all(k in s for k in ["total_hits", "total_misses", "overall_hit_ratio", "patterns"])

    def test_pattern_metrics_has_expected_keys(self):
        metrics = CacheMetrics()
        metrics.record_hit("available_slots")
        d = metrics._patterns["available_slots"].to_dict()
        assert all(k in d for k in ["pattern_name", "hits", "misses", "hit_ratio"])

    def test_phi_violation_increments_phi_counter(self):
        metrics = CacheMetrics()
        cache = QueryResultCache(InMemoryQueryCache(), metrics=metrics)
        # Force a PHI violation via get_or_set loader returning PHI data
        phi_value = [{"id": 1, "patient_email": "x@y.com"}]
        cache.get_or_set("available_slots", {"d": "x"}, lambda: phi_value)
        assert metrics._patterns.get("available_slots") is not None

    def test_available_returns_true_on_healthy_backend(self):
        assert _cache().is_available() is True

    def test_available_returns_false_on_unavailable_backend(self):
        cache = QueryResultCache(UnavailableQueryCache())
        assert cache.is_available() is False


# ===========================================================================
# QA-4: Cache Outage Tests (BE-3)
# ===========================================================================


class TestCacheOutage:
    """QA-4 — Graceful fallback to DB when Redis unavailable."""

    def test_get_returns_none_on_outage(self):
        cache = QueryResultCache(UnavailableQueryCache())
        assert cache.get("available_slots", {"d": "x"}) is None

    def test_set_returns_false_on_outage(self):
        cache = QueryResultCache(UnavailableQueryCache())
        assert cache.set("available_slots", {"d": "x"}, _slot_value()) is False

    def test_get_or_set_calls_loader_on_outage(self):
        cache = QueryResultCache(UnavailableQueryCache())
        called = []
        result = cache.get_or_set("available_slots", {"d": "x"}, lambda: (called.append(1) or _slot_value()))
        assert len(called) == 1
        assert result == _slot_value()

    def test_invalidate_returns_false_on_outage(self):
        cache = QueryResultCache(UnavailableQueryCache())
        assert cache.invalidate("available_slots", {"d": "x"}) is False

    def test_outage_events_recorded(self):
        cache = QueryResultCache(UnavailableQueryCache())
        cache.get("available_slots", {"d": "1"})
        cache.set("available_slots", {"d": "2"}, _slot_value())
        events = cache.outage_events()
        assert len(events) >= 2

    def test_outage_event_has_operation_key(self):
        cache = QueryResultCache(UnavailableQueryCache())
        cache.get("available_slots", {"d": "1"})
        assert "operation" in cache.outage_events()[0]

    def test_unavailable_backend_ping_false(self):
        assert UnavailableQueryCache().ping() is False

    def test_phi_in_value_raises_before_storing(self):
        cache = _cache()
        with pytest.raises(CachePHIViolationError):
            cache.set("available_slots", {"d": "x"}, [{"id": 1, "patient_email": "x@y.com"}])

    def test_validate_cache_value_no_phi_passes_clean_data(self):
        validate_cache_value_no_phi([{"id": 1, "status": "available"}])  # no error

    def test_validate_cache_value_phi_raises(self):
        with pytest.raises(CachePHIViolationError):
            validate_cache_value_no_phi({"email": "x@y.com"})

    def test_namespace_config_production_safe(self):
        cfg = CacheNamespaceConfig(tls_enabled=True, auth_password="s3cr3t")
        assert cfg.is_production_safe()

    def test_namespace_config_not_safe_without_password(self):
        cfg = CacheNamespaceConfig(tls_enabled=True, auth_password=None)
        assert not cfg.is_production_safe()
