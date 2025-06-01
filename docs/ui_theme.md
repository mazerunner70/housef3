# UI Theme and Style Guide

This document outlines the CSS scheme for a professional and compact user interface.

## 1. Color Palette

### Primary Colors
- **Primary Brand**: `#2C3E50` (Midnight Blue) - Used for main actions, headers, and important elements.
- **Secondary Brand**: `#3498DB` (Peter River Blue) - Used for secondary actions, highlights, and accents.

### Neutral Colors
- **Background (Light)**: `#F8F9FA` (Very Light Gray)
- **Background (Darker/Subtle)**: `#ECF0F1` (Clouds)
- **Borders/Dividers**: `#BDC3C7` (Silver)
- **Text (Primary)**: `#212529` (Near Black)
- **Text (Secondary)**: `#7F8C8D` (Asbestos - a muted gray)
- **Text (Disabled)**: `#B0BEC5` (Light Gray Blue)

### Accent & Status Colors
- **Accent**: `#E67E22` (Carrot Orange) - For calls to action or attention-grabbing elements (use sparingly).
- **Success**: `#2ECC71` (Emerald Green)
- **Warning**: `#F1C40F` (Sun Flower Yellow)
- **Error/Danger**: `#E74C3C` (Alizarin Crimson)
- **Info**: `#3498DB` (Peter River Blue) - Same as secondary brand for consistency.

## 2. Typography

### Font Family
- **Primary Font**: 'Inter', sans-serif (Fallback: 'Helvetica Neue', 'Arial', sans-serif)
  - *Reasoning*: Inter is a highly legible and modern sans-serif font designed specifically for user interfaces. It offers excellent readability at various sizes.

### Font Scale (Modular Scale - e.g., 1.25 ratio)
- **Base Font Size**: 15px (for body text)
- **Line Height (Body)**: 1.6

- **Headings**:
  - `h1`: 32px (Bold)
  - `h2`: 26px (Bold)
  - `h3`: 20px (Semi-Bold)
  - `h4`: 16px (Semi-Bold)
- **Body Text**: 15px (Regular)
- **Small/Caption Text**: 13px (Regular)
- **Button Text**: 14px (Medium or Semi-Bold)

## 3. Spacing & Sizing (Compactness)

- **Base Unit**: 4px. All margins, paddings, and fixed sizes should be multiples of this unit (e.g., 4px, 8px, 12px, 16px, 24px, 32px).
- **Layout**: Utilize Flexbox and CSS Grid for efficient and responsive layouts.
- **Padding**:
  - General container padding: 16px - 24px.
  - Input fields & buttons: 8px 12px (vertical horizontal). Aim for a shorter height to be compact.
- **Margins**: Use margins consistently to separate elements, but avoid excessive empty space. Collapse margins where appropriate.
- **Border Radius**: 4px for most elements (buttons, inputs, cards) for a subtle rounded corner. 8px for larger containers if desired.

## 4. Component Styling Principles

### Buttons
- **Padding**: 8px 16px (for standard buttons), 6px 12px (for smaller/compact buttons).
- **Height**: Aim for a standard height like 36px or 40px for form elements to ensure vertical rhythm.
- **States**: Clear hover, focus, active, and disabled states.
  - *Hover*: Slight darken/lighten of background or border.
  - *Focus*: Subtle box-shadow or outline (accessibility).
- **Primary Button**: `Primary Brand` background, light text.
- **Secondary Button**: `Secondary Brand` background or outline with `Secondary Brand` text.
- **Tertiary/Text Button**: Minimal styling, often just text color change on hover.

### Forms
- **Input Fields**:
  - Background: `#FFFFFF` (White)
  - Border: 1px solid `NeutralColors.Borders/Dividers`
  - Focus Border: `PrimaryColors.SecondaryBrand`
  - Padding: 8px 12px
  - Font Size: 14px or 15px
- **Labels**: Clear, associated with inputs. Font size 14px, `TextColors.Primary`.
- **Form Layout**: Stack labels above inputs or use a two-column layout for wider forms to save vertical space. Consistent spacing between form groups.

### Cards & Containers
- **Background**: `NeutralColors.Background (Light)` or `White`.
- **Border**: Optional, 1px solid `NeutralColors.Borders/Dividers` or subtle `box-shadow`.
  - `box-shadow: 0 2px 4px rgba(0,0,0,0.05);`
- **Padding**: 16px or 20px.

### Icons
- Use a consistent icon set (e.g., Feather Icons, Material Icons, or custom SVG icons).
- Size: Typically 16px, 20px, or 24px, aligned with text.

## 5. General Principles
- **Consistency**: Apply styles consistently across all UI elements.
- **Accessibility (WCAG AA)**: Ensure sufficient color contrast, keyboard navigability, and ARIA attributes where necessary.
- **Responsiveness**: Design for various screen sizes.
- **Performance**: Optimize CSS, use modern CSS features efficiently.
- **Compactness**: Prioritize information density without sacrificing readability. Minimize unnecessary graphical embellishments. Use negative space thoughtfully.

## Implementation Notes
- Consider using CSS Custom Properties (Variables) for colors, fonts, and spacing units to make the theme easily maintainable and customizable.
  ```css
  :root {
    --primary-color: #2C3E50;
    --font-body: 'Inter', sans-serif;
    --spacing-unit: 4px;
    /* ... etc. */
  }
  ```
- Structure CSS files logically (e.g., by component, layout, or utility classes).
- The new UI components should adhere to the `frontend/src/new-ui/` directory structure. 