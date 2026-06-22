# Unit Test Plan: US-049 Implement Secure Password Reset (Email Link)

## Metadata

- Story ID: US-049
- Epic: EP-005
- Plan ID: UTP-US-049
- Related Tasks: task_049_001, task_049_002, task_049_003, task_049_004
- Status: Planned

## Objectives

- Verify business-critical logic for US-049.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given a valid email, when a password reset is requested, then the system sends a one-time reset link to the user's email. | UT-US049-001, UT-US049-002 |
| AC2: Given an expired or invalid reset link, when the user attempts to use it, then the system rejects it with a clear error. | UT-US049-003, UT-US049-004 |
| AC3: Given a valid reset link, when the user submits a new password, then the password is updated and the token invalidated. | UT-US049-005, UT-US049-006 |
| AC4: Given multiple reset requests, then tokens are rate-limited and earlier unused tokens are invalidated. | UT-US049-007, UT-US049-008 |
| AC5: Given a password reset occurs, then the user receives notification of the activity. | UT-US049-009, UT-US049-010 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US049-101: validates happy-path behavior for the main workflow.
- UT-US049-102: rejects invalid inputs and preserves state consistency.
- UT-US049-103: enforces transition guards and business rules.
- UT-US049-104: verifies idempotent handling of repeated operations.
- UT-US049-105: validates fallback/error response contracts.
- UT-US049-106: ensures derived fields/flags are computed correctly.
- UT-US049-107: confirms no regression for non-target/unchanged states.
- UT-US049-108: validates boundary conditions and null/empty handling.

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
