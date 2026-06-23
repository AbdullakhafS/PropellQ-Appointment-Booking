# TASK-003: Implement Slot Reservation and Checkout Locking

**User Story:** US-003 (EP-001)  
**Source File:** `.propel/context/tasks/EP-001/us_003/us_003.md`  
**Priority:** CRITICAL  
**Estimated Effort:** 5-6 dev days + concurrency validation  
**Status:** Planned  
**Created:** 2026-06-18

---

## 1. Objective

Implement a resilient booking checkout flow that reserves a selected slot during checkout, supports optional preferred-slot capture, and prevents double-booking under concurrent load.

---

## 2. Scope Mapping to Acceptance Criteria

| AC ID | User Story Acceptance Criterion | Covered By |
|---|---|---|
| AC-1 | Slot selection and summary panel | FE-1, QA-1 |
| AC-2 | Preferred slot optional input | FE-2, DB-1, QA-1 |
| AC-3 | 60-second reservation lock | BE-1, DB-2, QA-2 |
| AC-4 | Conflict handling modal and recovery | BE-2, FE-3, QA-3 |
| AC-5 | Checkout form validation | FE-4, QA-1 |
| AC-6 | Confirmation summary before final booking | FE-5, QA-1 |
| AC-7 | Mobile single-column checkout and POST submit | FE-6, BE-3, QA-4 |
| AC-8 | Accessible form and error announcements | A11Y-1, QA-5 |

---

## 3. Layered Implementation Tasks

## Frontend Tasks

### FE-1: Slot Selection State
- Add selected slot highlighting and details sidebar.
- Persist selected slot through checkout step transitions.

### FE-2: Preferred Slot Capture
- Add optional preferred-slot checkbox/dropdown.
- Validate optional preferred slot semantics.

### FE-3: Conflict Recovery UI
- Show conflict modal when 409/slot unavailable is returned.
- Return user to calendar with reservation cleared.

### FE-4: Checkout Validation
- Validate required confirmation fields and terms checkbox.
- Show inline, accessible validation messages.

### FE-5: Confirmation Summary
- Render final summary of date/time/provider/location/duration/cost estimate.

### FE-6: Mobile Checkout UX
- Single-column touch-optimized layout.
- Minimum button size and reliable mobile submission.

## Backend/API Tasks

### BE-1: Reservation API
- Implement `POST /api/appointments/checkout` to create 60-second reservation.
- Return reservation ID and expiry timestamp.

### BE-2: Booking Finalization API
- Implement `POST /api/appointments/book` to finalize appointment from reservation.
- Return 409 for conflicts and 410 for expired reservation.

### BE-3: Idempotent Booking Submission
- Add idempotency key handling for duplicate client submissions.

## Database Tasks

### DB-1: Preferred Slot Data
- Add/validate `preferred_slot_id` in appointments (nullable).

### DB-2: Reservation Storage
- Create reservation table with `slot_id`, `user_id`, `expires_at`.
- Add index for expiry cleanup and active lookup.

### DB-3: Concurrency Safety
- Enforce unique constraints to prevent double booking.
- Use locking strategy for final slot claim.

## Accessibility Tasks

### A11Y-1: Form Accessibility
- Ensure labels, field descriptions, error announcements, and keyboard flow.

## Testing Tasks

### QA-1: Functional Flow Tests
- Validate selection, preferred slot, validation, and summary.

### QA-2: Reservation Expiry Tests
- Validate lock creation, timeout expiry, and cleanup.

### QA-3: Conflict Tests
- Simulate concurrent booking attempts and verify safe outcomes.

### QA-4: Mobile Tests
- Validate full booking flow at mobile breakpoint.

### QA-5: Accessibility Tests
- Validate keyboard and screen-reader behavior for checkout.

---

## 4. Dependencies

- US-001 and US-002 for search/calendar selection.
- EP-005 authentication context.

---

## 5. Definition of Done

- [x] Reservation and booking APIs implemented with timeout/conflict handling.
- [x] Preferred slot capture integrated.
- [x] Checkout UX complete for desktop and mobile.
- [x] Concurrency safeguards verified by tests.
- [x] Accessibility and validation behaviors complete.
- [x] AC-1 through AC-8 fully validated.

---

## 6. Suggested Execution Order

1. DB-1, DB-2, DB-3  
2. BE-1, BE-2, BE-3  
3. FE-1, FE-2, FE-4, FE-5, FE-6  
4. FE-3  
5. A11Y-1  
6. QA-1 through QA-5
