# Unit Test Plan: US-039 Implement Waitlist Join & Accept/Decline Flow

## Metadata

- Story ID: US-039
- Epic: EP-004
- Plan ID: UTP-US-039
- Related Tasks: task_039_001, task_039_002, task_039_003, task_039_004, task_039_005
- Status: Planned

## Objectives

- Verify business-critical logic for US-039.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given an appointment slot is full, then staff can add a patient to the waitlist. | UT-US039-001, UT-US039-002 |
| AC2: Given a slot opens, then the first eligible waitlisted patient receives an offer. | UT-US039-003, UT-US039-004 |
| AC3: Given a patient receives an offer, then they can accept or decline it within 30 minutes. | UT-US039-005, UT-US039-006 |
| AC4: Given the patient accepts, then the system converts the waitlist entry to a booked appointment. | UT-US039-007, UT-US039-008 |
| AC5: Given the patient declines or times out, then the next waitlisted patient receives an offer. | UT-US039-009, UT-US039-010 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US039-101: validates happy-path behavior for the main workflow.
- UT-US039-102: rejects invalid inputs and preserves state consistency.
- UT-US039-103: enforces transition guards and business rules.
- UT-US039-104: verifies idempotent handling of repeated operations.
- UT-US039-105: validates fallback/error response contracts.
- UT-US039-106: ensures derived fields/flags are computed correctly.
- UT-US039-107: confirms no regression for non-target/unchanged states.
- UT-US039-108: validates boundary conditions and null/empty handling.

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
