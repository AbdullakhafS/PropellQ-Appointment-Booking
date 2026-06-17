# Figma Interactive Prototype Flows

**Document Version:** 1.0  
**Date:** 2026-06-17  
**Status:** Ready for Figma Implementation  
**Purpose:** Detailed prototype interactions and navigation flows for Figma Page 6

---

## Prototype Flow Architecture

### Flow Layers

Each flow defines:
- **Entry Point:** First screen in the journey
- **Hotspots:** Interactive elements (buttons, links, form elements)
- **Transitions:** Target frame + animation type + delay
- **Conditional Branches:** Different paths based on user choices
- **Exit Points:** End screens

---

## Flow 1: Patient Booking Journey

**Flow Name:** `booking-appointment-flow`  
**Entry Point:** `SCR-P-004-Search`  
**Complexity:** Multi-step with conditional branching  
**Duration:** 5-8 screens

### Frame Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│ SCR-P-004: Search & Book Appointment                           │
│ [Filter Form] + [Results Grid with Provider Cards]             │
├─────────────────────────────────────────────────────────────────┤
│ Hotspots:                                                       │
│ • [Search button] → Animated spinner, results update           │
│ • [Provider Card - Select Slot button] → SCR-P-005             │
│ • [Recently Viewed Provider Link] → Same as provider card      │
└─────────────────────────────────────────────────────────────────┘
          ↓ [Select Slot button clicked]
          
┌─────────────────────────────────────────────────────────────────┐
│ SCR-P-005: Provider Selection & Calendar                       │
│ [Provider Info] + [Availability Calendar] + [Time Picker]      │
├─────────────────────────────────────────────────────────────────┤
│ Hotspots:                                                       │
│ • [Date in Calendar] → Time picker highlights available times  │
│ • [Time Slot Selection] → Button enables                       │
│ • [Continue button] → SCR-P-006                                │
│ • [Back link] → SCR-P-004                                      │
└─────────────────────────────────────────────────────────────────┘
          ↓ [Continue clicked]
          
┌─────────────────────────────────────────────────────────────────┐
│ SCR-P-006: Preferred Slot Selection (Optional)                 │
│ [Current Slot Display] + [Alternative Slot Picker]             │
├─────────────────────────────────────────────────────────────────┤
│ Hotspots:                                                       │
│ • [Choose Alternative toggle] → Dual calendar appears          │
│ • [Alternative Slot] → Highlight changes, summary updates      │
│ • [Confirm Selection button] → SCR-P-007                       │
│ • [Back link] → SCR-P-005                                      │
└─────────────────────────────────────────────────────────────────┘
          ↓ [Confirm Selection clicked]
          
┌─────────────────────────────────────────────────────────────────┐
│ SCR-P-007: Checkout & Review                                   │
│ [Appointment Summary] + [Insurance Verification] + [Payment]   │
├─────────────────────────────────────────────────────────────────┤
│ Hotspots:                                                       │
│ • [Edit Appointment link] → Modal overlay (modify date/time)   │
│ • [Terms Checkbox] → Button becomes enabled                    │
│ • [Book Appointment button] → Loading state (spinner)          │
│ • [Back link] → SCR-P-006                                      │
│ • [Book Appointment] (with terms) → SCR-P-008 (fade transition)│
└─────────────────────────────────────────────────────────────────┘
          ↓ [Book Appointment clicked & submitted]
          
┌─────────────────────────────────────────────────────────────────┐
│ SCR-P-008: Confirmation                                         │
│ [Success Icon] + [Confirmation Number] + [Appointment Details] │
├─────────────────────────────────────────────────────────────────┤
│ Hotspots:                                                       │
│ • [Copy Confirmation Number] → Toast "Copied!" appears         │
│ • [Add to Calendar button] → Modal (calendar selection)        │
│ • [Start Intake Form button] → SCR-P-009 OR SCR-P-010          │
│ • [View Appointment link] → SCR-P-014                          │
│ • [Home link] → SCR-P-011 (Patient Dashboard)                  │
└─────────────────────────────────────────────────────────────────┘
          ↓ Conditional Branch ↓
          
    ┌─────────────────────────────────────────────┐
    │ [Patient Chooses: Start Intake]             │
    │ ↓                                            │
    │ SCR-P-009: AI-Assisted Intake        │ OR   │ SCR-P-010: Manual Intake Form
    │ [Chatbot] + [Question] + [Responses]       │ [Multi-step Form] + [Progress]
    │                                            │ [Medical History] + [Medications]
    └─────────────────────────────────────────────┘
          ↓ [Intake Complete]
          
┌─────────────────────────────────────────────────────────────────┐
│ SCR-P-011: Profile Dashboard (Post-Booking)                    │
│ [Patient Data] + [Tabs: Overview, Meds, Allergies, Docs]       │
├─────────────────────────────────────────────────────────────────┤
│ Exit Point: User can navigate to:                              │
│ • SCR-P-012 (Upload Documents)                                 │
│ • SCR-P-013 (Upcoming Appointments)                            │
│ • SCR-P-014 (Appointment Detail)                               │
└─────────────────────────────────────────────────────────────────┘
```

### Hotspot Interaction Details

**SCR-P-004: Search Results**
- **Hotspot:** `.provider-card-select-button`
- **Trigger:** Click
- **Target:** `SCR-P-005-Provider-Selection`
- **Transition:** Slide right (200ms ease-out)
- **Data Pass:** Provider ID, selected slot info

**SCR-P-005: Time Selection**
- **Hotspot:** `.time-slot-selection`
- **Trigger:** Click
- **Action:** Enable "Continue" button
- **Visual:** Button changes from disabled (neutral-300) to enabled (color-primary-500)

**SCR-P-007: Book Appointment**
- **Hotspot:** `.book-appointment-button`
- **Trigger:** Click (only if terms checkbox checked)
- **Action:** Show loading spinner
- **Animation:** Pulse spinner for 1.5 seconds
- **Target:** `SCR-P-008-Confirmation`
- **Transition:** Fade in (200ms ease-out)

---

## Flow 2: Staff Queue Management

**Flow Name:** `staff-queue-flow`  
**Entry Point:** `SCR-S-001-Dashboard`  
**Complexity:** Multi-state with real-time updates  
**Duration:** 3-5 screens

### Frame Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│ SCR-S-001: Staff Dashboard                                      │
│ [KPI Cards] + [Queue Widget] + [Charts] + [Quick Actions]       │
├─────────────────────────────────────────────────────────────────┤
│ Hotspots:                                                       │
│ • [Queue Widget - View Full Queue] → SCR-S-002                  │
│ • [Add Walk-In button] → SCR-S-009 (modal overlay)              │
│ • [KPI Cards] → SCR-A-002 (Reports detail)                      │
└─────────────────────────────────────────────────────────────────┘
          ↓ [View Full Queue clicked]
          
┌──────────────────────────────────────────────────────────────────┐
│ SCR-S-002: Queue Management (Main)                              │
│ [3-Panel Layout: Queue | Patient Detail | Actions]              │
├──────────────────────────────────────────────────────────────────┤
│ Panel 1: Queue List (Left)                                      │
│ • Hotspot: Each `.queue-item` card                              │
│   Trigger: Click                                                │
│   Action: Highlight card (border color-primary-500)             │
│           Center panel updates with patient data (200ms fade)    │
│                                                                │
│ • Hotspot: `.queue-item` (drag handle)                          │
│   Trigger: Drag start                                           │
│   Action: Show visual feedback (elevation, shadow-lg)           │
│           Update reorder preview                                 │
│                                                                │
│ Panel 2: Patient Detail (Center)                                │
│ • Hotspot: `.tab-header` (Overview, Meds, Allergies, etc.)      │
│   Trigger: Click                                                │
│   Action: Switch tab content with fade animation (150ms)        │
│   Conditional: Show alert if conflicts detected                 │
│                                                                │
│ Panel 3: Action Buttons (Right)                                 │
│ • Hotspot: `.mark-ready-button`                                 │
│   Trigger: Click                                                │
│   Action: Move patient in queue to "In-Room" status             │
│           Toast confirmation appears                            │
│           Queue list updates automatically                      │
│                                                                │
│ • Hotspot: `.resolve-conflict-button`                           │
│   Trigger: Click                                                │
│   Action: Open SCR-S-006 (Conflict Resolution) in modal         │
│           Modal overlay blocks queue behind                     │
│                                                                │
│ • Hotspot: `.cancel-appointment-button`                         │
│   Trigger: Click                                                │
│   Action: Confirmation modal appears                           │
│           On confirm: Remove from queue, show toast             │
└──────────────────────────────────────────────────────────────────┘
```

### Queue Item Drag Behavior

- **Drag Start:** Visual feedback (shadow elevates to shadow-lg)
- **Drag Over:** Highlight drop target row with color-primary-50 background
- **Drop:** Animate to new position (200ms ease-out)
- **Update:** Queue list re-renders with new order
- **Confirmation:** Toast "Queue order updated" appears

---

## Flow 3: Admin Dashboard & Settings

**Flow Name:** `admin-settings-flow`  
**Entry Point:** `SCR-A-001-Dashboard`  
**Complexity:** Configuration with data updates  
**Duration:** 4-6 screens

### Frame Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│ SCR-A-001: Admin Dashboard                                      │
│ [KPI Cards] + [Charts] + [Alerts] + [Performance Table]         │
├─────────────────────────────────────────────────────────────────┤
│ Hotspots:                                                       │
│ • [Alert Item Link] → Relevant settings page                    │
│ • [KPI Card Numbers] → Drill-down reports                       │
│ • [Sidebar Menu Item: Settings] → SCR-A-006/007/008             │
└─────────────────────────────────────────────────────────────────┘
          ↓ [Settings menu clicked]
          
┌─────────────────────────────────────────────────────────────────┐
│ SCR-A-006: Appointment Settings                                 │
│ [Form: Duration] + [Cancellation Window] + [No-Show Threshold]  │
├─────────────────────────────────────────────────────────────────┤
│ Hotspots:                                                       │
│ • [Input Field] → Focus state (border color-primary-500)        │
│ • [Save Changes button] → Loading spinner                       │
│   On success: Toast "Settings saved successfully" (green)       │
│   Spinner animates for 0.5 seconds, then button returns normal  │
│ • [Restore Defaults link] → Confirmation modal                  │
│   On confirm: Form resets, toast appears                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 4: Patient Intake (AI vs Manual Branch)

**Flow Name:** `patient-intake-flow`  
**Entry Point:** `SCR-P-009` (AI) or `SCR-P-010` (Manual)  
**Complexity:** Multi-step conditional form  
**Duration:** 3-8 screens

### SCR-P-009: AI-Assisted Intake

```
┌─────────────────────────────────────────────────────────────────┐
│ SCR-P-009: AI Intake Chatbot                                    │
│ [Progress Bar: Step 1/5] + [Chatbot Message] + [Options]        │
├─────────────────────────────────────────────────────────────────┤
│ Hotspots (per question):                                        │
│ • [Option Button] → Question marked answered (✓ checkmark)      │
│                    Progress bar advances 20%                    │
│                    Next question fades in (200ms)               │
│                    Scroll animates to new question              │
│                                                                │
│ • [Skip button] → Same as option (marks as skipped)             │
│                                                                │
│ • [Previous button] → Returns to last question                  │
│                      Progress bar decreases 20%                │
│                                                                │
│ • [Submit button] (on final step) → Loading spinner             │
│                                      Processes response         │
│                                      → SCR-P-011 (Success)      │
│                                      Fade transition            │
└─────────────────────────────────────────────────────────────────┘
```

### SCR-P-010: Manual Intake Form

```
┌─────────────────────────────────────────────────────────────────┐
│ SCR-P-010: Multi-Step Form                                      │
│ [Progress Indicator] + [Form Sections] + [Navigation]           │
├─────────────────────────────────────────────────────────────────┤
│ Hotspots:                                                       │
│ • [Form Input] → Validation on blur                             │
│   Valid: Green border (color-success-500)                       │
│   Invalid: Red border (color-error-500) + error message        │
│                                                                │
│ • [Next Section button] → Validation check                      │
│   If valid: Fade current section out, next fades in            │
│             Progress bar advances                              │
│   If invalid: Scroll to first error, highlight in red          │
│               Toast "Please fill in required fields"           │
│                                                                │
│ • [Previous Section] → Collapse current, show previous         │
│   Data preserved                                               │
│                                                                │
│ • [Submit Form] → Validation on all sections                   │
│   If all valid: Loading spinner, submit                        │
│                → SCR-P-011 (Success)                           │
│   If invalid: Error toast, scroll to first error              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 5: Medical Conflict Resolution

**Flow Name:** `conflict-resolution-flow`  
**Entry Point:** `SCR-S-006` (Modal overlay on SCR-S-002)  
**Complexity:** Decision flow with audit trail  
**Duration:** 1-2 screens

### Frame Sequence

```
┌──────────────────────────────────────────────────────────────────┐
│ SCR-S-006: Conflict Resolution Modal (Overlay)                  │
│ [Source 1 Data Block] [VS] [Source 2 Data Block]                │
├──────────────────────────────────────────────────────────────────┤
│ Hotspots:                                                        │
│ • [Source 1 Card] → Highlight on hover (shadow-md)              │
│   On click: Show source details tooltip                         │
│                                                                 │
│ • [Source 2 Card] → Same behavior                               │
│                                                                 │
│ • [Accept Source 1 button] → Animate card to right             │
│                              Highlight as selected (green)     │
│                              Other buttons disable             │
│                              → Update patient record           │
│                              → Close modal (fade out)          │
│                              → Show toast "Conflict resolved"  │
│                                                                 │
│ • [Accept Source 2 button] → Same as above                      │
│                                                                 │
│ • [Manual Resolution link] → Open text editor modal             │
│                              Staff can manually merge data      │
│                              Save merged result                │
│                              → Close conflict modal            │
│                                                                 │
│ • [X Close button] → Modal closes (fade out)                    │
│                      Conflict remains unresolved               │
└──────────────────────────────────────────────────────────────────┘
```

---

## Transition Animations Library

### Standard Transitions

| Transition Type | Duration | Easing | Use Case |
|-----------------|----------|--------|----------|
| Fade In/Out | 150-200ms | ease-out | Screen changes, modal appearance |
| Slide Right | 200ms | ease-out | Multi-step form next |
| Slide Left | 200ms | ease-out | Multi-step form back |
| Scale In | 150ms | ease-out | Modal opens, dropdown |
| Bounce | 300ms | cubic-bezier(0.68, -0.55, 0.265, 1.55) | Success confirmations |
| Pulse | 500ms loop | ease-in-out | Loading states |
| Spin | 1000ms loop | linear | Spinner, processing |

### Hover Animations

| Element | Animation | Duration |
|---------|-----------|----------|
| Button | Shadow elevation + slight scale | 100ms |
| Card | Shadow elevation | 100ms |
| Link | Underline + color change | 100ms |
| Form Input | Focus border + shadow | 100ms |

---

## Interactive Component Behaviors

### Modal Dialogs

**Opening:**
- Backdrop fades in (200ms)
- Modal scales in from center (200ms, ease-out)
- Focus moves to first input/button

**Closing:**
- Modal scales out (150ms, ease-in)
- Backdrop fades out (150ms)
- Focus returns to trigger button

**Keyboard:**
- Escape key closes modal
- Tab cycles through focusable elements
- Enter submits form (if focused on submit button)

### Dropdowns

**Opening:**
- Options list slides down (150ms, ease-out)
- Highlight first option

**Closing:**
- Options list slides up (100ms, ease-in)
- Selected option shows in trigger

**Keyboard:**
- Arrow up/down moves highlight
- Enter selects option
- Escape closes dropdown

### Form Validation

**On Blur (after user leaves field):**
- Check if required and empty → Show error state
- Check if pattern invalid → Show specific error message
- Animate error message in (100ms)

**On Submit:**
- Validate all fields
- If any invalid: Scroll to first error, focus on field
- Disable submit button until corrected

### Pagination

**Page Navigation:**
- Previous/Next buttons navigate pages
- Slide transition between pages (200ms)
- Update page numbers highlight
- Disable Previous on first page, Next on last page

---

## Conditional Flows (Branching)

### Booking Flow Branching

```
After SCR-P-008 (Confirmation):
├─ [User selects: Start Intake]
│  ├─ [System detects: AI intake enabled]
│  │  └─ → SCR-P-009 (AI Chatbot)
│  └─ [System detects: Manual intake only]
│     └─ → SCR-P-010 (Manual Form)
└─ [User selects: Done / Skip]
   └─ → SCR-P-011 (Patient Dashboard)
```

### Admin Settings Branching

```
SCR-A-001 (Dashboard):
├─ [Alert: Insurance Verification Pending]
│  └─ → SCR-A-007 (Notification Templates) [Send reminder]
├─ [Alert: System Performance]
│  └─ → SCR-A-006 (Appointment Settings) [Adjust parameters]
└─ [Alert: User Management]
   └─ → SCR-A-003 (User List) [Review activity]
```

---

## Prototype Testing Checklist

- [ ] All hotspots trigger correct transitions
- [ ] Navigation back/forward works bidirectionally
- [ ] Form validation shows errors correctly
- [ ] Loading states show spinners/loaders
- [ ] Modals open/close smoothly with overlay
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] Animations smooth (no jank)
- [ ] Mobile responsive (test at 375px width)
- [ ] Tablet responsive (test at 768px width)
- [ ] Desktop optimal (test at 1024px+ width)
- [ ] Color contrast meets WCAG AA (4.5:1)
- [ ] Focus indicators visible for all interactive elements

---

**Figma Prototype Flows Status:** Ready for Implementation  
**Last Updated:** 2026-06-17  
**Version:** 1.0

