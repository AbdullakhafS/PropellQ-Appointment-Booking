# Figma Specification: Unified Patient Access & Clinical Intelligence Platform

**Document Version:** 1.0  
**Date:** 2026-06-17  
**Status:** Draft  
**Source:** spec.md, design.md  
**Design System Reference:** designsystem.md

---

## Table of Contents

1. [UX Requirements & Design Principles](#ux-requirements--design-principles)
2. [Screen Inventory](#screen-inventory)
3. [Portal Structures](#portal-structures)
4. [Component Library](#component-library)
5. [Navigation & Flow Maps](#navigation--flow-maps)
6. [Design Coverage Matrix](#design-coverage-matrix)

---

## UX Requirements & Design Principles

### Design Philosophy

**User-Centric Care:** Prioritize patient agency and clinical staff efficiency over system elegance.

**Accessibility First:** WCAG 2.2 Level AA compliance mandatory for all screens (keyboard navigation, screen reader support, color contrast).

**Mobile-First Responsive:** Design for mobile first, then scale to tablet and desktop (3 breakpoints: 375px, 768px, 1024px+).

**Information Density:** Clinical screens may contain more density; patient-facing screens prioritize simplicity.

**Data Transparency:** All extracted/AI data clearly indicates confidence scores, sources, and verification status.

**Clear Error Messages:** All validation errors are specific, actionable, and avoid technical jargon.

### Core UX Requirements Extracted from Use Cases

| UXR ID | Use Case | Requirement | Priority | Design Implication |
|--------|----------|-------------|----------|-------------------|
| UXR-001 | UC-001 | Appointment search with date/time/provider/specialty filters | CRITICAL | Multi-filter interface with real-time result updates |
| UXR-002 | UC-001 | Visual calendar view of available slots | CRITICAL | Interactive calendar component with real-time availability |
| UXR-003 | UC-001 | Provider information display (bio, specialty, ratings) | HIGH | Provider card component with rich detail view |
| UXR-004 | UC-001 | Instant booking confirmation within 60 seconds | CRITICAL | Loading state handling, confirmation modal, PDF generation |
| UXR-005 | UC-002 | Preferred slot selection during primary booking | CRITICAL | Dual-slot picker UI with timeout indication (24h) |
| UXR-006 | UC-003 | Notification UI for slot swaps with confirmation | HIGH | In-app notification + email + SMS designs |
| UXR-007 | UC-003 | Waitlist management & availability alerts | HIGH | Waitlist status display, opt-in/opt-out controls |
| UXR-008 | UC-004 | Reminder preference controls (channels, timing) | HIGH | Preference settings panel with toggle controls |
| UXR-009 | UC-004 | Multi-channel reminder delivery (SMS/Email) | CRITICAL | SMS delivery confirmation, email template designs |
| UXR-010 | UC-005 | Calendar OAuth authorization flow | HIGH | OAuth consent screen, connection status UI |
| UXR-011 | UC-005 | Calendar sync status & event details | HIGH | Sync indicator, event detail preview |
| UXR-012 | UC-006 | AI-assisted intake chatbot UI | HIGH | Chat bubble interface, response validation, progress indication |
| UXR-013 | UC-006 | Natural language input handling & error recovery | HIGH | Input validation feedback, re-prompt options |
| UXR-014 | UC-007 | Manual intake form with auto-population | HIGH | Multi-step form, field auto-fill, progress tracker |
| UXR-015 | UC-008 | Insurance pre-check result display | HIGH | Status badge (verified/unverified), warning banner |
| UXR-016 | UC-009 | Document upload interface | HIGH | Drag-and-drop upload, file type validation, progress tracking |
| UXR-017 | UC-009 | OCR processing progress & results display | HIGH | Processing state UI, extraction result preview |
| UXR-018 | UC-010 | 360-degree patient profile display | CRITICAL | Tabbed interface (medications, allergies, diagnoses, vitals) |
| UXR-019 | UC-010 | Data conflict flag & resolution UI | HIGH | Conflict alert badge, resolution workflow UI |
| UXR-020 | UC-011 | Staff conflict resolution interface | HIGH | Side-by-side comparison, resolution options, audit trail |
| UXR-021 | UC-012 | ICD-10 code suggestions with confidence scores | HIGH | Suggestion list with confidence badges, verification controls |
| UXR-022 | UC-012 | Auto-accepted high-confidence codes (≥70%) | HIGH | Auto-selection indicator, override option |
| UXR-023 | UC-013 | CPT code suggestions interface | HIGH | Suggestion list, manual search fallback |
| UXR-024 | UC-014 | Pre-appointment patient profile summary for staff | CRITICAL | Compact profile card, quick-access to detailed data |
| UXR-025 | UC-015 | Walk-in appointment creation form | HIGH | Quick entry form, patient lookup, slot availability |
| UXR-026 | UC-016 | Real-time queue management interface | CRITICAL | Queue list with status indicators, drag-and-drop reordering |
| UXR-027 | UC-017 | Check-in interface (kiosk & staff-assisted) | HIGH | Fast check-in flow, patient verification, status update |
| UXR-028 | UC-018 | Waitlist notification & slot acceptance | HIGH | Time-sensitive notification, quick-accept option |
| UXR-029 | UC-019 | Appointment cancellation & reschedule flows | HIGH | Confirmation modals, reason capture, alternative suggestions |
| UXR-030 | UC-020 | Staff user account management (CRUD) | HIGH | User table/list, add/edit/delete forms, role assignment |
| UXR-031 | UC-021 | System configuration settings UI | MEDIUM | Settings panel, toggle/slider controls, save confirmation |

---

## Screen Inventory

### Patient Portal Screens (15 unique screens + variants)

#### Authentication & Onboarding (3 screens)

**SCR-P-001: Login Screen**
- **User Story:** UC-001 (Patient books appointment)
- **States:** Default, Loading, Error, Password Reset Mode
- **Components:** Email input, password input (toggle visibility), "Remember me" checkbox, "Forgot password" link, Login button, Social login options (Google/Apple)
- **Size Classes:** Mobile (100% width), Tablet (400px centered), Desktop (400px centered)
- **Design Tokens:** Primary button, secondary text, form input
- **Accessibility:** Form labels, ARIA roles, keyboard tab order
- **Error Handling:** Invalid credentials message, account locked warning, password reset flow

**SCR-P-002: Register Screen**
- **States:** Default, Loading, Error, Success
- **Components:** First name input, last name input, email input, password input with strength meter, confirm password input, Terms & Privacy agreement checkbox, Register button
- **Design Tokens:** Form inputs, validation states (error red, success green)
- **Validation:** Email format, password strength (min 8 chars, uppercase, number, symbol)
- **Post-Registration:** Redirect to MFA enrollment or appointment booking

**SCR-P-003: MFA Verification Screen**
- **States:** Default, Loading, Error, Retry
- **Components:** TOTP input field (6 digits), "Didn't receive code?" link, Resend button, Back to login link
- **Timeout:** 5-minute expiry indication, countdown timer
- **Design Tokens:** Code input, timer styling
- **Accessibility:** Clear labeling, numeric input hints

---

#### Appointment Booking Flow (5 screens + states)

**SCR-P-004: Appointment Search Screen**
- **User Story:** UC-001 (Search & book appointment)
- **Components:**
  - Date picker (single day selection)
  - Time range selector (Morning/Afternoon/Evening presets OR custom time)
  - Provider search/autocomplete
  - Specialty filter (dropdown)
  - Search button
  - Recently viewed providers (if applicable)
- **Results Display:** Loading state, 0 results message, up to 20 results per page
- **Design Tokens:** Form inputs, filter tags, result cards
- **Responsive:** Filters collapse into modal on mobile
- **Accessibility:** Form labels, aria-expanded for filter section

**SCR-P-005: Provider Selection & Slot Picker**
- **User Story:** UC-001, UC-005
- **Two-Column Layout:**
  - **Left Panel:** Provider details card (name, specialty, bio, ratings, profile photo, location/telehealth indicator)
  - **Right Panel:** Interactive calendar with available slots
- **Calendar Component:**
  - Month view initially, drill into day view
  - Visual indication of availability (green = available, gray = booked)
  - Slot durations shown (15min, 30min, 1hr)
  - Hover effect showing slot details
- **Design Tokens:** Calendar styles, availability colors, slot cards
- **States:** Selecting, Selected, Unavailable
- **Accessibility:** Calendar keyboard navigation (arrow keys), slot focus indicators

**SCR-P-006: Preferred Slot Selection**
- **User Story:** UC-001, UC-002 (Preferred slot swap)
- **Components:**
  - Primary slot display (read-only, confirmed)
  - "Want your preferred time?" CTA
  - Preferred slot picker (similar to SCR-P-005 but with limited availability)
  - Timeout timer (24 hours) with explanation text
  - "Skip" and "Continue to checkout" buttons
- **Design Tokens:** CTA color, timer styling, secondary slot styling
- **Optional Feature Indication:** Make it clear this is optional and recommended

**SCR-P-007: Booking Checkout Confirmation**
- **User Story:** UC-001
- **Components:**
  - Appointment summary (date, time, provider, location/telehealth)
  - Preferred slot summary (if selected)
  - Insurance information (if captured in intake)
  - Terms & conditions checkbox
  - Confirm & Book button
  - Back/Cancel button
- **Loading State:** Submit button shows loading indicator (animated spinner)
- **Success State:** Transitioned to confirmation screen
- **Design Tokens:** Summary card styling, primary button
- **Accessibility:** Summary data presented as list, not just visual

**SCR-P-008: Booking Confirmation Screen**
- **User Story:** UC-001 (Instant confirmation)
- **Components:**
  - Success message ("Your appointment is confirmed!")
  - Appointment card (date, time, provider, confirmation number)
  - Provider contact info
  - Location OR telehealth join link (with 15-min button appearing 15 min before appointment)
  - Reminder settings link
  - "Add to calendar" button (triggers calendar sync for authorized users)
  - Download PDF confirmation button
  - Next steps (intake, insurance verification if pending)
  - "Back to appointments" button
- **Design Tokens:** Success color (green), confirmation card styling
- **Email Trigger:** Send PDF confirmation within 60 seconds

---

#### Patient Profile & Intake (4 screens)

**SCR-P-009: AI-Assisted Intake Chatbot**
- **User Story:** UC-006
- **Layout:** Chat-style interface with conversation history
- **Components:**
  - Chat bubble area (scrollable, bot messages on left, patient responses on right)
  - Input field for patient responses
  - Suggested quick-reply buttons (for specific questions)
  - Progress bar at top showing intake completion % (5 steps: demographics, chief complaint, medical history, medications, allergies)
  - "Edit previous answer" links
  - "Skip this question" option
  - Timer indication (estimated time remaining)
- **Bot Messages:** Natural language, empathetic tone, clear data requests
- **Design Tokens:** Chat bubble styling, quick-reply button styling
- **Validation:** Validation feedback shown inline, no hard errors (conversational retries)
- **Accessibility:** Screen reader friendly chat structure, input labeling

**SCR-P-010: Manual Intake Form**
- **User Story:** UC-007
- **Layout:** Multi-step form (Step indicator at top)
- **Steps:**
  1. Demographics (first name, last name, DOB, phone, email)
  2. Chief Complaint & Reason for Visit (text area)
  3. Medical History (checkboxes: hypertension, diabetes, etc. + open-ended field)
  4. Current Medications (table: medication name, dosage, frequency + Add row button)
  5. Allergies (table: substance, reaction, severity + Add row button)
  6. Insurance Information (insurance company, member ID, group number)
- **Auto-Population:** Fields pre-filled from previous intake if consent given
- **Progress Indicator:** Step tabs at top, "Back/Next" buttons at bottom
- **Design Tokens:** Form inputs, field validation (error/success states)
- **Accessibility:** Fieldset grouping, legend labels, error associations via aria-describedby

**SCR-P-011: Patient Profile Dashboard**
- **User Story:** UC-010 (360-degree profile)
- **Layout:** Tabbed interface
- **Tabs:**
  - **Overview:** Quick facts (age, upcoming appointments, pending actions)
  - **Medical History:** Allergies, medical conditions, medications (with conflict flags)
  - **Documents:** Uploaded documents list, upload button, document preview on click
  - **Lab Results & Vitals:** Tabular display with source and date
  - **Insurance:** Insurance details, verification status badge
- **Conflict Indicators:** Red badge on tabs with conflicts, detail view shows conflict cards
- **Design Tokens:** Tab styling, conflict badge (red), verified badge (green), data source attribution styling
- **Accessibility:** Tab focus management, content within tab marked as live region for updates

**SCR-P-012: Document Upload Interface**
- **User Story:** UC-009
- **Components:**
  - Drag-and-drop zone (large, prominent)
  - "Or select files" button (standard file picker)
  - File type indicators (PDF, DOCX, images supported)
  - Document list during upload (with progress bars)
  - Post-upload list of documents (with delete option)
  - Processing status (e.g., "OCR in progress", "Ready for review")
- **Design Tokens:** Drag-drop zone styling, upload progress, status indicators
- **Validation:** File type check, file size limit (e.g., 25MB max)
- **Accessibility:** Keyboard support for file selection, screen reader feedback on upload progress

---

#### Appointment Management (3 screens)

**SCR-P-013: Upcoming Appointments**
- **User Story:** UC-019 (Appointment management)
- **Layout:** List view (mobile) / Card grid (desktop)
- **Components (Per Appointment):**
  - Date & time
  - Provider name & specialty
  - Location or telehealth indicator
  - Status badge (Scheduled, Arrived, Completed, Cancelled)
  - Actions: View Details, Reschedule, Cancel, Add to Calendar
- **Sections:** Upcoming (next 30 days), Past (last 12 months, collapsed by default)
- **Design Tokens:** Card styling, date/time typography, status badge colors
- **Empty State:** "No upcoming appointments" with CTA to book

**SCR-P-014: Appointment Detail & Reschedule**
- **User Story:** UC-019
- **Detail View:**
  - Full appointment info (date, time, provider, location, confirmation number)
  - Provider details (contact, specialty, bio)
  - Appointment notes (if available)
  - Reminder settings
- **Reschedule Modal:**
  - Calendar picker (similar to SCR-P-005)
  - Time picker
  - Confirmation before finalizing
  - Confirmation sent to email
- **Cancel Flow:**
  - "Are you sure?" confirmation
  - Reason for cancellation (dropdown: scheduling conflict, no longer needed, other)
  - Confirmation of cancellation
- **Design Tokens:** Detail card styling, modal overlay, reschedule button styling

**SCR-P-015: Notification Center**
- **User Story:** UC-002, UC-003, UC-018
- **Layout:** List of notifications (with timestamp, type icon)
- **Notification Types:**
  - Appointment reminders (48h, 24h, 2h before)
  - Preferred slot swap available
  - Waitlist slot available
  - Appointment confirmed/cancelled
  - System alerts
- **Components:**
  - Notification item (title, time, action buttons like "Reschedule", "Accept")
  - Notification preferences link
  - Mark as read/unread
  - Delete notification option
- **Design Tokens:** Notification card styling, type icons (color-coded)
- **Empty State:** "No notifications" message

---

#### Settings & Preferences (1 screen)

**SCR-P-016: Reminder & Notification Preferences**
- **User Story:** UC-004 (Manage communication preferences)
- **Components:**
  - Reminder timing toggles (48h, 24h, 2h before appointment)
  - Channel preferences (SMS toggle, Email toggle)
  - Time window preferences (e.g., "Don't send reminders between 9 PM - 9 AM")
  - Preferred phone number (for SMS)
  - Preferred email address
  - Waitlist alerts toggle
  - "Save preferences" button
- **Design Tokens:** Toggle switch styling, save button
- **Feedback:** Confirmation message when preferences saved

---

### Staff Portal Screens (10 unique screens + variants)

#### Dashboard & Queue Management (3 screens)

**SCR-S-001: Staff Dashboard (Today's View)**
- **User Story:** UC-016, UC-017 (Queue management, check-in)
- **Layout:** Multi-panel dashboard
- **Panels:**
  - **Schedule Widget:** Today's schedule (list of appointments with times, provider, status)
  - **Queue Status:** Current queue count, average wait time, patients waiting
  - **Alerts:** Insurance verification pending, conflicts to resolve, walk-in requests
  - **Quick Actions:** Create walk-in, search patient, view reports
- **Design Tokens:** Widget styling, alert badge colors (red = urgent, yellow = warning)
- **Real-Time Updates:** Queue status refreshes every 30 seconds

**SCR-S-002: Queue Management Interface**
- **User Story:** UC-016 (Manage same-day queue)
- **Layout:** Queue list (left) + Patient detail (right) on desktop; stacked on mobile
- **Queue List Components:**
  - Reorderable patient list (drag-and-drop)
  - Patient name, appointment time, wait time, status (checked-in, waiting, in-room, completed)
  - Color-coded status (green = in-room, yellow = waiting, blue = checked-in)
  - Search/filter (by patient name, provider)
  - Add walk-in button at top
- **Patient Detail Panel:**
  - Quick profile summary
  - Insurance verification status
  - Clinical data conflicts (if any)
  - Action buttons: Check In, Move Up, Mark Ready, Complete
- **Design Tokens:** List styling, drag-handle styling, action button styling

**SCR-S-003: Check-In Interface (Kiosk & Staff-Assisted)**
- **User Story:** UC-017
- **Two Modes:**
  - **Kiosk Mode (Tablet-oriented):** Self-service check-in with large buttons
    - "I'm here for my appointment" button
    - Patient confirms name, DOB or appointment number
    - Success confirmation shown
  - **Staff Mode:** Staff-assisted check-in from desktop
    - Patient lookup (by appointment or name)
    - Quick check-in button
    - Confirmation message
- **Design Tokens:** Large, touch-friendly buttons for kiosk mode, professional styling for staff mode

---

#### Patient Management (3 screens)

**SCR-S-004: Patient Search & Selection**
- **User Story:** UC-014, UC-010 (Pre-appointment profile review)
- **Components:**
  - Search bar (by name, MRN, appointment ID)
  - Search results list (name, DOB, MRN, upcoming appointments)
  - Click to view full profile
  - Recently viewed patients (quick access)
- **Design Tokens:** Search input, result list styling

**SCR-S-005: 360-Degree Patient Profile (Staff View)**
- **User Story:** UC-010, UC-014 (Review patient profile pre-appointment)
- **Layout:** Multi-tab interface (similar to SCR-P-011 but with staff actions)
- **Tabs:**
  - **Overview:** Demographics, upcoming appointments, alerts
  - **Medical History:** Medications, allergies, diagnoses (with conflict flags)
  - **Documents:** Uploaded documents, extraction results
  - **Lab Results & Vitals:** Historical data, trends
  - **Insurance:** Insurance details, verification status
  - **Coding:** Suggested ICD-10/CPT codes, verification history
- **Conflict Indicators:** Conflict cards with resolution options
- **Actions:**
  - Resolve data conflict (if conflicts present)
  - Verify/flag insurance
  - Approve/override code suggestions
- **Design Tokens:** Tab styling, conflict resolution widget styling, staff action buttons

**SCR-S-006: Data Conflict Resolution**
- **User Story:** UC-011 (Resolve data conflicts)
- **Layout:** Side-by-side comparison
- **Components:**
  - Conflict summary (type: duplicate, mismatch, interaction)
  - Two data versions displayed side-by-side (old vs. new, with source indicators)
  - Staff notes/reasoning field
  - Resolution options: Accept new value, Keep old value, Merge, Request clarification
  - Confirmation before finalizing
- **Design Tokens:** Comparison layout styling, resolution button group

---

#### Medical Coding (2 screens)

**SCR-S-007: ICD-10 & CPT Code Suggestions**
- **User Story:** UC-012, UC-013 (Suggest codes from patient data)
- **Layout:** Suggestion list with action panel
- **Components:**
  - **ICD-10 Suggestions Table:**
    - Code, description, confidence score badge (high ≥70% in green, low <70% in yellow)
    - Auto-selected indicator for high-confidence codes
    - Verify button (to lock), Override button (to change)
  - **CPT Suggestions Table:** Similar layout
  - Manual code search field (fallback if suggestions insufficient)
  - Notes field for medical necessity
  - Submit/Save codes button
- **Design Tokens:** Suggestion card styling, confidence badge colors, verify/override button styling
- **Accessibility:** Table structure with proper headers, suggestion reasoning accessible via alt-text or expandable detail

**SCR-S-008: Coding History & Audit**
- **User Story:** UC-012, UC-013
- **Layout:** Table of historical codings
- **Components:**
  - Date, patient, codes submitted, approver, approval status
  - Click to view detail (original suggestions, staff selections, reasoning)
- **Design Tokens:** Table styling, status badge colors

---

#### Administrative (2 screens)

**SCR-S-009: Walk-In Appointment Creation**
- **User Story:** UC-015 (Create walk-in appointment)
- **Layout:** Quick-entry form
- **Components:**
  - Patient lookup (search existing or create new)
  - Provider selection (dropdown or search)
  - Appointment time (current or future time slot picker)
  - Reason for visit (free text)
  - Insurance flag (if needed)
  - Create appointment button
- **Design Tokens:** Form input styling, quick-entry button styling
- **Feedback:** Confirmation with appointment details

**SCR-S-010: Staff Settings & Schedule**
- **User Story:** UC-016 (Staff operations)
- **Components:**
  - Personal profile (name, specialty, contact)
  - Availability schedule (weekly view with blocks for available/unavailable times)
  - Notification preferences (email, SMS)
  - Password change
  - Save settings button
- **Design Tokens:** Settings form styling, schedule grid

---

### Admin Portal Screens (8 unique screens + variants)

#### Dashboard & Analytics (2 screens)

**SCR-A-001: Admin Dashboard**
- **User Story:** UC-021 (System configuration)
- **Layout:** Dashboard with KPI cards and charts
- **KPI Cards:**
  - Total appointments (this week)
  - No-show rate (%)
  - Average wait time
  - Insurance verification rate
  - System uptime (%)
  - Active users
- **Charts:**
  - Appointments over time (line chart)
  - No-show trend (bar chart)
  - Busiest hours (heatmap)
- **Alerts:** System alerts, pending approvals
- **Design Tokens:** KPI card styling, chart styling

**SCR-A-002: Analytics & Reports**
- **User Story:** UC-021
- **Layout:** Report builder interface
- **Components:**
  - Date range picker
  - Filter controls (by provider, specialty, appointment type)
  - Report type selector (appointments, no-shows, insurance, revenue)
  - Table with sortable columns
  - Export button (CSV, PDF)
  - Chart visualizations (selectable)
- **Design Tokens:** Report styling, export button styling

---

#### User Management (3 screens)

**SCR-A-003: User Management List**
- **User Story:** UC-020 (Manage staff accounts)
- **Layout:** User table with actions
- **Components:**
  - User table (name, email, role, status, last login)
  - Search/filter (by name, email, role)
  - Add User button
  - Actions per user: Edit, Deactivate, Reset Password, Delete
- **Design Tokens:** Table styling, action button styling

**SCR-A-004: Add/Edit User Account**
- **User Story:** UC-020
- **Layout:** Form with validation
- **Components:**
  - First name, last name inputs
  - Email input (with validation)
  - Role dropdown (Patient, Staff, Admin)
  - Specialty (if Staff role)
  - Phone number
  - Department/Clinic assignment
  - Active/Inactive toggle
  - Save/Cancel buttons
- **Design Tokens:** Form input styling, role-based field visibility

**SCR-A-005: User Activity Log**
- **User Story:** UC-020
- **Layout:** Table of user activities
- **Components:**
  - User, action (login, logout, patient access, code verification), timestamp, IP address
  - Filter by date range, user, action type
  - Export button
- **Design Tokens:** Log table styling

---

#### System Configuration (3 screens)

**SCR-A-006: Appointment Settings**
- **User Story:** UC-021
- **Components:**
  - Default appointment duration (minutes)
  - Buffer time between appointments (minutes)
  - Preferred slot swap timeout (hours)
  - Reminder timing (48h, 24h, 2h toggles)
  - Max documents per patient
  - Allowed document formats
  - Save settings button
- **Design Tokens:** Settings form styling

**SCR-A-007: Notification & Reminder Templates**
- **User Story:** UC-021
- **Components:**
  - Template selector (SMS reminder, Email reminder, Confirmation, Cancellation, etc.)
  - Template preview (with variable placeholders like {{patientName}}, {{appointmentTime}})
  - Edit template (WYSIWYG editor for email)
  - Save/Reset buttons
- **Design Tokens:** Template editor styling, preview panel styling

**SCR-A-008: Security & Compliance Settings**
- **User Story:** UC-021
- **Components:**
  - MFA requirement toggle
  - Password policy (min length, complexity requirements)
  - Session timeout (minutes)
  - Audit log retention period (years)
  - API key management (view, rotate)
  - Encryption settings (read-only, informational)
  - Save settings button
- **Design Tokens:** Settings form styling, security warning badges

---

## Portal Structures

### Navigation Hierarchy

#### Patient Portal Navigation
```
Primary Navigation (top or left sidebar on desktop, hamburger on mobile):
├── Dashboard
├── Appointments
│   ├── Upcoming
│   ├── Search & Book
│   └── History
├── Profile
│   ├── Medical History
│   ├── Documents
│   └── Insurance
├── Notifications
└── Settings
    ├── Communication Preferences
    └── Account
```

#### Staff Portal Navigation
```
Primary Navigation:
├── Dashboard
├── Queue & Check-In
├── Patient Search
├── Medical Coding
├── Reports
└── Settings
    ├── Schedule
    ├── Preferences
    └── Account
```

#### Admin Portal Navigation
```
Primary Navigation:
├── Dashboard
├── Analytics & Reports
├── User Management
├── System Configuration
│   ├── Appointment Settings
│   ├── Templates
│   └── Security
├── Audit Log
└── Settings
    └── Account
```

---

## Component Library

### Core Components (Reusable Across Portals)

#### 1. Form Components
- **Text Input:** Label, placeholder, error message, validation indicator, helper text
- **Email Input:** Inherits from Text Input with email validation
- **Password Input:** Visibility toggle, strength meter, hint text
- **Checkbox:** Label, indeterminate state, disabled state
- **Radio Button Group:** Label, selected state, disabled option
- **Dropdown/Select:** Label, placeholder, options list, search (if >10 items), disabled state
- **Date Picker:** Calendar widget, time picker (if needed), validation, range selection
- **Time Picker:** Hour/minute inputs, AM/PM toggle, preset buttons
- **Text Area:** Resizable, character counter, validation
- **File Upload:** Drag-and-drop zone, file list, delete button, progress indicator

#### 2. Navigation Components
- **Top Navigation Bar:** Logo, navigation menu, user profile dropdown, notifications bell
- **Sidebar Navigation:** Collapsible menu items, active state indicator, icon + label
- **Breadcrumbs:** Hierarchical path display, clickable links
- **Tabs:** Tab headers, active state, content area
- **Pagination:** Previous/Next buttons, page number display, total items

#### 3. Data Display Components
- **Table:** Headers, rows, sortable columns, hover state, selection (checkbox), pagination
- **Card:** Container with shadow, padding, image placeholder, content area
- **Modal/Dialog:** Overlay, header, body content, footer with actions, close button
- **Alert/Banner:** Icon, message, action button (optional), dismiss button
- **Badge:** Small label with background color (status, count, severity)
- **Progress Bar:** Filled percentage, label, animation
- **Timeline:** Vertical or horizontal timeline with events, dates, icons

#### 4. Action Components
- **Button:** Primary, secondary, tertiary variants, size variants (small, medium, large), loading state, disabled state, icon support
- **Button Group:** Multiple related actions
- **Floating Action Button (FAB):** Bottom-right positioned, circular, for primary action
- **Context Menu:** Right-click or dropdown menu with actions

#### 5. Feedback Components
- **Toast Notification:** Auto-dismiss, position options (top-right, bottom-left), success/error/warning/info variants
- **Loading Indicator:** Spinner, skeleton screens (for data loading states)
- **Empty State:** Illustration, message, CTA button
- **Error Boundary:** Error message display with recovery option

#### 6. Patient-Specific Components
- **Appointment Card:** Date, time, provider, location, status badge, action buttons
- **Provider Card:** Photo, name, specialty, bio, rating, action buttons
- **Clinical Data Card:** Data type, value, source, confidence score, verification status
- **Reminder Preference Control:** Channel toggles, timing options
- **Insurance Status Badge:** Verified/Unverified, warning icon
- **Conflict Resolution Widget:** Side-by-side comparison, resolution buttons

#### 7. Staff-Specific Components
- **Queue Status Indicator:** Patient count, avg wait time, color-coded status
- **Patient Profile Compact:** Quick facts, upcoming appointments, alerts
- **Code Suggestion Item:** Code + description, confidence score, auto-selected indicator, verify/override buttons
- **Walk-In Quick Form:** Inline form fields with auto-suggest

#### 8. Admin-Specific Components
- **KPI Card:** Title, metric value, trend indicator, sparkline chart
- **Report Builder Panel:** Filter controls, date range, export options
- **User Row (Management):** Name, email, role, status, action menu
- **Settings Toggle Group:** Label, toggle, description

---

## Navigation & Flow Maps

### Patient-Facing Flows

#### Flow 1: Book Appointment
```
Login → Appointment Search → Select Provider → Select Slot → 
Preferred Slot Selection (Optional) → Checkout → Confirmation → 
[Optional: AI Intake / Manual Form] → Done
```

#### Flow 2: Manage Appointment Reminders
```
Login → Profile → Notification Preferences → 
Toggle channels (SMS/Email) → Set reminder times → Save → Confirmation
```

#### Flow 3: Upload & Review Clinical Documents
```
Login → Profile → Documents → Upload Files (Drag-Drop) → 
Processing → View Extracted Data → Resolve Conflicts → Confirmation
```

#### Flow 4: Cancel or Reschedule
```
Login → Appointments → Select Appointment → 
[Reschedule: Calendar picker → Confirm] OR [Cancel: Reason → Confirm] → Confirmation
```

---

### Staff-Facing Flows

#### Flow 1: Manage Queue
```
Login → Dashboard → Queue Management → 
[Reorder patients (drag-drop)] → Check In Patient → 
[View Profile & Clinical Data] → Mark Ready/Completed
```

#### Flow 2: Verify Medical Codes
```
Login → Patient Search → View Profile → Coding Tab → 
Review Suggestions → [Approve/Override] → 
Notes (if override) → Submit Codes
```

#### Flow 3: Resolve Data Conflicts
```
Login → Patient Search → View Profile → Conflicts Tab → 
Select Conflict → Review Side-by-Side → Choose Resolution → 
Add Notes → Confirm → Audit Logged
```

---

### Admin-Facing Flows

#### Flow 1: Manage System Settings
```
Login → Settings → [Select Category: Appointments/Notifications/Security] → 
Edit Settings → Save → Confirmation
```

#### Flow 2: Create New User
```
Login → User Management → Add User Button → 
Fill Form (name, email, role, specialty) → Save → 
Confirmation + User receives welcome email
```

---

## Design Coverage Matrix

### Requirement-to-Screen Traceability

| Functional Requirement | Use Case | Screen(s) | Status |
|------------------------|----------|-----------|--------|
| FR-001: Patient Self-Service Booking | UC-001 | SCR-P-004, SCR-P-005, SCR-P-007, SCR-P-008 | ✓ |
| FR-002: Preferred Slot Swap | UC-003 | SCR-P-006, SCR-P-015 | ✓ |
| FR-003: Multi-Channel Reminders | UC-002 | SCR-P-009, SCR-P-016 | ✓ |
| FR-004: Calendar Integration | UC-005 | SCR-P-008 (Add to calendar), SCR-P-016 | ✓ |
| FR-005: AI-Assisted Intake | UC-006 | SCR-P-009 | ✓ |
| FR-006: Manual Intake Form | UC-007 | SCR-P-010 | ✓ |
| FR-007: 360-Degree Profile | UC-010 | SCR-P-011, SCR-S-005 | ✓ |
| FR-008: ICD-10/CPT Extraction | UC-012, UC-013 | SCR-S-007, SCR-S-008 | ✓ |
| FR-009: Data Conflict Detection | UC-011 | SCR-S-006, SCR-P-011 | ✓ |
| FR-010: Walk-In Management | UC-015 | SCR-S-009 | ✓ |
| FR-011: Same-Day Queue | UC-016 | SCR-S-002 | ✓ |
| FR-012: Check-In Process | UC-017 | SCR-S-003 | ✓ |
| FR-013: Waitlist Management | UC-018 | SCR-P-013, SCR-P-015 (Waitlist tab) | ✓ |
| FR-014: Cancellation/Reschedule | UC-019 | SCR-P-014, SCR-P-015 | ✓ |
| FR-015: RBAC User Management | UC-020 | SCR-A-003, SCR-A-004 | ✓ |
| FR-016: Admin User Management | UC-020 | SCR-A-003, SCR-A-004 | ✓ |
| FR-017: Dashboard & Analytics | UC-021 | SCR-A-001, SCR-A-002 | ✓ |
| FR-018: Configurable Settings | UC-021 | SCR-A-006, SCR-A-007, SCR-A-008 | ✓ |
| FR-019: HIPAA Compliance | All | Audit logging (implicit in all staff screens) | ✓ |
| FR-020: Audit Logging | All | SCR-A-005 (User Activity) | ✓ |
| FR-021: Uptime SLA | All | SCR-A-001 (Health indicators) | ✓ |
| FR-022: Scalability | All | Infrastructure (not UI-visible) | ✓ |

---

## Responsive Breakpoints

All screens designed for 3 breakpoints:
- **Mobile:** 375px - 767px (primary breakpoint)
- **Tablet:** 768px - 1023px
- **Desktop:** 1024px+

### Mobile Adaptations
- Navigation: Hamburger menu (sidebar slides in from left)
- Forms: Single-column layout, full-width inputs
- Tables: Horizontal scroll OR collapsed card view
- Modals: Full-screen dialogs
- Calendar: Compact month view, drill into day details

### Tablet Adaptations
- Navigation: Sidebar visible but narrower
- Forms: Two-column grid layout (if space allows)
- Tables: Full table view with horizontal scroll
- Modals: Centered, max-width 600px

### Desktop Adaptations
- Navigation: Full sidebar + top bar
- Forms: Multi-column grid layout
- Tables: Full-width with smooth interactions
- Modals: Centered, max-width 800px

---

## Accessibility (WCAG 2.2 Level AA)

### Keyboard Navigation
- All interactive elements accessible via Tab key
- Logical tab order (left-to-right, top-to-bottom)
- Modal focus trap (focus stays within modal)
- Escape key closes modals/dropdowns

### Screen Reader Support
- All buttons labeled with aria-label or visible text
- Form inputs have associated labels (via label element or aria-label)
- Tables have proper header associations (thead/tbody, th elements)
- Modal dialogs have aria-modal="true" and aria-labelledby
- Live regions (aria-live) for real-time updates (queue status, notifications)

### Color Contrast
- All text has contrast ratio ≥ 4.5:1 (normal) or 3:1 (large text)
- Color is never sole indicator of status (use icons + text + color)

### Visual Design
- Focus indicators visible (outline or ring)
- Sufficient touch target size (min 44px × 44px for mobile)
- Proper spacing between interactive elements

---

## Design System Reference

See `designsystem.md` for:
- Color palette (primary, secondary, semantic colors)
- Typography system (font family, sizes, weights, line heights)
- Spacing scale
- Border radius system
- Shadow system
- Icon system
- Animation/Motion guidelines

---

**Next Steps:**
1. Export Figma design file with all screens and components
2. Create interactive prototype with key flows
3. Set up component library in Figma for developer hand-off
4. Generate design specs with CSS variables for engineering team

---

*Document prepared by: Senior Product Designer (AI)*  
*Figma Workspace:** [To be created]  
*Design System File:** designsystem.md

