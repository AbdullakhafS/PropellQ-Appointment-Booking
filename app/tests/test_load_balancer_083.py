"""
EP-008 US-083: Load Balancer Configuration — Test Suite

QA-1  Distribution Tests     — round-robin spread, no sticky sessions
QA-2  Failover Tests         — unhealthy instance removed within threshold
QA-3  Multi-Instance Tests   — minimum 3 instances serviced
QA-4  Change Management Tests — config updates without disruption

Also covers:
  INFRA-2  Health check endpoints in the WSGI app (/health/live, /health/ready)
  INFRA-3  Session affinity disabled at config creation
  OPS-1    Version increment enforced on config update
"""
from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

import pytest

from src.load_balancer import (
    BackendInstance,
    FakeHealthChecker,
    HealthCheckConfig,
    LoadBalancerConfig,
    LoadBalancerConfigError,
    LoadBalancerPool,
    NoHealthyBackendError,
    build_liveness_response,
    build_readiness_response,
    render_nginx_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_instance(host: str = "10.0.0.1", port: int = 8000) -> BackendInstance:
    return BackendInstance(host=host, port=port)


def _make_pool(
    n: int = 3,
    healthy: bool = True,
    checker: FakeHealthChecker | None = None,
) -> LoadBalancerPool:
    instances = [_make_instance(f"10.0.0.{i + 1}", 8000) for i in range(n)]
    for inst in instances:
        inst.healthy = healthy
    cfg = LoadBalancerConfig(version=1, instances=instances)
    return LoadBalancerPool(cfg, checker=checker or FakeHealthChecker())


def _wsgi_request(method: str, path: str) -> tuple[int, dict]:
    """Send a minimal WSGI request and return (status_code, body_dict)."""
    import sqlite3
    from src.web_app import create_app

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = Path(tmp) / "test.db"
        app = create_app(db_path=db_path)

        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "wsgi.input": io.BytesIO(b""),
            "CONTENT_LENGTH": "0",
            "QUERY_STRING": "",
        }
        status_holder: list[str] = []

        def start_response(status, headers, exc_info=None):
            status_holder.append(status)

        body_chunks = app(environ, start_response)
        body = b"".join(body_chunks).decode()
        status_code = int(status_holder[0].split(" ", 1)[0])
        return status_code, json.loads(body) if body else {}


# ===========================================================================
# QA-1: Distribution Tests — round-robin, no sticky sessions
# ===========================================================================


class TestDistribution:
    """QA-1 — Verify even distribution across healthy instances."""

    def test_round_robin_cycles_all_instances(self):
        pool = _make_pool(n=3)
        seen = set()
        for _ in range(6):
            inst = pool.select()
            seen.add(inst.address)
        assert len(seen) == 3

    def test_sequential_requests_hit_different_instances(self):
        pool = _make_pool(n=3)
        first = pool.select().address
        second = pool.select().address
        assert first != second

    def test_distribution_is_even_over_many_requests(self):
        pool = _make_pool(n=3)
        counts: dict[str, int] = {}
        for _ in range(90):
            addr = pool.select().address
            counts[addr] = counts.get(addr, 0) + 1
        # Each instance should receive ~30 requests; allow ±5 variance
        for addr, count in counts.items():
            assert 25 <= count <= 35, f"{addr} received {count} requests (expected ~30)"

    def test_stats_track_total_requests(self):
        pool = _make_pool(n=3)
        for _ in range(9):
            pool.select()
        stats = pool.distribution_stats()
        assert sum(stats.values()) == 9

    def test_sticky_sessions_disabled_at_config_creation(self):
        """INFRA-3: Enabling sticky sessions raises LoadBalancerConfigError."""
        with pytest.raises(LoadBalancerConfigError):
            LoadBalancerConfig(
                version=1,
                instances=[_make_instance()],
                sticky_sessions=True,
            )

    def test_config_sticky_sessions_is_false_by_default(self):
        cfg = LoadBalancerConfig(version=1, instances=[_make_instance()])
        assert cfg.sticky_sessions is False

    def test_pool_selects_only_healthy_instances(self):
        checker = FakeHealthChecker()
        instances = [BackendInstance(host=f"10.0.0.{i+1}", port=8000, healthy=True) for i in range(3)]
        # Mark first two healthy, last one unhealthy
        instances[2].healthy = False
        cfg = LoadBalancerConfig(version=1, instances=instances)
        pool = LoadBalancerPool(cfg, checker=checker)
        selected = {pool.select().address for _ in range(20)}
        assert instances[2].address not in selected


# ===========================================================================
# QA-2: Failover Tests — unhealthy instance removal
# ===========================================================================


class TestFailoverRouting:
    """QA-2 — Verify unhealthy instances are removed within threshold window."""

    def test_unhealthy_instance_not_selected(self):
        pool = _make_pool(n=3)
        pool.config.instances[0].healthy = False
        selected = {pool.select().address for _ in range(20)}
        assert pool.config.instances[0].address not in selected

    def test_health_check_marks_instance_unhealthy_after_threshold(self):
        checker = FakeHealthChecker()
        pool = _make_pool(n=3, checker=checker)
        # Report first instance as unhealthy
        checker.set_result("10.0.0.1", 8000, False)
        checker.set_result("10.0.0.2", 8000, True)
        checker.set_result("10.0.0.3", 8000, True)
        # Run checks equal to the threshold
        for _ in range(pool.config.health_check.unhealthy_threshold):
            pool.run_health_checks()
        assert pool.config.instances[0].healthy is False

    def test_instance_recovers_after_consecutive_passes(self):
        checker = FakeHealthChecker()
        pool = _make_pool(n=2, checker=checker)
        pool.config.instances[0].healthy = False
        pool.config.instances[0].consecutive_failures = 5
        # All now reporting healthy
        checker.set_result("10.0.0.1", 8000, True)
        checker.set_result("10.0.0.2", 8000, True)
        for _ in range(pool.config.health_check.healthy_threshold):
            pool.run_health_checks()
        assert pool.config.instances[0].healthy is True

    def test_no_healthy_backend_raises(self):
        pool = _make_pool(n=2, healthy=False)
        with pytest.raises(NoHealthyBackendError):
            pool.select()

    def test_single_failure_below_threshold_does_not_mark_unhealthy(self):
        checker = FakeHealthChecker()
        pool = _make_pool(n=2, checker=checker)
        checker.set_result("10.0.0.1", 8000, False)
        checker.set_result("10.0.0.2", 8000, True)
        pool.run_health_checks()  # only 1 failure, threshold is 2
        assert pool.config.instances[0].healthy is True  # not yet removed

    def test_health_check_results_returned_per_instance(self):
        checker = FakeHealthChecker()
        pool = _make_pool(n=3, checker=checker)
        checker.set_result("10.0.0.2", 8000, False)
        # Run threshold times to trigger unhealthy state
        for _ in range(pool.config.health_check.unhealthy_threshold):
            results = pool.run_health_checks()
        assert results["10.0.0.2:8000"] is False
        assert results["10.0.0.1:8000"] is True


# ===========================================================================
# QA-3: Multi-Instance Tests — minimum 3 instances
# ===========================================================================


class TestMultiInstanceCapacity:
    """QA-3 — Verify traffic is served across at least three instances."""

    def test_three_instance_pool_selects_all_three(self):
        pool = _make_pool(n=3)
        seen = set()
        for _ in range(9):
            seen.add(pool.select().address)
        assert len(seen) == 3, f"Expected 3 unique instances, got {len(seen)}: {seen}"

    def test_five_instance_pool_distributes_across_all(self):
        pool = _make_pool(n=5)
        seen = set()
        for _ in range(25):
            seen.add(pool.select().address)
        assert len(seen) == 5

    def test_capacity_minimum_constant_is_three(self):
        from src.load_balancer import LB_MIN_INSTANCES
        assert LB_MIN_INSTANCES == 3

    def test_pool_summary_reports_instance_count(self):
        pool = _make_pool(n=4)
        summary = pool.status()
        assert summary["total_instances"] == 4
        assert summary["healthy_instances"] == 4

    def test_partial_failure_still_serves_remaining_instances(self):
        pool = _make_pool(n=4)
        pool.config.instances[0].healthy = False
        seen = set()
        for _ in range(30):
            seen.add(pool.select().address)
        assert len(seen) == 3  # 4 - 1 unhealthy


# ===========================================================================
# QA-4: Change Management Tests — zero-downtime config updates (OPS-1)
# ===========================================================================


class TestZeroDowntimeConfigUpdate:
    """QA-4 — Config updates increment version and apply atomically."""

    def test_config_update_increments_version(self):
        pool = _make_pool(n=3)
        new_cfg = LoadBalancerConfig(
            version=2,
            instances=[_make_instance("10.0.1.1", 9000)],
        )
        pool.update_config(new_cfg)
        assert pool.config.version == 2

    def test_new_config_replaces_instance_list(self):
        pool = _make_pool(n=3)
        new_instances = [BackendInstance(host="192.168.1.1", port=9090)]
        new_cfg = LoadBalancerConfig(version=2, instances=new_instances)
        pool.update_config(new_cfg)
        assert pool.config.instances[0].host == "192.168.1.1"

    def test_downgrade_version_raises_error(self):
        pool = _make_pool(n=3)
        old_cfg = LoadBalancerConfig(version=0, instances=[_make_instance()])
        with pytest.raises(LoadBalancerConfigError):
            pool.update_config(old_cfg)

    def test_same_version_raises_error(self):
        pool = _make_pool(n=3)
        same_cfg = LoadBalancerConfig(version=1, instances=[_make_instance()])
        with pytest.raises(LoadBalancerConfigError):
            pool.update_config(same_cfg)

    def test_sticky_sessions_blocked_on_update(self):
        pool = _make_pool(n=2)
        with pytest.raises(LoadBalancerConfigError):
            LoadBalancerConfig(version=2, instances=[_make_instance()], sticky_sessions=True)

    def test_select_works_immediately_after_update(self):
        pool = _make_pool(n=3)
        new_instances = [BackendInstance(host=f"10.1.0.{i}", port=8080) for i in range(1, 4)]
        pool.update_config(LoadBalancerConfig(version=2, instances=new_instances))
        inst = pool.select()
        assert inst.port == 8080

    def test_nginx_config_contains_version_comment(self):
        cfg = LoadBalancerConfig(
            version=7,
            instances=[_make_instance("10.0.0.1", 8000), _make_instance("10.0.0.2", 8000)],
        )
        rendered = render_nginx_config(cfg)
        assert "Config version: 7" in rendered
        assert "10.0.0.1:8000" in rendered
        assert "10.0.0.2:8000" in rendered
        assert "ip_hash;" not in rendered  # INFRA-3: no session affinity directive


# ===========================================================================
# INFRA-2: Health check endpoint tests (via WSGI app)
# ===========================================================================


class TestHealthEndpoints:
    """INFRA-2 — /health/live and /health/ready endpoints."""

    def test_liveness_returns_200(self):
        code, body = _wsgi_request("GET", "/health/live")
        assert code == 200

    def test_liveness_body_contains_status_alive(self):
        _, body = _wsgi_request("GET", "/health/live")
        assert body["status"] == "alive"

    def test_liveness_body_contains_timestamp(self):
        _, body = _wsgi_request("GET", "/health/live")
        assert "checked_at" in body

    def test_readiness_returns_200_with_valid_db(self):
        code, body = _wsgi_request("GET", "/health/ready")
        assert code == 200
        assert body["status"] == "ready"

    def test_readiness_body_contains_database_check(self):
        _, body = _wsgi_request("GET", "/health/ready")
        assert body["checks"]["database"] == "ok"

    def test_build_liveness_response_structure(self):
        resp = build_liveness_response()
        assert resp["status"] == "alive"
        assert "checked_at" in resp

    def test_build_readiness_response_ready(self):
        resp = build_readiness_response(db_ok=True)
        assert resp["status"] == "ready"
        assert resp["checks"]["database"] == "ok"

    def test_build_readiness_response_not_ready(self):
        resp = build_readiness_response(db_ok=False)
        assert resp["status"] == "not_ready"
        assert resp["checks"]["database"] == "unavailable"

    def test_build_readiness_accepts_extra_checks(self):
        resp = build_readiness_response(db_ok=True, extra={"cache": "ok"})
        assert resp["checks"]["cache"] == "ok"

    def test_build_readiness_not_ready_if_any_extra_check_fails(self):
        resp = build_readiness_response(db_ok=True, extra={"cache": "unavailable"})
        assert resp["status"] == "not_ready"
