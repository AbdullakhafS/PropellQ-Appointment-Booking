# System Design Document: Unified Patient Access & Clinical Intelligence Platform

**Document Version:** 1.0  
**Date:** 2026-06-17  
**Status:** Draft  
**Source:** spec.md  
**Architecture Decision Record:** Architecture-001

---

## Table of Contents
1. [Non-Functional Requirements (NFRs)](#non-functional-requirements)
2. [Technical Requirements (TRs)](#technical-requirements)
3. [Data Requirements (DRs)](#data-requirements)
4. [Architecture Constraints & Assumptions](#architecture-constraints--assumptions)
5. [System Architecture](#system-architecture)
6. [Technology Stack](#technology-stack)
7. [Component Design](#component-design)
8. [Data Model & Database Schema](#data-model--database-schema)
9. [API Design & Integration](#api-design--integration)
10. [Security & Compliance Architecture](#security--compliance-architecture)
11. [Scalability & Performance Strategy](#scalability--performance-strategy)
12. [Deployment & Infrastructure](#deployment--infrastructure)
13. [Architecture Diagrams](#architecture-diagrams)

---

## Non-Functional Requirements (NFRs)

### NFR-001: Availability & Reliability
**Category:** Reliability  
**Criticality:** CRITICAL

**Requirement:**
System shall maintain 99.9% uptime (maximum ~43 minutes downtime per month) with fault tolerance for critical operations (appointment booking, reminders, clinical data access).

**Design Implications:**
- Database replication with automatic failover (RPO < 30 seconds, RTO < 30 seconds)
- Load-balanced API layer across multiple instances
- Health checks every 5 seconds with automatic instance restart
- Circuit breakers and graceful degradation for non-critical services
- No single point of failure (SPOF) in booking critical path

**Measurement:**
- Monthly uptime percentage tracked automatically
- Incident response SLA: P0 < 15 minutes, P1 < 1 hour
- Recovery time objective (RTO): 30 seconds max

---

### NFR-002: Response Time & Performance
**Category:** Performance  
**Criticality:** CRITICAL

**Requirement:**
API response times shall meet:
- p95: < 500ms
- p99: < 1000ms
- Booking operation completion: < 5 seconds (from submit to confirmation)
- Reminder delivery: < 60 seconds from trigger
- Document processing: < 60 seconds for upload to extraction
- Dashboard load time: < 2 seconds

**Design Implications:**
- Database query optimization with strategic indexing
- Redis caching layer for session data and frequently accessed information
- Asynchronous processing for reminders, document processing, and data extraction
- CDN for static assets (UI, images)
- Query optimization targeting < 100ms for 95th percentile
- Connection pooling and prepared statements
- Lazy loading of large patient profiles

**Measurement:**
- APM (Application Performance Monitoring) with percentile tracking
- Dashboard latency monitored per page and component
- API response time SLAs tracked per endpoint

---

### NFR-003: Scalability & Concurrency
**Category:** Scalability  
**Criticality:** HIGH

**Requirement:**
System shall support 10,000+ concurrent users with linear performance degradation as load increases.

**Design Implications:**
- Stateless API design enabling horizontal scaling
- Load balancing with session affinity (if needed) or distributed sessions
- Database connection pooling with configurable max connections
- Asynchronous queues for background jobs (reminders, document processing)
- Caching strategy reducing database load by 70%+
- Message queue (e.g., Redis Streams or similar) for decoupling services
- Rate limiting per API endpoint

**Measurement:**
- Load testing targeting 10,000 concurrent users
- Database connection utilization monitored
- Queue depth and processing time tracked

---

### NFR-004: Data Consistency & Integrity
**Category:** Data Integrity  
**Criticality:** CRITICAL

**Requirement:**
All data operations shall be ACID-compliant with no loss of appointment, clinical data, or audit information. Transactions shall be atomic and consistent.

**Design Implications:**
- Relational database (PostgreSQL/SQL Server) ensuring ACID compliance
- Transactional integrity for appointment booking (atomic: slot lock + appointment create + availability update)
- Foreign key constraints and referential integrity
- Optimistic locking for conflict detection (e.g., concurrent edits)
- Two-phase commit for distributed transactions (if applicable)
- Data validation at application and database layers

**Measurement:**
- Transaction rollback rate monitored
- Data validation errors tracked and investigated

---

### NFR-005: Security & Data Protection
**Category:** Security  
**Criticality:** CRITICAL

**Requirement:**
System shall enforce HIPAA-compliant data protection with encryption at rest and in transit, strict access control, and immutable audit logging.

**Design Implications:**
- Encryption at rest: AES-256 for all databases and file storage
- Encryption in transit: TLS 1.2+ for all HTTP connections
- Password hashing: bcrypt with minimum 12 rounds
- Multi-factor authentication (MFA) for staff/admin accounts
- Role-based access control (RBAC) with principle of least privilege
- Session management with 15-minute timeout
- Immutable audit logs (write-once, read-many)
- Secrets management (encrypted environment variables, key rotation)
- Data classification: Sensitive (PHI), Internal, Public

**Measurement:**
- Security audit logs reviewed monthly
- Vulnerability scanning during CI/CD
- Penetration testing annually
- HIPAA compliance checklist validation

---

### NFR-006: Data Privacy & Retention
**Category:** Privacy  
**Criticality:** CRITICAL

**Requirement:**
Personal health information (PHI) shall be retained according to HIPAA requirements with secure deletion of non-required data.

**Design Implications:**
- Data retention policies: Audit logs retained 7 years minimum, appointment records 3 years
- Secure deletion: Cryptographic erasure or multi-pass overwrite
- Consent management for data usage and integrations
- Privacy by design: Minimal data collection, data minimization
- Right to deletion: Patient can request data deletion (with legal holds)
- Data export capability for patient portability

**Measurement:**
- Data retention policy compliance verified quarterly
- Deletion audit trail maintained

---

### NFR-007: Maintainability & Supportability
**Category:** Operability  
**Criticality:** HIGH

**Requirement:**
System shall be maintainable with clear logging, monitoring, and diagnostics for operations teams.

**Design Implications:**
- Structured logging (JSON format) with correlation IDs for request tracing
- Centralized logging aggregation (e.g., ELK, CloudWatch)
- Application monitoring and alerting (APM)
- Error tracking and alerting (e.g., Sentry)
- Health check endpoints for deployment monitoring
- Standardized configuration management
- Documentation for deployment, troubleshooting, and operations

**Measurement:**
- MTTR (Mean Time To Repair) tracked
- Alert response time monitored
- Log retention and searchability verified

---

### NFR-008: Accessibility & Usability
**Category:** Usability  
**Criticality:** HIGH

**Requirement:**
Patient and staff interfaces shall comply with WCAG 2.2 Level AA accessibility standards and be intuitive for non-technical users.

**Design Implications:**
- Semantic HTML and ARIA attributes
- Keyboard navigation support
- Color contrast ratio ≥4.5:1 for text
- Alt text for images
- Screen reader compatibility
- Responsive design for mobile, tablet, desktop
- Internationalization (i18n) for multi-language support

**Measurement:**
- Automated accessibility testing in CI/CD
- Manual accessibility audit annually
- User feedback on usability

---

### NFR-009: Portability & Integration
**Category:** Interoperability  
**Criticality:** MEDIUM

**Requirement:**
System shall support integration with external calendar systems (Google, Outlook) and future EHR integrations through well-defined APIs.

**Design Implications:**
- REST API with JSON payloads
- OAuth 2.0 for third-party integrations
- Webhook support for event notifications
- API versioning strategy (URL-based or header-based)
- API documentation (OpenAPI/Swagger)
- SDK or client library availability

**Measurement:**
- API uptime tracked separately
- Integration test coverage
- API adoption by third parties

---

## Technical Requirements (TRs)

### TR-001: Technology Stack Constraints
**Requirement:**
System shall exclusively use free, open-source technologies for deployment. Paid cloud services (AWS, Azure, GCP) are explicitly prohibited.

**Design Decision:**
- **Frontend Hosting:** Netlify (free tier), Vercel (free tier), or GitHub Pages
- **Backend Hosting:** GitHub Codespaces, self-hosted on Windows Server with IIS
- **Database:** PostgreSQL (open-source) or SQL Server Express (free tier)
- **Cache:** Redis (open-source)
- **Messaging:** Redis Streams or RabbitMQ (open-source)
- **CI/CD:** GitHub Actions (free for public repos)

**Implications:**
- Self-hosted infrastructure on on-premise Windows Server
- No managed database services; self-managed PostgreSQL/SQL Server
- Storage on local file system or free S3-like alternatives (MinIO)
- No serverless or containerized orchestration (no Kubernetes)

---

### TR-002: Backend Architecture Pattern
**Requirement:**
Backend shall follow a layered architecture with clear separation of concerns enabling testability and maintainability.

**Design Decision:** Layered Architecture with Repository Pattern

**Layers:**
1. **Presentation Layer (API Controllers)**
   - ASP.NET Core Controllers or Minimal APIs
   - Request/Response DTOs
   - Input validation and error handling
   - CORS and authentication middleware

2. **Business Logic Layer (Services)**
   - Domain services (AppointmentService, PatientService, ClinicalDataService)
   - Business rule enforcement
   - Transaction orchestration
   - Cross-cutting concerns

3. **Data Access Layer (Repositories)**
   - Repository pattern for data access abstraction
   - Entity Framework Core or Dapper ORM
   - Query optimization and caching
   - Transaction management

4. **Domain Model**
   - Entities: Appointment, Patient, Provider, ClinicalData, AuditLog, etc.
   - Value objects: Money, TimeRange, MedicalCode, etc.
   - Domain events for event sourcing (optional)

**Benefits:**
- Clear separation of concerns
- Testability at each layer
- Flexibility in data store changes
- Reusability of business logic

---

### TR-003: Frontend Architecture Pattern
**Requirement:**
Frontend shall be built with a modern component-based architecture enabling scalability and code reuse.

**Design Decision:** React (recommended) or Angular with State Management

**Architecture:**
- **Presentation Components:** Functional components with hooks
- **Container Components:** Smart components managing state and side effects
- **State Management:** Redux or Context API for global state
- **Routing:** React Router for client-side routing
- **HTTP Client:** Axios or Fetch API with interceptors for auth
- **Build Tool:** Vite or Create React App for bundling

**Component Structure:**
```
src/
├── components/          # Reusable UI components
├── pages/              # Page-level components
├── hooks/              # Custom React hooks
├── services/           # API service calls
├── store/              # Redux state management
├── utils/              # Helper functions
└── styles/             # Global and component styles
```

**Benefits:**
- Component reusability
- Easier testing and debugging
- Clear data flow
- Scalable structure for growth

---

### TR-004: API Design & Communication
**Requirement:**
Backend APIs shall follow RESTful principles with clear contracts and versioning.

**Design Decision:**
- **Protocol:** HTTPS/TLS 1.2+
- **Format:** JSON for all request/response payloads
- **Versioning:** URL-based versioning (e.g., `/api/v1/appointments`)
- **Authentication:** Bearer token (JWT) in Authorization header
- **Response Format:** Consistent envelope with status, data, errors, and pagination
- **Error Handling:** Standard HTTP status codes with descriptive error messages

**API Response Envelope:**
```json
{
  "success": true,
  "status": 200,
  "data": { /* response payload */ },
  "errors": [],
  "timestamp": "2026-06-17T10:30:00Z",
  "requestId": "uuid"
}
```

**RESTful Endpoints:**
- GET /api/v1/appointments - List appointments
- POST /api/v1/appointments - Create appointment
- GET /api/v1/appointments/{id} - Get appointment details
- PATCH /api/v1/appointments/{id} - Update appointment
- DELETE /api/v1/appointments/{id} - Cancel appointment
- POST /api/v1/appointments/{id}/check-in - Mark as arrived
- Similar patterns for patients, providers, clinical data, etc.

---

### TR-005: Authentication & Authorization
**Requirement:**
System shall implement secure authentication with role-based access control.

**Design Decision:**
- **Authentication Method:** JWT (JSON Web Tokens) with refresh tokens
- **Session Management:** Refresh tokens valid for 7 days, access tokens valid for 1 hour
- **Authorization:** Role-based access control (RBAC) with permission matrix
- **MFA:** TOTP (Time-based One-Time Password) for staff/admin accounts
- **Session Timeout:** 15 minutes of inactivity

**Roles & Permissions:**
- **Patient:** Can book, view own appointments, upload documents, manage preferences
- **Staff:** Can create walk-ins, manage queue, check-in patients, review clinical data
- **Admin:** Can manage users, configure settings, view analytics

---

### TR-006: Asynchronous Processing
**Requirement:**
Long-running operations (reminders, document processing) shall be processed asynchronously to avoid blocking user requests.

**Design Decision:**
- **Job Queue:** Redis Streams or RabbitMQ for job queuing
- **Workers:** Background worker services (ASP.NET Core Background Service or similar)
- **Processing:** Event-driven architecture with retry logic and dead-letter queues
- **Examples:**
  - Reminder delivery jobs triggered 48h, 24h, 2h before appointment
  - Document processing jobs triggered on file upload
  - Data extraction and conflict detection jobs
  - Email/SMS delivery jobs

**Job Processing Flow:**
1. User action triggers job creation (e.g., document upload)
2. Job enqueued to Redis Streams
3. Background worker picks up job
4. Job processing with retry logic (3 retries on failure)
5. Job completion logged and status updated
6. Notification sent to user (optional)

---

### TR-007: Caching Strategy
**Requirement:**
System shall implement multi-layer caching to reduce database load and improve response times.

**Design Decision:**

**Cache Layers:**
1. **Browser Cache:** Static assets cached with ETags, 30-day expiration
2. **CDN Cache:** Static content cached at edge locations (optional)
3. **Application Cache (Redis):**
   - Session data: Stored in Redis with 15-minute TTL
   - User permissions: Cached for 5 minutes per user
   - Appointment availability: Cached for 30 seconds (near real-time)
   - Provider schedules: Cached for 1 hour
   - Patient profiles: Cached for 5 minutes
4. **Database Query Cache:** ORM-level query caching (Entity Framework Core)

**Cache Invalidation:**
- Time-based expiration (TTL) for most entries
- Event-based invalidation on data changes
- Manual cache clear for admin operations

**Cache Performance Target:**
- Cache hit rate > 70% for frequently accessed data
- Database load reduction of 70%+

---

### TR-008: Error Handling & Resilience
**Requirement:**
System shall gracefully handle errors and provide meaningful feedback to users and operations teams.

**Design Decision:**

**Error Handling Strategy:**
- **Try-Catch blocks** in all external API calls and database operations
- **Circuit Breaker pattern** for failing dependencies (max 3 failures, 30-second reset)
- **Retry logic** with exponential backoff (max 3 retries)
- **Fallback behavior** for non-critical services (e.g., analytics unavailable doesn't block booking)
- **Logging** of all errors with stack trace and context
- **Monitoring & Alerting** for critical errors

**Common Errors:**
- 400 Bad Request: Invalid input
- 401 Unauthorized: Missing or invalid authentication
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Resource not found
- 409 Conflict: Data conflict (e.g., appointment already booked)
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Unexpected server error
- 503 Service Unavailable: Database/external service down

---

## Data Requirements (DRs)

### DR-001: Data Model Overview
**Requirement:**
System shall store all patient, appointment, clinical, and audit data in a relational database with referential integrity.

**Core Entities:**
1. **User** - Patients, Staff, Admins
2. **Patient** - Patient profile and demographics
3. **Provider** - Healthcare provider information
4. **Appointment** - Appointment records with status tracking
5. **AppointmentSlot** - Available appointment slots
6. **ClinicalData** - Patient health information (medications, allergies, diagnoses)
7. **Document** - Patient-uploaded documents
8. **ExtractedData** - Data extracted from documents
9. **MedicalCode** - ICD-10 and CPT code mappings
10. **AuditLog** - Immutable audit trail

---

### DR-002: Data Storage & Organization
**Requirement:**
Patient health data shall be organized in a normalized database schema enabling efficient queries and analysis.

**Database Design Principles:**
- **Normalization:** Third normal form (3NF) to minimize data redundancy
- **Indexing:** Strategic indexes on frequently queried columns (patient_id, appointment_date, etc.)
- **Partitioning:** Large tables (AuditLog, Appointments) partitioned by date for performance
- **Backup Strategy:** Full backup daily, incremental backups hourly, 7-year retention
- **Replication:** Read replicas for reporting and analytics

**Key Tables & Indexes:**
- `users` - Indexed on email, username
- `appointments` - Indexed on patient_id, provider_id, appointment_date
- `audit_logs` - Indexed on user_id, action_type, created_at (append-only)
- `clinical_data` - Indexed on patient_id, data_type, created_at
- `documents` - Indexed on patient_id, upload_date

---

### DR-003: Data Retention & Lifecycle
**Requirement:**
Data shall be retained according to HIPAA and business requirements with secure deletion of expired data.

**Retention Schedule:**
- **Audit Logs:** 7 years (regulatory requirement)
- **Appointment Records:** 3 years
- **Patient Health Data:** Duration of patient relationship + 3 years
- **Deleted User Data:** 30-day grace period before permanent deletion
- **Temporary Data (sessions, cache):** Per TTL configuration
- **Document Files:** Duration of patient relationship + 3 years

**Deletion Strategy:**
- Soft delete (logical deletion) with "deleted_at" timestamp for 30 days
- Hard delete after 30-day grace period for non-audit data
- Cryptographic erasure of document files
- Audit trail preserved for deleted data (reference only)

---

### DR-004: Data Access & Querying
**Requirement:**
Clinical staff and admins shall have efficient query access to patient and operational data with HIPAA compliance.

**Query Patterns:**
- Patient lookup: By name, DOB, phone, insurance ID, email
- Appointment search: By date range, provider, status, patient
- Clinical data access: All data for patient with source linkage
- Audit log search: By user, action, date range, affected data
- Reporting queries: No-show rate, wait times, clinical accuracy metrics

**Performance Targets:**
- Patient lookup: < 100ms (with index)
- Appointment search: < 500ms (even with large date range)
- Clinical data assembly: < 1 second (for 360-degree profile)
- Report generation: < 5 seconds (even with large datasets)

---

## Architecture Constraints & Assumptions

### Constraints
1. **No Paid Cloud Services:** Must use free/open-source hosting only
2. **No Containerization:** Windows Server/IIS deployment, no Kubernetes
3. **No Serverless:** Lambda, Functions, etc. out of scope
4. **No Direct EHR Integration:** Patient data uploaded manually, not pulled from EHR
5. **Free Tier Limits:** API rate limits, storage, and bandwidth constraints of free hosting
6. **No Managed Services:** Self-manage database, cache, message queue

### Assumptions
1. **Single Clinic Deployment:** Initial version targets single clinic, not multi-tenant
2. **PostgreSQL Availability:** PostgreSQL or SQL Server Express installed on Windows Server
3. **Email/SMS Providers:** Third-party SMS (Twilio) and email (SendGrid) have free tiers
4. **Calendar API Access:** Google Calendar and Microsoft Graph APIs accessible from deployment
5. **Staff Technical Proficiency:** Staff comfortable with web-based portal (no legacy system required)
6. **Internet Connectivity:** Clinic has reliable internet for hosting and integrations

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                                 │
├─────────────────────────────────────────────────────────────────┤
│  • Patient Portal (React SPA) - Booking, Intake, Profile        │
│  • Staff Portal (React SPA) - Queue, Check-in, Clinical Data    │
│  • Admin Portal (React SPA) - User Mgmt, Settings, Analytics    │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTPS/TLS
┌─────────────────────────────────────────────────────────────────┐
│                     API GATEWAY / LOAD BALANCER                  │
├─────────────────────────────────────────────────────────────────┤
│  • Request routing and load balancing                            │
│  • SSL termination                                               │
│  • Rate limiting and DDoS protection                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     API LAYER (Multiple Instances)              │
├─────────────────────────────────────────────────────────────────┤
│  Instance 1:                                                     │
│  ├─ AppointmentController                                        │
│  ├─ PatientController                                            │
│  ├─ ClinicalDataController                                       │
│  ├─ ProviderController                                           │
│  └─ UserController                                               │
│                                                                  │
│  Instance 2: (Same as Instance 1)                               │
│  Instance 3: (Same as Instance 1)                               │
└─────────────────────────────────────────────────────────────────┘
            ↓                    ↓                    ↓
    ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
    │  SERVICE 1    │   │  SERVICE 2    │   │  SERVICE 3    │
    │  Business     │   │  Clinical     │   │  Data Access  │
    │  Logic        │   │  Data Service │   │  Service      │
    └───────────────┘   └───────────────┘   └───────────────┘
                              ↓ (Async Jobs)
    ┌──────────────────────────────────────────────────────────┐
    │  BACKGROUND WORKERS (Job Processing)                     │
    ├──────────────────────────────────────────────────────────┤
    │  • Reminder Delivery Worker                              │
    │  • Document Processing Worker                            │
    │  • Data Extraction Worker                                │
    │  • Email/SMS Delivery Worker                             │
    └──────────────────────────────────────────────────────────┘
                              ↓
    ┌────────────────┬──────────────────┬──────────────────────┐
    │  CACHE LAYER   │  MESSAGE QUEUE   │  FILE STORAGE        │
    │  (Redis)       │  (Redis Streams) │  (Local Filesystem)  │
    │                │                  │                      │
    │  - Sessions    │  - Reminder Jobs │  - Patient Documents │
    │  - Permissions │  - Doc Processing│  - Extracted Files   │
    │  - Availability│  - Email/SMS Jobs│  - Audit Logs (opt.) │
    └────────────────┴──────────────────┴──────────────────────┘
                              ↓
    ┌────────────────┬──────────────────┬──────────────────────┐
    │  DATABASE      │  AUDIT LOG DB    │  EXTERNAL SERVICES  │
    │  (PostgreSQL)  │  (Append-Only)   │                      │
    │                │                  │  - Google Calendar   │
    │  - Users       │  - All Actions   │  - Outlook Calendar  │
    │  - Patients    │  - PHI Access    │  - Twilio (SMS)      │
    │  - Appts       │  - Data Changes  │  - SendGrid (Email)  │
    │  - Clinical    │  - 7-year Reten.│  - NLP (Document AI) │
    │  - Documents   │                  │                      │
    └────────────────┴──────────────────┴──────────────────────┘
```

---

## Technology Stack

### Frontend
| Layer | Technology | Justification |
|-------|-----------|---------------|
| Framework | React 18+ | Modern, component-based, large ecosystem, free |
| Language | TypeScript | Type safety, better IDE support, catches errors early |
| State Mgmt | Redux + Redux Thunk | Predictable state, time-travel debugging, middleware for async |
| Routing | React Router v6 | Standard routing library for SPAs |
| HTTP Client | Axios | Promise-based, interceptors for auth, widely used |
| Styling | Tailwind CSS | Utility-first CSS, rapid development, responsive design |
| UI Components | Material-UI or shadcn/ui | Pre-built components, accessibility compliance |
| Build Tool | Vite | Fast dev server, optimized production build |
| Testing | Jest + React Testing Library | Unit and component testing |
| Deployment | Netlify or Vercel | Free tier, easy CI/CD, auto-deploys from GitHub |

### Backend
| Layer | Technology | Justification |
|-------|-----------|---------------|
| Framework | ASP.NET Core 8+ | Modern, performant, open-source, C# type safety |
| Language | C# | Strong typing, LINQ for data queries, mature ecosystem |
| API Style | Controllers + Minimal APIs | Clean separation of concerns, OpenAPI support |
| ORM | Entity Framework Core | Abstraction over database, LINQ queries, migrations |
| Validation | FluentValidation | Fluent syntax, reusable validators |
| Logging | Serilog | Structured logging, multiple sinks, JSON output |
| DI Container | Built-in Microsoft.Extensions.DependencyInjection | No external dependency |
| Background Jobs | Hangfire or custom HostedService | Job scheduling and execution |
| Testing | xUnit + Moq | Unit and integration testing |
| Deployment | IIS on Windows Server | Self-hosted, no managed services |

### Data Layer
| Component | Technology | Justification |
|-----------|-----------|---------------|
| Primary DB | PostgreSQL 14+ | Free, open-source, ACID-compliant, powerful JSON support |
| Cache | Redis 7+ | In-memory caching, session storage, message queue |
| Message Queue | Redis Streams | Built into Redis, simple pub/sub, at-least-once delivery |
| Full-Text Search | PostgreSQL FTS or Elasticsearch (optional) | Patient search optimization |
| Backup | PostgreSQL pg_dump + custom scripts | Free, built-in tools |

### Infrastructure & DevOps
| Component | Technology | Justification |
|-----------|-----------|---------------|
| Hosting | Windows Server (on-premise) + IIS | Free tier, self-managed |
| CI/CD | GitHub Actions | Free for public repos, native to GitHub |
| Secrets Mgmt | Environment variables (encrypted) | Free, simple, integrates with deployment |
| Monitoring | Application Insights or open-source (Prometheus + Grafana) | Performance tracking, alerts |
| Error Tracking | Sentry (free tier) | Error capture and notification |
| DNS | Free DNS provider (Cloudflare, Route53 free tier) | Domain resolution |

### Third-Party Integrations (Free Tiers)
| Service | Purpose | Free Tier |
|---------|---------|-----------|
| Google Calendar API | Calendar sync | Free for development |
| Microsoft Graph (Outlook) | Calendar sync | Free for development |
| Twilio | SMS reminders | Free trial + pay-as-you-go |
| SendGrid | Email reminders | 100 emails/day free tier |
| OpenAI (GPT-4) | Clinical coding AI | Pay-as-you-go (optional) |

---

## Component Design

### Core Services Architecture

#### 1. Appointment Service
**Responsibilities:**
- Book/reschedule/cancel appointments
- Manage appointment slots and availability
- Enforce business rules (no double-booking, scheduling conflicts)
- Coordinate with reminder service
- Manage preferred slot swap logic

**Key Methods:**
```csharp
public interface IAppointmentService
{
    Task<Appointment> BookAppointment(BookingRequest request);
    Task<Appointment> RescheduleAppointment(string appointmentId, DateTime newDateTime);
    Task CancelAppointment(string appointmentId, string reason);
    Task CheckInPatient(string appointmentId);
    Task<List<AvailableSlot>> GetAvailableSlots(DateTime startDate, DateTime endDate, string providerId);
    Task ProcessPreferredSlotSwap(string appointmentId, DateTime preferredDateTime);
}
```

#### 2. Clinical Data Service
**Responsibilities:**
- Aggregate patient health data from intake, documents, visits
- Extract structured data (ICD-10, CPT, vitals, medications)
- Detect and resolve data conflicts
- Maintain 360-degree patient profile
- Generate medical coding suggestions

**Key Methods:**
```csharp
public interface IClinicalDataService
{
    Task<PatientProfile> GetPatientProfile(string patientId);
    Task<ExtractedData> ProcessDocument(string patientId, Stream documentContent);
    Task<List<DataConflict>> DetectConflicts(string patientId);
    Task<ResolvedConflict> ResolveConflict(string conflictId, ResolutionType resolution);
    Task<List<MedicalCodeSuggestion>> SuggestICD10Codes(string patientId);
    Task<List<MedicalCodeSuggestion>> SuggestCPTCodes(string patientId);
}
```

#### 3. Reminder Service
**Responsibilities:**
- Schedule appointment reminders (48h, 24h, 2h before)
- Execute reminder delivery via SMS and email
- Track delivery status and retry failed attempts
- Update patient preferences

**Key Methods:**
```csharp
public interface IReminderService
{
    Task ScheduleReminders(string appointmentId);
    Task SendReminder(string appointmentId, ReminderType type);
    Task RetryFailedReminder(string reminderId);
    Task UpdateReminderPreferences(string patientId, ReminderPreferences prefs);
}
```

#### 4. Patient Service
**Responsibilities:**
- Manage patient profiles and registration
- Update patient contact information
- Handle intake form submission
- Manage patient document uploads
- Track patient communication preferences

**Key Methods:**
```csharp
public interface IPatientService
{
    Task<Patient> RegisterPatient(PatientRegistration registration);
    Task<Patient> GetPatientById(string patientId);
    Task<Patient> GetPatientByEmail(string email);
    Task UpdatePatient(string patientId, PatientUpdate update);
    Task UploadDocument(string patientId, DocumentUpload document);
    Task<List<Document>> GetPatientDocuments(string patientId);
}
```

#### 5. User & Authentication Service
**Responsibilities:**
- User authentication and JWT token generation
- Role-based access control
- User account management
- Session management
- MFA (TOTP) enrollment and verification

**Key Methods:**
```csharp
public interface IAuthenticationService
{
    Task<AuthResponse> Login(LoginRequest request);
    Task<AuthResponse> RefreshToken(string refreshToken);
    Task Logout(string userId);
    Task<User> GetCurrentUser(ClaimsPrincipal principal);
    Task EnrollMFA(string userId);
    Task<AuthResponse> VerifyMFA(string userId, string totp);
}
```

### Background Jobs (Workers)

#### 1. Reminder Delivery Worker
- Triggered by cron job or event (appointment created, 48h before)
- Sends SMS and email reminders
- Retries failed deliveries up to 3 times
- Logs delivery status for audit

#### 2. Document Processing Worker
- Triggered by document upload event
- Performs OCR (if PDF image)
- Extracts structured data (vitals, meds, allergies, diagnoses)
- Detects conflicts with existing patient data
- Tags data with confidence scores

#### 3. Data Extraction Worker
- Processes extracted data from documents
- Maps diagnoses to ICD-10 codes
- Maps procedures to CPT codes
- Generates AI confidence scores
- Updates patient profile incrementally

#### 4. Email/SMS Delivery Worker
- Executes actual SMS/email sends via Twilio/SendGrid
- Handles rate limiting
- Retries on provider errors
- Logs delivery status

---

## Data Model & Database Schema

### Entity-Relationship Diagram (Conceptual)

```
┌──────────────────┐          ┌──────────────────┐
│      User        │          │     Patient      │
├──────────────────┤          ├──────────────────┤
│ UserId (PK)      │◄────────►│ PatientId (PK)   │
│ Email            │ 1       *│ UserId (FK)      │
│ PasswordHash     │          │ FirstName        │
│ Role             │          │ LastName         │
│ MFAEnabled       │          │ DOB              │
│ CreatedAt        │          │ InsuranceId      │
│ UpdatedAt        │          │ CreatedAt        │
└──────────────────┘          └──────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
        ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
        │ Appointment      │ │ ClinicalData     │ │ Document         │
        ├──────────────────┤ ├──────────────────┤ ├──────────────────┤
        │ AppointmentId(PK)│ │ ClinicalDataId(P)│ │ DocumentId (PK)  │
        │ PatientId (FK)   │ │ PatientId (FK)   │ │ PatientId (FK)   │
        │ ProviderId (FK)  │ │ DataType         │ │ DocumentType     │
        │ StartDateTime    │ │ Value            │ │ ContentType      │
        │ EndDateTime      │ │ SourceDocument   │ │ FilePath         │
        │ Status           │ │ ConfidenceScore  │ │ UploadedAt       │
        │ CreatedAt        │ │ VerifiedBy       │ │ Size             │
        │ UpdatedAt        │ │ VerifiedAt       │ │ Deleted          │
        └──────────────────┘ │ CreatedAt        │ └──────────────────┘
                              │ UpdatedAt        │
                              └──────────────────┘

┌──────────────────┐          ┌──────────────────┐
│    Provider      │          │  AppointmentSlot │
├──────────────────┤          ├──────────────────┤
│ ProviderId (PK)  │◄────────►│ SlotId (PK)      │
│ FirstName        │ 1       *│ ProviderId (FK)  │
│ LastName         │          │ StartDateTime    │
│ Specialty        │          │ IsAvailable      │
│ Bio              │          │ CreatedAt        │
│ CreatedAt        │          └──────────────────┘
└──────────────────┘

┌──────────────────┐          ┌──────────────────┐
│   MedicalCode    │          │  AuditLog        │
├──────────────────┤          ├──────────────────┤
│ CodeId (PK)      │          │ AuditLogId (PK)  │
│ PatientId (FK)   │          │ UserId (FK)      │
│ CodeType         │          │ Action           │
│ CodeValue        │          │ EntityType       │
│ Description      │          │ EntityId         │
│ ConfidenceScore  │          │ OldValue         │
│ VerifiedBy       │          │ NewValue         │
│ VerifiedAt       │          │ CreatedAt        │
│ CreatedAt        │          │ IpAddress        │
└──────────────────┘          └──────────────────┘
```

### Key Tables & Schemas

#### Users Table
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('Patient', 'Staff', 'Admin')),
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_role (role)
);
```

#### Appointments Table
```sql
CREATE TABLE appointments (
    appointment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    provider_id UUID NOT NULL REFERENCES providers(provider_id),
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('Scheduled', 'Arrived', 'Completed', 'Cancelled')),
    cancellation_reason VARCHAR(500),
    cancelled_at TIMESTAMP,
    cancelled_by_user_id UUID REFERENCES users(user_id),
    preferred_slot_datetime TIMESTAMP,
    swapped_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_patient_id (patient_id),
    INDEX idx_provider_id (provider_id),
    INDEX idx_start_datetime (start_datetime),
    INDEX idx_status (status)
);
```

#### Audit Logs Table (Immutable, Append-Only)
```sql
CREATE TABLE audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- No update_at or delete, audit logs are immutable
    INDEX idx_user_id (user_id),
    INDEX idx_entity_type (entity_type),
    INDEX idx_created_at (created_at)
) PARTITION BY RANGE (created_at);  -- Partitioned by date for performance
```

---

## API Design & Integration

### RESTful API Endpoints

#### Appointment Management
```
POST   /api/v1/appointments                    - Create appointment
GET    /api/v1/appointments                    - List appointments (filtered)
GET    /api/v1/appointments/{appointmentId}   - Get appointment details
PATCH  /api/v1/appointments/{appointmentId}   - Update appointment
DELETE /api/v1/appointments/{appointmentId}   - Cancel appointment
POST   /api/v1/appointments/{appointmentId}/check-in      - Mark as arrived
POST   /api/v1/appointments/{appointmentId}/swap-preferred - Execute preferred slot swap
GET    /api/v1/slots/available                - Get available slots (filtered)
```

#### Patient Management
```
POST   /api/v1/patients                        - Register patient
GET    /api/v1/patients/{patientId}           - Get patient details
PATCH  /api/v1/patients/{patientId}           - Update patient
GET    /api/v1/patients/{patientId}/profile   - Get 360-degree profile
POST   /api/v1/patients/{patientId}/documents - Upload document
GET    /api/v1/patients/{patientId}/documents - List patient documents
```

#### Clinical Data
```
GET    /api/v1/patients/{patientId}/clinical-data       - Get clinical data
GET    /api/v1/patients/{patientId}/conflicts           - Get data conflicts
PATCH  /api/v1/patients/{patientId}/conflicts/{id}      - Resolve conflict
GET    /api/v1/patients/{patientId}/medical-codes       - Get suggested codes
POST   /api/v1/patients/{patientId}/medical-codes       - Finalize codes
```

#### Authentication
```
POST   /api/v1/auth/login                     - User login (returns JWT)
POST   /api/v1/auth/refresh                   - Refresh access token
POST   /api/v1/auth/logout                    - Logout
POST   /api/v1/auth/mfa/enroll                - Enroll MFA
POST   /api/v1/auth/mfa/verify                - Verify MFA code
```

### Third-Party API Integration

#### Google Calendar Integration
- **OAuth 2.0 Flow:** Authorize user account
- **Sync:** On appointment creation, create calendar event
- **Watch:** Monitor for external calendar changes, sync back to PropellQ
- **Error Handling:** Gracefully degrade if authorization fails

#### Twilio SMS Integration
- **Endpoint:** Send SMS reminders via Twilio API
- **Rate Limiting:** Respect Twilio sending limits
- **Retry Logic:** Retry 3 times on failure
- **Logging:** Log all SMS sends for audit

#### SendGrid Email Integration
- **Endpoint:** Send email confirmations and reminders
- **Templates:** Use SendGrid templates for consistent formatting
- **Bounce Handling:** Update invalid emails
- **Logging:** Log all email sends

---

## Security & Compliance Architecture

### HIPAA Compliance Controls

#### Authentication & Access Control
- **Multi-Factor Authentication (MFA):** TOTP-based MFA for staff/admin accounts
- **Role-Based Access Control (RBAC):** Minimum privileges per role
- **Session Management:** 15-minute timeout with automatic logout
- **Password Policy:** Minimum 12 characters, complexity requirements, rotation every 90 days
- **Audit Logging:** All user actions logged with user ID, timestamp, action, data accessed

#### Data Protection
- **Encryption at Rest:** AES-256 for databases, sensitive files
- **Encryption in Transit:** TLS 1.2+ for all network communication
- **Key Management:** Secure key storage, no hardcoded secrets
- **Data Anonymization:** Patient names/PHI removed for testing and development
- **Secure Deletion:** Cryptographic erasure or multi-pass overwrite (NIST SP 800-88)

#### Audit & Compliance
- **Immutable Audit Logs:** Write-once, read-many storage for all actions
- **Audit Trail:** 7-year retention for all audit logs
- **PHI Access Logging:** Every access to patient data logged
- **Compliance Reports:** Generate audit reports for regulatory reviews
- **Business Associate Agreement (BAA):** Required for all third-party services

### Security Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    PERIMETER SECURITY                    │
├─────────────────────────────────────────────────────────┤
│  • Firewall rules (allow HTTPS only)                     │
│  • Network segmentation                                  │
│  • DDoS protection (at ISP or edge)                      │
│  • Rate limiting on all API endpoints                    │
└─────────────────────────────────────────────────────────┘
                          ↓ HTTPS/TLS 1.2+
┌─────────────────────────────────────────────────────────┐
│                    TRANSPORT SECURITY                    │
├─────────────────────────────────────────────────────────┤
│  • TLS 1.2+ certificates (auto-renewed)                 │
│  • HSTS headers (force HTTPS)                           │
│  • Certificate pinning (optional for mobile)            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 AUTHENTICATION & AUTHZ                   │
├─────────────────────────────────────────────────────────┤
│  • JWT tokens with 1-hour expiration                    │
│  • Refresh tokens with 7-day expiration                 │
│  • TOTP-based MFA for staff/admin                       │
│  • RBAC permission matrix enforcement                   │
│  • Session timeout after 15 minutes inactivity          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              APPLICATION-LEVEL SECURITY                  │
├─────────────────────────────────────────────────────────┤
│  • Input validation (whitelist, sanitize)               │
│  • SQL injection prevention (parameterized queries)     │
│  • CSRF protection (token-based)                        │
│  • XSS prevention (HTML encoding, CSP headers)          │
│  • API rate limiting per endpoint                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              DATA-LEVEL SECURITY                         │
├─────────────────────────────────────────────────────────┤
│  • AES-256 encryption at rest                           │
│  • Field-level encryption for sensitive data            │
│  • Database access controls (read replicas for reports) │
│  • Secrets management (encrypted env vars)              │
│  • Data masking in logs and error messages              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              AUDIT & COMPLIANCE                          │
├─────────────────────────────────────────────────────────┤
│  • Immutable audit logs (append-only)                   │
│  • All PHI access logged                                │
│  • Failed login attempts logged                         │
│  • Administrative actions logged                        │
│  • 7-year retention for compliance                      │
└─────────────────────────────────────────────────────────┘
```

---

## Scalability & Performance Strategy

### Horizontal Scalability

#### Stateless API Design
- No session state stored in API instance
- Session data stored in Redis (shareable across instances)
- Load balancer routes requests to available instances
- Instances can be added/removed dynamically

#### Database Optimization
- **Query Optimization:** EXPLAIN ANALYZE all queries, add indexes strategically
- **Connection Pooling:** Max 20-50 connections per instance
- **Read Replicas:** Async read replicas for reporting queries
- **Caching:** Redis caching reduces database load by 70%+
- **Partitioning:** Large tables (Appointments, AuditLogs) partitioned by date

#### Asynchronous Processing
- Long-running operations moved to background workers
- Job queues (Redis Streams) decouple request processing
- Workers scale independently based on queue depth
- No blocking on reminder delivery, document processing, etc.

### Performance Monitoring

#### Key Metrics
- **Response Time Percentiles:** p50, p95, p99 tracked per endpoint
- **Database Query Performance:** Query execution time, slow query log
- **Cache Hit Rate:** Target >70% for frequently accessed data
- **Queue Depth:** Monitor job queue length for scaling signals
- **Resource Utilization:** CPU, memory, disk usage, connection count

#### Alerting
- **Critical:** API latency p99 > 2 seconds
- **Critical:** Error rate > 1%
- **High:** Database connections > 80% capacity
- **High:** Redis memory > 80% capacity
- **Medium:** Cache hit rate < 50%

---

## Deployment & Infrastructure

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│  DEVELOPMENT                                             │
│  • Local development environment                        │
│  • npm/dotnet local dev server                          │
│  • Local PostgreSQL + Redis                             │
└─────────────────────────────────────────────────────────┘
         ↓ Git push to feature branch
┌─────────────────────────────────────────────────────────┐
│  CONTINUOUS INTEGRATION (GitHub Actions)                │
│  ├─ Code checkout and build                            │
│  ├─ Unit tests + code coverage                         │
│  ├─ Static analysis (SonarQube, ESLint)                │
│  ├─ Security scanning (SAST, dependency check)         │
│  └─ Build artifacts (Docker image or ZIP)              │
└─────────────────────────────────────────────────────────┘
         ↓ Pull request and manual review
┌─────────────────────────────────────────────────────────┐
│  STAGING ENVIRONMENT                                     │
│  • Production-like environment                          │
│  • Full integration tests                               │
│  • Performance/load testing                             │
│  • Security penetration testing                         │
│  • UAT with stakeholders                                │
└─────────────────────────────────────────────────────────┘
         ↓ Approval to merge to main
┌─────────────────────────────────────────────────────────┐
│  PRODUCTION ENVIRONMENT (Windows Server + IIS)          │
│  • Load balancer routes traffic                         │
│  • Multiple API instances (N+1 redundancy)              │
│  • PostgreSQL database (primary + read replicas)        │
│  • Redis cache + message queue                          │
│  • Health checks and auto-restart                       │
└─────────────────────────────────────────────────────────┘
```

### Infrastructure Components

#### Load Balancer
- **Role:** Route incoming requests to multiple API instances
- **Health Checks:** Every 5 seconds, mark unhealthy instances as down
- **Session Persistence:** Optional sticky sessions or distributed sessions via Redis
- **SSL Termination:** Decrypt HTTPS, communicate with backend via HTTP (internal)

#### API Instances (N ≥ 3)
- **Count:** Minimum 3 instances for N+1 redundancy (lose 1, system still operational)
- **Health Status:** Monitored continuously, auto-restart on failure
- **Scaling:** Add instances when CPU > 70% or queue depth > threshold
- **Resources:** 2 CPU cores, 4 GB RAM per instance (baseline)

#### Database (PostgreSQL)
- **Primary:** Read/write primary instance with automated backups
- **Replication:** Async replication to standby instance
- **Failover:** Manual or automatic failover to standby on primary failure
- **Backup:** Daily full backup + hourly incremental backup (7-year retention for audit logs)
- **Recovery:** Test backup recovery procedure monthly

#### Cache & Message Queue (Redis)
- **Redis Primary:** Stores sessions, cache data, message queues
- **Replication:** Async replication to Redis standby
- **Persistence:** RDB snapshots (append-only file optional for durability)
- **Memory:** Size Redis to hold 24 hours of session data + cache

#### File Storage
- **Location:** Local filesystem on server with regular backup
- **Patient Documents:** Encrypted, segregated by patient ID
- **Backup:** Copied to external storage daily (7-year retention for clinical documents)
- **Recovery:** Test file recovery procedure monthly

### Deployment Process

#### Release Procedure
1. **Code Freeze:** Branch cut 1 week before release
2. **Final Testing:** All tests pass on release branch
3. **Staging Deploy:** Deploy release candidate to staging
4. **UAT:** Business users validate on staging
5. **Go/No-Go Meeting:** Team reviews readiness
6. **Production Deploy:** Rolling deploy to update API instances one at a time
7. **Post-Deploy Monitoring:** 1-hour intensive monitoring for errors/issues
8. **Rollback Plan:** If critical issues, automatic or manual rollback to previous version

#### Rollback Procedure
- Keep N+1 versions deployed (current + 1 previous)
- Load balancer can switch traffic to previous version
- Database migrations must be backwards compatible (or have rollback scripts)
- Secrets/configuration rollback via environment variables

---

## Architecture Diagrams

### Deployment Topology Diagram

```puml
@startuml deployment-diagram
title PropellQ Deployment Topology

component "Client Layer" {
    component PatientPortal [Patient Portal\n(React SPA)]
    component StaffPortal [Staff Portal\n(React SPA)]
    component AdminPortal [Admin Portal\n(React SPA)]
}

component "CDN / Static Hosting" {
    component NetlifyHost [Netlify\n(Frontend Hosting)]
}

cloud "Internet" {
}

component "Server Infrastructure (Windows Server + IIS)" {
    component LoadBalancer [Load Balancer\n(IIS URL Rewrite)]
    
    component "API Instances (N+1)" {
        component APIInstance1 [API Instance 1\n(.NET Core on IIS)]
        component APIInstance2 [API Instance 2\n(.NET Core on IIS)]
        component APIInstance3 [API Instance 3\n(.NET Core on IIS)]
    }
    
    component "Data Layer" {
        database PostgreSQLPrimary [PostgreSQL Primary\n(Read/Write)]
        database PostgreSQLStandby [PostgreSQL Standby\n(Replication)]
        component RedisPrimary [Redis Primary\n(Sessions, Cache)]
        component RedisStandby [Redis Standby\n(Replication)]
    }
    
    component "Storage" {
        component FileStorage [File Storage\n(Patient Documents,\nEncrypted)]
        component BackupStorage [Backup Storage\n(Daily Snapshots)]
    }
    
    component "Background Workers" {
        component ReminderWorker [Reminder Worker]
        component DocumentWorker [Document Processing Worker]
        component ExtractionWorker [Data Extraction Worker]
    }
}

PatientPortal --> NetlifyHost
StaffPortal --> NetlifyHost
AdminPortal --> NetlifyHost

NetlifyHost --> Internet
Internet --> LoadBalancer

LoadBalancer --> APIInstance1
LoadBalancer --> APIInstance2
LoadBalancer --> APIInstance3

APIInstance1 --> PostgreSQLPrimary
APIInstance2 --> PostgreSQLPrimary
APIInstance3 --> PostgreSQLPrimary

PostgreSQLPrimary --> PostgreSQLStandby

APIInstance1 --> RedisPrimary
APIInstance2 --> RedisPrimary
APIInstance3 --> RedisPrimary

RedisPrimary --> RedisStandby

APIInstance1 --> FileStorage
APIInstance2 --> FileStorage
APIInstance3 --> FileStorage

FileStorage --> BackupStorage

ReminderWorker --> RedisPrimary
DocumentWorker --> RedisPrimary
ExtractionWorker --> RedisPrimary

ReminderWorker --> PostgreSQLPrimary
DocumentWorker --> PostgreSQLPrimary
ExtractionWorker --> PostgreSQLPrimary

@enduml
```

### System Component Diagram

```puml
@startuml component-diagram
title PropellQ System Components

package "Presentation Layer" {
    component PatientUI [Patient Portal UI]
    component StaffUI [Staff Portal UI]
    component AdminUI [Admin Portal UI]
}

package "API Layer" {
    component AuthController [Auth Controller]
    component AppointmentController [Appointment Controller]
    component PatientController [Patient Controller]
    component ClinicalController [Clinical Data Controller]
    component ProviderController [Provider Controller]
    component UserController [User Controller]
}

package "Business Logic Layer" {
    component AppointmentService [Appointment Service]
    component PatientService [Patient Service]
    component ClinicalDataService [Clinical Data Service]
    component AuthService [Auth Service]
    component ReminderService [Reminder Service]
}

package "Data Access Layer" {
    component AppointmentRepository [Appointment Repository]
    component PatientRepository [Patient Repository]
    component ClinicalRepository [Clinical Data Repository]
    component UserRepository [User Repository]
    component AuditRepository [Audit Log Repository]
}

package "Infrastructure & External" {
    component Database [PostgreSQL]
    component Cache [Redis]
    component MessageQueue [Redis Streams]
    component EmailService [SendGrid]
    component SMSService [Twilio]
    component CalendarAPI [Google/Outlook Calendar]
}

PatientUI --> AuthController
StaffUI --> AppointmentController
AdminUI --> UserController

AuthController --> AuthService
AppointmentController --> AppointmentService
PatientController --> PatientService
ClinicalController --> ClinicalDataService

AppointmentService --> AppointmentRepository
PatientService --> PatientRepository
ClinicalDataService --> ClinicalRepository

AppointmentRepository --> Database
PatientRepository --> Database
ClinicalRepository --> Database
UserRepository --> Database
AuditRepository --> Database

AppointmentService --> Cache
ReminderService --> MessageQueue

ReminderService --> EmailService
ReminderService --> SMSService

PatientService --> CalendarAPI

@enduml
```

---

## Architecture Decision Records (ADRs)

### ADR-001: Layered Architecture Pattern
**Status:** ACCEPTED  
**Context:** Need clear separation of concerns and testability  
**Decision:** Use layered architecture (Presentation → Business Logic → Data Access)  
**Rationale:** Familiar pattern, enables independent testing, supports future changes  
**Consequences:** Additional abstraction layers, potential performance overhead from mapping DTOs

---

### ADR-002: Relational Database (PostgreSQL)
**Status:** ACCEPTED  
**Context:** HIPAA compliance requires ACID guarantees for healthcare data  
**Decision:** Use PostgreSQL for all operational and audit data  
**Rationale:** Open-source, ACID-compliant, powerful JSON support, proven at scale  
**Consequences:** No NoSQL flexibility, schema migrations required for changes

---

### ADR-003: Asynchronous Processing for Background Jobs
**Status:** ACCEPTED  
**Context:** Reminders and document processing should not block user requests  
**Decision:** Use Redis Streams for job queuing with background workers  
**Rationale:** Decouples request processing, enables scaling workers independently  
**Consequences:** Eventual consistency, requires retry logic and dead-letter queues

---

### ADR-004: JWT Authentication with Refresh Tokens
**Status:** ACCEPTED  
**Context:** Stateless API design requires token-based auth  
**Decision:** Use JWT access tokens (1-hour) + refresh tokens (7-day)  
**Rationale:** Stateless, scalable, industry standard, supports MFA  
**Consequences:** Token revocation challenges, requires secure token storage on client

---

### ADR-005: Self-Hosted Infrastructure (No Managed Services)
**Status:** ACCEPTED  
**Context:** Project constraints require free/open-source technologies only  
**Decision:** Self-host on Windows Server with IIS, manage PostgreSQL/Redis ourselves  
**Rationale:** No cost, full control, meets constraint  
**Consequences:** Operational burden, need ops expertise, limited auto-scaling capabilities

---

## Risk Mitigation

### High-Risk Items

| Risk | Probability | Impact | Mitigation |
|------|-----------|--------|-----------|
| Database failure | Medium | Critical | Replication + automated failover, daily backups, test recovery monthly |
| API instance failure | Low | Medium | N+1 redundancy, health checks every 5s, auto-restart |
| Data breach / unauthorized access | Low | Critical | HIPAA encryption, RBAC, MFA, audit logging, penetration testing |
| Document processing fails | Medium | High | Retry logic, dead-letter queue, manual intervention option |
| 3rd-party API outage (Twilio, SendGrid) | Low | Medium | Fallback providers, graceful degradation, manual retry |
| Performance degradation under load | Medium | High | Caching, async processing, load testing, performance monitoring |

---

## Conclusion

This design document provides a comprehensive architecture for the PropellQ Unified Patient Access & Clinical Intelligence Platform, addressing all non-functional, technical, and data requirements. The layered architecture, technology stack selection, and deployment strategy support the platform's goals of reliability, security, scalability, and HIPAA compliance, while adhering to the constraints of free/open-source technologies.

**Document Status:** Ready for Review  
**Next Steps:** Design Models (UML diagrams), Create Figma Specification, Plan Cloud Infrastructure

---

## Appendix: Performance & Security Checklist

### Pre-Production Deployment Checklist
- [ ] All NFRs validated in performance testing
- [ ] Security penetration test completed
- [ ] HIPAA compliance audit passed
- [ ] Disaster recovery procedure tested
- [ ] API load testing at 10K+ concurrent users
- [ ] Database backup/restore tested
- [ ] SSL certificates installed and auto-renewal configured
- [ ] Secrets management system operational
- [ ] Monitoring and alerting configured
- [ ] Runbook documentation completed

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-17  
**Next Review:** Upon completion of detailed design phase
