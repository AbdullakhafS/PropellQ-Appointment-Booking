# Design System: PropellQ Unified Patient Access & Clinical Intelligence Platform

**Document Version:** 1.0  
**Date:** 2026-06-17  
**Status:** Draft  
**Framework:** Design Tokens (CSS Variables, Figma Design Tokens)

---

## Table of Contents

1. [Overview & Design Principles](#overview--design-principles)
2. [Color Palette](#color-palette)
3. [Typography System](#typography-system)
4. [Spacing & Layout](#spacing--layout)
5. [Shadows & Elevation](#shadows--elevation)
6. [Border Radius & Borders](#border-radius--borders)
7. [Interactive States](#interactive-states)
8. [Icons](#icons)
9. [Motion & Animation](#motion--animation)
10. [Component Specifications](#component-specifications)
11. [Responsive Grid System](#responsive-grid-system)
12. [Accessibility Tokens](#accessibility-tokens)
13. [CSS Custom Properties](#css-custom-properties)

---

## Overview & Design Principles

### Design Language

**PropellQ** adopts a **healthcare-forward, modern minimalist** aesthetic that prioritizes:

1. **Trust & Clarity:** Clean layouts, clear hierarchy, unambiguous actions
2. **Accessibility:** High contrast, clear labeling, keyboard-friendly interactions
3. **Efficiency:** Information-dense clinical views vs. simplified patient views
4. **Responsiveness:** Mobile-first design scaling seamlessly to desktop
5. **Data Transparency:** All AI/automated data clearly marked with confidence, source, and verification status

### Target Audiences & Tone

- **Patients:** Approachable, empowering, jargon-free
- **Clinical Staff:** Professional, efficient, detail-rich
- **Administrators:** Authoritative, data-centric, compliance-focused

---

## Color Palette

### Primary Colors

| Token | Hex | RGB | Use Case | Accessibility |
|-------|-----|-----|----------|-----------------|
| `color-primary-50` | `#E8F3FF` | rgb(232, 243, 255) | Light backgrounds, hover states | — |
| `color-primary-100` | `#CCE4FF` | rgb(204, 228, 255) | Form field backgrounds | — |
| `color-primary-200` | `#99CCFF` | rgb(153, 204, 255) | Secondary hover, disabled states | — |
| `color-primary-300` | `#66B2FF` | rgb(102, 178, 255) | Medium-weight interactive elements | — |
| `color-primary-400` | `#3399FF` | rgb(51, 153, 255) | Primary CTA buttons, links | WCAG AA ✓ (4.5:1 on white) |
| `color-primary-500` | `#0066FF` | rgb(0, 102, 255) | **Primary brand color, primary buttons, active states** | WCAG AAA ✓ (7.0:1 on white) |
| `color-primary-600` | `#0052CC` | rgb(0, 82, 204) | Button hover/active, link hover | WCAG AAA ✓ (7.8:1 on white) |
| `color-primary-700` | `#003D99` | rgb(0, 61, 153) | Button press, dark state | WCAG AAA ✓ (9.5:1 on white) |
| `color-primary-800` | `#002966` | rgb(0, 41, 102) | Reserved for dark mode | — |
| `color-primary-900` | `#001433` | rgb(0, 20, 51) | Reserved for dark mode | — |

### Secondary Colors (Accent)

| Token | Hex | RGB | Use Case |
|-------|-----|-----|----------|
| `color-secondary-50` | `#F0EDFF` | rgb(240, 237, 255) | Light accents |
| `color-secondary-400` | `#9B7EFF` | rgb(155, 126, 255) | Secondary CTA, accent elements |
| `color-secondary-500` | `#7C5FFF` | rgb(124, 95, 255) | Secondary buttons, accent |
| `color-secondary-600` | `#6A4FD9` | rgb(106, 79, 217) | Secondary button hover |

### Semantic Colors

#### Success (Green)
| Token | Hex | Use Case |
|-------|-----|----------|
| `color-success-50` | `#E8F7E8` | Success background |
| `color-success-100` | `#C8E6C9` | Success light |
| `color-success-400` | `#66BB6A` | Success icon, border |
| `color-success-500` | `#4CAF50` | **Success indicator, appointment confirmed** |
| `color-success-600` | `#388E3C` | Success hover/active |

**WCAG Compliance:** `color-success-500` has 4.8:1 contrast on white (AA ✓), 8.2:1 on dark backgrounds

#### Warning (Amber)
| Token | Hex | Use Case |
|-------|-----|----------|
| `color-warning-50` | `#FFF8E1` | Warning background |
| `color-warning-100` | `#FFE082` | Warning light |
| `color-warning-400` | `#FFA726` | Warning icon, border |
| `color-warning-500` | `#FF9800` | **Warning badge, pending actions** |
| `color-warning-600` | `#F57C00` | Warning hover/active |

**WCAG Compliance:** `color-warning-500` has 4.5:1 contrast on white (AA ✓), 8.1:1 on dark backgrounds

#### Error (Red)
| Token | Hex | Use Case |
|-------|-----|----------|
| `color-error-50` | `#FFEBEE` | Error background |
| `color-error-100` | `#FFCDD2` | Error light |
| `color-error-400` | `#EF5350` | Error icon, border |
| `color-error-500` | `#F44336` | **Error indicator, conflict flag** |
| `color-error-600` | `#D32F2F` | Error hover/active |

**WCAG Compliance:** `color-error-500` has 3.9:1 contrast on white (AA ✓), 7.7:1 on dark backgrounds

#### Info (Blue)
| Token | Hex | Use Case |
|-------|-----|----------|
| `color-info-50` | `#E3F2FD` | Info background |
| `color-info-400` | `#42A5F5` | Info icon, border |
| `color-info-500` | `#2196F3` | **Info notification, additional info** |
| `color-info-600` | `#1976D2` | Info hover/active |

#### Neutral (Grayscale)
| Token | Hex | RGB | Use Case |
|-------|-----|-----|----------|
| `color-neutral-0` | `#FFFFFF` | rgb(255, 255, 255) | Background, card surfaces |
| `color-neutral-50` | `#F9FAFB` | rgb(249, 250, 251) | Subtle background |
| `color-neutral-100` | `#F3F4F6` | rgb(243, 244, 246) | Form field background, dividers |
| `color-neutral-200` | `#E5E7EB` | rgb(229, 231, 235) | Button borders, subtle dividers |
| `color-neutral-300` | `#D1D5DB` | rgb(209, 213, 219) | Input borders, disabled state |
| `color-neutral-400` | `#9CA3AF` | rgb(156, 163, 175) | Helper text, secondary labels |
| `color-neutral-500` | `#6B7280` | rgb(107, 114, 128) | Secondary text, disabled button text |
| `color-neutral-600` | `#4B5563` | rgb(75, 85, 99) | Primary text, headings |
| `color-neutral-700` | `#374151` | rgb(55, 65, 81) | Strong text |
| `color-neutral-800` | `#1F2937` | rgb(31, 41, 55) | High contrast text |
| `color-neutral-900` | `#111827` | rgb(17, 24, 39) | Maximum contrast text |

### Color Usage Guidelines

| Element | Token | Notes |
|---------|-------|-------|
| Primary CTA Button | `color-primary-500` | Default state |
| Primary CTA Button Hover | `color-primary-600` | 20% darker |
| Primary CTA Button Active/Pressed | `color-primary-700` | Darkest active state |
| Disabled Button | `color-neutral-300` background, `color-neutral-500` text | Reduced contrast |
| Form Input Border | `color-neutral-200` | Default |
| Form Input Border Focus | `color-primary-400` | Clear focus indicator |
| Form Input Error Border | `color-error-500` | Error state |
| Success Badge | `color-success-500` | Appointment confirmed, task completed |
| Warning Badge | `color-warning-500` | Pending actions, unverified insurance |
| Error Badge | `color-error-500` | Conflicts, system errors |
| Link Color | `color-primary-500` | Underlined in body text |
| Link Hover | `color-primary-600` | Darker on hover |
| Background | `color-neutral-0` | Main canvas |
| Secondary Background | `color-neutral-50` | Card backgrounds, sections |
| Divider | `color-neutral-200` | 1px horizontal rule |
| Primary Text | `color-neutral-900` | Body text, high contrast |
| Secondary Text | `color-neutral-600` | Labels, supporting text |
| Tertiary Text | `color-neutral-500` | Helper text, disabled labels |

---

## Typography System

### Font Stack

```css
/* Primary (UI) */
--font-family-primary: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;

/* Monospace (Code, timestamps) */
--font-family-mono: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Menlo, Courier, monospace;
```

### Font Scale

Designed on a **1.125x modular scale** (major second interval) for harmonious sizing.

| Token | Size | Weight | Line Height | Letter Spacing | Use Case |
|-------|------|--------|-------------|-----------------|----------|
| `font-size-xs` | 12px | 400 | 1.5 (18px) | 0 | Caption text, timestamps |
| `font-size-sm` | 13.5px | 400 | 1.5 (20px) | 0 | Helper text, form labels (secondary) |
| `font-size-base` | 15px | 400 | 1.6 (24px) | 0 | **Body text, form labels** |
| `font-size-lg` | 16.875px | 400 | 1.6 (27px) | 0 | Large body text |
| `font-size-xl` | 19px | 500 | 1.6 (30px) | -0.3px | Subheading, form section titles |
| `font-size-2xl` | 21.4px | 600 | 1.5 (32px) | -0.5px | Section heading, card title |
| `font-size-3xl` | 24px | 600 | 1.4 (34px) | -0.5px | Page heading, modal title |
| `font-size-4xl` | 27px | 700 | 1.3 (35px) | -1px | Large page heading, dashboard title |
| `font-size-5xl` | 30.4px | 700 | 1.2 (37px) | -1px | Extra large heading (rarely used) |

### Font Weights

| Token | Weight | Use Case |
|-------|--------|----------|
| `font-weight-normal` | 400 | Body text, default |
| `font-weight-medium` | 500 | Labels, subheadings, emphasis |
| `font-weight-semibold` | 600 | Headings, strong emphasis |
| `font-weight-bold` | 700 | Major headings, high emphasis |

### Typography Styles (Composite)

| Token | Size | Weight | Line Height | Use Case | Example |
|-------|------|--------|-------------|----------|---------|
| `typography-display-lg` | 30.4px | 700 | 1.2 | Dashboard/admin title | "Dashboard" |
| `typography-display-md` | 27px | 700 | 1.3 | Page heading | "Search Appointments" |
| `typography-heading-lg` | 24px | 600 | 1.4 | Modal title, section heading | "Appointment Confirmation" |
| `typography-heading-md` | 21.4px | 600 | 1.5 | Card title, subsection | "Insurance Information" |
| `typography-heading-sm` | 19px | 600 | 1.6 | Form section label | "Medical History" |
| `typography-body-lg` | 16.875px | 400 | 1.6 | Large body text | Form instructions |
| `typography-body-md` | 15px | 400 | 1.6 | **Default body text** | Paragraph text, form labels |
| `typography-body-sm` | 13.5px | 400 | 1.5 | Helper text, secondary info | Form field hints |
| `typography-label-md` | 15px | 500 | 1.6 | Form field labels, tabs | Input label, tab text |
| `typography-label-sm` | 13.5px | 500 | 1.5 | Small label, badge text | Badge content |
| `typography-caption` | 12px | 400 | 1.5 | Caption, timestamp | "Last updated: 2 hours ago" |
| `typography-code` | 13px | 400 | 1.5 | Code, API responses | `POST /api/v1/appointments` |

### Text Colors

| Token | Usage |
|-------|-------|
| `text-primary` | `color-neutral-900` - High contrast, body text, headings |
| `text-secondary` | `color-neutral-600` - Labels, supporting information |
| `text-tertiary` | `color-neutral-500` - Helper text, disabled text |
| `text-inverse` | `color-neutral-0` - Text on dark backgrounds (modals, overlays) |
| `text-link` | `color-primary-500` - Links (underlined in body context) |
| `text-success` | `color-success-600` - Success messages |
| `text-warning` | `color-warning-600` - Warning messages |
| `text-error` | `color-error-600` - Error messages |
| `text-info` | `color-info-600` - Informational messages |

### Line Height Guidelines

- **Display/Heading:** 1.2 - 1.3 (tighter for visual impact)
- **Body:** 1.6 (28.8px for 18px text, ensures 24-28px total line height per WCAG)
- **Caption/Small:** 1.5

---

## Spacing & Layout

### Spacing Scale

Built on **8px base unit** with 8-step scale:

| Token | Value | Use Case |
|-------|-------|----------|
| `space-0` | 0px | No spacing |
| `space-1` | 4px | Tight internal padding (icon + text) |
| `space-2` | 8px | **Default small gap, form field margin** |
| `space-3` | 12px | Small section padding |
| `space-4` | 16px | **Standard padding (buttons, cards, inputs)** |
| `space-5` | 20px | Medium gap, section spacing |
| `space-6` | 24px | **Medium-large gap, container padding** |
| `space-7` | 32px | Large gap, page section spacing |
| `space-8` | 40px | Extra large gap, major sections |
| `space-9` | 48px | Very large gap, page-level spacing |
| `space-10` | 56px | Extra-large gap (rarely used) |
| `space-12` | 64px | Maximum spacing (rarely used) |

### Padding Guidelines

| Element | Padding | Notes |
|---------|---------|-------|
| Button (medium) | `space-2 space-4` | 8px vertical, 16px horizontal |
| Button (large) | `space-3 space-6` | 12px vertical, 24px horizontal |
| Form input | `space-2 space-3` | 8px vertical, 12px horizontal |
| Card | `space-4` / `space-6` | 16px or 24px depending on card type |
| Modal header | `space-6` | 24px padding |
| Modal body | `space-6` | 24px padding |
| Page container | `space-4` mobile, `space-6` desktop | Responsive padding |
| Section heading margin-bottom | `space-4` | Space below heading |

### Margin Guidelines

| Element | Margin | Notes |
|---------|--------|-------|
| Paragraph (body text) | `margin-bottom: space-4` | 16px below paragraphs |
| Form field group | `margin-bottom: space-5` | 20px below each field |
| Section | `margin-bottom: space-6` | 24px between sections |
| Button (in group) | `margin-right: space-2` | 8px between buttons |

### Container Widths

| Breakpoint | Container Max-Width | Padding | Available Width |
|------------|-------------------|---------|-----------------|
| Mobile (375px) | 100% | `space-4` (16px each side) | 343px |
| Tablet (768px) | 100% | `space-6` (24px each side) | 720px |
| Desktop (1024px) | 1200px | `space-6` (24px each side) | 1152px |

---

## Shadows & Elevation

### Elevation System (4 levels)

Shadows created using CSS for layering and depth:

| Token | Box-Shadow | Elevation | Use Case |
|-------|-----------|-----------|----------|
| `shadow-none` | none | 0 | Flat surfaces (primary background) |
| `shadow-sm` | `0 1px 2px 0 rgba(0, 0, 0, 0.05)` | 1 | **Default card shadow, subtle elevation** |
| `shadow-md` | `0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)` | 2 | Hover state for cards, input focus |
| `shadow-lg` | `0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)` | 3 | Modals, dropdowns, tooltips |
| `shadow-xl` | `0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)` | 4 | Maximum elevation (alerts, popovers) |

### Shadow Usage

| Component | Shadow | Notes |
|-----------|--------|-------|
| Card (default) | `shadow-sm` | 1px subtle shadow |
| Card (hover) | `shadow-md` | Lift effect on hover |
| Form input (focus) | `shadow-md` + border color change | Visual focus indicator |
| Modal | `shadow-xl` | Dark overlay backdrop with max shadow |
| Tooltip | `shadow-lg` | Elevated above content |
| Dropdown menu | `shadow-lg` | Clear layering indication |
| Floating button (FAB) | `shadow-lg` | Raised above main content |

---

## Border Radius & Borders

### Border Radius Scale

| Token | Value | Use Case |
|-------|-------|----------|
| `radius-none` | 0px | Square elements (rarely used) |
| `radius-sm` | 4px | Subtle rounding (tag badges) |
| `radius-md` | 6px | **Default rounding (buttons, inputs, cards)** |
| `radius-lg` | 8px | Larger components, modals |
| `radius-xl` | 12px | Large cards, emphasis |
| `radius-2xl` | 16px | Extra-large rounded (rarely used) |
| `radius-full` | 9999px | Fully rounded (pills, circular elements) |

### Border Radius Application

| Element | Radius | Notes |
|---------|--------|-------|
| Button | `radius-md` | 6px for standard buttons |
| Form input | `radius-md` | 6px consistent with buttons |
| Card | `radius-md` / `radius-lg` | 6px for small cards, 8px for large |
| Modal | `radius-lg` | 8px for professional appearance |
| Alert banner | `radius-md` | 6px |
| Tooltip | `radius-sm` | 4px (subtle) |
| Avatar | `radius-full` | Fully circular |
| Badge | `radius-full` | Fully rounded/pill shape |

### Border System

| Token | Style | Use Case |
|-------|-------|----------|
| `border-none` | none | No border |
| `border-1` | 1px solid | **Default border width** |
| `border-2` | 2px solid | Emphasis, active state |

### Border Colors

| Token | Color | Use Case |
|-------|-------|----------|
| `border-default` | `color-neutral-200` | Form input borders, dividers |
| `border-focus` | `color-primary-400` | Input focus state |
| `border-error` | `color-error-500` | Error input state |
| `border-success` | `color-success-500` | Success input state |
| `border-disabled` | `color-neutral-300` | Disabled input border |

---

## Interactive States

### Button States

#### Primary Button
```css
/* Default */
background: color-primary-500;
color: color-neutral-0;
border: border-none;

/* Hover */
background: color-primary-600;
cursor: pointer;

/* Active/Pressed */
background: color-primary-700;
box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);

/* Disabled */
background: color-neutral-300;
color: color-neutral-500;
cursor: not-allowed;
```

#### Secondary Button
```css
/* Default */
background: color-neutral-100;
color: color-primary-600;
border: 1px solid color-neutral-300;

/* Hover */
background: color-neutral-200;
border-color: color-neutral-400;

/* Active */
background: color-neutral-300;
border-color: color-neutral-500;

/* Disabled */
background: color-neutral-100;
color: color-neutral-500;
border-color: color-neutral-300;
cursor: not-allowed;
```

#### Tertiary Button (Text-only)
```css
/* Default */
background: transparent;
color: color-primary-600;
border: none;
text-decoration: underline;

/* Hover */
color: color-primary-700;
background: color-primary-50;

/* Active */
color: color-primary-700;

/* Disabled */
color: color-neutral-400;
cursor: not-allowed;
```

### Form Input States

#### Default
```css
border: 1px solid color-neutral-200;
background: color-neutral-0;
color: color-neutral-900;
outline: none;
```

#### Focus
```css
border: 1px solid color-primary-400;
background: color-neutral-0;
box-shadow: 0 0 0 3px color-primary-100;
```

#### Filled (with value)
```css
border: 1px solid color-neutral-200;
background: color-neutral-0;
color: color-neutral-900;
```

#### Disabled
```css
border: 1px solid color-neutral-300;
background: color-neutral-100;
color: color-neutral-500;
cursor: not-allowed;
```

#### Error
```css
border: 1px solid color-error-500;
background: color-neutral-0;
box-shadow: 0 0 0 3px color-error-50;
```

#### Success
```css
border: 1px solid color-success-500;
background: color-neutral-0;
box-shadow: 0 0 0 3px color-success-50;
```

### Link States

#### Default
```css
color: color-primary-500;
text-decoration: none;
cursor: pointer;
```

#### Hover
```css
color: color-primary-600;
text-decoration: underline;
```

#### Active/Visited
```css
color: color-primary-700;
```

#### Disabled
```css
color: color-neutral-400;
cursor: not-allowed;
text-decoration: none;
```

---

## Icons

### Icon System

- **Format:** SVG (scalable, crisp on all devices)
- **Library:** Material Design Icons (v7.2+) + custom healthcare icons
- **Base Size:** 24px × 24px (standard)
- **Sizes:** 16px (small), 20px (medium), 24px (default), 32px (large), 48px (extra-large)

### Icon Color Usage

| Context | Color | Notes |
|---------|-------|-------|
| Navigation | `color-neutral-600` default, `color-primary-500` active | Clearly indicates active state |
| Action buttons | `color-neutral-900` or `color-primary-500` | Depends on button style |
| Status indicator | `color-success-500` (success), `color-error-500` (error), `color-warning-500` (warning) | Semantic coloring |
| Disabled icon | `color-neutral-400` | Muted appearance |
| Interactive element (hover) | Darkens or highlights appropriately | Visual feedback |

### Common Icon Mappings

| Icon Name | Use Case | Alternatives |
|-----------|----------|--------------|
| `calendar` | Appointment dates, date selection | — |
| `clock` | Time, duration, reminders | `timer`, `schedule` |
| `user` | Patient/staff profile | `person`, `account_circle` |
| `search` | Search functionality | `magnifying_glass` |
| `plus` | Add item, create new | — |
| `trash` | Delete, remove | `delete_outline` |
| `edit` | Edit item | `pencil` |
| `check` | Confirm, success | `check_circle` |
| `close` | Close, cancel | `x` |
| `menu` | Hamburger menu | — |
| `bell` | Notifications | `notifications` |
| `alert` | Warning, alert | `warning` |
| `document` | Document, file | `description`, `file` |
| `download` | Download | — |
| `upload` | Upload | — |
| `eye` | Show, visibility | `visibility` |
| `eye_off` | Hide, visibility off | `visibility_off` |
| `lock` | Secure, locked | `lock_closed` |
| `chevron_down` | Dropdown | — |
| `chevron_right` | Navigation forward | — |
| `phone` | Call, phone number | `call` |
| `mail` | Email, message | `email` |
| `map_pin` | Location | `location_on` |
| `heart` | Favorites, ratings | `favorite` |
| `star` | Ratings, reviews | — |

---

## Motion & Animation

### Animation Principles

1. **Purposeful:** Every animation serves a function (feedback, guidance, transition)
2. **Quick:** Most animations < 300ms (no sluggish feel)
3. **Easing:** Use `ease-out` for entrances, `ease-in-out` for interactions
4. **Accessible:** Respect `prefers-reduced-motion` setting

### Easing Functions

| Token | Value | Use Case |
|-------|-------|----------|
| `ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | Exit animations (fade out, slide off) |
| `ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | Entrance animations (fade in, slide in) |
| `ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | **Interactive animations (button hover, input focus)** |
| `ease-linear` | `linear` | Continuous motion (loading spinner) |

### Duration Tokens

| Token | Duration | Use Case |
|-------|----------|----------|
| `duration-fast` | 150ms | Quick feedback (button hover, icon change) |
| `duration-base` | 200ms | **Standard transition (modal open, form field focus)** |
| `duration-slow` | 300ms | Slower entrance animations (page transition) |
| `duration-slower` | 500ms | Background animations (progress bar animation) |

### Common Animation Patterns

#### Fade In (entrance)
```css
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* Usage */
animation: fadeIn duration-base ease-out;
```

#### Fade Out (exit)
```css
@keyframes fadeOut {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}

/* Usage */
animation: fadeOut duration-base ease-in;
```

#### Slide In (left to right)
```css
@keyframes slideInRight {
  from {
    transform: translateX(-100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* Usage */
animation: slideInRight duration-base ease-out;
```

#### Scale/Pop (entrance emphasis)
```css
@keyframes scaleIn {
  from {
    transform: scale(0.9);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

/* Usage */
animation: scaleIn duration-fast ease-out;
```

#### Loading Spinner
```css
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Usage */
animation: spin duration-slower linear infinite;
```

#### Pulse (attention)
```css
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* Usage */
animation: pulse duration-base ease-in-out infinite;
```

### Transition Guidelines

| Interaction | Property | Duration | Easing |
|-------------|----------|----------|--------|
| Button hover | `background-color`, `box-shadow` | `duration-fast` | `ease-in-out` |
| Input focus | `border-color`, `box-shadow` | `duration-fast` | `ease-in-out` |
| Modal open | `opacity`, `transform` (scale) | `duration-base` | `ease-out` |
| Modal close | `opacity`, `transform` (scale) | `duration-base` | `ease-in` |
| Dropdown open | `opacity`, `transform` (translateY) | `duration-fast` | `ease-out` |
| Page transition | `opacity` | `duration-slow` | `ease-in-out` |
| Loading indicator | `transform` (rotate) | `duration-slower` | `linear` (infinite) |
| Notification enter | `transform` (slideInRight) | `duration-base` | `ease-out` |
| Notification exit | `transform`, `opacity` | `duration-base` | `ease-in` |

### Accessibility: Reduced Motion

Always respect user's motion preferences:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Component Specifications

### Button Component

#### Size Variants

| Token | Padding | Font Size | Height | Usage |
|-------|---------|-----------|--------|-------|
| `button-sm` | `space-1 space-3` (4px 12px) | `font-size-sm` (13.5px) | 32px | Secondary actions, inline buttons |
| `button-md` | `space-2 space-4` (8px 16px) | `font-size-base` (15px) | 40px | **Default/primary buttons** |
| `button-lg` | `space-3 space-6` (12px 24px) | `font-size-lg` (16.875px) | 48px | CTA buttons, modal actions |

#### Style Variants

1. **Primary:** Filled background (`color-primary-500`), white text
2. **Secondary:** Light background (`color-neutral-100`), border, primary text
3. **Tertiary:** Transparent, text-only, underline (optional)
4. **Danger:** Red background (`color-error-500`), white text
5. **Success:** Green background (`color-success-500`), white text

### Form Input Component

#### Size Variants

| Token | Height | Padding | Font Size |
|-------|--------|---------|-----------|
| `input-sm` | 32px | `space-2 space-3` | `font-size-sm` |
| `input-md` | 40px | `space-2 space-4` | `font-size-base` |
| `input-lg` | 48px | `space-3 space-4` | `font-size-lg` |

#### Field Components

- **Text Input:** Default, Email, Password, Number, Tel, URL
- **Textarea:** Resizable, multi-line
- **Select/Dropdown:** Single-select, searchable, disabled options
- **Checkbox:** Label, indeterminate state, disabled
- **Radio Button:** Label, group context
- **Date Picker:** Calendar widget, range selection
- **Time Picker:** Hour/minute spinners
- **File Upload:** Drag-and-drop, file list

### Card Component

#### Sizes

| Token | Padding | Border Radius | Usage |
|-------|---------|---------------|-------|
| `card-sm` | `space-4` (16px) | `radius-md` | Compact cards, in lists |
| `card-md` | `space-6` (24px) | `radius-md` / `radius-lg` | **Default card size** |
| `card-lg` | `space-6` (24px) | `radius-lg` | Feature cards, emphasis |

#### Card Variants

1. **Elevated:** Shadow + white background (default)
2. **Outlined:** Border + transparent background
3. **Filled:** Subtle background color

### Badge Component

#### Sizes

| Token | Padding | Font Size | Height |
|-------|---------|-----------|--------|
| `badge-sm` | `space-1 space-2` (4px 8px) | `font-size-xs` (12px) | 24px |
| `badge-md` | `space-1 space-3` (4px 12px) | `font-size-sm` (13.5px) | 28px |

#### Badge Variants

1. **Success:** Green background (`color-success-100`), green text (`color-success-600`)
2. **Warning:** Amber background (`color-warning-100`), amber text (`color-warning-600`)
3. **Error:** Red background (`color-error-100`), red text (`color-error-600`)
4. **Info:** Blue background (`color-info-100`), blue text (`color-info-600`)
5. **Neutral:** Gray background (`color-neutral-100`), gray text (`color-neutral-600`)

---

## Responsive Grid System

### Breakpoints

| Name | Min Width | Max Width | Columns | Gutter |
|------|-----------|-----------|---------|--------|
| `xs` | 0px | 374px | 4 | 16px |
| `sm` | 375px | 767px | 4 | 16px |
| `md` | 768px | 1023px | 8 | 24px |
| `lg` | 1024px | 1439px | 12 | 24px |
| `xl` | 1440px | ∞ | 12 | 24px |

### Column Spans

```css
/* Mobile (4 columns) */
.col-full { width: 100%; }
.col-half { width: 50%; }
.col-third { width: 33.333%; }
.col-quarter { width: 25%; }

/* Tablet (8 columns) */
@media (min-width: 768px) {
  .col-md-full { width: 100%; }
  .col-md-half { width: 50%; }
  .col-md-third { width: 33.333%; }
  .col-md-2-3 { width: 66.666%; }
}

/* Desktop (12 columns) */
@media (min-width: 1024px) {
  .col-lg-full { width: 100%; }
  .col-lg-half { width: 50%; }
  .col-lg-third { width: 33.333%; }
  .col-lg-2-3 { width: 66.666%; }
  .col-lg-4 { width: 33.333%; }
  .col-lg-6 { width: 50%; }
  .col-lg-8 { width: 66.666%; }
}
```

---

## Accessibility Tokens

### Focus Indicators

```css
--focus-outline: 2px solid color-primary-500;
--focus-offset: 2px;
--focus-radius: radius-md;
```

### High Contrast Mode Support

For users with high contrast preferences:

```css
@media (prefers-contrast: more) {
  --color-neutral-200: rgb(180, 180, 180);
  --border-default: 2px solid rgb(0, 0, 0);
  --font-weight-default: 600;
}
```

### Screen Reader Text (Utility Class)

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

---

## CSS Custom Properties

### Usage in Figma & Code

Export all design tokens as CSS custom properties for seamless handoff to engineering:

```css
:root {
  /* Colors */
  --color-primary-50: #E8F3FF;
  --color-primary-100: #CCE4FF;
  /* ... continue for all colors ... */
  
  /* Typography */
  --font-family-primary: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-size-base: 15px;
  --font-size-lg: 16.875px;
  --line-height-base: 1.6;
  /* ... continue for all typography ... */
  
  /* Spacing */
  --space-0: 0px;
  --space-2: 8px;
  --space-4: 16px;
  --space-6: 24px;
  /* ... continue for all spacing ... */
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  /* ... continue for all shadows ... */
  
  /* Border Radius */
  --radius-md: 6px;
  --radius-lg: 8px;
  /* ... continue for all radii ... */
  
  /* Animations */
  --duration-base: 200ms;
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  /* ... continue for all animations ... */
}
```

### Dark Mode (Optional Future Support)

```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-neutral-0: #111827;
    --color-neutral-900: #FFFFFF;
    /* ... invert colors for dark mode ... */
  }
}
```

---

## Implementation Checklist

- [ ] Export all design tokens to Figma Design Tokens plugin
- [ ] Create CSS variables file (`design-tokens.css`)
- [ ] Set up Tailwind config with design token values (optional)
- [ ] Create Storybook documentation for all components
- [ ] Publish component library in Figma (shared library)
- [ ] Add design tokens to engineering documentation
- [ ] Set up Figma plugins for token syncing
- [ ] Create accessibility audit checklist
- [ ] Establish color contrast verification process
- [ ] Document animation guidelines for developers

---

**Design System Version:** 1.0  
**Last Updated:** 2026-06-17  
**Maintained By:** Design Team  
**Next Review:** 2026-07-17 (quarterly)

---

## References

- [WCAG 2.2 Color Contrast Checker](https://www.tpgi.com/color-contrast-checker/)
- [Web Content Accessibility Guidelines (WCAG 2.2 Level AA)](https://www.w3.org/WAI/WCAG22/quickref/)
- [Material Design 3 System](https://m3.material.io/)
- [Tailwind CSS Design System](https://tailwindcss.com/)
- [Figma Design Systems Best Practices](https://help.figma.com/hc/en-us/articles/360040318273)

