# TASK-003: Implement Slot Reservation and Checkout Confirmation Flow

**User Story:** US-003 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_003/us_003.md`  
**Priority:** CRITICAL  
**Estimated Effort:** 5-6 dev days + QA/perf validation  
**Status:** Planned  
**Created:** 2026-06-18

---

## 1. Objective

Implement the end-to-end checkout flow for appointment slot selection with temporary reservation locking, optional preferred-slot capture, conflict-safe booking finalization, and accessible mobile-friendly confirmation UX.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Slot selection with visual state + details sidebar | FE-1, FE-2 |
| AC-2 | Optional preferred slot swap selection | FE-3, BE-2, DB-2 |
| AC-3 | 60-second reservation lock and temporary slot removal | BE-1, DB-1, FE-4 |
| AC-4 | Conflict modal if slot taken by another user | BE-3, FE-5 |
| AC-5 | Checkout validation and inline field errors | FE-6, QA-1 |
| AC-6 | Final confirmation summary before booking | FE-7 |
| AC-7 | Mobile single-column touch-friendly checkout submit | FE-8, QA-3 |
| AC-8 | Accessibility for labels, errors, keyboard navigation | FE-9, QA-2 |

---

## 3. Layered Implementation Tasks

## Frontend Tasks

### FE-1: Slot Selection State
- Add selected slot visual state in calendar results (Selected/Reserved indicators).
- On select, populate sidebar with appointment date/time, provider, and location.
- Ensure selection state clears safely on API conflict/expiry responses.

### FE-2: Checkout Entry Flow
- Add Confirm Booking action that transitions user into checkout state.
- Trigger reservation creation call before showing final submit action.
- Display reservation countdown timer from server `expiresAt`.

### FE-3: Preferred Slot Input
- Add optional Preferred Slot Swap checkbox and preferred-slot selector.
- Bind optional `preferredSlotId` into checkout and booking payloads.
- Keep optional path non-blocking when user leaves it blank.

### FE-4: Reserved State Presentation
- Show reserved badge and countdown while reservation is active.
- Disable duplicate submit while reservation request is in-flight.
- Auto-revert to selection view when reservation expires.

### FE-5: Conflict and Expiry Handling
- Handle `409 Conflict` with modal: slot already booked.
- Handle `410 Gone` with modal: reservation expired.
- Return user to slot selection with clear next-action guidance.

### FE-6: Form Validation and Error UX
- Validate required fields (appointment selected, provider context, terms accepted).
- Provide inline errors and error summary anchor for accessibility.
- Prevent submission when required fields are missing.

### FE-7: Confirmation Summary Screen
- Render pre-submit summary with date/time/provider/location/duration/cost estimate.
- Confirm action calls final booking endpoint with reservation token/id.
- Show deterministic success state including confirmation number.

### FE-8: Mobile Checkout UX
- Implement single-column layout for 375px and touch-friendly controls (>=44px height).
- Keep primary action sticky/visible where possible.
- Ensure no horizontal scrolling across checkout states.

### FE-9: Accessibility Compliance
- Bind labels to all inputs and controls.
- Ensure modal/dialogs are focus-trapped and keyboard-escapable.
- Announce inline errors and status changes to assistive tech.

## Backend/API Tasks

### BE-1: Reservation Creation Endpoint
- Implement `POST /api/appointments/checkout`:
  - Input: `slotId`, optional `preferredSlotId`
  - Output: `reservationId`, `expiresAt`, normalized appointment details
- Lock selected slot atomically with reservation expiry (default 60 seconds).
- Return consistent error schema for invalid slot state.

### BE-2: Preferred Slot Persistence
- Persist optional preferred slot choice with reservation/appointment context.
- Validate preferred slot exists and is eligible for future swap workflows.
- Keep preferred slot optional and non-failing when omitted.

### BE-3: Booking Finalization Endpoint
- Implement `POST /api/appointments/book`:
  - Validate reservation ownership and expiry
  - Convert reservation into booked appointment
  - Release reservation record and finalize audit events
- Return `409` if slot already booked and `410` if reservation expired.
- Ensure idempotency for duplicate client retries.

### BE-4: Cleanup and Recovery
- Implement scheduled cleanup to expire stale reservations.
- Release reserved slots for expired reservations.
- Add protection against partial failures (transaction rollback + retry-safe operations).

### BE-5: Logging and Traceability
- Add structured logs for reservation create/expire/finalize/conflict paths.
- Propagate correlation IDs across checkout and booking endpoints.
- Emit metrics for lock contention, expiry rate, and conflict rate.

## Database Tasks

### DB-1: Reservations Table and Constraints
- Create Reservations table with:
  - `slot_id`, `user_id`, `created_at`, `expires_at`, status
- Add indexes for `slot_id` and `expires_at` cleanup scans.
- Add uniqueness/locking constraints to prevent duplicate active reservations per slot.

### DB-2: Appointment Preferred Slot Column
- Add nullable `preferred_slot_id` to Appointments (or reservation projection table).
- Add FK/index for fast lookup in downstream swap logic.

### DB-3: Concurrency and Transaction Integrity
- Enforce transaction boundaries around reserve/book transitions.
- Validate behavior under concurrent reserve/book attempts.
- Add deterministic tie-break strategy for simultaneous reservation attempts.

## Testing Tasks

### QA-1: Unit Tests
- Form validation and required-field rules.
- Reservation countdown and expiry state transitions.
- Preferred slot optional-path handling.

### QA-2: Integration and API Contract Tests
- Reservation creation success/failure cases.
- Booking finalization with valid/expired/conflicting reservation.
- Error code and payload consistency for `409` and `410`.

### QA-3: Accessibility and Responsive Tests
- Keyboard and screen-reader flow through checkout and dialogs.
- Mobile layout verification at 375/768/1024+.
- Control touch target size validation.

### QA-4: Concurrency and Performance Tests
- Simulate 100 concurrent checkout attempts on same slot pool.
- Verify no double-booking and stable API response under contention.
- Confirm checkout/book endpoints stay within target latency (<500ms for baseline conditions).

---

## 4. Dependencies

- US-001 and US-002 flows available for slot discovery and selection.
- EP-005 authentication available for user-bound reservation ownership checks.
- Appointment schema and slot state model finalized in data layer.

---

## 5. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Reservation race causes double-booking | Critical | DB-level active-slot constraints + transactional reserve/book flow |
| Reservation expiration timing drift | High | Server-issued `expiresAt`, server-authoritative validation, synchronized cleanup job |
| Duplicate client submits create inconsistent state | Medium | Endpoint idempotency key or reservation-state guarding |
| Complex mobile checkout causes drop-off | Medium | Simplified single-column UX and reduced required fields |
| Dialog/error states inaccessible | Medium | Focus management, aria-live announcements, keyboard escape support |

---

## 6. Definition of Done

- [ ] Slot selection and details sidebar behavior implemented.
- [ ] Reservation creation endpoint implemented with 60-second lock semantics.
- [ ] Booking finalization endpoint implemented with conflict/expiry handling.
- [ ] Optional preferred slot path captured and persisted.
- [ ] Reservation cleanup job implemented and verified.
- [ ] Concurrency tests prove zero double-booking under load.
- [ ] Mobile and accessibility validations pass.
- [ ] Unit/integration/performance tests passing.
- [ ] API contract documented in Swagger/OpenAPI.
- [ ] Story AC-1 through AC-8 mapped and validated.

---

## 7. Suggested Execution Order

1. DB-1, DB-3
2. BE-1, BE-3
3. BE-2, DB-2
4. FE-1 through FE-7
5. FE-8, FE-9
6. BE-4, BE-5
7. QA-1 through QA-4
8. Final AC validation and sign-off
