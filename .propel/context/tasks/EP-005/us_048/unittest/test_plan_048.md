# Unit Test Plan: US-048 Implement User Create/Edit/Deactivate

## Metadata

- Story ID: US-048
- Epic: EP-005
- Plan ID: UTP-US-048
- Related Tasks: task_048_001, task_048_002, task_048_003, task_048_004
- Status: Planned

## Objectives

- Verify business-critical logic for US-048.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given Admin credentials, when a create account request is submitted, then a new user record is created with assigned role and active status. | UT-US048-001, UT-US048-002 |
| AC2: Given Admin credentials, when user details are edited, then the updates are persisted and returned in the API response. | UT-US048-003, UT-US048-004 |
| AC3: Given Admin credentials, when a user is deactivated, then the user's status becomes inactive and they can no longer authenticate. | UT-US048-005, UT-US048-006 |
| AC4: Given invalid user data is submitted, then the API returns a validation error with clear messages. | UT-US048-007, UT-US048-008 |
| AC5: Given any create/edit/deactivate action occurs, then it is audit-logged with actor, timestamp, and changes. | UT-US048-009, UT-US048-010 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US048-101: validates happy-path behavior for the main workflow.
- UT-US048-102: rejects invalid inputs and preserves state consistency.
- UT-US048-103: enforces transition guards and business rules.
- UT-US048-104: verifies idempotent handling of repeated operations.
- UT-US048-105: validates fallback/error response contracts.
- UT-US048-106: ensures derived fields/flags are computed correctly.
- UT-US048-107: confirms no regression for non-target/unchanged states.
- UT-US048-108: validates boundary conditions and null/empty handling.

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
