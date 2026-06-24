"""
EP-008 US-092: Graceful Degradation Pattern — Test Suite

QA-1  Core Flow Fault Tests     — booking available during optional service outage
QA-2  UX Fallback Tests         — degraded messaging appears without full app failure
QA-3  Resilience Behavior Tests — retries and bypass don't block core workflows
QA-4  Alerting Tests            — degraded mode generates operational alerts
"""
from __future__ import annotations

import pytest

from src.graceful_degradation import (
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_HALF_OPEN_SUCCESSES,
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    DegradedAlertEvent,
    DegradedStateAlerter,
    DegradedUXRegistry,
    DependencyGuard,
    DependencyKind,
    DependencyRegistry,
    DependencySpec,
    InMemoryDegradedAlertSink,
    RetryPolicy,
    build_optional_guard,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _always_fail(msg="service error"):
    def fn():
        raise RuntimeError(msg)
    return fn


def _always_succeed(value="ok"):
    def fn():
        return value
    return fn


def _sink_and_alerter(cooldown=0.0):
    sink = InMemoryDegradedAlertSink()
    alerter = DegradedStateAlerter(sink)
    return sink, alerter


# ===========================================================================
# QA-1: Core Flow Fault Tests (BE-1)
# ===========================================================================


class TestCoreFlowFaults:
    """QA-1 — Booking remains available when optional services fail."""

    def test_optional_guard_returns_none_on_failure(self):
        guard = build_optional_guard("reminder_service")
        result = guard.execute(_always_fail())
        assert result is None

    def test_optional_guard_returns_value_on_success(self):
        guard = build_optional_guard("reminder_service")
        assert guard.execute(_always_succeed("enqueued")) == "enqueued"

    def test_critical_guard_raises_on_failure(self):
        guard = DependencyGuard(
            "database",
            DependencyKind.CRITICAL,
            retry_policy=RetryPolicy(max_attempts=1, base_delay=0.0),
        )
        with pytest.raises(RuntimeError):
            guard.execute(_always_fail())

    def test_multiple_optional_failures_do_not_raise(self):
        guard = build_optional_guard("analytics_service", failure_threshold=5)
        for _ in range(6):
            assert guard.execute(_always_fail()) is None

    def test_optional_guard_open_circuit_returns_none(self):
        cb = CircuitBreaker("reminder", failure_threshold=1, recovery_timeout=9999.0)
        guard = DependencyGuard(
            "reminder_service", DependencyKind.OPTIONAL,
            circuit_breaker=cb,
            retry_policy=RetryPolicy(max_attempts=1, base_delay=0.0),
        )
        guard.execute(_always_fail())  # trips circuit
        guard.execute(_always_fail())  # circuit open → None, no exception

    def test_dependency_registry_classifies_optional(self):
        reg = DependencyRegistry()
        assert reg.is_optional("reminder_service")
        assert reg.is_optional("redis_cache")
        assert reg.is_optional("email_gateway")

    def test_dependency_registry_classifies_critical(self):
        reg = DependencyRegistry()
        assert reg.is_critical("database")

    def test_bypass_flag_returns_none_immediately(self):
        guard = build_optional_guard("analytics_service")
        called = []
        result = guard.execute(lambda: called.append(1) or "value", bypass=True)
        assert result is None
        assert called == []


# ===========================================================================
# QA-2: UX Fallback Tests (FE-1)
# ===========================================================================


class TestUXFallback:
    """QA-2 — Degraded messaging appears; booking still succeeds."""

    def test_ux_registry_adds_message_on_failure(self):
        ux = DegradedUXRegistry()
        guard = build_optional_guard("reminder_service", ux_registry=ux)
        guard.execute(_always_fail())
        assert ux.has_warnings()

    def test_ux_registry_to_list_has_feature(self):
        ux = DegradedUXRegistry()
        ux.add("reminder_service")
        msgs = ux.to_list()
        assert any(m["feature"] == "reminder_service" for m in msgs)

    def test_ux_registry_deduplicates_feature(self):
        ux = DegradedUXRegistry()
        ux.add("reminder_service")
        ux.add("reminder_service")
        assert len(ux.to_list()) == 1

    def test_ux_message_has_expected_keys(self):
        ux = DegradedUXRegistry()
        ux.add("email_gateway")
        msg = ux.to_list()[0]
        assert all(k in msg for k in ["feature", "user_message", "severity"])

    def test_ux_message_severity_is_warning(self):
        ux = DegradedUXRegistry()
        ux.add("redis_cache")
        assert ux.to_list()[0]["severity"] == "warning"

    def test_ux_registry_custom_message(self):
        ux = DegradedUXRegistry()
        ux.add("email_gateway", "Custom message for email outage")
        assert ux.to_list()[0]["user_message"] == "Custom message for email outage"

    def test_ux_registry_clear(self):
        ux = DegradedUXRegistry()
        ux.add("reminder_service")
        ux.clear()
        assert not ux.has_warnings()

    def test_unknown_feature_uses_default_message(self):
        ux = DegradedUXRegistry()
        ux.add("unknown_feature_xyz")
        msg = ux.to_list()[0]["user_message"]
        assert "unknown_feature_xyz" in msg


# ===========================================================================
# QA-3: Resilience Behavior Tests (BE-2)
# ===========================================================================


class TestResilienceBehavior:
    """QA-3 — Retries and circuit breaker don't block core workflows."""

    def test_circuit_breaker_opens_after_threshold(self):
        cb = CircuitBreaker("svc", failure_threshold=2, recovery_timeout=9999.0)
        for _ in range(2):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_circuit_breaker_closed_initially(self):
        assert CircuitBreaker("svc").state == CircuitState.CLOSED

    def test_circuit_breaker_allows_request_when_closed(self):
        assert CircuitBreaker("svc").allow_request() is True

    def test_circuit_breaker_rejects_request_when_open(self):
        cb = CircuitBreaker("svc", failure_threshold=1, recovery_timeout=9999.0)
        cb.record_failure()
        assert cb.allow_request() is False

    def test_circuit_breaker_transitions_half_open_after_timeout(self):
        cb = CircuitBreaker("svc", failure_threshold=1, recovery_timeout=0.0)
        cb.record_failure()
        # After timeout=0, next state check should be HALF_OPEN
        import time; time.sleep(0.01)
        assert cb.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_closes_after_half_open_successes(self):
        cb = CircuitBreaker("svc", failure_threshold=1, recovery_timeout=0.0,
                            half_open_successes=2)
        cb.record_failure()
        import time; time.sleep(0.01)
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_circuit_breaker_returns_to_open_on_half_open_failure(self):
        cb = CircuitBreaker("svc", failure_threshold=1, recovery_timeout=0.0)
        cb.record_failure()
        import time; time.sleep(0.01)
        _ = cb.state  # trigger half-open transition
        cb.record_failure()  # failure while half-open → back to OPEN
        # Check internal state directly to avoid re-triggering the
        # zero-timeout half-open transition inside the .state property.
        assert cb._state == CircuitState.OPEN

    def test_retry_policy_delay_doubles_each_attempt(self):
        policy = RetryPolicy(max_attempts=3, base_delay=1.0)
        assert policy.delay_for(1) == 1.0
        assert policy.delay_for(2) == 2.0
        assert policy.delay_for(3) == 4.0

    def test_retry_policy_respects_max_delay(self):
        policy = RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=3.0)
        assert policy.delay_for(5) == 3.0

    def test_retry_policy_retryable_on_all_by_default(self):
        policy = RetryPolicy()
        assert policy.is_retryable(RuntimeError("any"))

    def test_retry_policy_retryable_filtered(self):
        policy = RetryPolicy(retryable_on=(ValueError,))
        assert not policy.is_retryable(RuntimeError("other"))
        assert policy.is_retryable(ValueError("val"))

    def test_guard_retries_before_giving_up(self):
        call_count = [0]
        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("temporary")
            return "ok"
        guard = build_optional_guard(
            "reminder_service",
            max_retry_attempts=3,
        )
        result = guard.execute(flaky)
        assert result == "ok"
        assert call_count[0] == 3

    def test_circuit_breaker_stats_has_expected_keys(self):
        cb = CircuitBreaker("svc")
        stats = cb.stats()
        assert all(hasattr(stats, k) for k in ["state", "failure_count", "last_state_change_at"])


# ===========================================================================
# QA-4: Alerting Tests (OPS-1)
# ===========================================================================


class TestDegradedStateAlerting:
    """QA-4 — Degraded mode generates operational alerts."""

    def test_alert_emitted_on_first_failure(self):
        sink, alerter = _sink_and_alerter()
        guard = build_optional_guard("reminder_service", alerter=alerter, failure_threshold=1)
        guard.execute(_always_fail())
        assert len(sink.events) >= 1

    def test_alert_event_type_entered_degraded(self):
        sink, alerter = _sink_and_alerter()
        guard = build_optional_guard("reminder_service", alerter=alerter, failure_threshold=1)
        guard.execute(_always_fail())
        assert any(e.event_type == "entered_degraded" for e in sink.events)

    def test_no_duplicate_degraded_alert(self):
        sink, alerter = _sink_and_alerter()
        guard = build_optional_guard("reminder_service", alerter=alerter, failure_threshold=1)
        guard.execute(_always_fail())
        guard.execute(_always_fail())
        entered_events = [e for e in sink.events if e.event_type == "entered_degraded"]
        assert len(entered_events) == 1

    def test_recovery_alert_emitted_after_success(self):
        sink, alerter = _sink_and_alerter()
        # Use a high circuit threshold so 1 failure doesn't open the circuit;
        # the alerter still records degraded on the first failure.
        guard = build_optional_guard("reminder_service", alerter=alerter, failure_threshold=10)
        guard.execute(_always_fail())     # failure → alerter marks degraded
        guard.execute(_always_succeed())  # success → alerter fires recovery
        assert any(e.event_type == "recovered" for e in sink.events)

    def test_alerter_is_degraded_flag(self):
        sink, alerter = _sink_and_alerter()
        guard = build_optional_guard("reminder_service", alerter=alerter, failure_threshold=1)
        guard.execute(_always_fail())
        assert alerter.is_degraded("reminder_service")

    def test_alerter_is_not_degraded_after_recovery(self):
        sink, alerter = _sink_and_alerter()
        guard = build_optional_guard("reminder_service", alerter=alerter, failure_threshold=10)
        guard.execute(_always_fail())     # marks degraded
        guard.execute(_always_succeed())  # clears degraded
        assert not alerter.is_degraded("reminder_service")

    def test_alert_event_has_dependency_name(self):
        sink, alerter = _sink_and_alerter()
        guard = build_optional_guard("email_gateway", alerter=alerter, failure_threshold=1)
        guard.execute(_always_fail())
        assert sink.events[0].dependency_name == "email_gateway"

    def test_alert_event_to_dict_has_expected_keys(self):
        event = DegradedAlertEvent(
            dependency_name="svc",
            event_type="entered_degraded",
            circuit_state="open",
        )
        d = event.to_dict()
        assert all(k in d for k in ["dependency_name", "event_type", "circuit_state", "occurred_at"])
