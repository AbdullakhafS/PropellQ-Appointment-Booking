"""
EP-008 US-086: Automatic Instance Removal on Failure

INFRA-1  AutoRemovalController auto-deregisters instances after consecutive
         failures reach failure_threshold.  Removed instances stop receiving
         traffic immediately.

INFRA-2  DrainPolicy — configures failure_threshold (before removal),
         drain_seconds (graceful drain window before hard removal), and
         recovery_threshold (passes needed before re-joining).  The drain
         window lets in-flight requests complete before the instance is fully
         removed.

INFRA-3  Rejoin conditions — once an instance transitions to REMOVED it enters
         RECOVERING on the first passing check.  It must accumulate
         recovery_threshold consecutive passes before returning to HEALTHY.
         This prevents flapping: a single pass after many failures does not
         restore rotation membership.

OPS-1    RemovalEventSinkProtocol — emitted on every removal and rejoin.
         Wire ``InMemoryRemovalEventSink`` in tests; in production connect to
         CloudWatch Events, PagerDuty, or an alerting pipeline.

Injectable sink pattern mirrors US-085 (HealthCheckAlerter) and US-083
(HealthCheckerProtocol) for consistency across EP-008 modules.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Constants (INFRA-2 / INFRA-3)
# ---------------------------------------------------------------------------

REMOVAL_FAILURE_THRESHOLD: int = 2     # consecutive failures → removal
REMOVAL_RECOVERY_THRESHOLD: int = 2    # consecutive passes → rejoin
DRAIN_DEFAULT_SECONDS: float = 30.0    # production drain window
DRAIN_IMMEDIATE_SECONDS: float = 0.0   # test-friendly immediate removal


# ---------------------------------------------------------------------------
# Enumerations and events
# ---------------------------------------------------------------------------


class InstanceState(str, Enum):
    """Lifecycle states for a backend instance.

    Transitions::

        HEALTHY ──(failures ≥ threshold)──► DRAINING ──(drain expires)──► REMOVED
                                          ◄──(pass while draining)
        REMOVED ──(first pass)──► RECOVERING ──(passes ≥ threshold)──► HEALTHY
        RECOVERING ──(failure)──► REMOVED
    """

    HEALTHY = "healthy"
    DRAINING = "draining"
    REMOVED = "removed"
    RECOVERING = "recovering"


@dataclass
class RemovalEvent:
    """Emitted when an instance is removed from the rotation (OPS-1).

    Attributes
    ----------
    address         ``host:port`` of the removed instance.
    reason          Short string: ``"consecutive_failures"`` or ``"drain_expired"``.
    failure_count   Number of consecutive failures at time of removal.
    removed_at      ISO-8601 UTC timestamp.
    """

    address: str
    reason: str
    failure_count: int
    removed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class RejoinEvent:
    """Emitted when a recovered instance re-joins the rotation (OPS-1).

    Attributes
    ----------
    address          ``host:port`` of the rejoining instance.
    recovery_count   Number of consecutive passes that triggered the rejoin.
    rejoined_at      ISO-8601 UTC timestamp.
    """

    address: str
    recovery_count: int
    rejoined_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# OPS-1: Event sink protocol + implementations
# ---------------------------------------------------------------------------


class RemovalEventSinkProtocol(Protocol):
    """Injectable sink for removal / rejoin lifecycle events.

    Production: push to CloudWatch Events, PagerDuty webhook, Slack, etc.
    Tests: use ``InMemoryRemovalEventSink``.
    """

    def on_removed(self, event: RemovalEvent) -> None:
        """Called when an instance is removed from rotation."""
        ...

    def on_rejoined(self, event: RejoinEvent) -> None:
        """Called when a recovered instance re-joins rotation."""
        ...


class InMemoryRemovalEventSink:
    """Captures removal and rejoin events in memory for inspection in tests."""

    def __init__(self) -> None:
        self._removal_events: list[RemovalEvent] = []
        self._rejoin_events: list[RejoinEvent] = []

    def on_removed(self, event: RemovalEvent) -> None:
        self._removal_events.append(event)

    def on_rejoined(self, event: RejoinEvent) -> None:
        self._rejoin_events.append(event)

    @property
    def removal_events(self) -> list[RemovalEvent]:
        return list(self._removal_events)

    @property
    def rejoin_events(self) -> list[RejoinEvent]:
        return list(self._rejoin_events)

    def clear(self) -> None:
        self._removal_events.clear()
        self._rejoin_events.clear()


# ---------------------------------------------------------------------------
# INFRA-2: Drain policy configuration
# ---------------------------------------------------------------------------


@dataclass
class DrainPolicy:
    """Controls when instances are removed and when they may rejoin (INFRA-2/INFRA-3).

    Attributes
    ----------
    failure_threshold   Consecutive failures before starting drain/removal.
                        Default: ``REMOVAL_FAILURE_THRESHOLD`` (2).
    recovery_threshold  Consecutive passes needed before a RECOVERING instance
                        rejoins rotation.  Provides flapping protection (INFRA-3).
                        Default: ``REMOVAL_RECOVERY_THRESHOLD`` (2).
    drain_seconds       Duration the instance stays in DRAINING state before it
                        is fully REMOVED.  Zero means immediate removal.
                        Default: ``DRAIN_IMMEDIATE_SECONDS`` (0.0) for tests;
                        use ``DRAIN_DEFAULT_SECONDS`` (30.0) in production.
    """

    failure_threshold: int = REMOVAL_FAILURE_THRESHOLD
    recovery_threshold: int = REMOVAL_RECOVERY_THRESHOLD
    drain_seconds: float = DRAIN_IMMEDIATE_SECONDS


# ---------------------------------------------------------------------------
# Internal lifecycle state tracking
# ---------------------------------------------------------------------------


@dataclass
class InstanceLifecycleState:
    """Per-instance mutable state tracked by ``AutoRemovalController``."""

    address: str
    state: InstanceState = InstanceState.HEALTHY
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    drain_started_at: float | None = None   # monotonic clock time

    def reset_counters(self) -> None:
        self.consecutive_failures = 0
        self.consecutive_successes = 0


# ---------------------------------------------------------------------------
# INFRA-1/2/3: Main controller
# ---------------------------------------------------------------------------


class AutoRemovalController:
    """Manages the full instance lifecycle: healthy → draining → removed → recovery.

    Call ``record_check(address, passed)`` after each health check result.
    The controller transitions instances through ``InstanceState`` and emits
    ``RemovalEvent`` / ``RejoinEvent`` to the configured sink.

    Use ``is_in_rotation(address)`` to determine whether an instance should
    receive traffic before calling ``LoadBalancerPool.select()``.

    Example::

        policy = DrainPolicy(failure_threshold=2, recovery_threshold=2)
        sink   = InMemoryRemovalEventSink()
        ctrl   = AutoRemovalController(policy=policy, sink=sink)

        ctrl.register("10.0.0.1:8000")
        ctrl.register("10.0.0.2:8000")

        # On each health check round
        for address, passed in health_check_results.items():
            ctrl.record_check(address, passed)

        # Determine traffic eligibility
        if ctrl.is_in_rotation("10.0.0.1:8000"):
            pool.select()
    """

    def __init__(
        self,
        policy: DrainPolicy | None = None,
        sink: RemovalEventSinkProtocol | None = None,
    ) -> None:
        self._policy: DrainPolicy = policy or DrainPolicy()
        self._sink: RemovalEventSinkProtocol
        if sink is not None:
            self._sink = sink
        else:
            self._default_sink = InMemoryRemovalEventSink()
            self._sink = self._default_sink
        self._states: dict[str, InstanceLifecycleState] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, address: str) -> None:
        """Pre-register an instance.  Records are also created on-demand in
        ``record_check``, so explicit registration is optional."""
        self._states.setdefault(address, InstanceLifecycleState(address=address))

    def deregister(self, address: str) -> None:
        """Remove an instance from tracking entirely."""
        self._states.pop(address, None)

    # ------------------------------------------------------------------
    # INFRA-1/2/3: State machine
    # ------------------------------------------------------------------

    def record_check(self, address: str, passed: bool) -> InstanceState:
        """Record the result of one health check and advance the state machine.

        Returns the updated ``InstanceState`` for the address.
        """
        ls = self._states.setdefault(
            address, InstanceLifecycleState(address=address)
        )
        policy = self._policy
        now = time.monotonic()

        if passed:
            ls.consecutive_failures = 0
            if ls.state == InstanceState.DRAINING:
                # Pass while draining → immediately healthy (abort drain)
                ls.state = InstanceState.HEALTHY
                ls.consecutive_successes = 1
                self._sink.on_rejoined(
                    RejoinEvent(address=address, recovery_count=1)
                )
            elif ls.state == InstanceState.REMOVED:
                # First pass after removal → enter RECOVERING
                ls.state = InstanceState.RECOVERING
                ls.consecutive_successes = 1
            elif ls.state == InstanceState.RECOVERING:
                ls.consecutive_successes += 1
                if ls.consecutive_successes >= policy.recovery_threshold:
                    ls.state = InstanceState.HEALTHY
                    self._sink.on_rejoined(
                        RejoinEvent(
                            address=address,
                            recovery_count=ls.consecutive_successes,
                        )
                    )
            else:  # HEALTHY
                ls.consecutive_successes += 1
        else:
            ls.consecutive_successes = 0
            if ls.state == InstanceState.HEALTHY:
                ls.consecutive_failures += 1
                if ls.consecutive_failures >= policy.failure_threshold:
                    if policy.drain_seconds > 0:
                        ls.state = InstanceState.DRAINING
                        ls.drain_started_at = now
                    else:
                        ls.state = InstanceState.REMOVED
                        self._sink.on_removed(
                            RemovalEvent(
                                address=address,
                                reason="consecutive_failures",
                                failure_count=ls.consecutive_failures,
                            )
                        )
            elif ls.state == InstanceState.DRAINING:
                ls.consecutive_failures += 1
                elapsed = now - (ls.drain_started_at or now)
                if elapsed >= policy.drain_seconds:
                    ls.state = InstanceState.REMOVED
                    self._sink.on_removed(
                        RemovalEvent(
                            address=address,
                            reason="drain_expired",
                            failure_count=ls.consecutive_failures,
                        )
                    )
            elif ls.state == InstanceState.RECOVERING:
                # Failure during recovery → back to REMOVED
                ls.consecutive_failures += 1
                ls.consecutive_successes = 0
                ls.state = InstanceState.REMOVED

        return ls.state

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def is_in_rotation(self, address: str) -> bool:
        """Return True if the instance should receive traffic (state == HEALTHY)."""
        ls = self._states.get(address)
        if ls is None:
            return True  # unknown instances assumed healthy
        return ls.state == InstanceState.HEALTHY

    def get_state(self, address: str) -> InstanceState | None:
        """Return the current lifecycle state for an address, or None if unknown."""
        ls = self._states.get(address)
        return ls.state if ls else None

    def all_states(self) -> dict[str, InstanceState]:
        """Return a snapshot of all tracked instance states."""
        return {addr: ls.state for addr, ls in self._states.items()}

    def in_rotation_addresses(self) -> list[str]:
        """Return addresses of all currently HEALTHY instances."""
        return [
            addr for addr, ls in self._states.items()
            if ls.state == InstanceState.HEALTHY
        ]

    def removal_events(self) -> list[RemovalEvent]:
        """Return removal events if using the default InMemoryRemovalEventSink."""
        if hasattr(self, "_default_sink"):
            return self._default_sink.removal_events
        return []

    def rejoin_events(self) -> list[RejoinEvent]:
        """Return rejoin events if using the default InMemoryRemovalEventSink."""
        if hasattr(self, "_default_sink"):
            return self._default_sink.rejoin_events
        return []

    def status(self) -> dict[str, Any]:
        """Return a summary of all tracked instance states."""
        counts: dict[str, int] = {s.value: 0 for s in InstanceState}
        for ls in self._states.values():
            counts[ls.state.value] += 1
        return {
            "tracked_instances": len(self._states),
            "state_counts": counts,
            "in_rotation": len(self.in_rotation_addresses()),
        }
