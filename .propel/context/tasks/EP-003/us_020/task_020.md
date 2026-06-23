# TASK-020: Implement Document Upload and Processing Pipeline

**User Story:** US-020 (EP-003)
**Source File:** `.propel/context/tasks/EP-003/us_020/us_020.md`
**Priority:** CRITICAL
**Estimated Effort:** 3-4 dev days
**Status:** Completed
**Created:** 2026-06-18

---

## 1. Objective

Implement a secure document upload endpoint that accepts PDF and DOCX files, stores them with PHI protections, enqueues asynchronous processing, and tracks processing status through to completion.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Accept PDF/DOCX uploads and store securely | BE-1, SEC-1, DB-1, QA-1 |
| AC-2 | Extracted metadata available after processing | BE-2, DB-2, QA-2 |
| AC-3 | Unsupported file type returns informative error | BE-1, QA-3 |
| AC-4 | Processing status updated and accessible from profile | BE-3, DB-2, QA-2 |

---

## 3. Layered Implementation Tasks

## Backend Tasks

### BE-1: Upload Endpoint
- Implement `POST /api/documents/upload`.
- Validate file type (PDF/DOCX only) and size limit.
- Return 400 with descriptive error for unsupported types.

### BE-2: Async Processing Queue
- Enqueue processing job after successful upload.
- Worker extracts text and metadata, forwards to extraction pipeline (US-021).

### BE-3: Status Tracking
- Update document processing status: `uploaded` → `processing` → `complete` / `failed`.
- Expose status via GET endpoint for profile and UI polling.

## Database Tasks

### DB-1: Document Storage Metadata
- Store document reference, patient ID, file type, upload timestamp, storage path (no raw PHI in DB).
- Add index on patient_id and status.

### DB-2: Processing Result Storage
- Store extracted metadata reference and status with timestamps.

## Security Tasks

### SEC-1: PHI-Safe Storage
- Store files in encrypted object storage (server-side encryption).
- Restrict access via signed/time-limited URLs.
- Ensure HIPAA-aligned storage configuration.

## Testing Tasks

### QA-1: Upload Tests
- Validate PDF and DOCX upload success flows.

### QA-2: Processing Status Tests
- Validate status transitions and result availability.

### QA-3: Rejection Tests
- Validate rejection of unsupported file types with clear error messages.

---

## 4. Dependencies

- Secure storage configured.
- Document extraction worker from US-021.

---

## 5. Definition of Done

- [x] Upload, processing queue, and status tracking implemented.
- [x] PHI-safe storage and access controls in place.
- [x] Rejection and error flows validated.
- [x] AC-1 through AC-4 validated.

---

## 6. Suggested Execution Order

1. DB-1, DB-2, SEC-1
2. BE-1, BE-2, BE-3
3. QA-1 through QA-3
