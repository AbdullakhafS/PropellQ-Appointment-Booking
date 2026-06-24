# TASK-085: Implement Automated Health Checks

**User Story:** US-085 (EP-008)
**Source File:** `.propel/context/tasks/EP-008/us_085/us_085.md`
**Priority:** CRITICAL
**Status:** Done
**Created:** 2026-06-19

## Objective
Implement readiness and liveness health probes for core services, integrate them with routing/orchestration, and alert on persistent failures without exposing sensitive internals.

## AC Mapping
- AC-1: BE-1, QA-1
- AC-2: INFRA-1, QA-2
- AC-3: BE-2, QA-3
- AC-4: OPS-1, QA-4
- AC-5: DOC-1, QA-5

## Tasks
### BE-1: Liveness and Readiness Endpoints
- Add lightweight endpoints for process health and dependency readiness.

### BE-2: Startup Readiness Logic
- Prevent readiness passing until critical dependencies are available.

### INFRA-1: Probe Integration
- Wire probes into LB/orchestrator health checks.

### OPS-1: Persistent Failure Alerting
- Alert on repeated health check failure patterns.

### DOC-1: Endpoint Behavior Documentation
- Document expected health endpoint semantics and consumers.

### QA-1: Endpoint Tests
- Validate liveness/readiness endpoints return expected signals.

### QA-2: Traffic Removal Tests
- Validate unhealthy instances removed from traffic.

### QA-3: Startup Gate Tests
- Validate traffic blocked until readiness passes.

### QA-4: Alert Tests
- Validate repeated failure alert generation.

### QA-5: Documentation Review
- Validate health-check docs are accurate and complete.

## Definition of Done
- [x] Health endpoints implemented (`app/src/health_checks.py` — `HealthProbeRegistry`, `StartupGate`, liveness/readiness).
- [x] Probe integrations active (`_STARTUP_GATE` wired into `/health/ready` in `web_app.py`).
- [x] Alerts configured (`HealthCheckAlerter`, `InMemoryAlertSink`, `AlertSinkProtocol`).
- [x] Documentation updated (`app/HEALTH_CHECK_ENDPOINTS.md`).
- [x] AC-1 through AC-5 validated (53/53 tests in `app/tests/test_health_checks_085.py`).
