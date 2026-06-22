# Unit Test Plan: US-032 Assign Walk-In to Available Slots

## Metadata

- Story ID: US-032
- Epic: EP-004
- Plan ID: UTP-US-032
- Related Tasks: task_032_001, task_032_002, task_032_003, task_032_004, task_032_005
- Status: Planned

## Objectives

- Verify business-critical logic for US-032.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given a walk-in patient is ready to be booked, when the staff user views available slots, then the system suggests open slots for the selected provider or clinic. | UT-US032-001, UT-US032-002 |
| AC2: Given a slot is selected, when the walk-in booking is submitted, then the appointment persists in that slot and no double-booking occurs. | UT-US032-003, UT-US032-004 |
| AC3: Given no open slots exist, when the staff user tries to save the walk-in, then a clear message is shown and alternative options are offered. | UT-US032-005, UT-US032-006 |
| AC4: Given the walk-in is scheduled, then the appointment record includes the selected slot and walk-in flag. | UT-US032-007, UT-US032-008 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US032-101: validates happy-path behavior for the main workflow.
- UT-US032-102: rejects invalid inputs and preserves state consistency.
- UT-US032-103: enforces transition guards and business rules.
- UT-US032-104: verifies idempotent handling of repeated operations.
- UT-US032-105: validates fallback/error response contracts.
- UT-US032-106: ensures derived fields/flags are computed correctly.
- UT-US032-107: confirms no regression for non-target/unchanged states.
- UT-US032-108: validates boundary conditions and null/empty handling.

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
