"""
EP-008 US-084: Database Replication (Primary + Standby) — Test Suite

QA-1  Replication Sync Tests   — standby stays current with primary updates
QA-2  Failover Drill Tests     — promotion timing and app reconnection
QA-3  Lag Alert Tests          — alerting on simulated lag breach
QA-4  Documentation Review     — runbook file exists and is complete

Also covers:
  DB-1   ReplicationTopology and InMemoryReplicationBackend setup
  DB-2   FailoverController.promote_standby()
  OPS-1  ReplicationMonitor lag measurement and alert emission
  APP-1  ConnectionRegistry.switch_primary()
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from src.replication_manager import (
    AlertSeverity,
    AlreadyPrimaryError,
    ConnectionRegistry,
    FailoverController,
    FailoverError,
    InMemoryReplicationBackend,
    LagAlert,
    LagThresholdPolicy,
    NodeRole,
    NodeStatus,
    ReplicationLag,
    ReplicationManager,
    ReplicationMonitor,
    ReplicationNode,
    ReplicationStatus,
    ReplicationTopology,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]  # workspace root


def _make_topology(n_standbys: int = 1) -> tuple[ReplicationTopology, InMemoryReplicationBackend]:
    backend = InMemoryReplicationBackend()
    primary = ReplicationNode(
        node_id="primary-01", role=NodeRole.PRIMARY, host="10.0.0.1", port=5432
    )
    standbys = [
        ReplicationNode(
            node_id=f"standby-0{i + 1}",
            role=NodeRole.STANDBY,
            host=f"10.0.1.{i + 1}",
            port=5432,
        )
        for i in range(n_standbys)
    ]
    for s in standbys:
        backend.sync_standby(s.node_id)
    topology = ReplicationTopology(primary=primary, standbys=standbys)
    return topology, backend


def _make_manager(n_standbys: int = 1) -> ReplicationManager:
    topology, backend = _make_topology(n_standbys)
    reg = ConnectionRegistry(host="10.0.0.1", port=5432, database="propeliq")
    return ReplicationManager(topology, backend, connection_registry=reg)


# ===========================================================================
# QA-1: Replication Sync Tests
# ===========================================================================


class TestReplicationSync:
    """QA-1 — Standby tracks primary LSN; lag detected when behind."""

    def test_initial_state_is_in_sync(self):
        topology, backend = _make_topology()
        monitor = ReplicationMonitor(topology, backend)
        lags = monitor.poll()
        assert len(lags) == 1
        assert lags[0].is_in_sync

    def test_lag_detected_after_primary_advances(self):
        topology, backend = _make_topology()
        monitor = ReplicationMonitor(topology, backend)
        backend.advance_primary(50_000)  # 50 KB write on primary
        lags = monitor.poll()
        assert lags[0].lag_bytes == 50_000
        assert not lags[0].is_in_sync

    def test_lag_zero_after_standby_catches_up(self):
        topology, backend = _make_topology()
        monitor = ReplicationMonitor(topology, backend)
        backend.advance_primary(100)
        backend.sync_standby("standby-01")
        lags = monitor.poll()
        assert lags[0].is_in_sync

    def test_primary_lsn_updated_in_node_after_poll(self):
        topology, backend = _make_topology()
        monitor = ReplicationMonitor(topology, backend)
        backend.advance_primary(200)
        monitor.poll()
        assert topology.primary.current_lsn == backend.get_primary_lsn()

    def test_standby_lsn_updated_in_node_after_poll(self):
        topology, backend = _make_topology()
        monitor = ReplicationMonitor(topology, backend)
        backend.advance_primary(300)
        backend.advance_standby("standby-01", 100)
        monitor.poll()
        assert topology.standbys[0].current_lsn < topology.primary.current_lsn

    def test_multiple_standbys_all_polled(self):
        topology, backend = _make_topology(n_standbys=2)
        monitor = ReplicationMonitor(topology, backend)
        backend.advance_primary(100)
        lags = monitor.poll()
        assert len(lags) == 2

    def test_in_sync_flag_is_true_at_zero_lag(self):
        lag = ReplicationLag(
            primary_lsn=500, standby_lsn=500, lag_bytes=0, lag_seconds=0.0
        )
        assert lag.is_in_sync is True

    def test_in_sync_flag_is_false_when_lagging(self):
        lag = ReplicationLag(
            primary_lsn=500, standby_lsn=400, lag_bytes=100, lag_seconds=1.5
        )
        assert lag.is_in_sync is False

    def test_topology_status_healthy_when_no_lag(self):
        manager = _make_manager()
        manager.poll_lag()
        assert manager.status()["status"] == ReplicationStatus.HEALTHY.value


# ===========================================================================
# QA-2: Failover Drill Tests
# ===========================================================================


class TestFailoverDrill:
    """QA-2 — Promotion timing, role reassignment, and app reconnection."""

    def test_promote_standby_returns_failover_record(self):
        topology, backend = _make_topology()
        backend.set_reachable("primary-01", False)
        controller = FailoverController(topology, backend)
        record = controller.promote_standby("standby-01", trigger="manual")
        assert record.success is True

    def test_promoted_node_becomes_primary(self):
        topology, backend = _make_topology()
        backend.set_reachable("primary-01", False)
        controller = FailoverController(topology, backend)
        controller.promote_standby("standby-01", trigger="manual")
        assert topology.primary.node_id == "standby-01"

    def test_old_primary_added_to_standbys_after_failover(self):
        topology, backend = _make_topology()
        backend.set_reachable("primary-01", False)
        controller = FailoverController(topology, backend)
        controller.promote_standby("standby-01", trigger="manual")
        standby_ids = [s.node_id for s in topology.standbys]
        assert "primary-01" in standby_ids

    def test_promoted_node_removed_from_standbys_list(self):
        topology, backend = _make_topology()
        backend.set_reachable("primary-01", False)
        controller = FailoverController(topology, backend)
        controller.promote_standby("standby-01", trigger="manual")
        standby_ids = [s.node_id for s in topology.standbys]
        assert "standby-01" not in standby_ids

    def test_failover_drill_bypasses_primary_liveness(self):
        topology, backend = _make_topology()
        # Primary is still reachable — drill mode bypasses the check
        controller = FailoverController(topology, backend)
        record = controller.promote_standby("standby-01", trigger="drill")
        assert record.success is True

    def test_failover_blocked_when_primary_alive_and_not_drill(self):
        topology, backend = _make_topology()
        controller = FailoverController(topology, backend)
        with pytest.raises(FailoverError):
            controller.promote_standby("standby-01", trigger="manual")

    def test_failover_blocked_when_standby_unreachable(self):
        topology, backend = _make_topology()
        backend.set_reachable("primary-01", False)
        backend.set_reachable("standby-01", False)
        controller = FailoverController(topology, backend)
        with pytest.raises(FailoverError):
            controller.promote_standby("standby-01", trigger="manual")

    def test_unknown_standby_raises_failover_error(self):
        topology, backend = _make_topology()
        controller = FailoverController(topology, backend)
        with pytest.raises(FailoverError):
            controller.promote_standby("does-not-exist", trigger="drill")

    def test_failover_duration_recorded(self):
        topology, backend = _make_topology()
        backend.set_reachable("primary-01", False)
        controller = FailoverController(topology, backend)
        record = controller.promote_standby("standby-01", trigger="manual")
        assert record.duration_seconds >= 0.0

    def test_failover_record_stored_in_history(self):
        topology, backend = _make_topology()
        backend.set_reachable("primary-01", False)
        controller = FailoverController(topology, backend)
        controller.promote_standby("standby-01", trigger="manual")
        history = controller.failover_history()
        assert len(history) == 1
        assert history[0].new_primary_id == "standby-01"

    def test_connection_registry_updated_after_failover(self):
        topology, backend = _make_topology()
        backend.set_reachable("primary-01", False)
        reg = ConnectionRegistry(host="10.0.0.1", port=5432, database="propeliq")
        controller = FailoverController(topology, backend, connection_registry=reg)
        controller.promote_standby("standby-01", trigger="manual")
        assert reg.current_primary()["host"] == "10.0.1.1"  # standby-01's host


# ===========================================================================
# QA-3: Lag Alert Tests
# ===========================================================================


class TestLagAlerts:
    """QA-3 — Alert emitted when lag exceeds warning or critical threshold."""

    def test_no_alert_when_in_sync(self):
        topology, backend = _make_topology()
        monitor = ReplicationMonitor(topology, backend)
        monitor.poll()
        assert monitor.get_alerts() == []

    def test_warning_alert_emitted_above_warning_threshold(self):
        topology, backend = _make_topology()
        policy = LagThresholdPolicy(warning_seconds=5.0, critical_seconds=30.0)
        # 100 MB lag at 10 MB/s = 10 seconds → WARNING
        monitor = ReplicationMonitor(topology, backend, policy=policy, bytes_per_second=10_000_000)
        backend.advance_primary(100_000_000)  # 100 MB
        monitor.poll()
        alerts = monitor.get_alerts()
        assert any(a.severity == AlertSeverity.WARNING for a in alerts)

    def test_critical_alert_emitted_above_critical_threshold(self):
        topology, backend = _make_topology()
        policy = LagThresholdPolicy(warning_seconds=5.0, critical_seconds=30.0)
        # 400 MB lag at 10 MB/s = 40 seconds → CRITICAL
        monitor = ReplicationMonitor(topology, backend, policy=policy, bytes_per_second=10_000_000)
        backend.advance_primary(400_000_000)
        monitor.poll()
        alerts = monitor.get_alerts(severity=AlertSeverity.CRITICAL)
        assert len(alerts) >= 1

    def test_alert_contains_node_id(self):
        topology, backend = _make_topology()
        policy = LagThresholdPolicy(warning_seconds=1.0, critical_seconds=30.0)
        monitor = ReplicationMonitor(topology, backend, policy=policy, bytes_per_second=1_000_000)
        backend.advance_primary(5_000_000)
        monitor.poll()
        alerts = monitor.get_alerts()
        assert all(a.node_id == "standby-01" for a in alerts)

    def test_alert_contains_lag_seconds_and_bytes(self):
        topology, backend = _make_topology()
        policy = LagThresholdPolicy(warning_seconds=1.0, critical_seconds=30.0)
        monitor = ReplicationMonitor(topology, backend, policy=policy, bytes_per_second=1_000_000)
        backend.advance_primary(5_000_000)
        monitor.poll()
        alerts = monitor.get_alerts()
        assert alerts[0].lag_bytes == 5_000_000
        assert alerts[0].lag_seconds > 1.0

    def test_topology_status_degraded_on_lag_breach(self):
        topology, backend = _make_topology()
        policy = LagThresholdPolicy(warning_seconds=1.0, critical_seconds=30.0)
        monitor = ReplicationMonitor(topology, backend, policy=policy, bytes_per_second=1_000_000)
        backend.advance_primary(5_000_000)
        monitor.poll()
        assert topology.status == ReplicationStatus.DEGRADED

    def test_node_status_lagging_on_warning(self):
        topology, backend = _make_topology()
        policy = LagThresholdPolicy(warning_seconds=5.0, critical_seconds=30.0)
        monitor = ReplicationMonitor(topology, backend, policy=policy, bytes_per_second=10_000_000)
        backend.advance_primary(100_000_000)  # 10s lag → WARNING
        monitor.poll()
        assert topology.standbys[0].status == NodeStatus.LAGGING

    def test_node_status_critical_on_critical_lag(self):
        topology, backend = _make_topology()
        policy = LagThresholdPolicy(warning_seconds=5.0, critical_seconds=30.0)
        monitor = ReplicationMonitor(topology, backend, policy=policy, bytes_per_second=10_000_000)
        backend.advance_primary(400_000_000)  # 40s → CRITICAL
        monitor.poll()
        assert topology.standbys[0].status == NodeStatus.CRITICAL_LAG

    def test_alert_filter_by_severity(self):
        topology, backend = _make_topology()
        policy = LagThresholdPolicy(warning_seconds=5.0, critical_seconds=30.0)
        monitor = ReplicationMonitor(topology, backend, policy=policy, bytes_per_second=10_000_000)
        backend.advance_primary(400_000_000)  # triggers CRITICAL
        monitor.poll()
        critical_alerts = monitor.get_alerts(severity=AlertSeverity.CRITICAL)
        warning_alerts = monitor.get_alerts(severity=AlertSeverity.WARNING)
        assert len(critical_alerts) >= 1
        assert all(a.severity == AlertSeverity.CRITICAL for a in critical_alerts)

    def test_lag_threshold_policy_classify_below_warning(self):
        policy = LagThresholdPolicy(warning_seconds=5.0, critical_seconds=30.0)
        assert policy.classify(4.9) is None

    def test_lag_threshold_policy_classify_warning(self):
        policy = LagThresholdPolicy(warning_seconds=5.0, critical_seconds=30.0)
        assert policy.classify(5.0) == AlertSeverity.WARNING

    def test_lag_threshold_policy_classify_critical(self):
        policy = LagThresholdPolicy(warning_seconds=5.0, critical_seconds=30.0)
        assert policy.classify(30.0) == AlertSeverity.CRITICAL


# ===========================================================================
# QA-4: Documentation Review — runbook completeness
# ===========================================================================


class TestRunbookExists:
    """QA-4 — DB_REPLICATION_RUNBOOK.md exists and covers required sections."""

    @pytest.fixture
    def runbook_text(self) -> str:
        runbook = Path(__file__).resolve().parents[1] / "db" / "DB_REPLICATION_RUNBOOK.md"
        assert runbook.exists(), f"Runbook not found at {runbook}"
        return runbook.read_text(encoding="utf-8")

    def test_runbook_file_exists(self, runbook_text):
        assert len(runbook_text) > 500

    def test_runbook_covers_topology_setup(self, runbook_text):
        assert "DB-1" in runbook_text or "Replication Setup" in runbook_text

    def test_runbook_covers_failover_procedure(self, runbook_text):
        assert "Failover" in runbook_text

    def test_runbook_covers_lag_monitoring(self, runbook_text):
        assert "Lag" in runbook_text or "Monitoring" in runbook_text

    def test_runbook_covers_application_connectivity(self, runbook_text):
        assert "connectivity" in runbook_text.lower() or "ConnectionRegistry" in runbook_text

    def test_runbook_covers_roles_and_responsibilities(self, runbook_text):
        assert "Roles" in runbook_text or "Responsibilities" in runbook_text

    def test_runbook_covers_recovery_checklist(self, runbook_text):
        assert "checklist" in runbook_text.lower() or "Checklist" in runbook_text

    def test_runbook_covers_failover_drill(self, runbook_text):
        assert "Drill" in runbook_text or "drill" in runbook_text

    def test_runbook_specifies_failover_target_timing(self, runbook_text):
        assert "Target" in runbook_text or "minutes" in runbook_text

    def test_runbook_has_version_history(self, runbook_text):
        assert "Version History" in runbook_text or "Version" in runbook_text


# ===========================================================================
# APP-1: Connection Registry Tests
# ===========================================================================


class TestConnectionRegistry:
    """APP-1 — Connectivity switchover after promotion."""

    def test_initial_connection_string_contains_host(self):
        reg = ConnectionRegistry(host="10.0.0.1", port=5432, database="propeliq")
        assert "10.0.0.1" in reg.get_connection_string()

    def test_switch_primary_updates_host(self):
        reg = ConnectionRegistry(host="10.0.0.1", port=5432, database="propeliq")
        reg.switch_primary("10.0.1.1", 5432)
        assert reg.current_primary()["host"] == "10.0.1.1"

    def test_switch_primary_updates_port(self):
        reg = ConnectionRegistry(host="10.0.0.1", port=5432, database="propeliq")
        reg.switch_primary("10.0.1.1", 5433)
        assert reg.current_primary()["port"] == 5433

    def test_switch_history_records_each_switch(self):
        reg = ConnectionRegistry(host="10.0.0.1", port=5432, database="propeliq")
        reg.switch_primary("10.0.1.1", 5432)
        reg.switch_primary("10.0.2.1", 5432)
        assert len(reg.switch_history()) == 2

    def test_switch_history_records_old_and_new_host(self):
        reg = ConnectionRegistry(host="10.0.0.1", port=5432, database="propeliq")
        reg.switch_primary("10.0.1.1", 5432)
        entry = reg.switch_history()[0]
        assert entry["old_primary"]["host"] == "10.0.0.1"
        assert entry["new_primary"]["host"] == "10.0.1.1"

    def test_connection_string_reflects_new_primary_after_switch(self):
        reg = ConnectionRegistry(host="10.0.0.1", port=5432, database="propeliq")
        reg.switch_primary("new-primary.internal", 5432)
        assert "new-primary.internal" in reg.get_connection_string()
