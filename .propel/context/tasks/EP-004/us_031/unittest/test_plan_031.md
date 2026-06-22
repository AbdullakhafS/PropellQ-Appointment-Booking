# Unit Test Plan: US-031 Build Walk-In Booking UI (Search/Create Patient)

## Metadata

- Story ID: US-031
- Epic: EP-004
- Plan ID: UTP-US-031
- Related Tasks: task_031_001, task_031_002, task_031_003, task_031_004, task_031_005
- Status: Planned

## Objectives

- Verify business-critical logic for US-031.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given a staff user is on the walk-in booking screen, when they search for a patient, then matching patient records are displayed instantly. | UT-US031-001, UT-US031-002 |
| AC2: Given a staff user cannot find the patient, when they create a new patient record, then the record is created and available for booking. | UT-US031-003, UT-US031-004 |
| AC3: Given a patient is selected or created, when the staff user starts booking, then the booking flow proceeds with walk-in context. | UT-US031-005, UT-US031-006 |
| AC4: Given the walk-in is saved, then the appointment record is flagged as a walk-in and visible in the staff queue. | UT-US031-007, UT-US031-008 |
| AC5: Given the staff user submits the booking, then the system shows a confirmation summary with patient name, provider, time, and walk-in status. | UT-US031-009, UT-US031-010 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US031-101: validates happy-path behavior for the main workflow.
- UT-US031-102: rejects invalid inputs and preserves state consistency.
- UT-US031-103: enforces transition guards and business rules.
- UT-US031-104: verifies idempotent handling of repeated operations.
- UT-US031-105: validates fallback/error response contracts.
- UT-US031-106: ensures derived fields/flags are computed correctly.
- UT-US031-107: confirms no regression for non-target/unchanged states.
- UT-US031-108: validates boundary conditions and null/empty handling.

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
