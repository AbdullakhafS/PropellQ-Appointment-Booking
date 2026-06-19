# UNIT-TEST-PLAN-091: Query Result Caching (Redis)

User Story: US-091 (EP-008)
Source File: .propel/context/tasks/EP-008/us_091/us_091.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for Redis query result caching, cache invalidation strategy, cache hit/miss observability, and graceful database fallback on cache outage.

---

## 2. Scope and Assumptions

### In Scope
- Query result caching for selected read-heavy queries.
- Cache invalidation on data changes.
- Hit/miss ratio monitoring and observability.
- Graceful fallback when Redis is unavailable.

### Out of Scope
- Full caching of all endpoints.
- Caching sensitive PHI without controls.

### Assumptions
- Redis cache layer is abstracted via injectable adapter.
- Query execution is unit-testable via mocks.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Selected queries cached in Redis | UT-091-001, UT-091-002 |
| AC-2 | Cache invalidation updates/evicts stale entries | UT-091-003, UT-091-004 |
| AC-3 | Hit/miss metrics monitored and reported | UT-091-005, UT-091-006 |
| AC-4 | System falls back to DB queries on cache outage | UT-091-007, UT-091-008 |

---

## 4. Unit Test Areas

### UT-091-001: Query result stored in Redis cache
- Execute approved query.
- Assert result cached in Redis.

### UT-091-002: Cached result returned on subsequent calls
- Call query twice.
- Assert second call retrieves cached result.

### UT-091-003: Cache invalidated when underlying data changes
- Change source data.
- Assert cache entry invalidated/evicted.

### UT-091-004: Cache TTL expires stale entries
- Set cache with TTL.
- Assert entry evicted after expiration.

### UT-091-005: Cache hit metric incremented on cache retrieval
- Mock cache hit scenario.
- Assert hit counter incremented.

### UT-091-006: Cache miss metric incremented on DB query
- Mock cache miss scenario.
- Assert miss counter incremented.

### UT-091-007: Redis unavailable triggers DB fallback
- Mock Redis connection failure.
- Assert query executed directly on database.

### UT-091-008: Fallback behavior is graceful (no user-facing errors)
- Assert fallback query succeeds without exception.

---

## 5. Test Data and Mocking Strategy

- Fixtures: query result sets, invalidation events, TTL configs, cache metrics.
- Mocks: Redis adapter, cache invalidator, query executor, metrics publisher.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-091-001 through UT-091-008.

---

## 7. Suggested File Layout

- tests/unit/cache/QueryResultCaching.test.ts
- tests/unit/cache/CacheInvalidation.test.ts
- tests/unit/cache/CacheHitMissMetrics.test.ts
- tests/unit/cache/CacheFallback.test.ts
- tests/unit/cache/__fixtures__/queryCaching.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-091-001 through UT-091-008 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
