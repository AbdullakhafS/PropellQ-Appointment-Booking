# PropellQ Navigation Map & Information Architecture

**Document Version:** 1.0  
**Date:** 2026-06-17  
**Status:** Draft  
**Fidelity Level:** High-Fidelity  
**Source:** figma_spec.md, designsystem.md

---

## Table of Contents

1. [Site Architecture Overview](#site-architecture-overview)
2. [Portal Navigation Maps](#portal-navigation-maps)
3. [Information Architecture](#information-architecture)
4. [User Flow Paths](#user-flow-paths)
5. [Cross-Portal Navigation](#cross-portal-navigation)
6. [Screen Inventory & Traceability](#screen-inventory--traceability)

---

## Site Architecture Overview

### High-Level System Structure

```
PropellQ Platform
│
├── Authentication Layer (Public)
│   ├── Login
│   ├── Register
│   └── MFA Verification
│
├── Patient Portal (Private - Authenticated)
│   ├── Dashboard
│   ├── Appointment Management
│   ├── Patient Intake
│   ├── Profile & Documents
│   ├── Notifications
│   └── Settings
│
├── Staff Portal (Private - Role-Gated)
│   ├── Dashboard & Queue
│   ├── Patient Management
│   ├── Medical Coding
│   ├── Operations
│   └── Settings
│
└── Admin Portal (Private - Admin-Only)
    ├── Dashboard & Analytics
    ├── User Management
    ├── System Configuration
    └── Settings
```

### Entry Points

| Portal | Entry Point | URL Pattern | Auth Required |
|--------|------------|-----------|-----------------|
| Patient | Login/Register | `/auth/login`, `/auth/register` | No (redirect if authenticated) |
| Staff | Login | `/auth/login` | No (role verified at entry) |
| Admin | Login | `/auth/login` | No (admin role verified) |
| Public | Authentication | `/` | No |

---

## Portal Navigation Maps

### Patient Portal Navigation Map

```
Patient Portal (authenticated as role=PATIENT)
│
├── [Top Navigation Bar]
│   ├── Logo (Home link → Dashboard)
│   ├── Menu Icon (Mobile: hamburger, Desktop: sidebar)
│   ├── Notifications Bell → Notification Center
│   └── User Profile Dropdown → Profile / Logout
│
├── [Sidebar / Hamburger Menu]
│   ├── Dashboard
│   │   └── Quick stats, upcoming appointments, pending actions
│   │
│   ├── Appointments
│   │   ├── Search & Book
│   │   │   ├── Search Screen (SCR-P-004)
│   │   │   ├── Provider Selection (SCR-P-005)
│   │   │   ├── Preferred Slot (SCR-P-006)
│   │   │   ├── Checkout (SCR-P-007)
│   │   │   └── Confirmation (SCR-P-008)
│   │   │
│   │   ├── Upcoming
│   │   │   └── Appointment List (SCR-P-013)
│   │   │       └── [Click] → Appointment Detail (SCR-P-014)
│   │   │           ├── View Details
│   │   │           ├── Reschedule
│   │   │           └── Cancel
│   │   │
│   │   └── History
│   │       └── Past Appointments (collapsible)
│   │
│   ├── Profile
│   │   ├── Medical History
│   │   │   └── Profile Dashboard (SCR-P-011)
│   │   │       ├── Tab: Medical History
│   │   │       ├── Tab: Medications
│   │   │       ├── Tab: Allergies
│   │   │       └── Tab: Lab Results
│   │   │
│   │   ├── Documents
│   │   │   ├── Upload (SCR-P-012)
│   │   │   │   └── Drag-drop zone, file list
│   │   │   │
│   │   │   └── Document List
│   │   │       └── View extracted data
│   │   │
│   │   └── Insurance
│   │       └── Insurance Details & Status
│   │
│   ├── Intake (if appointment pending intake)
│   │   ├── AI-Assisted (SCR-P-009)
│   │   │   └── Chat interface with progress
│   │   │
│   │   └── Manual Form (SCR-P-010)
│   │       └── Multi-step form
│   │
│   ├── Notifications
│   │   └── Notification Center (SCR-P-015)
│   │       ├── Appointment Reminders
│   │       ├── Slot Swap Alerts
│   │       ├── Waitlist Notifications
│   │       └── System Alerts
│   │
│   └── Settings
│       ├── Communication Preferences (SCR-P-016)
│       │   ├── Reminder Timing
│       │   ├── Channel Preferences
│       │   └── Quiet Hours
│       │
│       └── Account
│           ├── Profile Management
│           ├── Password Change
│           ├── MFA Settings
│           └── Logout
│
└── [Persistent Elements]
    ├── Footer: Help, Contact, Privacy
    └── Feedback widget (?)
```

### Staff Portal Navigation Map

```
Staff Portal (authenticated as role=STAFF or ADMIN)
│
├── [Top Navigation Bar]
│   ├── Logo (Home link → Dashboard)
│   ├── Today's Date / Clinic Selector
│   ├── Search Patient (global search)
│   ├── Notifications Bell
│   └── User Profile Dropdown
│
├── [Sidebar Navigation]
│   ├── Dashboard
│   │   ├── Today's View (SCR-S-001)
│   │   │   ├── Schedule widget
│   │   │   ├── Queue status
│   │   │   └── Alerts panel
│   │   │
│   │   └── Analytics (limited access)
│   │
│   ├── Queue & Check-In
│   │   ├── Queue Management (SCR-S-002)
│   │   │   ├── Real-time queue list
│   │   │   ├── Drag-drop reordering
│   │   │   └── [Click patient] → Quick profile panel
│   │   │
│   │   ├── Check-In (SCR-S-003)
│   │   │   ├── Kiosk Mode (tablets)
│   │   │   └── Staff-Assisted Mode (desktop)
│   │   │
│   │   └── Walk-In Creation (SCR-S-009)
│   │       └── Quick entry form
│   │
│   ├── Patient Management
│   │   ├── Search & Select (SCR-S-004)
│   │   │   └── Search bar, recent patients
│   │   │
│   │   ├── Patient Profile (SCR-S-005)
│   │   │   ├── Tab: Overview
│   │   │   ├── Tab: Medical History
│   │   │   ├── Tab: Documents
│   │   │   ├── Tab: Lab Results
│   │   │   ├── Tab: Insurance
│   │   │   └── Tab: Coding (if applicable)
│   │   │
│   │   └── Data Conflict Resolution (SCR-S-006)
│   │       ├── Conflict list
│   │       └── [Click] → Side-by-side comparison
│   │           └── Resolution action
│   │
│   ├── Medical Coding
│   │   ├── ICD-10/CPT Suggestions (SCR-S-007)
│   │   │   ├── Auto-suggested codes (high confidence)
│   │   │   ├── Verification workflow
│   │   │   └── Manual code search
│   │   │
│   │   └── Coding History (SCR-S-008)
│   │       └── Historical codes list
│   │
│   ├── Settings
│   │   ├── Personal Schedule (SCR-S-010)
│   │   ├── Notification Preferences
│   │   └── Account Settings
│   │
│   └── Help & Resources
│       ├── Documentation
│       └── Contact Admin
│
└── [Persistent Elements]
    ├── Footer: Help, Feedback, Support
    └── Session timeout warning (15 min)
```

### Admin Portal Navigation Map

```
Admin Portal (authenticated as role=ADMIN)
│
├── [Top Navigation Bar]
│   ├── Logo (Home link → Dashboard)
│   ├── System Health Indicator
│   ├── Notifications Bell
│   └── User Profile Dropdown
│
├── [Sidebar Navigation]
│   ├── Dashboard
│   │   ├── KPI Dashboard (SCR-A-001)
│   │   │   ├── Total appointments
│   │   │   ├── No-show rate
│   │   │   ├── Average wait time
│   │   │   ├── System uptime
│   │   │   └── Alerts
│   │   │
│   │   └── Analytics & Reports (SCR-A-002)
│   │       ├── Report builder
│   │       ├── Filters (date, provider, specialty)
│   │       ├── Table view
│   │       └── Export (CSV, PDF)
│   │
│   ├── User Management
│   │   ├── User List (SCR-A-003)
│   │   │   ├── Search/filter users
│   │   │   ├── [Row Action] → Edit User (SCR-A-004)
│   │   │   │   ├── Form fields
│   │   │   │   └── Save/Cancel
│   │   │   │
│   │   │   ├── Add User (SCR-A-004)
│   │   │   │   └── Create new user form
│   │   │   │
│   │   │   ├── Deactivate/Delete User
│   │   │   └── Reset Password
│   │   │
│   │   └── User Activity Log (SCR-A-005)
│   │       ├── Audit log table
│   │       └── Filter by date/user/action
│   │
│   ├── System Configuration
│   │   ├── Appointment Settings (SCR-A-006)
│   │   │   ├── Default duration
│   │   │   ├── Buffer time
│   │   │   ├── Preferred slot timeout
│   │   │   └── Reminder timing
│   │   │
│   │   ├── Notification Templates (SCR-A-007)
│   │   │   ├── Template selector
│   │   │   ├── Preview panel
│   │   │   └── WYSIWYG editor
│   │   │
│   │   └── Security & Compliance (SCR-A-008)
│   │       ├── MFA requirement
│   │       ├── Password policy
│   │       ├── Session timeout
│   │       ├── Audit log retention
│   │       └── Encryption settings
│   │
│   ├── Audit Log
│   │   └── Full audit trail (append-only)
│   │       ├── User actions
│   │       ├── System changes
│   │       └── Compliance records
│   │
│   └── Settings
│       ├── Admin Profile
│       ├── Organization Settings
│       └── Logout
│
└── [Persistent Elements]
    ├── Footer: Documentation, Support
    └── Emergency contact info
```

---

## Information Architecture

### Content Hierarchy by Portal

#### Patient Portal Content Model

```
Root: Patient Dashboard
│
├── Level 1: Self-Service Features
│   ├── Appointment Search & Booking (high visibility)
│   ├── Upcoming Appointments (quick access)
│   ├── Notifications (alerts, reminders)
│   └── Profile & Documents (secondary)
│
├── Level 2: Required Data Entry
│   ├── Intake (AI or Manual)
│   └── Insurance Information
│
├── Level 3: Account Management
│   ├── Communication Preferences
│   ├── Profile Settings
│   └── Account Security
│
└── Level 4: Reference
    ├── Help & FAQ
    └── Contact Support
```

#### Staff Portal Content Model

```
Root: Staff Dashboard (today's focus)
│
├── Level 1: Operational Tasks
│   ├── Queue Management (real-time, actionable)
│   ├── Patient Check-In (fast flow)
│   ├── Patient Profile Review (pre-appointment)
│   └── Walk-In Management (ad-hoc)
│
├── Level 2: Clinical Tasks
│   ├── Medical Coding (codes verification)
│   ├── Data Conflict Resolution (integrity)
│   └── Insurance Verification (billing)
│
├── Level 3: Analytics
│   ├── Today's Performance
│   └── Reports (optional, varies by role)
│
└── Level 4: Account
    ├── Schedule Management
    └── Preferences
```

#### Admin Portal Content Model

```
Root: Admin Dashboard (system-wide view)
│
├── Level 1: System Health & Analytics
│   ├── KPI Dashboard (executive view)
│   ├── Real-time Alerts
│   └── Reports & Trends
│
├── Level 2: User & Access Management
│   ├── User CRUD
│   ├── Role Assignment
│   ├── Activity Audit
│   └── Compliance Reporting
│
├── Level 3: System Configuration
│   ├── Appointment Rules
│   ├── Communication Templates
│   ├── Security Policies
│   └── Integration Settings
│
└── Level 4: Compliance & Governance
    ├── Audit Logs
    ├── Data Retention Policies
    └── Security Settings
```

---

## User Flow Paths

### Critical User Journeys

#### Journey 1: Patient Books Appointment (High Priority)
```
1. Login / Register
   ↓
2. Dashboard (quick stats shown)
   ↓
3. "Search & Book" Button (CTA prominent)
   ↓
4. Search Screen (filters: date, provider, specialty)
   ↓
5. Provider Selection + Calendar (real-time availability)
   ↓
6. [Optional] Preferred Slot Selection (if available)
   ↓
7. Checkout Review
   ↓
8. Confirmation Page (email sent)
   ↓
9. [Conditional] Redirect to Intake (if pending)
```

**Entry Point:** Dashboard CTA or direct link  
**Exit Point:** Confirmation, or Intake completion  
**Mobile Adaptation:** Full-screen modals for steps 4-7, single-column forms

---

#### Journey 2: Staff Manages Queue (High Priority)
```
1. Login as Staff
   ↓
2. Dashboard (today's view + queue widget)
   ↓
3. "Queue Management" or direct from widget
   ↓
4. Real-time Queue List
   │  ├── Drag-drop reorder (for priority)
   │  └── Click patient → Quick profile panel
   │
5. Check-In Patient (click "Check In" button)
   │  └── Status updates in queue
   │
6. [Conditional] Patient arrives → Move to "In-Room"
   │
7. [Conditional] View Patient Profile (tab)
   │  └── Clinical data, conflicts, insurance status
   │
8. [Optional] Resolve Conflicts (if flagged)
   │  └── Side-by-side comparison
   │
9. Complete Appointment (mark finished)
```

**Entry Point:** Dashboard or direct Staff Portal link  
**Exit Point:** End of shift or logout  
**Real-Time:** Queue refreshes every 30 seconds

---

#### Journey 3: Admin Configures System (Medium Priority)
```
1. Login as Admin
   ↓
2. Admin Dashboard (KPIs, alerts)
   ↓
3. "System Configuration" → Select category
   │  ├── Appointment Settings
   │  ├── Notification Templates
   │  └── Security & Compliance
   │
4. Edit Setting (form)
   ↓
5. Save (confirmation message)
   ↓
6. Return to Settings or Dashboard
```

**Entry Point:** Admin Portal sidebar  
**Exit Point:** Back to dashboard  
**Permissions:** Admin-only gated

---

## Cross-Portal Navigation

### Login Flow (All Portals)

```
Anonymous User
│
├── URL: /auth/login
│
├── [Login Page]
│   ├── Email input
│   ├── Password input
│   ├── "Remember me" checkbox
│   ├── Login button
│   ├── Forgot password link
│   ├── Sign up link (patients only)
│   └── Social login (optional)
│
├── [On Submit]
│   ├── Validate credentials
│   │
│   ├── [Invalid] → Show error, stay on login
│   │
│   └── [Valid]
│       ├── Check role (patient/staff/admin)
│       ├── [MFA enabled] → Redirect to MFA screen
│       │   │
│       │   ├── Enter TOTP code
│       │   └── Verify
│       │
│       └── [MFA disabled or verified]
│           ├── Set auth token
│           └── Redirect to portal home
│               ├── Patient → Patient Dashboard
│               ├── Staff → Staff Dashboard
│               └── Admin → Admin Dashboard
│
└── [Error Handling]
    ├── Invalid credentials → Clear, try again
    ├── Account locked → Show unlock flow
    ├── MFA device not recognized → Contact support
    └── Session timeout → Redirect to login
```

### Logout Flow (All Portals)

```
Authenticated User
│
├── Click User Profile Dropdown
│   └── Select "Logout"
│
├── [Confirm logout?]
│   └── Yes / Cancel
│
├── [On Confirm]
│   ├── Clear auth token
│   ├── Invalidate session
│   ├── Clear local storage (if used)
│   └── Redirect to /auth/login
│
└── [Timeout Logout]
    ├── 15-minute inactivity timer (configurable)
    ├── Warning at 2 minutes: "Your session will expire in 2 minutes"
    │   └── Option to extend session
    └── Auto-logout + redirect to login
```

### Role-Based Portal Switching (for multi-role users)

```
User with Multiple Roles (e.g., Staff + Admin)
│
├── [After Login]
│   ├── If single role → Auto-route to portal
│   └── If multiple roles → Show role selector
│       ├── "Continue as Staff" button
│       ├── "Switch to Admin" button
│       └── Default role (from settings)
│
├── [Portal Home]
│   ├── "Switch Role" link in profile dropdown
│   │   └── Return to role selector
│   │
│   └── Different session per role (for security)
```

---

## Screen Inventory & Traceability

### Patient Portal Screens (16 total)

| SCR ID | Screen Name | Path | Purpose | Parent | Children | UXR Mapping |
|--------|------------|------|---------|--------|----------|------------|
| SCR-P-001 | Login | `/auth/login` | Authentication | (root) | Register, MFA, Forgot Password | — |
| SCR-P-002 | Register | `/auth/register` | Account creation | Login | MFA Enrollment | — |
| SCR-P-003 | MFA Verification | `/auth/mfa` | 2FA confirmation | Login, Register | Dashboard | — |
| SCR-P-004 | Search Appointments | `/appointments/search` | Find availability | Dashboard | Provider Selection | UXR-001 |
| SCR-P-005 | Provider Selection | `/appointments/provider` | Choose provider & slot | Search | Preferred Slot | UXR-002, UXR-003 |
| SCR-P-006 | Preferred Slot | `/appointments/preferred` | Optional slot preference | Provider Selection | Checkout | UXR-005 |
| SCR-P-007 | Checkout | `/appointments/checkout` | Confirm booking | Preferred Slot | Confirmation | UXR-004 |
| SCR-P-008 | Confirmation | `/appointments/confirmed` | Success message | Checkout | Intake (conditional) | UXR-004, UXR-006 |
| SCR-P-009 | AI Intake | `/intake/ai` | Chatbot form | Confirmation, Dashboard | Manual Form | UXR-012, UXR-013 |
| SCR-P-010 | Manual Intake | `/intake/form` | Structured form | Confirmation, AI Intake | Dashboard | UXR-014, UXR-015 |
| SCR-P-011 | Profile Dashboard | `/profile/overview` | 360° patient data | Dashboard | Documents | UXR-018, UXR-019 |
| SCR-P-012 | Document Upload | `/profile/documents` | Upload medical docs | Profile Dashboard | Profile Dashboard | UXR-016, UXR-017 |
| SCR-P-013 | Upcoming Appointments | `/appointments/upcoming` | List future apps | Dashboard | Appointment Detail | — |
| SCR-P-014 | Appointment Detail | `/appointments/:id` | View/edit/cancel | Upcoming | Reschedule Modal | UXR-029 |
| SCR-P-015 | Notification Center | `/notifications` | All alerts | Dashboard | — | UXR-006, UXR-007, UXR-028 |
| SCR-P-016 | Preferences | `/settings/preferences` | Reminder config | Settings | Settings (return) | UXR-008, UXR-009 |

### Staff Portal Screens (10 total)

| SCR ID | Screen Name | Path | Purpose | Parent | Children | UXR Mapping |
|--------|------------|------|---------|--------|----------|------------|
| SCR-S-001 | Dashboard | `/staff` | Today's overview | (root) | Queue, Patient Search | — |
| SCR-S-002 | Queue Management | `/queue` | Manage patient line | Dashboard | Patient Profile (inline) | UXR-026 |
| SCR-S-003 | Check-In | `/check-in` | Mark arrival | Queue, Dashboard | Queue (return) | UXR-027 |
| SCR-S-004 | Patient Search | `/patients/search` | Find patient | Dashboard | Patient Profile | — |
| SCR-S-005 | Patient Profile | `/patients/:id/profile` | Clinical data view | Patient Search, Queue | Conflict Resolution | UXR-024, UXR-020 |
| SCR-S-006 | Conflict Resolution | `/patients/:id/conflicts` | Resolve data issues | Patient Profile | Patient Profile (return) | UXR-020, UXR-025 |
| SCR-S-007 | Medical Codes | `/coding/suggest` | ICD-10/CPT codes | Patient Profile | Coding History | UXR-021, UXR-022, UXR-023 |
| SCR-S-008 | Coding History | `/coding/history` | Past code submissions | Medical Codes | — | — |
| SCR-S-009 | Walk-In Form | `/appointments/walk-in` | Quick walk-in entry | Dashboard | Queue (return) | UXR-025 |
| SCR-S-010 | Staff Settings | `/staff/settings` | Personal preferences | Dashboard | — | — |

### Admin Portal Screens (12 total)

| SCR ID | Screen Name | Path | Purpose | Parent | Children | UXR Mapping |
|--------|------------|------|---------|--------|----------|------------|
| SCR-A-001 | Dashboard | `/admin` | System overview | (root) | Reports | — |
| SCR-A-002 | Reports | `/admin/reports` | Analytics builder | Dashboard | — | — |
| SCR-A-003 | User List | `/admin/users` | User management | Dashboard | Add/Edit User | UXR-030 |
| SCR-A-004 | Add/Edit User | `/admin/users/new`, `/admin/users/:id/edit` | Create/modify user | User List | User List (return) | UXR-030 |
| SCR-A-005 | Activity Log | `/admin/audit` | User activity trail | Dashboard | — | — |
| SCR-A-006 | Appointment Settings | `/admin/settings/appointments` | Config options | Dashboard | Settings (return) | UXR-031 |
| SCR-A-007 | Notification Templates | `/admin/settings/templates` | Email/SMS templates | Dashboard | Settings (return) | UXR-031 |
| SCR-A-008 | Security Settings | `/admin/settings/security` | MFA, encryption, etc | Dashboard | Settings (return) | UXR-031 |
| SCR-A-009 | Organization Config | `/admin/settings/organization` | Clinic details | Dashboard | Settings (return) | — |
| SCR-A-010 | Integration Settings | `/admin/settings/integrations` | API keys, OAuth | Dashboard | Settings (return) | — |
| SCR-A-011 | Compliance Audit | `/admin/compliance` | Audit log retention | Dashboard | — | — |
| SCR-A-012 | Help & Resources | `/admin/help` | Documentation | Dashboard | — | — |

---

## Wireframe File References

### High-Fidelity Wireframes Generated

All wireframes are available in `.propel/context/wireframes/Hi-Fi/`:

| Wireframe File | Screen(s) | Type | Key Elements |
|----------------|-----------|------|--------------|
| `wireframe-SCR-P-004-appointment-search.html` | Search Appointments | High-Fi | Filters, results grid, real-time update |
| `wireframe-SCR-P-005-provider-selection.html` | Provider Selection | High-Fi | Provider card, calendar, slot picker |
| `wireframe-SCR-P-008-confirmation.html` | Confirmation | High-Fi | Success badge, appointment details, next steps |
| `wireframe-SCR-P-011-profile-dashboard.html` | Patient Profile | High-Fi | Tabbed interface, conflict indicators, data cards |
| `wireframe-SCR-P-013-upcoming-appointments.html` | Upcoming Appointments | High-Fi | Appointment list, action buttons |
| `wireframe-SCR-S-001-dashboard.html` | Staff Dashboard | High-Fi | KPI cards, queue widget, alerts |
| `wireframe-SCR-S-002-queue-management.html` | Queue Management | High-Fi | Queue list, drag-drop, patient detail panel |
| `wireframe-SCR-S-005-patient-profile.html` | Patient Profile (Staff) | High-Fi | Tabbed interface, quick profile, action buttons |
| `wireframe-SCR-A-001-admin-dashboard.html` | Admin Dashboard | High-Fi | KPI cards, charts, alerts |
| `wireframe-SCR-A-003-user-list.html` | User List | High-Fi | User table, search, action menu |

---

## Mobile Navigation Patterns

### Responsive Behavior

#### Mobile (< 768px)
- **Navigation:** Hamburger menu (sidebar slides from left)
- **Screens:** Stacked vertically, full-width
- **Modals:** Full-screen dialogs
- **Lists:** Card-style view instead of tables
- **Touch Targets:** Min 44px × 44px

#### Tablet (768px - 1023px)
- **Navigation:** Collapsible sidebar + top bar
- **Screens:** 1-2 column layouts
- **Modals:** Centered, max-width 600px
- **Lists:** Hybrid (cards on mobile, tables on tablet+)

#### Desktop (≥ 1024px)
- **Navigation:** Full sidebar + top bar
- **Screens:** 2-3 column layouts
- **Modals:** Centered, max-width 800px
- **Lists:** Full table views with hover effects

---

## Component Library Reference

All wireframes use components from the design system:

- **Buttons:** Primary, Secondary, Tertiary (sizes: sm, md, lg)
- **Forms:** Text input, email, password, select, date picker, checkbox
- **Navigation:** Top bar, sidebar, breadcrumbs, tabs
- **Data Display:** Table, card, list, badge, progress
- **Feedback:** Modal, toast, alert, loading indicator
- **Layout:** Grid (4-12 cols), container, spacing utilities

See `designsystem.md` for complete component specifications and CSS tokens.

---

## Accessibility Compliance

All wireframes follow WCAG 2.2 Level AA standards:

✅ Keyboard Navigation: All interactive elements accessible via Tab  
✅ Screen Readers: Proper semantic HTML, ARIA labels, form associations  
✅ Color Contrast: All text ≥ 4.5:1 contrast (AA) or 3:1 for large text  
✅ Focus Indicators: Clear, visible focus rings on all elements  
✅ Touch Targets: Min 44px × 44px on mobile  
✅ Motion: Respects `prefers-reduced-motion` setting  
✅ Labels & Instructions: All form fields clearly labeled  

---

**Document Status:** Ready for Design Implementation  
**Next Steps:** Convert wireframes to Figma designs, create interactive prototypes

---

**Wireframe Generated By:** Senior UX Designer (AI)  
**Date:** 2026-06-17  
**Version:** 1.0

