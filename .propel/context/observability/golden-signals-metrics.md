# METRIC-1: Golden Signal Metrics

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Audience:** Backend engineers, SRE, platform teams

---

## 1. Overview

This document defines the "golden signals" — the four key metrics that indicate service health: latency, traffic, errors, and saturation. These metrics form the basis for SLO definitions, alerting, and incident response.

**Objectives:**
- Define standardized metrics across all services
- Extract metrics from traces and logs
- Establish measurement methodology
- Enable consistent SLO/alerting definitions

---

## 2. Golden Signals Framework

### 2.1 The Four Golden Signals

| Signal | Metric | Measurement | Importance |
|---|---|---|---|
| **Latency** | p50, p95, p99 response time | Per-endpoint | User experience |
| **Traffic** | Requests per second (RPS) | Per-service, per-endpoint | Workload |
| **Errors** | Error rate (% of requests) | Per-service, per-endpoint | Reliability |
| **Saturation** | Resource utilization | CPU, Memory, Disk, DB connections | Capacity |

### 2.2 Metric Hierarchy

```
Service-Level Metrics
├─ Appointment Service Metrics
│  ├─ POST /api/v1/appointments
│  │  ├─ latency_p95_ms
│  │  ├─ error_rate_percent
│  │  └─ request_count
│  └─ GET /api/v1/appointments
│     ├─ latency_p95_ms
│     ├─ error_rate_percent
│     └─ request_count
├─ Database Metrics
│  ├─ appointments_table_query_latency_p95
│  ├─ connection_pool_utilization
│  └─ query_error_rate
└─ Infrastructure Metrics
   ├─ cpu_usage_percent
   ├─ memory_usage_percent
   └─ disk_usage_percent
```

---

## 3. Latency Metrics

### 3.1 Latency Definition and Measurement

**Definition:** Time from request entry to response exit (end-to-end)

**Percentiles tracked:**
- **p50 (median):** 50% of requests faster than this
- **p95:** 95% of requests faster than this (SLO target)
- **p99:** 99% of requests faster than this (worst-case)

**Collection:**
```
Extract from trace span:
start_time = 2026-06-22T10:00:00.000Z
end_time = 2026-06-22T10:00:00.145Z
latency_ms = (end_time - start_time) * 1000 = 145 ms

Aggregate across trace backend (Prometheus, Datadog):
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### 3.2 Latency Targets by Endpoint

| Endpoint | p95 Target | p99 Target | Rationale |
|---|---|---|---|
| `POST /api/v1/appointments` | 200ms | 500ms | Create operations slower |
| `GET /api/v1/appointments` | 100ms | 250ms | List operations faster |
| `GET /api/v1/appointments/{id}` | 150ms | 350ms | Single record fetch |
| `PATCH /api/v1/appointments/{id}/confirm` | 100ms | 250ms | State updates fast |
| `DELETE /api/v1/appointments/{id}` | 100ms | 250ms | Delete operations fast |

### 3.3 Component Latency Breakdown

For slow endpoints (> target), identify bottleneck:

```
POST /api/v1/appointments (target 200ms, actual p95 = 250ms)
├─ HTTP Handler: 5ms
├─ Validation: 10ms
├─ Authentication: 15ms
├─ Database Query: 180ms  ← BOTTLENECK
├─ Event Publish: 20ms
└─ Serialization: 5ms
Total: 235ms

Optimization: Add database index on eligibility column
```

**Trace Query in Datadog:**
```
@_trace.span_name:"POST /api/v1/appointments"
  | stats avg(duration) as avg_latency, 
          pct(duration, 95) as p95_latency, 
          pct(duration, 99) as p99_latency
  by service.name
```

---

## 4. Traffic Metrics

### 4.1 Request Rate (RPS)

**Definition:** Number of requests per second

**Measurement:**
```
Prometheus Query:
rate(http_requests_total[5m])

Datadog Query:
stats count as request_count by service.name, @_trace.span_name
```

### 4.2 Traffic by Endpoint

```
Appointment Service (total RPS: ~500):
├─ POST /api/v1/appointments: 50 RPS (10%)
├─ GET /api/v1/appointments: 300 RPS (60%)
├─ GET /api/v1/appointments/{id}: 100 RPS (20%)
├─ PATCH /api/v1/appointments/{id}/confirm: 40 RPS (8%)
└─ DELETE /api/v1/appointments/{id}: 10 RPS (2%)
```

### 4.3 Traffic Forecasting

Monitor traffic trends to predict capacity needs:

| Period | Peak RPS | Trend | Action |
|---|---|---|---|
| Week 1-2 | 100 | Stable | Baseline |
| Week 3-4 | 150 | +50% | Monitor |
| Week 5-6 | 250 | +67% | Plan scaling |
| Week 7-8 | 400 | +60% | Scale database |

---

## 5. Error Rate Metrics

### 5.1 Error Rate Definition

**Definition:** Percentage of requests that result in errors (5xx status code)

**Formula:**
```
error_rate = (requests_with_5xx_status / total_requests) * 100

Example:
total_requests = 10,000
requests_with_5xx = 50
error_rate = (50 / 10,000) * 100 = 0.5%
```

### 5.2 Error Rate by Type

Track errors by category:

```
Appointment Service Error Breakdown:
├─ 400 Bad Request: 2% (validation errors)
├─ 401 Unauthorized: 0.1% (auth failures)
├─ 403 Forbidden: 0.05% (authorization)
├─ 404 Not Found: 0.2% (missing resources)
├─ 500 Internal Server Error: 0.4%
│  ├─ Database Errors: 0.2%
│  ├─ Service Timeouts: 0.15%
│  └─ Unhandled Exceptions: 0.05%
└─ 503 Service Unavailable: 0.1%
```

### 5.3 Error Rate Tracking Queries

**Prometheus:**
```
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

**Datadog:**
```
@http.status_code:[500 TO 599] 
| stats count as errors, 
        count as total_requests by service.name
| stats eval("100 * errors / total_requests") as error_rate_pct
```

### 5.4 Error Rate Targets by Service

| Service | Target Error Rate | Threshold |
|---|---|---|
| API Gateway | < 0.1% | Alert if > 0.2% |
| Appointment Service | < 0.5% | Alert if > 0.75% |
| Clinical Data Service | < 0.3% | Alert if > 0.5% |
| Notification Service | < 1.0% | Alert if > 1.5% |
| Database | < 0.05% | Alert if > 0.1% |

---

## 6. Saturation Metrics

### 6.1 Resource Utilization

**Definition:** Percentage of resource consumed (CPU, Memory, Disk, Connections)

| Resource | Warning | Critical | Action |
|---|---|---|---|
| CPU | 70% | 85% | Scale horizontally |
| Memory | 75% | 90% | Increase instance size |
| Disk | 80% | 90% | Archive old logs |
| DB Connections | 75% | 90% | Increase pool size |

### 6.2 Database Connection Pool Saturation

```
Database Metrics:
├─ Pool Size: 20 connections
├─ In Use: 18 connections (90% saturation)
├─ Waiting Requests: 5 (backlog)
├─ Average Wait Time: 50ms
└─ Alert: Critical if > 95% for > 5min
```

**Datadog Query:**
```
@db.client.connections.usage / @db.client.connections.pool_size * 100
```

### 6.3 Query Performance Saturation

Track slow query rate:

```
Slow Queries (> 100ms):
├─ Total Queries: 10,000 per minute
├─ Slow Queries: 250 per minute (2.5%)
├─ Average Slow Query Duration: 250ms
└─ Alert: If slow query rate > 5%
```

---

## 7. Composite Metrics (Derived)

### 7.1 Success Rate

```
success_rate = (total_requests - error_requests) / total_requests * 100

= 1 - error_rate

Target: 99.5% (SLO)
```

### 7.2 Availability

```
availability = (successful_checks / total_checks) * 100

Measured via synthetic monitoring:
- Periodic health checks every 30 seconds
- Each check is binary: pass/fail
- Availability = % of checks that passed

Example:
- 288 checks per day (every 5 min)
- 287 checks passed
- Availability = 287/288 = 99.65%
```

### 7.3 Mean Time Between Failures (MTBF)

```
MTBF = Total Operating Time / Number of Failures

Example:
- Service uptime: 30 days
- Number of failures: 2
- MTBF = 30 days / 2 = 15 days between failures
```

---

## 8. Metric Extraction and Collection

### 8.1 Metrics from Traces

OpenTelemetry Collector configuration:

```yaml
receivers:
  jaeger:
    protocols:
      grpc:
        endpoint: 0.0.0.0:14250

processors:
  # Extract metrics from traces
  spanmetrics:
    dimensions:
      - service.name
      - http.method
      - http.url
      - http.status_code
      - span.kind
    metrics:
      - latency_histogram
      - error_rate_counter
      - request_rate_counter

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"

service:
  pipelines:
    traces:
      receivers: [jaeger]
      processors: [spanmetrics]
      exporters: [prometheus]
```

### 8.2 Metrics from Logs

Extract metrics from structured logs:

```csharp
public class MetricsExtractor
{
    public void ExtractFromLogs(LogEvent logEvent)
    {
        var duration = logEvent.Context?["duration_ms"];
        var statusCode = logEvent.Context?["http_status_code"];
        var service = logEvent.Context?["service"];

        if (duration != null && int.TryParse(duration.ToString(), out var ms))
        {
            _latencyHistogram
                .WithLabelValues(service?.ToString(), statusCode?.ToString())
                .Observe(ms);
        }
    }
}
```

### 8.3 Metrics from Infrastructure

Collect infrastructure metrics via Prometheus agents:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']  # Node Exporter
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']  # Postgres Exporter
  
  - job_name: 'kubernetes'
    kubernetes_sd_configs:
      - role: pod
```

---

## 9. Metric Storage and Retention

### 9.1 Metric Storage Strategy

| Metric Type | Storage | Retention | Resolution |
|---|---|---|---|
| Real-time (< 1h) | In-memory | 1 hour | 1 second |
| Short-term (1h-7d) | Prometheus | 7 days | 15 seconds |
| Medium-term (7d-90d) | Datadog/CloudWatch | 90 days | 1 minute |
| Long-term (> 90d) | S3/Archive | 1 year | 1 hour |

### 9.2 Cardinality Management

Prevent cardinality explosion:

```
❌ BAD: Include request IDs in metric labels
  http_request_duration{request_id="12345"} = 145ms
  http_request_duration{request_id="12346"} = 152ms
  → Creates millions of unique metric series

✅ GOOD: Use bounded labels only
  http_request_duration{service="appointment-service", endpoint="/api/v1/appointments"} = 145ms
  → Creates limited number of series
```

---

## 10. Metric Validation Checklist

For each service, verify:

- [ ] Latency metrics (p50, p95, p99) collected
- [ ] Traffic metrics (RPS) tracked per endpoint
- [ ] Error rate metrics broken down by status code
- [ ] Resource utilization monitored (CPU, Memory, DB connections)
- [ ] Composite metrics calculated (success rate, availability)
- [ ] Metrics stored with appropriate retention
- [ ] Metric cardinality controlled
- [ ] Metric collection has minimal overhead (< 1% CPU)
- [ ] Metrics queryable by service/endpoint/dimension
- [ ] Alerting rules configured for critical metrics

---

## 11. Metric Integration with SLOs

These metrics form the basis for SLO definitions (see SLO-1):

```
SLO Definition:
Availability SLO: 99.5%
Latency SLO: p95 < 200ms

Measurement:
- Availability = error_rate SLO (metric)
- Latency = latency_p95 (metric)

Monitoring:
- Alert if availability drops below 99.5%
- Alert if p95 latency exceeds 200ms
```

---

## 12. References

- Google SRE Book: https://sre.google/sre-book/
- OpenTelemetry Metrics: https://opentelemetry.io/docs/reference/specification/metrics/
- Prometheus Documentation: https://prometheus.io/docs/
- Datadog Metrics Guide: https://docs.datadoghq.com/metrics/

**Next:** [SLO-1: SLO Definition](../slo/slo-definition.md)
