# UNIT-TEST-PLAN-097: Disaster Recovery Drill

User Story: US-097 (EP-008)
Source File: .propel/context/tasks/EP-008/us_097/us_097.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for disaster recovery drill execution, findings documentation, action item creation, and plan updates based on drill outcomes.

---

## 2. Scope and Assumptions

### In Scope
- Controlled DR drill execution in test environment.
- Findings and gaps documentation.
- Action item creation for remediation.
- Plan updates from drill learnings.

### Out of Scope
- Unplanned production outages.

### Assumptions
- Drill environment state is testable via mocks.
- Findings and action tracking is injectable.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Recovery plan executed in controlled environment | UT-097-001, UT-097-002 |
| AC-2 | Gaps and improvements documented | UT-097-003, UT-097-004 |
| AC-3 | Action items created for deficiencies | UT-097-005, UT-097-006 |
| AC-4 | Plan updated based on findings | UT-097-007, UT-097-008 |

---

## 4. Unit Test Areas

### UT-097-001: DR drill executes recovery plan in test environment
- Run simulated drill scenario.
- Assert plan executed without errors.

### UT-097-002: Drill team can follow plan steps sequentially
- Execute each step in order.
- Assert team able to proceed through recovery.

### UT-097-003: Gaps in plan identified and documented
- Capture deviations during drill.
- Assert gaps logged with detail.

### UT-097-004: Time-to-recover measured and compared to RTO
- Measure drill recovery time.
- Assert actual vs. target RTO documented.

### UT-097-005: Drill findings captured with description and severity
- Log findings with structured format.
- Assert severity and recommendation recorded.

### UT-097-006: Action items created for each finding
- Create remediation tasks from findings.
- Assert actionable items with owner and deadline.

### UT-097-007: Plan updated with drill improvements
- Apply approved changes to plan.
- Assert updated version reflects drill learnings.

### UT-097-008: Plan version incremented after update
- Check version number.
- Assert version incremented post-drill.

---

## 5. Test Data and Mocking Strategy

- Fixtures: drill scenarios, recovery timelines, finding templates, action item configs.
- Mocks: drill executor, findings logger, plan updater.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-097-001 through UT-097-008.

---

## 7. Suggested File Layout

- tests/unit/dr/DrillExecution.test.ts
- tests/unit/dr/FindingsDocumentation.test.ts
- tests/unit/dr/ActionItemCreation.test.ts
- tests/unit/dr/PlanUpdatesFromDrill.test.ts
- tests/unit/dr/__fixtures__/drDrill.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-097-001 through UT-097-008 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
