# TASK-088: Implement Redis Session Cache

**User Story:** US-088 (EP-008)
**Source File:** `.propel/context/tasks/EP-008/us_088/us_088.md`
**Priority:** CRITICAL
**Status:** Done
**Created:** 2026-06-19

## Objective
Integrate a secure Redis-backed session cache to support shared session state across stateless API instances, with expiration, fallback behavior, and PHI-safe storage practices.

## AC Mapping
- AC-1: BE-1, INFRA-1, QA-1
- AC-2: BE-2, QA-2
- AC-3: BE-3, QA-3
- AC-4: SEC-1, QA-4

## Tasks
### INFRA-1: Redis Provisioning and Security
- Configure Redis/managed cache with auth, TLS/network restrictions, and HA settings.

### BE-1: Session Storage Integration
- Store/retrieve session state from Redis across all API instances.

### BE-2: Expiration and Invalidation
- Align TTL and invalidation with session timeout policy.

### BE-3: Graceful Redis Failure Handling
- Define and implement safe fallback/degraded behavior when Redis unavailable.

### SEC-1: Sensitive Data Minimization
- Keep cached values small and free of PHI/secrets beyond approved identifiers.

### QA-1: Cross-Instance Session Tests
- Validate session retrieval from any instance.

### QA-2: Expiration Tests
- Validate timeout and invalidation behavior.

### QA-3: Redis Outage Tests
- Validate graceful fallback or safe failure behavior.

### QA-4: Security Review Tests
- Validate PHI is not stored in Redis values.

## Definition of Done
- [x] Redis session cache integrated securely.
- [x] Expiration and invalidation work correctly.
- [x] Outage fallback behavior documented and tested.
- [x] AC-1 through AC-4 validated.
