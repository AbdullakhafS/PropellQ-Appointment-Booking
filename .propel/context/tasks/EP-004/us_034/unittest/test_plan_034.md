# Unit Test Plan: US-034 Build Real-Time Queue Management UI

## Metadata

- Story ID: US-034
- Epic: EP-004
- Plan ID: UTP-US-034
- Related Tasks: task_034_001, task_034_002, task_034_003, task_034_004, task_034_005, task_034_006
- Status: Planned

## Objectives

- Verify business-critical logic for US-034.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given multiple staff users are logged in, when any user updates the queue, then all sessions see the queue change in real-time. | UT-US034-001, UT-US034-002 |
| AC2: Given a new walk-in or check-in event occurs, then the queue updates without manual refresh. | UT-US034-003, UT-US034-004 |
| AC3: Given queue items change status, then the UI reflects the current status immediately. | UT-US034-005, UT-US034-006 |
| AC4: Given the queue displays appointments, then each item shows patient name, appointment type, provider, scheduled time, and current status. | UT-US034-007, UT-US034-008 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US034-101: validates happy-path behavior for the main workflow.
- UT-US034-102: rejects invalid inputs and preserves state consistency.
- UT-US034-103: enforces transition guards and business rules.
- UT-US034-104: verifies idempotent handling of repeated operations.
- UT-US034-105: validates fallback/error response contracts.
- UT-US034-106: ensures derived fields/flags are computed correctly.
- UT-US034-107: confirms no regression for non-target/unchanged states.
- UT-US034-108: validates boundary conditions and null/empty handling.

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
