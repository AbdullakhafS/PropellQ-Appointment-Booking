# Health Check Endpoints

**Document ID:** DOC-HEALTH-001  
**User Story:** US-085 (EP-008)  
**Version:** 1.0  
**Owner:** Platform / Infrastructure Engineer  

---

## 1. Overview

PropelIQ exposes two HTTP health check endpoints for integration with load
balancers, container orchestrators (Kubernetes, ECS), and monitoring tools.

| Endpoint | Type | Typical Consumer |
|----------|------|-----------------|
| `GET /health/live` | Liveness | Container runtime, orchestrator |
| `GET /health/ready` | Readiness | Load balancer (traffic gate) |

Implementation: `app/src/health_checks.py`, wired into `app/src/web_app.py`.

---

## 2. Liveness Probe — `GET /health/live`

### Purpose
Confirms the Python process is running and can handle HTTP requests.  
Does **not** check any external dependencies.

### Semantics
- Always returns **HTTP 200** as long as the WSGI app is up.
- Consumer action on failure: **restart the container/instance**.

### Response

```json
{
  "status": "alive",
  "checked_at": "2026-06-24T10:00:00.000000+00:00"
}
```

### Consumer Configuration

```yaml
# Kubernetes example
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
```

---

## 3. Readiness Probe — `GET /health/ready`

### Purpose
Confirms the instance is ready to receive traffic.  Checks:

1. **Database connectivity** — SQLite ping (or PostgreSQL in production).
2. **Startup gate** — all probes registered via `_STARTUP_GATE` must pass.

### Semantics
- Returns **HTTP 200** when all checks pass → instance receives traffic.
- Returns **HTTP 503** when any check fails → instance is removed from the
  load balancer pool until it recovers.

### Response — Ready

```json
{
  "status": "ready",
  "checks": {
    "database": "ok"
  },
  "checked_at": "2026-06-24T10:00:00.000000+00:00"
}
```

### Response — Not Ready

```json
{
  "status": "not_ready",
  "checks": {
    "database": "unavailable"
  },
  "checked_at": "2026-06-24T10:00:01.000000+00:00"
}
```

### Consumer Configuration

```yaml
# Kubernetes example
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 2
  successThreshold: 1
```

```nginx
# Nginx upstream example (see load_balancer.py render_nginx_config)
location = /health/ready {
    proxy_pass http://propeliq_api;
    proxy_connect_timeout 1s;
    proxy_read_timeout    2s;
}
```

---

## 4. Startup Gate (BE-2)

The `StartupGate` class prevents readiness from passing until all registered
critical dependencies have produced at least one passing probe result.

### Usage at Application Startup

```python
from src.health_checks import _STARTUP_GATE, FunctionProbe

# Register probes before serving traffic
_STARTUP_GATE.add_dependency(
    "database",
    FunctionProbe("database", lambda: db_ping())
)
_STARTUP_GATE.add_dependency(
    "cache",
    FunctionProbe("cache", lambda: cache_ping())
)
```

### Gate Behaviour

| Probes registered | All pass | `is_ready()` result |
|-------------------|----------|---------------------|
| None              | N/A      | `True` (open gate)  |
| 1+                | Yes      | `True`              |
| 1+                | Any fail | `False`             |

---

## 5. Persistent Failure Alerting (OPS-1)

`HealthCheckAlerter` emits alerts after `failure_threshold` consecutive
probe failures.  Wire it into the probe execution loop:

```python
from src.health_checks import (
    HealthProbeRegistry, HealthCheckAlerter,
    InMemoryAlertSink, FunctionProbe
)

registry = HealthProbeRegistry()
registry.register("database", FunctionProbe("database", db_ping))

alerter = HealthCheckAlerter(failure_threshold=3)  # OPS-1: alert after 3 failures

# In background health check loop
while True:
    results = registry.run_all()
    for probe_name, result in results.items():
        alerter.record_result(probe_name, result)
    time.sleep(5)
```

### Alert Routing

```
HealthCheckAlerter(failure_threshold=3)
  └─ AlertSinkProtocol
       ├─ InMemoryAlertSink     — tests / local dev
       ├─ CloudWatchAlertSink   — AWS production (custom)
       └─ PagerDutyAlertSink    — on-call paging (custom)
```

---

## 6. Probe Implementations

| Class | Use Case |
|-------|----------|
| `FunctionProbe(name, fn)` | Wrap any `() -> bool` callable |
| `AlwaysPassingProbe(name)` | Placeholder / test double |
| `AlwaysFailingProbe(name)` | Test alert threshold behaviour |

---

## 7. Key Security Properties

- Health endpoints are **unauthenticated** — no bearer token required.
- They return **no sensitive data** (no user info, no stack traces).
- Probe functions should catch all exceptions internally and return `False`
  rather than propagating; `FunctionProbe` does this automatically.
- Do not expose internal dependency hostnames or credentials in `message`
  fields when deploying publicly.

---

## 8. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-24 | Initial documentation. US-085 DOC-1. |
