# UNIT-TEST-PLAN-057: Document Upload from Dashboard

User Story: US-057 (EP-006)
Source File: .propel/context/tasks/EP-006/us_057/us_057.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for dashboard document upload to validate supported file acceptance, unsupported file rejection messaging, upload progress/confirmation UX, and uploaded document status visibility.

---

## 2. Scope and Assumptions

### In Scope
- Upload widget behavior (file picker/drag-drop trigger behavior).
- Client-side validation for type and size.
- Upload progress and completion messaging.
- Uploaded document status list rendering (type, time, processing state).
- Error-state handling for rejected or failed uploads.

### Out of Scope
- End-to-end storage persistence verification.
- PHI encryption/storage internals (covered by backend/security tests).
- OCR/clinical extraction behavior.

### Assumptions
- Upload component uses service abstraction for upload and status retrieval.
- Supported file types include PDF, JPG, PNG, DOCX.
- Unit tests use Jest/Vitest with Testing Library patterns.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Uploaded document is accepted and saved | UT-057-001, UT-057-002 |
| AC-2 | Supported file types upload successfully with confirmation | UT-057-003, UT-057-004 |
| AC-3 | Unsupported file type is rejected with clear error | UT-057-005, UT-057-006 |
| AC-4 | Uploaded document status and type are visible in dashboard | UT-057-007, UT-057-008 |

---

## 4. Unit Test Areas

## A. Upload Widget and Trigger Behavior

### UT-057-001: Upload widget accepts selected file and starts upload flow
- Mock file selection event with valid supported file.
- Assert upload service call is invoked with expected payload.
- Assert control state switches to uploading.

### UT-057-002: Drag-drop and picker entry paths behave consistently
- Simulate drag-drop and input-picker flows with same valid file.
- Assert both paths call upload with equivalent metadata.

## B. Supported Type Success Behavior

### UT-057-003: Supported file type matrix passes client validation
- Test PDF, JPG, PNG, DOCX fixtures.
- Assert no validation error for each supported extension/mime mapping.

### UT-057-004: Successful upload shows completion confirmation
- Mock successful upload response.
- Assert progress reaches completion state.
- Assert success confirmation message is rendered.

## C. Rejection and Validation Behavior

### UT-057-005: Unsupported file type is rejected before upload request
- Provide unsupported file (for example EXE or ZIP).
- Assert upload request is not sent.
- Assert clear unsupported-type error appears.

### UT-057-006: Oversized or invalid file shows clear validation message
- Provide valid type but over-limit size fixture.
- Assert user-facing size/validation error appears.
- Assert widget remains usable for retry with valid file.

## D. Status Visibility and Dashboard List

### UT-057-007: Uploaded document row renders type, upload time, and status
- Mock status list response including newly uploaded file.
- Assert document type label, timestamp text, and processing state are displayed.

### UT-057-008: Status refresh updates row state correctly
- Render with initial status (for example Processing).
- Simulate status polling/refresh update to Completed.
- Assert row status updates without duplicate rows or remount issues.

## E. Robustness and Error States

### UT-057-009: Upload service failure shows recoverable error state
- Mock upload API failure.
- Assert failure message appears with retry affordance (if defined).
- Assert component remains interactive for new attempts.

### UT-057-010: Mixed list with failed and successful uploads renders independently
- Mock status list containing multiple upload outcomes.
- Assert each row reflects independent status and messaging.

---

## 5. Non-Functional Unit Checks

### UT-057-011: Accessibility checks for upload controls and status messages
- Assert upload trigger has accessible label/name.
- Assert validation and status messages are screen-reader discoverable.

### UT-057-012: Stable rerender behavior during progress updates
- Simulate incremental progress updates.
- Assert progress UI updates deterministically without stale jumps or duplicate items.

---

## 6. Test Data Strategy

- Maintain deterministic file fixtures for supported and unsupported extensions.
- Include boundary-size fixtures (just below/above allowed size).
- Maintain status fixtures for Processing, Completed, Failed states.
- Use fixed timestamps for stable rendering assertions.

---

## 7. Mocking Strategy

- Mock upload API/service for success and failure paths.
- Mock status retrieval hook/service and polling updates.
- Mock file objects with controlled name, mime type, and size.
- Mock date/time formatter for deterministic upload-time assertions.

---

## 8. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-057-001 through UT-057-008 before merge.

---

## 9. Exit Criteria

- All AC-mapped unit tests pass.
- Coverage thresholds met for upload module.
- No flaky behavior across 3 consecutive local/CI runs.
- Supported/rejected/status scenarios pass consistently.

---

## 10. Suggested File Layout

- tests/unit/documents/DocumentUploadWidget.test.tsx
- tests/unit/documents/DocumentUploadValidation.test.tsx
- tests/unit/documents/DocumentUploadStatusList.test.tsx
- tests/unit/documents/DocumentUploadStates.test.tsx
- tests/unit/documents/__fixtures__/documentUpload.fixtures.ts

---

## 11. Execution Checklist

1. Create file fixtures for supported, unsupported, and boundary-size cases.
2. Implement widget trigger tests (UT-057-001..002).
3. Implement supported-type and success UX tests (UT-057-003..004).
4. Implement rejection/validation tests (UT-057-005..006).
5. Implement status rendering/refresh tests (UT-057-007..008).
6. Implement error and mixed-state robustness tests (UT-057-009..010).
7. Add accessibility and rerender stability checks (UT-057-011..012).
8. Run unit suite and verify coverage thresholds.

---

## 12. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-057.
- [ ] Test cases UT-057-001 through UT-057-012 implemented.
- [ ] Acceptance criteria traceability retained in test naming/comments.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes without flaky failures.
