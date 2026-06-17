# Figma Design Handoff Guide

**Document Version:** 1.0  
**Date:** 2026-06-17  
**Status:** Ready for Engineering Handoff  
**Audience:** Frontend developers, QA engineers, product managers

---

## Overview

This guide provides everything needed for engineering teams to implement the PropellQ design system in React/TypeScript using the design tokens and component specifications.

---

## Design Token Export (CSS Variables)

### CSS Variable Format

All design tokens are available as CSS custom properties. Export from Figma using Figma Tokens plugin.

```css
/* Colors */
--color-primary-50: #E8F3FF;
--color-primary-100: #D0E7FF;
--color-primary-500: #0066FF;
--color-primary-600: #0052CC;
--color-secondary-500: #9B7EFF;
--color-success-500: #4CAF50;
--color-warning-500: #FF9800;
--color-error-500: #F44336;
--color-info-500: #2196F3;
--color-neutral-0: #FFFFFF;
--color-neutral-50: #F9FAFB;
--color-neutral-100: #F3F4F6;
--color-neutral-200: #E5E7EB;
--color-neutral-300: #D1D5DB;
--color-neutral-500: #6B7280;
--color-neutral-700: #374151;
--color-neutral-900: #111827;

/* Typography */
--font-family-system: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
--font-family-mono: "SF Mono", Monaco, "Roboto Mono", monospace;

--font-size-xs: 12px;
--font-size-sm: 13.5px;
--font-size-base: 15px;
--font-size-lg: 19px;
--font-size-xl: 21.4px;
--font-size-2xl: 24px;
--font-size-3xl: 27px;
--font-size-4xl: 30.4px;

--font-weight-normal: 400;
--font-weight-medium: 500;
--font-weight-semibold: 600;
--font-weight-bold: 700;

--line-height-display: 1.2;
--line-height-heading: 1.3;
--line-height-body: 1.6;
--line-height-caption: 1.5;

/* Spacing */
--space-0: 0px;
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-7: 28px;
--space-8: 32px;
--space-9: 36px;
--space-10: 40px;
--space-12: 64px;

/* Shadows */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
--shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.15);

/* Border Radius */
--radius-none: 0px;
--radius-sm: 2px;
--radius-md: 6px;
--radius-lg: 8px;
--radius-xl: 12px;
--radius-2xl: 16px;
--radius-full: 9999px;

/* Animation */
--duration-fast: 100ms;
--duration-base: 200ms;
--duration-slow: 300ms;
--easing-ease-in: cubic-bezier(0.4, 0, 1, 1);
--easing-ease-out: cubic-bezier(0, 0, 0.2, 1);
--easing-ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
```

### Implementation in React

**Option 1: CSS Custom Properties (Recommended)**

```tsx
// styles/tokens.css
:root {
  --color-primary-500: #0066FF;
  --space-4: 16px;
  /* ...all tokens... */
}

// React Component
const Button = ({ variant = 'primary' }) => (
  <button
    style={{
      backgroundColor: 'var(--color-primary-500)',
      padding: 'var(--space-4)',
    }}
  >
    Click me
  </button>
);
```

**Option 2: Tailwind CSS (Alternative)**

Create Tailwind config from design tokens:

```js
// tailwind.config.js
export default {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#E8F3FF',
          500: '#0066FF',
          600: '#0052CC',
        },
        // ...all colors...
      },
      spacing: {
        4: '16px',
        6: '24px',
        // ...all spacing...
      },
      fontSize: {
        xs: '12px',
        sm: '13.5px',
        base: '15px',
        // ...all sizes...
      },
    },
  },
};
```

---

## Component Implementation Map

### Button Component

**Figma Reference:** `Component Library / Button` (Page 2)

**React Implementation:**

```tsx
// src/components/Button.tsx
import React from 'react';

interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'tertiary' | 'danger' | 'success';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  loading?: boolean;
  icon?: React.ReactNode;
  onClick?: () => void;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  icon,
  onClick,
  children,
}) => {
  const baseStyle = {
    borderRadius: 'var(--radius-md)',
    fontWeight: 'var(--font-weight-medium)',
    fontSize: 'var(--font-size-sm)',
    transition: 'all var(--duration-fast) var(--easing-ease-out)',
    border: 'none',
    cursor: disabled ? 'not-allowed' : 'pointer',
  };

  const sizeStyles = {
    small: { padding: `${8}px ${16}px`, minHeight: '32px' },
    medium: { padding: `${12}px ${24}px`, minHeight: '40px' },
    large: { padding: `${16}px ${32}px`, minHeight: '48px' },
  };

  const variantStyles = {
    primary: {
      backgroundColor: 'var(--color-primary-500)',
      color: 'white',
      '&:hover': { backgroundColor: 'var(--color-primary-600)' },
    },
    secondary: {
      backgroundColor: 'var(--color-neutral-100)',
      color: 'var(--color-neutral-900)',
      '&:hover': { backgroundColor: 'var(--color-neutral-200)' },
    },
    danger: {
      backgroundColor: 'var(--color-error-500)',
      color: 'white',
      '&:hover': { backgroundColor: 'var(--color-error-600)' },
    },
    // ...other variants...
  };

  return (
    <button
      style={{
        ...baseStyle,
        ...sizeStyles[size],
        ...variantStyles[variant],
        opacity: disabled ? 0.5 : 1,
      }}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading && <span>⏳</span>}
      {icon && <span style={{ marginRight: 'var(--space-2)' }}>{icon}</span>}
      {children}
    </button>
  );
};
```

### Form Input Component

**Figma Reference:** `Component Library / TextInput` (Page 2)

```tsx
// src/components/Input.tsx
interface InputProps {
  variant?: 'default' | 'filled' | 'search';
  size?: 'small' | 'medium' | 'large';
  state?: 'default' | 'focus' | 'filled' | 'disabled' | 'error' | 'success';
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  icon?: React.ReactNode;
  errorMessage?: string;
}

export const Input: React.FC<InputProps> = ({
  variant = 'default',
  size = 'medium',
  state = 'default',
  placeholder,
  value,
  onChange,
  icon,
  errorMessage,
}) => {
  const sizeStyles = {
    small: { padding: 'var(--space-2) var(--space-3)', fontSize: 'var(--font-size-xs)' },
    medium: { padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--font-size-base)' },
    large: { padding: 'var(--space-4) var(--space-5)', fontSize: 'var(--font-size-lg)' },
  };

  const stateStyles = {
    default: { borderColor: 'var(--color-neutral-200)', borderWidth: '1px' },
    focus: { borderColor: 'var(--color-primary-500)', boxShadow: '0 0 0 3px var(--color-primary-50)' },
    error: { borderColor: 'var(--color-error-500)', borderWidth: '1px' },
    success: { borderColor: 'var(--color-success-500)', borderWidth: '1px' },
    disabled: { backgroundColor: 'var(--color-neutral-50)', color: 'var(--color-neutral-300)' },
  };

  return (
    <div>
      <input
        style={{
          borderRadius: 'var(--radius-md)',
          fontFamily: 'var(--font-family-system)',
          ...sizeStyles[size],
          ...stateStyles[state],
        }}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        disabled={state === 'disabled'}
      />
      {errorMessage && state === 'error' && (
        <p style={{ color: 'var(--color-error-500)', fontSize: 'var(--font-size-xs)', marginTop: 'var(--space-1)' }}>
          {errorMessage}
        </p>
      )}
    </div>
  );
};
```

### Card Component

**Figma Reference:** `Component Library / Card` (Page 2)

```tsx
interface CardProps {
  header?: React.ReactNode;
  footer?: React.ReactNode;
  elevated?: boolean;
  children: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ header, footer, elevated = false, children }) => (
  <div
    style={{
      backgroundColor: 'var(--color-neutral-0)',
      border: '1px solid var(--color-neutral-200)',
      borderRadius: 'var(--radius-md)',
      boxShadow: elevated ? 'var(--shadow-md)' : 'var(--shadow-sm)',
      padding: 'var(--space-6)',
      transition: 'box-shadow var(--duration-fast)',
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.boxShadow = 'var(--shadow-md)';
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.boxShadow = elevated ? 'var(--shadow-md)' : 'var(--shadow-sm)';
    }}
  >
    {header && <div style={{ marginBottom: 'var(--space-4)' }}>{header}</div>}
    <div>{children}</div>
    {footer && <div style={{ marginTop: 'var(--space-4)' }}>{footer}</div>}
  </div>
);
```

---

## Screen Implementation Guidelines

### Patient Portal: SCR-P-004 (Search & Book)

**Figma Frame:** `.propel/context/figma/figma-design-system.md` → Page 3

**Component Hierarchy:**
```
Page
├── TopBar (Logo + Navigation)
├── Container
│   ├── Page Title
│   ├── FilterSection
│   │   ├── DateInput (TextInput variant)
│   │   ├── TimeSelect (Select component)
│   │   ├── ProviderSearch (TextInput + search icon)
│   │   ├── SpecialtySelect (Select component)
│   │   └── SearchButton (Button variant="primary")
│   ├── ResultsGrid
│   │   └── AppointmentCard[] (reusable card components)
│   │       ├── ProviderName
│   │       ├── Specialty
│   │       ├── LocationBadge
│   │       ├── DateTime
│   │       ├── Rating
│   │       └── SelectButton
│   └── RecentlyViewed
└── Footer
```

**Styling Implementation:**

```tsx
// src/pages/AppointmentSearch.tsx
import { useState } from 'react';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Card } from '../components/Card';

export const AppointmentSearch = () => {
  const [filters, setFilters] = useState({});

  return (
    <div style={{ padding: 'var(--space-8)' }}>
      <h1 style={{ fontSize: 'var(--font-size-4xl)', marginBottom: 'var(--space-6)' }}>
        Search & Book Appointment
      </h1>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--space-6)',
          marginBottom: 'var(--space-8)',
        }}
      >
        <Input placeholder="Preferred Date" type="date" />
        <select style={{ padding: 'var(--space-3)', borderRadius: 'var(--radius-md)' }}>
          <option>Morning (8am - 12pm)</option>
          <option>Afternoon (12pm - 5pm)</option>
        </select>
        <Input placeholder="Provider Name" />
        <Button>Search Slots</Button>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap: 'var(--space-6)',
        }}
      >
        {/* AppointmentCard components */}
      </div>
    </div>
  );
};
```

---

## Responsive Design Implementation

### Mobile-First Breakpoints

```tsx
// src/styles/breakpoints.ts
export const breakpoints = {
  xs: '320px',      // min-width
  sm: '640px',      // tablet
  md: '1024px',     // desktop
  lg: '1280px',     // large desktop
  xl: '1536px',     // extra large
};

// Usage in CSS
const gridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
  
  // Mobile: 1 column
  '@media (max-width: 640px)': {
    gridTemplateColumns: '1fr',
  },
  
  // Tablet: 2 columns
  '@media (max-width: 1024px)': {
    gridTemplateColumns: 'repeat(2, 1fr)',
  },
};
```

### Example: Responsive Sidebar

```tsx
const [sidebarOpen, setSidebarOpen] = useState(true);

return (
  <div style={{ display: 'flex' }}>
    {/* Sidebar hidden on mobile */}
    <aside
      style={{
        display: 'none',
        width: '240px',
        backgroundColor: 'var(--color-neutral-0)',
        padding: 'var(--space-6)',
        '@media (min-width: 1024px)': {
          display: 'block',
        },
      }}
    >
      {/* Navigation items */}
    </aside>

    {/* Main content */}
    <main style={{ flex: 1, padding: 'var(--space-6)' }}>
      {/* Page content */}
    </main>
  </div>
);
```

---

## Accessibility Implementation

### Color Contrast

All color combinations must maintain 4.5:1 minimum contrast ratio for normal text, 3:1 for large text.

**WCAG Compliant Combinations:**

```tsx
// ✓ Compliant (7.0:1 contrast)
const compliantButton = {
  backgroundColor: 'var(--color-primary-500)', // #0066FF
  color: 'white', // #FFFFFF
};

// ✗ Non-compliant (needs fix)
const poorContrast = {
  backgroundColor: 'var(--color-primary-100)', // #D0E7FF
  color: 'var(--color-primary-500)', // #0066FF (too light)
};
```

### Keyboard Navigation

```tsx
const Button = ({ onClick, children }) => (
  <button
    onClick={onClick}
    onKeyDown={(e) => {
      // Handle Enter and Space keys
      if (e.key === 'Enter' || e.key === ' ') {
        onClick?.();
      }
    }}
    style={{
      outline: 'none',
      '&:focus': {
        outline: '2px solid var(--color-primary-500)',
        outlineOffset: '2px',
      },
    }}
  >
    {children}
  </button>
);
```

### ARIA Labels

```tsx
<IconButton
  aria-label="Close dialog"
  onClick={onClose}
>
  ✕
</IconButton>

<input
  id="email"
  type="email"
  aria-labelledby="email-label"
  aria-describedby="email-error"
/>
<label id="email-label">Email Address</label>
<span id="email-error" role="alert">Email is required</span>
```

---

## Animation Implementation

### Button Hover Animation

```tsx
const Button = () => {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      style={{
        transform: isHovered ? 'translateY(-2px)' : 'translateY(0)',
        boxShadow: isHovered ? 'var(--shadow-md)' : 'var(--shadow-sm)',
        transition: 'all var(--duration-fast) var(--easing-ease-out)',
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      Hover me
    </button>
  );
};
```

### Modal Fade Animation

```tsx
import { useState } from 'react';

const Modal = ({ open, onClose, children }) => {
  return (
    <>
      {/* Backdrop */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
          transition: 'opacity var(--duration-base) var(--easing-ease-out)',
        }}
        onClick={onClose}
      />

      {/* Modal */}
      <div
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: open
            ? 'translate(-50%, -50%) scale(1)'
            : 'translate(-50%, -50%) scale(0.9)',
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
          transition: 'all var(--duration-base) var(--easing-ease-out)',
          backgroundColor: 'var(--color-neutral-0)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-8)',
          boxShadow: 'var(--shadow-xl)',
        }}
      >
        {children}
      </div>
    </>
  );
};
```

---

## Testing Guidelines

### Component Testing

```tsx
// src/components/Button.test.tsx
import { render, screen } from '@testing-library/react';
import { Button } from './Button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = jest.fn();
    render(<Button onClick={onClick}>Click</Button>);
    screen.getByText('Click').click();
    expect(onClick).toHaveBeenCalled();
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('has correct color variant', () => {
    const { container } = render(<Button variant="danger">Delete</Button>);
    expect(container.querySelector('button')).toHaveStyle(
      'backgroundColor: var(--color-error-500)'
    );
  });
});
```

---

## Design to Code Checklist

Before implementing a screen from Figma:

- [ ] **Layout**: Grid/flex layout matches Figma frame
- [ ] **Colors**: All colors use CSS variables (--color-*)
- [ ] **Typography**: Font sizes, weights, line heights match design system
- [ ] **Spacing**: Padding/margins use space tokens (--space-*)
- [ ] **Shadows**: Box shadows use shadow tokens (--shadow-*)
- [ ] **Border Radius**: All borders use radius tokens (--radius-*)
- [ ] **Interactive States**: Hover, focus, active, disabled all present
- [ ] **Responsive**: Mobile (375px), Tablet (768px), Desktop (1024px+)
- [ ] **Accessibility**: WCAG AA compliant colors, keyboard nav, ARIA labels
- [ ] **Animations**: Use duration/easing tokens (--duration-*, --easing-*)
- [ ] **Icons**: Consistent size and color with design system
- [ ] **Components**: Reuse existing components instead of duplicating code

---

## Storybook Integration (Optional)

Document components in Storybook for reference:

```tsx
// src/components/Button.stories.tsx
import { Button } from './Button';

export default {
  title: 'Components/Button',
  component: Button,
};

export const Primary = () => <Button variant="primary">Primary Button</Button>;
export const Secondary = () => <Button variant="secondary">Secondary</Button>;
export const Danger = () => <Button variant="danger">Delete</Button>;
export const Loading = () => <Button loading>Processing...</Button>;
export const Disabled = () => <Button disabled>Disabled</Button>;
```

Run Storybook:
```bash
npm run storybook
# Storybook will open at http://localhost:6006
```

---

## Figma Links & Resources

- **Figma Design File:** [PropellQ Design System v1.0](https://figma.com/file/...)
- **CSS Tokens Export:** `.propel/context/figma/tokens.css`
- **Component Library:** See Page 2 of Figma file
- **Screen Frames:** Pages 3-5 of Figma file
- **Interactive Prototypes:** Page 6 of Figma file (with clickable flows)

---

**Design Handoff Status:** Complete & Ready for Development  
**Last Updated:** 2026-06-17  
**Version:** 1.0

