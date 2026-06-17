# Figma Design System & Component Library

**Document Version:** 1.0  
**Date:** 2026-06-17  
**Status:** Ready for Figma Implementation  
**Fidelity Level:** Production-Ready  
**Source:** figma_spec.md, designsystem.md, wireframes/

---

## Project Structure Overview

### Figma File Organization (6-Page Structure)

```
PropellQ Design System
├── 📄 Page 1: Design Tokens (Read-Only Reference)
├── 📄 Page 2: Component Library (Master Components)
├── 📄 Page 3: Patient Portal Screens
├── 📄 Page 4: Staff Portal Screens
├── 📄 Page 5: Admin Portal Screens
└── 📄 Page 6: Prototype Flows & Interactions
```

---

## Page 1: Design Tokens (Read-Only Reference)

**Purpose:** Central repository for all design tokens used across the system.

### Color Tokens Frame

| Token Name | Value | Hex | Usage |
|-----------|-------|-----|-------|
| `color-primary-50` | #E8F3FF | Used for light backgrounds, disabled states |
| `color-primary-100` | #D0E7FF | Hover states, secondary backgrounds |
| `color-primary-500` | #0066FF | Primary buttons, links, focus states |
| `color-primary-600` | #0052CC | Primary button hover |
| `color-secondary-500` | #9B7EFF | Secondary actions, accents |
| `color-success-500` | #4CAF50 | Success states, confirmations |
| `color-warning-500` | #FF9800 | Warnings, attention |
| `color-error-500` | #F44336 | Errors, critical alerts |
| `color-info-500` | #2196F3 | Information, notes |
| `color-neutral-0` | #FFFFFF | Backgrounds, cards |
| `color-neutral-50` | #F9FAFB | Subtle backgrounds |
| `color-neutral-100` | #F3F4F6 | Light dividers, section backgrounds |
| `color-neutral-200` | #E5E7EB | Form borders, light dividers |
| `color-neutral-300` | #D1D5DB | Disabled text, secondary borders |
| `color-neutral-500` | #6B7280 | Secondary text, labels |
| `color-neutral-700` | #374151 | Body text |
| `color-neutral-900` | #111827 | Primary text, headings |

### Typography Tokens Frame

| Style Name | Font Family | Size | Weight | Line Height | Usage |
|-----------|------------|------|--------|-------------|-------|
| `typography-display-lg` | System Font | 30.4px | 700 | 1.2 | Page titles, hero sections |
| `typography-heading-lg` | System Font | 27px | 600 | 1.2 | Major section headers |
| `typography-heading-md` | System Font | 21.4px | 600 | 1.3 | Subsection headers |
| `typography-heading-sm` | System Font | 19px | 600 | 1.3 | Card titles, form sections |
| `typography-body-lg` | System Font | 15px | 400 | 1.6 | Rich content, descriptions |
| `typography-body-md` | System Font | 13.5px | 400 | 1.6 | Body copy (default) |
| `typography-body-sm` | System Font | 12px | 400 | 1.6 | Small text, captions |
| `typography-label-md` | System Font | 13.5px | 500 | 1.5 | Form labels |
| `typography-label-sm` | System Font | 12px | 500 | 1.5 | Small labels |
| `typography-code` | Monospace | 13.5px | 400 | 1.5 | Code snippets |

### Spacing Tokens Frame

```
space-0:  0px     space-4:  16px    space-8:  32px
space-1:  4px     space-5:  20px    space-9:  36px
space-2:  8px     space-6:  24px    space-10: 40px
space-3:  12px    space-7:  28px    space-12: 64px
```

### Shadow & Radius Tokens Frame

**Shadows:**
- `shadow-sm`: 0 1px 2px rgba(0,0,0,0.05)
- `shadow-md`: 0 4px 6px rgba(0,0,0,0.1)
- `shadow-lg`: 0 10px 15px rgba(0,0,0,0.1)
- `shadow-xl`: 0 20px 25px rgba(0,0,0,0.15)

**Border Radius:**
- `radius-none`: 0px
- `radius-sm`: 2px
- `radius-md`: 6px
- `radius-lg`: 8px
- `radius-xl`: 12px
- `radius-2xl`: 16px
- `radius-full`: 9999px

---

## Page 2: Component Library (Master Components)

**Purpose:** Reusable component master instances for all screens. Each component includes all interactive states.

### Navigation Components

#### `TopBar` Component
- **Variants:**
  - Default (white background)
  - Dark (dark background for modal overlay)
- **Slots:**
  - Logo (left-aligned text: "PropellQ" in color-primary-500)
  - Center Spacer
  - Right Nav Items (flex row, gap-16px)
- **Nested Components:**
  - `IconButton` (notification bell 🔔, user profile 👤)
  - `Dropdown` (for user menu)
- **Responsive Behavior:**
  - Mobile: 1-column collapse to hamburger menu
  - Tablet: Full width, simplified nav
  - Desktop: Full features

#### `Sidebar` Component
- **Variants:**
  - Expanded (full width 240px)
  - Collapsed (narrow 80px icon-only)
  - Mobile (full overlay, closes on navigation)
- **Content Areas:**
  - Logo section (top)
  - Navigation menu (middle, 6 primary items per portal)
  - User section (bottom)
- **States:**
  - Active nav item (highlight with color-primary-500)
  - Hover (light background)
  - Disabled (grayed out)

#### `Tabs` Component
- **Variants:**
  - Horizontal (default)
  - Vertical (for side navigation)
- **States per Tab:**
  - Active (underline color-primary-500, bold text)
  - Inactive (gray text)
  - Hover (light background)
  - Disabled (grayed out)
- **Responsive:** Horizontal→Vertical at mobile breakpoint

#### `Breadcrumb` Component
- **Structure:** Icon → Text → Separator → ... → Text
- **States:**
  - Link (color-primary-500, underline on hover)
  - Current (bold, gray, no link)
  - Disabled (neutral-300)

### Form Components

#### `TextInput` Component
- **Variants:**
  - Default (neutral-200 border)
  - Filled (color-neutral-50 background)
  - Search (with search icon)
- **States:**
  - Default (neutral-200 border)
  - Focus (color-primary-500 border, shadow-md)
  - Filled (color-neutral-50 background)
  - Disabled (grayed, not interactive)
  - Error (color-error-500 border)
  - Success (color-success-500 border)
- **Sizes:** Small (32px), Medium (40px), Large (48px)
- **Left/Right Icons:** Optional slots for icons or actions

#### `Select` Component
- **States:**
  - Closed (shows selected value)
  - Open (dropdown menu visible, items list)
  - Hover (over options)
- **Nested:** Uses `MenuItem` component for options
- **Sizes:** Small, Medium, Large (same heights as TextInput)

#### `DatePicker` Component
- **Display:**
  - Calendar grid (7 columns for days, 6 rows)
  - Month/year selector (top)
  - Navigation arrows
- **States:**
  - Selected (color-primary-500 background)
  - Hover (light background)
  - Today (border accent)
  - Disabled (grayed)
- **Responsive:** Full calendar desktop, compact picker mobile

#### `TimePicker` Component
- **Variants:**
  - Dropdown (select from preset times: Morning, Afternoon, Evening, Any)
  - Clock (visual 12-hour clock with hour/minute selection)
- **Presets:** 15-min, 30-min, 1-hour intervals

#### `Checkbox` Component
- **Sizes:** Small (16px), Medium (20px), Large (24px)
- **States:**
  - Unchecked (neutral-200 border)
  - Checked (color-primary-500 background, white checkmark)
  - Indeterminate (dash icon)
  - Disabled (grayed)
- **Variants:** Default, Error, Success

#### `RadioButton` Component
- **Sizes:** Small (16px), Medium (20px), Large (24px)
- **States:**
  - Unselected (neutral-200 border circle)
  - Selected (color-primary-500 border with filled inner circle)
  - Disabled (grayed)

#### `Toggle` Component
- **Sizes:** Small, Medium, Large
- **States:**
  - Off (gray background)
  - On (color-primary-500 background)
  - Disabled (grayed)

#### `FormLabel` Component
- **Typography:** typography-label-md
- **Color:** color-neutral-700
- **Optional:** Red asterisk (*) for required fields
- **Helpers:** Description text below in typography-body-sm, color-neutral-500

### Button Components

#### `Button` Component (Primary)
- **Sizes:** Small (32px), Medium (40px), Large (48px)
- **States:**
  - Default (color-primary-500 background, white text)
  - Hover (color-primary-600 background)
  - Active (darker shade)
  - Disabled (neutral-200 background, neutral-300 text)
  - Loading (spinner animation)
- **Icon Support:** Left/right icon slots
- **Text Alignment:** Center, with optional icon + text

#### `Button` Component (Secondary)
- **Sizes:** Small, Medium, Large
- **States:**
  - Default (color-neutral-100 background, color-neutral-900 text)
  - Hover (color-neutral-200 background)
  - Active (darker shade)
  - Disabled (neutral-100 background, neutral-300 text)
- **Icon Support:** Yes

#### `Button` Component (Tertiary/Ghost)
- **Sizes:** Small, Medium, Large
- **States:**
  - Default (transparent, color-primary-500 text)
  - Hover (color-neutral-50 background)
  - Active (darker shade)
  - Disabled (neutral-300 text)
- **Icon Support:** Yes

#### `Button` Component (Danger)
- **Sizes:** Small, Medium, Large
- **States:**
  - Default (color-error-500 background, white text)
  - Hover (darker shade)
  - Active (even darker)
  - Disabled (neutral-200 background)

#### `Button` Component (Success)
- **Sizes:** Small, Medium, Large
- **States:**
  - Default (color-success-500 background, white text)
  - Hover (darker shade)
  - Disabled (neutral-200)

#### `Link` Component
- **States:**
  - Default (color-primary-500, underline)
  - Hover (color-primary-600, underline)
  - Active (visited state)
  - Disabled (color-neutral-300, no underline)
- **Icon Support:** Yes (for external links, downloads, etc.)

### Card Components

#### `Card` Component
- **Sizes:** Small (300px), Medium (400px), Large (500px+)
- **Structure:**
  - Header (optional): Title + subtitle, space-4 padding
  - Body: Main content, space-6 padding
  - Footer (optional): Action buttons, space-4 padding
- **Styling:** color-neutral-0 background, border-1px color-neutral-200, radius-md, shadow-sm
- **States:**
  - Default (shadow-sm)
  - Hover (shadow-md, cursor pointer)
  - Active (border-2 color-primary-500)

#### `AppointmentCard` Component
- **Extends:** Card Component
- **Fields:**
  - Provider name (typography-heading-sm)
  - Specialty (typography-body-sm, gray)
  - Location badge (color-primary-50 background, blue text)
  - Date/Time (typography-body-md)
  - Rating (⭐ emoji + number)
  - Select button (CTA)

#### `QueueItemCard` Component
- **Extends:** Card Component
- **Fields:**
  - Patient name (typography-heading-sm)
  - Appointment status (badge: waiting/checked-in/in-room)
  - Waiting time
  - Quick action buttons

#### `StatCard` Component (Admin Dashboard)
- **Extends:** Card Component
- **Fields:**
  - Stat name (typography-label-md, gray)
  - Stat value (typography-display-lg, primary color)
  - Trend indicator (📈 up, 📉 down)
  - Trend description (typography-body-sm)
- **Color Variants:** Primary, Warning, Success, Error

### Badge Components

#### `Badge` Component
- **Sizes:** Small (24px), Medium (32px), Large (40px)
- **Variants:**
  - Primary (color-primary-500 background)
  - Success (color-success-500 background)
  - Warning (color-warning-500 background)
  - Error (color-error-500 background)
  - Info (color-info-500 background)
- **Shape:** Pill-shaped (radius-full)
- **Text:** White, center-aligned

#### `StatusBadge` Component
- **States:**
  - Waiting (color-warning-500 + "⏳" icon)
  - Checked-In (color-info-500 + "✓" icon)
  - In-Room (color-success-500 + "→" icon)
  - Completed (color-success-500 + "✓" icon)
  - Cancelled (color-error-500 + "✕" icon)

### Data Display Components

#### `DataTable` Component
- **Structure:**
  - Header row (typography-label-md, color-neutral-500 text)
  - Data rows (typography-body-sm)
  - Footer with pagination
- **Styling:** Striped rows (alternate color-neutral-0 and color-neutral-50)
- **Interactive:**
  - Hover rows (highlight with color-neutral-50)
  - Sortable headers (arrow icon on hover)
  - Selectable rows (checkbox column)
- **Responsive:** Horizontal scroll on mobile

#### `List` Component
- **Item:** Flex row with icon, primary text, secondary text, optional action button
- **States:**
  - Default
  - Hover (color-neutral-50 background)
  - Selected (color-primary-50 background, border-left color-primary-500)
- **Dividers:** Between items (color-neutral-200)

#### `Pagination` Component
- **Elements:** Prev button | Page numbers | Next button
- **States:**
  - Default (color-primary-500 links)
  - Current page (bold, darker)
  - Disabled (neutral-300 text, not clickable)
- **Responsive:** Show fewer page numbers on mobile

### Feedback Components

#### `Alert` Component
- **Variants:** Info, Success, Warning, Error
- **Structure:**
  - Icon (left, size 24px)
  - Title (typography-heading-sm)
  - Description (typography-body-sm)
  - Close button (optional)
- **Colors (background + border + icon):**
  - Info: color-info-50 + color-info-500
  - Success: color-success-50 + color-success-500
  - Warning: color-warning-50 + color-warning-500
  - Error: color-error-50 + color-error-500

#### `Toast` Component
- **Size:** Width 320px, position bottom-right
- **Variants:** Info, Success, Warning, Error (same color scheme as Alert)
- **Auto-dismiss:** 4 second animation out
- **Stack:** Multiple toasts stack vertically

#### `Modal` Component
- **Structure:**
  - Header: Title + close button (X)
  - Body: Content (scrollable if tall)
  - Footer: Action buttons (right-aligned)
- **Backdrop:** Semi-transparent (rgba(0,0,0,0.5))
- **Animation:** Fade in/out (200ms ease-out)
- **Responsive:** Full-screen on mobile, centered on desktop

#### `Tooltip` Component
- **Size:** Auto-width, max 200px
- **Styling:** Dark background (color-neutral-900), white text, radius-sm
- **Arrow:** Pointing to trigger element
- **Position:** Auto-flip (top/bottom)
- **Trigger:** Hover or focus on icon

#### `Spinner` Component (Loading)
- **Sizes:** Small (20px), Medium (32px), Large (48px)
- **Animation:** Continuous rotation (1s per rotation, linear)
- **Color:** color-primary-500
- **Variants:** Default circle, dots (3 dots bouncing)

#### `ProgressBar` Component
- **Width:** 100% container
- **Height:** 4px or 8px
- **States:**
  - Indeterminate (animated, stripes moving)
  - Determinate (shows percentage, 0-100%)
- **Color Variants:** Primary, Success, Warning, Error

### Custom Portal Components

#### `PatientIntakeCard` Component
- **Extends:** Card Component
- **Fields:**
  - AI/Manual toggle
  - Progress indicator
  - Form questions (dynamic)
  - Next/Previous/Submit buttons

#### `ClinicalDataCard` Component
- **Extends:** Card Component
- **Fields:**
  - Data type (diagnosis, medication, allergy)
  - Value + source
  - Confidence score (if AI-generated)
  - Action buttons (verify, resolve conflict, edit)

#### `ConflictResolutionPanel` Component
- **Structure:**
  - Source 1 data block (left)
  - "VS" divider (center)
  - Source 2 data block (right)
  - "Accept / Reject / Both" buttons (bottom)
- **Styling:** Red border (color-error-500), light red background (color-error-50)

---

## Page 3: Patient Portal Screens

**Frames organized by user flow:**

### Authentication Flow

#### Frame: `SCR-P-001-Login`
- **Size:** 1024×768px (responsive 375px mobile variant)
- **Components:**
  - TopBar (PropellQ logo centered)
  - Form card (centered, white background)
    - Email input (TextInput)
    - Password input (TextInput, masked)
    - "Remember me" checkbox
    - "Sign in" button (primary)
    - "Forgot password?" link
    - "Sign up" link
  - Footer (company info, terms, privacy)
- **States:** Default, Loading, Error (red alert banner)

#### Frame: `SCR-P-002-MFA`
- **Components:**
  - Step indicator (2 of 2)
  - OTP input (6 digit boxes)
  - "Verify" button
  - "Resend code" link
  - "Use backup code" link

#### Frame: `SCR-P-003-SignUp`
- **Components:** Similar to login but with additional fields (name, DOB, phone)

### Appointment Booking Flow

#### Frame: `SCR-P-004-Search`
- **Components:** (Already wireframed)
  - Filter section (date, time, provider, specialty)
  - Results grid (provider cards)
  - Recently viewed section
- **Responsive:** 4-col desktop → 2-col tablet → 1-col mobile

#### Frame: `SCR-P-005-Provider-Selection`
- **Components:**
  - Provider name + specialty + bio
  - Provider availability calendar (DatePicker)
  - Time slot picker (TimePicker dropdown)
  - Insurance/payment info summary
  - "Continue" CTA button

#### Frame: `SCR-P-006-Preferred-Slot`
- **Components:**
  - Current selected slot (display)
  - "Choose alternative" toggle
  - Slot preference picker (dual calendar)
  - "Confirm selection" button

#### Frame: `SCR-P-007-Checkout`
- **Components:**
  - Appointment summary card
  - Patient info summary
  - Insurance verification section
  - Payment method selector (if applicable)
  - Terms checkbox
  - "Book appointment" CTA button

#### Frame: `SCR-P-008-Confirmation`
- **Components:**
  - Success icon (🎉)
  - Confirmation number (copy-to-clipboard)
  - Appointment details card
  - Next steps (intake form CTA)
  - Add to calendar button
  - "View appointment" link

### Patient Profile

#### Frame: `SCR-P-011-Profile-Dashboard`
- **Components:** (Already wireframed)
  - Profile header (avatar + name + MRN)
  - Tabs (Overview, Medications, Allergies, Diagnoses, Documents, Insurance)
  - Tab content changes based on selection
  - Edit profile button

### Intake Forms

#### Frame: `SCR-P-009-AI-Intake`
- **Components:**
  - Header ("AI-Assisted Health Intake")
  - Progress bar (current step of total)
  - Chatbot message (AI asks question)
  - User response options (buttons or text input)
  - Navigation buttons (Previous/Next)

#### Frame: `SCR-P-010-Manual-Intake`
- **Components:**
  - Multi-step form (progress indicator)
  - Form sections (medical history, medications, allergies)
  - Conditional fields (show/hide based on answers)
  - Save & continue button

### Additional Patient Screens

#### Frame: `SCR-P-012-Document-Upload`
- **Components:**
  - Drag-drop zone (dashed border, upload icon)
  - File list (after upload)
  - Processing status (spinner + "Extracting data...")
  - Document preview

#### Frame: `SCR-P-013-Upcoming-Appointments`
- **Components:**
  - List of appointment cards
  - Each card shows: Provider, date, time, status, actions (reschedule, cancel, check-in if time is near)
  - Empty state ("No upcoming appointments")

#### Frame: `SCR-P-014-Appointment-Detail`
- **Components:**
  - Full appointment info
  - Appointment timeline (scheduled → confirmed → reminder sent → check-in)
  - Actions (reschedule, cancel, add notes)
  - Provider contact info

#### Frame: `SCR-P-015-Notifications`
- **Components:**
  - Notification list (most recent first)
  - Each notification: Icon + title + timestamp + "Mark as read" action
  - Filter tabs (All, Unread, Appointments, Intake, System)

#### Frame: `SCR-P-016-Settings`
- **Components:**
  - Sidebar menu (profile, notifications, privacy, security, communication preferences)
  - Settings panels (change per selection)
  - Save changes button

---

## Page 4: Staff Portal Screens

### Queue Management

#### Frame: `SCR-S-001-Dashboard`
- **Components:**
  - KPI cards (today's appointments, current queue, avg wait time, system health)
  - Queue widget (live queue list, top 5)
  - Charts (appointments today, no-show trend)
  - Quick actions (add walk-in, send reminder)

#### Frame: `SCR-S-002-Queue-Management`
- **Components:** (Already wireframed)
  - Left: Queue list (draggable items, status badges)
  - Center: Patient detail panel (tabs: demographics, medical, alerts)
  - Right: Action buttons
  - Real-time updates badge

#### Frame: `SCR-S-003-Check-In`
- **Components:**
  - Patient scan/search field
  - Patient info card (quick verify)
  - "Check-in confirmed" success feedback
  - Next patient button

### Patient Management

#### Frame: `SCR-S-004-Patient-Search`
- **Components:**
  - Search input (autocomplete, filters)
  - Results table (name, MRN, last visit, status)
  - Patient detail modal (on selection)

#### Frame: `SCR-S-005-Patient-Profile-Staff`
- **Components:**
  - 360° patient view (similar to patient version but with staff-specific actions)
  - Conflict resolution section (if conflicts exist)
  - Notes section (staff-only)
  - Medical coding suggestions

### Medical Coding

#### Frame: `SCR-S-006-Conflict-Resolution`
- **Components:** (Already wireframed as part of design)
  - ConflictResolutionPanel component
  - Conflict details + source info
  - "Accept / Reject / Manually Resolve" buttons
  - Audit trail (showing who resolved it, when)

#### Frame: `SCR-S-007-Medical-Codes`
- **Components:**
  - Code suggestion list (ICD-10, CPT codes)
  - Each item: Code + description + confidence % + auto-accept toggle
  - Bulk actions (accept all, review all)
  - Search/filter by code type

#### Frame: `SCR-S-008-Coding-History`
- **Components:**
  - Table of previous codings
  - Columns: Date, Patient, Codes, Provider, Confidence, Status
  - Audit log access

### Administrative

#### Frame: `SCR-S-009-Walk-In-Form`
- **Components:**
  - Patient info form (name, DOB, phone)
  - New patient toggle
  - Chief complaint textarea
  - "Create appointment" button
  - "Add to queue" button

#### Frame: `SCR-S-010-Settings`
- **Components:**
  - Profile settings
  - Notification preferences
  - Coding preferences

---

## Page 5: Admin Portal Screens

### Analytics & Reporting

#### Frame: `SCR-A-001-Dashboard`
- **Components:** (Already wireframed)
  - KPI cards (appointments, no-show rate, wait time, uptime, active users, pending items)
  - Charts (trends, distributions)
  - Alerts panel
  - Performance table

#### Frame: `SCR-A-002-Reports`
- **Components:**
  - Report type selector (dropdown)
  - Date range picker
  - Export buttons (PDF, CSV, Excel)
  - Report preview/table

### User Management

#### Frame: `SCR-A-003-User-List`
- **Components:**
  - Table: Name, Email, Role, Status, Last Active, Actions (edit, deactivate)
  - Bulk actions (select multiple, deactivate, send message)
  - Add user button (CTA)
  - Filter sidebar (by role, status, department)

#### Frame: `SCR-A-004-Add-Edit-User`
- **Components:**
  - Form sections: Personal info, Role assignment, Permissions, Notifications
  - Multi-select roles (Patient, Staff, Admin)
  - Save/Cancel buttons
  - Delete user link (for edit mode)

#### Frame: `SCR-A-005-Activity-Log`
- **Components:**
  - Timeline of user actions
  - Filters: Date range, user, action type, result
  - Export button
  - Details modal (on row click)

### System Configuration

#### Frame: `SCR-A-006-Appointment-Settings`
- **Components:**
  - Settings form (appointment duration, cancellation window, no-show threshold)
  - Save changes button
  - Restore defaults link

#### Frame: `SCR-A-007-Notification-Templates`
- **Components:**
  - Template selector (email, SMS)
  - Template editor (WYSIWYG, drag-drop blocks)
  - Variable insertion helpers ({{patient_name}}, {{appointment_time}})
  - Preview pane
  - Save/Cancel buttons

#### Frame: `SCR-A-008-Security-Settings`
- **Components:**
  - MFA enforcement (toggle)
  - Password policy (min length, complexity)
  - Session timeout
  - IP whitelist (optional)
  - Encryption settings (read-only reference)

---

## Page 6: Prototype Flows & Interactions

**Clickable prototype frames showing user journeys with hotspots and transitions:**

### Patient Booking Flow Prototype

```
SCR-P-001 (Login)
  ↓ [Sign In button]
SCR-P-004 (Search)
  ↓ [Select Slot]
SCR-P-005 (Provider Selection)
  ↓ [Continue]
SCR-P-006 (Preferred Slot)
  ↓ [Confirm Selection]
SCR-P-007 (Checkout)
  ↓ [Book Appointment]
SCR-P-008 (Confirmation)
  ↓ [Start Intake] OR [Done]
SCR-P-009 (AI Intake) OR SCR-P-010 (Manual Intake)
  ↓ [Submit]
SCR-P-011 (Profile Dashboard)
```

**Hotspots & Interactions:**
- All buttons have hover state (shadow-md, cursor pointer)
- Form inputs show focus state (color-primary-500 border, shadow)
- Navigation tabs update content with 200ms fade animation
- Modal dialogs have overlay backdrop with fade-in animation

### Staff Queue Management Flow Prototype

```
SCR-S-001 (Dashboard)
  ↓ [View Queue]
SCR-S-002 (Queue Management)
  ↓ [Drag to reorder] OR [Click patient for detail]
  ↓ [Action button]
SCR-S-003 (Check-In)
  ↓ [Check-In Complete]
SCR-S-002 (Queue updated, next patient ready)
```

**Hotspots & Interactions:**
- Queue items are draggable (visual feedback on drag)
- Patient detail panel updates on queue item selection
- Check-in scanner has input focus state
- Toast notification appears on successful check-in

### Admin Dashboard Flow Prototype

```
SCR-A-001 (Dashboard)
  ↓ [Alert link]
SCR-A-006 / SCR-A-007 / SCR-A-008 (Settings)
  ↓ [Save changes]
SCR-A-001 (Dashboard updated with changes)
```

**Hotspots & Interactions:**
- Chart areas are interactive (hover shows data points)
- Alert items have link navigation
- Settings modals close with overlay click or X button
- Form inputs validate on blur (show error state if invalid)

---

## Component Integration Rules

### Responsive Behavior Matrix

| Screen Size | Grid Cols | Font Scale | Spacing Scale | Component Changes |
|------------|-----------|-----------|----------------|-------------------|
| Mobile (375px) | 1-2 | 0.9x | 0.85x | Sidebar→Hamburger, Modals fullscreen, Tables scroll |
| Tablet (768px) | 4-8 | 0.95x | 0.9x | Sidebar collapsed option, Cards 2-col |
| Desktop (1024px+) | 12 | 1x | 1x | Full sidebar, Cards 3-4 col |

### State Transition Animations

- **Button states:** 100ms ease-out
- **Modal open/close:** 200ms ease-out
- **Page transitions:** 150ms fade
- **Hover effects:** 100ms ease-in

### Accessibility Requirements

- All interactive elements have focus indicators (outline or ring)
- Color alone never indicates state (use text + color + icon)
- Minimum touch target 44×44px
- Form labels associated with inputs via `label for` or ARIA
- ARIA roles on custom components (button, role="button", etc.)

---

## Export Specifications

### Image Exports

**For each key screen (10 screens):**
- Export as JPG (100% quality)
- Dimensions: 1024×768px (desktop), 375×667px (mobile)
- Naming: `export-SCR-{ID}-{name}-{device}.jpg`

**Location:** `.propel/context/figma/exports/`

### Component Library Export

- Figma component JSON export (for design handoff)
- CSS file with design tokens (for engineering)
- Storybook documentation (for development)

### Prototype Link

- Figma sharing link with comment permissions enabled
- Documented in `.propel/context/figma/prototype-link.md`

---

## Figma File Specifications

### Setup & Configuration

- **File Name:** PropellQ Design System v1.0
- **Color Mode:** RGB
- **Grid:** 8px modular grid (visible, lock guides)
- **Typography:** System font installed locally
- **Plugins:** Figma Tokens plugin recommended for token sync
- **Sharing:** Team access (Editor), Stakeholder access (Viewer)

### Page Locks & Protections

- **Page 1 (Design Tokens):** Locked (read-only reference)
- **Page 2 (Components):** Locked components, unlocked for edits with specific permissions
- **Pages 3-5 (Screens):** Unlocked for design changes
- **Page 6 (Prototypes):** Locked (finalized flows)

### Version Control

- **Versioning:** Use Figma version history
- **Save frequency:** After each design decision
- **Backup:** Export to `.propel/context/figma/backups/`

---

## Next Steps

1. **Create Figma Project** using this specification
2. **Set up component library** from Page 2 definitions
3. **Build screen frames** from wireframes (Pages 3-5)
4. **Configure prototype flows** with hotspot interactions (Page 6)
5. **Export assets** (JPG screens, CSS tokens, JSON components)
6. **Share with stakeholders** for review and feedback
7. **Hand off to development team** with Figma link + design tokens

---

**Figma Design System Status:** Ready for Implementation  
**Last Updated:** 2026-06-17  
**Version:** 1.0

