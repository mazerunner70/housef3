# When to Abstract Composition Pages

## Current Decision: Start Explicit (Option 1)

**Strategy**: Use explicit, named composition pages. Abstract to config-driven pattern only when duplication becomes painful.

## The "Rule of Three"

Don't abstract until you have **three similar instances**:

```
1 instance  → Write it explicitly
2 instances → Tolerate duplication (might be coincidence)
3 instances → Consider abstraction (pattern confirmed)
5+ instances → Definitely abstract
```

## Current State: Explicit Pages ✅

### Example: TransactionsPage (to be renamed)
```typescript
// pages/FinancialManagementPage.tsx (or TransactionsHubPage.tsx)
const FinancialManagementPage = () => {
  const [activeTab, setActiveTab] = useState('LIST');
  
  return (
    <div className="financial-management-page">
      <header>
        <h1>Financial Management</h1>
      </header>
      
      <Tabs activeTab={activeTab} onChange={setActiveTab}>
        <Tab id="LIST" label="Transactions">
          <TransactionsListTab />
        </Tab>
        <Tab id="CATEGORIES" label="Categories">
          <CategoryManagementTab />
        </Tab>
        <Tab id="IMPORTS" label="Imports">
          <StatementsImportsTab />
        </Tab>
        <Tab id="TRANSFERS" label="Transfers">
          <TransfersDashboard />
        </Tab>
      </Tabs>
    </div>
  );
};
```

**Benefits:**
- ✅ Clear and explicit
- ✅ Easy to debug
- ✅ Easy to customize per page
- ✅ No indirection

**Cost:**
- ❌ Duplication if we have many similar pages

## When to Abstract: Future Trigger Points

### Trigger 1: Three+ Similar Tab Structures
```
If you create:
1. FinancialManagementPage (4 tabs)
2. PortfolioManagementPage (5 tabs)
3. ReportsWorkspacePage (3 tabs)

→ Consider abstracting tab pattern
```

### Trigger 2: Repetitive Tab Logic
```typescript
// If you're copy-pasting this everywhere:
const [activeTab, setActiveTab] = useState(defaultTab);
const handleTabChange = (newTab) => {
  setActiveTab(newTab);
  // Maybe save to URL or localStorage
  // Maybe analytics tracking
};
```

### Trigger 3: Consistent Requirements
```
If all tab pages need:
- URL persistence (activeTab in query params)
- Analytics tracking
- Keyboard shortcuts
- Loading states
- Error boundaries

→ Good candidate for abstraction
```

## Future Abstraction Approach (When Needed)

### Config-Driven Pattern

```typescript
// configs/pageConfigs.ts
export const financialManagementConfig = {
  title: "Financial Management",
  route: "/financial",
  defaultTab: "LIST",
  tabs: [
    {
      id: "LIST",
      label: "Transactions",
      component: TransactionsListTab,
      icon: "📊"
    },
    {
      id: "CATEGORIES",
      label: "Categories",
      component: CategoryManagementTab,
      icon: "🏷️"
    },
    {
      id: "IMPORTS",
      label: "Imports",
      component: StatementsImportsTab,
      icon: "📥"
    },
    {
      id: "TRANSFERS",
      label: "Transfers",
      component: TransfersDashboard,
      icon: "↔️"
    }
  ]
};

// components/TabbedPage.tsx (generic)
const TabbedPage = ({ config }) => {
  const [activeTab, setActiveTab] = useState(config.defaultTab);
  
  return (
    <div className="tabbed-page">
      <header>
        <h1>{config.title}</h1>
      </header>
      
      <Tabs activeTab={activeTab} onChange={setActiveTab}>
        {config.tabs.map(tab => (
          <Tab key={tab.id} id={tab.id} label={tab.label} icon={tab.icon}>
            <tab.component />
          </Tab>
        ))}
      </Tabs>
    </div>
  );
};

// App.tsx
<Route 
  path="/financial" 
  element={<TabbedPage config={financialManagementConfig} />} 
/>
```

### Benefits of Abstraction (When Time Comes)
- ✅ DRY - one implementation for all tab pages
- ✅ Consistent behavior
- ✅ Easier to add features (URL persistence, analytics, etc.)
- ✅ Configuration is data (could come from backend)

### Costs of Abstraction
- ❌ Harder to understand flow (indirection)
- ❌ Harder to customize individual pages
- ❌ Configuration complexity grows
- ❌ TypeScript types become complex

## Migration Path (When Abstracting)

### Step 1: Identify Pattern
Count similar tab structures. If 5+, proceed.

### Step 2: Extract Common Component
Create `TabbedPage` with common logic.

### Step 3: Create Configs
```typescript
configs/
├── financialManagementConfig.ts
├── portfolioManagementConfig.ts
└── reportsWorkspaceConfig.ts
```

### Step 4: Migrate One Page at a Time
Don't migrate all at once. Prove the pattern works.

### Step 5: Keep Escape Hatch
Allow pages to opt-out and stay explicit if they have unique needs.

## Current Recommendation: DON'T ABSTRACT YET

**Why:**
- Only 1-2 similar tab pages currently
- No confirmed pattern yet
- Explicit pages are working fine
- No pain from duplication

**When to revisit:**
- 5+ similar tab structures
- Copy-pasting becoming painful
- Need to add consistent behavior across all (analytics, URL persistence, etc.)

## The Principle

> "Duplication is far cheaper than the wrong abstraction."
> — Sandi Metz

**Start simple. Abstract when the pattern is clear and the pain is real.**

## Current Status

✅ **Decision**: Use explicit, well-named pages  
✅ **Monitor**: Count similar tab structures  
⏸️ **Abstract**: When we hit 5+ similar patterns  

This is the right call! 🎯

