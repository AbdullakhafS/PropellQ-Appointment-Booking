"""
EP-008 US-093: Load Testing and Benchmarking — Test Suite

QA-1  Concurrency Coverage Tests  — suite exercises target concurrency levels
QA-2  Benchmark Output Tests      — p95/p99 and resource metrics are reported
QA-3  Findings Review Tests       — bottlenecks are clearly documented
QA-4  Stability Tests             — system remains stable during performance runs
"""
from __future__ import annotations

import pytest

from src.load_testing import (
    DEFAULT_ERROR_RATE_THRESHOLD,
    DEFAULT_P95_SLO_MS,
    BenchmarkReport,
    BottleneckAnalyzer,
    BottleneckFinding,
    BottleneckReport,
    LoadScenario,
    LoadTestResult,
    LoadTestRunner,
    RequestSample,
    StabilityThresholds,
    StabilityValidator,
    StabilityViolationError,
    make_propeliq_scenarios,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _noop() -> None:
    pass


def _fail_step():
    raise RuntimeError("simulated failure")


def _run(scenario: LoadScenario) -> LoadTestResult:
    return LoadTestRunner().run(scenario)


# ===========================================================================
# QA-1: Concurrency Coverage Tests (PERF-1)
# ===========================================================================


class TestConcurrencyCoverage:
    """QA-1 — Suite exercises target concurrency levels and flows."""

    def test_single_request_executed(self):
        scenario = LoadScenario("ping", _noop, total_requests=1)
        result = _run(scenario)
        assert result.total_requests == 1

    def test_multiple_requests_all_executed(self):
        scenario = LoadScenario("ping", _noop, total_requests=20)
        result = _run(scenario)
        assert result.total_requests == 20

    def test_concurrent_requests_all_complete(self):
        scenario = LoadScenario("concurrent", _noop, concurrency=4, total_requests=20)
        result = _run(scenario)
        assert result.total_requests == 20

    def test_make_propeliq_scenarios_returns_three(self):
        scenarios = make_propeliq_scenarios()
        assert len(scenarios) == 3

    def test_propeliq_scenario_names(self):
        names = [s.name for s in make_propeliq_scenarios()]
        assert "search_available_slots" in names
        assert "book_appointment" in names
        assert "send_reminder" in names

    def test_scenario_tags_assigned(self):
        scenarios = make_propeliq_scenarios()
        for s in scenarios:
            assert s.tags  # non-empty

    def test_custom_concurrency_accepted(self):
        scenarios = make_propeliq_scenarios(concurrency=5, requests_per_scenario=5)
        for s in scenarios:
            assert s.concurrency == 5
            assert s.total_requests == 5

    def test_result_scenario_name_matches(self):
        scenario = LoadScenario("my_test", _noop, total_requests=5)
        result = _run(scenario)
        assert result.scenario_name == "my_test"

    def test_runner_respects_total_requests(self):
        scenario = LoadScenario("count_test", _noop, total_requests=7)
        result = _run(scenario)
        assert len(result.samples) == 7


# ===========================================================================
# QA-2: Benchmark Output Tests (PERF-2)
# ===========================================================================


class TestBenchmarkOutput:
    """QA-2 — p95/p99 and throughput metrics are captured and reported."""

    def test_result_to_dict_has_expected_keys(self):
        scenario = LoadScenario("bench", _noop, total_requests=10)
        result = _run(scenario)
        d = result.to_dict()
        assert all(k in d for k in [
            "scenario_name", "total_requests", "error_count", "error_rate",
            "mean_ms", "p50_ms", "p95_ms", "p99_ms", "throughput_rps",
        ])

    def test_p95_computed_from_samples(self):
        result = LoadTestResult("test")
        for i in range(100):
            result.add(RequestSample("test", float(i), True))
        result.finish()
        assert result.p95_ms is not None
        assert result.p95_ms >= 90.0

    def test_p99_computed_from_samples(self):
        result = LoadTestResult("test")
        for i in range(100):
            result.add(RequestSample("test", float(i), True))
        result.finish()
        assert result.p99_ms is not None
        assert result.p99_ms >= 95.0

    def test_throughput_positive_after_run(self):
        scenario = LoadScenario("tp", _noop, total_requests=10)
        result = _run(scenario)
        assert result.throughput_rps > 0

    def test_error_rate_zero_on_success(self):
        scenario = LoadScenario("ok", _noop, total_requests=10)
        result = _run(scenario)
        assert result.error_rate == 0.0

    def test_error_rate_one_on_all_failures(self):
        scenario = LoadScenario("fail", _fail_step, total_requests=5)
        result = _run(scenario)
        assert result.error_rate == 1.0

    def test_error_count_matches_failures(self):
        call_count = [0]
        def partial_fail():
            call_count[0] += 1
            if call_count[0] <= 3:
                raise RuntimeError("fail")
        scenario = LoadScenario("partial", partial_fail, total_requests=5)
        result = _run(scenario)
        assert result.error_count == 3

    def test_benchmark_report_aggregates_results(self):
        report = BenchmarkReport()
        for scenario in make_propeliq_scenarios(requests_per_scenario=5):
            result = _run(scenario)
            report.add(result)
        assert len(report.results) == 3

    def test_benchmark_report_to_dict(self):
        report = BenchmarkReport()
        report.add(_run(LoadScenario("x", _noop, total_requests=5)))
        d = report.to_dict()
        assert all(k in d for k in ["suite_name", "generated_at", "overall_error_rate", "scenarios"])

    def test_benchmark_report_scenario_names(self):
        report = BenchmarkReport()
        report.add(_run(LoadScenario("alpha", _noop, total_requests=2)))
        report.add(_run(LoadScenario("beta", _noop, total_requests=2)))
        assert "alpha" in report.scenario_names()
        assert "beta" in report.scenario_names()

    def test_benchmark_report_get_result(self):
        report = BenchmarkReport()
        result = _run(LoadScenario("alpha", _noop, total_requests=3))
        report.add(result)
        assert report.get_result("alpha") is result

    def test_benchmark_report_worst_p95(self):
        report = BenchmarkReport()
        r1 = LoadTestResult("slow")
        r2 = LoadTestResult("fast")
        for lat in [100.0] * 20:
            r1.add(RequestSample("slow", lat, True))
        for lat in [10.0] * 20:
            r2.add(RequestSample("fast", lat, True))
        r1.finish(); r2.finish()
        report.add(r1); report.add(r2)
        assert report.worst_p95_ms() >= 100.0


# ===========================================================================
# QA-3: Findings Review Tests (DOC-1)
# ===========================================================================


class TestFindingsReview:
    """QA-3 — Bottlenecks are identified and documented."""

    def test_clean_report_has_no_findings(self):
        report = BenchmarkReport()
        report.add(_run(LoadScenario("ok", _noop, total_requests=10)))
        analyzer = BottleneckAnalyzer(StabilityThresholds(max_p95_latency_ms=10000))
        br = analyzer.analyze(report)
        assert br.is_clean

    def test_slow_scenario_generates_latency_finding(self):
        report = BenchmarkReport()
        # Inject a slow result manually
        result = LoadTestResult("slow_query")
        for _ in range(10):
            result.add(RequestSample("slow_query", 1000.0, True))
        result.finish()
        report.add(result)
        analyzer = BottleneckAnalyzer(StabilityThresholds(max_p95_latency_ms=100.0))
        br = analyzer.analyze(report)
        assert any(f.finding_type == "high_latency" for f in br.findings)

    def test_high_error_rate_generates_finding(self):
        scenario = LoadScenario("fail_all", _fail_step, total_requests=10)
        report = BenchmarkReport()
        report.add(_run(scenario))
        analyzer = BottleneckAnalyzer(StabilityThresholds(max_error_rate=0.0))
        br = analyzer.analyze(report)
        assert any(f.finding_type == "high_error_rate" for f in br.findings)

    def test_finding_has_recommendation(self):
        result = LoadTestResult("slow")
        for _ in range(10):
            result.add(RequestSample("slow", 2000.0, True))
        result.finish()
        report = BenchmarkReport()
        report.add(result)
        analyzer = BottleneckAnalyzer(StabilityThresholds(max_p95_latency_ms=100.0))
        br = analyzer.analyze(report)
        assert br.findings[0].recommendation

    def test_bottleneck_finding_to_dict(self):
        f = BottleneckFinding("slow", "high_latency", 600.0, 500.0, "Add index")
        d = f.to_dict()
        assert all(k in d for k in ["scenario_name", "finding_type", "metric_value", "recommendation"])

    def test_bottleneck_report_to_dict(self):
        br = BottleneckReport()
        d = br.to_dict()
        assert all(k in d for k in ["finding_count", "is_clean", "findings"])

    def test_finding_count_correct(self):
        result = LoadTestResult("x")
        for _ in range(10):
            result.add(RequestSample("x", 1000.0, True))
        result.finish()
        report = BenchmarkReport()
        report.add(result)
        analyzer = BottleneckAnalyzer(StabilityThresholds(max_p95_latency_ms=100.0))
        br = analyzer.analyze(report)
        assert br.finding_count >= 1


# ===========================================================================
# QA-4: Stability Tests (PERF-3)
# ===========================================================================


class TestStabilityValidation:
    """QA-4 — System remains stable; violations are clearly flagged."""

    def test_stable_run_does_not_raise(self):
        scenario = LoadScenario("ok", _noop, total_requests=10)
        result = _run(scenario)
        validator = StabilityValidator(StabilityThresholds(max_p95_latency_ms=10000))
        validator.assert_stable(result)  # must not raise

    def test_high_error_rate_raises_violation(self):
        scenario = LoadScenario("fail", _fail_step, total_requests=5)
        result = _run(scenario)
        validator = StabilityValidator(StabilityThresholds(max_error_rate=0.0))
        with pytest.raises(StabilityViolationError):
            validator.assert_stable(result)

    def test_violation_message_contains_scenario_name(self):
        result = LoadTestResult("slow_test")
        for _ in range(5):
            result.add(RequestSample("slow_test", 2000.0, True))
        result.finish()
        validator = StabilityValidator(StabilityThresholds(max_p95_latency_ms=100.0))
        with pytest.raises(StabilityViolationError, match="slow_test"):
            validator.assert_stable(result)

    def test_suite_stable_passes_on_clean(self):
        report = BenchmarkReport()
        for scenario in make_propeliq_scenarios(requests_per_scenario=5):
            report.add(_run(scenario))
        validator = StabilityValidator(StabilityThresholds(max_p95_latency_ms=10000))
        validator.assert_suite_stable(report)

    def test_suite_raises_if_any_scenario_violates(self):
        report = BenchmarkReport()
        # One passing scenario
        report.add(_run(LoadScenario("ok", _noop, total_requests=5)))
        # One failing scenario
        report.add(_run(LoadScenario("fail", _fail_step, total_requests=5)))
        validator = StabilityValidator(StabilityThresholds(max_error_rate=0.0))
        with pytest.raises(StabilityViolationError):
            validator.assert_suite_stable(report)

    def test_check_returns_empty_on_stable(self):
        scenario = LoadScenario("ok", _noop, total_requests=5)
        result = _run(scenario)
        validator = StabilityValidator(StabilityThresholds(max_p95_latency_ms=10000))
        assert validator.check(result) == []

    def test_check_returns_violations_on_unstable(self):
        scenario = LoadScenario("fail", _fail_step, total_requests=5)
        result = _run(scenario)
        validator = StabilityValidator(StabilityThresholds(max_error_rate=0.0))
        violations = validator.check(result)
        assert len(violations) >= 1

    def test_default_thresholds_defined(self):
        assert DEFAULT_P95_SLO_MS == 500.0
        assert DEFAULT_ERROR_RATE_THRESHOLD == 0.01

    def test_p99_threshold_checked_when_configured(self):
        result = LoadTestResult("x")
        for _ in range(100):
            result.add(RequestSample("x", 1000.0, True))
        result.finish()
        validator = StabilityValidator(StabilityThresholds(
            max_p95_latency_ms=10000,
            max_p99_latency_ms=100.0,
        ))
        violations = validator.check(result)
        assert any("p99" in v for v in violations)
