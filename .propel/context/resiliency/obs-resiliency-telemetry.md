# OBS-1: Resiliency Telemetry and Alerting

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, platform architects, SRE

---

## 1. Overview

This document defines metrics, dashboards, and alerting rules for monitoring resiliency behavior across timeouts, retries, circuit breakers, and fallbacks.

**Principles:**
- All resiliency events emit metrics
- Dashboards provide visibility into system health
- Alerts notify on anomalies or failures
- Metrics enable data-driven decisions

---

## 2. Resiliency Metrics

### 2.1 Timeout Metrics

```
timeout_events_total{service, endpoint}
  Description: Total timeout events
  Type: Counter
  Example: timeout_events_total{service="booking_db"} = 42

timeout_rate{service, endpoint}
  Description: Timeouts per minute
  Type: Gauge
  Example: timeout_rate{service="external_api"} = 1.5

timeout_duration_ms{service, endpoint}
  Description: Timeout value in milliseconds
  Type: Histogram (p50, p95, p99)
  Example: timeout_duration_ms{service="db", quantile="0.95"} = 10200
```

### 2.2 Retry Metrics

```
retry_attempts_total{service, endpoint, reason}
  Description: Total retry attempts
  Type: Counter
  Reasons: timeout, 5xx_error, connection_refused
  Example: retry_attempts_total{service="api", reason="timeout"} = 1250

retry_budget_used{service}
  Description: Retry budget utilization percentage
  Type: Gauge
  Range: 0-100%
  Example: retry_budget_used{service="booking_db"} = 65

retry_budget_exhausted{service}
  Description: Whether retry budget is exhausted
  Type: Gauge (0 or 1)
  Example: retry_budget_exhausted{service="api"} = 0
```

### 2.3 Circuit Breaker Metrics

```
circuit_breaker_state{service, state}
  Description: Current circuit breaker state
  Type: Gauge (0=closed, 1=open, 2=half_open)
  Example: circuit_breaker_state{service="payment_api", state="closed"} = 0

circuit_breaker_transitions_total{service, from_state, to_state}
  Description: Total state transitions
  Type: Counter
  Example: circuit_breaker_transitions_total{service="payment_api", from="closed", to="open"} = 3

circuit_breaker_fast_failures{service}
  Description: Requests rejected while circuit open
  Type: Counter
  Example: circuit_breaker_fast_failures{service="api"} = 450

half_open_probes_total{service, result}
  Description: Half-open probe attempts
  Type: Counter
  Result: success, failed, timeout
  Example: half_open_probes_total{service="db", result="success"} = 12
```

### 2.4 Fallback Metrics

```
fallback_activations_total{service, dependency, fallback_type}
  Description: Times fallback was activated
  Type: Counter
  FallbackType: empty_result, cached_data, skip_operation, retry_queue
  Example: fallback_activations_total{service="booking", dependency="search", type="empty"} = 8

fallback_success_rate{service, dependency}
  Description: Percentage of successful fallback operations
  Type: Gauge (0-100%)
  Example: fallback_success_rate{service="booking", dependency="recommendations"} = 98
```

---

## 3. Dashboard Configuration

### 3.1 Overview Dashboard

```
┌─ Resiliency Health Overview ────────────────────────────┐
│                                                          │
│ Active Circuit Breakers: 2                              │
│ ├─ PaymentGateway (OPEN)  - opened 5 min ago          │
│ └─ SearchService (CLOSED) - stable                    │
│                                                          │
│ Retry Budget Usage:                                    │
│ ├─ BookingDb: 65% (450/700)                           │
│ ├─ ExternalApi: 22% (110/500)                         │
│ └─ SearchService: 4% (10/250)                         │
│                                                          │
│ Fallback Activations (last hour):                      │
│ ├─ SearchService: 12 times                            │
│ ├─ RecommendationEngine: 8 times                      │
│ └─ NotificationService: 0 times                       │
│                                                          │
│ Fast Failures (circuit open rejections):               │
│ ├─ PaymentGateway: 245 requests/min                   │
│ └─ ExternalApi: 12 requests/min                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 3.2 Per-Service Deep Dive

```
┌─ PaymentGateway Service ───────────────────────────────┐
│                                                          │
│ Circuit Breaker State: OPEN (since 5 min ago)         │
│                                                          │
│ Request Rates:                                         │
│ ├─ Success rate: 78%                                   │
│ ├─ Timeout rate: 12%                                   │
│ ├─ Error rate: 10%                                     │
│                                                          │
│ Timeout Distribution:                                  │
│ ├─ p50: 8.2s                                           │
│ ├─ p95: 18.9s (ALERT - near 20s limit)               │
│ ├─ p99: 19.8s                                          │
│                                                          │
│ Retry Metrics:                                         │
│ ├─ Retry budget used: 45%                              │
│ ├─ Retry storms: 0                                     │
│ └─ Budget exhaustion risk: LOW                         │
│                                                          │
│ Recent Events:                                         │
│ ├─ T-5min: Circuit opened (10 failures in 30s)       │
│ ├─ T-3min: 125 fast failures (requests rejected)      │
│ ├─ T-2min: Probe sent (failed, timeout)               │
│ └─ T-1min: Next probe in 30s                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 4. Alerting Rules

### 4.1 Critical Alerts

```yaml
alerts:
  CircuitBreakerOpenCritical:
    condition: |
      circuit_breaker_state{state="open"} > 0
      AND time_in_open_state > 5m
    severity: CRITICAL
    action: |
      1. Page on-call engineer
      2. Investigate service health
      3. Prepare rollback/fix
    
  RetryBudgetExhausted:
    condition: |
      retry_budget_used{service="X"} > 0.95
    severity: CRITICAL
    action: |
      1. Investigate failure cause
      2. Increase budget or fix root cause
      3. Monitor closely
    
  TimeoutRateAnomaly:
    condition: |
      rate(timeout_events_total[5m]) > 10
      AND rate(timeout_events_total[5m]) > 
          avg_over_time(rate(timeout_events_total[5m])[30m]) * 2
    severity: CRITICAL
    action: |
      1. Check downstream service status
      2. Verify network connectivity
      3. Escalate if persistent
```

### 4.2 Warning Alerts

```yaml
alerts:
  CircuitBreakerFrequentOpen:
    condition: |
      rate(circuit_breaker_transitions_total{to="open"}[1h]) > 3
    severity: WARNING
    action: |
      1. Review error patterns
      2. Consider increasing thresholds
      3. Schedule follow-up investigation
    
  RetryBudgetWarning:
    condition: |
      retry_budget_used{service="X"} > 0.80
    severity: WARNING
    action: |
      1. Notify team
      2. Monitor closely for exhaustion
      3. Prepare escalation plan
    
  FallbackActivationSpike:
    condition: |
      rate(fallback_activations_total[5m]) > 5
    severity: WARNING
    action: |
      1. Investigate which dependency is failing
      2. Check dependent service health
      3. Verify fallback is working correctly
```

---

## 5. Metric Collection

### 5.1 C# / .NET Implementation

```csharp
using System.Diagnostics.Metrics;

public class ResiliencyMetrics
{
    private readonly Meter _meter;
    private readonly Counter<long> _timeoutEvents;
    private readonly Histogram<double> _timeoutDuration;
    private readonly Counter<long> _retryAttempts;
    private readonly ObservableGauge<int> _circuitState;
    
    public ResiliencyMetrics()
    {
        _meter = new Meter("Booking.Resiliency");
        
        _timeoutEvents = _meter.CreateCounter<long>(
            "timeout_events_total",
            description: "Total timeout events"
        );
        
        _timeoutDuration = _meter.CreateHistogram<double>(
            "timeout_duration_ms",
            unit: "ms",
            description: "Timeout duration in milliseconds"
        );
        
        _retryAttempts = _meter.CreateCounter<long>(
            "retry_attempts_total",
            description: "Total retry attempts"
        );
    }
    
    public void RecordTimeout(string service, string endpoint)
    {
        _timeoutEvents.Add(1, 
            new KeyValuePair<string, object>("service", service),
            new KeyValuePair<string, object>("endpoint", endpoint)
        );
    }
    
    public void RecordTimeoutDuration(double ms, string service)
    {
        _timeoutDuration.Record(ms,
            new KeyValuePair<string, object>("service", service)
        );
    }
}
```

### 5.2 Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'booking-service'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s
    
    # Record exemplars for trace correlation
    exemplar_sample_limit: 100
```

---

## 6. Testing Metrics Collection

### 6.1 Unit Test - Metric Recording

```csharp
[TestMethod]
public void ResiliencyMetrics_RecordsTimeout_IncrementsCounter()
{
    var metrics = new ResiliencyMetrics();
    var listener = new MeterListener();
    listener.InstrumentPublished += (instrument, arg) => { };
    listener.Start();
    
    // Record timeout
    metrics.RecordTimeout("payment_api", "/charge");
    
    // Verify via listener or exporter
    Assert.IsTrue(metricsExporter.HasMetric("timeout_events_total"));
}
```

---

## 7. Success Criteria

- [ ] All resiliency events emit metrics
- [ ] Dashboards configured for visibility
- [ ] Alerting rules defined for anomalies
- [ ] Metric collection tested and validated
- [ ] On-call runbooks reference metrics
- [ ] SLA/SLO baselines established
- [ ] Documentation published for SRE/on-call

---

## References

- OpenTelemetry Metrics: https://opentelemetry.io/docs/reference/specification/protocol/exporter/
- Prometheus Best Practices: https://prometheus.io/docs/prometheus/latest/best_practices/
- Google SRE Golden Signals: https://sre.google/sre-book/monitoring-distributed-systems/

**Next:** [OPS-1: Breaker and Recovery Runbook](ops-breaker-runbook.md)
