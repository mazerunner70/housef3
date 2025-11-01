# Sidebar Registry Pattern

## Overview
The sidebar system uses a **registry pattern** to decouple the base `ContextualSidebar` component from domain-specific sidebar implementations. This ensures clean separation of concerns and makes the system extensible.

## Architecture

### Core Components

1. **`sidebarRegistry.ts`** - Registry singleton that maps routes to sidebar components
2. **`registerSidebars.ts`** - Registration file that imports and registers all sidebars
3. **`ContextualSidebar.tsx`** - Generic base component that looks up sidebars from the registry
4. **Domain-specific sidebars** - Individual sidebar implementations in their respective domains

## How It Works

### 1. Registration (App Initialization)
```typescript
// main.tsx
import { registerAllSidebars } from './components/navigation/sidebar-content/registerSidebars'
registerAllSidebars() // Called once at app startup
```

### 2. Registry Pattern
```typescript
// registerSidebars.ts
export function registerAllSidebars(): void {
    sidebarRegistry.register('transactions', TransactionsSidebarContent);
    sidebarRegistry.register('accounts', AccountsSidebarContent);
    // ... more registrations
}
```

### 3. Lookup (Runtime)
```typescript
// ContextualSidebar.tsx
const SidebarComponent = sidebarRegistry.get(route) || sidebarRegistry.get('default');
return <SidebarComponent sidebarCollapsed={sidebarCollapsed} />;
```

## Adding a New Sidebar

To add a new sidebar for a domain:

1. **Create your sidebar component** in `components/domain/{feature}/sidebar/`
```typescript
// components/domain/myfeature/sidebar/MyFeatureSidebarContent.tsx
const MyFeatureSidebarContent: React.FC<Props> = ({ sidebarCollapsed }) => {
    return <BaseSidebarContent config={myFeatureConfig} sidebarCollapsed={sidebarCollapsed} />;
};
```

2. **Register it** in `registerSidebars.ts`
```typescript
import MyFeatureSidebarContent from '@/components/domain/myfeature/sidebar/MyFeatureSidebarContent';

export function registerAllSidebars(): void {
    // ... existing registrations
    sidebarRegistry.register('myfeature', MyFeatureSidebarContent);
}
```

3. **Done!** The sidebar will automatically be used when navigating to `/myfeature`

## Benefits

✅ **Decoupling**: `ContextualSidebar` doesn't know about specific sidebar implementations  
✅ **Extensibility**: Easy to add new sidebars without modifying base components  
✅ **Maintainability**: Each domain manages its own sidebar  
✅ **Single Source of Truth**: All registrations in one place  
✅ **Type Safety**: TypeScript ensures all registered components match the interface

## File Locations

- **Shared sidebars**: `components/navigation/sidebar-content/`
- **Domain sidebars**: `components/domain/{feature}/sidebar/`
- **Registry files**: `components/navigation/sidebar-content/sidebarRegistry.ts`
- **Registration**: `components/navigation/sidebar-content/registerSidebars.ts`

