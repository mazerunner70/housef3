# Contextual Sidebar Development Conventions

> **⚠️ NOTE**: This document describes the legacy architecture. For the current registry-based architecture, see [README.md](./README.md).
> 
> **Current Structure**:
> - Domain-specific sidebars now live in `components/domain/{feature}/sidebar/`
> - Shared infrastructure remains in `components/navigation/sidebar-content/`
> - Registration happens via `registerSidebars.ts`

## Overview
This document defines the conventions and patterns for developing contextual sidebar components in the `/sidebar-content/` folder. The sidebar system uses a configuration-driven approach to eliminate code duplication and provide consistent navigation experiences across different application contexts.

## Architecture Overview

### Core Components
- **`ContextualSidebar.tsx`** - Main sidebar container that routes to appropriate content
- **`BaseSidebarContent.tsx`** - Reusable base component that processes configurations
- **`SidebarConfigFactory.ts`** - Factory functions for processing configurations
- **`types.ts`** - TypeScript interfaces for the configuration system
- **`configs/`** - Configuration objects for different sidebar contexts

### Design Principles
1. **Configuration-Driven**: Use declarative configuration objects instead of imperative component logic
2. **DRY (Don't Repeat Yourself)**: Eliminate code duplication across sidebar components
3. **Type Safety**: Comprehensive TypeScript interfaces for all configurations
4. **Separation of Concerns**: Separate navigation logic from presentation logic
5. **Consistency**: Uniform behavior and styling across all sidebar contexts

## File Naming Conventions

### Sidebar Content Components
```
{Context}SidebarContent.tsx
```
**Examples:**
- `AccountsSidebarContent.tsx`
- `TransactionsSidebarContent.tsx`
- `ImportSidebarContent.tsx`
- `CategoriesSidebarContent.tsx`

### Configuration Files
```
configs/{context}Config.ts
```
**Examples:**
- `configs/accountsConfig.ts`
- `configs/transactionsConfig.ts`
- `configs/importSidebarConfig.ts`
- `configs/categoriesConfig.ts`

### Supporting Files
- `types.ts` - All TypeScript interfaces
- `SidebarConfigFactory.ts` - Factory functions and utilities
- `BaseSidebarContent.tsx` - Base component implementation

## Component Development Patterns

### 1. Configuration-Based Components (Preferred)

Use `BaseSidebarContent` with configuration objects for new sidebar contexts:

```typescript
// configs/importSidebarConfig.ts
import { SidebarContentConfig } from '../types';
import { createNavItem, createActionItem } from '../SidebarConfigFactory';

export const importSidebarConfig: SidebarContentConfig = {
    sections: [
        {
            type: 'navigation',
            title: 'Import Tools',
            items: [
                createNavItem('upload-file', 'Upload File', '/import/upload', '📤'),
                createNavItem('import-history', 'Import History', '/import/history', '📋'),
                createActionItem('field-mappings', 'Field Mappings', () => openMappingsDialog(), '🗂️')
            ],
            collapsible: false
        }
    ]
};

// ImportSidebarContent.tsx
import React from 'react';
import BaseSidebarContent from './BaseSidebarContent';
import { importSidebarConfig } from './configs/importSidebarConfig';

interface ImportSidebarContentProps {
    sidebarCollapsed: boolean;
}

const ImportSidebarContent: React.FC<ImportSidebarContentProps> = ({ sidebarCollapsed }) => {
    return (
        <BaseSidebarContent
            sidebarCollapsed={sidebarCollapsed}
            config={importSidebarConfig}
        />
    );
};

export default ImportSidebarContent;
```

### 2. Custom Components (When Needed)

For complex dynamic behavior that can't be handled by configuration:

```typescript
// AccountsSidebarContent.tsx
import React, { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import SidebarSection from '@/components/navigation/SidebarSection';
import useAccountsWithStore from '@/stores/useAccountsStore';

interface AccountsSidebarContentProps {
    sidebarCollapsed: boolean;
}

const AccountsSidebarContent: React.FC<AccountsSidebarContentProps> = ({ sidebarCollapsed }) => {
    const { accounts } = useAccountsWithStore();
    
    const sections = useMemo(() => {
        // Dynamic section generation based on loaded accounts
        return generateAccountSections(accounts);
    }, [accounts]);

    return (
        <>
            {sections.map((section, index) => (
                <SidebarSection
                    key={`${section.type}-${index}`}
                    section={section}
                    sidebarCollapsed={sidebarCollapsed}
                />
            ))}
        </>
    );
};

export default AccountsSidebarContent;
```

## Configuration System

### Section Types
```typescript
type SectionType = 'navigation' | 'context' | 'actions';
```

- **`navigation`** - Primary navigation links (e.g., main menu items)
- **`context`** - Contextual information and secondary navigation
- **`actions`** - Action buttons and quick actions

### Item Types

#### Navigation Items
```typescript
createNavItem(
    'item-id',           // Unique identifier
    'Display Label',     // Text shown to user
    '/path/to/route',    // Navigation URL
    '🔗',               // Optional icon
    customActiveCheck    // Optional custom active state function
)
```

#### Action Items
```typescript
createActionItem(
    'action-id',         // Unique identifier
    'Action Label',      // Button text
    () => doSomething(), // Click handler function
    '⚡'                // Optional icon
)
```

#### Filter Items
```typescript
createFilterItem(
    'filter-id',                    // Unique identifier
    'Filter Label',                 // Display text
    '/base/url',                   // Base URL for navigation
    { filter: 'value', tab: 'x' }, // URL search parameters
    '🔍'                           // Optional icon
)
```

### Dynamic Sections
For sections that depend on runtime data:

```typescript
export const dynamicConfig: SidebarContentConfig = {
    sections: [
        // Static sections...
    ],
    dynamicSections: ({ pathname, searchParams }) => {
        // Generate sections based on current context
        return [
            {
                type: 'context',
                title: 'Dynamic Content',
                items: generateDynamicItems(pathname, searchParams)
            }
        ];
    }
};
```

## Integration with ContextualSidebar

### Adding New Sidebar Content

1. **Create Configuration** (if using config-based approach):
```typescript
// configs/newFeatureConfig.ts
export const newFeatureConfig: SidebarContentConfig = {
    sections: [/* ... */]
};
```

2. **Create Component**:
```typescript
// NewFeatureSidebarContent.tsx
import BaseSidebarContent from './BaseSidebarContent';
import { newFeatureConfig } from './configs/newFeatureConfig';

const NewFeatureSidebarContent: React.FC<Props> = ({ sidebarCollapsed }) => {
    return <BaseSidebarContent sidebarCollapsed={sidebarCollapsed} config={newFeatureConfig} />;
};
```

3. **Register in ContextualSidebar**:
```typescript
// ContextualSidebar.tsx
import NewFeatureSidebarContent from './sidebar-content/NewFeatureSidebarContent';

const renderSidebarContent = () => {
    const route = pathSegments[0];
    
    switch (route) {
        case 'new-feature':
            return <NewFeatureSidebarContent sidebarCollapsed={sidebarCollapsed} />;
        // ... other cases
    }
};
```

## Styling Conventions

### CSS Class Naming
Follow BEM (Block Element Modifier) methodology:

```css
/* Block */
.sidebar-section { }

/* Elements */
.sidebar-section__title { }
.sidebar-section__items { }

/* Modifiers */
.sidebar-section--navigation { }
.sidebar-section--context { }
.sidebar-section--actions { }
```

### Section-Specific Styling
```css
/* Navigation sections */
.sidebar-section-navigation {
    border-bottom: 1px solid var(--border-color);
}

/* Context sections */
.sidebar-section-context {
    background-color: var(--context-bg);
}

/* Action sections */
.sidebar-section-actions {
    margin-top: auto; /* Push to bottom */
}
```

### Responsive Behavior
```css
/* Collapsed sidebar */
.contextual-sidebar.collapsed .sidebar-section-title {
    display: none;
}

.contextual-sidebar.collapsed .sidebar-item-label {
    display: none;
}
```

## State Management

### Navigation State
Use `useNavigationStore` for sidebar-related state:

```typescript
import { useNavigationStore } from '@/stores/navigationStore';

const {
    sidebarCollapsed,
    setSidebarCollapsed,
    selectedAccount,
    selectedFile,
    currentView
} = useNavigationStore();
```

### Route-Based State
Access current route information:

```typescript
import { useLocation } from 'react-router-dom';

const location = useLocation();
const pathSegments = location.pathname.split('/').filter(Boolean);
const searchParams = new URLSearchParams(location.search);
```

## Accessibility Standards

### Keyboard Navigation
- **Tab order**: Logical progression through sidebar items
- **Arrow keys**: Navigate within sections
- **Enter/Space**: Activate items
- **Escape**: Collapse expanded sections

### ARIA Attributes
```typescript
// Section titles
<h3 role="heading" aria-level="3">{section.title}</h3>

// Navigation sections
<nav role="navigation" aria-label="Contextual navigation">

// Action buttons
<button aria-label="Import transactions" onClick={handleImport}>
```

### Screen Reader Support
```typescript
// Live regions for dynamic content
<div aria-live="polite" aria-atomic="true">
    {importStatus && `Import in progress: ${importStatus}`}
</div>

// Descriptive labels
<button aria-describedby="import-help">
    Import File
</button>
<div id="import-help" className="sr-only">
    Upload CSV, OFX, or QIF files to import transactions
</div>
```

## Testing Conventions

### Unit Tests
Test configuration processing and component rendering:

```typescript
// __tests__/ImportSidebarContent.test.tsx
describe('ImportSidebarContent', () => {
    it('renders all configured sections', () => {
        render(<ImportSidebarContent sidebarCollapsed={false} />);
        
        expect(screen.getByText('Import Tools')).toBeInTheDocument();
        expect(screen.getByText('Upload File')).toBeInTheDocument();
    });
    
    it('handles collapsed state correctly', () => {
        render(<ImportSidebarContent sidebarCollapsed={true} />);
        
        expect(screen.queryByText('Import Tools')).not.toBeInTheDocument();
    });
});
```

### Configuration Tests
```typescript
// __tests__/configs/importSidebarConfig.test.ts
describe('importSidebarConfig', () => {
    it('generates correct section structure', () => {
        const context = createMockContext();
        const sections = createSidebarSections(importSidebarConfig, context);
        
        expect(sections).toHaveLength(2);
        expect(sections[0].type).toBe('navigation');
    });
});
```

### Integration Tests
```typescript
// __tests__/ContextualSidebar.integration.test.tsx
describe('ContextualSidebar Integration', () => {
    it('shows import sidebar on import route', () => {
        renderWithRouter(<ContextualSidebar />, '/import');
        
        expect(screen.getByText('Upload File')).toBeInTheDocument();
    });
});
```

## Performance Considerations

### Memoization
Use `useMemo` for expensive section generation:

```typescript
const sections = useMemo(() => {
    return generateComplexSections(accounts, files, transactions);
}, [accounts, files, transactions]);
```

### Lazy Loading
For sidebars with heavy data dependencies:

```typescript
const AccountsSidebarContent = React.lazy(() => import('./AccountsSidebarContent'));

// In ContextualSidebar.tsx
<Suspense fallback={<SidebarSkeleton />}>
    <AccountsSidebarContent sidebarCollapsed={sidebarCollapsed} />
</Suspense>
```

### Configuration Caching
Cache static configurations:

```typescript
// configs/index.ts
export const configCache = new Map<string, SidebarContentConfig>();

export const getConfig = (key: string): SidebarContentConfig => {
    if (!configCache.has(key)) {
        configCache.set(key, loadConfig(key));
    }
    return configCache.get(key)!;
};
```

## Error Handling

### Configuration Validation
```typescript
const validateConfig = (config: SidebarContentConfig): void => {
    if (!config.sections || config.sections.length === 0) {
        throw new Error('Sidebar configuration must have at least one section');
    }
    
    config.sections.forEach((section, index) => {
        if (!section.items || section.items.length === 0) {
            console.warn(`Section ${index} has no items`);
        }
    });
};
```

### Graceful Degradation
```typescript
const SafeSidebarContent: React.FC<Props> = ({ config, ...props }) => {
    try {
        return <BaseSidebarContent config={config} {...props} />;
    } catch (error) {
        console.error('Sidebar configuration error:', error);
        return <DefaultSidebarContent {...props} />;
    }
};
```

## Migration Guide

### From Custom Components to Configuration

1. **Identify Static Sections**: Convert hardcoded sections to configuration objects
2. **Extract Dynamic Logic**: Move dynamic section generation to `dynamicSections` function
3. **Update Imports**: Replace custom component with `BaseSidebarContent`
4. **Test Thoroughly**: Ensure all navigation and interactions work correctly

### Example Migration
```typescript
// Before (Custom Component)
const OldSidebarContent = ({ sidebarCollapsed }) => {
    return (
        <>
            <SidebarSection section={{
                type: 'navigation',
                title: 'Tools',
                items: [
                    { id: 'upload', label: 'Upload', onClick: handleUpload }
                ]
            }} />
        </>
    );
};

// After (Configuration-Based)
const newConfig: SidebarContentConfig = {
    sections: [{
        type: 'navigation',
        title: 'Tools',
        items: [
            createActionItem('upload', 'Upload', handleUpload)
        ]
    }]
};

const NewSidebarContent = ({ sidebarCollapsed }) => {
    return <BaseSidebarContent config={newConfig} sidebarCollapsed={sidebarCollapsed} />;
};
```

## Best Practices

### Do's
- ✅ Use configuration-based approach for simple, static sidebars
- ✅ Implement proper TypeScript interfaces for all configurations
- ✅ Follow consistent naming conventions
- ✅ Include accessibility attributes
- ✅ Test both collapsed and expanded states
- ✅ Use semantic section types (`navigation`, `context`, `actions`)
- ✅ Implement proper error boundaries
- ✅ Cache expensive computations with `useMemo`

### Don'ts
- ❌ Don't duplicate navigation logic across components
- ❌ Don't hardcode URLs in multiple places
- ❌ Don't ignore accessibility requirements
- ❌ Don't create custom components for simple static content
- ❌ Don't forget to handle loading and error states
- ❌ Don't use inline styles instead of CSS classes
- ❌ Don't create deeply nested item hierarchies (max 2-3 levels)

## Future Enhancements

### Planned Features
- **Theme Support**: Dynamic theming for sidebar sections
- **Drag & Drop**: Reorderable sidebar sections
- **Customization**: User-configurable sidebar layouts
- **Analytics**: Track sidebar usage patterns
- **Keyboard Shortcuts**: Hotkeys for common sidebar actions

### Extension Points
- **Custom Item Types**: Beyond navigation, action, and filter items
- **Section Plugins**: Pluggable section types for third-party features
- **Dynamic Icons**: Icon selection based on context or user preferences
- **Internationalization**: Multi-language support for sidebar content

This document should be updated whenever new patterns emerge or architectural decisions change the sidebar system.
