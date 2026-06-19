# UNIT-TEST-PLAN-020: Implement Document Upload and Processing

User Story: US-020 (EP-003)
Source File: .propel/context/tasks/EP-003/us_020/us_020.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit tests for document-upload and processing pipeline logic including file validation, queueing, processing-state transitions, and failure handling.

## 2. Scope and Assumptions

### In Scope
- File-type and size validation.
- Upload metadata capture.
- Processing-job enqueue and status updates.
- Retry and terminal-failure states.

### Out of Scope
- Real cloud storage/network transfer behavior.
- OCR/ML extraction accuracy.

### Assumptions
- Upload service and processing orchestrator are mockable.
- Status lifecycle is represented in deterministic state transitions.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 validation/upload | UT-020-001, UT-020-002 |
| AC-4 to AC-6 processing lifecycle | UT-020-003, UT-020-004 |
| AC-7 to AC-9 retries/failures | UT-020-005, UT-020-006 |

## 4. Unit Test Areas

### UT-020-001: Supported file types pass validation
### UT-020-002: Invalid type or oversize file is rejected with clear error
### UT-020-003: Valid upload creates processing job with correlation id
### UT-020-004: Status transitions queued to processing to completed
### UT-020-005: Transient processing failure schedules retry
### UT-020-006: Terminal failure marks document failed and logs reason
### UT-020-007: Duplicate upload detection prevents duplicate jobs
### UT-020-008: Metadata persists source and upload timestamp fields

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-020-001 through UT-020-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/documents/DocumentUploadValidation.test.ts
- tests/unit/clinical/documents/DocumentProcessingLifecycle.test.ts
- tests/unit/clinical/documents/__fixtures__/documentUpload.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-020.
- [ ] Test cases UT-020-001 through UT-020-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
