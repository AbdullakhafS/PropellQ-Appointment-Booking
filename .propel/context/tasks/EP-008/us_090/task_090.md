# TASK-090: Optimize Database Queries with Indexes

**User Story:** US-090 (EP-008)
**Source File:** `.propel/context/tasks/EP-008/us_090/us_090.md`
**Priority:** HIGH
**Status:** Done
**Created:** 2026-06-19

## Objective
Improve high-frequency database query performance through targeted indexing and query-plan optimization while avoiding unacceptable write amplification.

## AC Mapping
- AC-1: DB-1, QA-1
- AC-2: DB-2, QA-2
- AC-3: DB-3, QA-3
- AC-4: OPS-1, QA-2

## Tasks
### DB-1: Query Pattern Audit and Index Design
- Identify top booking, user, queue, and audit queries and design supporting indexes.

### DB-2: Query Plan Validation
- Compare before/after query plans and benchmark under representative load.

### DB-3: Write-Side Impact Review
- Measure write amplification and remove low-value indexes.

### OPS-1: Performance Telemetry Baseline
- Track latency p95/p99 before and after index changes.

### QA-1: Plan Improvement Tests
- Validate targeted queries use intended indexes and improve plans.

### QA-2: Load Validation Tests
- Validate latency improvements under load.

### QA-3: Write Impact Tests
- Validate no unacceptable write-side regressions.

## Definition of Done
- [x] High-frequency indexes implemented.
- [x] Query plans improved and benchmarked.
- [x] Write impact assessed and acceptable.
- [x] AC-1 through AC-4 validated.
