# Transfer Review Backend Call Pattern Analysis

## Current Implementation Analysis

### API Call Sequence on Page Load

When a user lands on the Transfers Dashboard, the following calls are made:

```
1. getTransferProgressAndRecommendation()  ← Single optimized call
   └─► GET /user-preferences (includes checked range + account range)
   
2. Promise.all([
     listPairedTransfers(dateRange),      ← GET /transfers/paired?startDate=X&endDate=Y
     getTotalPairedTransfersCount(),      ← GET /transfers/paired?count_only=true
     getAccounts()                        ← GET /accounts
   ])
```

**Total Initial Calls: 4 API requests**

## Current State Summary

- `detectPotentialTransfers(startDate,endDate)`: 1 GET only; no preference update, no progress reload on scan.
- `bulkMarkTransfers(...)`: No `scannedDateRange` parameter; marks pairs only.
- End-of-cycle handled by UI via `completeReviewCycle()`:
  - POST update to user preferences (checked range)
  - GET `getTransferProgressAndRecommendation()` to refresh progress/recommendation
  - GET `detectPotentialTransfers` to load next chunk automatically when available
- Ignore operations are local-only until all candidates are processed; then end-of-cycle behavior runs.
- Optimistic updates: no refetch of paired transfers after marking; local state updates are applied.

Call counts (now):
- Per scan: 1 API call (GET detect)
- Per cycle completion: 4 API calls (POST bulk mark) + (POST update prefs) + (GET progress/recommendation) + (GET detect next)

### Call Pattern During Review Cycle

#### Scenario 1: User Clicks "Scan for Transfers"

```
1. detectPotentialTransfers(startDate, endDate)
   └─► GET /transfers/detect?startDate=X&endDate=Y

// No preference update, no progress reload on scan
```

**Total: 1 API request per scan**

#### Scenario 2: User Confirms Transfers (Complete Review Cycle)

```
1. bulkMarkTransfers(selectedPairs)
   └─► POST /transfers/bulk-mark
       └─► Backend creates "Transfers" category if needed
       └─► Backend updates both transactions

2. If all candidates processed (confirmed or ignored):
   └─► updateTransferPreferences(checkedDateRange)
       └─► POST /user-preferences [only at end of cycle]

3. Refresh progress and recommendation
   └─► getTransferProgressAndRecommendation()
       └─► GET /user-preferences

4. loadNextChunk()
   └─► detectPotentialTransfers(nextRange)
       └─► GET /transfers/detect
```

**Total: 4 API requests when completing a review cycle**

#### Scenario 3: User Ignores Transfers (Frontend Only)

```
Ignore operations are handled locally:
setIgnoredTransfers() updates a local Set

When all candidates in the chunk are processed, end-of-cycle behavior runs:
  - POST /user-preferences (update checked range)
  - GET /user-preferences (progress/recommendation)
  - GET /transfers/detect (auto-load next chunk)
```

#### Scenario 4: User Marks as Reviewed & Next

```
1. updateTransferPreferences(updateData)
   └─► POST /user-preferences
   
2. loadTransferProgress()
   └─► getTransferProgressAndRecommendation()
       └─► GET /user-preferences
       
3. loadNextChunk() → [triggers Scenario 1]
```

**Total: 3 API requests (POST update prefs, GET progress, GET detect next)**

## Optimization Analysis

### ✅ Already Optimized

1. **Single Progress Call**
   - `getTransferProgressAndRecommendation()` combines progress + recommendation
   - Avoids duplicate calls for the same data
   - Smart implementation! 👍

2. **Batch Operations**
   - `bulkMarkTransfers()` processes multiple pairs in single request
   - Includes date range update in same call
   - Good server-side efficiency

3. **Count-Only Endpoint**
   - `getTotalPairedTransfersCount()` uses `?count_only=true`
   - Avoids fetching full data when only count is needed
   - Lightweight query

4. **Frontend-Only Ignore**
   - No backend calls for ignoring candidates
   - Session-only state management
   - Zero network overhead

### ⚠️ Potential Issues

#### Issue: Progress refresh after cycle completion could be computed locally

Current flow on cycle completion:
```
1) POST /user-preferences (update checked range)
2) GET  /user-preferences via getTransferProgressAndRecommendation() (refresh progress + recommendation)
3) GET  /transfers/detect (load next chunk)
```

Observation: Step (2) is acceptable, but could be avoided by computing progress and the next recommended range locally after we write preferences, reducing one GET per cycle.

## Recommended Optimizations

### Optimization 1: Move Checked Range Update to End of Review Cycle ⭐⭐⭐

**Current Code:**
```typescript
// TransferService.ts - detectPotentialTransfers()
const result = await validateApiResponse(...);

// This happens automatically after detection (TOO EARLY)
try {
  await retryPreferenceUpdate(startMs, endMs, ...);
} catch (error) {
  // Warning added to response
}
```

**Problem**: The checked range is updated after detection (beginning of review cycle), but it should update after the user completes reviewing the chunk (end of review cycle). A range is "checked" when the user has reviewed and processed all candidates, not when candidates are first detected.

**Recommended Change:**

```typescript
// Remove automatic preference update from detectPotentialTransfers()
export const detectPotentialTransfers = (startDate: number, endDate: number) => {
  const query = new URLSearchParams();
  query.append('startDate', startDate.toString());
  query.append('endDate', endDate.toString());

  const url = `/transfers/detect?${query.toString()}`;

  return withApiLogging(
    'TransferService',
    url,
    'GET',
    async () => {
      const result = await validateApiResponse(
        () => ApiClient.getJson<any>(url),
        (rawData) => DetectedTransfersResponseSchema.parse(rawData),
        'detected transfers data',
        'Failed to detect transfers.'
      );

      // REMOVED: Automatic preference update
      // The checked range should only update when review cycle completes
      
      return result;
    },
    { /* ... */ }
  );
};
```

**Update Review Cycle Logic:**

```typescript
// TransfersDashboard.tsx - Complete Review Cycle
const completeReviewCycle = async () => {
  // This is called when:
  // 1. All candidates confirmed/ignored, OR
  // 2. User clicks "Mark Reviewed & Next"
  
  // Update checked range at END of review cycle
  await updateTransferPreferences({
    checkedDateRangeStart: Math.min(
      existingCheckedStart,
      currentDateRange.startDate.getTime()
    ),
    checkedDateRangeEnd: Math.max(
      existingCheckedEnd,
      currentDateRange.endDate.getTime()
    )
  });
  
  // Move to next chunk
  await loadNextChunk();
};

// Modified confirm handler
const handleBulkMarkTransfers = async () => {
  // 1. Mark transfers
  const result = await bulkMarkTransfers(selectedPairs);  // NO date range passed
  
  // 2. Update UI
  // ... update local state ...
  
  // 3. If all processed, complete review cycle
  if (areAllTransfersProcessed()) {
    await completeReviewCycle();  // Updates checked range + advances
  }
};

// Modified ignore handler  
const handleBulkIgnoreTransfers = () => {
  // Update local state only
  setIgnoredTransfers(prev => {
    const newIgnored = new Set(prev);
    selectedPendingTransfers.forEach(key => newIgnored.add(key));
    return newIgnored;
  });
  
  // If all processed, complete review cycle
  if (areAllTransfersProcessed()) {
    completeReviewCycle();  // Updates checked range + advances
  }
};
```

**Benefit**: 
- Semantically correct: Range marked as "checked" only when actually reviewed
- Eliminates redundant update (was updating on detect, then again on mark)
- Single source of truth for when range is marked complete
- Saves 1 POST per scan (now only updates once at end)
- **Resumable workflow**: User can leave page mid-review and return - checked range accurately reflects what was actually completed

### Optimization 2: Proper Review Cycle with End-of-Cycle Updates ⭐⭐

**Current Code:**
```typescript
const handleBulkMarkTransfers = async () => {
  // Passes scannedDateRange to bulkMarkTransfers
  const result = await bulkMarkTransfers(selectedPairs, scannedDateRange);
  
  // Reload everything
  const [updatedTransfers, updatedTotalCount] = await Promise.all([
    listPairedTransfers({ startDate, endDate })(),
    getTotalPairedTransfersCount()()
  ]);
  
  setPairedTransfers(updatedTransfers.pairedTransfers);
  setTotalPairedTransfersCount(updatedTotalCount);
  
  // Separately update checked range
  await loadTransferProgress();
};
```

**Optimized Version:**

```typescript
// Unified review cycle completion
const completeReviewCycle = async () => {
  // Update checked range at END of review cycle
  await updateTransferPreferences({
    checkedDateRangeStart: Math.min(
      transferProgress?.checkedDateRange?.startDate || currentDateRange.startDate.getTime(),
      currentDateRange.startDate.getTime()
    ),
    checkedDateRangeEnd: Math.max(
      transferProgress?.checkedDateRange?.endDate || currentDateRange.endDate.getTime(),
      currentDateRange.endDate.getTime()
    )
  });
  
  // Update local progress state (no refetch needed)
  updateLocalProgressState(currentDateRange);
  
  // Load next chunk
  const nextRange = calculateNextRange();
  const nextChunk = await detectPotentialTransfers(nextRange.startDate, nextRange.endDate);
  
  setCurrentDateRange(nextRange);
  setDetectedTransfers(nextChunk.transfers);
};

const handleBulkMarkTransfers = async () => {
  // Don't pass scannedDateRange - checked range updates at END of cycle
  const result = await bulkMarkTransfers(selectedPairs);
  
  if (result.successCount > 0) {
    // Update local state optimistically
    setTotalPairedTransfersCount(prev => prev + result.successCount);
    
    // Remove from detected list
    const successfulIds = new Set(
      result.successful.flatMap(s => [s.outgoingTransactionId, s.incomingTransactionId])
    );
    setDetectedTransfers(prev =>
      prev.filter(pair => !successfulIds.has(pair.outgoingTransaction.transactionId))
    );
  }
  
  // Clear selection
  setSelectedPendingTransfers(new Set());
  
  // If all processed, complete review cycle
  if (areAllTransfersProcessed()) {
    await completeReviewCycle();
  }
};

const handleBulkIgnoreTransfers = () => {
  // Add to ignored set (local only)
  setIgnoredTransfers(prev => {
    const newIgnored = new Set(prev);
    selectedPendingTransfers.forEach(key => newIgnored.add(key));
    return newIgnored;
  });
  
  // Clear selection
  setSelectedPendingTransfers(new Set());
  
  // If all processed, complete review cycle
  if (areAllTransfersProcessed()) {
    completeReviewCycle();
  }
};
```

**Key Changes:**
1. Remove `scannedDateRange` parameter from `bulkMarkTransfers`
2. Checked range updates only at END of review cycle (when all candidates processed)
3. Single completion point for both confirm and ignore paths
4. Optimistic local updates (no reload)
5. Auto-advance built into cycle completion

**Benefit**: 
- Correct semantics: Checked range = fully reviewed
- Eliminates double update (was updating on detect + mark)
- Single source of truth for cycle completion
- Optimistic updates (faster UI)
- Saves 2-3 API calls per cycle

### Optimization 3: Local Progress Tracking ⭐

**Current Code:**
```typescript
const updateCheckedDateRange = async () => {
  await updateTransferPreferences(updateData);
  await loadTransferProgress();  // Refetch what we just set
};
```

**Optimized Version:**

```typescript
const updateCheckedDateRange = async () => {
  const updateData = { /* ... */ };
  
  await updateTransferPreferences(updateData);
  
  // Update local state instead of refetching
  setTransferProgress(prev => ({
    ...prev,
    checkedDateRange: {
      startDate: updateData.checkedDateRangeStart,
      endDate: updateData.checkedDateRangeEnd
    },
    checkedDays: calculateCheckedDays(updateData),
    progressPercentage: calculateProgress(updateData)
  }));
  
  // Update recommended range locally
  const newRecommendation = calculateRecommendedRange(
    { startDate: updateData.checkedDateRangeStart, endDate: updateData.checkedDateRangeEnd },
    transferProgress.accountDateRange
  );
  setRecommendedRange(newRecommendation);
  
  // No need to call loadTransferProgress()
};
```

**Benefit**: Saves 1 GET request per chunk completion

### Optimization 4: Batch Initial Load Data ⭐

**Current Code:**
```typescript
// Initial load - separate calls
const progressAndRecommendation = await getTransferProgressAndRecommendation();
const [transfersData, totalCount, accountsData] = await Promise.all([
  listPairedTransfers(rangeToUseForAPI)(),
  getTotalPairedTransfersCount()(),
  getAccounts()
]);
```

**Potential Backend Optimization:**

Create a single endpoint that returns all initial data:

```typescript
// New endpoint: GET /transfers/dashboard-init?startDate=X&endDate=Y
interface DashboardInitResponse {
  progress: TransferProgress;
  recommendedRange: DateRange | null;
  pairedTransfers: TransferPair[];
  totalCount: number;
  accounts: AccountInfo[];
}
```

**Frontend Usage:**

```typescript
const loadAllInitialData = async () => {
  const initData = await getDashboardInitialData(dateRange);
  
  setTransferProgress(initData.progress);
  setRecommendedRange(initData.recommendedRange);
  setPairedTransfers(initData.pairedTransfers);
  setTotalPairedTransfersCount(initData.totalCount);
  setAccounts(initData.accounts);
};
```

**Benefit**: Reduces initial load from 4 requests to 1, faster page load

## Compact UI Optimizations

For the proposed compact review UI, optimize the review cycle:

### Current Flow (Full Cycle)

```
1. Load page: 4 API calls
2. Scan chunk: 3 API calls
3. Confirm transfers: 4 API calls
4. Auto-advance (next chunk): 3 API calls

Total: 14 API calls per chunk
```

### Optimized Flow

```
1. Load page: 1 API call (dashboard-init - future optimization)
2. Scan chunk: 1 API call (detect only, no preference update)
3. Review & complete cycle: 2 API calls
   - bulkMarkTransfers (mark approved transfers)
   - updateTransferPreferences (mark range as checked)
   - detectPotentialTransfers (next chunk)

Total: 4 API calls per complete review cycle (71% reduction!)
```

### Implementation for Compact UI

```typescript
// Complete review cycle with proper order
const completeReviewCycleAndAdvance = async () => {
  // At this point, all candidates have been confirmed or ignored
  
  // 1. Update checked range (mark as reviewed)
  await updateTransferPreferences({
    checkedDateRangeStart: Math.min(
      transferProgress?.checkedDateRange?.startDate || currentDateRange.startDate.getTime(),
      currentDateRange.startDate.getTime()
    ),
    checkedDateRangeEnd: Math.max(
      transferProgress?.checkedDateRange?.endDate || currentDateRange.endDate.getTime(),
      currentDateRange.endDate.getTime()
    )
  });
  
  // 2. Update local progress state (no refetch)
  setTransferProgress(prev => ({
    ...prev,
    checkedDateRange: {
      startDate: Math.min(prev?.checkedDateRange?.startDate || currentDateRange.startDate.getTime(), currentDateRange.startDate.getTime()),
      endDate: Math.max(prev?.checkedDateRange?.endDate || currentDateRange.endDate.getTime(), currentDateRange.endDate.getTime())
    }
  }));
  
  // 3. Calculate next range
  const nextRange = calculateNextRange(currentDateRange, transferProgress);
  
  // 4. Detect next chunk
  const nextChunk = await detectPotentialTransfers(nextRange.startDate, nextRange.endDate);
  
  // 5. Update UI
  setCurrentDateRange(nextRange);
  setDetectedTransfers(nextChunk.transfers);
  setIgnoredTransfers(new Set());  // Clear ignored set for new chunk
  clearSelection();
};

// Optimized confirm handler
const confirmAndAdvance = async () => {
  if (selectedCount === 0) return;
  
  // 1. Mark selected as transfers (no date range parameter)
  const result = await bulkMarkTransfers(selectedPairs);
  
  // 2. Update local state optimistically
  if (result.successCount > 0) {
    setTotalPairedTransfersCount(prev => prev + result.successCount);
    
    // Remove from detected list
    const successfulIds = new Set(
      result.successful.flatMap(s => [s.outgoingTransactionId, s.incomingTransactionId])
    );
    setDetectedTransfers(prev =>
      prev.filter(pair => !successfulIds.has(pair.outgoingTransaction.transactionId))
    );
  }
  
  clearSelection();
  
  // 3. If all processed, complete review cycle and advance
  if (areAllTransfersProcessed()) {
    await completeReviewCycleAndAdvance();
  }
};

// Optimized ignore handler
const ignoreAndAdvance = () => {
  if (selectedCount === 0) return;
  
  // 1. Add to ignored set (local only)
  setIgnoredTransfers(prev => {
    const newIgnored = new Set(prev);
    selectedPendingTransfers.forEach(key => newIgnored.add(key));
    return newIgnored;
  });
  
  clearSelection();
  
  // 2. If all processed, complete review cycle and advance
  if (areAllTransfersProcessed()) {
    completeReviewCycleAndAdvance();
  }
};
```

**Key Points:**
- Review cycle ends only when all candidates are processed (confirmed or ignored)
- Checked range updated at END of cycle, not beginning
- Single call to update checked range per cycle
- Single call to detect next chunk per cycle
- No reload of paired transfers (will show in next chunk if needed)
- Total: 2-3 API calls per complete review cycle

## Summary

### Current State: 🟡 Good but Not Optimal

**Strengths:**
- Combined progress/recommendation call
- Bulk operations
- Count-only endpoint
- Frontend-only ignore

**Weaknesses:**
- Redundant preference updates (detect → mark)
- Unnecessary reloads after confirm
- Fetching data we just set
- 4 separate calls on page load

### Recommended Priority

| Optimization | Impact | Effort | Priority | Savings |
|--------------|--------|--------|----------|---------|
| Move checked range to end of cycle | High | Low | ⭐⭐⭐ | 1 POST per scan |
| Proper review cycle completion | High | Medium | ⭐⭐⭐ | Correct semantics |
| Optimistic UI updates | Medium | Low | ⭐⭐ | 2-3 GET per cycle |
| Local progress tracking | Low | Low | ⭐ | 1 GET per cycle |
| Batch init endpoint | Medium | High | Future | 3 requests on load |

### Expected Improvement

**Before**: 14 API calls per complete review cycle
**After**: 4 API calls per complete review cycle (71% reduction)

**Per Review Cycle Breakdown:**

| Phase | Before | After | Notes |
|-------|--------|-------|-------|
| Scan | 3 calls | 1 call | Remove auto-update from detect |
| Confirm transfers | 1 call | 1 call | bulkMarkTransfers (no date range) |
| Complete cycle | 4 calls | 1 call | updatePreferences (checked range) |
| Load next | 3 calls | 1 call | detectPotentialTransfers |
| Reload UI | 3 calls | 0 calls | Optimistic updates |
| **Total** | **14 calls** | **4 calls** | **71% reduction** |

**For 10 Complete Review Cycles**:
- Before: 140 API calls
- After: 40 API calls
- **Savings: 100 API calls (71% reduction)**

**Additional Benefits**:
- ✅ **Correct semantics**: Checked range updated at END of review cycle
- ✅ **Single source of truth**: One place where cycle completes
- ✅ **Approved transfers + checked range**: Both updated together
- ✅ **No race conditions**: Sequential updates, clear order
- ✅ **Faster UI response**: Optimistic updates
- ✅ **Reduced server load**: Fewer redundant calls
- ✅ **Better UX**: Less waiting, smoother flow
- ✅ **Resumability**: User can leave and return - range only marked "checked" when fully reviewed

## Implementation Roadmap

### Phase 1: Critical - Review Cycle Semantics (Low Effort, High Impact)
1. ✅ Remove auto-update from `detectPotentialTransfers()` - Checked range should update at END of cycle, not beginning
2. ✅ Remove `scannedDateRange` from `bulkMarkTransfers()` - Backend shouldn't update checked range
3. ✅ Create `completeReviewCycle()` function - Single place where cycle ends and range is marked checked
4. ✅ Update both confirm and ignore handlers to call `completeReviewCycle()` when all processed

**Why Critical**: Currently, the checked range is updated at the WRONG time (when candidates are detected, not when reviewed). This is semantically incorrect and breaks resumability - if a user leaves mid-review, the range is marked "checked" even though they haven't finished reviewing it.

### Phase 2: Optimization - Reduce API Calls (Low Effort, Medium Impact)
5. ✅ Add optimistic updates after bulk mark - Update local state, skip reload
6. ✅ Local progress calculation - Calculate locally after update
7. ✅ Skip reload if auto-advancing - Will get fresh data in next chunk anyway

### Phase 3: Backend Optimization (Future)
8. ⏳ Dashboard init endpoint - Batch initial data load (requires backend changes)
9. 🔮 WebSocket for real-time progress - Long term enhancement

**All Phase 1 and 2 improvements can be done purely in frontend without backend changes!**

The key insight: **A review cycle should end with updating both approved transfer pairs AND checked range together**, not update checked range when candidates are first detected.

## Resumability: A Critical Feature

### The Problem with Current Implementation

**Current Behavior (BAD)**:
```
User starts reviewing Jan 1-31:
1. detectPotentialTransfers(Jan 1-31)
   └─► Immediately marks Jan 1-31 as "checked" ❌
2. User reviews 5 of 10 candidates
3. User leaves page (phone call, emergency, etc.)
4. User returns later
5. System shows: "Jan 1-31 already checked" ✓
6. System recommends: "Next chunk: Feb 1-28"
7. Result: 5 candidates NEVER REVIEWED! 💥
```

**The 5 un-reviewed candidates are lost in limbo:**
- Not marked as transfers (user didn't confirm them)
- Not marked as ignored (user didn't see them)
- Range marked as "checked" (but wasn't fully reviewed)
- Won't appear in future scans (range already checked)
- Only discoverable by manually browsing transactions

### The Solution: End-of-Cycle Updates

**Correct Behavior (GOOD)**:
```
User starts reviewing Jan 1-31:
1. detectPotentialTransfers(Jan 1-31)
   └─► Shows candidates, does NOT update checked range ✓
2. User confirms 5 of 10 candidates (saved to DB)
3. User leaves page (phone call, emergency, etc.)
4. User returns later
5. System recommends: Jan 1-31 (same range, since not complete)
6. User clicks "Scan Next Chunk" (same as any scan)
7. detectPotentialTransfers(Jan 1-31) runs (just a normal scan)
8. Shows 5 remaining candidates (the 5 confirmed are filtered out)
9. User processes remaining 5
10. completeReviewCycle() → Marks Jan 1-31 as "checked" ✓
11. Result: ALL candidates reviewed! ✅
```

### Resume Scenarios

#### Scenario 1: User Leaves During Review

**Timeline:**
```
10:00 AM - Scan Jan 1-31 (10 candidates found)
10:05 AM - Confirm 3 candidates
10:07 AM - Phone rings, user navigates away
         [checked range NOT updated - still empty]
         
3:00 PM  - User returns to transfers page
         - System loads: checkedRange = previous range (not including Jan 1-31)
         - Recommends: Jan 1-31 (since not marked complete)
         - User clicks "Scan Next Chunk" (normal button, no special UI)
         - Scan runs: 10 candidates found
         - 3 already categorized as transfers (filtered out by backend)
         - Shows: 7 remaining candidates
         - User processes remaining 7
         - All processed → checkedRange updated to include Jan 1-31
```

**Key Point**: The 3 confirmed transfers are persisted, but the range isn't marked "checked" until ALL candidates are reviewed.

#### Scenario 2: User Leaves Between Chunks

**Timeline:**
```
10:00 AM - Complete review of Jan 1-31
         - All candidates processed
         - Checked range updated: Jan 1-31 ✓
         - Next chunk (Feb 1-28) starts loading
         
10:01 AM - User closes tab before Feb chunk loads
         [Feb NOT marked as checked]
         
Later    - User returns
         - Checked range: Jan 1-31
         - Recommends: Feb 1-28 (picks up where left off)
         - User can continue seamlessly ✅
```

#### Scenario 3: User Ignores Some, Leaves, Returns

**Timeline:**
```
10:00 AM - Scan Jan 1-31 (8 candidates)
10:05 AM - Confirm 2, Ignore 3 (5 processed, 3 remaining)
10:06 AM - User leaves
         [checked range NOT updated]
         
Later    - User returns
         - Recommends: Jan 1-31 (not complete)
         - User scans Jan 1-31 (normal scan, nothing special)
         - 2 already confirmed (filtered out - have transfer category)
         - 6 remaining candidates shown (ignored state is session-only, so they reappear)
         - User processes all 6
         - All processed → Jan 1-31 marked complete
```

**Note**: Ignored state is session-only, so re-scanning will show previously ignored candidates again. This is acceptable - user can ignore them again or take a different action. The key point: **scanning the same range multiple times is normal and expected**, not a special "resume" mode.

### Comparison Table

| Aspect | Current (Wrong) | Optimized (Correct) |
|--------|----------------|-------------------|
| **When checked range updates** | After detect | After complete review |
| **User leaves mid-review** | Range marked checked ❌ | Range NOT marked checked ✓ |
| **Unreviewed candidates** | Lost in limbo | Shown again on return |
| **Resume behavior** | Skips to next range | Resumes same range |
| **Data integrity** | Broken | Maintained |
| **User trust** | Low (data loss) | High (reliable) |

### Implementation Details for Resumability

```typescript
// On page load - nothing special about resume
const loadAllInitialData = async () => {
  // 1. Get progress and recommended range
  const { progress, recommendedRange } = await getTransferProgressAndRecommendation();
  
  // 2. Set the recommended range (might be same as before if incomplete)
  if (recommendedRange) {
    setCurrentDateRange({
      startDate: new Date(recommendedRange.startDate),
      endDate: new Date(recommendedRange.endDate)
    });
  }
  
  // 3. That's it! User clicks "Scan Next Chunk" - works identically
  //    whether it's a new range or resuming an incomplete range
};

// Detection doesn't update checked range - just shows candidates
const handleDetectTransfers = async () => {
  const detected = await detectPotentialTransfers(
    currentDateRange.startDate.getTime(),
    currentDateRange.endDate.getTime()
  );
  
  // Show candidates (already confirmed ones are filtered out by backend)
  setDetectedTransfers(detected.transfers);
  
  // User can leave anytime - range only marked "checked" when cycle completes
  // Re-scanning the same range is normal, not special
};

// Only when ALL candidates processed
const completeReviewCycle = async () => {
  // NOW we mark as checked (user actually reviewed everything)
  await updateTransferPreferences({
    checkedDateRangeStart: Math.min(existing, current.start),
    checkedDateRangeEnd: Math.max(existing, current.end)
  });
  
  // Safe to move to next chunk
  await loadNextChunk();
};
```

### Why This Matters

**User Experience:**
- ✅ Users can work at their own pace
- ✅ Interruptions don't cause data loss
- ✅ No special "resume" UI needed - just scan again
- ✅ Scanning same range multiple times is normal and idempotent
- ✅ Clear progress tracking (what's actually done)
- ✅ Confidence in the system

**Data Integrity:**
- ✅ Checked range accurately reflects reviewed data
- ✅ No "lost" candidates in limbo
- ✅ Predictable, reliable behavior
- ✅ Audit trail is accurate

**Business Value:**
- ✅ Higher completion rates (users can resume)
- ✅ Better data quality (nothing skipped)
- ✅ Increased trust (system is reliable)
- ✅ Reduced support burden (fewer "where did my data go" questions)

This is not just an optimization - it's a **critical correctness fix** that ensures the system works reliably in real-world usage where interruptions are common.

### Key Insight: Idempotent Scanning

**The beauty of this design**: Scanning is idempotent. User can:
- Scan Jan 1-31 today, process some candidates
- Scan Jan 1-31 tomorrow, process remaining candidates
- Scan Jan 1-31 next week (if still not complete)
- No special UI, no "resume" button, no state management
- Just: "Scan Next Chunk" → shows whatever's left
- When all processed → range marked complete → next chunk recommended

**No distinction between**:
- "First scan of a new range"
- "Resuming an incomplete range"
- "Re-scanning to find more candidates"

They're all just: **scan a date range, show unprocessed candidates**.

