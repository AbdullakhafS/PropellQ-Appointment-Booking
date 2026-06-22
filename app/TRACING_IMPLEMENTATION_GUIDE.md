# TASK-100 Tracing & SLO Implementation Guide

**Version**: 1.0  
**Last Updated**: 2026-06-22  
**Status**: Complete & Production Ready

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Getting Started](#getting-started)
3. [Core Components](#core-components)
4. [Integration Patterns](#integration-patterns)
5. [SLO Management](#slo-management)
6. [Dashboard Setup](#dashboard-setup)
7. [Incident Investigation](#incident-investigation)
8. [Operations](#operations)
9. [FAQ](#faq)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Observability Platform                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────┐    ┌──────────────────────┐      │
│  │ Tracing Layer        │    │ Logging Layer (099)  │      │
│  │ - Spans              │◄──►│ - Correlation IDs    │      │
│  │ - Hierarchy          │    │ - Redaction          │      │
│  │ - W3C Context        │    │ - Structured Format  │      │
│  └──────────────────────┘    └──────────────────────┘      │
│           ▼                            ▼                    │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Correlation Registry (Link Layer)                │      │
│  │ - Trace ↔ Log Bidirectional Mapping             │      │
│  │ - Investigation Reports                         │      │
│  └──────────────────────────────────────────────────┘      │
│           ▼                                                 │
│  ┌──────────────────────┐    ┌──────────────────────┐      │
│  │ Metrics Collection   │    │ SLO Tracking        │      │
│  │ - Latency (p50/95/99)│    │ - Error Budget      │      │
│  │ - Errors             │    │ - Burn Rate         │      │
│  │ - Availability       │    │ - Compliance        │      │
│  └──────────────────────┘    └──────────────────────┘      │
│           ▼                            ▼                    │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Alerting Engine                                  │      │
│  │ - Multi-window Burn Rate Rules                  │      │
│  │ - Severity Escalation                          │      │
│  │ - Handler Routing (log, email, PagerDuty)      │      │
│  └──────────────────────────────────────────────────┘      │
│           ▼                                                 │
│  ┌──────────────────────┐    ┌──────────────────────┐      │
│  │ Operational Dashboard│    │ Reliability Reports │      │
│  │ - Uptime Gauge       │    │ - Weekly SLO Export │      │
│  │ - Latency Graphs     │    │ - Error Budget      │      │
│  │ - Error Rate         │    │ - Incident Summary  │      │
│  │ - Top Endpoints      │    │ - Top Errors        │      │
│  └──────────────────────┘    └──────────────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
HTTP Request
    ↓
[1. Extract/Create Trace Context]
    - W3C Trace Context from header
    - Generate trace_id if missing
    - Generate span_id for this request
    ↓
[2. Record Span]
    - Operation name (e.g., "handle_booking_request")
    - Attributes (method, URL, user_id)
    - Service name
    ↓
[3. Child Spans]
    - DB queries: start_span("query_appointments")
    - External calls: start_span("call_payment_service")
    - Cache ops: start_span("check_cache")
    ↓
[4. Calculate Metrics]
    - Latency per span
    - Success/failure status
    - Error details
    ↓
[5. Link Trace to Logs]
    - Correlation ID = trace_id (or custom UUID)
    - All logs in request carry correlation_id
    - Enable trace ↔ log navigation
    ↓
[6. Evaluate SLOs]
    - Aggregate metrics across spans
    - Calculate error budget consumption
    - Check burn rate thresholds
    ↓
[7. Alert if Needed]
    - Multi-window burn rate check
    - Severity determination
    - Handler dispatch (log, email, PagerDuty)
    ↓
[8. Dashboard Update]
    - Refresh uptime gauge
    - Update latency percentiles
    - Recalculate top failing endpoints
    ↓
[9. Weekly Report]
    - Aggregate SLO compliance
    - Export HTML report
    - Email to stakeholders
```

---

## Getting Started

### 1. Basic Installation

```bash
# Install dependencies (already included in PropellQ environment)
pip install pytest dataclasses enum typing

# No external SDK required - pure Python implementation
```

### 2. Minimal Setup

```python
from src.tracing_instrumentation import Tracer, TracingMiddleware, SpanKind
from src.metrics_slo import MetricsCollector, SLOTarget
from src.alerting_engine import AlertingEngine, create_standard_burn_rate_alerts

# 1. Create tracer
tracer = Tracer("my_service")

# 2. Create metrics collector
collector = MetricsCollector()

# 3. Setup alerting
alerting_engine = AlertingEngine()
alerting_engine.register_rule(
    create_standard_burn_rate_alerts("booking_slo")
)

# 4. Register log handler
alerting_engine.register_handler(
    lambda alert: print(f"🚨 Alert: {alert.message}")
)

# 5. Instrument WSGI app
app = TracingMiddleware(original_app, tracer)
```

### 3. Record Your First Span

```python
def handle_booking_request(booking_data):
    # Start span
    span = tracer.start_span(
        "handle_booking_request",
        kind=SpanKind.SERVER,
        attributes={
            "http.method": "POST",
            "http.url": "/api/appointments/book",
            "user.id": booking_data["user_id"]
        }
    )
    
    try:
        # Your business logic
        result = process_booking(booking_data)
        
        # End span successfully
        tracer.end_span(span)
        
        # Record metrics
        collector.record_request(
            latency_ms=span.duration_ms(),
            success=True,
            service="booking",
            endpoint="/api/appointments/book"
        )
        
        return result
    except Exception as e:
        # Record exception
        span.record_exception(e)
        span.set_status(SpanStatus.ERROR)
        tracer.end_span(span)
        
        # Record failed metric
        collector.record_request(
            latency_ms=span.duration_ms(),
            success=False,
            service="booking",
            endpoint="/api/appointments/book"
        )
        
        raise
```

---

## Core Components

### 1. Tracing Instrumentation

#### SpanContext (W3C Trace Context)

```python
from src.tracing_instrumentation import SpanContext, SpanKind

# Create root span context
context = SpanContext.create_root()
# Fields:
#   trace_id: "4bf92f3577b34da6a3ce929d0e0e4736" (32 hex chars)
#   span_id: "00f067aa0ba902b7" (16 hex chars)
#   parent_span_id: None
#   trace_flags: 0x01 (sampled)

# Create child context
child = context.create_child()
# Automatically:
#   trace_id: same as parent
#   span_id: new ID
#   parent_span_id: parent.span_id

# Propagate via W3C header
traceparent = context.to_traceparent_header()
# "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

# Extract from header
context = SpanContext.from_traceparent_header(header_value)
```

#### Span

```python
from src.tracing_instrumentation import Span, SpanStatus, SpanKind

span = Span(
    trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
    span_id="00f067aa0ba902b7",
    operation_name="query_database",
    kind=SpanKind.CLIENT  # DB query
)

# Set attributes
span.set_attribute("db.system", "postgresql")
span.set_attribute("db.statement", "SELECT * FROM appointments")
span.set_attribute("db.rows_affected", 42)

# Add event
span.add_event("slow_query_detected", {
    "query_duration_ms": 2500
})

# Record exception
try:
    execute_query()
except Exception as e:
    span.record_exception(e)
    span.set_status(SpanStatus.ERROR)

# Calculate latency
span.end()
duration_ms = span.duration_ms()  # milliseconds
```

#### Tracer

```python
from src.tracing_instrumentation import Tracer, TraceContext

tracer = Tracer(service_name="booking_service")

# Start root span
root = tracer.start_span("handle_request", kind=SpanKind.SERVER)

# Create child spans
child1 = tracer.start_span("validate_input")
tracer.end_span(child1)

child2 = tracer.start_span("query_availability")
tracer.end_span(child2)

# End root span
tracer.end_span(root)

# Export trace with critical path
export = tracer.export_trace()
# {
#   "trace_id": "...",
#   "spans": [...],
#   "total_duration_ms": 245.3,
#   "critical_path": [
#       {"operation": "query_availability", "duration_ms": 150},
#       {"operation": "handle_request", "duration_ms": 245.3}
#   ]
# }
```

### 2. Metrics & SLO

#### MetricsCollector

```python
from src.metrics_slo import MetricsCollector

collector = MetricsCollector()

# Record latency + success
collector.record_request(
    latency_ms=145.3,
    success=True,
    service="booking",
    endpoint="/api/appointments/book",
    operation="create_appointment"  # Optional, for fine-grained metrics
)

# Get snapshot of all metrics
snapshot = collector.get_metrics_snapshot()
# Returns dict with keys like:
# {
#   "booking|/api/appointments/book": GoldenSignal(...),
#   "booking|/api/appointments/search": GoldenSignal(...)
# }

# Get metrics for specific endpoint
metrics = collector.get_endpoint_metrics("/api/appointments/book", "booking")
# {
#   "latency_p50": 120.5,
#   "latency_p95": 450.2,
#   "latency_p99": 1200.0,
#   "error_rate": 0.02,
#   "request_count": 10000
# }

# Find top failing endpoints
top_failures = collector.get_top_failing_endpoints("booking", limit=10)
# Returns: [(endpoint, error_rate), ...]
```

#### SLOTarget

```python
from src.metrics_slo import SLOTarget

# Define SLO
booking_slo = SLOTarget(
    name="booking_availability",
    description="Booking service availability target",
    metric_type="availability",  # Or "latency"
    target_value=0.999,  # 99.9% uptime = 0.1% error rate
    window_seconds=30 * 24 * 3600  # 30-day window
)

# Calculate burn rate
# Allowed error budget: 0.1% × 2,592,000 seconds = 2,592 seconds/month
errors_in_window = 26  # 26 requests failed
total_requests = 10000

burn_rate = booking_slo.burn_rate(errors_in_window, total_requests)
# burn_rate ≈ 1.0 (at target, consuming budget at normal rate)
# burn_rate ≈ 2.0 (at 2x rate, consuming budget twice as fast)
# burn_rate ≈ 10.0 (critical degradation)

# Calculate remaining error budget
error_budget = booking_slo.error_budget_seconds(30)
# Returns seconds remaining
```

### 3. Alerting Engine

#### BurnRateAlertRule

```python
from src.alerting_engine import (
    BurnRateAlertRule, BurnRateWindow, 
    AlertSeverity, create_standard_burn_rate_alerts
)

# Use standard Google SRE windows
rule = create_standard_burn_rate_alerts("booking_slo")
# Configures:
# - 2.0x threshold over 1 hour → WARNING
# - 5.0x threshold over 30 minutes → WARNING
# - 10.0x threshold over 5 minutes → CRITICAL

# Or create custom
windows = [
    BurnRateWindow("slow", 3600, 1.5, AlertSeverity.WARNING),
    BurnRateWindow("fast", 300, 8.0, AlertSeverity.CRITICAL),
]
custom_rule = BurnRateAlertRule("custom_slo", windows)

# Evaluate compliance
compliance = {
    "burn_rate": 5.5,
    "target": 0.999,
    "actual": 0.996
}

alert = rule.evaluate(compliance)
# Returns Alert with:
# - status: AlertStatus.FIRING (or RESOLVED)
# - severity: AlertSeverity.WARNING (or CRITICAL)
# - message: Human-readable alert text
```

#### AlertingEngine

```python
from src.alerting_engine import AlertingEngine, AlertStatus

engine = AlertingEngine()

# Register rules
engine.register_rule(create_standard_burn_rate_alerts("booking_slo"))
engine.register_rule(create_standard_burn_rate_alerts("payment_slo"))

# Register handlers (handlers are called when alerts fire)
def log_handler(alert):
    if alert.status == AlertStatus.FIRING:
        print(f"🚨 ALERT: {alert.message}")
    else:
        print(f"✅ RESOLVED: {alert.message}")

engine.register_handler(log_handler)

# Evaluate all rules
slo_compliances = {
    "booking_slo": {"burn_rate": 5.0, "target": 0.999, "actual": 0.997},
    "payment_slo": {"burn_rate": 0.5, "target": 0.9999, "actual": 0.9999}
}

alerts = engine.evaluate_all(slo_compliances)
# Handlers are called for each alert
# Returns list of Alert objects
```

### 4. Dashboards & Reporting

#### OperationalDashboard

```python
from src.observability_dashboard import OperationalDashboard
import json

dashboard = OperationalDashboard()

# Dashboard has 6 panels:
# 1. Platform Uptime (30-day gauge)
# 2. API p95 Latency (5-minute graph)
# 3. Error Rate Trend (1-hour graph)
# 4. Top Failing Endpoints (table)
# 5. Request Volume (RPS)
# 6. Service Health (status)

# Export to JSON for visualization tool
json_str = dashboard.to_json()
config = json.loads(json_str)
# {
#   "dashboard": {
#     "name": "Operational Dashboard",
#     "description": "..."
#   },
#   "panels": [
#     {"title": "Platform Uptime", "type": "gauge", ...},
#     {"title": "API p95 Latency", "type": "graph", ...},
#     ...
#   ]
# }

# Use config to provision in Grafana, Datadog, etc.
```

#### ReliabilityReport

```python
from src.observability_dashboard import (
    ReliabilityReport, SLOReportEntry, ReportGenerator
)
from datetime import datetime, timedelta

# Create report for week
report = ReliabilityReport(
    report_date=datetime.utcnow(),
    report_period_start=datetime.utcnow() - timedelta(days=7),
    report_period_end=datetime.utcnow()
)

# Add SLO entries
report.add_slo_entry(SLOReportEntry(
    slo_name="booking_availability",
    target=0.999,
    actual=0.9985,
    compliant=True,
    error_budget_seconds=2592,  # ≈43 minutes
    error_budget_percent=5.0,
    window_days=30
))

report.add_slo_entry(SLOReportEntry(
    slo_name="payment_availability",
    target=0.9999,
    actual=0.9998,
    compliant=False,
    error_budget_seconds=10,
    error_budget_percent=0.1,
    window_days=30
))

# Calculate summary
report.calculate_summary()
# summary: {
#   "total_slos": 2,
#   "slos_met": 1,
#   "overall_slo_percent": 50.0,
#   "total_incidents": 2,
#   "critical_incidents": 0
# }

# Export formats
json_output = report.to_json()      # For programmatic use
html_output = report.to_html()      # For email

# Send HTML report
import smtplib
msg = create_email_message(html_output)
smtplib.SMTP(...).send_message(msg)
```

### 5. Trace-Log Correlation

#### TraceLinkRegistry

```python
from src.tracing_correlation import TraceLinkRegistry

registry = TraceLinkRegistry()

# Register traces by correlation ID
registry.register_trace("trace-123", "corr-456")

# Register logs by correlation ID
log_entry = {
    "timestamp": "2026-06-22T10:30:00Z",
    "level": "ERROR",
    "message": "Database connection timeout",
    "service": "booking"
}
registry.register_log("corr-456", log_entry)

# Query mappings
traces_for_corr = registry.get_traces_for_correlation("corr-456")
# Returns: ["trace-123"]

logs_for_trace = registry.get_logs_for_trace("trace-123")
# Returns: [log_entry]
```

#### TraceLogNavigator

```python
from src.tracing_correlation import TraceLogNavigator

navigator = TraceLogNavigator(registry)

# Investigate incident by correlation ID
investigation = navigator.create_investigation_report("corr-456")
# Returns: {
#   "correlation_id": "corr-456",
#   "incident_summary": {
#     "trace_count": 1,
#     "log_count": 3,
#     "error_count": 1,
#     "critical_events": [...]
#   },
#   "errors": [...],
#   "investigation_checkpoints": [
#     "1. Check trace details for corr-456",
#     "2. Review logs ordered by severity",
#     "3. Identify critical events",
#     "4. Validate error recovery"
#   ]
# }
```

---

## Integration Patterns

### Pattern 1: WSGI Middleware Integration

```python
from src.tracing_instrumentation import Tracer, TracingMiddleware

tracer = Tracer("my_app")
app = TracingMiddleware(original_app, tracer)

# TracingMiddleware automatically:
# 1. Extracts W3C traceparent header from request
# 2. Creates root span for request
# 3. Sets span attributes (method, URL, headers)
# 4. Calls wrapped app
# 5. Records response status
# 6. Propagates trace to downstream services
```

### Pattern 2: Cross-Service Tracing

```python
# Service A
def call_service_b():
    span = tracer.start_span("call_service_b", kind=SpanKind.CLIENT)
    
    # Get current trace context
    from src.tracing_instrumentation import TraceContext
    context = TraceContext.current()
    
    # Create W3C traceparent header
    headers = context.to_headers()
    # {"traceparent": "00-...-...-01", "X-Correlation-ID": "..."}
    
    # Call Service B with trace context
    response = requests.post(
        "http://service-b:8002/api/endpoint",
        headers=headers,
        json=payload
    )
    
    span.set_attribute("http.status_code", response.status_code)
    tracer.end_span(span)

# Service B automatically continues trace
# (via TracingMiddleware extracting header)
```

### Pattern 3: Database Call Instrumentation

```python
def query_database(query_sql):
    span = tracer.start_span("db_query", kind=SpanKind.CLIENT)
    span.set_attribute("db.system", "postgresql")
    span.set_attribute("db.statement", query_sql)
    
    try:
        rows = db.execute(query_sql)
        span.set_attribute("db.rows_affected", len(rows))
        tracer.end_span(span)
        return rows
    except Exception as e:
        span.record_exception(e)
        tracer.end_span(span)
        raise
```

### Pattern 4: Cache Instrumentation

```python
def get_cached_value(key):
    span = tracer.start_span("cache_lookup", kind=SpanKind.CLIENT)
    span.set_attribute("cache.key", key)
    
    value = cache.get(key)
    
    if value is None:
        span.set_attribute("cache.hit", False)
        # Cache miss - fetch from source
        value = fetch_from_source(key)
        cache.set(key, value)
    else:
        span.set_attribute("cache.hit", True)
    
    tracer.end_span(span)
    return value
```

---

## SLO Management

### Defining SLOs

```python
from src.metrics_slo import SLOTarget

# Booking service availability SLO
booking_slo = SLOTarget(
    name="booking_availability",
    description="Booking API 99.9% uptime",
    metric_type="availability",
    target_value=0.999,  # 99.9%
    window_seconds=30 * 24 * 3600  # 30 days
)

# Payment service latency SLO
payment_latency_slo = SLOTarget(
    name="payment_latency",
    description="Payment API p95 latency < 500ms",
    metric_type="latency",
    target_value=0.95,  # 95% of requests < 500ms
    window_seconds=7 * 24 * 3600  # 7 days
)
```

### Error Budget Calculation

```
Monthly Error Budget for 99.9% uptime SLO:
  Total seconds per month: 30 × 24 × 3600 = 2,592,000 seconds
  Allowed error: (1 - 0.999) × 2,592,000 = 2,592 seconds
  Percentage: 0.1% of month

During a 30-day window:
  - Consuming budget at normal rate: ~86 seconds/day
  - At 2x burn rate (WARNING): ~172 seconds/day
  - At 10x burn rate (CRITICAL): ~860 seconds/day
```

### Burn Rate Windows

Google SRE recommends multi-window alerting to avoid false positives:

| Window | Duration | Burn Rate | Severity | Meaning |
|--------|----------|-----------|----------|---------|
| Slow | 1 hour | 2.0x | WARNING | Sustained degradation over an hour |
| Medium | 30 min | 5.0x | WARNING | Sustained degradation over 30 min |
| Fast | 5 min | 10.0x | CRITICAL | Rapid degradation - immediate action |

```python
from src.alerting_engine import create_standard_burn_rate_alerts

# Automatically configured with above windows
rule = create_standard_burn_rate_alerts("booking_slo")
```

---

## Dashboard Setup

### Operational Dashboard (SRE View)

For operations and on-call engineers:

```python
from src.observability_dashboard import OperationalDashboard

dashboard = OperationalDashboard()

# Panels:
# 1. Platform Uptime (30-day gauge)
#    - Shows 99.85% uptime with green/yellow/red zones
#    - Below 99.9% triggers investigation
# 
# 2. API p95 Latency (5-minute graph)
#    - Y-axis: milliseconds
#    - Shows SLO target line
#    - Color-coded: green (<SLO), yellow (0.9-1.0x), red (>SLO)
#
# 3. Error Rate Trend (1-hour graph)
#    - Y-axis: percentage
#    - Shows current, 1h avg, 24h avg
#    - Highlights incidents
#
# 4. Top Failing Endpoints (table)
#    - Endpoint | Error Rate | Request Count
#    - Sorted by error rate descending
#    - Top 10 shown
#
# 5. Request Volume (RPS graph)
#    - Shows traffic patterns
#    - Helps correlate incidents with load
#
# 6. Service Health (status board)
#    - Per-service status: OK, DEGRADED, DOWN
#    - Last check timestamp
#    - Link to traces
```

### Consumer Dashboard (Leadership View)

For product/business stakeholders:

```python
from src.observability_dashboard import ConsumerDashboard

dashboard = ConsumerDashboard()

# Simplified panels:
# 1. Overall Platform Health
#    - Simple score: 100% OK, 95% DEGRADED, 0% DOWN
#    - Human-readable: "Service is operating normally"
#
# 2. SLO Attainment (monthly)
#    - Booking SLO: 99.87% (target 99.9%) ⚠️
#    - Payment SLO: 99.98% (target 99.99%) ✅
#    - Display as percentage bars
#
# 3. Error Budget Consumed
#    - Monthly error budget: 2,592 seconds
#    - Used so far: 1,200 seconds (46%)
#    - Remaining: 1,392 seconds (54%)
#    - Display as horizontal bar
#
# 4. Recent Incidents
#    - Date | Duration | Impact | Status
#    - Last 30 days
#    - Most recent first
```

---

## Incident Investigation

### Quick Investigation Workflow

```python
from src.tracing_correlation import TraceLogNavigator

# Step 1: Customer reports issue at 10:30am with correlation ID in error response
correlation_id = "corr-abc123xyz"

# Step 2: Create investigation report
investigation = navigator.create_investigation_report(correlation_id)

# Step 3: Review incident summary
print(f"Correlation ID: {investigation['correlation_id']}")
print(f"Traces involved: {investigation['incident_summary']['trace_count']}")
print(f"Logs collected: {investigation['incident_summary']['log_count']}")
print(f"Errors found: {investigation['incident_summary']['error_count']}")

# Step 4: Follow investigation checkpoints
for checkpoint in investigation['investigation_checkpoints']:
    print(f"→ {checkpoint}")

# Step 5: Review critical events
for event in investigation['incident_summary']['critical_events']:
    print(f"[{event['timestamp']}] {event['message']}")

# Step 6: Review errors
for error in investigation['errors']:
    print(f"Error: {error['message']}")
    print(f"  Stack Trace: {error.get('stack_trace', 'N/A')}")
```

### Common Investigation Scenarios

#### Scenario 1: High Latency

```python
# Investigation steps
investigation = navigator.create_investigation_report("corr-xyz")

# Look for traces showing critical path
critical_path = investigation['traces'][0]['critical_path']
for operation in critical_path:
    if operation['duration_ms'] > 1000:  # >1 second
        print(f"Slow operation: {operation['operation']} ({operation['duration_ms']}ms)")

# Check logs for database queries
for log in investigation['logs']:
    if "db" in log['service'].lower():
        print(f"DB log: {log['message']}")
```

#### Scenario 2: Errors

```python
# Filter logs by severity
critical_logs = [l for l in investigation['logs'] if l['level'] == 'ERROR']

# Check traces for exceptions
for trace in investigation['traces']:
    if 'exceptions' in trace:
        for exc in trace['exceptions']:
            print(f"Exception: {exc['type']}: {exc['message']}")

# Follow correlation chain to root cause
print(f"Trace-to-Logs: {len(investigation['traces'])} traces, {len(investigation['logs'])} logs")
```

#### Scenario 3: Cross-Service Failure

```python
# Multiple traces indicate multi-service issue
trace_count = investigation['incident_summary']['trace_count']

if trace_count > 1:
    print("Multi-service incident detected")
    
    for trace in investigation['traces']:
        print(f"Service: {trace['service']}")
        print(f"  Status: {trace['status']}")
        print(f"  Duration: {trace['total_duration_ms']}ms")
        
        # Look for service-to-service calls
        for span in trace['spans']:
            if span['kind'] == 'CLIENT':
                print(f"  → Call to: {span.get('target_service', 'unknown')}")
```

---

## Operations

### Daily Operations

#### Morning Checklist

```bash
# 1. Check overnight alerts (if any)
curl http://observability-api:8080/alerts?status=FIRING

# 2. Review SLO attainment
curl http://observability-api:8080/slo/status

# 3. Check top failing endpoints
curl http://observability-api:8080/metrics/top_failing_endpoints

# 4. Verify alert rules are active
curl http://observability-api:8080/alerting/rules
```

#### Weekly Review

```bash
# 1. Generate weekly report
report = ReportGenerator.generate_weekly_report(
    slo_data=get_slo_compliance("last_7_days"),
    incidents=get_incidents("last_7_days"),
    endpoints=get_top_endpoints("last_7_days", limit=10)
)

# 2. Send to stakeholders
send_email(
    to="leadership@propellq.com",
    subject="Weekly Reliability Report",
    html=report.to_html()
)

# 3. File in knowledge base
store_report_archive(report, "2026-06-22")
```

#### Monthly Operations

```bash
# 1. Review SLO targets - are they still appropriate?
# 2. Analyze burn rate patterns - which services trending bad?
# 3. Evaluate alert rules - too many false positives?
# 4. Plan capacity - any scaling needed?
# 5. Review dashboard - still showing right metrics?
```

### Troubleshooting

#### Issue: Missing Traces

```python
# Check TraceContext
from src.tracing_instrumentation import TraceContext
context = TraceContext.current()

if context is None:
    print("ERROR: No active trace context")
    # Solution: Ensure TracingMiddleware is enabled
    # or TraceContext.push() was called
else:
    print(f"Active trace: {context.trace_id}")

# Check span export
export = tracer.export_trace()
if not export['spans']:
    print("ERROR: No spans recorded")
    # Solution: Ensure start_span/end_span called
```

#### Issue: Metrics Not Updating

```python
# Check MetricsCollector
snapshot = collector.get_metrics_snapshot()

if not snapshot:
    print("ERROR: No metrics recorded")
    # Solutions:
    # 1. Ensure record_request() called
    # 2. Check buffer size isn't exceeded
    # 3. Verify collector instance is same used throughout

# Check metric values
metrics = collector.get_endpoint_metrics("/api/book", "booking")
if metrics.latency_p95 is None:
    print("ERROR: Not enough samples for percentile")
    # Need at least 100 samples for p95
```

#### Issue: Alerts Not Firing

```python
# Check rule registration
rules = alerting_engine.rules
if not rules:
    print("ERROR: No rules registered")
    # Solution: Call register_rule()

# Check compliance data
for rule_name, rule in rules.items():
    alert = rule.evaluate(compliance_data)
    if alert.status == AlertStatus.FIRING:
        print(f"Rule {rule_name} would fire")
    else:
        print(f"Rule {rule_name} not triggering (compliance OK)")
```

---

## FAQ

### Q: What's the difference between a Span and a Log?

**Spans** (Tracing):
- Represent operations/functions
- Show hierarchy and critical path
- Measure latency
- Track success/failure at operation level
- Example: "query_appointments" took 150ms

**Logs** (Logging):
- Detailed messages about what happened
- Show state changes and errors
- Queryable by timestamp/service/level
- Can include debugging info
- Example: "Database connection timeout after 3 retries"

**Use Together**: Span shows "what operation", Log shows "why it succeeded/failed"

---

### Q: How do I reduce alert fatigue?

Multi-window burn-rate alerting helps:

1. **Slow Window (2.0x/1hr)**: Catches sustained degradation, ignores blips
2. **Medium Window (5.0x/30min)**: Indicates real problem, not just variance
3. **Fast Window (10.0x/5min)**: Only for severe incidents

Tuning:
- Increase thresholds for less critical services
- Increase window duration for stable services
- Add snooze capabilities to handlers

---

### Q: What SLO target should we use?

Guidelines:

| Service Type | Target | Error Budget |
|--------------|--------|--------------|
| Best-effort | 99% | ~7 hours/month |
| Production | 99.5% | ~3.6 hours/month |
| Critical | 99.9% | ~43 min/month |
| Mission-critical | 99.99% | ~4.3 min/month |

Start conservative (99%), increase only if you consistently meet target.

---

### Q: How do I handle SLO violations?

When burn rate alert fires:

1. **First 5 minutes**: Investigate (traces/logs via correlation ID)
2. **5-15 minutes**: Implement quick fix or rollback
3. **15-30 minutes**: If not resolved, page on-call for deep investigation
4. **Post-incident**: Document root cause, update runbooks

---

### Q: Can I use this for custom metrics?

Yes! MetricsCollector is extensible:

```python
# Record custom metric
collector.record_request(
    latency_ms=245,
    success=True,
    service="booking",
    endpoint="/api/custom",
    operation="complex_calculation",  # Custom dimension
    # Add custom attributes to Span
)
```

---

### Q: How do I export to external tools?

```python
# Export traces to external tracing system
export = tracer.export_trace()
send_to_jaeger(export)  # or Zipkin, DataDog, etc.

# Export metrics to monitoring system
snapshot = collector.get_metrics_snapshot()
send_to_prometheus(snapshot)

# Export dashboards
dashboard_json = dashboard.to_json()
provision_grafana(dashboard_json)

# Export reports
report_html = report.to_html()
send_to_email(report_html)
```

---

**For more information, see**:
- [TRACING_QUICK_REFERENCE.md](./TRACING_QUICK_REFERENCE.md) - Quick start
- [TASK-099 LOGGING_IMPLEMENTATION_GUIDE.md](../us_099/LOGGING_IMPLEMENTATION_GUIDE.md) - Related logging infrastructure

---

**Status**: Production Ready ✅  
**Last Updated**: 2026-06-22  
**Questions?** See FAQ above or file a ticket in .propel/issues
