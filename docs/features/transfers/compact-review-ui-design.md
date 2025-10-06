# Compact Transfer Review UI Design

## Executive Summary

This document proposes a streamlined UI for transfer detection review that minimizes button presses and focuses on the core review cycle: **Scan → Review → Approve/Ignore → Next Chunk**. The goal is to create a flow where users can process transfer chunks with maximum efficiency and minimal friction.

### Four Primary Actions

The compact UI provides four buttons that handle all review scenarios:

1. **✓ Confirm & Next** (`Enter`)
   - Marks selected candidates as confirmed transfers
   - Auto-advances to next chunk
   - Primary action for true positives

2. **✗ Ignore** (`Backspace`)  
   - Ignores selected candidates (leaves uncategorized)
   - Removes from pending list
   - For false positives

3. **🔍 Manual Review** (`M`)
   - Opens transactions page with current date range filtered
   - Allows manual categorization of ambiguous cases
   - Date range NOT marked as reviewed (user can return)

4. **Mark Reviewed & Next** (`→`)
   - Updates checked date range to include current period
   - Advances to next chunk without processing candidates
   - For chunks with no candidates or all already ignored
   - **Note**: Since checked range is continuous (start/end only), this moves progress forward permanently

This approach respects the constraint that checked ranges cannot have gaps - they're stored as continuous start/end dates only.

### Action Flow Decision Tree

```
Chunk Loaded with Candidates
         │
         ├─► High Confidence Matches Pre-selected
         │
         ▼
    Review Candidates
         │
         ├─── All look correct? ──► Press ENTER (Confirm & Next)
         │                              │
         │                              ▼
         │                         Next Chunk Loads
         │
         ├─── Some false positives? ──► Deselect wrong ones
         │                              │
         │                              ├─► Press ENTER (Confirm rest)
         │                              │   
         │                              └─► Select wrong ones + Press BACKSPACE (Ignore)
         │                                  │
         │                                  ▼
         │                             Next Chunk Loads
         │
         ├─── Uncertain/Ambiguous? ──► Press M (Manual Review)
         │                              │
         │                              ▼
         │                         Transactions Page Opens
         │                         (User manually categorizes)
         │                         Return to continue
         │
         └─── No candidates or all ignored? ──► Press → (Mark Reviewed & Next)
                                                 │
                                                 ▼
                                            Next Chunk Loads
```

## Current UX Analysis

### Current Flow Issues

1. **Too Many Steps**: Users must navigate multiple UI sections and press multiple buttons
   - Click "Scan for Transfers" button
   - Scroll to results section
   - Select candidates using checkboxes
   - Click either "Confirm as Transfers" or "Ignore Candidates"
   - Return to scan controls
   - Repeat

2. **Scattered Interface**: Key actions are spread across three different panels:
   - Scan controls at top
   - Progress tracking in middle
   - Results/actions at bottom

3. **Excessive Visual Noise**: 
   - Large header with gradient background
   - Multiple stat cards
   - Timeline visualization
   - Strategy options
   - Advanced settings

4. **Delayed Feedback**: Success messages appear but users must manually initiate next scan

## Proposed Compact Design

### Core Principle: Single-Screen Review Flow

All essential actions should be visible and accessible within a single viewport without scrolling.

### Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  Transfer Review (Chunk X of Y) [Progress Bar: 45%]    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Current Range: Jan 1-31, 2024  [Next Chunk ▶]        │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │ ✓  Checking → Savings   Jan 15  $500   0 days │    │
│  │ ✓  Credit → Checking    Jan 20  $1,200 2 days │    │
│  │ ☐  Savings → Investment Jan 18  $300   1 day  │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  [Confirm Selected (2)] [Ignore Selected] [Skip All ▶] │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Key Features

#### 1. **Unified Action Bar**
- All primary actions in one row at the bottom
- Keyboard shortcuts for power users
- Actions auto-advance to next chunk

#### 2. **Inline Selection with Auto-select**
- Pre-select high-confidence matches (>90% confidence)
- Users deselect false positives instead of selecting true positives
- Click row to toggle (not just checkbox)

#### 3. **Auto-advance to Next Chunk**
- When all candidates are processed (confirmed or ignored), automatically load next chunk
- No button press required
- Optional 2-second countdown with cancel option

#### 4. **Compact Table View**
- Single-line rows with essential info only
- Expandable details on hover/click
- Remove redundant columns
- Color coding for quick visual scanning

#### 5. **Minimal Progress Tracking**
- Single progress bar with percentage
- "Chunk X of Y" indicator
- Hide detailed timeline/stats (available in collapsed section)

## Detailed Design Specifications

### Top Bar (Always Visible)

```tsx
<div className="transfer-review-header-compact">
  <div className="review-progress">
    <span className="chunk-indicator">Chunk 5 of 12</span>
    <div className="progress-bar-mini">
      <div className="progress-fill" style={{ width: '42%' }}></div>
    </div>
    <span className="progress-text">42% complete</span>
  </div>
  <button className="settings-icon" onClick={toggleAdvanced}>⚙️</button>
</div>
```

**Features**:
- Minimal height (40px)
- Shows current position in overall review process
- Settings icon for advanced options (collapsed by default)

### Range Navigation (Compact)

```tsx
<div className="range-navigation-compact">
  <div className="current-range">
    <span className="range-label">Scanning:</span>
    <span className="range-dates">Jan 1-31, 2024</span>
    <span className="range-stats">(30 days, 245 transactions)</span>
  </div>
  <button 
    className="next-chunk-button-mini"
    disabled={hasUnprocessedCandidates}
    onClick={loadNextChunk}
  >
    Next Chunk ▶
  </button>
</div>
```

**Features**:
- Single line showing current scope
- "Next Chunk" button disabled until current chunk is processed
- Visual indication of what's being scanned

### Compact Results Table

```tsx
<table className="transfer-review-table-compact">
  <thead>
    <tr>
      <th className="col-select">
        <input type="checkbox" onChange={toggleAll} checked={allSelected} />
      </th>
      <th className="col-flow">Flow</th>
      <th className="col-amount">Amount</th>
      <th className="col-date">Date</th>
      <th className="col-confidence">✓</th>
    </tr>
  </thead>
  <tbody>
    {candidates.map(pair => (
      <tr 
        key={pair.id}
        className={`candidate-row ${isSelected(pair) ? 'selected' : ''} ${getConfidenceClass(pair)}`}
        onClick={() => toggleSelection(pair)}
      >
        <td className="col-select">
          <input 
            type="checkbox" 
            checked={isSelected(pair)}
            onChange={() => toggleSelection(pair)}
          />
        </td>
        <td className="col-flow">
          <div className="flow-display">
            <span className="account-from">{pair.from}</span>
            <span className="flow-arrow">→</span>
            <span className="account-to">{pair.to}</span>
          </div>
        </td>
        <td className="col-amount">
          <span className="amount-value">${formatAmount(pair.amount)}</span>
        </td>
        <td className="col-date">
          <span className="date-value">{formatDate(pair.date)}</span>
          {pair.daysDiff > 0 && (
            <span className="days-diff">+{pair.daysDiff}d</span>
          )}
        </td>
        <td className="col-confidence">
          <span className={`confidence-indicator ${getConfidenceLevel(pair)}`}>
            {getConfidenceIcon(pair)}
          </span>
        </td>
      </tr>
    ))}
  </tbody>
</table>
```

**Features**:
- Condensed columns (5 instead of 8)
- "Flow" column combines source/target accounts in single cell
- Confidence shown as colored icon instead of percentage bar
- Entire row is clickable for selection
- High-confidence rows pre-selected and highlighted

**Column Reductions**:
- OLD: Source Account | Source Date | Source Amount | Target Account | Target Date | Target Amount | Days Apart | Confidence
- NEW: ☐ | Flow (From → To) | Amount | Date (+Δ) | ✓

### Action Bar (Fixed at Bottom)

```tsx
<div className="action-bar-compact">
  <div className="selection-summary">
    <span className="selected-count">{selectedCount} selected</span>
    <span className="total-count">of {totalCount}</span>
  </div>
  
  <div className="primary-actions">
    <button 
      className="btn-confirm-primary"
      onClick={confirmAndAdvance}
      disabled={selectedCount === 0}
      hotkey="Enter"
    >
      ✓ Confirm {selectedCount > 0 ? `(${selectedCount})` : ''} & Next
    </button>
    
    <button 
      className="btn-ignore"
      onClick={ignoreAndAdvance}
      disabled={selectedCount === 0}
      hotkey="Backspace"
    >
      ✗ Ignore {selectedCount > 0 ? `(${selectedCount})` : ''}
    </button>
    
    <button 
      className="btn-manual-review"
      onClick={openTransactionsPageWithRange}
      hotkey="m"
      title="Open transactions page to manually review this date range"
    >
      🔍 Manual Review
    </button>
    
    <button 
      className="btn-skip-advance"
      onClick={markAsReviewedAndAdvance}
      disabled={hasUnprocessedCandidates}
      hotkey="→"
      title="Mark range as reviewed and move to next chunk (candidates remain unprocessed)"
    >
      Mark Reviewed & Next ▶
    </button>
  </div>
  
  <div className="keyboard-hints">
    <span className="hint">Enter: Confirm | Backspace: Ignore | M: Manual | →: Next</span>
  </div>
</div>
```

**Features**:
- Fixed position at bottom of viewport (always visible)
- Three primary actions: Confirm, Ignore, Skip
- All actions auto-advance to next chunk
- Keyboard shortcuts prominently displayed
- Selection count visible at all times

### Button Behavior Details

#### 1. Manual Review Button

Opens the transactions page with the current date range pre-filtered, allowing users to manually categorize transactions:

```tsx
const openTransactionsPageWithRange = () => {
  const startDate = currentDateRange.startDate.getTime();
  const endDate = currentDateRange.endDate.getTime();
  
  // Navigate to transactions page with date range filter
  navigate(`/transactions?startDate=${startDate}&endDate=${endDate}`);
  
  // Optional: Store return context to allow user to come back
  sessionStorage.setItem('transferReviewReturnContext', JSON.stringify({
    currentRange: currentDateRange,
    progress: transferProgress
  }));
};
```

**Use Case**: When candidates are ambiguous or user wants more control over manual categorization.

**Behavior**:
- Opens transactions page in same tab with date filter applied
- User manually categorizes any transfers they identify
- User can return to transfer review page to continue
- Date range remains unmarked (not added to checked range)

#### 2. Mark Reviewed & Next Button

Marks the current date range as reviewed and advances to next chunk, even if candidates remain unprocessed:

```tsx
const markAsReviewedAndAdvance = async () => {
  // Update checked date range to include current range
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
  
  // Refresh progress and load next chunk
  await loadTransferProgress();
  await loadNextChunk();
};
```

**Use Case**: When no candidates found, or user has ignored all candidates and wants to move on.

**Behavior**:
- Updates checked date range in user preferences (extends start/end)
- Does NOT process or mark any pending candidates
- Candidates remain in "uncategorized" state (can be found in transactions page)
- Auto-advances to next recommended chunk
- Disabled when unprocessed candidates exist (must confirm or ignore first)

**Important**: Since checked range is continuous (only start/end dates), users cannot "skip" chunks and come back. The range is marked as reviewed and progress moves forward.

#### What Happens to Ignored Candidates?

When users click "Ignore" on candidates:

```tsx
const handleIgnore = async () => {
  // Remove from detected transfers list (frontend only)
  // Transactions remain uncategorized in database
  // They can be found and categorized via:
  // 1. Transactions page (filtered by uncategorized)
  // 2. Manual search in transactions page
  // 3. Future detection runs may re-detect them
  
  setIgnoredTransfers(prev => {
    const newIgnored = new Set(prev);
    selectedPendingTransfers.forEach(key => newIgnored.add(key));
    return newIgnored;
  });
  
  // Clear selection and check if chunk is complete
  clearSelection();
  
  // If all candidates processed, auto-advance
  if (areAllTransfersProcessed()) {
    updateCheckedDateRange();
    loadNextChunk();
  }
};
```

**Key Points**:
- Ignored ≠ Deleted
- Ignored candidates remain as regular uncategorized transactions
- Users can manually categorize them later via transactions page
- Ignored state is session-only (not persisted to database)
- When date range is marked as reviewed, candidates are simply left uncategorized

### Auto-advance Behavior

After confirming or ignoring transfers:

```tsx
// Pseudo-code for auto-advance logic
const processSelectionAndAdvance = async (action: 'confirm' | 'ignore') => {
  // 1. Process current selection
  await processTransfers(selectedCandidates, action);
  
  // 2. Remove processed items from view
  const remainingCandidates = candidates.filter(c => !isSelected(c));
  
  // 3. Check if chunk is complete
  if (remainingCandidates.length === 0) {
    // All candidates in chunk processed
    
    // Show brief success toast
    showToast(`${action === 'confirm' ? 'Confirmed' : 'Ignored'} ${selectedCount} transfers`, {
      duration: 1500,
      type: 'success'
    });
    
    // Auto-advance after brief delay
    setTimeout(() => {
      loadNextChunk();
    }, 500);
  } else {
    // More candidates remain in current chunk
    setCandidates(remainingCandidates);
    clearSelection();
  }
};
```

### Smart Pre-selection Logic

```tsx
// Automatically pre-select high-confidence matches
const autoSelectHighConfidence = (candidates: TransferPair[]) => {
  const highConfidence = candidates.filter(pair => {
    const confidence = calculateConfidence(pair);
    return (
      confidence >= 90 &&                    // High confidence score
      pair.dateDifference <= 1 &&            // Same day or next day
      pair.amountMatch === 'exact' &&        // Exact amount match
      !hasConflictingPatterns(pair)          // No red flags
    );
  });
  
  return new Set(highConfidence.map(p => p.id));
};

// On chunk load
useEffect(() => {
  const candidates = detectedTransfers;
  const preSelected = autoSelectHighConfidence(candidates);
  setSelectedTransfers(preSelected);
}, [detectedTransfers]);
```

**Benefits**:
- Users review pre-selections instead of making selections
- Most common action becomes "deselect false positives and confirm"
- Reduces clicks from 3-4 per transfer to 1-2 per false positive
- For accurate detection, most transfers require zero clicks

### Keyboard Navigation

```tsx
const KeyboardShortcuts = {
  'Enter': confirmSelectedAndAdvance,
  'Backspace': ignoreSelectedAndAdvance,
  'm': openTransactionsPageWithRange,
  'ArrowRight': markAsReviewedAndAdvance,
  'ArrowDown': selectNextRow,
  'ArrowUp': selectPreviousRow,
  'Space': toggleCurrentRow,
  'a': selectAllVisibleRows,
  'Escape': clearSelection,
  'n': loadNextChunk,
  'p': loadPreviousChunk
};

// Enable keyboard navigation
useKeyboardShortcuts(KeyboardShortcuts, {
  enabled: !isModalOpen && !isInputFocused
});
```

### Visual Density Options

Provide three density modes (user preference):

1. **Comfortable** (default): 48px row height, standard padding
2. **Compact**: 36px row height, reduced padding
3. **Dense**: 28px row height, minimal padding

```tsx
<select 
  value={densityMode} 
  onChange={(e) => setDensityMode(e.target.value)}
  className="density-selector"
>
  <option value="comfortable">Comfortable</option>
  <option value="compact">Compact</option>
  <option value="dense">Dense</option>
</select>
```

## Interaction Flows

### Flow 1: Review and Approve All (Happy Path)

1. User lands on transfers page
2. System auto-loads first chunk with recommended range
3. High-confidence matches are pre-selected
4. User reviews pre-selections (2 seconds scan)
5. User presses **Enter** (or clicks "Confirm & Next")
6. Brief success message (1.5s)
7. Next chunk auto-loads (0.5s delay)
8. **Total time: ~4 seconds per chunk**
9. **Button presses: 1 per chunk**

### Flow 2: Mixed Approval (Some False Positives)

1. Chunk loads with 5 candidates, 4 pre-selected
2. User spots 1 false positive in pre-selected items
3. User clicks row to deselect false positive (1 click)
4. User presses **Enter** to confirm remaining 3
5. User selects the 1 remaining candidate (which was not pre-selected)
6. User presses **Backspace** to ignore it
7. Next chunk auto-loads
8. **Total time: ~6 seconds**
9. **Button presses: 3 (deselect, confirm, ignore)**

### Flow 3: Manual Review for Uncertain Chunk

1. Chunk loads with ambiguous candidates
2. User doesn't feel confident about automated detection
3. User presses **M** (or clicks "Manual Review")
4. Transactions page opens with current date range pre-filtered
5. User can manually categorize transactions as transfers if needed
6. User returns to transfer review to continue
7. **Total time: varies (user handles manually)**
8. **Button presses: 1 to open manual review**

### Flow 4: Mark as Reviewed and Continue

1. Chunk loads with no candidates (or all ignored)
2. User wants to mark range as checked and move on
3. User presses **→** (or clicks "Mark Reviewed & Next")
4. Checked date range updated to include current range
5. Next chunk auto-loads
6. **Total time: 2 seconds**
7. **Button presses: 1**

### Flow 5: Power User Keyboard-Only

1. User navigates with arrow keys
2. User toggles selections with spacebar
3. User confirms with Enter
4. **No mouse required**
5. **Processing rate: 10-15 chunks per minute**

## Implementation Priority

### Phase 1: Core Compact UI (High Priority)
- [ ] Compact header with mini progress bar
- [ ] Single-line range navigation
- [ ] Condensed 5-column table
- [ ] Fixed action bar with 3 primary buttons
- [ ] Auto-advance after confirmation/ignore

### Phase 2: Smart Selection (High Priority)
- [ ] Auto-select high-confidence matches
- [ ] Pre-select algorithm based on confidence + date + amount
- [ ] Clickable rows for quick toggle
- [ ] "Select All" / "Deselect All" in table header

### Phase 3: Keyboard Navigation (Medium Priority)
- [ ] Enter/Backspace/Arrow shortcuts
- [ ] Visual keyboard hint bar
- [ ] Arrow key row navigation
- [ ] Spacebar to toggle selection

### Phase 4: Advanced Features (Low Priority)
- [ ] Density mode selector
- [ ] Collapsible advanced settings
- [ ] Manual review integration with transactions page
- [ ] Batch size customization
- [ ] Undo last action

### Phase 5: Backend Call Optimization (Medium Priority)
- [ ] Remove auto-update from `detectPotentialTransfers()`
- [ ] Implement optimistic UI updates after confirm
- [ ] Add local progress calculation (skip refetch)
- [ ] Smart reload logic (skip if auto-advancing)
- [ ] Consider dashboard init endpoint (future)

## Visual Design Guidelines

### Color Coding for Quick Scanning

```css
/* Confidence-based row highlighting */
.candidate-row.confidence-high {
  background: #ecfdf5; /* Light green */
  border-left: 3px solid #10b981;
}

.candidate-row.confidence-medium {
  background: #fef3c7; /* Light yellow */
  border-left: 3px solid #f59e0b;
}

.candidate-row.confidence-low {
  background: #fee2e2; /* Light red */
  border-left: 3px solid #ef4444;
}

/* Selected state */
.candidate-row.selected {
  background: #dbeafe !important; /* Light blue */
  border-left-color: #3b82f6;
  box-shadow: inset 0 0 0 2px #3b82f6;
}
```

### Compact Spacing

```css
.transfer-review-table-compact {
  font-size: 14px;
  line-height: 1.4;
}

.transfer-review-table-compact th,
.transfer-review-table-compact td {
  padding: 8px 12px; /* Reduced from 12px 16px */
}

.candidate-row {
  height: 48px; /* Comfortable mode */
  cursor: pointer;
  transition: background-color 0.15s;
}

.candidate-row:hover {
  background-color: #f9fafb;
}
```

### Fixed Action Bar

```css
.action-bar-compact {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  border-top: 2px solid #e5e7eb;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
}

.btn-confirm-primary {
  background: #10b981;
  color: white;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-confirm-primary:hover:not(:disabled) {
  background: #059669;
}

.btn-confirm-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
```

## Mobile Responsiveness

For mobile devices, further simplify:

```
┌───────────────────────────┐
│ Chunk 5/12  [42% ████▒▒▒] │
├───────────────────────────┤
│ ☑ Checking → Savings      │
│   $500   Jan 15   0d  ✓✓  │
├───────────────────────────┤
│ ☑ Credit → Checking       │
│   $1,200 Jan 20   2d  ✓   │
├───────────────────────────┤
│ ☐ Savings → Investment    │
│   $300   Jan 18   1d  ✓✓  │
├───────────────────────────┤
│ [✓ Confirm 2] [✗ Ignore]  │
│ [🔍 Manual] [Mark Done ▶] │
└───────────────────────────┘
```

**Mobile Changes**:
- Stack table into cards (one per row)
- Two-line layout per candidate
- Larger touch targets (48px minimum)
- Swipe gestures: right=confirm, left=ignore
- Action bar split into two rows (primary actions on top, secondary below)
- Manual Review and Mark Done buttons in second row

## Success Metrics

Track these metrics to measure improvement:

1. **Time per Chunk**: Target < 5 seconds average
2. **Clicks per Chunk**: Target < 2 clicks average
3. **Keyboard Usage Rate**: Target > 30% of power users
4. **Auto-advance Adoption**: Target > 90% don't disable
5. **Chunks per Session**: Increase by 2-3x
6. **User Satisfaction**: Survey score > 4.5/5

## Accessibility Considerations

1. **Screen Readers**: 
   - Proper ARIA labels on all interactive elements
   - Announce confidence scores and pre-selections
   - Keyboard navigation announcements

2. **Keyboard Navigation**:
   - All actions accessible without mouse
   - Visual focus indicators
   - Skip links for lengthy tables

3. **Color Blindness**:
   - Don't rely solely on color for confidence
   - Use icons and patterns in addition to colors
   - High contrast mode support

4. **Reduced Motion**:
   - Respect `prefers-reduced-motion`
   - Disable auto-advance animations
   - Instant transitions instead of smooth

## Migration Path

### Current → Compact Transition

1. **Add Feature Flag**: `enableCompactReviewMode`
2. **Parallel Implementation**: Build compact mode alongside existing
3. **A/B Testing**: 50/50 split for 2 weeks
4. **Gather Feedback**: User surveys and analytics
5. **Iterate**: Refine based on feedback
6. **Full Rollout**: Enable for all users
7. **Deprecate Old UI**: After 1 month grace period

### Backwards Compatibility

Maintain current UI as "Classic Mode" accessible via settings for users who prefer it:

```tsx
<div className="view-mode-toggle">
  <label>
    <input 
      type="radio" 
      value="compact" 
      checked={viewMode === 'compact'}
      onChange={() => setViewMode('compact')}
    />
    Compact Review
  </label>
  <label>
    <input 
      type="radio" 
      value="classic" 
      checked={viewMode === 'classic'}
      onChange={() => setViewMode('classic')}
    />
    Classic View
  </label>
</div>
```

## Conclusion

This compact review UI design focuses on eliminating friction in the transfer review workflow. By combining smart pre-selection, auto-advance behavior, keyboard shortcuts, and a streamlined layout, we can reduce the average time and effort per chunk by 50-70% while maintaining (or improving) review accuracy.

**Key Innovations**:
1. Pre-select high-confidence matches (users deselect instead of select)
2. Auto-advance to next chunk after processing
3. All actions in fixed bottom bar (no scrolling)
4. Single-screen layout (no context switching)
5. Keyboard-first navigation with visible shortcuts
6. Manual review integration for ambiguous cases
7. Smart handling of continuous date range tracking

**Four-Button Action Model**:
- **Confirm & Next**: Process true positives and advance
- **Ignore**: Skip false positives (remain uncategorized)
- **Manual Review**: Open transactions page for manual categorization
- **Mark Reviewed & Next**: Mark range as checked and continue

**Expected Impact**:
- **Time savings**: 4 seconds per chunk (down from 10-15 seconds)
- **Click reduction**: 1-2 clicks per chunk (down from 4-6 clicks)
- **Throughput increase**: 3-4x more chunks processed per session
- **User satisfaction**: Higher completion rates and less fatigue

**Technical Constraints Respected**:
- Checked date ranges are continuous (start/end only, no gaps)
- Manual review doesn't update checked range (allows return)
- Mark Reviewed advances progress permanently
- All actions respect the continuous range model

The design maintains all functionality of the current system while dramatically reducing cognitive load and physical interaction requirements, and properly integrates with the existing date range tracking architecture.

## Quick Reference: Button Behavior Summary

| Button | Keyboard | Action | Updates Checked Range | Advances to Next |
|--------|----------|--------|---------------------|------------------|
| **✓ Confirm & Next** | `Enter` | Marks selected as transfers | ✅ Yes (after all processed) | ✅ Yes |
| **✗ Ignore** | `Backspace` | Removes from view (leaves uncategorized) | ✅ Yes (after all processed) | ✅ Yes |
| **🔍 Manual Review** | `M` | Opens transactions page with filter | ❌ No | ❌ No (manual return) |
| **Mark Reviewed & Next** | `→` | Marks range as checked | ✅ Yes (immediately) | ✅ Yes |

### State of Candidates After Each Action

| Action | Database State | Can Be Re-detected | Shows in Transactions Page | Notes |
|--------|---------------|-------------------|---------------------------|-------|
| **Confirmed** | Categorized as "Transfer" | ❌ No (excluded from detection) | ✅ Yes (as transfer) | Permanently marked |
| **Ignored** | Uncategorized | ✅ Yes (in future scans) | ✅ Yes (uncategorized) | Session-only ignore |
| **Manual Review** | Varies (user decides) | Depends on categorization | ✅ Yes | User controls outcome |
| **Mark Reviewed** | Unchanged | ✅ Yes (in future scans) | ✅ Yes (current state) | Range marked, data unchanged |

### When to Use Each Button

- **Confirm**: "These ARE transfers" → Mark them as such
- **Ignore**: "These are NOT transfers" → Skip for now, keep uncategorized
- **Manual Review**: "I'm not sure / Need more context" → Look at full transaction details
- **Mark Reviewed**: "Done with this chunk / No candidates" → Move to next range

## Backend Call Optimization

For detailed analysis, see `backend-call-pattern-analysis.md`.

### Current API Call Pattern (Per Chunk)

```
Scan → Detect → Confirm → Next
  ↓       ↓        ↓        ↓
  3      (0)       4        3  = 10 API calls per chunk
```

### Optimized API Call Pattern (Per Chunk)

```
Scan → Detect → Confirm & Next
  ↓       ↓            ↓
  1      (0)           2        = 3 API calls per chunk
```

**Reduction**: 70% fewer API calls per chunk

### Key Optimizations

1. **Remove redundant preference updates**
   - Currently: `detect` updates preferences, then `bulkMark` updates again
   - Optimized: Only update when chunk is completed

2. **Optimistic UI updates**
   - Currently: Reload all data after confirm
   - Optimized: Update local state, skip reload if advancing

3. **Local progress calculation**
   - Currently: Refetch preferences after every update
   - Optimized: Calculate locally, trust our writes

4. **Smart reload logic**
   - Currently: Always reload paired transfers
   - Optimized: Skip reload if moving to next chunk

**Result**: Faster UI, less server load, better UX

### Critical: Resumability

The optimized flow enables a critical feature: **users can leave and return without losing progress**.

**Current Problem**:
- Scan marks range as "checked" immediately
- User reviews 5 of 10 candidates
- User leaves page (interruption)
- Range marked "checked" even though incomplete
- 5 candidates lost in limbo ❌

**Optimized Solution**:
- Scan does NOT mark range as "checked"
- User reviews 5 of 10 candidates  
- User leaves page (interruption)
- Range NOT marked "checked"
- User returns, system recommends same range
- User clicks "Scan Next Chunk" (normal button, nothing special)
- Shows remaining 5 candidates
- Completes review, THEN marks "checked" ✅

**Key Point**: No special "resume" UI needed. Scanning is idempotent - user can scan the same range multiple times, and it just shows unprocessed candidates. This ensures data integrity and seamless workflow.

