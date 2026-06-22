# Unit Test Plan: US-040 Auto-Offer First Waitlist Patient

## Metadata

- Story ID: US-040
- Epic: EP-004
- Plan ID: UTP-US-040
- Related Tasks: task_040_001, task_040_002, task_040_003, task_040_004, task_040_005
- Status: Planned

## Objectives

- Verify business-critical logic for US-040.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given a slot is released, then the system identifies the first eligible waitlisted patient. | UT-US040-001, UT-US040-002 |
| AC2: Given the first waitlisted patient is eligible, then the system creates and sends an offer notification. | UT-US040-003, UT-US040-004 |
| AC3: Given the patient accepts the offer, then the appointment is confirmed automatically. | UT-US040-005, UT-US040-006 |
| AC4: Given the offer expires or is declined, then the next patient receives an offer. | UT-US040-007, UT-US040-008 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US040-101: validates happy-path behavior for the main workflow.
- UT-US040-102: rejects invalid inputs and preserves state consistency.
- UT-US040-103: enforces transition guards and business rules.
- UT-US040-104: verifies idempotent handling of repeated operations.
- UT-US040-105: validates fallback/error response contracts.
- UT-US040-106: ensures derived fields/flags are computed correctly.
- UT-US040-107: confirms no regression for non-target/unchanged states.
- UT-US040-108: validates boundary conditions and null/empty handling.

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
