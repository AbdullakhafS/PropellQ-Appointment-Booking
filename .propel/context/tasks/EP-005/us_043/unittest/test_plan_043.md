# Unit Test Plan: US-043 Implement RBAC Permission Model

## Metadata

- Story ID: US-043
- Epic: EP-005
- Plan ID: UTP-US-043
- Related Tasks: task_043_001, task_043_002, task_043_003, task_043_004, task_043_005
- Status: Planned

## Objectives

- Verify business-critical logic for US-043.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given an authenticated user, when they request a protected resource, then role-based permission checks are executed before returning data. | UT-US043-001, UT-US043-002 |
| AC2: Given a Patient user, when they access appointment or profile endpoints, then they only see their own records and not other patients'. | UT-US043-003, UT-US043-004 |
| AC3: Given a Staff user, when they access queue or check-in endpoints, then they can access only assigned patient appointments and not unrelated patient details. | UT-US043-005, UT-US043-006 |
| AC4: Given an Admin user, when they access management endpoints, then they have full access to user account and audit resources. | UT-US043-007, UT-US043-008 |
| AC5: Given a request fails authorization, then the API returns a standard 403 response and logs the denied action. | UT-US043-009, UT-US043-010 |
| AC6: Given role definitions are updated, then the permission model is documented and reviewable. | UT-US043-011, UT-US043-012 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US043-101: validates happy-path behavior for the main workflow.
- UT-US043-102: rejects invalid inputs and preserves state consistency.
- UT-US043-103: enforces transition guards and business rules.
- UT-US043-104: verifies idempotent handling of repeated operations.
- UT-US043-105: validates fallback/error response contracts.
- UT-US043-106: ensures derived fields/flags are computed correctly.
- UT-US043-107: confirms no regression for non-target/unchanged states.
- UT-US043-108: validates boundary conditions and null/empty handling.

## Mocking Strategy

- Mock persistence and external service boundaries.
- Use deterministic time fixtures for timestamp-dependent logic.
- Assert side effects through spies on event dispatch and state updates.

## Exit Criteria

- All listed unit tests pass.
- Coverage gates are met for story scope.
- No open critical defects in core logic.

## Suggested Execution Order

1. Implement validation and transition guard tests.
2. Implement happy-path and idempotency tests.
3. Implement error/fallback and boundary-condition tests.
4. Run full unit suite and validate coverage thresholds.
