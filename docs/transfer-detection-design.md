# Transfer Detection System - Technical Design

## Overview

The transfer detection system automatically identifies and pairs transactions that represent money transfers between user accounts. This is crucial for accurate financial reporting, as transfers should not be counted as income or expenses but rather as movements between accounts.

## Problem Statement

When users import transactions from multiple accounts, transfers between accounts appear as separate transactions:
- **Account A**: -$500 (outgoing transfer)
- **Account B**: +$500 (incoming transfer)

Without proper pairing, these would incorrectly appear as:
- $500 expense from Account A
- $500 income to Account B

The system must automatically detect these pairs and categorize them as transfers to provide accurate financial insights.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│   Frontend UI   │    │   Backend API        │    │   Detection     │
│   TransfersTab  │◄──►│   transfer_operations│◄──►│   Service       │
└─────────────────┘    └──────────────────────┘    └─────────────────┘
                                                           │
                                                           ▼
                                                    ┌─────────────────┐
                                                    │   Database      │
                                                    │   Transactions  │
                                                    └─────────────────┘
```

## Core Components

### 1. TransferDetectionService (`backend/src/services/transfer_detection_service.py`)

The main engine for detecting transfer pairs using an optimized sliding window algorithm.

#### Key Classes

```python
class MinimalTransaction(NamedTuple):
    """Memory-efficient transaction representation for detection."""
    transaction_id: str
    account_id: str
    amount: Decimal
    date: int  # timestamp in milliseconds
    abs_amount: Decimal

class TransferDetectionService:
    """Service for detecting and managing transfer transactions."""
```

#### Core Methods

- `detect_transfers_for_user_in_range()` - Main detection method
- `mark_as_transfer_pair()` - Mark two transactions as a transfer pair
- `_sliding_window_transfer_detection()` - Optimized detection algorithm
- `get_or_create_transfer_category()` - Manage transfer categories

### 2. Transfer Operations Handler (`backend/src/handlers/transfer_operations.py`)

REST API endpoints for transfer operations:

- `GET /transfers/detect` - Detect potential transfers
- `GET /transfers/paired` - Get existing transfer pairs
- `POST /transfers/mark-pair` - Mark single transfer pair
- `POST /transfers/bulk-mark` - Mark multiple transfer pairs

### 3. Frontend Transfer Service (`frontend/src/services/TransferService.ts`)

Client-side service handling:
- API communication
- Progress tracking
- Date range recommendations
- Error handling and validation

### 4. Transfer UI Component (`frontend/src/new-ui/components/business/transactions/TransfersTab.tsx`)

User interface providing:
- Transfer detection controls
- Progress visualization
- Bulk selection and marking
- Date range management

## Detection Algorithm

### Sliding Window Approach

The system uses a sophisticated sliding window algorithm to efficiently process large datasets:

```
Timeline: |----Window 1----|
          |        |----Window 2----|
          |        |        |----Window 3----|
          |<-overlap->|<-overlap->|

Window Size: 14 days
Overlap: 3 days
```

#### Why Sliding Windows?

1. **Memory Efficiency**: Process transactions in manageable chunks
2. **Cross-Boundary Detection**: Overlap ensures transfers spanning window boundaries are detected
3. **Performance**: Avoid loading entire transaction history at once
4. **Scalability**: Handles millions of transactions efficiently

### Matching Criteria

Two transactions are considered a transfer pair if they meet ALL criteria:

#### 1. Different Accounts
```python
if tx1.account_id == tx2.account_id:
    continue  # Skip same-account transactions
```

#### 2. Opposite Amounts (within tolerance)
```python
amount_tolerance = Decimal('0.01')  # $0.01 tolerance
if abs(abs(tx1.amount) - abs(tx2.amount)) <= amount_tolerance:
    if (tx1.amount > 0 and tx2.amount < 0) or (tx1.amount < 0 and tx2.amount > 0):
        # Valid amount match
```

#### 3. Date Proximity
```python
max_date_diff = 7 * 24 * 60 * 60 * 1000  # 7 days in milliseconds
if abs(tx1.date - tx2.date) <= max_date_diff:
    # Valid date match
```

#### 4. Not Already Processed
```python
if tx_id not in processed_ids:
    # Available for matching
```

### Optimization Techniques

#### 1. Amount Sorting
Transactions are sorted by absolute amount to enable early termination:

```python
minimal_txs.sort(key=lambda tx: tx.abs_amount)

# Early termination when amount difference exceeds tolerance
if amount_diff > tolerance:
    break  # No point checking further
```

#### 2. Minimal Memory Usage
Convert to lightweight objects during processing:

```python
minimal_tx = MinimalTransaction(
    transaction_id=tx_id,
    account_id=str(tx.account_id),
    amount=tx.amount,
    date=tx.date,
    abs_amount=abs(tx.amount)
)
```

#### 3. Batch Processing
Process transactions in batches to prevent memory overflow:

```python
batch_size = 14  # days
overlap_size = 3  # days
```

## Progress Tracking System

### User Preferences Integration

The system tracks which date ranges have been checked to:
- Avoid duplicate processing
- Show progress to users
- Recommend next ranges to check

```typescript
interface TransferProgress {
    hasData: boolean;
    totalDays: number;
    checkedDays: number;
    progressPercentage: number;
    isComplete: boolean;
    accountDateRange: DateRange;
    checkedDateRange: DateRange;
}
```

### Smart Recommendations

The system provides intelligent recommendations for next date ranges:

#### Initial Recommendation
- Start with recent 30 days of actual transaction data
- Don't extend beyond actual account boundaries

#### Forward Extension
- Extend toward present with 3-day overlap
- Cap at latest transaction date

#### Backward Extension  
- Extend into historical data with 3-day overlap
- Cap at earliest transaction date

```typescript
const OVERLAP_DAYS = 3;  // For transfer pair detection
const CHUNK_DAYS = 30;   // Manageable processing chunks
```

## Category Management

### Transfer Category Creation

When transfers are detected and marked:

1. **Auto-create Transfer Category**: If none exists
```python
category_create = CategoryCreate(
    name="Transfers",
    type=CategoryType.TRANSFER,
    icon="transfer",
    color="#6B7280"
)
```

2. **Assign to Both Transactions**: Both outgoing and incoming transactions get the transfer category

3. **Set as Primary**: Transfer category becomes the primary category

### Impact on Financial Reporting

- **Income/Expense Calculations**: Transfer transactions are excluded
- **Account Balances**: Remain accurate (transfers don't affect net worth)
- **Category Reports**: Transfers appear in their own category

## Performance Considerations

### Database Optimization

#### Pagination Handling
```python
# Prevent infinite loops in DynamoDB pagination
consecutive_empty_batches = 0
max_consecutive_empty_batches = 3

if len(batch_result) == 0:
    consecutive_empty_batches += 1
    if consecutive_empty_batches >= max_consecutive_empty_batches:
        break  # Prevent infinite loop
```

#### Query Optimization
- Use GSI for date range queries
- Limit batch sizes to prevent timeouts
- Index on user_id + date for efficient filtering

### Memory Management

#### Minimal Objects
Use lightweight objects during processing to reduce memory usage:

```python
# Instead of full Transaction objects
minimal_txs = [MinimalTransaction(...) for tx in transactions]
```

#### Garbage Collection
- Clear processed transaction sets between batches
- Use generators where possible
- Avoid keeping full transaction lists in memory

### Algorithm Complexity

- **Time Complexity**: O(n log n) due to sorting + O(n²) for matching in worst case
- **Space Complexity**: O(n) for minimal transaction objects
- **Practical Performance**: Optimized for real-world data patterns

## Error Handling

### Backend Error Patterns

```python
try:
    # Transfer detection logic
    transfer_pairs = self._detect_transfers_in_batches(user_id, date_range_days)
except Exception as e:
    logger.error(f"Error detecting transfers for user {user_id}: {str(e)}")
    return []  # Graceful degradation
```

### Frontend Error Handling

```typescript
try {
    const result = await detectPotentialTransfers(startDate, endDate);
    // Handle success
} catch (error) {
    setError(error instanceof Error ? error.message : 'Failed to detect transfers');
    // Show user-friendly error message
}
```

### Common Error Scenarios

1. **DynamoDB Pagination Issues**: Infinite loops with empty results
2. **Date Format Mismatches**: Invalid timestamp conversions  
3. **Memory Exhaustion**: Too many transactions in single batch
4. **Network Timeouts**: Long-running detection operations

## Testing Strategy

### Unit Tests

#### Algorithm Testing (`test_transfer_detection_service.py`)
- Simple transfer pair detection
- Amount tolerance validation
- Date window validation
- Same account rejection
- Multiple pair detection
- Edge cases (empty lists, single transactions)

#### Frontend Testing (`TransferService.test.ts`)
- Progress calculation accuracy
- Date range recommendation logic
- Boundary condition handling
- Error scenario handling

### Integration Tests

- Full API workflow testing
- Database interaction validation
- UI component integration
- Performance benchmarking

### Test Data Patterns

```python
# Create test transfer pair
tx_out = create_test_transaction(
    amount=Decimal("-100.00"),
    date=base_date,
    account_id="account-a"
)
tx_in = create_test_transaction(
    amount=Decimal("100.00"),
    date=base_date + timedelta(hours=1),
    account_id="account-b"
)
```

## Security Considerations

### Authorization
- All operations require valid user authentication
- Transactions are filtered by user_id
- Cross-user data access is prevented

### Data Validation
- Amount validation (reasonable ranges)
- Date validation (not in future, not too old)
- Account ownership verification

### Rate Limiting
- Detection operations are resource-intensive
- Consider rate limiting for bulk operations
- Monitor for abuse patterns

## Monitoring and Observability

### Logging Strategy

```python
logger.info(f"Detected {len(all_transfer_pairs)} potential transfer pairs for user {user_id}")
logger.debug(f"Processing window {i+1}/{loop_size}: {window_start.date()} to {current_end.date()}")
logger.warning(f"Empty batch detected - potential pagination issue")
```

### Metrics to Track

- **Detection Success Rate**: Percentage of successful detections
- **Processing Time**: Time per batch/user
- **Memory Usage**: Peak memory during detection
- **User Adoption**: How many users use transfer detection
- **Accuracy**: Manual verification of detected pairs

### Performance Monitoring

- **Database Query Performance**: Monitor slow queries
- **API Response Times**: Track endpoint latency
- **Error Rates**: Monitor failed detection attempts
- **Resource Usage**: CPU and memory consumption

## Future Enhancements

### Algorithm Improvements

1. **Machine Learning**: Learn from user corrections to improve matching
2. **Fuzzy Matching**: Handle slight amount differences better
3. **Description Analysis**: Use transaction descriptions for better matching
4. **Recurring Transfer Detection**: Identify patterns in regular transfers

### User Experience

1. **Auto-Approval**: Automatically approve high-confidence matches
2. **Bulk Operations**: Enhanced bulk selection and management
3. **Transfer Templates**: Save common transfer patterns
4. **Mobile Optimization**: Improve mobile transfer management

### Performance Optimizations

1. **Caching**: Cache detection results for repeated queries
2. **Background Processing**: Move detection to background jobs
3. **Incremental Updates**: Only process new transactions
4. **Database Optimization**: Specialized indexes for transfer queries

### Integration Features

1. **Bank Integration**: Direct transfer detection from bank APIs
2. **Multi-Currency**: Handle transfers between different currencies
3. **Investment Transfers**: Handle investment account transfers
4. **Scheduled Transfers**: Predict and pre-mark scheduled transfers

## Conclusion

The transfer detection system provides a sophisticated solution for automatically identifying and managing inter-account transfers. The sliding window algorithm with overlap ensures comprehensive detection while maintaining good performance. The system is designed for scalability, reliability, and user-friendliness, with comprehensive error handling and progress tracking.

The modular architecture allows for future enhancements while maintaining backward compatibility. The extensive testing ensures reliability, and the monitoring capabilities provide visibility into system performance and user behavior.
