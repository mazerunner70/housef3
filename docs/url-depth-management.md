# URL Depth Management Strategy

## Problem Statement

In long navigation sessions, URL endpoints can grow excessively deep, leading to:
- URLs exceeding browser limits (~2000 characters)
- Poor user experience with unreadable URLs
- SEO issues with very deep paths
- Difficulty sharing/bookmarking complex views

## Current URL Structure

### Shallow Navigation (≤ 3 levels)
```
/accounts                                    → Account List
/accounts/:accountId                        → Account Detail  
/accounts/:accountId/files/:fileId         → File Transactions
/accounts/:accountId/transactions/:transactionId → Transaction Detail
```

### Potential Deep Navigation Issues
```
/accounts/:accountId/files/:fileId/transactions/:transactionId/categories/:categoryId/tags/:tagId
```

## Solution Strategy

### 1. Hybrid Routing Approach

**Shallow Routes** (≤ 3 levels): Use path segments
```
/accounts/acc123/files/file456
```

**Deep Routes** (> 3 levels): Switch to query parameters
```
/accounts/acc123?view=transaction&fileId=file456&transactionId=tx789&filter=category
```

### 2. URL Depth Monitoring

- **Warning threshold**: 1500 characters
- **Auto-switch**: Automatically use query params when depth exceeds 3 levels
- **Context compression**: Encode complex state into shorter parameters

### 3. Query Parameter Strategy

#### Core Navigation (always in path)
- Account ID: `/accounts/:accountId`
- Primary view context

#### Secondary Context (query parameters)
- `view`: Current view type (transaction, file, etc.)
- `fileId`: Selected file
- `transactionId`: Selected transaction
- `filter`: Applied filters
- `sort`: Sort preferences
- `page`: Pagination
- `dateRange`: Date filters
- `categoryId`: Category filters
- `tagId`: Tag filters

### 4. Context Management

#### Adding Context
```typescript
// Add filter without changing primary navigation
addContext({ filter: 'category:food', sort: 'date-desc' });
// URL: /accounts/123?view=transactions&filter=category:food&sort=date-desc
```

#### Clearing Context
```typescript
// Clear all secondary context, keep primary navigation
clearContext();
// URL: /accounts/123
```

### 5. URL Shortening for Complex States

For very complex navigation states:
```typescript
// Instead of: /accounts/123?view=transaction&fileId=f456&transactionId=t789&filter=cat:food&sort=date&page=2&dateRange=2024-01
// Use: /accounts/123?ctx=eyJ2aWV3IjoidHJhbnNhY3Rpb24iLCJmaWxlSWQiOiJmNDU2In0
```

## Implementation Benefits

### ✅ Scalability
- Handles unlimited navigation depth
- Graceful degradation for complex states
- Future-proof for new features

### ✅ User Experience
- Readable URLs for simple navigation
- Bookmarkable complex states
- Browser back/forward works correctly

### ✅ Performance
- No URL length issues
- Fast navigation state changes
- Efficient context management

### ✅ SEO Friendly
- Primary navigation in paths (good for SEO)
- Secondary context in queries (ignored by search engines)

## Migration Path

1. **Phase 1**: Implement `useSmartRouting` hook
2. **Phase 2**: Add URL depth monitoring
3. **Phase 3**: Implement context compression
4. **Phase 4**: Add URL shortening for extreme cases

## Usage Examples

### Simple Navigation
```typescript
// User clicks account → file → transaction
// URLs: /accounts → /accounts/123 → /accounts/123/files/456 → /accounts/123?view=transaction&fileId=456&transactionId=789
```

### Complex Filtering
```typescript
// User applies multiple filters and sorts
// URL: /accounts/123?view=transactions&filter=category:food,amount:>100&sort=date-desc&page=2&dateRange=2024-01
```

### Context Switching
```typescript
// User switches between different views of same account
// Base: /accounts/123
// Files view: /accounts/123?view=files
// Transactions view: /accounts/123?view=transactions&filter=recent
```

This strategy ensures URLs remain manageable regardless of session length or feature complexity.
