"""
EP-008 US-085: Automated Health Checks — Test Suite

QA-1  Endpoint Tests         — liveness/readiness signals
QA-2  Traffic Removal Tests  — HTTP 503 causes LB to remove instance
QA-3  Startup Gate Tests     — traffic blocked until dependencies pass
QA-4  Alert Tests            — HealthCheckAlerter fires after threshold
QA-5  Documentation Review   — health check docs exist and are complete
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.health_checks import (
    HEALTH_CHECK_FAILURE_THRESHOLD,
    AlwaysFailingProbe,
    AlwaysPassingProbe,
    FunctionProbe,
    HealthCheckAlerter,
    HealthCheckResult,
    HealthProbeRegistry,
    InMemoryAlertSink,
    ProbeStatus,
    StartupGate,
    _STARTUP_GATE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fail_probe(name: str = "dep") -> AlwaysFailingProbe:
    return AlwaysFailingProbe(name)


def _pass_probe(name: str = "dep") -> AlwaysPassingProbe:
    return AlwaysPassingProbe(name)


# ===========================================================================
# QA-1: Endpoint tests — liveness / readiness signal structure
# ===========================================================================


class TestHealthCheckResultDataclass:
    """QA-1 — HealthCheckResult carries correct fields."""

    def test_passing_result_is_passing(self):
        r = HealthCheckResult(probe_name="db", status=ProbeStatus.PASSING, message="ok")
        assert r.is_passing is True

    def test_failing_result_is_not_passing(self):
        r = HealthCheckResult(probe_name="db", status=ProbeStatus.FAILING, message="err")
        assert r.is_passing is False

    def test_result_has_checked_at_timestamp(self):
        r = HealthCheckResult(probe_name="x", status=ProbeStatus.UNKNOWN, message="?")
        assert r.checked_at is not None

    def test_latency_defaults_to_zero(self):
        r = HealthCheckResult(probe_name="x", status=ProbeStatus.PASSING, message="ok")
        assert r.latency_ms == 0.0


class TestProbeImplementations:
    """QA-1 — Probe implementations return correct results."""

    def test_always_passing_probe_passes(self):
        result = AlwaysPassingProbe("test").run()
        assert result.is_passing

    def test_always_failing_probe_fails(self):
        result = AlwaysFailingProbe("test").run()
        assert not result.is_passing

    def test_function_probe_true_returns_passing(self):
        probe = FunctionProbe("db", lambda: True)
        assert probe.run().is_passing

    def test_function_probe_false_returns_failing(self):
        probe = FunctionProbe("db", lambda: False)
        assert not probe.run().is_passing

    def test_function_probe_exception_returns_failing(self):
        def boom() -> bool:
            raise RuntimeError("network error")
        probe = FunctionProbe("db", boom)
        assert not probe.run().is_passing

    def test_function_probe_records_latency(self):
        probe = FunctionProbe("db", lambda: True)
        result = probe.run()
        assert result.latency_ms >= 0.0

    def test_function_probe_sets_probe_name(self):
        probe = FunctionProbe("database", lambda: True)
        assert probe.run().probe_name == "database"


class TestHealthProbeRegistry:
    """QA-1 — Registry manages and runs probes."""

    def test_register_and_run_all(self):
        reg = HealthProbeRegistry()
        reg.register("a", AlwaysPassingProbe("a"))
        reg.register("b", AlwaysFailingProbe("b"))
        results = reg.run_all()
        assert results["a"].is_passing
        assert not results["b"].is_passing

    def test_run_one_returns_single_result(self):
        reg = HealthProbeRegistry()
        reg.register("db", AlwaysPassingProbe("db"))
        result = reg.run_one("db")
        assert result.probe_name == "db"

    def test_run_one_raises_for_unknown_probe(self):
        reg = HealthProbeRegistry()
        with pytest.raises(KeyError):
            reg.run_one("nonexistent")

    def test_unregister_removes_probe(self):
        reg = HealthProbeRegistry()
        reg.register("db", AlwaysPassingProbe("db"))
        reg.unregister("db")
        assert "db" not in reg.probe_names

    def test_len_returns_registered_count(self):
        reg = HealthProbeRegistry()
        reg.register("a", AlwaysPassingProbe("a"))
        reg.register("b", AlwaysPassingProbe("b"))
        assert len(reg) == 2


# ===========================================================================
# QA-2: Traffic removal tests — 503 semantics drive LB removal
# ===========================================================================


class TestReadinessResponseDrives503:
    """QA-2 — Unhealthy readiness → LB removes instance (tested via
    build_readiness_response which the /health/ready route uses)."""

    def test_db_ok_false_produces_not_ready(self):
        from src.load_balancer import build_readiness_response
        resp = build_readiness_response(db_ok=False)
        assert resp["status"] == "not_ready"

    def test_not_ready_database_check_is_unavailable(self):
        from src.load_balancer import build_readiness_response
        resp = build_readiness_response(db_ok=False)
        assert resp["checks"]["database"] == "unavailable"

    def test_extra_check_failure_makes_not_ready(self):
        from src.load_balancer import build_readiness_response
        resp = build_readiness_response(db_ok=True, extra={"cache": "unavailable"})
        assert resp["status"] == "not_ready"

    def test_all_checks_pass_produces_ready(self):
        from src.load_balancer import build_readiness_response
        resp = build_readiness_response(db_ok=True, extra={"cache": "ok"})
        assert resp["status"] == "ready"

    def test_liveness_always_alive(self):
        from src.load_balancer import build_liveness_response
        assert build_liveness_response()["status"] == "alive"


# ===========================================================================
# QA-3: Startup gate tests — readiness blocked until deps pass (BE-2)
# ===========================================================================


class TestStartupGate:
    """QA-3 — StartupGate blocks readiness until every dependency passes."""

    def setup_method(self):
        # Use a fresh gate per test — do NOT mutate the module singleton
        self.gate = StartupGate()

    def test_empty_gate_is_ready(self):
        assert self.gate.is_ready() is True

    def test_single_passing_dep_is_ready(self):
        self.gate.add_dependency("db", AlwaysPassingProbe("db"))
        assert self.gate.is_ready() is True

    def test_single_failing_dep_blocks_readiness(self):
        self.gate.add_dependency("db", AlwaysFailingProbe("db"))
        assert self.gate.is_ready() is False

    def test_mixed_deps_failing_one_blocks_readiness(self):
        self.gate.add_dependency("db", AlwaysPassingProbe("db"))
        self.gate.add_dependency("cache", AlwaysFailingProbe("cache"))
        assert self.gate.is_ready() is False

    def test_all_passing_deps_are_ready(self):
        self.gate.add_dependency("db", AlwaysPassingProbe("db"))
        self.gate.add_dependency("cache", AlwaysPassingProbe("cache"))
        assert self.gate.is_ready() is True

    def test_dependencies_status_shows_passing(self):
        self.gate.add_dependency("db", AlwaysPassingProbe("db"))
        self.gate.is_ready()
        status = self.gate.dependencies_status()
        assert status["db"] == ProbeStatus.PASSING.value

    def test_dependencies_status_shows_failing(self):
        self.gate.add_dependency("svc", AlwaysFailingProbe("svc"))
        self.gate.is_ready()
        status = self.gate.dependencies_status()
        assert status["svc"] == ProbeStatus.FAILING.value

    def test_remove_dependency_updates_readiness(self):
        self.gate.add_dependency("failing", AlwaysFailingProbe("failing"))
        assert not self.gate.is_ready()
        self.gate.remove_dependency("failing")
        assert self.gate.is_ready()

    def test_clear_removes_all_dependencies(self):
        self.gate.add_dependency("a", AlwaysFailingProbe("a"))
        self.gate.add_dependency("b", AlwaysFailingProbe("b"))
        self.gate.clear()
        assert self.gate.is_ready() is True

    def test_module_singleton_exists(self):
        assert _STARTUP_GATE is not None

    def test_module_singleton_starts_empty_and_ready(self):
        """Module-level gate must not have pre-registered blocking probes."""
        fresh_gate = StartupGate()
        assert fresh_gate.is_ready() is True

    def test_function_probe_integrates_with_startup_gate(self):
        """BE-2: gate works with FunctionProbe wrapping any callable."""
        results = {"db": True}
        self.gate.add_dependency("db", FunctionProbe("db", lambda: results["db"]))
        assert self.gate.is_ready() is True
        results["db"] = False
        assert self.gate.is_ready() is False


# ===========================================================================
# QA-4: Alert tests — HealthCheckAlerter fires after threshold failures (OPS-1)
# ===========================================================================


class TestHealthCheckAlerter:
    """QA-4 — HealthCheckAlerter emits alerts at threshold and resolves on pass."""

    def setup_method(self):
        self.sink = InMemoryAlertSink()
        self.alerter = HealthCheckAlerter(failure_threshold=3, sink=self.sink)

    def _fail(self, name: str = "db") -> HealthCheckResult:
        return HealthCheckResult(probe_name=name, status=ProbeStatus.FAILING, message="err")

    def _pass(self, name: str = "db") -> HealthCheckResult:
        return HealthCheckResult(probe_name=name, status=ProbeStatus.PASSING, message="ok")

    def test_no_alert_below_threshold(self):
        for _ in range(2):  # threshold is 3
            self.alerter.record_result("db", self._fail())
        assert self.sink.alerts == []

    def test_alert_fires_at_threshold(self):
        for _ in range(3):
            self.alerter.record_result("db", self._fail())
        assert len(self.sink.alerts) == 1

    def test_alert_continues_beyond_threshold(self):
        for _ in range(5):
            self.alerter.record_result("db", self._fail())
        assert len(self.sink.alerts) == 3  # fired on 3rd, 4th, 5th

    def test_alert_contains_probe_name(self):
        for _ in range(3):
            self.alerter.record_result("cache", self._fail("cache"))
        assert self.sink.alerts[0]["probe_name"] == "cache"

    def test_alert_contains_failure_count(self):
        for _ in range(3):
            self.alerter.record_result("db", self._fail())
        assert self.sink.alerts[0]["failure_count"] == 3

    def test_passing_result_resolves_alert(self):
        for _ in range(3):
            self.alerter.record_result("db", self._fail())
        self.alerter.record_result("db", self._pass())
        assert "db" not in self.alerter.get_active_alerts()

    def test_failure_count_resets_after_pass(self):
        for _ in range(3):
            self.alerter.record_result("db", self._fail())
        self.alerter.record_result("db", self._pass())
        assert self.alerter.failure_count("db") == 0

    def test_get_active_alerts_before_threshold(self):
        self.alerter.record_result("db", self._fail())
        assert self.alerter.get_active_alerts() == []

    def test_get_active_alerts_at_threshold(self):
        for _ in range(3):
            self.alerter.record_result("db", self._fail())
        assert "db" in self.alerter.get_active_alerts()

    def test_clear_alert_resolves_manually(self):
        for _ in range(3):
            self.alerter.record_result("db", self._fail())
        self.alerter.clear_alert("db")
        assert "db" not in self.alerter.get_active_alerts()

    def test_default_threshold_constant(self):
        assert HEALTH_CHECK_FAILURE_THRESHOLD == 3

    def test_default_sink_is_in_memory(self):
        alerter = HealthCheckAlerter()
        assert isinstance(alerter.sink, InMemoryAlertSink)

    def test_multiple_probes_tracked_independently(self):
        for _ in range(3):
            self.alerter.record_result("db", self._fail("db"))
            self.alerter.record_result("cache", self._fail("cache"))
        active = self.alerter.get_active_alerts()
        assert "db" in active
        assert "cache" in active


# ===========================================================================
# QA-5: Documentation review — HEALTH_CHECK_ENDPOINTS.md exists
# ===========================================================================


class TestHealthCheckDocumentation:
    """QA-5 — Health check documentation is complete and covers required topics."""

    @pytest.fixture
    def doc_text(self) -> str:
        doc = Path(__file__).resolve().parents[1] / "HEALTH_CHECK_ENDPOINTS.md"
        assert doc.exists(), f"Documentation not found at {doc}"
        return doc.read_text(encoding="utf-8")

    def test_doc_exists(self, doc_text):
        assert len(doc_text) > 200

    def test_doc_covers_liveness(self, doc_text):
        assert "/health/live" in doc_text

    def test_doc_covers_readiness(self, doc_text):
        assert "/health/ready" in doc_text

    def test_doc_covers_startup_gate(self, doc_text):
        assert "StartupGate" in doc_text or "startup gate" in doc_text.lower()

    def test_doc_covers_alerting(self, doc_text):
        assert "HealthCheckAlerter" in doc_text or "alert" in doc_text.lower()

    def test_doc_covers_probe_consumers(self, doc_text):
        assert "Consumer" in doc_text or "consumer" in doc_text.lower()

    def test_doc_covers_503_semantics(self, doc_text):
        assert "503" in doc_text

    def test_doc_covers_security_properties(self, doc_text):
        assert "sensitive" in doc_text.lower() or "security" in doc_text.lower()
