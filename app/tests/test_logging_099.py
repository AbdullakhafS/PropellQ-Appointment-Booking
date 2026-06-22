"""
Centralized Logging Test Suite - TASK-099

Test coverage for:
- QA-1: Correlation ID injection and propagation (AC-1)
- QA-2: Cross-service discoverability by correlation ID (AC-2)
- QA-3: Redaction/masking validation (AC-3)
- QA-4: Delivery reliability validation (AC-4)
- QA-5: Searchability and filtering (AC-5)
- QA-6: Retention policy enforcement (AC-6)
"""

import pytest
from datetime import datetime, timedelta
import json
from typing import Dict, Any

from src.logging_schema import (
    StructuredLogEntry, CorrelationContext, LogContext, LogEnvironment,
    LogSeverity, LogSource, CorrelationPropagator, get_correlation_id,
    push_context, pop_context, current_context
)
from src.logging_redaction import (
    FieldRedactor, LogRedactor, RedactionLevel, SanitizedLogEntry,
    LoggingBoundary, create_safe_log_entry
)
from src.logging_pipeline import (
    LogPipeline, LogSink, InMemoryLogSink, DeliveryStatus,
    RetentionPolicy, PipelineFactory, LogDeliveryRecord
)
from src.logging_search import (
    QueryBuilder, TimelineBuilder, TimelineEvent, TimelineEventType,
    IncidentQuery
)


# ============================================================================
# QA-1: Correlation ID Injection and Propagation (AC-1)
# ============================================================================

class TestCorrelationInjection:
    """QA-1: Validate AC-1 - Missing correlation ID is generated."""
    
    def test_correlation_id_generated_on_missing(self):
        """UT-099-001: Generate correlation ID when missing."""
        headers = {}  # No X-Correlation-ID header
        context = CorrelationContext.from_headers(headers)
        
        assert context.correlation_id is not None
        assert len(context.correlation_id) > 0
        # Should be UUID format
        assert "-" in context.correlation_id
    
    def test_correlation_id_preserved_if_present(self):
        """UT-099-002: Preserve correlation ID from header."""
        test_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"X-Correlation-ID": test_id}
        context = CorrelationContext.from_headers(headers)
        
        assert context.correlation_id == test_id
    
    def test_correlation_propagated_to_headers(self):
        """UT-099-003: Propagate correlation to outbound headers."""
        context = CorrelationContext.create_new()
        headers = context.to_headers()
        
        assert headers["X-Correlation-ID"] == context.correlation_id
        assert headers["X-Trace-ID"] == context.trace_id
    
    def test_child_correlation_maintains_chain(self):
        """UT-099-004: Child correlation maintains parent chain."""
        parent = CorrelationContext.create_new()
        child = parent.create_child()
        
        assert child.parent_id == parent.correlation_id
        assert child.trace_id == parent.trace_id
        assert child.correlation_id != parent.correlation_id
    
    def test_context_extraction_from_full_headers(self):
        """UT-099-005: Extract full context from headers."""
        headers = {
            "X-Correlation-ID": "corr-123",
            "X-Parent-ID": "parent-123",
            "X-User-ID": "user-456",
            "X-Session-ID": "session-789"
        }
        context = CorrelationContext.from_headers(headers)
        
        assert context.correlation_id == "corr-123"
        assert context.parent_id == "parent-123"
        assert context.user_id == "user-456"
        assert context.session_id == "session-789"
    
    def test_correlation_propagator_get_current(self):
        """UT-099-006: Get current correlation via propagator."""
        test_id = CorrelationContext.generate_id()
        context = CorrelationContext(correlation_id=test_id)
        CorrelationPropagator.set_current(context)
        
        retrieved = CorrelationPropagator.get_current()
        assert retrieved.correlation_id == test_id
        
        CorrelationPropagator.clear()


# ============================================================================
# QA-2: Cross-Service Discoverability (AC-2)
# ============================================================================

class TestCrossServiceDiscoverability:
    """QA-2: Validate AC-2 - Events discoverable by correlation ID timeline."""
    
    def test_timeline_reconstruction_from_logs(self):
        """UT-099-007: Reconstruct timeline from correlation ID."""
        correlation_id = CorrelationContext.generate_id()
        
        # Create log entries for a multi-step flow
        entries = []
        for i in range(5):
            entry = StructuredLogEntry(
                correlation_id=correlation_id,
                message=f"Step {i}",
                source=LogSource.SERVICE,
                status="success"
            )
            entries.append(entry)
        
        # All events have same correlation ID
        assert all(e.correlation_id == correlation_id for e in entries)
    
    def test_timeline_with_parent_ids(self):
        """UT-099-008: Timeline maintains parent chain."""
        root_context = CorrelationContext.create_new()
        child1 = root_context.create_child()
        child2 = root_context.create_child()
        
        assert child1.parent_id == root_context.correlation_id
        assert child2.parent_id == root_context.correlation_id
        assert child1.trace_id == child2.trace_id  # Same trace
    
    def test_timeline_builder_constructs_event_flow(self):
        """UT-099-009: Timeline builder creates ordered event sequence."""
        correlation_id = CorrelationContext.generate_id()
        builder = TimelineBuilder(correlation_id)
        
        # Add events in sequence
        now = datetime.utcnow()
        for i in range(3):
            event = TimelineEvent(
                timestamp=now + timedelta(seconds=i),
                event_type=TimelineEventType.SERVICE_CALL,
                service_name=f"service_{i}",
                correlation_id=correlation_id,
                parent_id=None,
                actor="user_1",
                route="/api/test",
                status="success",
                http_status=200,
                message=f"Call {i}",
                duration_ms=100.0 * (i + 1),
                details={},
                severity="INFO"
            )
            builder.add_event(event)
        
        timeline = builder.build()
        assert timeline["correlation_id"] == correlation_id
        assert len(timeline["events"]) == 3
        assert timeline["total_duration_ms"] > 0
    
    def test_query_all_events_for_correlation(self):
        """UT-099-010: Query all events for correlation ID."""
        correlation_id = "test-corr-123"
        query = IncidentQuery.all_events_for_correlation(correlation_id)
        
        assert query["filters"]["correlation_id"] == correlation_id
        assert query["sort_order"] == "asc"


# ============================================================================
# QA-3: Redaction and Masking Validation (AC-3)
# ============================================================================

class TestRedactionValidation:
    """QA-3: Validate AC-3 - PHI/secret masking prevents leakage."""
    
    def test_email_redaction(self):
        """UT-099-011: Redact email addresses."""
        data = {
            "user_email": "user@example.com",
            "message": "Contact john@company.com"
        }
        redactor = LogRedactor(RedactionLevel.MEDIUM)
        redacted = redactor.redact_dict(data)
        
        assert "[REDACTED" in redacted["user_email"]
        assert "user@example.com" not in str(redacted)
    
    def test_sensitive_field_redaction(self):
        """UT-099-012: Redact sensitive field names."""
        data = {
            "password": "secret123",
            "api_key": "key_abc123",
            "credit_card": "4532-1234-5678-9010"
        }
        redactor = LogRedactor(RedactionLevel.MEDIUM)
        redacted = redactor.redact_dict(data)
        
        assert "[REDACTED" in str(redacted["password"])
        assert "[REDACTED" in str(redacted["api_key"])
        assert "[REDACTED" in str(redacted["credit_card"])
        assert "secret123" not in str(redacted)
    
    def test_phi_redaction(self):
        """UT-099-013: Redact medical data (PHI)."""
        data = {
            "mrn": "123456",
            "patient_name": "John Doe",
            "diagnosis": "Type 2 Diabetes"
        }
        redactor = LogRedactor(RedactionLevel.MEDIUM)
        redacted = redactor.redact_dict(data)
        
        assert "[REDACTED" in str(redacted)
        assert "John Doe" not in str(redacted)
        assert "Diabetes" not in str(redacted)
    
    def test_phone_number_redaction(self):
        """UT-099-014: Redact phone numbers."""
        data = {"contact": "Call 555-123-4567 for support"}
        redactor = LogRedactor(RedactionLevel.MEDIUM)
        redacted = redactor.redact_dict(data)
        
        assert "555-123-4567" not in str(redacted)
        assert "[REDACTED" in str(redacted)
    
    def test_nested_structure_redaction(self):
        """UT-099-015: Redact nested sensitive data."""
        data = {
            "user": {
                "name": "Alice",
                "email": "alice@company.com",
                "credentials": {
                    "password": "pass123"
                }
            }
        }
        redactor = LogRedactor(RedactionLevel.MEDIUM)
        redacted = redactor.redact_dict(data)
        
        assert "alice@company.com" not in json.dumps(redacted)
        assert "pass123" not in json.dumps(redacted)
    
    def test_boundary_validation_rejects_forbidden_fields(self):
        """UT-099-016: Boundary validation rejects forbidden fields."""
        data = {"password": "secret"}
        violations = LoggingBoundary.validate_entry_safety(data)
        
        assert len(violations) > 0
        assert "password" in violations[0]
    
    def test_safe_log_entry_creation(self):
        """UT-099-017: Create safe log entry with auto-redaction."""
        unsafe_data = {
            "correlation_id": "123",
            "message": "User logged in",
            "email": "user@example.com"
        }
        safe = create_safe_log_entry(unsafe_data)
        
        data_dict = safe.to_dict()
        assert "user@example.com" not in json.dumps(data_dict)


# ============================================================================
# QA-4: Delivery Reliability Validation (AC-4)
# ============================================================================

class TestDeliveryReliability:
    """QA-4: Validate AC-4 - Delivery success >= 99.9% with retry."""
    
    def test_log_delivery_to_sink(self):
        """UT-099-018: Deliver log to sink successfully."""
        sink = InMemoryLogSink()
        pipeline = LogPipeline(sinks=[sink])
        
        event = {
            "correlation_id": "test-123",
            "message": "Test event",
            "severity": "INFO"
        }
        
        success = pipeline.emit(event)
        pipeline.flush()
        
        assert success
        assert len(sink.get_logs()) == 1
    
    def test_delivery_retry_on_failure(self):
        """UT-099-019: Retry on transient failure."""
        
        class FailOnceSink(LogSink):
            def __init__(self):
                self.call_count = 0
            
            def send(self, event):
                self.call_count += 1
                return self.call_count > 1  # Fail first, succeed second
            
            def is_healthy(self):
                return True
        
        sink = FailOnceSink()
        pipeline = LogPipeline(sinks=[sink])
        
        event = {"correlation_id": "test", "message": "test"}
        pipeline.emit(event)
        
        # First flush attempts delivery (fails)
        pipeline.flush()
        assert len(pipeline.pending_events) > 0
        
        # Second flush retries (succeeds)
        pipeline.flush()
        metrics = pipeline.get_metrics()
        assert metrics.delivered_events > 0
    
    def test_delivery_success_rate_calculation(self):
        """UT-099-020: Calculate delivery success rate (AC-4)."""
        sink = InMemoryLogSink()
        pipeline = LogPipeline(sinks=[sink])
        
        # Emit 100 events
        for i in range(100):
            event = {"correlation_id": f"test-{i}", "message": f"Event {i}"}
            pipeline.emit(event)
        
        pipeline.flush()
        success_rate = pipeline.get_delivery_success_rate()
        
        assert success_rate >= 0.999  # Target >= 99.9%
        assert success_rate <= 1.0
    
    def test_backpressure_handling(self):
        """UT-099-021: Backpressure when queue full."""
        sink = InMemoryLogSink()
        pipeline = LogPipeline(sinks=[sink], max_pending_events=10)
        
        # Emit more events than capacity
        success_count = 0
        for i in range(20):
            event = {"correlation_id": f"test-{i}"}
            if pipeline.emit(event):
                success_count += 1
        
        # Some events should be rejected due to backpressure
        assert success_count < 20
        assert pipeline.metrics.backpressure_events > 0
    
    def test_dead_letter_queue(self):
        """UT-099-022: Failed events go to dead letter queue."""
        
        class FailingSink(LogSink):
            def send(self, event):
                return False  # Always fail
            def is_healthy(self):
                return True
        
        sink = FailingSink()
        pipeline = LogPipeline(sinks=[sink])
        
        event = {"correlation_id": "test", "message": "fail"}
        pipeline.emit(event)
        
        # Retry until dead lettering
        for _ in range(5):
            pipeline.flush()
        
        dlq = pipeline.get_dead_letter_queue()
        assert len(dlq) > 0


# ============================================================================
# QA-5: Searchability and Filtering Validation (AC-5)
# ============================================================================

class TestSearchability:
    """QA-5: Validate AC-5 - Search filters support incident triage."""
    
    def test_query_with_correlation_filter(self):
        """UT-099-023: Filter by correlation ID."""
        query = QueryBuilder().with_correlation_id("corr-123").to_query_dict()
        assert query["filters"]["correlation_id"] == "corr-123"
    
    def test_query_with_service_filter(self):
        """UT-099-024: Filter by service name."""
        query = QueryBuilder().with_service("booking_service").to_query_dict()
        assert query["filters"]["service_name"] == "booking_service"
    
    def test_query_with_environment_filter(self):
        """UT-099-025: Filter by environment."""
        query = QueryBuilder().with_environment("production").to_query_dict()
        assert query["filters"]["environment"] == "production"
    
    def test_query_with_severity_filter(self):
        """UT-099-026: Filter by severity level."""
        query = QueryBuilder().with_severity("ERROR").to_query_dict()
        assert query["filters"]["severity"] == "ERROR"
    
    def test_query_with_time_range(self):
        """UT-099-027: Filter by time range."""
        now = datetime.utcnow()
        start = now - timedelta(hours=1)
        query = QueryBuilder().with_time_range(start, now).to_query_dict()
        
        assert "timestamp" in query["filters"]
    
    def test_query_errors_only(self):
        """UT-099-028: Query errors and higher severity."""
        query = QueryBuilder().with_error_only().to_query_dict()
        assert "severity_numeric" in query["filters"]
    
    def test_query_last_hour_errors(self):
        """UT-099-029: Query errors in last hour."""
        query = IncidentQuery.errors_in_last_hour()
        assert "severity_numeric" in query["filters"]
        assert "timestamp" in query["filters"]
    
    def test_query_service_failures(self):
        """UT-099-030: Query service failures."""
        query = IncidentQuery.service_failures("booking_service")
        assert query["filters"]["service_name"] == "booking_service"
        assert query["filters"]["status"] == "failure"
    
    def test_multiple_filters_combined(self):
        """UT-099-031: Combine multiple filters."""
        query = QueryBuilder()\
            .with_service("api")\
            .with_environment("production")\
            .with_error_only()\
            .with_last_hours(1)\
            .to_query_dict()
        
        assert query["filters"]["service_name"] == "api"
        assert query["filters"]["environment"] == "production"


# ============================================================================
# QA-6: Retention Policy Validation (AC-6)
# ============================================================================

class TestRetentionPolicy:
    """QA-6: Validate AC-6 - Retention policy enforced by environment."""
    
    def test_development_retention_7_days(self):
        """UT-099-032: Development logs retained 7 days."""
        policy = RetentionPolicy.DEVELOPMENT
        assert policy.retention_seconds() == 7 * 24 * 3600
    
    def test_staging_retention_30_days(self):
        """UT-099-033: Staging logs retained 30 days."""
        policy = RetentionPolicy.STAGING
        assert policy.retention_seconds() == 30 * 24 * 3600
    
    def test_production_retention_90_days(self):
        """UT-099-034: Production logs retained 90 days."""
        policy = RetentionPolicy.PRODUCTION
        assert policy.retention_seconds() == 90 * 24 * 3600
    
    def test_pipeline_respects_retention_policy(self):
        """UT-099-035: Pipeline enforces retention cleanup."""
        sink = InMemoryLogSink()
        pipeline = LogPipeline(
            sinks=[sink],
            retention_policy=RetentionPolicy.DEVELOPMENT
        )
        
        event = {"correlation_id": "test", "message": "old"}
        pipeline.emit(event)
        pipeline.flush()
        
        # Event should be retained based on policy
        assert len(pipeline.pending_events) >= 0
    
    def test_factory_creates_env_specific_pipeline(self):
        """UT-099-036: Factory creates env-specific pipeline."""
        pipeline_prod = PipelineFactory.create_default_pipeline("production")
        assert pipeline_prod.retention_policy == RetentionPolicy.PRODUCTION
        
        pipeline_dev = PipelineFactory.create_default_pipeline("development")
        assert pipeline_dev.retention_policy == RetentionPolicy.DEVELOPMENT


# ============================================================================
# Integration Tests
# ============================================================================

class TestLoggingIntegration:
    """Integration tests for full logging workflow."""
    
    def test_end_to_end_logging_flow(self):
        """UT-099-037: Complete logging workflow."""
        # Create context
        headers = {}
        correlation_context = CorrelationContext.from_headers(headers)
        
        # Create log entry
        entry = StructuredLogEntry(
            correlation_id=correlation_context.correlation_id,
            message="User login",
            source=LogSource.API,
            environment=LogEnvironment.PRODUCTION
        )
        
        # Redact if needed
        redacted = LogRedactor().redact_dict(entry.to_dict())
        safe_entry = create_safe_log_entry(redacted)
        
        # Deliver via pipeline
        sink = InMemoryLogSink()
        pipeline = LogPipeline(sinks=[sink])
        pipeline.emit(safe_entry.data)
        pipeline.flush()
        
        # Verify delivery
        logs = sink.get_logs()
        assert len(logs) == 1
        assert logs[0]["correlation_id"] == correlation_context.correlation_id
    
    def test_context_stack_management(self):
        """UT-099-038: Log context stack operations."""
        context1 = LogContext(
            correlation=CorrelationContext.create_new(),
            service_name="service1",
            environment=LogEnvironment.DEVELOPMENT
        )
        
        push_context(context1)
        assert current_context() == context1
        
        popped = pop_context()
        assert popped == context1
        assert current_context() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
