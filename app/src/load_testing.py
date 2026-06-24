"""
EP-008 US-093: Load Testing and Benchmarking

PERF-1  Load test suite authoring — ``LoadScenario`` defines a named test
        with a callable ``step`` function (simulates one virtual user
        iteration), target concurrency, ramp-up duration, and hold duration.
        ``LoadTestRunner`` executes scenarios sequentially using a thread pool
        so tests run without external tools.

PERF-2  Metrics capture and benchmarking — ``LoadTestResult`` captures
        per-request latency samples, error counts, total throughput, and
        per-endpoint p95 / p99 percentiles.  ``BenchmarkReport`` aggregates
        all scenario results into a single structured report ready for
        dashboards or CI assertions.

PERF-3  Stability validation — ``StabilityValidator`` asserts that no
        scenario exceeded the acceptable error rate and that p95 latency
        stayed within the configured SLO budget.  A failed assertion raises
        ``StabilityViolationError`` with a clear diagnostic message.

DOC-1   Bottleneck reporting — ``BottleneckReport`` summarises the slowest
        endpoints, highest error-rate scenarios, and recommended follow-up
        actions.  ``BottleneckAnalyzer.analyze()`` builds this from a
        completed ``BenchmarkReport``.

All concurrency is simulated via Python's ``concurrent.futures.ThreadPoolExecutor``
using injectable step callables, so the suite is self-contained and does not
require a live server during unit tests.  Replace step callables with real HTTP
requests (``requests.get(url)``) for production load runs.
"""
from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Constants (PERF-2 / PERF-3)
# ---------------------------------------------------------------------------

DEFAULT_P95_SLO_MS: float = 500.0        # 500 ms p95 latency budget
DEFAULT_ERROR_RATE_THRESHOLD: float = 0.01  # 1 % acceptable error rate
DEFAULT_RAMP_UP_SECONDS: float = 0.0      # test-friendly: no ramp-up by default
DEFAULT_HOLD_SECONDS: float = 0.0         # test-friendly: minimal hold
DEFAULT_CONCURRENCY: int = 1


# ---------------------------------------------------------------------------
# PERF-1: Load scenario
# ---------------------------------------------------------------------------


@dataclass
class LoadScenario:
    """Describes one load test scenario (PERF-1).

    Attributes
    ----------
    name            Unique scenario identifier (e.g. ``"search_available_slots"``).
    step            Zero-argument callable representing one virtual-user iteration.
                    Should return a truthy value on success and raise on failure.
    concurrency     Number of concurrent virtual users.
    total_requests  Total number of requests to issue (across all VUs).
    ramp_up_seconds Seconds over which to increase concurrency from 1 to ``concurrency``.
    tags            Optional labels for grouping (e.g. ``{"flow": "booking"}``).
    """

    name: str
    step: Callable[[], Any]
    concurrency: int = DEFAULT_CONCURRENCY
    total_requests: int = 10
    ramp_up_seconds: float = DEFAULT_RAMP_UP_SECONDS
    tags: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PERF-2: Per-request sample
# ---------------------------------------------------------------------------


@dataclass
class RequestSample:
    """Result of a single virtual-user step execution.

    Attributes
    ----------
    scenario_name   Name of the parent ``LoadScenario``.
    latency_ms      Wall-clock time for the step in milliseconds.
    success         True when the step returned without raising.
    error           Exception message if success is False.
    sampled_at      ISO-8601 UTC timestamp.
    """

    scenario_name: str
    latency_ms: float
    success: bool
    error: str = ""
    sampled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# PERF-2: Scenario result
# ---------------------------------------------------------------------------


class LoadTestResult:
    """Aggregated metrics for one completed ``LoadScenario`` (PERF-2).

    All percentile calculations are done lazily from the raw sample list.
    """

    def __init__(self, scenario_name: str) -> None:
        self.scenario_name = scenario_name
        self.samples: list[RequestSample] = []
        self._started_at: float = time.monotonic()
        self._finished_at: float | None = None

    def add(self, sample: RequestSample) -> None:
        self.samples.append(sample)

    def finish(self) -> None:
        self._finished_at = time.monotonic()

    # ------------------------------------------------------------------
    # Derived metrics
    # ------------------------------------------------------------------

    @property
    def total_requests(self) -> int:
        return len(self.samples)

    @property
    def error_count(self) -> int:
        return sum(1 for s in self.samples if not s.success)

    @property
    def error_rate(self) -> float:
        if not self.samples:
            return 0.0
        return self.error_count / len(self.samples)

    @property
    def latencies(self) -> list[float]:
        return [s.latency_ms for s in self.samples]

    def _percentile(self, p: float) -> float | None:
        lats = sorted(self.latencies)
        if not lats:
            return None
        idx = max(0, int(len(lats) * p / 100) - 1)
        return lats[min(idx, len(lats) - 1)]

    @property
    def p50_ms(self) -> float | None:
        return self._percentile(50)

    @property
    def p95_ms(self) -> float | None:
        return self._percentile(95)

    @property
    def p99_ms(self) -> float | None:
        return self._percentile(99)

    @property
    def mean_ms(self) -> float | None:
        lats = self.latencies
        return statistics.mean(lats) if lats else None

    @property
    def min_ms(self) -> float | None:
        lats = self.latencies
        return min(lats) if lats else None

    @property
    def max_ms(self) -> float | None:
        lats = self.latencies
        return max(lats) if lats else None

    @property
    def duration_seconds(self) -> float:
        if self._finished_at is None:
            return 0.0
        return self._finished_at - self._started_at

    @property
    def throughput_rps(self) -> float:
        dur = self.duration_seconds
        if dur <= 0:
            return 0.0
        return self.total_requests / dur

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "total_requests": self.total_requests,
            "error_count": self.error_count,
            "error_rate": round(self.error_rate, 4),
            "mean_ms": round(self.mean_ms or 0, 2),
            "min_ms": round(self.min_ms or 0, 2),
            "max_ms": round(self.max_ms or 0, 2),
            "p50_ms": round(self.p50_ms or 0, 2),
            "p95_ms": round(self.p95_ms or 0, 2),
            "p99_ms": round(self.p99_ms or 0, 2),
            "throughput_rps": round(self.throughput_rps, 2),
            "duration_seconds": round(self.duration_seconds, 3),
        }


# ---------------------------------------------------------------------------
# PERF-1: Runner
# ---------------------------------------------------------------------------


class LoadTestRunner:
    """Executes ``LoadScenario`` instances and collects metrics (PERF-1).

    Uses a ``ThreadPoolExecutor`` so multiple virtual users run in parallel.
    The runner is self-contained — no live server or network required when
    ``step`` is a pure Python callable.

    Usage::

        runner = LoadTestRunner()
        result = runner.run(LoadScenario(
            name="search_slots",
            step=lambda: db.query("SELECT …"),
            concurrency=5,
            total_requests=100,
        ))
        assert result.p95_ms < 100
    """

    def __init__(self, sleep_fn: Callable[[float], None] = time.sleep) -> None:
        self._sleep = sleep_fn

    def run(self, scenario: LoadScenario) -> LoadTestResult:
        """Execute *scenario* and return an aggregated ``LoadTestResult``."""
        result = LoadTestResult(scenario.name)
        max_workers = max(1, scenario.concurrency)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(self._run_step, scenario)
                for _ in range(scenario.total_requests)
            ]
            for fut in as_completed(futures):
                sample = fut.result()
                result.add(sample)

        result.finish()
        return result

    def _run_step(self, scenario: LoadScenario) -> RequestSample:
        t0 = time.monotonic()
        try:
            scenario.step()
            latency = (time.monotonic() - t0) * 1000.0
            return RequestSample(
                scenario_name=scenario.name,
                latency_ms=latency,
                success=True,
            )
        except Exception as exc:  # noqa: BLE001
            latency = (time.monotonic() - t0) * 1000.0
            return RequestSample(
                scenario_name=scenario.name,
                latency_ms=latency,
                success=False,
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# PERF-2: Benchmark report
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkReport:
    """Aggregated results for a full load test suite run (PERF-2).

    Attributes
    ----------
    results         Per-scenario ``LoadTestResult`` objects.
    generated_at    ISO-8601 UTC timestamp.
    suite_name      Optional label for the test run.
    """

    results: list[LoadTestResult] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    suite_name: str = "PropelIQ Load Test Suite"

    def add(self, result: LoadTestResult) -> None:
        self.results.append(result)

    def scenario_names(self) -> list[str]:
        return [r.scenario_name for r in self.results]

    def get_result(self, scenario_name: str) -> LoadTestResult | None:
        return next((r for r in self.results if r.scenario_name == scenario_name), None)

    def overall_error_rate(self) -> float:
        total = sum(r.total_requests for r in self.results)
        errors = sum(r.error_count for r in self.results)
        return errors / total if total > 0 else 0.0

    def worst_p95_ms(self) -> float | None:
        vals = [r.p95_ms for r in self.results if r.p95_ms is not None]
        return max(vals) if vals else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "generated_at": self.generated_at,
            "scenario_count": len(self.results),
            "overall_error_rate": round(self.overall_error_rate(), 4),
            "worst_p95_ms": round(self.worst_p95_ms() or 0, 2),
            "scenarios": [r.to_dict() for r in self.results],
        }


# ---------------------------------------------------------------------------
# PERF-3: Stability validator
# ---------------------------------------------------------------------------


class StabilityViolationError(Exception):
    """Raised when a scenario violates stability thresholds (PERF-3)."""


@dataclass
class StabilityThresholds:
    """Configurable per-scenario stability thresholds (PERF-3 / OPS-1).

    Attributes
    ----------
    max_error_rate      Acceptable fraction of failed requests (0.0–1.0).
    max_p95_latency_ms  Acceptable p95 response time in milliseconds.
    max_p99_latency_ms  Optional p99 ceiling; ``None`` means unchecked.
    """

    max_error_rate: float = DEFAULT_ERROR_RATE_THRESHOLD
    max_p95_latency_ms: float = DEFAULT_P95_SLO_MS
    max_p99_latency_ms: float | None = None


class StabilityValidator:
    """Validates benchmark results against stability thresholds (PERF-3).

    Usage::

        validator = StabilityValidator(StabilityThresholds(max_p95_latency_ms=200))
        validator.assert_stable(result)  # raises StabilityViolationError if not
    """

    def __init__(self, thresholds: StabilityThresholds | None = None) -> None:
        self._thresholds = thresholds or StabilityThresholds()

    def check(self, result: LoadTestResult) -> list[str]:
        """Return a list of violation messages (empty = stable)."""
        violations: list[str] = []
        t = self._thresholds

        if result.error_rate > t.max_error_rate:
            violations.append(
                f"[{result.scenario_name}] error_rate={result.error_rate:.2%} "
                f"exceeds threshold {t.max_error_rate:.2%}"
            )
        if result.p95_ms is not None and result.p95_ms > t.max_p95_latency_ms:
            violations.append(
                f"[{result.scenario_name}] p95={result.p95_ms:.1f}ms "
                f"exceeds SLO {t.max_p95_latency_ms:.1f}ms"
            )
        if (
            t.max_p99_latency_ms is not None
            and result.p99_ms is not None
            and result.p99_ms > t.max_p99_latency_ms
        ):
            violations.append(
                f"[{result.scenario_name}] p99={result.p99_ms:.1f}ms "
                f"exceeds ceiling {t.max_p99_latency_ms:.1f}ms"
            )
        return violations

    def assert_stable(self, result: LoadTestResult) -> None:
        violations = self.check(result)
        if violations:
            raise StabilityViolationError("\n".join(violations))

    def assert_suite_stable(self, report: BenchmarkReport) -> None:
        all_violations: list[str] = []
        for result in report.results:
            all_violations.extend(self.check(result))
        if all_violations:
            raise StabilityViolationError("\n".join(all_violations))


# ---------------------------------------------------------------------------
# DOC-1: Bottleneck reporting
# ---------------------------------------------------------------------------


@dataclass
class BottleneckFinding:
    """A single bottleneck observation with recommended action (DOC-1).

    Attributes
    ----------
    scenario_name   The scenario where the bottleneck was detected.
    finding_type    ``"high_latency"`` | ``"high_error_rate"`` | ``"low_throughput"``
    metric_value    Observed value (ms or fraction).
    threshold       The comparison threshold.
    recommendation  Suggested follow-up action.
    """

    scenario_name: str
    finding_type: str
    metric_value: float
    threshold: float
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "finding_type": self.finding_type,
            "metric_value": round(self.metric_value, 3),
            "threshold": round(self.threshold, 3),
            "recommendation": self.recommendation,
        }


@dataclass
class BottleneckReport:
    """Summary of all bottleneck findings from a benchmark run (DOC-1).

    Attributes
    ----------
    findings            List of identified bottlenecks.
    benchmark_report    Reference to the source ``BenchmarkReport``.
    generated_at        ISO-8601 UTC timestamp.
    """

    findings: list[BottleneckFinding] = field(default_factory=list)
    benchmark_report: BenchmarkReport | None = None
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def is_clean(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "finding_count": self.finding_count,
            "is_clean": self.is_clean,
            "findings": [f.to_dict() for f in self.findings],
        }


class BottleneckAnalyzer:
    """Produces a ``BottleneckReport`` from a completed ``BenchmarkReport`` (DOC-1).

    Thresholds are configurable via ``StabilityThresholds``.
    """

    def __init__(
        self,
        thresholds: StabilityThresholds | None = None,
        min_throughput_rps: float = 0.0,
    ) -> None:
        self._thresholds = thresholds or StabilityThresholds()
        self._min_throughput = min_throughput_rps

    def analyze(self, report: BenchmarkReport) -> BottleneckReport:
        findings: list[BottleneckFinding] = []

        for result in report.results:
            if (
                result.p95_ms is not None
                and result.p95_ms > self._thresholds.max_p95_latency_ms
            ):
                findings.append(BottleneckFinding(
                    scenario_name=result.scenario_name,
                    finding_type="high_latency",
                    metric_value=result.p95_ms,
                    threshold=self._thresholds.max_p95_latency_ms,
                    recommendation=(
                        f"p95 latency ({result.p95_ms:.0f}ms) exceeds SLO. "
                        "Review index coverage, N+1 queries, or introduce caching."
                    ),
                ))

            if result.error_rate > self._thresholds.max_error_rate:
                findings.append(BottleneckFinding(
                    scenario_name=result.scenario_name,
                    finding_type="high_error_rate",
                    metric_value=result.error_rate,
                    threshold=self._thresholds.max_error_rate,
                    recommendation=(
                        f"Error rate ({result.error_rate:.1%}) exceeds threshold. "
                        "Review error logs and add retry logic or circuit breakers."
                    ),
                ))

            if (
                self._min_throughput > 0
                and result.throughput_rps < self._min_throughput
            ):
                findings.append(BottleneckFinding(
                    scenario_name=result.scenario_name,
                    finding_type="low_throughput",
                    metric_value=result.throughput_rps,
                    threshold=self._min_throughput,
                    recommendation=(
                        f"Throughput ({result.throughput_rps:.1f} req/s) below target. "
                        "Profile hot paths and consider connection pooling or async I/O."
                    ),
                ))

        return BottleneckReport(findings=findings, benchmark_report=report)


# ---------------------------------------------------------------------------
# Pre-built PropelIQ load scenarios (PERF-1)
# ---------------------------------------------------------------------------


def make_propeliq_scenarios(
    search_step: Callable[[], Any] | None = None,
    booking_step: Callable[[], Any] | None = None,
    reminder_step: Callable[[], Any] | None = None,
    concurrency: int = 1,
    requests_per_scenario: int = 10,
) -> list[LoadScenario]:
    """Return the standard PropelIQ scenario suite (PERF-1).

    Pass real callable steps to exercise live endpoints, or leave as None
    to use a no-op stub for unit testing.
    """
    noop: Callable[[], None] = lambda: None

    return [
        LoadScenario(
            name="search_available_slots",
            step=search_step or noop,
            concurrency=concurrency,
            total_requests=requests_per_scenario,
            tags={"flow": "booking", "endpoint": "/api/appointments/available"},
        ),
        LoadScenario(
            name="book_appointment",
            step=booking_step or noop,
            concurrency=concurrency,
            total_requests=requests_per_scenario,
            tags={"flow": "booking", "endpoint": "/api/appointments"},
        ),
        LoadScenario(
            name="send_reminder",
            step=reminder_step or noop,
            concurrency=concurrency,
            total_requests=requests_per_scenario,
            tags={"flow": "reminders", "endpoint": "/api/reminders"},
        ),
    ]
