# UNIT-TEST-PLAN-094: Uptime Monitoring & Alerting

User Story: US-094 (EP-008)
Source File: .propel/context/tasks/EP-008/us_094/us_094.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for uptime probe configuration, continuous monitoring, incident alerting, availability dashboards, and configurable SLA thresholds.

---

## 2. Scope and Assumptions

### In Scope
- Synthetic and internal uptime probes.
- Incident alert routing to operations team.
- Availability dashboards and SLA metrics.
- Configurable alert thresholds and documentation.

### Out of Scope
- Full business metrics observability.

### Assumptions
- Probe execution is mockable.
- Alert routing and dashboard systems are abstractable.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Uptime monitored continuously | UT-094-001, UT-094-002 |
| AC-2 | Alerts sent on outage/degraded state | UT-094-003, UT-094-004 |
| AC-3 | Dashboards display availability and incident history | UT-094-005, UT-094-006 |
| AC-4 | Alert thresholds configurable and documented | UT-094-007, UT-094-008 |

---

## 4. Unit Test Areas

### UT-094-001: Uptime probe monitors service availability continuously
- Mock service status checks.
- Assert availability tracked over time.

### UT-094-002: Probe failures logged and tracked for analysis
- Mock probe failures.
- Assert failures recorded with timestamp and reason.

### UT-094-003: Service outage triggers alert
- Mock complete service outage.
- Assert alert generated.

### UT-094-004: Service degradation triggers alert
- Mock degraded response times/error rates.
- Assert degradation alert generated.

### UT-094-005: Dashboard displays current uptime percentage
- Query dashboard data.
- Assert uptime percentage calculated and displayed.

### UT-094-006: Dashboard shows recent incident history
- Add sample incidents to history.
- Assert incidents displayed in dashboard.

### UT-094-007: Alert threshold is configurable
- Update threshold configuration.
- Assert new threshold applied to subsequent checks.

### UT-094-008: Threshold values are documented
- Assert threshold documentation complete and clear.

---

## 5. Test Data and Mocking Strategy

- Fixtures: service status states, uptime percentages, incident history, threshold configs.
- Mocks: probe executor, alert router, dashboard data provider.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-094-001 through UT-094-008.

---

## 7. Suggested File Layout

- tests/unit/monitoring/UptimeProbeMonitoring.test.ts
- tests/unit/monitoring/IncidentAlertRouting.test.ts
- tests/unit/monitoring/AvailabilityDashboard.test.ts
- tests/unit/monitoring/ThresholdConfiguration.test.ts
- tests/unit/monitoring/__fixtures__/uptimeMonitoring.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-094-001 through UT-094-008 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
