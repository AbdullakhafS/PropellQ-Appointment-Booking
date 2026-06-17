# UML Architectural Models: Unified Patient Access & Clinical Intelligence Platform

**Document Version:** 1.0  
**Date:** 2026-06-17  
**Status:** Draft  
**Source:** spec.md, design.md

---

## Table of Contents
1. [System Context Diagram](#system-context-diagram)
2. [Component Architecture Diagram](#component-architecture-diagram)
3. [Entity-Relationship Diagram (ERD)](#entity-relationship-diagram)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Sequence Diagrams](#sequence-diagrams)
6. [Deployment Topology Diagram](#deployment-topology-diagram)
7. [State Diagrams](#state-diagrams)

---

## System Context Diagram

### Overview
The system context diagram shows PropellQ as a single system and its interactions with external actors and systems. This high-level view establishes system boundaries and key integrations.

```puml
@startuml system-context
!define DIRECTION top to bottom
skinparam linetype ortho
title PropellQ System Context Diagram

actor Patient as P
actor "Staff\n(Front Desk/Clinical)" as S
actor Admin as A
system PropellQ as PQ
database "Google Calendar\nOutlook Calendar" as CALENDAR
system "Twilio\n(SMS Provider)" as TWILIO
system "SendGrid\n(Email Provider)" as SENDGRID
database "PostgreSQL\nDatabase" as DB
system "Document AI\n(OCR, NLP)" as AI
system "ICD-10/CPT\nCoding Engine" as CODING

P --> PQ: Book appointments\nUpload documents\nManage profile\nReceive reminders
S --> PQ: Create walk-ins\nManage queue\nCheck-in patients\nReview clinical data
A --> PQ: Manage users\nConfigure settings\nView analytics

PQ --> CALENDAR: Sync appointments\n(OAuth 2.0)
PQ --> TWILIO: Send SMS reminders\n(API)
PQ --> SENDGRID: Send email confirmations\nand reminders (API)
PQ --> DB: Persist data\n(ACID transactions)
PQ --> AI: Process documents\nExtract data\n(async jobs)
PQ --> CODING: Suggest ICD-10/CPT codes\n(ML model)

note right of PQ
  Core System:
  - Appointment booking & reminders
  - Clinical data aggregation
  - Medical code suggestion
  - HIPAA-compliant data handling
  - 99.9% uptime SLA
end note

@enduml
```

---

## Component Architecture Diagram

### Overview
The component architecture diagram breaks down PropellQ into major components and shows their dependencies and interactions.

```puml
@startuml component-architecture
!define DIRECTION left to right
skinparam linetype ortho
title PropellQ Component Architecture

package "Presentation Layer" {
    component [Patient Portal UI\n(React SPA)] as PatientUI
    component [Staff Portal UI\n(React SPA)] as StaffUI
    component [Admin Portal UI\n(React SPA)] as AdminUI
}

package "API Layer" {
    component [API Gateway\n(Load Balancer)] as Gateway
    component [Auth Controller] as AuthCtrl
    component [Appointment Controller] as AppCtrl
    component [Patient Controller] as PatCtrl
    component [Clinical Data Controller] as ClinCtrl
    component [User Controller] as UserCtrl
}

package "Business Logic Layer" {
    component [Auth Service] as AuthSvc
    component [Appointment Service] as AppSvc
    component [Patient Service] as PatSvc
    component [Clinical Data Service] as ClinSvc
    component [Reminder Service] as RemSvc
}

package "Data Access Layer" {
    component [Appointment Repository] as AppRepo
    component [Patient Repository] as PatRepo
    component [Clinical Repository] as ClinRepo
    component [User Repository] as UserRepo
    component [Audit Repository] as AuditRepo
}

package "Infrastructure" {
    database [PostgreSQL\nPrimary] as PgPrimary
    database [PostgreSQL\nStandby] as PgStandby
    component [Redis\n(Sessions, Cache)] as Redis
    component [Redis Streams\n(Message Queue)] as RedisMQ
    component [File Storage\n(Encrypted)] as FileStore
}

package "Background Workers" {
    component [Reminder\nWorker] as RemWorker
    component [Document\nProcessing Worker] as DocWorker
    component [Data Extraction\nWorker] as ExtWorker
    component [Email/SMS\nDelivery Worker] as DeliveryWorker
}

package "External Services" {
    component [Google/Outlook\nCalendar API] as CalAPI
    component [Twilio\nSMS] as TwilioAPI
    component [SendGrid\nEmail] as SendGridAPI
    component [Document AI\n(OCR/NLP)] as DocAI
}

' Presentation to API
PatientUI --> Gateway
StaffUI --> Gateway
AdminUI --> Gateway

' API to Controllers
Gateway --> AuthCtrl
Gateway --> AppCtrl
Gateway --> PatCtrl
Gateway --> ClinCtrl
Gateway --> UserCtrl

' Controllers to Services
AuthCtrl --> AuthSvc
AppCtrl --> AppSvc
PatCtrl --> PatSvc
ClinCtrl --> ClinSvc
AppCtrl --> RemSvc

' Services to Repositories
AuthSvc --> UserRepo
AppSvc --> AppRepo
PatSvc --> PatRepo
ClinSvc --> ClinRepo
RemSvc --> AppRepo

' Repositories to Database
AppRepo --> PgPrimary
PatRepo --> PgPrimary
ClinRepo --> PgPrimary
UserRepo --> PgPrimary
AuditRepo --> PgPrimary

' Database Replication
PgPrimary --> PgStandby

' Services to Cache/Queue
AuthSvc --> Redis
AppSvc --> Redis
PatSvc --> Redis
ClinSvc --> Redis
RemSvc --> RedisMQ

' Workers to Queue and Database
RedisMQ --> RemWorker
RedisMQ --> DocWorker
RedisMQ --> ExtWorker
RedisMQ --> DeliveryWorker

RemWorker --> DeliveryWorker
DocWorker --> ExtWorker
ExtWorker --> ClinRepo

' Workers to External Services
DeliveryWorker --> TwilioAPI
DeliveryWorker --> SendGridAPI
DocWorker --> DocAI

' Services to External APIs
AppSvc --> CalAPI
PatSvc --> FileStore

note right of Gateway
  API Gateway:
  - Load balancing
  - Health checks
  - Request routing
end note

@enduml
```

---

## Entity-Relationship Diagram

### Overview
The ERD shows all data entities, their attributes, and relationships in the PropellQ system.

```puml
@startuml erd
!define DIRECTION top to bottom
title PropellQ Entity-Relationship Diagram

entity "User" as User {
  * user_id (PK)
  --
  email
  password_hash
  first_name
  last_name
  role (Patient | Staff | Admin)
  mfa_enabled
  is_active
  created_at
  updated_at
}

entity "Patient" as Patient {
  * patient_id (PK)
  --
  user_id (FK)
  first_name
  last_name
  date_of_birth
  phone
  email
  insurance_id
  insurance_name
  created_at
  updated_at
}

entity "Provider" as Provider {
  * provider_id (PK)
  --
  first_name
  last_name
  specialty
  bio
  is_active
  created_at
  updated_at
}

entity "Appointment" as Appointment {
  * appointment_id (PK)
  --
  patient_id (FK)
  provider_id (FK)
  start_datetime
  end_datetime
  status
  is_walk_in
  cancellation_reason
  cancelled_at
  cancelled_by_user_id (FK)
  preferred_slot_datetime
  swapped_at
  created_at
  updated_at
}

entity "AppointmentSlot" as Slot {
  * slot_id (PK)
  --
  provider_id (FK)
  start_datetime
  end_datetime
  is_available
  created_at
}

entity "ClinicalData" as ClinicalData {
  * clinical_data_id (PK)
  --
  patient_id (FK)
  data_type (medication | allergy | diagnosis | vital | lab)
  value
  unit (if applicable)
  source_document_id (FK)
  confidence_score (0-100)
  verified_by_user_id (FK)
  verified_at
  created_at
  updated_at
}

entity "Document" as Document {
  * document_id (PK)
  --
  patient_id (FK)
  document_type
  file_name
  file_path
  file_size
  uploaded_by_user_id (FK)
  uploaded_at
  is_deleted
  deleted_at
}

entity "ExtractedData" as ExtractedData {
  * extracted_data_id (PK)
  --
  document_id (FK)
  data_type
  value
  confidence_score
  extracted_at
}

entity "MedicalCode" as MedicalCode {
  * medical_code_id (PK)
  --
  patient_id (FK)
  appointment_id (FK)
  code_type (ICD10 | CPT)
  code_value
  code_description
  confidence_score
  verified_by_user_id (FK)
  verified_at
  created_at
}

entity "DataConflict" as Conflict {
  * conflict_id (PK)
  --
  patient_id (FK)
  conflict_type (duplicate | mismatch | interaction)
  affected_entities
  severity (CRITICAL | HIGH | LOW)
  resolved_at
  resolved_by_user_id (FK)
  resolution_note
  created_at
}

entity "AuditLog" as AuditLog {
  * audit_log_id (PK)
  --
  user_id (FK)
  action
  entity_type
  entity_id
  old_value
  new_value
  ip_address
  created_at
}

entity "Notification" as Notification {
  * notification_id (PK)
  --
  patient_id (FK)
  appointment_id (FK)
  notification_type (reminder | confirmation | update)
  channel (SMS | EMAIL)
  status (pending | sent | failed)
  sent_at
  retry_count
  created_at
}

entity "ReminderPreference" as ReminderPref {
  * preference_id (PK)
  --
  patient_id (FK)
  remind_48h_before
  remind_24h_before
  remind_2h_before
  sms_enabled
  email_enabled
  updated_at
}

' Relationships
User ||--o{ Patient : "has"
User ||--o{ Appointment : "cancels"
User ||--o{ ClinicalData : "verifies"
User ||--o{ MedicalCode : "verifies"
User ||--o{ AuditLog : "performs"

Patient ||--o{ Appointment : "books"
Patient ||--o{ ClinicalData : "has"
Patient ||--o{ Document : "uploads"
Patient ||--o{ MedicalCode : "assigned"
Patient ||--o{ Notification : "receives"
Patient ||--o{ Conflict : "has"
Patient ||--o{ ReminderPref : "sets"

Provider ||--o{ Appointment : "provides"
Provider ||--o{ Slot : "schedules"

Appointment ||--o{ MedicalCode : "assigned"
Appointment ||--o{ Notification : "triggers"

Document ||--o{ ClinicalData : "extracts"
Document ||--o{ ExtractedData : "generates"
Document ||--o{ Conflict : "identifies"

ExtractedData ||--o{ ClinicalData : "converts"

AuditLog ||--o{ Patient : "logs access"
AuditLog ||--o{ Appointment : "logs changes"

@enduml
```

---

## Data Flow Diagrams

### DFD Level 0: System Boundary

```puml
@startuml dfd-level0
title PropellQ Data Flow Diagram - Level 0 (System Boundary)

actor Patient
actor Staff
actor Admin
system PropellQ as PQ
database Database as DB
system "External APIs" as EXT

Patient -d-> PQ: 1. Book appointment,\nUpload documents
Staff -d-> PQ: 2. Check-in, manage\nqueue, review data
Admin -d-> PQ: 3. Manage users,\nview analytics
PQ -d-> DB: 4. Store/retrieve\ndata
PQ -r-> EXT: 5. Send reminders\n(SMS/Email),\nSync calendars
@enduml
```

### DFD Level 1: Major Processes

```puml
@startuml dfd-level1
title PropellQ Data Flow Diagram - Level 1 (Major Processes)

actor Patient
actor Staff
actor Admin
database Database as DB
system "Twilio/SendGrid" as Notifications
system "Calendar APIs" as CalendarAPI

Patient -d-> [1.0\nBooking Process]
[1.0\nBooking Process] -d-> DB: Save appointment
[1.0\nBooking Process] --> [2.0\nReminder Process]: Trigger reminders
[1.0\nBooking Process] --> [3.0\nCalendar Sync]: Sync to calendar

[2.0\nReminder Process] -r-> Notifications: Send SMS/Email\nreminders
Patient <-l- Notifications: Receive notifications

Staff -d-> [4.0\nQueue Management]
[4.0\nQueue Management] -d-> DB: Update appointment\nstatus
[4.0\nQueue Management] --> [5.0\nClinical Data]

Admin -d-> [6.0\nUser Management]
[6.0\nUser Management] -d-> DB: Manage users

[5.0\nClinical Data] -d-> DB: Store clinical data
[5.0\nClinical Data] --> [7.0\nMedical Coding]: Suggest codes
[7.0\nMedical Coding] -d-> DB: Save codes

[3.0\nCalendar Sync] -r-> CalendarAPI: Create/update\ncalendar event
@enduml
```

### DFD: Appointment Booking Flow

```puml
@startuml dfd-booking
title PropellQ Data Flow - Appointment Booking Details

actor Patient
database Cache as CACHE
entity "Slot Mgmt" as Slots
entity "Appointment Mgmt" as Appt
entity "Reminder Scheduler" as Reminder
database Database as DB
entity "Calendar Sync" as Calendar
system "External Calendar" as ExtCalendar
entity "Notification Service" as NotifSvc
system "SendGrid" as EmailSvc

Patient -r-> Slots: 1. Request available\nslots (date, provider)
Slots -d-> Cache: 2. Check cache for\navailability
Cache -d-> DB: 3. Query if not\nin cache
DB -d-> Cache: 4. Return available\nslots
Cache -u-> Slots: 5. Return slots to\npatient
Slots -u-> Patient: 6. Display available\nslots

Patient -d-> Appt: 7. Select slot & book\n(primary + preferred)
Appt -r-> DB: 8. Create appointment\n(atomic transaction)
DB -u-> Appt: 9. Appointment created

Appt -d-> Reminder: 10. Schedule reminders\n(48h, 24h, 2h)
Reminder -d-> DB: 11. Store reminder\nschedule

Appt --> Calendar: 12. Prepare calendar event
Calendar --> ExtCalendar: 13. Sync to external\ncalendar (if auth)
ExtCalendar -u-> Calendar: 14. Calendar synced

Appt --> NotifSvc: 15. Trigger confirmation
NotifSvc --> EmailSvc: 16. Send email\nconfirmation (PDF)
EmailSvc -u-> Patient: 17. Confirmation email\nreceived

Appt -d-> DB: 18. Log to audit trail
@enduml
```

### DFD: Clinical Data Aggregation Flow

```puml
@startuml dfd-clinical
title PropellQ Data Flow - Clinical Data Aggregation

actor Patient
entity "Intake Service" as Intake
entity "Document Processor" as DocProc
entity "Data Extraction" as Extraction
entity "Conflict Detection" as Conflict
entity "Profile Builder" as ProfileBuilder
database Database as DB
actor Staff

Patient -r-> Intake: 1. Submit intake\n(AI or manual)
Intake -d-> DB: 2. Store intake data

Patient -r-> DocProc: 3. Upload documents
DocProc -d-> DocProc: 4. OCR if needed
DocProc --> Extraction: 5. Send for extraction

Extraction --> Extraction: 6. Parse content\nextract entities
Extraction -d-> DB: 7. Store extracted data\n(with confidence scores)

Extraction --> Conflict: 8. Check for conflicts
Conflict --> Conflict: 9. Compare with\nexisting data
Conflict -d-> DB: 10. Flag conflicts

ProfileBuilder -d-> DB: 11. Query all patient data\n(intake, documents,\nprevious visits)
DB -u-> ProfileBuilder: 12. Return all data

ProfileBuilder --> ProfileBuilder: 13. De-duplicate\ndata entries
ProfileBuilder --> ProfileBuilder: 14. Consolidate\ninto unified profile
ProfileBuilder -d-> DB: 15. Store 360-degree\nprofile

ProfileBuilder -u-> Staff: 16. Display profile to\nclinical staff

Staff -d-> ProfileBuilder: 17. Verify/correct\ndata as needed
ProfileBuilder -d-> DB: 18. Update profile\nwith corrections

@enduml
```

---

## Sequence Diagrams

### Sequence: Patient Books Appointment

```puml
@startuml seq-booking
title Sequence: Patient Books Appointment

participant Patient as P
participant "Patient Portal" as UI
participant "API Gateway" as GW
participant "Appointment Service" as AppSvc
participant "Cache (Redis)" as Cache
participant "Database" as DB
participant "Reminder Service" as RemSvc
participant "Calendar Service" as CalSvc
participant "External Calendar" as ExtCal
participant "Email Service" as EmailSvc

P -> UI: 1. Search appointments\n(date, provider)
UI -> GW: GET /api/v1/slots/available
GW -> AppSvc: getAvailableSlots()
AppSvc -> Cache: Check availability\ncache (30s TTL)
alt Cache hit
    Cache --> AppSvc: Return cached slots
else Cache miss
    AppSvc -> DB: Query available slots\nfrom appointment_slots
    DB --> AppSvc: Return slots
    AppSvc -> Cache: Store in cache (30s)
end
AppSvc --> GW: Return slots
GW --> UI: JSON response
UI --> P: Display calendar

P -> UI: 2. Select slot +\npreferred slot
UI -> GW: POST /api/v1/appointments\n{slot, preferred_slot}

activate GW
GW -> AppSvc: bookAppointment()
activate AppSvc

AppSvc -> DB: BEGIN TRANSACTION
AppSvc -> DB: Lock selected slot
alt Slot already booked
    DB -->> AppSvc: Conflict error
    AppSvc -->> GW: 409 Conflict
    deactivate AppSvc
    GW -->> UI: Error: Slot unavailable
    deactivate GW
    UI --> P: Show error
else Slot available
    AppSvc -> DB: Create appointment record\n(status: Scheduled)
    AppSvc -> DB: Release slot\n(is_available: false)
    AppSvc -> DB: Store preferred_slot\ndatetime
    AppSvc -> DB: COMMIT
    
    AppSvc --> Cache: Update availability cache
    
    AppSvc -> RemSvc: scheduleReminders(appointmentId)\n48h, 24h, 2h before
    RemSvc --> RemSvc: Enqueue reminder jobs
    
    AppSvc -> CalSvc: syncToCalendar(appointmentId)
    alt Patient authorized calendar
        CalSvc -> ExtCal: POST /calendar/events\n(OAuth token)
        ExtCal --> CalSvc: Event created
        CalSvc --> AppSvc: Calendar synced
    else Not authorized
        CalSvc -->> AppSvc: Calendar sync skipped
    end
    
    AppSvc -> EmailSvc: sendConfirmation(appointmentId)
    EmailSvc --> EmailSvc: Generate PDF\nAdd to queue
    
    AppSvc -> DB: Log to audit_logs\n(appointment_created)
    
    AppSvc --> GW: Appointment created\n(status: success)
    deactivate AppSvc
    
    GW --> UI: 200 OK + appointment details
    deactivate GW
    UI --> P: Confirmation screen\nShow appointment details
    
    par
        RemSvc -> RemSvc: Process reminder jobs\n(background workers)
        EmailSvc -> EmailSvc: Send email\n(60s SLA)
        P --> P: Receive email\nconfirmation + PDF
    end
end
@enduml
```

### Sequence: Appointment Reminder Flow

```puml
@startuml seq-reminder
title Sequence: Appointment Reminder Delivery

participant "Reminder Scheduler" as Scheduler
participant "Redis Queue" as Queue
participant "Reminder Worker" as Worker
participant "Email/SMS Service" as NotifSvc
participant "SendGrid" as SG
participant "Twilio" as TW
participant "Database" as DB
participant Patient as P

note over Scheduler
    Runs every minute via cron job
    Checks for appointments within
    reminder windows (48h, 24h, 2h)
end note

Scheduler -> DB: Query appointments\nwhere start_datetime\nin [now+48h, now+48h+1m]
DB --> Scheduler: Return appointments\nneeding 48h reminders

loop For each appointment
    Scheduler -> Queue: Enqueue reminder job\n{appointmentId, type: "48h"}
end

Worker -> Queue: Dequeue reminder job
activate Worker

Worker -> DB: Get appointment details\n& patient contact info
DB --> Worker: Return data

Worker -> DB: Get patient reminder\npreferences
DB --> Worker: Return preferences\n{sms_enabled, email_enabled}

alt SMS enabled
    Worker -> NotifSvc: sendSMS(appointmentId)
    NotifSvc -> TW: POST /messages/send\n(phone, message)
    TW --> NotifSvc: SMS queued
    NotifSvc --> Worker: SMS sent
    Worker -> DB: Log notification\n{type: SMS, status: sent}
end

alt Email enabled
    Worker -> NotifSvc: sendEmail(appointmentId)
    NotifSvc -> SG: POST /mail/send\n(email, template)
    SG --> NotifSvc: Email queued
    NotifSvc --> Worker: Email sent
    Worker -> DB: Log notification\n{type: EMAIL, status: sent}
end

Worker -> DB: Update reminder status\n{sent_at: now}

deactivate Worker

par
    TW -> P: SMS reminder delivered
    SG -> P: Email reminder delivered
end

P --> P: Patient receives reminder
@enduml
```

### Sequence: Clinical Data Conflict Resolution

```puml
@startuml seq-conflict
title Sequence: Clinical Data Conflict Detection & Resolution

participant Patient as P
participant "Patient Portal" as UI
participant "Document Processor" as DocProc
participant "Data Extraction" as Extract
participant "Conflict Detector" as ConflictDet
participant "Database" as DB
participant Staff as S
participant "Staff Portal" as StaffUI

P -> UI: 1. Upload medical\ndocument (PDF)
UI -> DocProc: Upload document
DocProc -> DocProc: OCR + parse\ncontent
DocProc -> Extract: Extract structured\ndata
Extract -> Extract: Identify:\n- Medications\n- Allergies\n- Diagnoses\n- Vitals

Extract -> DB: Store extracted data\n{value, confidence_score}

Extract -> ConflictDet: Check for conflicts\nwith existing data
activate ConflictDet

ConflictDet -> DB: Query patient's existing\nclinical data
DB --> ConflictDet: Return all stored\ndata for patient

ConflictDet -> ConflictDet: Compare new vs.\nexisting:\n- Same medication,\ndifferent dose?\n- Allergy vs.\nmedicine interaction?\n- Conflicting\ndiagnoses?

alt Conflicts found
    ConflictDet -> DB: Create conflict\nrecords\n{severity: CRITICAL/HIGH}
    DB --> ConflictDet: Conflict stored
    ConflictDet --> Extract: Conflicts detected
else No conflicts
    ConflictDet --> Extract: No conflicts
end

deactivate ConflictDet

Extract --> DocProc: Extraction complete
DocProc --> UI: Document processed
UI --> P: Document uploaded\nsuccessfully

S -> StaffUI: 2. View patient\nprofile pre-appointment
StaffUI -> DB: GET patient profile
DB --> StaffUI: Return 360-degree\nprofile + conflicts

StaffUI --> S: Display profile\nwith conflict alerts\n(red flags)

S -> UI: 3. Click conflict\nto review details
UI -> DB: GET conflict details\n{old_value, new_value,\nsource_docs}
DB --> UI: Return conflict info

S -> UI: 4. Review both\nvalues + sources

S -> UI: 5. Select resolution:\nAccept new value\nOR keep old value\nOR merge

UI -> DB: PATCH conflict\n{resolution: selected,\nresolved_by: staff_id}

DB -> DB: Update affected\nclinical data

DB -> DB: Log to audit_logs\n{conflict_resolved}

UI --> S: Conflict marked\nas resolved

S --> S: Profile now\naccurate & ready\nfor appointment
@enduml
```

### Sequence: Medical Code Suggestion

```puml
@startuml seq-coding
title Sequence: AI Medical Code Suggestion & Verification

participant Staff as S
participant "Staff Portal" as UI
participant "Coding Service" as CodingSvc
participant "AI Model API" as AIModel
participant "Database" as DB
participant Patient as P

S -> UI: 1. Access patient\nprofile pre/post visit
UI -> CodingSvc: GET medical codes\nfor patient
CodingSvc -> DB: Query patient clinical\ndata (diagnoses,\nprocedures, notes)
DB --> CodingSvc: Return clinical\ndata + confidence

CodingSvc -> AIModel: suggestCodes(\ndiagnoses, procedures,\nclinical_notes)
activate AIModel

AIModel -> AIModel: Process NLP\nExtract entities\nMap to ICD-10/CPT

AIModel --> CodingSvc: Return suggestions\n[\n  {code: E11.9,\n   type: ICD10,\n   description: "Type 2 diabetes",\n   confidence: 92%},\n  {code: 99213,\n   type: CPT,\n   description: "Office visit",\n   confidence: 87%}\n]

deactivate AIModel

CodingSvc -> DB: Store code suggestions\n{confidence_score}

CodingSvc --> UI: Return suggestions

UI --> S: Display codes:\n- High confidence (≥70%)\n  = auto-selected\n- Low confidence (<70%)\n  = require review

S -> UI: 2. Review auto-selected\ncodes (high confidence)

alt Code looks correct
    S -> UI: Click "Accept"
else Code incorrect
    S -> UI: Click "Override"\nEnter different code
end

UI -> DB: Save verified code\n{verified_by: staff_id,\nverified_at: now}

alt Low confidence code
    S -> UI: Review low-confidence\ncode suggestion
    S -> UI: Click "Accept",\n"Reject", or "Override"
    UI -> DB: Save staff decision\n{decision, reason}
end

DB -> DB: Lock codes\n(no further changes)

DB -> DB: Log to audit_logs\n{codes_finalized}

UI --> S: Codes finalized\n& locked

par
    DB -> DB: Track AI accuracy\n(for model retraining)
    S --> P: Patient receives\ncoded encounter\nfor claim submission
end
@enduml
```

---

## Deployment Topology Diagram

### Overview
The deployment diagram shows how PropellQ components are deployed across physical infrastructure.

```puml
@startuml deployment
title PropellQ Deployment Topology

node "Client Devices" as ClientNode {
    component PatientApp [Patient Portal\n(React SPA)]
    component StaffApp [Staff Portal\n(React SPA)]
    component AdminApp [Admin Portal\n(React SPA)]
}

cloud "CDN / Free Hosting" as CDN {
    artifact NetlifyStatic [Static Assets\n(CSS, JS, Images)\nNetlify/Vercel]
}

node "Internet" as Internet {
}

node "Windows Server (On-Premise)" as ServerNode {
    node "Load Balancer\n(IIS URL Rewrite)" as LB {
        component LBComponent [Request Routing\nSSL Termination\nHealth Checks]
    }
    
    node "API Instance 1\n(IIS + ASP.NET Core)" as API1 {
        component API1App [AppointmentController\nPatientController\nClinicalDataController]
    }
    
    node "API Instance 2\n(IIS + ASP.NET Core)" as API2 {
        component API2App [AppointmentController\nPatientController\nClinicalDataController]
    }
    
    node "API Instance 3\n(IIS + ASP.NET Core)" as API3 {
        component API3App [AppointmentController\nPatientController\nClinicalDataController]
    }
    
    node "Database Tier" as DBTier {
        database PgPrimary [PostgreSQL Primary\n(Read/Write)]
        database PgStandby [PostgreSQL Standby\n(Replication)]
    }
    
    node "Cache Tier" as CacheTier {
        database RedisPrimary [Redis Primary\n(Sessions, Cache)]
        database RedisStandby [Redis Standby\n(Replication)]
    }
    
    node "Storage" as Storage {
        artifact FileStore [File Storage\n(Patient Documents)\nEncrypted]
        artifact Backups [Backup Storage\n(Daily Snapshots)\n7-year retention]
    }
    
    node "Background Workers" as Workers {
        component ReminderWorker [Reminder Delivery\nWorker]
        component DocumentWorker [Document Processing\nWorker]
        component ExtractionWorker [Data Extraction\nWorker]
    }
}

node "External Services" as External {
    artifact GoogleCalendar [Google Calendar\n(OAuth 2.0)]
    artifact OutlookCalendar [Outlook Calendar\n(OAuth 2.0)]
    artifact Twilio [Twilio\n(SMS API)]
    artifact SendGrid [SendGrid\n(Email API)]
}

' Connections
PatientApp -.-> CDN: Load static assets
StaffApp -.-> CDN: Load static assets
AdminApp -.-> CDN: Load static assets

CDN -.-> Internet: Serve via CDN
Internet -down-> LB: HTTPS requests

LB --> API1: Route requests
LB --> API2: Route requests
LB --> API3: Route requests

API1 --> PgPrimary: Query/Update
API2 --> PgPrimary: Query/Update
API3 --> PgPrimary: Query/Update

API1 --> RedisPrimary: Get/Set cache\nDequeue jobs
API2 --> RedisPrimary: Get/Set cache\nDequeue jobs
API3 --> RedisPrimary: Get/Set cache\nDequeue jobs

PgPrimary --> PgStandby: Replication stream

ReminderWorker --> RedisPrimary: Dequeue jobs
DocumentWorker --> RedisPrimary: Dequeue jobs
ExtractionWorker --> RedisPrimary: Dequeue jobs

ReminderWorker --> PgPrimary: Log delivery status
DocumentWorker --> PgPrimary: Store extracted data
ExtractionWorker --> PgPrimary: Update clinical data

API1 --> FileStore: Upload/Download\ndocuments
API2 --> FileStore: Upload/Download\ndocuments
API3 --> FileStore: Upload/Download\ndocuments

FileStore --> Backups: Daily backup

ReminderWorker --> Twilio: Send SMS
ReminderWorker --> SendGrid: Send Email

API1 --> GoogleCalendar: Sync appointments
API1 --> OutlookCalendar: Sync appointments

note bottom of ServerNode
  Windows Server Infrastructure:
  - All components self-hosted
  - No managed cloud services
  - N+1 redundancy for API instances
  - Database replication & failover
  - Redis persistence for recovery
  - 99.9% uptime target
end note

@enduml
```

---

## State Diagrams

### Appointment State Machine

```puml
@startuml state-appointment
title Appointment State Machine

[*] --> Scheduled: Patient books or\nstaff creates walk-in

Scheduled --> Scheduled: Rescheduled by\npatient/staff

Scheduled --> Scheduled: Preferred slot\nswap offered

Scheduled --> Cancelled: Patient/staff\ncancels\n(>24h before)

Scheduled --> Arrived: Staff marks\npatient arrived\n(within 24h)

Arrived --> Completed: Visit finishes,\nnotes entered

Arrived --> NoShow: Appointment time\npassed, patient\nnever arrived

Cancelled --> [*]
NoShow --> [*]
Completed --> [*]

Scheduled: Entry: Schedule reminders\nSync to calendar\nEntry: Send confirmation

Scheduled: Do: Monitor preferred\nslot availability\nDo: Retry reminder\ndelivery

@enduml
```

### Patient Data Conflict State Machine

```puml
@startuml state-conflict
title Data Conflict Resolution State Machine

[*] --> Detected: Conflict identified\nduring:\n- Document processing\n- Data aggregation\n- Manual entry

Detected --> Detected: Additional data\nreveals more\nconflicts

Detected --> AwaitingReview: Conflict flagged\nfor staff review

AwaitingReview --> AwaitingReview: Timeout: 7 days\nescalate to admin

AwaitingReview --> Resolved: Staff chooses\nresolution:\n- Accept new\n- Keep old\n- Merge data\n- Request clarification

Resolved --> Archived: Resolution\nlogged & saved

Archived --> [*]

Detected: Severity:\nCRITICAL | HIGH | LOW

AwaitingReview: Entry: Create audit\nlog entry\nEntry: Alert staff

Resolved: Exit: Update clinical\ndata\nExit: Close conflict

@enduml
```

---

## Class Diagram (Domain Model)

### Core Domain Classes

```puml
@startuml class-diagram
title PropellQ Domain Model

class User {
  - userId: UUID
  - email: string
  - passwordHash: string
  - firstName: string
  - lastName: string
  - role: Role
  - mfaEnabled: boolean
  --
  + login(email, password): AuthResponse
  + verifyMFA(totp): boolean
  + updateProfile(details): void
}

enum Role {
  PATIENT
  STAFF
  ADMIN
}

class Patient {
  - patientId: UUID
  - user: User
  - dateOfBirth: DateTime
  - phone: string
  - insurance: Insurance
  --
  + getProfile(): PatientProfile
  + uploadDocument(file): Document
  + updatePreferences(prefs): void
}

class Insurance {
  - insuranceId: string
  - name: string
  - memberId: string
  - groupNumber: string
  - isVerified: boolean
}

class Provider {
  - providerId: UUID
  - firstName: string
  - lastName: string
  - specialty: string
  - bio: string
}

class Appointment {
  - appointmentId: UUID
  - patient: Patient
  - provider: Provider
  - startDateTime: DateTime
  - endDateTime: DateTime
  - status: AppointmentStatus
  - preferredSlotDateTime: DateTime
  --
  + book(patient, slot, preferred): Appointment
  + reschedule(newDateTime): void
  + cancel(reason): void
  + checkIn(): void
  + swapPreferredSlot(): void
}

enum AppointmentStatus {
  SCHEDULED
  ARRIVED
  COMPLETED
  CANCELLED
  NO_SHOW
}

class PatientProfile {
  - profileId: UUID
  - patient: Patient
  - medications: ClinicalData[]
  - allergies: ClinicalData[]
  - diagnoses: ClinicalData[]
  - vitals: ClinicalData[]
  - documents: Document[]
  --
  + addClinicalData(data): void
  + addDocument(doc): void
  + getConflicts(): DataConflict[]
  + resolve Conflict(conflictId, resolution): void
}

class ClinicalData {
  - clinicalDataId: UUID
  - dataType: DataType
  - value: string
  - sourceDocument: Document
  - confidenceScore: float
  - verifiedBy: User
  --
  + verify(): void
  + flag(): void
}

enum DataType {
  MEDICATION
  ALLERGY
  DIAGNOSIS
  VITAL
  LAB_RESULT
}

class Document {
  - documentId: UUID
  - patient: Patient
  - fileName: string
  - uploadedAt: DateTime
  - extractedData: ExtractedData[]
  --
  + process(): void
  + extract(): void
}

class ExtractedData {
  - extractedDataId: UUID
  - document: Document
  - value: string
  - confidenceScore: float
  --
  + validate(): boolean
}

class MedicalCode {
  - codeId: UUID
  - patient: Patient
  - appointment: Appointment
  - codeType: CodeType
  - codeValue: string
  - confidenceScore: float
  - verifiedBy: User
}

enum CodeType {
  ICD10
  CPT
}

class DataConflict {
  - conflictId: UUID
  - patient: Patient
  - conflictType: ConflictType
  - severity: Severity
  - resolvedBy: User
  - resolutionNote: string
  --
  + resolve(resolution): void
  + escalate(): void
}

enum ConflictType {
  DUPLICATE
  MISMATCH
  INTERACTION
}

enum Severity {
  CRITICAL
  HIGH
  LOW
}

' Relationships
User "1" -- "1" Patient: has
User "1" -- "0..*" Appointment: cancels
User "1" -- "0..*" ClinicalData: verifies

Patient "1" -- "0..*" Appointment: books
Patient "1" -- "1" PatientProfile: has
Patient "1" -- "0..*" Document: uploads
Patient "1" -- "0..*" MedicalCode: assigned
Patient "1" -- "0..*" DataConflict: has

Provider "1" -- "0..*" Appointment: provides

Appointment "1" -- "0..*" MedicalCode: assigned

PatientProfile "1" -- "0..*" ClinicalData: contains
PatientProfile "1" -- "0..*" Document: references

Document "1" -- "0..*" ExtractedData: generates

ClinicalData "0..*" --> "1" DataType: has

MedicalCode "0..*" --> "1" CodeType: has

DataConflict "0..*" --> "1" ConflictType: has
DataConflict "0..*" --> "1" Severity: has

User "1" -- "1" Role: has

@enduml
```

---

## Component Interaction Matrix

### Service Dependencies & Call Matrix

| Service | Calls | Called By | Async | Data |
|---------|-------|-----------|-------|------|
| AppointmentService | PatientService, ReminderService, ClinicalDataService | Controllers, RemindService | No | Appointments, Slots |
| PatientService | DocumentService, ClinicalDataService, CalendarService | Controllers | No | Patients, Documents |
| ClinicalDataService | PatientService | Controllers, ExtractionWorker | No | ClinicalData, MedicalCodes |
| ReminderService | AppointmentService, NotificationService | AppointmentService | Yes | Reminders, Notifications |
| AuthService | UserRepository | Controllers | No | Users, Tokens |
| DocumentService | ExtractionService, ConflictService | PatientService | Yes | Documents |
| ExtractionService | DocumentService, ClinicalDataService, ConflictService | DocumentService (async) | Yes | ExtractedData |
| ConflictService | ClinicalDataService | ExtractionService | No | Conflicts |
| CalendarService | PatientService | PatientService | Yes | Calendar Events |
| NotificationService | ReminderService | ReminderService | Yes | Notifications |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-17 | AI Assistant | Initial UML models and diagrams |

---

**Document Status:** Ready for Review  
**Next Steps:** Figma Specification (UI Screens), Create Epics (Implementation Breakdown)

---

## Diagram Reference Guide

All diagrams in this document use PlantUML syntax and can be rendered into PNG/SVG using:
- PlantUML online editor: https://www.plantuml.com/plantuml/uml/
- Local PlantUML: `plantuml models.md -o models_output/`
- VS Code extensions: PlantUML Preview

### Color Coding
- **Blue:** System/Process/Database
- **Green:** Actor/User
- **Yellow:** Data/Entity
- **Red:** Error/Conflict/Critical

