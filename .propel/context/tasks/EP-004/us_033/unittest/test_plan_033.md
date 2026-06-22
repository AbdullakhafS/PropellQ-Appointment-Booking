# Unit Test Plan: US-033 Flag Walk-In Appointments

## Metadata

- Story ID: US-033
- Epic: EP-004
- Plan ID: UTP-US-033
- Related Tasks: task_033_001, task_033_002, task_033_003, task_033_004, task_033_005
- Status: Planned

## Objectives

- Verify business-critical logic for US-033.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given a walk-in appointment is created, then the appointment record is marked with a "walk-in" indicator. | UT-US033-001, UT-US033-002 |
| AC2: Given staff views daily schedule or queue, then walk-in appointments have a distinct visual style or badge. | UT-US033-003, UT-US033-004 |
| AC3: Given staff filters for walk-ins, then only walk-in appointments are returned. | UT-US033-005, UT-US033-006 |
| AC4: Given a walk-in appointment is updated or moved, then the walk-in flag persists. | UT-US033-007, UT-US033-008 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US033-101: validates happy-path behavior for the main workflow.
- UT-US033-102: rejects invalid inputs and preserves state consistency.
- UT-US033-103: enforces transition guards and business rules.
- UT-US033-104: verifies idempotent handling of repeated operations.
- UT-US033-105: validates fallback/error response contracts.
- UT-US033-106: ensures derived fields/flags are computed correctly.
- UT-US033-107: confirms no regression for non-target/unchanged states.
- UT-US033-108: validates boundary conditions and null/empty handling.

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
