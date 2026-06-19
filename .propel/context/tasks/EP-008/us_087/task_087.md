# TASK-087: Make API Stateless (No Local Storage)

**User Story:** US-087 (EP-008)
**Source File:** `.propel/context/tasks/EP-008/us_087/us_087.md`
**Priority:** CRITICAL
**Status:** Planned
**Created:** 2026-06-19

## Objective
Remove instance-local session or workflow state from the API so any request can be served by any instance, with shared external state only where needed.

## AC Mapping
- AC-1: BE-1, QA-1
- AC-2: BE-2, QA-2
- AC-3: BE-3, QA-3
- AC-4: QA-2, QA-4

## Tasks
### BE-1: Remove Local Session Persistence
- Audit and eliminate file/disk/local-memory session persistence patterns.

### BE-2: Cross-Instance Auth Consistency
- Ensure auth/session validation works identically on any instance.

### BE-3: Externalize Shared State
- Move temporary workflow/session state to Redis or database where required.

### DOC-1: Statelessness Guidance
- Document prohibited local-state patterns and approved shared-state alternatives.

### QA-1: Local State Audit Tests
- Validate no user session state remains on local disk.

### QA-2: Multi-Instance Routing Tests
- Validate authenticated requests succeed across different instances.

### QA-3: Shared State Tests
- Validate required stateful data is stored in approved shared services.

### QA-4: Failover Session Continuity Tests
- Validate sessions survive scaling/failover without breakage.

## Definition of Done
- [ ] Local session persistence removed.
- [ ] Shared state externalized appropriately.
- [ ] Cross-instance auth/session behavior validated.
- [ ] AC-1 through AC-4 validated.
