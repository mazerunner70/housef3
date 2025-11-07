# Recurring Charge Detection - Implementation Guide

**Version:** 1.0  
**Date:** November 7, 2025

This guide describes bespoke code patterns and implementation details specific to the recurring charge detection feature.

---

## Table of Contents

1. [Enum Handling Pattern](#enum-handling-pattern)
2. [DynamoDB Serialization](#dynamodb-serialization)
3. [Circular Encoding for Temporal Features](#circular-encoding-for-temporal-features)
4. [Week-of-Month Pattern Detection](#week-of-month-pattern-detection)
5. [Confidence Score Calculation](#confidence-score-calculation)
6. [Performance Monitoring](#performance-monitoring)
7. [Access Control Pattern](#access-control-pattern)

---

## Enum Handling Pattern

### Problem
Pydantic models with `use_enum_values=True` convert enum objects back to strings during validation, causing `AttributeError: 'str' object has no attribute 'value'`.

### Solution
Use `model_construct()` instead of `model_validate()` after manual enum conversion.

### Implementation

```python
from enum import Enum
from pydantic import BaseModel, ConfigDict

class RecurrenceFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class RecurringChargePattern(BaseModel):
    frequency: RecurrenceFrequency
    
    model_config = ConfigDict(
        use_enum_values=True  # Converts enums to strings in JSON
    )
    
    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]):
        """Convert DynamoDB item to model, preserving enum types."""
        # Copy to avoid modifying original
        item = data.copy()
        
        # Manually convert string to enum BEFORE validation
        if 'frequency' in item and isinstance(item['frequency'], str):
            item['frequency'] = RecurrenceFrequency(item['frequency'])
        
        # Use model_construct to bypass validation that would convert back
        return cls.model_construct(**item)
```

### Why This Works
- `model_validate()` runs Pydantic validators that convert enums → strings
- `model_construct()` bypasses validators, preserving enum objects
- Manual conversion ensures we have enum objects, not strings

### Testing Pattern

```python
def test_enum_preservation():
    """Test that enums are preserved through serialization."""
    pattern = RecurringChargePattern(frequency=RecurrenceFrequency.MONTHLY)
    
    # Serialize to DynamoDB
    item = pattern.to_dynamodb_item()
    assert item['frequency'] == 'monthly'  # String in DB
    
    # Deserialize from DynamoDB
    restored = RecurringChargePattern.from_dynamodb_item(item)
    assert isinstance(restored.frequency, RecurrenceFrequency)  # Enum object
    assert restored.frequency == RecurrenceFrequency.MONTHLY
    assert restored.frequency.value == 'monthly'  # Can access .value
```

---

## DynamoDB Serialization

### Pattern: Bidirectional Conversion

```python
class RecurringChargePattern(BaseModel):
    pattern_id: uuid.UUID
    amount_mean: Decimal
    frequency: RecurrenceFrequency
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert model to DynamoDB item."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Convert UUIDs to strings
        for key, value in data.items():
            if isinstance(value, uuid.UUID):
                data[key] = str(value)
        
        # Decimals are handled automatically by boto3
        # Enums are already strings due to use_enum_values=True
        
        return data
    
    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]):
        """Convert DynamoDB item to model."""
        item = data.copy()
        
        # Convert string UUIDs back to UUID objects
        if 'patternId' in item and isinstance(item['patternId'], str):
            item['patternId'] = uuid.UUID(item['patternId'])
        
        # Convert string enums back to enum objects
        if 'frequency' in item and isinstance(item['frequency'], str):
            item['frequency'] = RecurrenceFrequency(item['frequency'])
        
        if 'temporalPatternType' in item and isinstance(item['temporalPatternType'], str):
            item['temporalPatternType'] = TemporalPatternType(item['temporalPatternType'])
        
        # Use model_construct to preserve enum objects
        return cls.model_construct(**item)
```

### Key Points
- Always use `model_dump(by_alias=True)` for camelCase field names
- Use `exclude_none=True` to avoid storing null values
- Convert UUIDs manually (boto3 doesn't handle them)
- Decimals are handled automatically by boto3
- Use `model_construct()` for deserialization

---

## Circular Encoding for Temporal Features

### Problem
Cyclical features (day of week, day of month) need to preserve their circular nature:
- Day 31 should be close to Day 1 (month boundary)
- Sunday should be close to Monday (week boundary)

### Solution
Use sine/cosine transformations.

### Implementation

```python
import numpy as np
from datetime import datetime
from calendar import monthrange

def extract_temporal_features(transaction_date: datetime) -> Dict[str, float]:
    """Extract temporal features with circular encoding."""
    day_of_week = transaction_date.weekday()  # 0=Monday, 6=Sunday
    day_of_month = transaction_date.day
    year = transaction_date.year
    month = transaction_date.month
    days_in_month = monthrange(year, month)[1]
    
    features = {}
    
    # Circular encoding for day of week
    features['day_of_week_sin'] = np.sin(2 * np.pi * day_of_week / 7)
    features['day_of_week_cos'] = np.cos(2 * np.pi * day_of_week / 7)
    
    # Circular encoding for absolute day of month (for "15th" patterns)
    features['day_of_month_sin'] = np.sin(2 * np.pi * day_of_month / 31)
    features['day_of_month_cos'] = np.cos(2 * np.pi * day_of_month / 31)
    
    # Circular encoding for relative position (for "last day" patterns)
    # Handles variable month lengths properly
    normalized_position = (day_of_month - 1) / (days_in_month - 1) if days_in_month > 1 else 0
    features['month_position_sin'] = np.sin(2 * np.pi * normalized_position)
    features['month_position_cos'] = np.cos(2 * np.pi * normalized_position)
    
    return features
```

### Why Two Encodings?
- **Absolute** (day_of_month): For patterns like "15th of each month"
- **Relative** (month_position): For patterns like "last day of month"

### Example
```python
# February 28 (last day)
feb_28 = datetime(2024, 2, 28)
features = extract_temporal_features(feb_28)
# month_position_sin ≈ 0.0 (normalized_position = 1.0)

# March 1 (first day)
mar_1 = datetime(2024, 3, 1)
features = extract_temporal_features(mar_1)
# month_position_sin ≈ 0.0 (normalized_position = 0.0)

# These are close in circular space!
```

---

## Week-of-Month Pattern Detection

### Pattern: Detect "Last Thursday" or "First Friday"

```python
from collections import Counter
from calendar import monthrange

def detect_weekday_of_month_pattern(cluster_transactions: List) -> Optional[Dict]:
    """Detect if transactions follow 'Nth weekday of month' pattern."""
    if len(cluster_transactions) < 3:
        return None
    
    weekday_info = []
    for txn in cluster_transactions:
        date = txn.date
        day_of_week = date.weekday()
        day = date.day
        days_in_month = monthrange(date.year, date.month)[1]
        
        # Which occurrence of this weekday? (1-5)
        occurrence = (day - 1) // 7 + 1
        
        # Is this the LAST occurrence?
        days_remaining = days_in_month - day
        is_last = days_remaining < 7
        
        weekday_info.append({
            'day_of_week': day_of_week,
            'occurrence': occurrence,
            'is_last': is_last
        })
    
    # Check for "last weekday of month" pattern
    last_weekday_matches = [w for w in weekday_info if w['is_last']]
    last_weekday_pct = len(last_weekday_matches) / len(weekday_info)
    
    if last_weekday_pct >= 0.70:
        weekdays = [w['day_of_week'] for w in last_weekday_matches]
        most_common_weekday = Counter(weekdays).most_common(1)[0][0]
        
        return {
            'pattern_type': TemporalPatternType.LAST_WEEKDAY_OF_MONTH,
            'day_of_week': most_common_weekday,
            'confidence': last_weekday_pct
        }
    
    # Check for "first weekday of month" pattern
    first_weekday_matches = [w for w in weekday_info if w['occurrence'] == 1]
    first_weekday_pct = len(first_weekday_matches) / len(weekday_info)
    
    if first_weekday_pct >= 0.70:
        weekdays = [w['day_of_week'] for w in first_weekday_matches]
        most_common_weekday = Counter(weekdays).most_common(1)[0][0]
        
        return {
            'pattern_type': TemporalPatternType.FIRST_WEEKDAY_OF_MONTH,
            'day_of_week': most_common_weekday,
            'confidence': first_weekday_pct
        }
    
    return None
```

### Key Algorithm Details
1. Calculate occurrence number: `(day - 1) // 7 + 1`
2. Detect last occurrence: `days_remaining < 7`
3. Require 70% consistency threshold
4. Find most common weekday within pattern

---

## Confidence Score Calculation

### Multi-Factor Confidence Formula

```python
def calculate_confidence_score(cluster_transactions: List, pattern: Dict) -> float:
    """Calculate multi-factor confidence score (0.0-1.0)."""
    
    # 1. Interval Regularity (30% weight)
    intervals = [
        (cluster_transactions[i+1].date - cluster_transactions[i].date).days
        for i in range(len(cluster_transactions) - 1)
    ]
    mean_interval = np.mean(intervals)
    std_interval = np.std(intervals)
    interval_regularity = 1.0 / (1.0 + std_interval / (mean_interval + 1))
    
    # 2. Amount Regularity (20% weight)
    amounts = [txn.amount for txn in cluster_transactions]
    mean_amount = np.mean(amounts)
    std_amount = np.std(amounts)
    amount_regularity = 1.0 / (1.0 + std_amount / (abs(mean_amount) + 1))
    
    # 3. Sample Size Score (20% weight)
    # More samples = higher confidence, cap at 12 (1 year monthly)
    sample_size_score = min(1.0, len(cluster_transactions) / 12)
    
    # 4. Temporal Consistency (30% weight)
    # Percentage of transactions matching detected pattern
    temporal_consistency = pattern.get('temporal_consistency', 0.0)
    
    # Weighted sum
    confidence = (
        0.30 * interval_regularity +
        0.20 * amount_regularity +
        0.20 * sample_size_score +
        0.30 * temporal_consistency
    )
    
    return round(confidence, 2)
```

### Example Calculation

```
Netflix Subscription (12 months):
- Intervals: [30, 31, 30, 31, 30, 31, 30, 31, 30, 31, 30]
- Mean: 30.5, Std: 0.5
- Interval regularity: 1.0 / (1.0 + 0.5/30.5) = 0.984

- Amounts: [14.99] × 12
- Mean: 14.99, Std: 0.0
- Amount regularity: 1.0 / (1.0 + 0.0/14.99) = 1.000

- Sample size: 12/12 = 1.000

- Temporal: 12/12 on day 15 = 1.000

Confidence = 0.30×0.984 + 0.20×1.000 + 0.20×1.000 + 0.30×1.000
          = 0.295 + 0.200 + 0.200 + 0.300
          = 0.995 ≈ 0.99
```

---

## Performance Monitoring

### Pattern: Stage-Level Tracking

```python
from backend.src.utils.ml_performance import MLPerformanceTracker

def detect_recurring_patterns(user_id: str, transactions: List):
    """Detect patterns with comprehensive performance tracking."""
    
    with MLPerformanceTracker("detect_recurring_charges") as tracker:
        tracker.set_transaction_count(len(transactions))
        
        # Stage 1: Feature Extraction
        with tracker.stage('feature_extraction'):
            features = extract_features(transactions)
        
        # Stage 2: Clustering
        with tracker.stage('clustering'):
            clusters = dbscan_cluster(features)
        tracker.set_clusters_identified(len(set(clusters)))
        
        # Stage 3: Pattern Analysis
        with tracker.stage('pattern_analysis'):
            patterns = analyze_patterns(clusters, transactions)
        tracker.set_patterns_detected(len(patterns))
        
        return patterns
    
    # Metrics automatically logged on context exit
```

### Automatic Logging

The tracker automatically logs:
- Total execution time
- Stage-level breakdown
- Transactions per second
- Memory usage
- Warning if >10s, error if >30s

### Example Output

```
INFO: ML operation 'detect_recurring_charges' completed in 8,234ms
  - Transactions: 1,543
  - Throughput: 187.4 transactions/second
  - Feature extraction: 1,823ms (22.1%)
  - Clustering: 4,521ms (54.9%)
  - Pattern analysis: 1,890ms (23.0%)
  - Patterns detected: 12
  - Clusters identified: 45
```

---

## Access Control Pattern

### Pattern: User Ownership Validation

```python
from backend.src.utils.db_utils import NotFound

def checked_mandatory_pattern(
    user_id: str,
    pattern_id: str
) -> RecurringChargePattern:
    """
    Get pattern and verify user ownership.
    Raises NotFound if pattern doesn't exist or user doesn't own it.
    """
    pattern = get_pattern_by_id_from_db(user_id, pattern_id)
    
    if not pattern:
        raise NotFound(f"Pattern {pattern_id} not found")
    
    if pattern.user_id != user_id:
        raise NotFound(f"Pattern {pattern_id} not found")  # Don't leak existence
    
    return pattern


def update_pattern_in_db(
    user_id: str,
    pattern_id: str,
    updates: Dict[str, Any]
) -> RecurringChargePattern:
    """Update pattern with ownership check."""
    # Verify ownership first
    existing_pattern = checked_mandatory_pattern(user_id, pattern_id)
    
    # Apply updates
    updates['updatedAt'] = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    # Update in database
    table = tables.recurring_charge_patterns
    table.update_item(
        Key={'userId': user_id, 'patternId': pattern_id},
        UpdateExpression='SET ' + ', '.join(f'#{k} = :{k}' for k in updates.keys()),
        ExpressionAttributeNames={f'#{k}': k for k in updates.keys()},
        ExpressionAttributeValues={f':{k}': v for k, v in updates.items()}
    )
    
    # Return updated pattern
    return get_pattern_by_id_from_db(user_id, pattern_id)
```

### Key Points
- Always validate user ownership before operations
- Use `NotFound` exception (don't leak pattern existence)
- Check ownership in GET, UPDATE, DELETE operations
- Don't expose whether pattern exists for other users

---

## Testing Patterns

### Pattern: Synthetic Data for ML Testing

```python
def create_synthetic_pattern(
    start_date: datetime,
    frequency_days: int,
    num_occurrences: int,
    amount: float,
    description: str,
    noise_days: int = 0,
    noise_amount: float = 0.0
) -> List[Transaction]:
    """Create synthetic transaction pattern for testing."""
    transactions = []
    current_date = start_date
    
    for i in range(num_occurrences):
        # Add temporal noise
        actual_date = current_date + timedelta(days=random.randint(-noise_days, noise_days))
        
        # Add amount noise
        actual_amount = amount + random.uniform(-noise_amount, noise_amount)
        
        transactions.append(Transaction(
            date=actual_date,
            amount=actual_amount,
            description=description
        ))
        
        current_date += timedelta(days=frequency_days)
    
    return transactions


def test_monthly_pattern_detection():
    """Test detection of perfect monthly pattern."""
    # Create 12 months of Netflix charges on 15th
    transactions = create_synthetic_pattern(
        start_date=datetime(2024, 1, 15),
        frequency_days=30,
        num_occurrences=12,
        amount=14.99,
        description="NETFLIX SUBSCRIPTION"
    )
    
    patterns = detect_recurring_patterns("test_user", transactions)
    
    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.frequency == RecurrenceFrequency.MONTHLY
    assert pattern.temporal_pattern_type == TemporalPatternType.DAY_OF_MONTH
    assert pattern.day_of_month == 15
    assert pattern.confidence_score >= 0.95
```

---

## Common Pitfalls

### 1. Enum AttributeError
❌ **Wrong:**
```python
pattern = RecurringChargePattern.from_dynamodb_item(item)
# pattern.frequency is a string!
print(pattern.frequency.value)  # AttributeError
```

✅ **Correct:**
```python
# Use model_construct in from_dynamodb_item
pattern = RecurringChargePattern.from_dynamodb_item(item)
# pattern.frequency is an enum object
print(pattern.frequency.value)  # Works!
```

### 2. Variable Month Lengths
❌ **Wrong:**
```python
# Treats all months as 31 days
day_of_month_sin = sin(2π × day / 31)
# Feb 28 and Mar 1 are far apart!
```

✅ **Correct:**
```python
# Use normalized position for end-of-month patterns
days_in_month = monthrange(year, month)[1]
normalized_position = (day - 1) / (days_in_month - 1)
month_position_sin = sin(2π × normalized_position)
# Feb 28 (position=1.0) and Mar 1 (position=0.0) are close!
```

### 3. Access Control
❌ **Wrong:**
```python
def get_pattern(pattern_id):
    return db.get(pattern_id)  # No user check!
```

✅ **Correct:**
```python
def get_pattern(user_id, pattern_id):
    pattern = db.get(pattern_id)
    if pattern.user_id != user_id:
        raise NotFound()  # Don't leak existence
    return pattern
```

---

## References

- **Data Models**: `backend/src/models/recurring_charge.py`
- **DB Operations**: `backend/src/utils/db/recurring_charges.py`
- **Performance Monitoring**: `backend/src/utils/ml_performance.py`
- **Tests**: `backend/tests/models/test_recurring_charge.py`

---

**Document Version:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-07 | Initial implementation guide |

