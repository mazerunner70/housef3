# UI/UX Documentation

User interface and user experience design specifications for Housef3.

## Foundation Documents

### [ui_design.md](./ui_design.md)
**High-level UI design principles and structure**

Core principles: Clarity, efficiency, insightful, modern aesthetic, responsive, accessible

Top-level navigation, feature areas, and technology considerations.

---

### [ui_theme.md](./ui_theme.md)
**CSS scheme and component styling guide**

Color palette, typography, spacing system, component styling principles, and design tokens.

**Use this as the single source of truth for all styling decisions.**

## Navigation & Routing

### [contextual-sidebar-design.md](./contextual-sidebar-design.md)
Multi-level contextual sidebar navigation pattern with state management and responsive design.

### [breadcrumb-navigation-design.md](./breadcrumb-navigation-design.md)
Breadcrumb navigation system with entity-based branching and session resumability.

### [url-depth-management.md](./url-depth-management.md)
Strategy for managing URL depth using hybrid routing and query parameters.

## Page Designs

### [new_ui_accounts_view.md](./new_ui_accounts_view.md)
**Accounts Management Interface**

Comprehensive account management with list view, detail view, files tab, and transactions tab.

---

### [new_ui_transactions_view.md](./new_ui_transactions_view.md)
**Transactions Section with Tabbed Interface**

Three main tabs: Transactions List, Category Management, and Statements & Imports.

---

### [ui-design-transaction-import-page.md](./ui-design-transaction-import-page.md)
**Transaction Import UI Pages**

Import page design with compact account list, file upload, field mapping, and drag-and-drop support.

## Design System Quick Reference

### Colors
- **Primary:** Blue tones for actions and emphasis
- **Neutral:** Grays for structure and backgrounds
- **Status:** Green (success), red (error), yellow (warning), blue (info)

### Typography
- **Font:** System fonts (SF Pro, Segoe UI, Roboto)
- **Scale:** 12px (small) to 24px (h1)

### Spacing
- **Base unit:** 4px
- **Common values:** 4px, 8px, 12px, 16px, 24px, 32px

### Component Patterns
- Compact by default
- Clear visual hierarchy
- Consistent interaction patterns
- Accessible (ARIA, keyboard navigation)

## UI Development Workflow

1. **Start with foundation docs** - Review `ui_design.md` and `ui_theme.md`
2. **Check page designs** - Find relevant page design document
3. **Reference navigation patterns** - Consult sidebar/breadcrumb/URL docs
4. **Follow component organization** - See `../architecture/component-organization-strategy.md`
5. **Maintain consistency** - Use established patterns and styles


