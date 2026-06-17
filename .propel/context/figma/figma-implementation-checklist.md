# Figma Design System Implementation Checklist

**Document Version:** 1.0  
**Date:** 2026-06-17  
**Status:** Complete  
**Purpose:** Comprehensive checklist for Figma design system creation and implementation

---

## Pre-Implementation: Design Preparation

- [x] Wireframes created (high-fidelity HTML prototypes)
- [x] Design system tokens finalized (colors, typography, spacing)
- [x] Component specifications documented
- [x] Screen inventory finalized (38 screens, 3 portals)
- [x] User flows mapped and prototyped

---

## Figma Project Setup

- [ ] Create new Figma file: "PropellQ Design System v1.0"
- [ ] Set up 6-page structure:
  - [ ] Page 1: Design Tokens (Read-Only Reference)
  - [ ] Page 2: Component Library (Master Components)
  - [ ] Page 3: Patient Portal Screens
  - [ ] Page 4: Staff Portal Screens
  - [ ] Page 5: Admin Portal Screens
  - [ ] Page 6: Prototype Flows & Interactions
- [ ] Configure grid (8px modular grid)
- [ ] Set up typography library (system font stack)
- [ ] Import/create color palette
- [ ] Install Figma Tokens plugin (for token sync)

---

## Page 1: Design Tokens Implementation

### Colors

- [ ] Create frame: "Color Palette Primary"
  - [ ] Add 9-step scale for primary color (#E8F3FF → #001433)
  - [ ] Add color swatches with labels and hex values
  
- [ ] Create frame: "Semantic Colors"
  - [ ] Success (4CAF50) with variants
  - [ ] Warning (FF9800) with variants
  - [ ] Error (F44336) with variants
  - [ ] Info (2196F3) with variants

- [ ] Create frame: "Neutral Grayscale"
  - [ ] Grayscale from white to black (16 steps)
  - [ ] Label each with token name and hex value

- [ ] Document WCAG compliance
  - [ ] Verify 4.5:1 contrast for all semantic colors

### Typography

- [ ] Create frame: "Font Sizes"
  - [ ] Display all 8-point modular scale sizes (12px → 30.4px)
  - [ ] Label each with token name

- [ ] Create frame: "Text Styles"
  - [ ] typography-display-lg
  - [ ] typography-heading-lg/md/sm
  - [ ] typography-body-lg/md/sm
  - [ ] typography-label-md/sm
  - [ ] typography-caption
  - [ ] typography-code

- [ ] Create frame: "Font Weights"
  - [ ] Show all 4 weights (400, 500, 600, 700)

### Spacing & Other Tokens

- [ ] Create frame: "Spacing Scale"
  - [ ] All 12 spacing values (0px → 64px)

- [ ] Create frame: "Shadows"
  - [ ] shadow-sm, shadow-md, shadow-lg, shadow-xl
  - [ ] Show visual examples

- [ ] Create frame: "Border Radius"
  - [ ] All 7 radius values

- [ ] Create frame: "Animation Tokens"
  - [ ] Durations (100ms, 200ms, 300ms, 500ms)
  - [ ] Easing functions (ease-in, ease-out, ease-in-out)

---

## Page 2: Component Library Implementation

### Navigation Components

- [ ] TopBar component
  - [ ] Variant: Default (white)
  - [ ] Variant: Dark (dark background)
  - [ ] Slot: Logo
  - [ ] Slot: Navigation items
  - [ ] Responsive behavior documented

- [ ] Sidebar component
  - [ ] Variant: Expanded (240px)
  - [ ] Variant: Collapsed (80px)
  - [ ] Variant: Mobile (full overlay)
  - [ ] Menu items with states (active, hover, disabled)

- [ ] Tabs component
  - [ ] Variant: Horizontal
  - [ ] Variant: Vertical
  - [ ] States: Active, Inactive, Hover, Disabled
  - [ ] Responsive behavior

- [ ] Breadcrumb component
  - [ ] States: Link, Current, Disabled

### Form Components

- [ ] TextInput component
  - [ ] Variant: Default, Filled, Search
  - [ ] States: Default, Focus, Filled, Disabled, Error, Success
  - [ ] Sizes: Small (32px), Medium (40px), Large (48px)
  - [ ] Icon slots (left/right)

- [ ] Select component
  - [ ] States: Closed, Open, Hover
  - [ ] Sizes: Small, Medium, Large
  - [ ] With MenuItems nested

- [ ] DatePicker component
  - [ ] Calendar grid (7×6)
  - [ ] Month/year selector
  - [ ] States: Selected, Hover, Today, Disabled

- [ ] TimePicker component
  - [ ] Variant: Dropdown (presets)
  - [ ] Variant: Clock (visual picker)

- [ ] Checkbox component
  - [ ] Sizes: Small (16px), Medium (20px), Large (24px)
  - [ ] States: Unchecked, Checked, Indeterminate, Disabled

- [ ] RadioButton component
  - [ ] Sizes: Small, Medium, Large
  - [ ] States: Unselected, Selected, Disabled

- [ ] Toggle component
  - [ ] Sizes: Small, Medium, Large
  - [ ] States: Off, On, Disabled

- [ ] FormLabel component
  - [ ] With optional red asterisk (required)
  - [ ] With helper text variant

### Button Components

- [ ] Button Primary
  - [ ] Sizes: Small (32px), Medium (40px), Large (48px)
  - [ ] States: Default, Hover, Active, Disabled, Loading
  - [ ] Icon support (left/right)

- [ ] Button Secondary
  - [ ] All size/state variants

- [ ] Button Tertiary/Ghost
  - [ ] All size/state variants

- [ ] Button Danger
  - [ ] All size/state variants

- [ ] Button Success
  - [ ] All size/state variants

- [ ] Link component
  - [ ] States: Default, Hover, Active, Disabled

### Card & Data Components

- [ ] Card component
  - [ ] Sizes: Small, Medium, Large
  - [ ] Slots: Header, Body, Footer
  - [ ] States: Default, Hover, Active

- [ ] AppointmentCard component (extends Card)
  - [ ] All required fields

- [ ] QueueItemCard component (extends Card)
  - [ ] All required fields

- [ ] StatCard component (Admin Dashboard)
  - [ ] Color variants: Primary, Warning, Success, Error
  - [ ] Trend indicators

### Badge Components

- [ ] Badge component
  - [ ] Sizes: Small (24px), Medium (32px), Large (40px)
  - [ ] Variants: Primary, Success, Warning, Error, Info

- [ ] StatusBadge component
  - [ ] States: Waiting, Checked-In, In-Room, Completed, Cancelled

### Data Display

- [ ] DataTable component
  - [ ] Header row styling
  - [ ] Data rows with striping
  - [ ] Sortable header indicators
  - [ ] Selectable rows (checkboxes)
  - [ ] Pagination footer

- [ ] List component
  - [ ] Item structure (icon, text, action)
  - [ ] States: Default, Hover, Selected
  - [ ] Dividers between items

- [ ] Pagination component
  - [ ] Prev/Next buttons
  - [ ] Page number buttons
  - [ ] States: Default, Current, Disabled

### Feedback Components

- [ ] Alert component
  - [ ] Variants: Info, Success, Warning, Error
  - [ ] With icon, title, description

- [ ] Toast component
  - [ ] All variants
  - [ ] Size: 320px width
  - [ ] Auto-dismiss animation

- [ ] Modal component
  - [ ] Structure: Header, Body, Footer
  - [ ] Backdrop overlay
  - [ ] Close button (X)

- [ ] Tooltip component
  - [ ] Dark background styling
  - [ ] Arrow pointer
  - [ ] Auto-flip positioning

- [ ] Spinner component
  - [ ] Sizes: Small (20px), Medium (32px), Large (48px)
  - [ ] Animated rotation

- [ ] ProgressBar component
  - [ ] States: Indeterminate, Determinate
  - [ ] Color variants

### Custom Portal Components

- [ ] PatientIntakeCard component
- [ ] ClinicalDataCard component
- [ ] ConflictResolutionPanel component

---

## Page 3: Patient Portal Screens

### Authentication Flow

- [ ] SCR-P-001: Login screen
  - [ ] TopBar, Login form card, Footer
  - [ ] Form states: Default, Loading, Error

- [ ] SCR-P-002: MFA screen
  - [ ] Step indicator
  - [ ] OTP input (6 digits)
  - [ ] Verify button, Resend link

- [ ] SCR-P-003: Sign Up screen
  - [ ] Extended form fields

### Appointment Booking Flow

- [ ] SCR-P-004: Search & Book
  - [ ] Filter section (4-column desktop, 1-column mobile)
  - [ ] Results grid with provider cards

- [ ] SCR-P-005: Provider Selection
  - [ ] Provider info + availability calendar + time picker

- [ ] SCR-P-006: Preferred Slot
  - [ ] Current slot display + alternative picker

- [ ] SCR-P-007: Checkout
  - [ ] Appointment summary + insurance + payment

- [ ] SCR-P-008: Confirmation
  - [ ] Success state + confirmation number

### Patient Profile & Intake

- [ ] SCR-P-009: AI-Assisted Intake
  - [ ] Progress bar + chatbot messages + options

- [ ] SCR-P-010: Manual Intake Form
  - [ ] Multi-step form with validation states

- [ ] SCR-P-011: Profile Dashboard
  - [ ] Tabs: Overview, Medications, Allergies, Diagnoses, Documents, Insurance

### Additional Screens

- [ ] SCR-P-012: Document Upload
- [ ] SCR-P-013: Upcoming Appointments
- [ ] SCR-P-014: Appointment Detail
- [ ] SCR-P-015: Notifications
- [ ] SCR-P-016: Settings

---

## Page 4: Staff Portal Screens

- [ ] SCR-S-001: Dashboard
  - [ ] KPI cards, queue widget, charts

- [ ] SCR-S-002: Queue Management
  - [ ] 3-panel layout (queue, patient detail, actions)
  - [ ] Draggable queue items

- [ ] SCR-S-003: Check-In
  - [ ] Patient search/scan + confirm

- [ ] SCR-S-004: Patient Search
  - [ ] Search input with autocomplete + results table

- [ ] SCR-S-005: Patient Profile (Staff View)
  - [ ] 360° view with staff-specific actions

- [ ] SCR-S-006: Conflict Resolution
  - [ ] ConflictResolutionPanel component

- [ ] SCR-S-007: Medical Codes
  - [ ] Code suggestion list with confidence scores

- [ ] SCR-S-008: Coding History
  - [ ] Table of previous codings

- [ ] SCR-S-009: Walk-In Form
  - [ ] Patient info form

- [ ] SCR-S-010: Settings

---

## Page 5: Admin Portal Screens

- [ ] SCR-A-001: Dashboard
  - [ ] KPI cards, charts, alerts panel, performance table

- [ ] SCR-A-002: Reports
  - [ ] Report selector, date range, export buttons

- [ ] SCR-A-003: User List
  - [ ] User table with actions, bulk operations

- [ ] SCR-A-004: Add/Edit User
  - [ ] User form with role/permission sections

- [ ] SCR-A-005: Activity Log
  - [ ] Timeline of user actions with filters

- [ ] SCR-A-006: Appointment Settings
  - [ ] Settings form

- [ ] SCR-A-007: Notification Templates
  - [ ] Template editor with variable insertion

- [ ] SCR-A-008: Security Settings
  - [ ] MFA, password policy, session timeout settings

---

## Page 6: Prototype Flows & Interactions

### Setup Prototype Flows

- [ ] Configure flow: Patient Booking Journey
  - [ ] SCR-P-004 → SCR-P-005 → SCR-P-006 → SCR-P-007 → SCR-P-008
  - [ ] Conditional branch to SCR-P-009/010 or SCR-P-011

- [ ] Configure flow: Staff Queue Management
  - [ ] SCR-S-001 → SCR-S-002
  - [ ] Queue item interactions (selection, reordering)

- [ ] Configure flow: Admin Dashboard Settings
  - [ ] SCR-A-001 → Settings pages

- [ ] Configure flow: Patient Intake
  - [ ] SCR-P-009 (AI chatbot) or SCR-P-010 (Manual form)

- [ ] Configure flow: Conflict Resolution
  - [ ] Modal overlay on SCR-S-002

### Setup Interactive Hotspots

- [ ] Button hotspots (all screens)
  - [ ] Set transitions (fade, slide, scale)
  - [ ] Set animation duration (200ms)

- [ ] Form input interactions
  - [ ] Show focus states
  - [ ] Error state transitions

- [ ] Modal hotspots
  - [ ] Backdrop close behavior
  - [ ] X button close

- [ ] Draggable elements (queue items)
  - [ ] Visual feedback on drag start
  - [ ] Drop target highlighting

---

## Design Review & Validation

- [ ] Design review with stakeholders
  - [ ] Verify all screens match specifications
  - [ ] Confirm all interactive states present
  - [ ] Review accessibility compliance

- [ ] Color contrast verification
  - [ ] WCAG AA (4.5:1) for all text
  - [ ] Use WebAIM contrast checker

- [ ] Responsive design validation
  - [ ] Mobile (375px) - responsive frames created
  - [ ] Tablet (768px) - responsive frames created
  - [ ] Desktop (1024px+) - original frames

- [ ] Animation review
  - [ ] All transitions smooth (no jank)
  - [ ] Durations and easing consistent

- [ ] Accessibility review
  - [ ] Keyboard navigation paths marked
  - [ ] Focus indicators visible
  - [ ] ARIA labels documented

---

## Export & Handoff Preparation

### Image Exports

- [ ] Export all 38 screens as JPG (100% quality)
  - [ ] Desktop version (1024×768px)
  - [ ] Mobile version (375×667px)
  - [ ] Naming: `export-SCR-{ID}-{name}-{device}.jpg`
  - [ ] Location: `.propel/context/figma/exports/`

### Token & Component Exports

- [ ] Export design tokens JSON
  - [ ] Use Figma Tokens plugin
  - [ ] Format: CSS variables

- [ ] Export component library JSON
  - [ ] For design system handoff

- [ ] Export CSS file with all tokens
  - [ ] For engineering integration
  - [ ] Location: `.propel/context/figma/tokens.css`

### Documentation Exports

- [ ] Create component usage guide PDF
- [ ] Export design system specification
- [ ] Create engineer handoff presentation

---

## Sharing & Permissions

- [ ] Set up Figma sharing
  - [ ] Team access: Editor
  - [ ] Stakeholder access: Viewer with comments
  - [ ] Developer access: Viewer

- [ ] Create Figma links document
  - [ ] Main design file link
  - [ ] Prototype link (clickable flows)
  - [ ] Token export link

- [ ] Enable design handoff features
  - [ ] Turn on Inspect for developers
  - [ ] Enable dev mode (if available)

---

## Engineering Handoff

- [ ] Share design system with engineering team
  - [ ] Figma file access (Viewer)
  - [ ] CSS tokens file
  - [ ] Component specifications
  - [ ] Handoff guide (figma-handoff-guide.md)

- [ ] Conduct design walkthrough
  - [ ] Review key screens
  - [ ] Discuss interaction patterns
  - [ ] Answer questions

- [ ] Provide Storybook examples
  - [ ] Component usage examples in React
  - [ ] Responsive breakpoint examples
  - [ ] Accessibility implementation examples

- [ ] Setup design-to-code workflow
  - [ ] Figma → Component library process
  - [ ] CSS variable injection
  - [ ] Design token updates

---

## Post-Implementation: Design System Maintenance

- [ ] Set up design token sync (GitHub Actions)
- [ ] Create design system versioning strategy
- [ ] Document component update process
- [ ] Establish design review process
- [ ] Create feedback collection mechanism

---

## Sign-Off & Completion

- [ ] Product Manager approval: _______________  Date: _______
- [ ] Design Lead approval: _______________  Date: _______
- [ ] Engineering Lead approval: _______________  Date: _______
- [ ] QA Lead approval: _______________  Date: _______

---

**Figma Implementation Status:** Ready to Begin  
**Last Updated:** 2026-06-17  
**Version:** 1.0

---

## Next Steps After Completion

1. ✅ Create Figma project structure
2. ✅ Build component library
3. ✅ Design all screen frames
4. ✅ Set up interactive prototypes
5. ✅ Export assets for engineering
6. ✅ Conduct design review
7. ✅ Hand off to engineering team
8. → **Begin Sprint 1 Implementation** (`/create-epics` → `/create-user-stories`)

