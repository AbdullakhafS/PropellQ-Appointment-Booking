# Unit Test Plan: US-038 Record Check-In Timestamp & Status

## Metadata

- Story ID: US-038
- Epic: EP-004
- Plan ID: UTP-US-038
- Related Tasks: task_038_001, task_038_002, task_038_003, task_038_004, task_038_005
- Status: Planned

## Objectives

- Verify business-critical logic for US-038.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given a patient is checked in, then the appointment record saves an arrival timestamp. | UT-US038-001, UT-US038-002 |
| AC2: Given check-in occurs, then the appointment status updates to "Arrived". | UT-US038-003, UT-US038-004 |
| AC3: Given staff reviews the appointment, then they can see arrival time and current status. | UT-US038-005, UT-US038-006 |
| AC4: Given queue or reporting UIs request appointment metadata, then arrival timestamp is included. | UT-US038-007, UT-US038-008 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US038-101: validates happy-path behavior for the main workflow.
- UT-US038-102: rejects invalid inputs and preserves state consistency.
- UT-US038-103: enforces transition guards and business rules.
- UT-US038-104: verifies idempotent handling of repeated operations.
- UT-US038-105: validates fallback/error response contracts.
- UT-US038-106: ensures derived fields/flags are computed correctly.
- UT-US038-107: confirms no regression for non-target/unchanged states.
- UT-US038-108: validates boundary conditions and null/empty handling.

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
