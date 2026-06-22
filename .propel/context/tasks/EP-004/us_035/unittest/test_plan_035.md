# Unit Test Plan: US-035 Implement Drag-Drop Queue Reordering

## Metadata

- Story ID: US-035
- Epic: EP-004
- Plan ID: UTP-US-035
- Related Tasks: task_035_001, task_035_002, task_035_003, task_035_004, task_035_005
- Status: Planned

## Objectives

- Verify business-critical logic for US-035.
- Ensure edge-case handling for validation, state transitions, and error paths.
- Provide deterministic unit coverage for core modules before integration tests.

## Coverage Targets

- Statement coverage: >= 85%
- Branch coverage: >= 80%
- Critical decision logic: >= 90% branch coverage

## Acceptance Criteria Traceability

| Acceptance Criteria | Unit Test IDs |
|---|---|
| AC1: Given the staff queue is displayed, then items can be reordered by dragging and dropping. | UT-US035-001, UT-US035-002 |
| AC2: Given a queue order change is saved, then the new order persists for all staff users. | UT-US035-003, UT-US035-004 |
| AC3: Given another user changes the queue concurrently, then the system resolves or warns about conflicting reorder operations. | UT-US035-005, UT-US035-006 |
| AC4: Given the queue item order changes, then the updated order is reflected in downstream processing such as check-in workflows. | UT-US035-007, UT-US035-008 |

## Unit Boundaries

- Domain/service logic for the story workflow
- API/request validation and response mapping
- UI/state mapping logic where applicable
- Error handling and recovery paths

## Core Test Cases

- UT-US035-101: validates happy-path behavior for the main workflow.
- UT-US035-102: rejects invalid inputs and preserves state consistency.
- UT-US035-103: enforces transition guards and business rules.
- UT-US035-104: verifies idempotent handling of repeated operations.
- UT-US035-105: validates fallback/error response contracts.
- UT-US035-106: ensures derived fields/flags are computed correctly.
- UT-US035-107: confirms no regression for non-target/unchanged states.
- UT-US035-108: validates boundary conditions and null/empty handling.

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
