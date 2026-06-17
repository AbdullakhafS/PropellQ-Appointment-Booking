# Epic Decomposition: PropellQ Appointment Booking System

**Document Version:** 1.0  
**Date:** 2026-06-17  
**Status:** Draft  
**Source:** spec.md (22 Functional Requirements)

---

## Executive Summary

This document decomposes the 22 functional requirements from the specification into business-aligned epics and inferred technical epics. Each epic groups related requirements with clear business value, priority levels, and dependencies.

**Total Epics:** 10 (EP-001 through EP-008, EP-TECH-001, EP-DATA-001)  
**Total Requirements Mapped:** 22 FRs (100% coverage)  
**Estimated Delivery Timeline:** 6-9 months across 4 phases

---

## Epic Summary Table

| Epic ID | Epic Name | Priority | Business Value | Complexity | Mapped FRs | Est. Effort |
|---------|-----------|----------|-----------------|------------|-----------|------------|
| EP-001 | Patient Appointment Booking | CRITICAL | Very High | High | FR-001, FR-002, FR-003, FR-004 | 20 pts |
| EP-002 | Patient Intake & Insurance | HIGH | High | Very High | FR-005, FR-006 | 16 pts |
| EP-003 | Clinical Data Intelligence | CRITICAL | Very High | Very High | FR-007, FR-008, FR-009 | 24 pts |
| EP-004 | Appointment Operations & Queue | HIGH | High | High | FR-010, FR-011, FR-012, FR-013, FR-014 | 18 pts |
| EP-005 | User Access & Security | CRITICAL | High | Medium | FR-015, FR-016 | 10 pts |
| EP-006 | Patient Portal & Analytics | HIGH | Medium | Medium | FR-017, FR-018 | 12 pts |
| EP-007 | Compliance & Audit | CRITICAL | Very High | High | FR-019, FR-020 | 14 pts |
| EP-008 | System Reliability & Performance | CRITICAL | Very High | Very High | FR-021, FR-022 | 18 pts |
| EP-TECH-001 | Technical Foundation & DevEx | CRITICAL | Very High | High | NFR-001..NFR-009, TR-001..TR-008 | 12 pts |
| EP-DATA-001 | Data Platform & Governance | CRITICAL | Very High | High | DR-001..DR-004, NFR-004, NFR-006 | 10 pts |

---

## Epic Definitions

---

## EP-001: Patient Appointment Booking

**Priority:** CRITICAL  
**Business Value:** Very High  
**Complexity:** High  
**Timeline:** Months 1-2 (Phase 1 - Foundation)  

### Objective
Provide patients with an intuitive, mobile-responsive self-service appointment booking experience that reduces friction, prevents double-booking, and integrates seamlessly with external calendars.

### Mapped Functional Requirements

| FR ID | Requirement | Priority | Complexity |
|-------|-------------|----------|------------|
| FR-001 | Patient Self-Service Appointment Booking | CRITICAL | High |
| FR-002 | Dynamic Preferred Slot Swap | CRITICAL | Very High |
| FR-003 | Multi-Channel Appointment Reminders | CRITICAL | Medium |
| FR-004 | Calendar Integration (Google/Outlook) | HIGH | Medium |

### Business Outcomes

✓ Self-service booking reduces front-desk workload by 40%  
✓ Preferred slot swap differentiates from competitors  
✓ Multi-channel reminders reduce no-show rate by 15%+  
✓ Calendar integration increases adoption (embedded workflow)  

### Key Success Metrics

- Booking completion rate ≥90%
- Appointment confirmation sent within 60 seconds (100%)
- No double-booking incidents (SLA: 0)
- Calendar integration adoption ≥60% of users
- SMS delivery success rate ≥95%
- Email delivery success rate ≥99%

### Dependencies

- EP-005 (User Access & Security) - Authentication required
- EP-007 (Compliance & Audit) - HIPAA data handling required
- EP-008 (System Reliability) - 99.9% uptime required

### Use Cases Covered

- UC-001: Patient Searches & Books Appointment
- UC-002: Patient Receives Appointment Reminders
- UC-003: Patient Joins Waitlist or Uses Preferred Slot Swap
- UC-005: Patient Authorizes Calendar Integration

### Acceptance Criteria (Epic-Level)

- [ ] Patients can search and filter appointments (date, time, provider, specialty)
- [ ] Real-time calendar view shows available slots with visual blocking
- [ ] Booking confirmation sent via email (PDF) within 60 seconds
- [ ] Preferred slot swap logic monitors and automatically swaps slots
- [ ] Multi-channel reminders sent at 48h, 24h, 2h with ≥95% SMS, ≥99% email delivery
- [ ] Google Calendar and Outlook integration functional (OAuth 2.0)
- [ ] Bidirectional calendar sync (cancellations/reschedules reflected)
- [ ] Mobile-responsive design (375px, 768px, 1024px+ breakpoints)
- [ ] No double-booking scenarios occur
- [ ] Audit logging captures all booking and calendar events

### Estimated User Stories

- US-001: Search Appointments with Filters
- US-002: Display Appointment Slots with Calendar
- US-003: Select Appointment & Lock Slot During Checkout
- US-004: Send Confirmation Email (PDF) Within 60 Seconds
- US-005: Implement Preferred Slot Swap Logic
- US-006: Send Appointment Reminders (48h, 24h, 2h)
- US-007: Authorize Google Calendar Integration
- US-008: Authorize Outlook Integration
- US-009: Bidirectional Calendar Sync (External Updates)
- US-010: Mobile-Responsive Booking Experience

---

## EP-002: Patient Intake & Insurance Verification

**Priority:** HIGH  
**Business Value:** High  
**Complexity:** Very High  
**Timeline:** Months 2-3 (Phase 1 - Foundation)  

### Objective
Streamline pre-visit data collection through flexible AI-assisted or manual intake forms, with soft validation of insurance information to reduce claim denials and improve billing efficiency.

### Mapped Functional Requirements

| FR ID | Requirement | Priority | Complexity |
|-------|-------------|----------|------------|
| FR-005 | Flexible Patient Intake (AI-Assisted & Manual Fallback) | HIGH | Very High |
| FR-006 | Insurance Pre-Check (Soft Validation) | HIGH | Medium |

### Business Outcomes

✓ Intake completion rate ≥85% (vs. 40% industry average)  
✓ AI-assisted intake reduces data collection time from 20 min to 5 min  
✓ Soft insurance validation surfaces issues pre-appointment  
✓ Billing team can pre-verify before discharge  

### Key Success Metrics

- Intake completion rate ≥85% before appointment
- AI-assisted intake adoption ≥50% of patients
- AI response consistency ≥95% with manual form requirements
- Insurance pre-check identifies 70%+ of verification issues
- Patient satisfaction with intake experience ≥4.5/5.0

### Dependencies

- EP-001 (Appointment Booking) - Intake triggered post-booking
- EP-005 (User Access) - Patient authentication required
- EP-007 (Compliance) - HIPAA handling of medical data
- External AI/NLP Service - Chatbot engine

### Use Cases Covered

- UC-006: Patient Completes Intake (AI or Manual)
- UC-008: Insurance Pre-Check on Booking

### Acceptance Criteria (Epic-Level)

- [ ] AI chatbot collects chief complaint, medical history, medications, allergies
- [ ] Patients can switch between AI and manual intake modes
- [ ] Manual form auto-populates from previous visits (with consent)
- [ ] AI and manual modes capture identical required data
- [ ] Insurance information soft-checked against predefined database
- [ ] Unverified insurance flagged for post-appointment staff review
- [ ] Intake responses stored in structured + natural language formats
- [ ] Intake data displayed in patient's 360° profile
- [ ] Patient can edit responses anytime without assistance
- [ ] Audit logging captures all intake interactions

### Estimated User Stories

- US-011: Implement AI Chatbot Engine (NLP integration)
- US-012: Design Multi-Step Chatbot Conversation Flow
- US-013: Build Manual Intake Form with Auto-Population
- US-014: Enable Intake Mode Switching (AI ↔ Manual)
- US-015: Implement Insurance Pre-Check Logic
- US-016: Flag Unverified Insurance for Staff Review
- US-017: Store Intake Data in Structured Format
- US-018: Display Intake Responses in Patient Profile

---

## EP-003: Clinical Data Intelligence & Coding

**Priority:** CRITICAL  
**Business Value:** Very High  
**Complexity:** Very High  
**Timeline:** Months 3-5 (Phase 2 - Intelligence)  

### Objective
Build a unified 360° patient profile by aggregating pre-visit intake, uploaded documents, and clinical notes. Automatically extract and suggest ICD-10/CPT codes with high confidence scores. Detect and alert on critical data conflicts (drug-drug interactions, duplicate medications, etc.).

### Mapped Functional Requirements

| FR ID | Requirement | Priority | Complexity |
|-------|-------------|----------|------------|
| FR-007 | 360-Degree Patient Profile Construction | CRITICAL | Very High |
| FR-008 | ICD-10 & CPT Code Extraction & Mapping | CRITICAL | Very High |
| FR-009 | Critical Data Conflict Detection & Alerting | CRITICAL | High |

### Business Outcomes

✓ Reduce clinical prep time from 20 minutes to <5 minutes  
✓ AI coding achieves 98%+ agreement with human coders  
✓ Prevent safety incidents via allergy-drug interaction detection  
✓ Reduce claim denials from data conflicts  

### Key Success Metrics

- Clinical data extraction time reduced from 20 min to <5 min
- AI-Human Agreement Rate ≥98%
- Document processing time <60 seconds per upload
- Critical conflicts identified 100% (no false negatives)
- Staff conflict resolution time <2 minutes
- Allergy-drug interactions detected 100% (no misses)

### Dependencies

- EP-002 (Patient Intake) - Intake data feeds profiles
- EP-001 (Appointment Booking) - Triggered post-appointment
- EP-005 (User Access) - Staff access controls
- EP-007 (Compliance) - HIPAA audit logging
- External AI Services - Document extraction, drug database, ICD-10/CPT model
- External APIs - Allergy-drug interaction database

### Use Cases Covered

- UC-009: Clinical Staff Views 360° Patient Profile
- UC-010: Staff Reviews Pre-Visit Clinical Data
- UC-011: System Detects Data Conflicts
- UC-012: AI Suggests ICD-10/CPT Codes
- UC-013: Staff Verifies/Rejects Code Suggestions
- UC-014: Staff Resolves Data Conflicts

### Acceptance Criteria (Epic-Level)

- [ ] System ingests up to 100 documents per patient (configurable)
- [ ] Supports PDF, DOCX formats with <60 second processing
- [ ] Extracted data tagged with source, date, confidence score
- [ ] Duplicate/conflicting medications flagged prominently
- [ ] Allergy-drug interactions checked and flagged in real-time
- [ ] Patient profile displays consolidated medication/allergy lists
- [ ] ICD-10 suggestions include confidence scores (0-100%)
- [ ] CPT suggestions included confidence scores (0-100%)
- [ ] Suggestions ≥70% confidence auto-accepted; <70% flagged for review
- [ ] Critical conflicts block appointment confirmation (require override)
- [ ] Conflict acknowledgment audit-logged with staff signature
- [ ] All profile changes tracked in immutable audit trail
- [ ] Patient can view all source documents linked to extracted data

### Estimated User Stories

- US-019: Aggregate Patient Data from Intake & Documents
- US-020: Implement Document Upload & Processing
- US-021: Extract Structured Data from PDF/DOCX
- US-022: Build 360° Patient Profile UI (Tabs: Overview, Meds, Allergies, Diagnoses)
- US-023: Display Document Sources with Traceability
- US-024: Implement Medication Conflict Detection
- US-025: Implement Allergy-Drug Interaction Check
- US-026: Implement ICD-10 Code Suggestion Engine
- US-027: Implement CPT Code Suggestion Engine
- US-028: Build Code Verification UI (Accept/Reject/Override)
- US-029: Implement Confidence Score Thresholds
- US-030: Build Conflict Resolution UI (Side-by-Side Comparison)

---

## EP-004: Appointment Operations & Queue Management

**Priority:** HIGH  
**Business Value:** High  
**Complexity:** High  
**Timeline:** Months 2-4 (Phase 1-2)  

### Objective
Enable staff to create walk-in appointments, manage same-day queues with real-time visibility, check in patients, and handle waitlist management and cancellations/rescheduling.

### Mapped Functional Requirements

| FR ID | Requirement | Priority | Complexity |
|-------|-------------|----------|------------|
| FR-010 | Staff Walk-In Appointment Booking | HIGH | Medium |
| FR-011 | Same-Day Queue Management | HIGH | Medium |
| FR-012 | Patient Check-In Management (Staff-Only) | HIGH | Low |
| FR-013 | Appointment Waitlist Functionality | HIGH | Medium |
| FR-014 | Appointment Cancellation & Rescheduling | HIGH | Low |

### Business Outcomes

✓ Front-desk staff can create walk-ins in <2 minutes  
✓ Real-time queue visibility reduces patient wait confusion  
✓ Waitlist automation increases slot fill rate by 20%+  
✓ Cancellation tracking enables no-show analysis  

### Key Success Metrics

- Walk-in creation time <2 minutes
- Queue visibility in real-time (0 second latency)
- Waitlist-to-booking conversion rate ≥70%
- Average wait time <15 minutes
- Cancellation processing automated 100%
- Queue reordering reflects in staff portal immediately

### Dependencies

- EP-001 (Appointment Booking) - Upstream booking system
- EP-005 (User Access) - Staff authentication/RBAC
- EP-007 (Compliance) - Audit logging
- EP-008 (System Reliability) - Real-time queue updates

### Use Cases Covered

- UC-003: Patient Joins Waitlist or Preferred Slot Swap
- UC-015: Staff Creates Walk-In Appointment
- UC-016: Staff Manages Same-Day Queue
- UC-017: Staff Checks In Patient
- UC-019: Appointment Cancelled or Rescheduled

### Acceptance Criteria (Epic-Level)

- [ ] Staff can search for existing patients or create new records
- [ ] Walk-in appointments assigned to available slots
- [ ] Walk-in flagged in appointment records
- [ ] Queue displays all appointments and walk-ins for current day
- [ ] Staff can manually reorder queue (drag-and-drop or priority)
- [ ] Queue state persisted and real-time across all staff users
- [ ] Staff marks patients as "Arrived" (check-in)
- [ ] Check-in timestamp recorded and logged
- [ ] Wait time calculated from scheduled to actual start
- [ ] Patients can join waitlist when slots full
- [ ] Waitlist FIFO ordered by join date with priority adjustments
- [ ] First waitlisted patient auto-offered slot when available
- [ ] Patient has 30 minutes to accept/decline offer
- [ ] Patients can cancel/reschedule up to 24 hours before
- [ ] Cancellation triggers waitlist processing
- [ ] Rescheduling maintains preferred slot preference
- [ ] All queue, check-in, cancel, reschedule actions audit-logged

### Estimated User Stories

- US-031: Build Walk-In Booking UI (Search/Create Patient)
- US-032: Assign Walk-In to Available Slots
- US-033: Flag Walk-In Appointments
- US-034: Build Real-Time Queue Management UI
- US-035: Implement Drag-Drop Queue Reordering
- US-036: Display Queue Statistics (Wait Time, Patient Count)
- US-037: Implement Patient Check-In Workflow
- US-038: Record Check-In Timestamp & Status
- US-039: Implement Waitlist Join & Accept/Decline Flow
- US-040: Auto-Offer First Waitlist Patient
- US-041: Implement Cancellation/Reschedule Logic
- US-042: Implement Waitlist Processing on Slot Release

---

## EP-005: User Access & Role Management

**Priority:** CRITICAL  
**Business Value:** High  
**Complexity:** Medium  
**Timeline:** Month 1 (Phase 1 - Foundation)  

### Objective
Establish foundation for multi-user system with strict role-based access control (RBAC) for three roles: Patient, Staff, and Admin. Provide admin tools for user account management and lifecycle.

### Mapped Functional Requirements

| FR ID | Requirement | Priority | Complexity |
|-------|-------------|----------|------------|
| FR-015 | Role-Based Access Control (RBAC) | CRITICAL | Medium |
| FR-016 | User Account Management (Admin) | HIGH | Low |

### Business Outcomes

✓ Secure multi-role system foundation  
✓ Least-privilege access prevents unauthorized data access  
✓ Admin tools streamline staff onboarding/offboarding  
✓ Role-based audit logging enables compliance reporting  

### Key Success Metrics

- Zero unauthorized access incidents
- Role assignment completed in <5 minutes per user
- Session token generation <100ms
- Permission check latency <50ms per API call
- 100% of role changes audit-logged

### Dependencies

- None (foundation epic)

### Use Cases Covered

- UC-020: Admin Manages System Users
- UC-021: Staff/Admin Logs Into System

### Acceptance Criteria (Epic-Level)

- [ ] Three roles defined: Patient, Staff, Admin
- [ ] Each user assigned exactly one primary role
- [ ] Patient role can view/book appointments, manage intake, view own profile
- [ ] Staff role can create walk-ins, manage queue, check-in patients
- [ ] Admin role can manage users, configure settings, view analytics
- [ ] Staff cannot access patient data outside assigned providers
- [ ] Session tokens include role information
- [ ] All API calls enforce permission checks
- [ ] RBAC permission model documented
- [ ] Admins can create/deactivate staff accounts
- [ ] Password resets secure (email-based link)
- [ ] Admin can view user audit logs
- [ ] All role changes audit-logged
- [ ] Inactive accounts cannot log in

### Estimated User Stories

- US-043: Implement RBAC Permission Model
- US-044: Define Patient Role & Permissions
- US-045: Define Staff Role & Permissions
- US-046: Define Admin Role & Permissions
- US-047: Build User Account Management UI (Admin Only)
- US-048: Implement User Create/Edit/Deactivate
- US-049: Implement Secure Password Reset (Email Link)
- US-050: Add Permission Checks to All API Endpoints
- US-051: Implement Session Token with Role Info
- US-052: Build Admin User Audit Log Viewer

---

## EP-006: Patient Portal & Analytics

**Priority:** HIGH  
**Business Value:** Medium  
**Complexity:** Medium  
**Timeline:** Months 3-4 (Phase 2)  

### Objective
Provide patients with a personal dashboard to view upcoming/past appointments, manage health profiles, upload documents, and configure preferences. Provide admins with operational dashboards for KPI tracking and trend analysis.

### Mapped Functional Requirements

| FR ID | Requirement | Priority | Complexity |
|-------|-------------|----------|------------|
| FR-017 | Patient Dashboard & Profile Management | HIGH | Medium |
| FR-018 | Operational Dashboard & KPI Tracking | HIGH | Medium |

### Business Outcomes

✓ Patient engagement increases with self-service dashboard  
✓ Admins gain data-driven insights for optimization  
✓ KPI tracking enables proactive management  
✓ Analytics support continuous improvement  

### Key Success Metrics

- Patient dashboard load time <2 seconds
- Mobile-responsive on all breakpoints
- Dashboard auto-refresh every 5 minutes
- KPI data lag <5 minutes from real-time
- No-show rate trended (monthly baseline)
- AI-Human Agreement Rate tracked (accuracy metric)

### Dependencies

- EP-001 (Appointment Booking) - Appointments displayed
- EP-003 (Clinical Intelligence) - Health profile data
- EP-005 (User Access) - Patient/Admin authentication

### Use Cases Covered

- UC-022: Patient Views Dashboard & Profile
- UC-023: Admin Views Operational Dashboard

### Acceptance Criteria (Epic-Level)

- [ ] Patient dashboard displays upcoming appointments with reschedule/cancel options
- [ ] Patient dashboard displays past appointments with clinical notes (if released)
- [ ] Patient dashboard shows personal health profile (meds, allergies, diagnoses)
- [ ] Patient can upload new documents
- [ ] Patient can manage notification preferences (SMS/email)
- [ ] Patient dashboard is mobile-responsive (375px, 768px, 1024px+)
- [ ] Dashboard loads in <2 seconds
- [ ] Admin dashboard displays no-show rate and trends
- [ ] Admin dashboard displays average wait times
- [ ] Admin dashboard displays appointment utilization by provider/specialty
- [ ] Admin dashboard displays intake completion rates
- [ ] Admin dashboard displays insurance verification status
- [ ] Admin dashboard displays AI-Human Agreement Rate
- [ ] Dashboard auto-refreshes every 5 minutes
- [ ] Users can filter by date range, provider, location
- [ ] Reports exportable as CSV
- [ ] Admins can customize dashboard widgets

### Estimated User Stories

- US-053: Build Patient Dashboard UI
- US-054: Display Upcoming Appointments with Actions
- US-055: Display Past Appointments with Clinical Notes
- US-056: Display Personal Health Profile
- US-057: Enable Document Upload from Dashboard
- US-058: Enable Notification Preference Management
- US-059: Make Patient Dashboard Mobile-Responsive
- US-060: Build Admin Operational Dashboard UI
- US-061: Display No-Show Rate & Trends
- US-062: Display Average Wait Time Metrics
- US-063: Display Appointment Utilization Analytics
- US-064: Display Intake Completion Rates
- US-065: Display Insurance Verification Status
- US-066: Display AI-Human Agreement Rate
- US-067: Implement Dashboard Auto-Refresh (5 min)
- US-068: Implement Date/Provider/Location Filters
- US-069: Implement CSV Export for Reports

---

## EP-007: Compliance & Audit Logging

**Priority:** CRITICAL  
**Business Value:** Very High  
**Complexity:** High  
**Timeline:** Months 1-2 (Phase 1 - Foundation)  

### Objective
Implement comprehensive HIPAA-compliant data handling and immutable audit logging. All PHI encrypted at rest and in transit. All user actions logged with timestamp, user ID, action, data affected, and result. Logs retained for 7 years minimum.

### Mapped Functional Requirements

| FR ID | Requirement | Priority | Complexity |
|-------|-------------|----------|------------|
| FR-019 | HIPAA Compliance & Data Privacy | CRITICAL | Very High |
| FR-020 | Immutable Audit Logging | CRITICAL | Medium |

### Business Outcomes

✓ HIPAA compliance achieved (regulatory requirement)  
✓ BAA framework established for vendor management  
✓ Audit trail enables forensics and compliance reporting  
✓ Patient data protected against unauthorized access  

### Key Success Metrics

- Zero HIPAA violations (audit rate: 100%)
- All PHI encrypted at rest and in transit
- Audit logs retained for 7 years
- Immutability verified (no tampering detected)
- Session timeout enforced (15 minutes inactivity)
- Password hashing bcrypt 12+ rounds
- MFA available for staff/admin

### Dependencies

- None (foundation epic, integrates with all others)

### Use Cases Covered

- All use cases (HIPAA applies globally)

### Acceptance Criteria (Epic-Level)

- [ ] All databases encrypted with AES-256 managed keys
- [ ] All API traffic uses TLS 1.2+ with valid certificates
- [ ] Session tokens expire after 15 minutes inactivity
- [ ] Passwords hashed with bcrypt minimum 12 rounds
- [ ] Audit logs stored separately from operational database
- [ ] Each log entry: timestamp, user ID, role, action, data affected, result, IP
- [ ] Audit logs cannot be deleted (only archived after 7 years)
- [ ] Log integrity checking detects tampering (HMAC or append-only)
- [ ] Log queries require admin authorization
- [ ] Audit logs retained minimum 7 years per HIPAA
- [ ] Business Associate Agreements (BAA) for all vendors
- [ ] MFA available for staff/admin accounts
- [ ] Data retention/deletion policies documented
- [ ] Compliance audit checklist 100% satisfied

### Estimated User Stories

- US-070: Implement AES-256 Database Encryption
- US-071: Implement TLS 1.2+ for All API Traffic
- US-072: Implement Bcrypt Password Hashing
- US-073: Implement Session Timeout (15 min inactivity)
- US-074: Build Immutable Audit Log Infrastructure
- US-075: Log All User Actions (Login, Access, Changes)
- US-076: Implement Audit Log Retention (7 years)
- US-077: Implement Log Integrity Checking (HMAC)
- US-078: Build Audit Log Query Interface (Admin Only)
- US-079: Implement MFA Support (TOTP)
- US-080: Document Data Retention & Deletion Policies
- US-081: Create HIPAA Compliance Checklist
- US-082: Establish Vendor BAA Process

---

## EP-008: System Reliability & Performance

**Priority:** CRITICAL  
**Business Value:** Very High  
**Complexity:** Very High  
**Timeline:** Months 1-6 (Continuous, Phase 1-2)  

### Objective
Achieve 99.9% uptime through load balancing, database replication, health checks, and graceful degradation. Optimize key operations (booking, reminders) and support 10,000+ concurrent users with <500ms p95 response time.

### Mapped Functional Requirements

| FR ID | Requirement | Priority | Complexity |
|-------|-------------|----------|------------|
| FR-021 | 99.9% Uptime & High Availability | CRITICAL | Very High |
| FR-022 | Scalable Architecture & Performance | HIGH | High |

### Business Outcomes

✓ 99.9% uptime (max ~43 minutes/month downtime)  
✓ Sub-500ms response times for appointment booking  
✓ Supports growth to 10,000+ concurrent users  
✓ 70%+ cache hit rate reduces database load  

### Key Success Metrics

- API response time p95 <500ms, p99 <1000ms
- Database failover <30 seconds
- Load balancer health check detection <10 seconds
- Health checks run every 5 seconds
- Uptime 99.9% (monitored weekly)
- Cache hit rate ≥70%
- Database query p95 <100ms
- Concurrent user support ≥10,000

### Dependencies

- All other epics (performance is cross-cutting concern)

### Use Cases Covered

- All use cases (reliability applies globally)

### Acceptance Criteria (Epic-Level)

- [ ] Load balancer distributes traffic across 3+ API instances
- [ ] Database replication (Primary + Standby) with <30s failover
- [ ] Health checks run every 5 seconds
- [ ] Unhealthy instances removed from load balancer <10 seconds
- [ ] API is stateless and horizontally scalable
- [ ] Session data stored in Redis cache tier
- [ ] Reminder delivery uses async queues (non-blocking on booking)
- [ ] Database queries optimized with strategic indexes
- [ ] p95 database query response time <100ms
- [ ] p95 API response time <500ms, p99 <1000ms
- [ ] Graceful degradation: booking works even if analytics unavailable
- [ ] Caching strategy reduces database load by 70%+
- [ ] System supports 10,000+ concurrent users
- [ ] Uptime monitored and reported weekly
- [ ] Auto-scaling configured for traffic spikes
- [ ] Disaster recovery plan documented and tested

### Estimated User Stories

- US-083: Implement Load Balancer Configuration
- US-084: Implement Database Replication (Primary+Standby)
- US-085: Implement Automated Health Checks
- US-086: Implement Automatic Instance Removal on Failure
- US-087: Make API Stateless (No Local Storage)
- US-088: Implement Redis Session Cache
- US-089: Implement Async Queue for Reminders
- US-090: Optimize Database Queries with Indexes
- US-091: Implement Query Result Caching (Redis)
- US-092: Implement Graceful Degradation Pattern
- US-093: Implement Load Testing & Benchmarking
- US-094: Implement Uptime Monitoring & Alerting
- US-095: Implement Auto-Scaling Rules
- US-096: Document Disaster Recovery Plan
- US-097: Run Disaster Recovery Drill

---

## EP-TECH-001: Technical Foundation & DevEx [SOURCE:INFERRED]

**Priority:** CRITICAL  
**Business Value:** Very High  
**Complexity:** High  
**Timeline:** Months 1-2 (Phase 1 - Foundation)

### Objective
Establish cross-cutting technical foundations and developer experience capabilities required to deliver all feature epics predictably: architecture guardrails, observability, CI quality gates, resiliency defaults, API standards, and security baselines.

### Mapped Requirements

| Requirement ID | Requirement |
|----------------|-------------|
| NFR-001..NFR-009 | Availability, performance, scalability, security, maintainability, accessibility, interoperability |
| TR-001..TR-008 | Stack constraints, architecture patterns, API design, auth, async processing, caching, resilience |

### Dependencies

- Blocks EP-001..EP-008 implementation velocity and release confidence

### Acceptance Criteria (Epic-Level)

- [ ] CI pipeline enforces lint, unit tests, dependency checks, and security scans
- [ ] Standard API conventions documented (error envelope, pagination, versioning, idempotency)
- [ ] Centralized structured logging and distributed tracing enabled end-to-end
- [ ] Health checks/readiness/liveness probes implemented for all core services
- [ ] Baseline observability dashboards and alerts for uptime, latency, error rate, queue depth
- [ ] Environment configuration strategy documented and automated for dev/test/prod
- [ ] Reference architecture guardrails adopted by all feature teams

### Estimated User Stories

- US-098: Define API standards and shared middleware contracts
- US-099: Implement centralized logging + correlation IDs
- US-100: Implement tracing and SLO dashboards
- US-101: Add CI quality gates (lint, test, SAST/SCA)
- US-102: Implement resiliency defaults (timeouts, retries, circuit breakers)
- US-103: Standardize environment configuration and secret loading

---

## EP-DATA-001: Data Platform & Governance [SOURCE:INFERRED]

**Priority:** CRITICAL  
**Business Value:** Very High  
**Complexity:** High  
**Timeline:** Months 1-3 (Phase 1-2)

### Objective
Deliver a governed data foundation for transactional integrity, lifecycle management, query performance, retention, and auditability across operational and analytical workloads.

### Mapped Requirements

| Requirement ID | Requirement |
|----------------|-------------|
| DR-001..DR-004 | Data model, storage organization, retention lifecycle, data access/querying |
| NFR-004, NFR-006 | Data consistency/integrity and privacy/retention controls |

### Dependencies

- Supports EP-003 (Clinical Intelligence), EP-006 (Analytics), EP-007 (Compliance), EP-008 (Reliability)

### Acceptance Criteria (Epic-Level)

- [ ] Core schema and indexing strategy implemented for high-frequency appointment and profile queries
- [ ] Data retention/archive jobs implemented per policy (including immutable audit retention)
- [ ] Migration strategy established with rollback and forward-fix procedures
- [ ] Data quality checks implemented for critical clinical fields and coding data
- [ ] Read/write access patterns documented with performance budgets
- [ ] Backup, restore, and integrity validation runbooks verified

### Estimated User Stories

- US-104: Finalize production schema + index strategy
- US-105: Implement migration and rollback pipeline
- US-106: Implement retention/archive lifecycle jobs
- US-107: Implement data quality validation checks
- US-108: Build backup/restore automation and verification

---

## Dependency Matrix

```
EP-001 (Booking)
  ├─ EP-005 (User Access) - Authentication
  ├─ EP-007 (Compliance) - HIPAA handling
  └─ EP-008 (Reliability) - 99.9% uptime

EP-002 (Intake & Insurance)
  ├─ EP-001 (Booking) - Post-booking intake
  ├─ EP-005 (User Access)
  ├─ EP-007 (Compliance)
  └─ EP-008 (Reliability)

EP-003 (Clinical Intelligence)
  ├─ EP-002 (Intake) - Intake data feeds profiles
  ├─ EP-001 (Booking) - Post-appointment
  ├─ EP-005 (User Access)
  ├─ EP-007 (Compliance)
  └─ EP-008 (Reliability)

EP-004 (Operations & Queue)
  ├─ EP-001 (Booking) - Upstream system
  ├─ EP-005 (User Access)
  ├─ EP-007 (Compliance)
  └─ EP-008 (Reliability) - Real-time updates

EP-005 (User Access)
  └─ No dependencies (foundation)

EP-006 (Patient Portal & Analytics)
  ├─ EP-001 (Booking) - Appointments displayed
  ├─ EP-003 (Clinical) - Health profile data
  ├─ EP-005 (User Access)
  └─ EP-008 (Reliability)

EP-007 (Compliance)
  ├─ EP-TECH-001 (Technical Foundation) - Security and observability baseline
  ├─ EP-DATA-001 (Data Platform) - Retention and integrity controls
  └─ No dependencies (cross-cutting)

EP-008 (Reliability)
  ├─ EP-TECH-001 (Technical Foundation) - Resilience and platform controls
  ├─ EP-DATA-001 (Data Platform) - Replication and data integrity support
  └─ No dependencies (cross-cutting)

EP-TECH-001 (Technical Foundation)
  └─ No dependencies (foundational inferred epic)

EP-DATA-001 (Data Platform)
  ├─ EP-TECH-001 (Technical Foundation)
  └─ No additional dependencies
```

---

## Delivery Phases

### Phase 1: Foundation & Core Booking (Months 1-2)

**Epics:** EP-TECH-001, EP-DATA-001, EP-005, EP-007, EP-001, EP-004 (partial)

**Objectives:**
- User authentication and RBAC
- Technical platform baseline (CI gates, observability, API standards)
- Data platform baseline (schema/indexing, migration safety, retention jobs)
- HIPAA compliance and audit logging
- Patient self-service appointment booking
- Preferred slot swap
- Appointment reminders
- Walk-in booking and queue management

**Success Criteria:**
- Patients can book appointments
- Staff can manage queue and check-in patients
- Compliance audit passes
- 99.9% uptime achieved

### Phase 2: Intelligence & Optimization (Months 3-5)

**Epics:** EP-002, EP-003, EP-004 (completion), EP-006, EP-008

**Objectives:**
- AI-assisted patient intake
- Clinical data aggregation (360° profile)
- AI-powered ICD-10/CPT code suggestion
- Conflict detection and alerting
- Patient dashboard and analytics
- Performance optimization

**Success Criteria:**
- AI-Human Agreement Rate ≥98%
- No-show rate reduced by 15%+
- Clinical prep time reduced to <5 minutes
- Support 10,000+ concurrent users

### Phase 3: Advanced Features & Scale (Months 6-9)

**Epics:** Feature enhancements, optimization, scale-out

**Objectives:**
- Multi-clinic support (if needed)
- Advanced analytics and reporting
- Mobile app (iOS/Android)
- International language support (if needed)
- Advanced integrations

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| AI model accuracy <95% | High | Medium | Extensive training data, human verification requirement |
| Integration failures (Calendar, Insurance DB) | High | Low | Fallback modes, manual override options |
| Database replication lag | High | Low | Continuous monitoring, failover testing |
| HIPAA audit failure | Critical | Low | Early compliance review, external audit |
| Performance degradation at scale | High | Medium | Load testing, caching strategy, optimization |
| Staff adoption of new workflows | Medium | Medium | Training, UAT, change management |

---

## Success Metrics Summary

**Customer Metrics:**
- No-show rate reduced by 15%+ (from ~12% to ~10% or less)
- Patient booking satisfaction ≥4.5/5.0
- Clinical prep time reduced from 20 min to <5 min

**Quality Metrics:**
- AI-Human Agreement Rate ≥98%
- 99.9% system uptime (max ~43 min/month downtime)
- API response time p95 <500ms, p99 <1000ms
- Zero HIPAA violations

**Operational Metrics:**
- No double-booking incidents (SLA: 0)
- Appointment reminder delivery ≥95% SMS, ≥99% email
- Waitlist-to-booking conversion ≥70%
- Staff walk-in creation time <2 minutes

---

## Glossary

**Epic:** Large body of work that can be broken down into multiple user stories
**FR (Functional Requirement):** Specific feature or capability the system must provide
**UC (Use Case):** Sequence of actions describing how actors interact with the system
**RBAC:** Role-Based Access Control (limiting access based on user role)
**PHI:** Protected Health Information (patient data subject to HIPAA)
**HIPAA:** Health Insurance Portability and Accountability Act (US healthcare privacy law)
**BAA:** Business Associate Agreement (contract with healthcare vendors)
**ICD-10:** International Classification of Diseases (diagnosis coding standard)
**CPT:** Current Procedural Terminology (procedure coding standard)
**Uptime SLA:** Service Level Agreement for system availability (99.9% = max 43 min/month downtime)

---

**Epic Decomposition Status:** Complete & Ready for User Story Creation  
**Last Updated:** 2026-06-17  
**Version:** 1.0  

**Next Steps:**
1. Review epics with Product & Engineering leadership
2. Refine estimates and dependencies
3. Execute `/create-user-stories EP-TECH-001` and `/create-user-stories EP-DATA-001` first
4. Conduct backlog refinement sessions
5. Begin Sprint 1 planning with Phase 1 epics (EP-TECH-001, EP-DATA-001, EP-005, EP-007, EP-001)

