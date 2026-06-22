# Unit Test Plan: US-051 Implement Session Token with Role Info

## Metadata

- Story ID: US-051
- Epic: EP-005
- Plan ID: UTP-US-051
- Related Tasks: task_051_001, task_051_002, task_051_003, task_051_004
- Status: Planned

## Objectives

- Verify business-critical logic for US-051.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given a user authenticates, then the issued session token contains the user???s role and relevant access claims. | UT-US051-001, UT-US051-002 |
| AC2: Given a request includes a valid token, then the authorization layer can resolve permissions from token claims. | UT-US051-003, UT-US051-004 |
| AC3: Given a token is expired or invalid, then the system rejects the request with a 401 Unauthorized. | UT-US051-005, UT-US051-006 |
| AC4: Given role changes occur, then tokens are invalidated or refreshed to reflect updated permissions. | UT-US051-007, UT-US051-008 |
| AC5: Given token payloads are examined, then no sensitive PHI is stored in the token. | UT-US051-009, UT-US051-010 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US051-101: validates happy-path behavior for the main workflow.
- UT-US051-102: rejects invalid inputs and preserves state consistency.
- UT-US051-103: enforces transition guards and business rules.
- UT-US051-104: verifies idempotent handling of repeated operations.
- UT-US051-105: validates fallback/error response contracts.
- UT-US051-106: ensures derived fields/flags are computed correctly.
- UT-US051-107: confirms no regression for non-target/unchanged states.
- UT-US051-108: validates boundary conditions and null/empty handling.

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
