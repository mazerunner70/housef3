# Epoch Time and Date Handling Best Practices

## Core Principle

**Epoch time should ONLY be used for storage and API communication. Date objects should be used everywhere else in application logic.**

## The Pattern: Layered Date Handling

### 1. Storage & API Layer (Epoch Timestamps)

Use `number` (milliseconds since epoch) for:
- Database storage
- API requests and responses  
- URL parameters
- Local storage
- Configuration files

```typescript
// API Interface - Always use epoch timestamps
interface TransferDetectionRequest {
    startDate: EpochTimestamp; // milliseconds since epoch
    endDate: EpochTimestamp;   // milliseconds since epoch
}

// Backend storage - DynamoDB item
{
    "transactionDate": 1704067200000, // epoch timestamp
    "createdAt": 1704067200000
}
```

### 2. Service Layer (Conversion Boundary)

**Convert immediately at API boundaries:**

```typescript
// ✅ CORRECT: Convert at service boundary
export const detectPotentialTransfers = (dateRange: DateRange) => {
    // Convert Date objects to epoch for API call
    const apiRange = dateRangeToEpochRange(dateRange);
    
    const response = await ApiClient.get(`/api/transfers?startDate=${apiRange.startDate}`);
    
    // Convert epoch timestamps back to Date objects for application
    return {
        ...response,
        transfers: response.transfers.map(t => ({
            ...t,
            dateObject: epochToDate(t.date) // Add converted field
        }))
    };
};

// ❌ WRONG: Passing epoch timestamps through application layer  
export const detectPotentialTransfers = (startDate: number, endDate: number) => {
    // Forces all calling code to work with epoch timestamps
}
```

### 3. Application Logic Layer (Date Objects)

**Always work with Date objects in business logic:**

```typescript
// ✅ CORRECT: Application logic uses Date objects
const calculateProgress = (checkedRange: DateRange, accountRange: DateRange) => {
    const totalDays = daysBetween(accountRange.startDate, accountRange.endDate);
    const checkedDays = daysBetween(checkedRange.startDate, checkedRange.endDate);
    return Math.round((checkedDays / totalDays) * 100);
};

// ❌ WRONG: Manual epoch calculations scattered throughout code
const calculateProgress = (checkedStart: number, checkedEnd: number) => {
    const totalMs = checkedEnd - checkedStart;
    const totalDays = Math.ceil(totalMs / (1000 * 60 * 60 * 24)); // Error-prone
};
```

### 4. UI/Display Layer (Formatted Strings)

**Format Date objects for display:**

```typescript
// ✅ CORRECT: UI receives Date objects and formats them
const TransactionRow = ({ transaction }: { transaction: { dateObject: Date } }) => {
    return (
        <div>
            {formatDisplayDate(transaction.dateObject)}
            {formatRelativeDate(transaction.dateObject)}
        </div>
    );
};

// ❌ WRONG: UI doing epoch conversion
const TransactionRow = ({ transaction }: { transaction: { date: number } }) => {
    const date = new Date(transaction.date); // Conversion in UI
    return <div>{date.toLocaleDateString()}</div>;
};
```

## Type Safety Strategy

Use distinct types to prevent mixing layers:

```typescript
// Type system prevents accidentally mixing epochs and Date objects
type EpochTimestamp = number;  // For API/storage layer
type DateRange = { startDate: Date; endDate: Date };      // For application layer
type ApiDateRange = { startDate: EpochTimestamp; endDate: EpochTimestamp }; // For API boundaries
```

## Common Anti-Patterns to Avoid

### ❌ Don't: Mixed epoch/Date calculations

```typescript
// BAD: Mixing epoch and Date object operations
const isAfter = (epochDate: number, dateObj: Date) => {
    return epochDate > dateObj.getTime(); // Confusing and error-prone
};
```

### ❌ Don't: Late conversion in UI

```typescript
// BAD: Converting in every component
const Component = ({ timestamp }: { timestamp: number }) => {
    const date = new Date(timestamp); // Should be done in service layer
    return <span>{date.toLocaleDateString()}</span>;
};
```

### ❌ Don't: Manual epoch arithmetic

```typescript
// BAD: Manual calculations instead of utility functions  
const daysAgo = (timestamp: number) => {
    const now = Date.now();
    const diffMs = now - timestamp;
    return Math.floor(diffMs / (1000 * 60 * 60 * 24)); // Error-prone
};

// GOOD: Use utility functions
const daysAgo = (date: Date) => {
    return daysBetween(date, new Date());
};
```

## Migration Strategy

### Phase 1: Add Centralized Utilities
1. Create `dateUtils.ts` with conversion functions
2. Add type aliases for clarity (`EpochTimestamp`, etc.)

### Phase 2: Update Service Layer  
1. Add conversion at API boundaries
2. Make services return Date objects
3. Add legacy compatibility functions

### Phase 3: Update Application Layer
1. Refactor business logic to use Date objects
2. Replace manual calculations with utilities
3. Update component props to expect Date objects

### Phase 4: Update UI Layer
1. Remove epoch conversions from components
2. Use formatting utilities consistently  
3. Remove manual date arithmetic

## Benefits

1. **Type Safety**: Prevents accidentally mixing epochs and Date objects
2. **Consistency**: One clear pattern across the entire application
3. **Maintainability**: Centralized date logic is easier to update
4. **Testing**: Easier to mock and test with Date objects
5. **Debugging**: Clear separation makes issues easier to track
6. **Timezone Handling**: Date objects handle timezone conversion properly

## Examples in Codebase

### ✅ Good Examples

- `dateUtils.ts` - Centralized conversion utilities
- `TransferService.detectPotentialTransfers()` - Converts at API boundary
- Date range calculations using `daysBetween()` utility

### 🔄 Needs Refactoring

- Components directly converting epoch timestamps
- Business logic mixing epoch and Date calculations  
- Manual date arithmetic instead of utility functions

## Testing Strategy

```typescript
// Test with Date objects, convert to epoch only when testing API boundaries
describe('TransferService', () => {
    it('should detect transfers in date range', async () => {
        const dateRange: DateRange = {
            startDate: new Date('2024-01-01'),
            endDate: new Date('2024-01-31')
        };
        
        const result = await detectPotentialTransfers(dateRange);
        expect(result.transfers[0].dateObject).toBeInstanceOf(Date);
    });
});
```

This pattern ensures epoch timestamps are contained to storage/API boundaries while the application logic works with proper Date objects throughout.
