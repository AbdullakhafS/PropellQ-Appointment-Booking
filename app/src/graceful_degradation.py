"""
EP-008 US-092: Graceful Degradation Pattern

BE-1    Critical vs optional dependency classification — every downstream
        service call is tagged as CRITICAL or OPTIONAL via
        ``DependencyClassification``.  The ``DependencyRegistry`` holds the
        full map.  Only optional dependency failures trigger degraded mode;
        critical failures propagate normally.

BE-2    Resilience controls — ``CircuitBreaker`` implements the standard
        CLOSED → OPEN → HALF_OPEN state machine.  ``RetryPolicy`` applies
        exponential back-off with a configurable ceiling.
        ``DependencyGuard`` combines a circuit breaker + retry policy + bypass
        flag so booking-flow code can call ``execute()`` without worrying about
        which resilience layer applies.

FE-1    Degraded UX messaging — ``DegradedModeMessage`` carries a
        user-facing message and a feature flag indicating which optional
        feature is unavailable.  ``DegradedUXRegistry`` collects messages
        for the current request so the API response can include them.

OPS-1   Degraded-state alerting — ``DegradedStateAlerter`` emits an
        ``DegradedAlertEvent`` whenever the application enters or exits
        degraded mode for a dependency.  Wire ``InMemoryDegradedAlertSink``
        in tests; in production connect to PagerDuty / CloudWatch.

Injectable adapter pattern (mirrors US-085/086/088 for consistency):
  Tests wire ``FakeServiceAdapter`` (always succeeds) or
  ``FailingServiceAdapter`` (always raises) into ``DependencyGuard``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Protocol, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Constants (BE-2)
# ---------------------------------------------------------------------------

CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3   # failures to open circuit
CIRCUIT_BREAKER_RECOVERY_TIMEOUT: float = 30.0  # seconds in OPEN before HALF_OPEN
CIRCUIT_BREAKER_HALF_OPEN_SUCCESSES: int = 2   # successes to close from HALF_OPEN
RETRY_MAX_ATTEMPTS: int = 3
RETRY_BASE_DELAY_SECONDS: float = 0.5          # doubled each attempt (cap 4 s)
RETRY_MAX_DELAY_SECONDS: float = 4.0
DEPENDENCY_CALL_TIMEOUT_SECONDS: float = 5.0   # per-call wall-clock ceiling


# ---------------------------------------------------------------------------
# BE-1: Dependency classification
# ---------------------------------------------------------------------------


class DependencyKind(str, Enum):
    """Whether a downstream service is required for core booking."""
    CRITICAL = "critical"   # failure → propagate exception
    OPTIONAL = "optional"   # failure → degraded mode, booking continues


@dataclass
class DependencySpec:
    """Registry entry describing a downstream service.

    Attributes
    ----------
    name        Unique identifier (e.g. ``"reminder_service"``).
    kind        CRITICAL or OPTIONAL.
    description Human-readable summary for ops dashboards.
    """

    name: str
    kind: DependencyKind
    description: str = ""


class DependencyRegistry:
    """Holds the authoritative classification map for all dependencies.

    Usage::

        registry = DependencyRegistry()
        registry.register(DependencySpec("reminder_service", DependencyKind.OPTIONAL))
        registry.register(DependencySpec("database", DependencyKind.CRITICAL))
        assert registry.is_optional("reminder_service")
    """

    # PropelIQ's built-in dependency map
    _BUILTIN: list[DependencySpec] = [
        DependencySpec("database", DependencyKind.CRITICAL,
                       "Primary SQLite / PostgreSQL database"),
        DependencySpec("redis_cache", DependencyKind.OPTIONAL,
                       "Redis query/session cache — graceful fallback available"),
        DependencySpec("reminder_service", DependencyKind.OPTIONAL,
                       "Async reminder queue — bookings proceed without it"),
        DependencySpec("audit_service", DependencyKind.OPTIONAL,
                       "Async audit log writer — uses local buffer fallback"),
        DependencySpec("analytics_service", DependencyKind.OPTIONAL,
                       "Dashboard analytics aggregator — read-only, non-blocking"),
        DependencySpec("email_gateway", DependencyKind.OPTIONAL,
                       "Transactional email delivery — reminder retries handle delay"),
    ]

    def __init__(self) -> None:
        self._specs: dict[str, DependencySpec] = {
            s.name: s for s in self._BUILTIN
        }

    def register(self, spec: DependencySpec) -> None:
        self._specs[spec.name] = spec

    def get(self, name: str) -> DependencySpec | None:
        return self._specs.get(name)

    def is_optional(self, name: str) -> bool:
        spec = self._specs.get(name)
        return spec is not None and spec.kind == DependencyKind.OPTIONAL

    def is_critical(self, name: str) -> bool:
        spec = self._specs.get(name)
        return spec is not None and spec.kind == DependencyKind.CRITICAL

    def all_names(self) -> list[str]:
        return list(self._specs.keys())


# ---------------------------------------------------------------------------
# BE-2: Circuit breaker
# ---------------------------------------------------------------------------


class CircuitState(str, Enum):
    CLOSED = "closed"         # Normal operation
    OPEN = "open"             # Rejecting calls
    HALF_OPEN = "half_open"   # Testing recovery


class CircuitOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""


@dataclass
class CircuitBreakerStats:
    state: str
    failure_count: int
    success_count: int
    last_failure_at: str | None
    last_state_change_at: str


class CircuitBreaker:
    """Standard three-state circuit breaker (BE-2).

    State machine::

        CLOSED ─(failures ≥ threshold)─► OPEN ─(timeout elapsed)─► HALF_OPEN
        HALF_OPEN ─(successes ≥ half_open_successes)─► CLOSED
        HALF_OPEN ─(failure)─► OPEN
        CLOSED ─(failure)─► CLOSED (increments counter)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_timeout: float = CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
        half_open_successes: int = CIRCUIT_BREAKER_HALF_OPEN_SUCCESSES,
    ) -> None:
        self.name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_successes = half_open_successes
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_success_count = 0
        self._opened_at: float | None = None
        self._last_failure_at: float | None = None
        self._state_changed_at: float = time.monotonic()

    @property
    def state(self) -> CircuitState:
        self._maybe_transition_to_half_open()
        return self._state

    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def allow_request(self) -> bool:
        """Return True when the circuit allows a call to proceed."""
        s = self.state
        return s in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        self._maybe_transition_to_half_open()
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_success_count += 1
            if self._half_open_success_count >= self._half_open_successes:
                self._transition(CircuitState.CLOSED)
                self._failure_count = 0
                self._half_open_success_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        self._last_failure_at = time.monotonic()
        if self._state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.OPEN)
            self._opened_at = time.monotonic()
            self._half_open_success_count = 0
            return
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._transition(CircuitState.OPEN)
            self._opened_at = time.monotonic()

    def stats(self) -> CircuitBreakerStats:
        return CircuitBreakerStats(
            state=self.state.value,
            failure_count=self._failure_count,
            success_count=self._half_open_success_count,
            last_failure_at=(
                datetime.fromtimestamp(self._last_failure_at, timezone.utc).isoformat()
                if self._last_failure_at else None
            ),
            last_state_change_at=datetime.fromtimestamp(
                self._state_changed_at, timezone.utc
            ).isoformat(),
        )

    def _maybe_transition_to_half_open(self) -> None:
        if (
            self._state == CircuitState.OPEN
            and self._opened_at is not None
            and (time.monotonic() - self._opened_at) >= self._recovery_timeout
        ):
            self._transition(CircuitState.HALF_OPEN)
            self._half_open_success_count = 0

    def _transition(self, new_state: CircuitState) -> None:
        self._state = new_state
        self._state_changed_at = time.monotonic()


# ---------------------------------------------------------------------------
# BE-2: Retry policy
# ---------------------------------------------------------------------------


@dataclass
class RetryPolicy:
    """Exponential back-off retry configuration (BE-2).

    Attributes
    ----------
    max_attempts    Total attempts including the first call (default 3).
    base_delay      Initial delay between attempts (seconds).
    max_delay       Cap on the delay (seconds).
    retryable_on    Exception types that trigger a retry.  If empty, all
                    exceptions are retried.
    """

    max_attempts: int = RETRY_MAX_ATTEMPTS
    base_delay: float = RETRY_BASE_DELAY_SECONDS
    max_delay: float = RETRY_MAX_DELAY_SECONDS
    retryable_on: tuple[type[Exception], ...] = ()

    def delay_for(self, attempt: int) -> float:
        """Return the delay (seconds) before attempt number *attempt* (1-based)."""
        delay = self.base_delay * (2 ** (attempt - 1))
        return min(delay, self.max_delay)

    def is_retryable(self, exc: Exception) -> bool:
        if not self.retryable_on:
            return True
        return isinstance(exc, self.retryable_on)


# ---------------------------------------------------------------------------
# FE-1: Degraded UX messaging
# ---------------------------------------------------------------------------


@dataclass
class DegradedModeMessage:
    """A user-facing message indicating an optional feature is unavailable.

    Attributes
    ----------
    feature         Name of the unavailable optional feature.
    user_message    Safe, human-readable explanation for the end user.
    severity        ``"warning"`` or ``"info"`` — never ``"error"``.
    """

    feature: str
    user_message: str
    severity: str = "warning"

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "user_message": self.user_message,
            "severity": self.severity,
        }


class DegradedUXRegistry:
    """Accumulates degraded-mode messages for the current request (FE-1).

    Usage::

        ux = DegradedUXRegistry()
        ux.add("reminder_service",
               "Appointment confirmed. Reminder emails may be delayed.")
        response_body["warnings"] = ux.to_list()
    """

    _MESSAGES: dict[str, str] = {
        "redis_cache": "Some search results may load slightly slower than usual.",
        "reminder_service": "Appointment confirmed. Reminder notifications may be delayed.",
        "audit_service": "Your appointment was saved. Audit logging will sync shortly.",
        "analytics_service": "Analytics data may be temporarily unavailable.",
        "email_gateway": "Confirmation email may be delayed. Your booking is confirmed.",
    }

    def __init__(self) -> None:
        self._messages: list[DegradedModeMessage] = []
        self._feature_set: set[str] = set()

    def add(self, feature: str, user_message: str | None = None, severity: str = "warning") -> None:
        if feature in self._feature_set:
            return
        msg_text = user_message or self._MESSAGES.get(
            feature, f"The {feature} feature is temporarily unavailable."
        )
        self._messages.append(DegradedModeMessage(feature, msg_text, severity))
        self._feature_set.add(feature)

    def has_warnings(self) -> bool:
        return bool(self._messages)

    def to_list(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self._messages]

    def clear(self) -> None:
        self._messages.clear()
        self._feature_set.clear()


# ---------------------------------------------------------------------------
# OPS-1: Alerting
# ---------------------------------------------------------------------------


@dataclass
class DegradedAlertEvent:
    """Emitted when a dependency enters or exits degraded mode (OPS-1).

    Attributes
    ----------
    dependency_name  Name of the affected dependency.
    event_type       ``"entered_degraded"`` or ``"recovered"``.
    circuit_state    Current CircuitBreaker state string.
    occurred_at      ISO-8601 UTC timestamp.
    detail           Optional additional context.
    """

    dependency_name: str
    event_type: str
    circuit_state: str
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependency_name": self.dependency_name,
            "event_type": self.event_type,
            "circuit_state": self.circuit_state,
            "occurred_at": self.occurred_at,
            "detail": self.detail,
        }


class DegradedAlertSinkProtocol(Protocol):
    def emit(self, event: DegradedAlertEvent) -> None: ...


class InMemoryDegradedAlertSink:
    """Test double / local alert sink (OPS-1)."""

    def __init__(self) -> None:
        self.events: list[DegradedAlertEvent] = []

    def emit(self, event: DegradedAlertEvent) -> None:
        self.events.append(event)


class DegradedStateAlerter:
    """Fires ``DegradedAlertEvent`` on degraded-mode transitions (OPS-1).

    Tracks per-dependency degraded state to avoid duplicate alerts.
    """

    def __init__(self, sink: DegradedAlertSinkProtocol) -> None:
        self._sink = sink
        self._degraded: set[str] = set()

    def notify_failure(
        self,
        dependency_name: str,
        circuit_state: str,
        detail: str = "",
    ) -> None:
        if dependency_name not in self._degraded:
            self._degraded.add(dependency_name)
            self._sink.emit(DegradedAlertEvent(
                dependency_name=dependency_name,
                event_type="entered_degraded",
                circuit_state=circuit_state,
                detail=detail,
            ))

    def notify_recovery(
        self,
        dependency_name: str,
        circuit_state: str,
    ) -> None:
        if dependency_name in self._degraded:
            self._degraded.discard(dependency_name)
            self._sink.emit(DegradedAlertEvent(
                dependency_name=dependency_name,
                event_type="recovered",
                circuit_state=circuit_state,
            ))

    def is_degraded(self, dependency_name: str) -> bool:
        return dependency_name in self._degraded


# ---------------------------------------------------------------------------
# BE-2: DependencyGuard — combines circuit breaker + retry + bypass
# ---------------------------------------------------------------------------


class DependencyGuard:
    """Resilience facade for a single optional or critical dependency (BE-2).

    Usage::

        guard = DependencyGuard(
            "reminder_service",
            DependencyKind.OPTIONAL,
            circuit_breaker=CircuitBreaker("reminder_service"),
            retry_policy=RetryPolicy(max_attempts=2, base_delay=0.0),
            ux_registry=ux,
            alerter=alerter,
        )
        result = guard.execute(lambda: reminder_client.enqueue(job))

    For OPTIONAL dependencies, when all retry attempts are exhausted (or the
    circuit is open), ``execute()`` returns ``None`` and records a degraded-mode
    message + alert instead of raising.

    For CRITICAL dependencies, the exception is always re-raised after exhausting
    retries.
    """

    def __init__(
        self,
        dependency_name: str,
        kind: DependencyKind,
        circuit_breaker: CircuitBreaker | None = None,
        retry_policy: RetryPolicy | None = None,
        ux_registry: DegradedUXRegistry | None = None,
        alerter: DegradedStateAlerter | None = None,
    ) -> None:
        self._name = dependency_name
        self._kind = kind
        self._cb = circuit_breaker or CircuitBreaker(dependency_name)
        self._retry = retry_policy or RetryPolicy(max_attempts=1, base_delay=0.0)
        self._ux = ux_registry
        self._alerter = alerter

    @property
    def name(self) -> str:
        return self._name

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._cb

    def execute(self, fn: Callable[[], T], bypass: bool = False) -> T | None:
        """Execute *fn* with retry and circuit-breaker protection.

        Parameters
        ----------
        fn      Zero-argument callable for the dependency call.
        bypass  If True, skip this call entirely and return None immediately
                (useful for feature flags and maintenance modes).
        """
        if bypass:
            return None

        if not self._cb.allow_request():
            self._handle_failure(CircuitOpenError(f"Circuit '{self._name}' is open"))
            return None

        last_exc: Exception | None = None
        for attempt in range(1, self._retry.max_attempts + 1):
            try:
                result = fn()
                self._cb.record_success()
                if self._alerter:
                    self._alerter.notify_recovery(self._name, self._cb.state.value)
                return result
            except CircuitOpenError as exc:
                last_exc = exc
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._cb.record_failure()
                if not self._retry.is_retryable(exc):
                    break
                if attempt < self._retry.max_attempts:
                    delay = self._retry.delay_for(attempt)
                    if delay > 0:
                        time.sleep(delay)

        self._handle_failure(last_exc)
        if self._kind == DependencyKind.CRITICAL:
            raise last_exc
        return None

    def _handle_failure(self, exc: Exception | None) -> None:
        if self._ux:
            self._ux.add(self._name)
        if self._alerter:
            self._alerter.notify_failure(
                self._name,
                self._cb.state.value,
                detail=str(exc) if exc else "",
            )


# ---------------------------------------------------------------------------
# Convenience: build a standard optional guard for the PropelIQ dependency map
# ---------------------------------------------------------------------------


def build_optional_guard(
    dependency_name: str,
    ux_registry: DegradedUXRegistry | None = None,
    alerter: DegradedStateAlerter | None = None,
    failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout: float = CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    max_retry_attempts: int = 1,
) -> DependencyGuard:
    """Build a pre-configured ``DependencyGuard`` for an optional service."""
    return DependencyGuard(
        dependency_name=dependency_name,
        kind=DependencyKind.OPTIONAL,
        circuit_breaker=CircuitBreaker(
            dependency_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        ),
        retry_policy=RetryPolicy(max_attempts=max_retry_attempts, base_delay=0.0),
        ux_registry=ux_registry,
        alerter=alerter,
    )
