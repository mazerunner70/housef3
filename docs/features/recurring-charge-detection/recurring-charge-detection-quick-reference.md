# Recurring Charge Detection - Quick Reference

## File Structure

```
backend/src/
├── services/
│   ├── recurring_charge_feature_service.py     (529 lines)
│   │   └─ RecurringChargeFeatureService        - Extracts 67 or 91-dim features
│   │      • extract_features_batch()           - Main entry point
│   │      • extract_temporal_features()        - 17 temporal features
│   │      • extract_amount_features_batch()    - 1 amount feature
│   │      • extract_description_features_batch() - 49 TF-IDF features
│   │      • _extract_account_type_features()   - 6 account type features (private)
│   │      • _extract_account_name_features()   - 8 account name features (private)
│   │      • _extract_institution_features()    - 5 institution features (private)
│   │      • _extract_account_activity_features() - 5 activity features (private)
│   │
│   └── recurring_charge_detection_service.py   (798 lines)
│       └─ RecurringChargeDetectionService      - Orchestrates ML detection
│          • detect_recurring_patterns()        - Main detection entry point
│          • _perform_clustering()              - DBSCAN clustering
│          • _analyze_clusters()                - Extract patterns from clusters
│          • _analyze_pattern()                 - Analyze single cluster
│          • _detect_frequency()                - Determine recurrence frequency
│          • _analyze_temporal_pattern()        - Extract temporal patterns
│          • _extract_merchant_pattern()        - Extract merchant name
│          • _calculate_confidence_score()      - Base confidence calculation
│          • _apply_account_confidence_adjustments() - Account-aware adjustments
│          • _categorize_pattern()              - Categorize pattern type
│
├── consumers/
│   └── recurring_charge_detection_consumer.py  (~200 lines)
│       └─ RecurringChargeDetectionConsumer     - Processes EventBridge events
│          • process_event()                    - Main event handler
│          • _fetch_transactions()              - Fetch user transactions
│          • _fetch_accounts_map()              - Fetch user accounts
│          • _update_operation_status()         - Update operation tracking
│
├── handlers/
│   └── recurring_charge_operations.py          (376 lines)
│       └─ API handlers for recurring charges
│
└── models/
    └── recurring_charge.py
        ├─ RecurringChargePattern               - Full pattern model
        ├─ RecurringChargePatternCreate         - Creation model
        ├─ RecurringChargePatternUpdate         - Update model
        ├─ RecurrenceFrequency                  - Frequency enum
        └─ TemporalPatternType                  - Pattern type enum
```

## Quick Usage Guide

### 1. Detect Patterns (Base Mode - 67 dimensions)

```python
from services.recurring_charge_detection_service import RecurringChargeDetectionService

service = RecurringChargeDetectionService(country_code='US')
patterns = service.detect_recurring_patterns(
    user_id="user123",
    transactions=transactions,
    min_occurrences=3,      # Default: 3
    min_confidence=0.6,     # Default: 0.6
    eps=0.5                 # DBSCAN epsilon, default: 0.5
)
```

### 2. Detect Patterns (Account-Aware - 91 dimensions)

```python
from services.recurring_charge_detection_service import RecurringChargeDetectionService
from utils.db.accounts import list_user_accounts

# Fetch accounts
accounts = list_user_accounts(user_id)
accounts_map = {account.account_id: account for account in accounts}

# Detect with account features
service = RecurringChargeDetectionService(country_code='US')
patterns = service.detect_recurring_patterns(
    user_id="user123",
    transactions=transactions,
    accounts_map=accounts_map  # Enables 91-dim features
)
```

### 3. Extract Features Only

```python
from services.recurring_charge_feature_service import RecurringChargeFeatureService

service = RecurringChargeFeatureService(country_code='US')

# Base features (67-dim)
features, vectorizer = service.extract_features_batch(transactions)

# Account-aware features (91-dim)
features, vectorizer = service.extract_features_batch(
    transactions, 
    accounts_map=accounts_map
)
```

## Feature Dimensions Reference

### Base Features (67 total)

| Category | Dimensions | Description |
|----------|-----------|-------------|
| Temporal | 17 | Circular encoding (8) + Boolean flags (8) + Position (1) |
| Amount | 1 | Log-scaled and normalized |
| Description | 49 | TF-IDF vectorization of merchant names |

### Account-Aware Features (+24 additional)

| Category | Dimensions | Description |
|----------|-----------|-------------|
| Account Type | 6 | One-hot: CHECKING, SAVINGS, CREDIT_CARD, INVESTMENT, LOAN, OTHER |
| Account Name | 8 | Keywords: business, personal, checking, savings, credit, joint, emergency, investment |
| Institution | 5 | Top 4 institutions + "other" |
| Activity | 5 | Tx count, amount ratio, age, frequency, active status |

**Total with accounts: 67 + 24 = 91 dimensions**

## Configuration Constants

### DBSCAN Clustering
```python
DEFAULT_EPS = 0.5              # Neighborhood radius
MIN_SAMPLES_RATIO = 0.01       # Min samples as ratio of dataset
MIN_CLUSTER_SIZE = 3           # Min transactions for pattern
MIN_CONFIDENCE = 0.6           # Min confidence to surface pattern
```

### Frequency Thresholds (days)
```python
DAILY: (0.5, 1.5)
WEEKLY: (6, 8)
BI_WEEKLY: (12, 16)
SEMI_MONTHLY: (13, 17)
MONTHLY: (25, 35)
BI_MONTHLY: (55, 65)
QUARTERLY: (85, 95)
SEMI_ANNUALLY: (175, 190)
ANNUALLY: (355, 375)
```

### Confidence Score Weights
```python
interval_regularity: 30%    # How regular are the intervals?
amount_regularity: 20%      # How consistent are the amounts?
sample_size: 20%           # How many occurrences?
temporal_consistency: 30%  # How consistent is the timing?
```

## Pattern Categories

Patterns are categorized for account-aware confidence adjustments:

- **subscription**: Streaming, software, memberships
- **utility**: Electric, gas, water, internet
- **bill**: Insurance, phone, credit card payments
- **income**: Salary, payroll, benefits
- **contribution**: Investment contributions, savings transfers
- **transfer**: Account transfers
- **fee**: Bank fees, service charges
- **dividend**: Investment dividends, interest
- **payment**: Loan payments
- **service**: General services
- **expense**: General expenses

## Confidence Adjustments Examples

| Account Type | Frequency | Category | Adjustment |
|-------------|-----------|----------|------------|
| CREDIT_CARD | MONTHLY | subscription | +0.10 ✅ Expected |
| CHECKING | MONTHLY | utility | +0.12 ✅ Expected |
| SAVINGS | WEEKLY | expense | -0.15 ⚠️ Unusual |
| INVESTMENT | QUARTERLY | dividend | +0.12 ✅ Expected |
| LOAN | MONTHLY | payment | +0.20 ✅ Expected |
| CREDIT_CARD | WEEKLY | expense | -0.05 ⚠️ Less typical |

## Event Flow (Consumer)

```
EventBridge Event
    ↓
recurring_charge.detection.requested
    ↓
RecurringChargeDetectionConsumer.process_event()
    ↓
1. Update status: QUEUED → IN_PROGRESS
2. Fetch transactions (with filters)
3. Fetch accounts map
4. Call detection service
5. Save patterns to database
6. Update status: IN_PROGRESS → COMPLETED
    ↓
Operation tracking updated
```

## Common Patterns

### Creating a Detection Operation

```python
from handlers.recurring_charge_operations import trigger_detection_handler

event = {
    "body": json.dumps({
        "minOccurrences": 3,
        "minConfidence": 0.6,
        "startDate": 1609459200000,  # Optional
        "endDate": 1640995200000,    # Optional
        "includeReviewed": False     # Optional
    })
}

response = trigger_detection_handler(event, user_id)
# Returns operation_id for tracking
```

### Monitoring Detection Progress

```python
# Operation status transitions:
QUEUED → IN_PROGRESS → COMPLETED (or FAILED)

# Progress updates during detection:
# 10%: Operation queued
# 30%: Fetching accounts
# 50%: Extracting features
# 70%: Clustering
# 90%: Analyzing patterns
# 100%: Complete
```

## Testing

### Unit Test Example

```python
def test_account_aware_features():
    service = RecurringChargeFeatureService('US')
    
    # Create test data
    account = Account(
        userId='test',
        accountId=uuid.uuid4(),
        accountName='Business Checking',
        accountType=AccountType.CHECKING,
        institution='Chase',
        firstTransactionDate=1600000000000
    )
    
    tx = Transaction(
        userId='test',
        fileId=uuid.uuid4(),
        accountId=account.account_id,
        date=1700000000000,
        description='NETFLIX',
        amount=Decimal('-15.99')
    )
    
    # Test account-aware mode
    features, _ = service.extract_features_batch(
        [tx],
        accounts_map={account.account_id: account}
    )
    
    assert features.shape == (1, 91)
    # Verify account type one-hot encoding
    # features[0, 67:73] should have CHECKING=1
```

## Performance Tips

1. **Batch Size**: Optimal batch size is 1000-5000 transactions
2. **Account Map**: Fetch accounts once, reuse for multiple detections
3. **Caching**: Consider caching TF-IDF vectorizers for repeated runs
4. **Parallelization**: Can process multiple users in parallel
5. **Memory**: ~73 KB per 1000 transactions in account-aware mode

## Troubleshooting

### No patterns detected
- Check `min_occurrences` (default: 3) - might need lower threshold
- Check `min_confidence` (default: 0.6) - might need lower threshold
- Verify sufficient transaction history (6+ months recommended)
- Check DBSCAN `eps` parameter - try values between 0.3 and 0.7

### Low confidence scores
- More transactions = higher confidence (sample size factor)
- Irregular intervals = lower confidence
- Variable amounts = lower confidence
- Inconsistent timing = lower confidence

### Performance issues
- Reduce batch size if memory constrained
- Consider filtering transactions before detection
- Check for outliers that might skew clustering
