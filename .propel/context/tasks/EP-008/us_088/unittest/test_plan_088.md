# UNIT-TEST-PLAN-088: Redis Session Cache

User Story: US-088 (EP-008)
Source File: .propel/context/tasks/EP-008/us_088/us_088.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for Redis session cache integration, cross-instance session retrieval, TTL expiration, PHI-safe storage practices, and graceful Redis failure handling.

---

## 2. Scope and Assumptions

### In Scope
- Redis provisioning and security validation.
- Session storage/retrieval across API instances.
- TTL and session invalidation behavior.
- Graceful fallback on Redis unavailability.
- PHI-safe caching practices.

### Out of Scope
- Redis cluster management internals.
- Full Redis persistence tuning.

### Assumptions
- Redis access is abstracted via injectable adapter.
- Session validation is unit-testable via mocks.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Session retrieved from Redis across any instance | UT-088-001, UT-088-002 |
| AC-2 | Session entry removed/invalidated on expiry | UT-088-003, UT-088-004 |
| AC-3 | System degrades gracefully when Redis unavailable | UT-088-005, UT-088-006 |
| AC-4 | PHI excluded from Redis cached values | UT-088-007, UT-088-008 |

---

## 4. Unit Test Areas

### UT-088-001: Session stored in Redis and retrieved by key
- Store session in mock Redis.
- Assert retrieval returns same data.

### UT-088-002: Session retrieved successfully from any instance
- Store session once, retrieve from different mock instances.
- Assert consistent retrieval.

### UT-088-003: Session TTL/timeout invalidates entry
- Set session with TTL.
- Assert entry expired and unavailable after TTL.

### UT-088-004: Manual session invalidation removes entry
- Trigger logout/invalidate action.
- Assert entry removed from cache.

### UT-088-005: Redis connection failure triggers safe fallback
- Mock Redis unavailable.
- Assert system uses fallback (error response or degraded path).

### UT-088-006: Fallback behavior is documented and non-breaking
- Assert failure mode is explicit and safe.

### UT-088-007: Cached session values do not include PHI
- Validate session object fields.
- Assert no PHI/patient data in Redis values.

### UT-088-008: Cache keys are non-sensitive identifiers
- Assert session key format does not leak sensitive data.

---

## 5. Test Data and Mocking Strategy

- Fixtures: session payloads, TTL configs, Redis failure states, PHI-safe/unsafe cache data.
- Mocks: Redis adapter, session validator, fallback handler.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-088-001 through UT-088-008.

---

## 7. Suggested File Layout

- tests/unit/cache/RedisCacheRetrieval.test.ts
- tests/unit/cache/RedisCacheExpiration.test.ts
- tests/unit/cache/RedisCacheFailover.test.ts
- tests/unit/cache/CachePHISafety.test.ts
- tests/unit/cache/__fixtures__/redis.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-088-001 through UT-088-008 implemented.
- [ ] AC-1 through AC-4 traceability retained.
- [ ] Coverage and CI reliability targets met.
