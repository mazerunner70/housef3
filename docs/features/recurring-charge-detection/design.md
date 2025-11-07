# Recurring Charge Detection - Design

**Version:** 2.0  
**Date:** November 7, 2025  
**Status:** Active Development

---

## Purpose

Automatically detect recurring charges (subscriptions, bills, salaries) in transaction history using unsupervised machine learning, enabling automatic categorization and budget forecasting.

---

## How It Works

### 1. Feature Engineering

Transform each transaction into a 67-dimensional feature vector:

**Temporal Features (17 features):**
- Circular encoding: day of week, day of month, month position, week of month (8 features)
- Boolean flags: working day, first/last working day, first/last weekday of month, weekend (8 features)
- Position: normalized day position in month (1 feature)

**Amount Features (1 feature):**
- Log-scaled and normalized amount

**Description Features (50 features):**
- TF-IDF vectorization of merchant names

### 2. Clustering (DBSCAN)

Group similar transactions without pre-specifying cluster count:
- **eps**: 0.5 (neighborhood radius)
- **min_samples**: max(3, n_samples × 0.01)
- Automatically identifies noise/outliers

### 3. Pattern Analysis

For each cluster (≥3 transactions):

**Detect Frequency:**
- Daily (~1 day), Weekly (~7 days), Monthly (~30 days), Quarterly (~90 days), etc.

**Detect Temporal Pattern (priority order):**
1. Last working day (>70% match)
2. First working day (>70% match)
3. Last weekday of month - e.g., last Thursday (>70% match)
4. First weekday of month - e.g., first Friday (>70% match)
5. Nth weekday of month - e.g., second Tuesday (>70% match)
6. Specific day of month - e.g., 15th (>60% match)
7. Specific day of week - e.g., every Tuesday (>60% match)
8. Flexible (no clear pattern)

**Extract Merchant Pattern:**
- Find common substring/prefix in descriptions
- Examples: "NETFLIX" from "NETFLIX SUBSCRIPTION", "NETFLIX MONTHLY"

**Calculate Confidence (0.0-1.0):**
```
confidence = 0.30 × interval_regularity +
             0.20 × amount_regularity +
             0.20 × sample_size_score +
             0.30 × temporal_consistency
```

### 4. Filtering

Surface patterns with:
- ≥3 occurrences
- ≥0.6 confidence score

---

## Data Models

### RecurringChargePattern

```python
{
  "patternId": "uuid",
  "userId": "string",
  "merchantPattern": "NETFLIX",           # Matching string
  "frequency": "monthly",                 # DAILY|WEEKLY|MONTHLY|etc.
  "temporalPatternType": "day_of_month",  # Pattern type
  "dayOfWeek": 3,                         # 0-6 (Mon-Sun), optional
  "dayOfMonth": 15,                       # 1-31, optional
  "weekOfMonth": 2,                       # 1-5, optional (for Nth weekday)
  "toleranceDays": 2,                     # ±N days
  "amountMean": 14.99,
  "amountStd": 0.0,
  "amountMin": 14.99,
  "amountMax": 14.99,
  "amountTolerancePct": 10.0,             # ±%
  "confidenceScore": 0.96,
  "transactionCount": 12,
  "firstOccurrence": 1672531200000,       # timestamp ms
  "lastOccurrence": 1704067200000,
  "suggestedCategoryId": "uuid",          # optional
  "autoCategorize": false,
  "active": true
}
```

### Pattern Types

| Type | dayOfWeek | dayOfMonth | weekOfMonth | Example |
|------|-----------|------------|-------------|---------|
| `day_of_month` | - | 15 | - | 15th of each month |
| `day_of_week` | 2 | - | - | Every Tuesday |
| `first_working_day` | - | - | - | First business day |
| `last_working_day` | - | - | - | Last business day |
| `last_weekday_of_month` | 3 | - | - | Last Thursday |
| `first_weekday_of_month` | 4 | - | 1 | First Friday |
| `second_weekday_of_month` | 1 | - | 2 | Second Tuesday |

---

## Architecture

### Backend Components

**Services:**
- `RecurringChargeFeatureService` - Feature extraction
- `RecurringChargeDetectionService` - DBSCAN clustering and pattern analysis
- `RecurringChargePredictionService` - Next occurrence prediction

**Handlers:**
- `detect_recurring_charges` - Trigger detection for user
- `get_patterns` - List detected patterns
- `update_pattern` - Modify pattern (activate/deactivate, link category)
- `predict_occurrences` - Get upcoming charges

**Database:**
- `recurring_charge_patterns` - Detected patterns
- `recurring_charge_predictions` - Next occurrence predictions
- `pattern_feedback` - User feedback for ML improvement

**Consumer:**
- `recurring_charge_detection_consumer` - Async detection via EventBridge

### Frontend Components

**Services:**
- `recurringChargeService.ts` - API client

**Components:**
- `RecurringChargesTab` - Main UI in category management
- `RecurringChargeCard` - Individual pattern display
- `PatternConfidenceBadge` - Confidence visualization
- `LinkToCategoryDialog` - Link pattern to category

---

## API Endpoints

### POST /api/recurring-charges/detect
Trigger pattern detection for user.

**Request:**
```json
{
  "minOccurrences": 3,
  "minConfidence": 0.6,
  "startDate": 1672531200000,  // optional
  "endDate": 1704067200000     // optional
}
```

**Response:**
```json
{
  "operationId": "uuid",
  "status": "processing",
  "message": "Detection started"
}
```

### GET /api/recurring-charges/patterns
List detected patterns.

**Query Params:**
- `active`: boolean
- `minConfidence`: float

**Response:**
```json
{
  "patterns": [...],
  "count": 12
}
```

### PATCH /api/recurring-charges/patterns/{patternId}
Update pattern.

**Request:**
```json
{
  "active": false,
  "suggestedCategoryId": "uuid",
  "autoCategorize": true
}
```

### GET /api/recurring-charges/predictions
Get upcoming charges (next 30 days).

**Response:**
```json
{
  "predictions": [
    {
      "patternId": "uuid",
      "merchantPattern": "NETFLIX",
      "nextExpectedDate": 1704067200000,
      "expectedAmount": 14.99,
      "daysUntil": 15,
      "confidence": 0.96
    }
  ],
  "totalAmount": 245.67,
  "count": 8
}
```

---

## Performance

### Execution Time
- Feature extraction: ~1-2s per 1,000 transactions
- Clustering: ~2-3s per 1,000 transactions
- Pattern analysis: ~0.5s per cluster
- **Total**: ~5-10s for 1,000 transactions

### Lambda Configuration
- **Memory**: 1024 MB (for scikit-learn)
- **Timeout**: 60 seconds
- **Runtime**: Python 3.12

### Scalability
- **Target**: 10,000+ transactions per user
- **Complexity**: O(n log n) with DBSCAN
- **Memory**: ~1MB per 10K transactions

---

## Expected Accuracy

| Timeline | Precision | Recall | F1 Score | Notes |
|----------|-----------|--------|----------|-------|
| Week 1   | 68%       | 65%    | 0.665    | Baseline, no feedback |
| Month 3  | 82%       | 78%    | 0.800    | With user feedback |
| Month 6  | 88%       | 84%    | 0.860    | Supervised learning active |
| Month 12 | 91%       | 87%    | 0.890    | Approaching ceiling |

**Improvement Mechanisms:**
1. User feedback loop (correct/incorrect patterns)
2. Parameter tuning based on performance metrics
3. Merchant database from aggregate user data
4. Semi-supervised learning layer

---

## Integration Points

### Category Rule Engine
When pattern is linked to category:
```python
CategoryRule(
    field="description",
    condition="contains",
    value=pattern.merchant_pattern,
    priority=100,  # High priority for recurring
    confidence=int(pattern.confidence_score * 100),
    amount_min=pattern.amount_min * 0.9,
    amount_max=pattern.amount_max * 1.1
)
```

### Budget Forecasting
Predict monthly expenses from active patterns:
```python
for pattern in active_patterns:
    if pattern.frequency == MONTHLY:
        prediction = predict_next_occurrence(pattern)
        if is_in_month(prediction.date, target_month):
            forecast.add(prediction)
```

### Transaction Categorization
New transaction → Check against patterns → Auto-categorize if match

---

## Limitations

1. **Data Quality Ceiling**: Poor transaction descriptions limit accuracy (~40-50%)
2. **Irregular Patterns**: Variable amounts/timing reduce confidence (~70% accuracy)
3. **Cold Start**: Need 3-4 months of data for reliable detection
4. **Computational Limits**: ~50K transactions per Lambda execution
5. **Asymptotic Accuracy**: Maximum ~92-95% for regular patterns

---

## Dependencies

```txt
scikit-learn>=1.3.0    # DBSCAN clustering
pandas>=2.0.0          # Data manipulation
numpy>=1.24.0          # Numerical operations
holidays>=0.35         # Working day detection
scipy>=1.11.0          # Statistical functions
```

---

## Real-World Examples

### Example 1: Netflix Subscription
```
Transactions: 12 occurrences, 15th of each month, $14.99
Pattern: DAY_OF_MONTH, day=15, confidence=0.96
Next: December 15, 2024
```

### Example 2: Salary (Last Thursday)
```
Transactions: Last Thursday of each month, $3,500
Pattern: LAST_WEEKDAY_OF_MONTH, dayOfWeek=3, confidence=0.94
Next: November 28, 2024
```

### Example 3: Gym (Variable Amount)
```
Transactions: 1st of month, $45-$55 (variable)
Pattern: DAY_OF_MONTH, day=1, confidence=0.78
Next: December 1, 2024, expected $50 ±$5
```

---

## References

- **ML Algorithm Details**: See `overview.md` for glossary and concepts
- **Implementation Patterns**: See `implementation-guide.md` for code patterns
- **Delivery Status**: See `delivery-phases.md` for current progress
- **DBSCAN**: https://scikit-learn.org/stable/modules/clustering.html#dbscan
- **Circular Encoding**: https://ianlondon.github.io/blog/encoding-cyclical-features-24hour-time/

---

**Document Version:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-02 | Initial design |
| 2.0 | 2025-11-07 | Consolidated design with temporal enhancements |

