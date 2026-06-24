"""
EP-008 US-086: Automatic Instance Removal on Failure — Test Suite

QA-1  Removal Tests          — failed instances stop receiving traffic
QA-2  Event Visibility Tests — removal/rejoin events are emitted
QA-3  Flapping Protection    — transient failures do not cause premature removal
QA-4  Recovery Rejoin Tests  — healthy instances can safely rejoin
"""
from __future__ import annotations

import pytest

from src.instance_removal import (
    DRAIN_IMMEDIATE_SECONDS,
    REMOVAL_FAILURE_THRESHOLD,
    REMOVAL_RECOVERY_THRESHOLD,
    AutoRemovalController,
    DrainPolicy,
    InMemoryRemovalEventSink,
    InstanceState,
    RemovalEvent,
    RejoinEvent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctrl(
    failure_threshold: int = REMOVAL_FAILURE_THRESHOLD,
    recovery_threshold: int = REMOVAL_RECOVERY_THRESHOLD,
    drain_seconds: float = DRAIN_IMMEDIATE_SECONDS,
    sink: InMemoryRemovalEventSink | None = None,
) -> AutoRemovalController:
    policy = DrainPolicy(
        failure_threshold=failure_threshold,
        recovery_threshold=recovery_threshold,
        drain_seconds=drain_seconds,
    )
    return AutoRemovalController(policy=policy, sink=sink)


ADDR = "10.0.0.1:8000"
ADDR2 = "10.0.0.2:8000"


# ===========================================================================
# QA-1: Removal Tests — failed instances stop receiving traffic (INFRA-1)
# ===========================================================================


class TestAutoRemoval:
    """QA-1 — Instance removed from rotation after failure threshold."""

    def test_healthy_instance_is_in_rotation(self):
        ctrl = _ctrl()
        ctrl.register(ADDR)
        assert ctrl.is_in_rotation(ADDR) is True

    def test_single_failure_below_threshold_stays_in_rotation(self):
        ctrl = _ctrl(failure_threshold=2)
        ctrl.record_check(ADDR, False)  # only 1 failure
        assert ctrl.is_in_rotation(ADDR) is True

    def test_instance_removed_after_threshold_failures(self):
        ctrl = _ctrl(failure_threshold=2)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        assert ctrl.is_in_rotation(ADDR) is False

    def test_removed_state_reported_correctly(self):
        ctrl = _ctrl(failure_threshold=2)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        assert ctrl.get_state(ADDR) == InstanceState.REMOVED

    def test_three_failures_still_removed(self):
        ctrl = _ctrl(failure_threshold=2)
        for _ in range(3):
            ctrl.record_check(ADDR, False)
        assert not ctrl.is_in_rotation(ADDR)

    def test_multiple_instances_tracked_independently(self):
        ctrl = _ctrl(failure_threshold=2)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)   # ADDR removed
        ctrl.record_check(ADDR2, True)   # ADDR2 still healthy
        assert not ctrl.is_in_rotation(ADDR)
        assert ctrl.is_in_rotation(ADDR2)

    def test_all_states_snapshot(self):
        ctrl = _ctrl(failure_threshold=2)
        ctrl.register(ADDR)
        ctrl.register(ADDR2)
        states = ctrl.all_states()
        assert states[ADDR] == InstanceState.HEALTHY
        assert states[ADDR2] == InstanceState.HEALTHY

    def test_status_summary_counts_removed(self):
        ctrl = _ctrl(failure_threshold=2)
        ctrl.register(ADDR)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        status = ctrl.status()
        assert status["state_counts"][InstanceState.REMOVED.value] == 1
        assert status["in_rotation"] == 0

    def test_unknown_address_assumed_in_rotation(self):
        ctrl = _ctrl()
        assert ctrl.is_in_rotation("unknown:9999") is True


# ===========================================================================
# QA-2: Event Visibility Tests — removal / rejoin events emitted (OPS-1)
# ===========================================================================


class TestRemovalEvents:
    """QA-2 — Events are produced on removal and rejoin."""

    def test_removal_event_emitted_on_threshold_reached(self):
        sink = InMemoryRemovalEventSink()
        ctrl = _ctrl(failure_threshold=2, sink=sink)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        assert len(sink.removal_events) == 1

    def test_removal_event_contains_address(self):
        sink = InMemoryRemovalEventSink()
        ctrl = _ctrl(failure_threshold=2, sink=sink)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        assert sink.removal_events[0].address == ADDR

    def test_removal_event_contains_failure_count(self):
        sink = InMemoryRemovalEventSink()
        ctrl = _ctrl(failure_threshold=2, sink=sink)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        assert sink.removal_events[0].failure_count == 2

    def test_removal_event_contains_reason(self):
        sink = InMemoryRemovalEventSink()
        ctrl = _ctrl(failure_threshold=2, sink=sink)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        assert sink.removal_events[0].reason == "consecutive_failures"

    def test_no_removal_event_below_threshold(self):
        sink = InMemoryRemovalEventSink()
        ctrl = _ctrl(failure_threshold=3, sink=sink)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)  # only 2; threshold is 3
        assert sink.removal_events == []

    def test_rejoin_event_emitted_on_recovery(self):
        sink = InMemoryRemovalEventSink()
        ctrl = _ctrl(failure_threshold=2, recovery_threshold=2, sink=sink)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)  # removed
        ctrl.record_check(ADDR, True)   # recovering
        ctrl.record_check(ADDR, True)   # healthy → rejoin event
        assert len(sink.rejoin_events) == 1

    def test_rejoin_event_contains_address(self):
        sink = InMemoryRemovalEventSink()
        ctrl = _ctrl(failure_threshold=2, recovery_threshold=2, sink=sink)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, True)
        ctrl.record_check(ADDR, True)
        assert sink.rejoin_events[0].address == ADDR

    def test_rejoin_event_contains_recovery_count(self):
        sink = InMemoryRemovalEventSink()
        ctrl = _ctrl(failure_threshold=2, recovery_threshold=2, sink=sink)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, True)
        ctrl.record_check(ADDR, True)
        assert sink.rejoin_events[0].recovery_count == 2

    def test_removal_event_has_timestamp(self):
        sink = InMemoryRemovalEventSink()
        ctrl = _ctrl(failure_threshold=1, sink=sink)
        ctrl.record_check(ADDR, False)
        assert sink.removal_events[0].removed_at is not None

    def test_in_memory_sink_clear(self):
        sink = InMemoryRemovalEventSink()
        ctrl = _ctrl(failure_threshold=1, sink=sink)
        ctrl.record_check(ADDR, False)
        sink.clear()
        assert sink.removal_events == []
        assert sink.rejoin_events == []


# ===========================================================================
# QA-3: Flapping Protection Tests (INFRA-3)
# ===========================================================================


class TestFlappingProtection:
    """QA-3 — Transient failures do not cause premature removal; recovery
    requires multiple consecutive passes before rejoining rotation."""

    def test_one_failure_then_pass_stays_healthy(self):
        ctrl = _ctrl(failure_threshold=3)
        ctrl.record_check(ADDR, False)  # 1 failure
        ctrl.record_check(ADDR, True)   # pass → reset counter
        assert ctrl.is_in_rotation(ADDR)

    def test_two_failures_below_threshold_stays_healthy(self):
        ctrl = _ctrl(failure_threshold=3)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        assert ctrl.is_in_rotation(ADDR)
        assert ctrl.get_state(ADDR) == InstanceState.HEALTHY

    def test_pass_after_near_threshold_resets_counter(self):
        ctrl = _ctrl(failure_threshold=3, recovery_threshold=2)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, True)   # resets consecutive failures
        ctrl.record_check(ADDR, False)  # only 1 failure from new run
        assert ctrl.is_in_rotation(ADDR)

    def test_recovery_requires_multiple_passes(self):
        ctrl = _ctrl(failure_threshold=2, recovery_threshold=3)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)   # removed
        ctrl.record_check(ADDR, True)    # recovering, 1 pass
        ctrl.record_check(ADDR, True)    # recovering, 2 passes
        # not yet healthy — still needs 3
        assert ctrl.get_state(ADDR) == InstanceState.RECOVERING
        assert not ctrl.is_in_rotation(ADDR)

    def test_single_pass_after_removal_enters_recovering(self):
        ctrl = _ctrl(failure_threshold=2, recovery_threshold=2)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)   # removed
        ctrl.record_check(ADDR, True)    # RECOVERING
        assert ctrl.get_state(ADDR) == InstanceState.RECOVERING

    def test_failure_during_recovery_resets_to_removed(self):
        ctrl = _ctrl(failure_threshold=2, recovery_threshold=2)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)   # removed
        ctrl.record_check(ADDR, True)    # recovering
        ctrl.record_check(ADDR, False)   # failed during recovery → REMOVED again
        assert ctrl.get_state(ADDR) == InstanceState.REMOVED

    def test_draining_state_used_when_drain_seconds_positive(self):
        # Use a short drain window; actual time-based expiry tested in OPS tests
        ctrl = _ctrl(failure_threshold=2, drain_seconds=9999.0)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)
        assert ctrl.get_state(ADDR) == InstanceState.DRAINING

    def test_pass_while_draining_immediately_restores_healthy(self):
        ctrl = _ctrl(failure_threshold=2, drain_seconds=9999.0)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)   # DRAINING
        ctrl.record_check(ADDR, True)    # pass aborts drain → HEALTHY
        assert ctrl.get_state(ADDR) == InstanceState.HEALTHY
        assert ctrl.is_in_rotation(ADDR)


# ===========================================================================
# QA-4: Recovery Rejoin Tests (INFRA-3)
# ===========================================================================


class TestRecoveryRejoin:
    """QA-4 — Healthy instances re-join rotation after sufficient recovery passes."""

    def test_instance_rejoins_after_recovery_threshold(self):
        ctrl = _ctrl(failure_threshold=2, recovery_threshold=2)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)   # removed
        ctrl.record_check(ADDR, True)    # recovering
        ctrl.record_check(ADDR, True)    # healthy — rejoined
        assert ctrl.is_in_rotation(ADDR)
        assert ctrl.get_state(ADDR) == InstanceState.HEALTHY

    def test_in_rotation_addresses_includes_recovered(self):
        ctrl = _ctrl(failure_threshold=2, recovery_threshold=2)
        ctrl.register(ADDR)
        ctrl.register(ADDR2)
        ctrl.record_check(ADDR, False)
        ctrl.record_check(ADDR, False)   # ADDR removed
        ctrl.record_check(ADDR, True)
        ctrl.record_check(ADDR, True)    # ADDR recovered
        in_rotation = ctrl.in_rotation_addresses()
        assert ADDR in in_rotation
        assert ADDR2 in in_rotation

    def test_multiple_removal_and_rejoin_cycles(self):
        ctrl = _ctrl(failure_threshold=2, recovery_threshold=2)
        for _ in range(3):
            ctrl.record_check(ADDR, False)
            ctrl.record_check(ADDR, False)   # removed
            ctrl.record_check(ADDR, True)
            ctrl.record_check(ADDR, True)    # recovered
        assert ctrl.is_in_rotation(ADDR)

    def test_rejoin_fires_event_each_cycle(self):
        sink = InMemoryRemovalEventSink()
        ctrl = _ctrl(failure_threshold=2, recovery_threshold=2, sink=sink)
        for _ in range(2):
            ctrl.record_check(ADDR, False)
            ctrl.record_check(ADDR, False)
            ctrl.record_check(ADDR, True)
            ctrl.record_check(ADDR, True)
        assert len(sink.rejoin_events) == 2

    def test_default_constants(self):
        assert REMOVAL_FAILURE_THRESHOLD == 2
        assert REMOVAL_RECOVERY_THRESHOLD == 2
        assert DRAIN_IMMEDIATE_SECONDS == 0.0
