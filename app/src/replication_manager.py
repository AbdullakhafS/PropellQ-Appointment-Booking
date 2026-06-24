"""
EP-008 US-084: Database Replication (Primary + Standby)

DB-1   Replication topology setup — ReplicationTopology, ReplicationNode, ReplicationState.
DB-2   Promotion and failover procedure — FailoverController.promote_standby().
OPS-1  Lag monitoring and alerting — ReplicationMonitor, LagAlert, LagThresholdPolicy.
APP-1  Application connectivity switchover — ConnectionRegistry.switch_primary().

All classes are designed for testability: no hard-coded network calls.
The ReplicationNode uses an injectable BackendAdapter protocol so tests can
substitute an in-memory SQLite adapter without running real replication I/O.

Production mapping:
  SQLite WAL-mode streaming  → WalReplicationAdapter
  PostgreSQL streaming       → map pg_stat_replication.write_lag to ReplicationLag
  MySQL GTID replication     → map Seconds_Behind_Master to ReplicationLag
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OPS-1: Lag thresholds
# ---------------------------------------------------------------------------

LAG_WARNING_SECONDS: float = 5.0     # emit WARNING alert above this
LAG_CRITICAL_SECONDS: float = 30.0   # emit CRITICAL alert above this; failover may be triggered
LAG_POLL_INTERVAL_SECONDS: int = 5   # how often the monitor polls lag

# ---------------------------------------------------------------------------
# Enumerations and exceptions
# ---------------------------------------------------------------------------


class NodeRole(str, Enum):
    PRIMARY = "primary"
    STANDBY = "standby"


class NodeStatus(str, Enum):
    ONLINE = "online"
    LAGGING = "lagging"           # lag > warning threshold
    CRITICAL_LAG = "critical_lag" # lag > critical threshold
    OFFLINE = "offline"
    PROMOTED = "promoted"         # standby successfully promoted to primary


class ReplicationStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILOVER_IN_PROGRESS = "failover_in_progress"
    STANDALONE = "standalone"     # no standby configured


class AlertSeverity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"
    RESOLVED = "resolved"


class ReplicationError(Exception):
    """Base for replication-related errors."""


class FailoverError(ReplicationError):
    """Raised when a failover attempt cannot complete."""


class AlreadyPrimaryError(ReplicationError):
    """Raised when promotion is attempted on the current primary."""


# ---------------------------------------------------------------------------
# DB-1: Data classes
# ---------------------------------------------------------------------------


@dataclass
class ReplicationLag:
    """Snapshot of replication lag at a point in time (OPS-1).

    primary_lsn     Log Sequence Number (or WAL offset) on the primary.
    standby_lsn     LSN the standby has confirmed applying.
    lag_bytes       Difference in bytes (0 when fully caught up).
    lag_seconds     Estimated time the standby is behind primary.
    measured_at     UTC ISO-8601 timestamp of this measurement.
    """

    primary_lsn: int
    standby_lsn: int
    lag_bytes: int
    lag_seconds: float
    measured_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_in_sync(self) -> bool:
        return self.lag_bytes == 0 and self.lag_seconds == 0.0


@dataclass
class ReplicationNode:
    """Represents a single database node (primary or standby).

    node_id         Unique identifier for this node.
    role            NodeRole.PRIMARY or NodeRole.STANDBY.
    host            Hostname / IP for connectivity.
    port            Database listen port.
    status          Current health status.
    current_lsn     Last confirmed LSN on this node.
    last_seen_at    ISO-8601 UTC timestamp of last successful contact.
    """

    node_id: str
    role: NodeRole
    host: str
    port: int
    status: NodeStatus = NodeStatus.ONLINE
    current_lsn: int = 0
    last_seen_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class LagThresholdPolicy:
    """Configurable lag alert thresholds (OPS-1)."""

    warning_seconds: float = LAG_WARNING_SECONDS
    critical_seconds: float = LAG_CRITICAL_SECONDS

    def classify(self, lag_seconds: float) -> AlertSeverity | None:
        if lag_seconds >= self.critical_seconds:
            return AlertSeverity.CRITICAL
        if lag_seconds >= self.warning_seconds:
            return AlertSeverity.WARNING
        return None


@dataclass
class LagAlert:
    """A replication lag alert event (OPS-1)."""

    severity: AlertSeverity
    node_id: str
    lag_seconds: float
    lag_bytes: int
    primary_lsn: int
    standby_lsn: int
    message: str
    raised_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class FailoverRecord:
    """Audit record created when a failover completes (DB-2)."""

    old_primary_id: str
    new_primary_id: str
    trigger: str                  # "manual" | "automatic" | "drill"
    started_at: str
    completed_at: str
    duration_seconds: float
    success: bool
    notes: str = ""


# ---------------------------------------------------------------------------
# DB-1: Backend adapter protocol (injectable for testing)
# ---------------------------------------------------------------------------


class ReplicationBackendProtocol(Protocol):
    """Injectable adapter for database-specific replication operations.

    Production implementations wrap psycopg2, sqlite3-WAL, or MySQLdb.
    Tests supply InMemoryReplicationBackend.
    """

    def get_primary_lsn(self) -> int:
        """Return the current write LSN on the primary."""
        ...

    def get_standby_lsn(self, node_id: str) -> int:
        """Return the LSN the standby identified by node_id has confirmed applying."""
        ...

    def promote_standby(self, node_id: str) -> bool:
        """Promote the standby to primary. Returns True on success."""
        ...

    def ping_node(self, node_id: str) -> bool:
        """Return True if the node is reachable."""
        ...


class InMemoryReplicationBackend:
    """In-memory backend for unit testing (no network / disk I/O).

    Call ``advance_primary(n)`` to simulate writes on the primary.
    Call ``advance_standby(node_id, n)`` to simulate replication applying.
    ``set_reachable(node_id, reachable)`` simulates network partitions.
    """

    def __init__(self) -> None:
        self._primary_lsn: int = 1000
        self._standby_lsn: dict[str, int] = {}
        self._reachable: dict[str, bool] = {}
        self._promoted: set[str] = set()

    def advance_primary(self, delta: int = 1) -> None:
        self._primary_lsn += delta

    def advance_standby(self, node_id: str, delta: int = 1) -> None:
        self._standby_lsn[node_id] = self._standby_lsn.get(node_id, self._primary_lsn) + delta

    def sync_standby(self, node_id: str) -> None:
        """Instantly bring standby to primary LSN (simulates full sync)."""
        self._standby_lsn[node_id] = self._primary_lsn

    def set_reachable(self, node_id: str, reachable: bool) -> None:
        self._reachable[node_id] = reachable

    # --- ReplicationBackendProtocol ---

    def get_primary_lsn(self) -> int:
        return self._primary_lsn

    def get_standby_lsn(self, node_id: str) -> int:
        return self._standby_lsn.get(node_id, self._primary_lsn)

    def promote_standby(self, node_id: str) -> bool:
        if not self._reachable.get(node_id, True):
            return False
        self._promoted.add(node_id)
        return True

    def ping_node(self, node_id: str) -> bool:
        return self._reachable.get(node_id, True)


# ---------------------------------------------------------------------------
# DB-1: Replication topology
# ---------------------------------------------------------------------------


@dataclass
class ReplicationTopology:
    """Describes the primary + standby topology (DB-1).

    primary     The current primary node.
    standbys    List of standby nodes (at least one for HA).
    status      Overall replication health.
    """

    primary: ReplicationNode
    standbys: list[ReplicationNode]
    status: ReplicationStatus = ReplicationStatus.HEALTHY

    def get_standby(self, node_id: str) -> ReplicationNode | None:
        for s in self.standbys:
            if s.node_id == node_id:
                return s
        return None

    def summary(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "primary": {
                "node_id": self.primary.node_id,
                "address": self.primary.address,
                "lsn": self.primary.current_lsn,
                "status": self.primary.status.value,
            },
            "standbys": [
                {
                    "node_id": s.node_id,
                    "address": s.address,
                    "lsn": s.current_lsn,
                    "status": s.status.value,
                }
                for s in self.standbys
            ],
        }


# ---------------------------------------------------------------------------
# OPS-1: Replication monitor and lag alerting
# ---------------------------------------------------------------------------


class ReplicationMonitor:
    """Measures replication lag and emits LagAlert records (OPS-1).

    ``poll()`` queries the backend for current LSN values, computes the lag,
    compares it to the threshold policy, and emits an alert if warranted.

    Alerts are stored in ``_alerts`` (bounded to 1000 entries) and are
    queryable via ``get_alerts()``.  In production, the alert emission
    hook should send to an alerting backend (PagerDuty, CloudWatch, etc.).
    """

    _MAX_ALERTS = 1000

    def __init__(
        self,
        topology: ReplicationTopology,
        backend: ReplicationBackendProtocol,
        policy: LagThresholdPolicy | None = None,
        bytes_per_second: float = 10_000_000,  # 10 MB/s default for lag_seconds estimation
    ) -> None:
        self._topology = topology
        self._backend = backend
        self._policy = policy or LagThresholdPolicy()
        self._bytes_per_second = bytes_per_second
        self._alerts: list[LagAlert] = []
        self._lag_history: list[ReplicationLag] = []

    def poll(self) -> list[ReplicationLag]:
        """Measure lag for every standby and update node status / emit alerts."""
        primary_lsn = self._backend.get_primary_lsn()
        self._topology.primary.current_lsn = primary_lsn

        results: list[ReplicationLag] = []
        any_critical = False
        any_warning = False

        for standby in self._topology.standbys:
            standby_lsn = self._backend.get_standby_lsn(standby.node_id)
            standby.current_lsn = standby_lsn

            lag_bytes = max(0, primary_lsn - standby_lsn)
            lag_seconds = lag_bytes / self._bytes_per_second if self._bytes_per_second > 0 else 0.0

            snap = ReplicationLag(
                primary_lsn=primary_lsn,
                standby_lsn=standby_lsn,
                lag_bytes=lag_bytes,
                lag_seconds=lag_seconds,
            )
            results.append(snap)
            self._lag_history.append(snap)

            severity = self._policy.classify(lag_seconds)
            if severity is None:
                standby.status = NodeStatus.ONLINE
            elif severity == AlertSeverity.WARNING:
                standby.status = NodeStatus.LAGGING
                any_warning = True
            elif severity == AlertSeverity.CRITICAL:
                standby.status = NodeStatus.CRITICAL_LAG
                any_critical = True

            if severity is not None:
                self._emit_alert(severity, standby, snap)

        # Update overall topology status
        if any_critical:
            self._topology.status = ReplicationStatus.DEGRADED
        elif any_warning:
            self._topology.status = ReplicationStatus.DEGRADED
        else:
            self._topology.status = ReplicationStatus.HEALTHY

        return results

    def _emit_alert(
        self,
        severity: AlertSeverity,
        node: ReplicationNode,
        lag: ReplicationLag,
    ) -> None:
        alert = LagAlert(
            severity=severity,
            node_id=node.node_id,
            lag_seconds=lag.lag_seconds,
            lag_bytes=lag.lag_bytes,
            primary_lsn=lag.primary_lsn,
            standby_lsn=lag.standby_lsn,
            message=(
                f"Replication lag {severity.value.upper()} on node '{node.node_id}': "
                f"{lag.lag_seconds:.1f}s / {lag.lag_bytes} bytes behind primary."
            ),
        )
        if len(self._alerts) >= self._MAX_ALERTS:
            self._alerts.pop(0)
        self._alerts.append(alert)
        logger.warning(
            "REPLICATION_LAG_%s | node=%s lag_s=%.1f lag_bytes=%d",
            severity.value.upper(),
            node.node_id,
            lag.lag_seconds,
            lag.lag_bytes,
        )

    def get_alerts(
        self,
        severity: AlertSeverity | None = None,
        node_id: str | None = None,
    ) -> list[LagAlert]:
        alerts = self._alerts
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if node_id:
            alerts = [a for a in alerts if a.node_id == node_id]
        return list(alerts)

    def latest_lag(self, node_id: str) -> ReplicationLag | None:
        for snap in reversed(self._lag_history):
            if snap.standby_lsn is not None:
                return snap
        return None


# ---------------------------------------------------------------------------
# DB-2: Failover controller
# ---------------------------------------------------------------------------


class FailoverController:
    """Executes and records primary → standby promotion (DB-2).

    ``promote_standby(node_id)`` validates preconditions, triggers the
    promotion via the backend adapter, updates topology roles, and records
    a ``FailoverRecord`` for audit purposes.

    Preconditions checked before promotion:
    1. Target node must exist in topology.standbys.
    2. Target node must be reachable.
    3. Primary must be confirmed offline (or trigger == "drill" bypasses this).
    """

    def __init__(
        self,
        topology: ReplicationTopology,
        backend: ReplicationBackendProtocol,
        connection_registry: ConnectionRegistry | None = None,
    ) -> None:
        self._topology = topology
        self._backend = backend
        self._connection_registry = connection_registry
        self._failover_history: list[FailoverRecord] = []

    def promote_standby(
        self,
        node_id: str,
        trigger: str = "manual",
        notes: str = "",
    ) -> FailoverRecord:
        """Promote *node_id* from standby to primary.

        Updates ``topology.primary``, removes the promoted node from standbys,
        adds the old primary as a new standby (if reachable), and updates
        the connection registry (APP-1).

        Returns a ``FailoverRecord`` on success; raises ``FailoverError`` on failure.
        """
        standby = self._topology.get_standby(node_id)
        if standby is None:
            raise FailoverError(f"Node '{node_id}' is not a registered standby.")

        if not self._backend.ping_node(node_id):
            raise FailoverError(
                f"Cannot promote node '{node_id}': node is not reachable."
            )

        if self._backend.ping_node(self._topology.primary.node_id) and trigger != "drill":
            raise FailoverError(
                f"Primary '{self._topology.primary.node_id}' is still reachable. "
                "Set trigger='drill' to force a promotion during a failover drill."
            )

        started_at = datetime.now(timezone.utc).isoformat()
        start_ts = time.monotonic()

        ok = self._backend.promote_standby(node_id)
        if not ok:
            raise FailoverError(f"Backend promotion of node '{node_id}' failed.")

        old_primary = self._topology.primary
        old_primary.role = NodeRole.STANDBY
        old_primary.status = NodeStatus.OFFLINE

        standby.role = NodeRole.PRIMARY
        standby.status = NodeStatus.PROMOTED

        self._topology.primary = standby
        self._topology.standbys = [
            s for s in self._topology.standbys if s.node_id != node_id
        ]
        if self._backend.ping_node(old_primary.node_id):
            old_primary.status = NodeStatus.ONLINE
        self._topology.standbys.append(old_primary)
        self._topology.status = ReplicationStatus.HEALTHY

        if self._connection_registry:
            self._connection_registry.switch_primary(standby.host, standby.port)

        completed_at = datetime.now(timezone.utc).isoformat()
        duration = time.monotonic() - start_ts

        record = FailoverRecord(
            old_primary_id=old_primary.node_id,
            new_primary_id=node_id,
            trigger=trigger,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=round(duration, 3),
            success=True,
            notes=notes,
        )
        self._failover_history.append(record)
        logger.info(
            "FAILOVER_COMPLETED | new_primary=%s trigger=%s duration_s=%.3f",
            node_id,
            trigger,
            duration,
        )
        return record

    def failover_history(self) -> list[FailoverRecord]:
        return list(self._failover_history)


# ---------------------------------------------------------------------------
# APP-1: Application connection registry
# ---------------------------------------------------------------------------


class ConnectionRegistry:
    """Tracks the current primary connection string (APP-1).

    The application reads ``get_connection_string()`` to obtain the active
    primary's DSN.  On failover, ``switch_primary()`` updates the registry
    atomically so new requests immediately target the promoted primary.

    In production, this registry is backed by a configuration store
    (e.g. AWS SSM Parameter Store, Consul KV, or a shared env var)
    so all application instances pick up the change simultaneously.
    """

    def __init__(self, host: str, port: int, database: str, **kwargs: str) -> None:
        self._host = host
        self._port = port
        self._database = database
        self._extra = kwargs
        self._switch_history: list[dict[str, Any]] = []

    def get_connection_string(self) -> str:
        base = f"host={self._host} port={self._port} dbname={self._database}"
        extras = " ".join(f"{k}={v}" for k, v in self._extra.items())
        return f"{base} {extras}".strip()

    def current_primary(self) -> dict[str, Any]:
        return {"host": self._host, "port": self._port, "database": self._database}

    def switch_primary(self, new_host: str, new_port: int) -> None:
        """Point the application at the newly promoted primary (APP-1)."""
        old = {"host": self._host, "port": self._port}
        self._host = new_host
        self._port = new_port
        self._switch_history.append({
            "old_primary": old,
            "new_primary": {"host": new_host, "port": new_port},
            "switched_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(
            "CONNECTION_SWITCHED | old=%s:%d new=%s:%d",
            old["host"], old["port"],
            new_host, new_port,
        )

    def switch_history(self) -> list[dict[str, Any]]:
        return list(self._switch_history)


# ---------------------------------------------------------------------------
# High-level replication manager
# ---------------------------------------------------------------------------


class ReplicationManager:
    """Orchestrates replication monitoring and failover (DB-1, DB-2, OPS-1, APP-1).

    Intended as the single entry point for operational scripts and tests.
    """

    def __init__(
        self,
        topology: ReplicationTopology,
        backend: ReplicationBackendProtocol,
        policy: LagThresholdPolicy | None = None,
        connection_registry: ConnectionRegistry | None = None,
    ) -> None:
        self._topology = topology
        self._monitor = ReplicationMonitor(topology, backend, policy)
        self._failover = FailoverController(topology, backend, connection_registry)

    def poll_lag(self) -> list[ReplicationLag]:
        return self._monitor.poll()

    def get_alerts(self, severity: AlertSeverity | None = None) -> list[LagAlert]:
        return self._monitor.get_alerts(severity=severity)

    def promote(
        self, node_id: str, trigger: str = "manual", notes: str = ""
    ) -> FailoverRecord:
        return self._failover.promote_standby(node_id, trigger=trigger, notes=notes)

    def status(self) -> dict[str, Any]:
        return self._topology.summary()

    def failover_history(self) -> list[FailoverRecord]:
        return self._failover.failover_history()
