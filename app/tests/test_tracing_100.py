"""
TASK-100: Distributed Tracing and SLO Dashboards - Comprehensive Test Suite

Test coverage for:
- QA-1: Trace completeness validation (AC-1)
- QA-2: Metric visibility validation (AC-2)
- QA-3: Burn-rate alert validation (AC-3)
- QA-4: Dashboard coverage validation (AC-4)
- QA-5: Report export validation (AC-5)
- QA-6: Cross-link validation (AC-6)
"""

import pytest
from datetime import datetime, timedelta
import json

from src.tracing_instrumentation import (
    SpanContext, Span, Tracer, SpanKind, SpanStatus, TraceContext,
    TracingMiddleware
)
from src.metrics_slo import (
    MetricsCollector, GoldenSignal, SLOTarget, MetricBuffer
)
from src.alerting_engine import (
    AlertingEngine, BurnRateAlertRule, BurnRateWindow,
    AlertSeverity, AlertStatus, create_standard_burn_rate_alerts
)
from src.observability_dashboard import (
    OperationalDashboard, ConsumerDashboard, ReliabilityReport,
    ReportGenerator, SLOReportEntry
)
from src.tracing_correlation import (
    TraceLinkRegistry, TraceLogNavigator, TraceLogLink
)


# ============================================================================
# QA-1: Trace Completeness Validation (AC-1)
# ============================================================================

class TestTraceCompleteness:
    """QA-1: Validate AC-1 - Parent-child spans show full path and latency."""
    
    def test_trace_id_generated_on_root_span(self):
        """UT-100-001: Root span has generated trace ID."""
        context = SpanContext.create_root()
        
        assert context.trace_id is not None
        assert len(context.trace_id) == 32  # UUID without dashes
        assert context.parent_span_id is None
    
    def test_child_span_maintains_trace_hierarchy(self):
        """UT-100-002: Child span maintains parent relationship."""
        root = SpanContext.create_root()
        child = root.create_child()
        
        assert child.trace_id == root.trace_id
        assert child.parent_span_id == root.span_id
        assert child.span_id != root.span_id
    
    def test_multi_level_span_hierarchy(self):
        """UT-100-003: Multi-level spans maintain hierarchy (AC-1)."""
        root = SpanContext.create_root()
        level1 = root.create_child()
        level2 = level1.create_child()
        level3 = level2.create_child()
        
        # All share same trace
        assert level1.trace_id == root.trace_id
        assert level2.trace_id == root.trace_id
        assert level3.trace_id == root.trace_id
        
        # Parent chain
        assert level1.parent_span_id == root.span_id
        assert level2.parent_span_id == level1.span_id
        assert level3.parent_span_id == level2.span_id
    
    def test_span_duration_calculation(self):
        """UT-100-004: Span duration calculated correctly (AC-1: latency)."""
        import time
        
        span = Span(
            trace_id="test-trace",
            span_id="test-span",
            operation_name="test_operation"
        )
        
        # Record operation
        time.sleep(0.1)  # 100ms operation
        span.end()
        
        duration = span.duration_ms()
        assert duration >= 100  # At least 100ms
        assert duration < 200   # Less than 200ms (shouldn't take that long)
    
    def test_tracer_creates_spans_with_hierarchy(self):
        """UT-100-005: Tracer creates spans with parent-child hierarchy."""
        tracer = Tracer(service_name="test_service")
        
        # Root span
        root_span = tracer.start_span("root_operation")
        assert root_span.parent_span_id is None
        tracer.end_span(root_span)
        
        # Child span (in same tracer context)
        TraceContext.push(SpanContext(
            trace_id=root_span.trace_id,
            span_id=root_span.span_id
        ))
        
        child_span = tracer.start_span("child_operation")
        assert child_span.parent_span_id == root_span.span_id
        assert child_span.trace_id == root_span.trace_id
        tracer.end_span(child_span)
    
    def test_trace_export_shows_critical_path(self):
        """UT-100-006: Exported trace includes critical path (AC-1)."""
        tracer = Tracer(service_name="test_service")
        
        # Create multi-level spans
        root = tracer.start_span("root")
        tracer.end_span(root)
        
        export = tracer.export_trace()
        
        assert "critical_path" in export
        assert len(export["critical_path"]) > 0
        assert export["critical_path"][0]["operation"] == "root"


# ============================================================================
# QA-2: Metric Visibility Validation (AC-2)
# ============================================================================

class TestMetricVisibility:
    """QA-2: Validate AC-2 - p95 latency/error metrics visible per endpoint."""
    
    def test_metrics_collector_records_latency(self):
        """UT-100-007: Collector records request latency."""
        collector = MetricsCollector()
        
        collector.record_request(
            latency_ms=150.0,
            success=True,
            service="booking",
            endpoint="/api/book",
            operation="create_appointment"
        )
        
        snapshot = collector.get_metrics_snapshot()
        assert len(snapshot) > 0
    
    def test_p95_latency_calculated(self):
        """UT-100-008: P95 latency calculated from requests (AC-2)."""
        collector = MetricsCollector()
        
        # Record 100 requests
        for i in range(100):
            latency = 100.0 + (i % 50)  # Latencies: 100-149ms
            collector.record_request(
                latency_ms=latency,
                success=True,
                service="booking",
                endpoint="/api/book"
            )
        
        snapshot = collector.get_metrics_snapshot()
        
        for metric_key, signal in snapshot.items():
            if "endpoint" in metric_key:
                assert signal.latency_p95 is not None
                assert signal.latency_p95 > 0
                assert signal.latency_p95 <= 149
    
    def test_error_rate_calculated(self):
        """UT-100-009: Error rate calculated correctly (AC-2)."""
        collector = MetricsCollector()
        
        # Record 100 requests, 10 failures
        for i in range(100):
            success = i < 90
            collector.record_request(
                latency_ms=100.0,
                success=success,
                service="booking",
                endpoint="/api/book"
            )
        
        snapshot = collector.get_metrics_snapshot()
        
        for signal in snapshot.values():
            assert signal.error_rate() == 0.10  # 10%
    
    def test_endpoint_specific_metrics(self):
        """UT-100-010: Get metrics for specific endpoint (AC-2)."""
        collector = MetricsCollector()
        
        # Different endpoints
        collector.record_request(100.0, True, "booking", "/api/book")
        collector.record_request(200.0, True, "booking", "/api/search")
        
        book_metrics = collector.get_endpoint_metrics("/api/book", "booking")
        search_metrics = collector.get_endpoint_metrics("/api/search", "booking")
        
        assert book_metrics is not None
        assert search_metrics is not None
        assert book_metrics.latency_mean != search_metrics.latency_mean
    
    def test_top_failing_endpoints(self):
        """UT-100-011: Identify top failing endpoints (AC-2, AC-4)."""
        collector = MetricsCollector()
        
        # Endpoint 1: 5% error rate
        for i in range(100):
            collector.record_request(100.0, i < 95, "svc", "/endpoint1")
        
        # Endpoint 2: 10% error rate
        for i in range(100):
            collector.record_request(100.0, i < 90, "svc", "/endpoint2")
        
        top = collector.get_top_failing_endpoints("svc", limit=2)
        
        assert len(top) == 2
        assert top[0][0] == "/endpoint2"  # Highest error rate first
        assert top[1][0] == "/endpoint1"


# ============================================================================
# QA-3: Burn-Rate Alert Validation (AC-3)
# ============================================================================

class TestBurnRateAlerts:
    """QA-3: Validate AC-3 - SLO burn-rate alerts trigger on degradation."""
    
    def test_burn_rate_calculated(self):
        """UT-100-012: Burn rate calculated from error budget."""
        slo = SLOTarget(
            name="booking_availability",
            description="99.9% uptime",
            metric_type="availability",
            target_value=0.999,
            window_seconds=30 * 24 * 3600  # 30 days
        )
        
        # All successful (no errors)
        burn_rate_zero = slo.burn_rate(0, 1000)
        assert burn_rate_zero == 0.0
        
        # 0.1% error rate (at target)
        burn_rate_one = slo.burn_rate(1, 1000)
        assert burn_rate_one == pytest.approx(1.0, rel=0.1)
        
        # 0.2% error rate (2x target)
        burn_rate_two = slo.burn_rate(2, 1000)
        assert burn_rate_two == pytest.approx(2.0, rel=0.1)
    
    def test_alert_fires_on_high_burn_rate(self):
        """UT-100-013: Alert fires when burn rate exceeds threshold."""
        rule = create_standard_burn_rate_alerts("test_slo")
        
        # Simulate degradation
        compliance = {
            "test_slo": {
                "burn_rate": 5.0,  # 5x burn rate over 30 minutes
                "target": 0.999,
                "actual": 0.995
            }
        }
        
        alert = rule.evaluate(compliance["test_slo"])
        
        assert alert is not None
        assert alert.status == AlertStatus.FIRING
        assert alert.severity == AlertSeverity.WARNING
    
    def test_alerting_engine_manages_alerts(self):
        """UT-100-014: Alerting engine manages alert lifecycle."""
        engine = AlertingEngine()
        rule = create_standard_burn_rate_alerts("test_slo")
        engine.register_rule(rule)
        
        # Track fired alerts
        fired_alerts = []
        engine.register_handler(lambda a: fired_alerts.append(a))
        
        # Initial degradation
        compliance_bad = {
            "test_slo": {
                "burn_rate": 10.0,
                "target": 0.999,
                "actual": 0.99
            }
        }
        
        alerts = engine.evaluate_all(compliance_bad)
        assert len(alerts) > 0
        assert any(a.status == AlertStatus.FIRING for a in alerts)
    
    def test_multiple_window_alerts(self):
        """UT-100-015: Multiple burn-rate windows trigger alerts (AC-3)."""
        windows = [
            BurnRateWindow("slow", 3600, 2.0, AlertSeverity.WARNING),
            BurnRateWindow("fast", 300, 10.0, AlertSeverity.CRITICAL),
        ]
        rule = BurnRateAlertRule("test", windows)
        
        # Test different burn rates
        compliance_warning = {"burn_rate": 3.0}
        alert = rule.evaluate(compliance_warning)
        assert alert.severity == AlertSeverity.WARNING
        
        compliance_critical = {"burn_rate": 12.0}
        alert = rule.evaluate(compliance_critical)
        assert alert.severity == AlertSeverity.CRITICAL


# ============================================================================
# QA-4: Dashboard Coverage Validation (AC-4)
# ============================================================================

class TestDashboardCoverage:
    """QA-4: Validate AC-4 - Dashboard shows required metrics."""
    
    def test_operational_dashboard_has_required_panels(self):
        """UT-100-016: Operational dashboard has uptime/latency/errors (AC-4)."""
        dashboard = OperationalDashboard()
        panel_titles = [p.title for p in dashboard.panels]
        
        assert any("Uptime" in t for t in panel_titles)
        assert any("Latency" in t for t in panel_titles)
        assert any("Error" in t for t in panel_titles)
        assert any("Failing" in t for t in panel_titles)
    
    def test_dashboard_exports_to_json(self):
        """UT-100-017: Dashboard configuration exports to JSON (AC-4)."""
        dashboard = OperationalDashboard()
        json_output = dashboard.to_json()
        
        data = json.loads(json_output)
        assert "dashboard" in data
        assert "panels" in data
        assert len(data["panels"]) > 0
    
    def test_consumer_dashboard_simplified(self):
        """UT-100-018: Consumer dashboard provides simplified view (AC-4)."""
        dashboard = ConsumerDashboard()
        
        # Should have fewer, simpler panels
        assert len(dashboard.panels) < 6
        
        panel_titles = [p.title for p in dashboard.panels]
        assert any("SLO" in t for t in panel_titles)
        assert any("Budget" in t for t in panel_titles)


# ============================================================================
# QA-5: Report Export Validation (AC-5)
# ============================================================================

class TestReportExport:
    """QA-5: Validate AC-5 - Weekly SLO/error-budget report available."""
    
    def test_slo_report_entry_created(self):
        """UT-100-019: SLO report entry captures compliance data."""
        entry = SLOReportEntry(
            slo_name="booking_availability",
            target=0.999,
            actual=0.9985,
            compliant=True,
            error_budget_seconds=2592,  # ~43 minutes
            error_budget_percent=5.0,
            window_days=30
        )
        
        assert entry.slo_name == "booking_availability"
        assert entry.compliant is True
    
    def test_reliability_report_generated(self):
        """UT-100-020: Reliability report generated with SLOs (AC-5)."""
        report = ReliabilityReport(
            report_date=datetime.utcnow(),
            report_period_start=datetime.utcnow() - timedelta(days=7),
            report_period_end=datetime.utcnow()
        )
        
        entry = SLOReportEntry(
            slo_name="test_slo",
            target=0.999,
            actual=0.9985,
            compliant=True,
            error_budget_seconds=2592,
            error_budget_percent=5.0,
            window_days=7
        )
        report.add_slo_entry(entry)
        report.calculate_summary()
        
        assert report.total_slos == 1
        assert report.slos_met == 1
        assert report.overall_slo_percent == 100.0
    
    def test_report_exports_json(self):
        """UT-100-021: Report exports to JSON format (AC-5)."""
        report = ReliabilityReport(
            report_date=datetime.utcnow(),
            report_period_start=datetime.utcnow() - timedelta(days=7),
            report_period_end=datetime.utcnow()
        )
        report.add_slo_entry(SLOReportEntry(
            "test", 0.999, 0.998, True, 2592, 5.0, 7
        ))
        report.calculate_summary()
        
        json_output = report.to_json()
        data = json.loads(json_output)
        
        assert "summary" in data
        assert data["summary"]["total_slos"] == 1
    
    def test_report_exports_html(self):
        """UT-100-022: Report exports to HTML format (AC-5)."""
        report = ReliabilityReport(
            report_date=datetime.utcnow(),
            report_period_start=datetime.utcnow() - timedelta(days=7),
            report_period_end=datetime.utcnow()
        )
        report.add_slo_entry(SLOReportEntry(
            "test", 0.999, 0.998, True, 2592, 5.0, 7
        ))
        report.calculate_summary()
        
        html_output = report.to_html()
        
        assert "<html>" in html_output
        assert "Weekly Reliability Report" in html_output
        assert "test" in html_output  # SLO name


# ============================================================================
# QA-6: Cross-Link Validation (AC-6)
# ============================================================================

class TestTraceLinkValidation:
    """QA-6: Validate AC-6 - Trace and logs cross-linked by correlation ID."""
    
    def test_trace_log_link_registered(self):
        """UT-100-023: Trace-log link registered (AC-6)."""
        registry = TraceLinkRegistry()
        
        registry.register_trace("trace-123", "corr-456")
        
        assert "corr-456" in registry.correlation_to_traces
        assert "trace-123" in registry.correlation_to_traces["corr-456"]
    
    def test_logs_associated_with_correlation(self):
        """UT-100-024: Logs associated with correlation ID (AC-6)."""
        registry = TraceLinkRegistry()
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Test log",
            "level": "INFO"
        }
        
        registry.register_log("corr-123", log_entry)
        
        logs = registry.correlation_to_logs["corr-123"]
        assert len(logs) == 1
        assert logs[0]["message"] == "Test log"
    
    def test_get_logs_for_trace(self):
        """UT-100-025: Navigate from trace to logs (AC-6)."""
        registry = TraceLinkRegistry()
        
        registry.register_trace("trace-123", "corr-456")
        registry.register_log("corr-456", {"message": "log1"})
        registry.register_log("corr-456", {"message": "log2"})
        
        logs = registry.get_logs_for_trace("trace-123")
        
        assert len(logs) == 2
        assert logs[0]["message"] == "log1"
    
    def test_get_traces_for_logs(self):
        """UT-100-026: Navigate from logs to traces (AC-6)."""
        registry = TraceLinkRegistry()
        
        registry.register_trace("trace-123", "corr-456")
        registry.register_trace("trace-789", "corr-456")
        registry.register_log("corr-456", {"message": "log1"})
        
        traces = registry.get_traces_for_correlation("corr-456")
        
        assert len(traces) == 2
        assert "trace-123" in traces
        assert "trace-789" in traces
    
    def test_trace_log_navigator(self):
        """UT-100-027: Navigator enables cross-navigation (AC-6)."""
        registry = TraceLinkRegistry()
        registry.register_trace("trace-123", "corr-456")
        registry.register_log("corr-456", {"message": "error"})
        
        navigator = TraceLogNavigator(registry)
        
        # Trace → Logs
        investigation = navigator.investigate_trace("trace-123")
        assert investigation["correlation_id"] == "corr-456"
        assert investigation["log_count"] == 1
        
        # Logs → Traces
        investigation = navigator.investigate_logs("corr-456")
        assert investigation["trace_count"] == 1
    
    def test_investigation_report_created(self):
        """UT-100-028: Investigation report combines traces & logs (AC-6)."""
        registry = TraceLinkRegistry()
        registry.register_trace("trace-1", "corr-x")
        registry.register_log("corr-x", {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "ERROR",
            "message": "Database error"
        })
        
        navigator = TraceLogNavigator(registry)
        report = navigator.create_investigation_report("corr-x")
        
        assert report["correlation_id"] == "corr-x"
        assert report["incident_summary"]["trace_count"] == 1
        assert report["incident_summary"]["log_count"] == 1
        assert len(report["errors"]) == 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestLoggingIntegration:
    """Integration tests for full TASK-100 workflow."""
    
    def test_end_to_end_tracing_and_metrics(self):
        """UT-100-029: Complete tracing and metrics workflow."""
        # Setup
        tracer = Tracer("test_service")
        collector = MetricsCollector()
        
        # Create span
        span = tracer.start_span("request", kind=SpanKind.SERVER)
        
        # Simulate work
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.url", "/api/book")
        
        tracer.end_span(span)
        
        # Record metrics
        collector.record_request(
            latency_ms=span.duration_ms(),
            success=True,
            service="test_service",
            endpoint="/api/book"
        )
        
        # Verify
        snapshot = collector.get_metrics_snapshot()
        assert len(snapshot) > 0
    
    def test_full_incident_investigation(self):
        """UT-100-030: Full incident investigation workflow (AC-6)."""
        # Setup systems
        registry = TraceLinkRegistry()
        navigator = TraceLogNavigator(registry)
        
        # Register trace-log linkage
        correlation = "incident-001"
        registry.register_trace("trace-abc", correlation)
        registry.register_log(correlation, {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "ERROR",
            "message": "Payment processing failed",
            "service": "payment"
        })
        
        # Investigate
        report = navigator.create_investigation_report(correlation)
        
        assert report["correlation_id"] == correlation
        assert report["incident_summary"]["trace_count"] == 1
        assert len(report["errors"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
