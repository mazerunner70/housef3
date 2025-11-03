# ML-Based Recurring Charge Detection System - Design Document

**Version:** 1.0  
**Date:** November 2, 2025  
**Status:** Design Phase  
**Integration Design:** See `recurring-charge-integration-design.md` for implementation details

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Models](#data-models)
4. [Feature Engineering](#feature-engineering)
5. [Detection Algorithm](#detection-algorithm)
6. [API Design](#api-design)
7. [Integration Points](#integration-points)
8. [Implementation Plan](#implementation-plan)
9. [Performance Considerations](#performance-considerations)
10. [Future Enhancements](#future-enhancements)

---

## Overview

### Purpose

This system provides intelligent detection of recurring charges in financial transactions using machine learning techniques. It identifies patterns based on:

- **Temporal patterns**: Day of week, day of month, working days, weekends
- **Amount patterns**: Similar amounts with acceptable variance
- **Merchant patterns**: Similar transaction descriptions
- **Frequency patterns**: Daily, weekly, monthly, quarterly, etc.

### Goals

1. Automatically identify recurring charges (subscriptions, bills, salaries)
2. Predict next occurrence and expected amount
3. Generate high-confidence category suggestions
4. Support automatic categorization workflow
5. Provide budget forecasting capabilities

### Key Features

- **Unsupervised Learning**: Uses DBSCAN clustering to group similar transactions
- **Temporal Intelligence**: Detects first/last working day patterns, specific dates
- **Confidence Scoring**: Multi-factor confidence calculation (0.0-1.0)
- **Prediction Engine**: Forecasts next occurrence with date and amount
- **Integration Ready**: Works with existing category rule engine

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Transaction Stream                       │
│                  (DynamoDB / Query API)                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Feature Engineering Pipeline                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Temporal Features                                   │   │
│  │  • day_of_week, day_of_month, week_of_month         │   │
│  │  • is_weekend, is_working_day, is_holiday           │   │
│  │  • is_first_working_day, is_last_working_day        │   │
│  │  • days_since_month_start, days_until_month_end     │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Description Features                                │   │
│  │  • TF-IDF vectorization (50 features)               │   │
│  │  • Normalized merchant names                        │   │
│  │  • Description length, word count                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Amount Features                                     │   │
│  │  • Log-scaled amounts (normalized)                  │   │
│  │  • Amount sign (income vs expense)                  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Sequence Features                                   │   │
│  │  • Days since last similar transaction              │   │
│  │  • Interval statistics (mean, std, mode)            │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│           Recurring Pattern Detection Engine                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Stage 1: Temporal Clustering (DBSCAN)             │   │
│  │  • Groups transactions by similarity                │   │
│  │  • Features: amount, temporal, description          │   │
│  │  • Circular encoding for cyclical features          │   │
│  │  • Identifies noise/outliers automatically          │   │
│  └─────────────────────────────────────────────────────┘   │
│                        │                                     │
│                        ▼                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Stage 2: Recurrence Pattern Analysis              │   │
│  │  • Calculate interval statistics per cluster       │   │
│  │  • Detect frequency (daily→annually)               │   │
│  │  • Identify temporal patterns                      │   │
│  │  • Extract merchant identifiers                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                        │                                     │
│                        ▼                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Stage 3: Confidence Scoring & Validation          │   │
│  │  • Interval regularity (30% weight)                │   │
│  │  • Amount regularity (20% weight)                  │   │
│  │  • Sample size (20% weight)                        │   │
│  │  • Temporal consistency (30% weight)               │   │
│  │  • Filter by minimum confidence threshold          │   │
│  └─────────────────────────────────────────────────────┘   │
│                        │                                     │
│                        ▼                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Stage 4: Rule Generation                          │   │
│  │  • Create RecurringChargePattern objects           │   │
│  │  • Generate category rule suggestions              │   │
│  │  • Predict next occurrences                        │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Pattern Storage & Application                   │
│  • Store patterns in DynamoDB                               │
│  • Apply to new transactions automatically                  │
│  • Feed into category suggestion workflow                   │
│  • Generate budget forecasts                                │
└─────────────────────────────────────────────────────────────┘
```

### Component Overview

| Component | Purpose | Technology |
|-----------|---------|------------|
| **RecurringChargeFeatureService** | Feature engineering and extraction | scikit-learn, pandas, numpy |
| **RecurringChargeDetectionService** | Pattern detection and analysis | DBSCAN, statistical analysis |
| **RecurringChargePattern Model** | Data representation | Pydantic |
| **recurring_charge_operations Handler** | API endpoints | AWS Lambda |
| **DynamoDB Storage** | Pattern persistence | DynamoDB |

---

## Data Models

### RecurringChargePattern

Core model representing a detected recurring charge pattern.

```python
class RecurringChargePattern(BaseModel):
    """Represents a detected recurring charge pattern"""
    pattern_id: uuid.UUID
    user_id: str
    
    # Pattern identification
    merchant_pattern: str              # Regex or substring for matching
    frequency: RecurrenceFrequency    # DAILY, WEEKLY, MONTHLY, etc.
    temporal_pattern_type: TemporalPatternType
    
    # Temporal constraints
    day_of_week: Optional[int]        # 0=Monday, 6=Sunday
    day_of_month: Optional[int]       # 1-31
    tolerance_days: int               # ±N days (default: 2)
    
    # Amount constraints
    amount_mean: Decimal
    amount_std: Decimal
    amount_min: Decimal
    amount_max: Decimal
    amount_tolerance_pct: float       # ±% (default: 10.0)
    
    # Pattern metadata
    confidence_score: float           # 0.0-1.0
    transaction_count: int            # Number of matching transactions
    first_occurrence: int             # Timestamp (ms)
    last_occurrence: int              # Timestamp (ms)
    
    # ML features
    feature_vector: Optional[List[float]]
    cluster_id: Optional[int]
    
    # Associated category
    suggested_category_id: Optional[uuid.UUID]
    auto_categorize: bool             # Auto-apply without review
    
    # Status
    active: bool
    created_at: int
    updated_at: int
```

### RecurrenceFrequency Enum

```python
class RecurrenceFrequency(str, Enum):
    DAILY = "daily"                   # ~1 day intervals
    WEEKLY = "weekly"                 # ~7 day intervals
    BI_WEEKLY = "bi_weekly"           # ~14 day intervals
    SEMI_MONTHLY = "semi_monthly"     # ~15 day intervals (1st & 15th)
    MONTHLY = "monthly"               # ~30 day intervals
    BI_MONTHLY = "bi_monthly"         # ~60 day intervals
    QUARTERLY = "quarterly"           # ~90 day intervals
    SEMI_ANNUALLY = "semi_annually"   # ~182 day intervals
    ANNUALLY = "annually"             # ~365 day intervals
    IRREGULAR = "irregular"           # No clear pattern
```

### TemporalPatternType Enum

```python
class TemporalPatternType(str, Enum):
    DAY_OF_WEEK = "day_of_week"              # e.g., every Tuesday
    DAY_OF_MONTH = "day_of_month"            # e.g., 15th of each month
    FIRST_WORKING_DAY = "first_working_day"  # First business day
    LAST_WORKING_DAY = "last_working_day"    # Last business day
    FIRST_DAY_OF_MONTH = "first_day_of_month" # 1st of month
    LAST_DAY_OF_MONTH = "last_day_of_month"  # End of month
    WEEKEND = "weekend"                      # Saturday or Sunday
    WEEKDAY = "weekday"                      # Monday-Friday
    FLEXIBLE = "flexible"                    # No strict temporal pattern
```

### RecurringChargePrediction

```python
class RecurringChargePrediction(BaseModel):
    """Prediction for next occurrence of a recurring charge"""
    pattern_id: uuid.UUID
    next_expected_date: int           # Timestamp (ms)
    expected_amount: Decimal
    confidence: float                 # 0.0-1.0
    days_until_due: int
    amount_range: Dict[str, Decimal]  # min/max expected
```

---

## Feature Engineering

### Temporal Features

Comprehensive temporal feature extraction that captures cyclical patterns:

#### Basic Temporal Features

- `day_of_week`: 0-6 (Monday=0, Sunday=6)
- `day_of_month`: 1-31
- `week_of_month`: 1-5 (which week of the month)
- `month`: 1-12
- `year`: Full year

#### Boolean Temporal Features

- `is_weekend`: Saturday or Sunday
- `is_first_week`: First 7 days of month
- `is_last_week`: Last 7 days of month (day >= 24)
- `is_holiday`: US federal holiday (configurable per locale)
- `is_working_day`: Monday-Friday AND not a holiday

#### Advanced Temporal Features

- `is_first_working_day`: First business day of month
- `is_last_working_day`: Last business day of month
- `days_since_month_start`: 0-30
- `days_until_month_end`: 0-30

#### Sequence Features

- `days_since_last_transaction`: Days since previous similar transaction
- `mean_interval_days`: Average days between occurrences
- `std_interval_days`: Standard deviation of intervals
- `mode_interval_days`: Most common interval
- `regularity_score`: Inverse coefficient of variation (1.0 = perfectly regular)

### Circular Encoding

Cyclical features (day of week, day of month) are encoded using sine/cosine transformations to preserve their circular nature:

```python
# Day of month (handles month boundaries properly)
day_of_month_sin = sin(2π × day_of_month / 31)
day_of_month_cos = cos(2π × day_of_month / 31)

# Day of week (handles week boundaries)
day_of_week_sin = sin(2π × day_of_week / 7)
day_of_week_cos = cos(2π × day_of_week / 7)
```

This ensures that:
- Day 31 and Day 1 are close together
- Sunday and Monday are close together
- Distance metrics work correctly

### Description Features

- **TF-IDF Vectorization**: 50-dimensional vector representation
  - N-grams: 1-2 words
  - Captures merchant name patterns
  - Example: "NETFLIX SUBSCRIPTION" → [0.8, 0.2, 0.0, ...]

- **Normalized Description**: Uppercase, stripped
- **Description Length**: Character count
- **Word Count**: Number of words

### Amount Features

- **Log-Scaled Amount**: `log(1 + amount)` to reduce skew
- **Normalized Amount**: StandardScaler transformation
- **Amount Sign**: +1 (income) or -1 (expense)

### Feature Vector Construction

Final feature vector for clustering (concatenated):

```
[log_amount_normalized,           # 1 feature
 day_of_month_sin,                # 1 feature
 day_of_month_cos,                # 1 feature
 day_of_week_sin,                 # 1 feature
 day_of_week_cos,                 # 1 feature
 is_working_day,                  # 1 feature
 is_first_working_day,            # 1 feature
 is_last_working_day,             # 1 feature
 tfidf_vector]                    # 50 features

Total: ~60 features
```

---

## Detection Algorithm

### Overview

The detection algorithm uses a multi-stage pipeline:

1. **Feature Engineering**: Extract temporal, amount, and description features
2. **Clustering**: Group similar transactions using DBSCAN
3. **Pattern Analysis**: Analyze each cluster for recurring patterns
4. **Validation**: Calculate confidence scores and filter low-confidence patterns

### Stage 1: DBSCAN Clustering

**Why DBSCAN?**

- Doesn't require pre-specifying number of clusters
- Automatically identifies noise/outliers
- Handles clusters of varying density
- Works well with high-dimensional feature spaces

**Parameters:**

```python
eps = 0.5                           # Neighborhood radius
min_samples = max(3, n_samples * 0.01)  # 1% of dataset or minimum 3
metric = 'euclidean'
```

**Output:**

- Cluster assignments: [0, 0, 1, -1, 1, 2, ...] where -1 = noise

### Stage 2: Pattern Analysis Per Cluster

For each cluster with ≥3 transactions:

#### Frequency Detection

Calculate mean interval between transactions:

```python
intervals = transaction_dates.diff().dt.days
mean_interval = intervals.mean()
std_interval = intervals.std()

# Classify frequency
if 28 <= mean_interval <= 33:
    frequency = MONTHLY
elif 5 <= mean_interval <= 9:
    frequency = WEEKLY
# ... etc
```

#### Temporal Pattern Detection (Priority Order)

1. **First Working Day** (>70% match)
   - Check if transactions occur on first business day of month
   - Algorithm: For each month, find first non-weekend, non-holiday day

2. **Last Working Day** (>70% match)
   - Check if transactions occur on last business day of month
   - Algorithm: For each month, find last non-weekend, non-holiday day

3. **Specific Day of Month** (>60% consistency)
   - Find most common day of month
   - Example: 80% of transactions on day 15 → DAY_OF_MONTH pattern

4. **Specific Day of Week** (>60% consistency)
   - Find most common day of week
   - Example: 70% of transactions on Tuesday → DAY_OF_WEEK pattern

5. **Weekend Pattern** (>70% on Sat/Sun)
   - Transactions predominantly on weekends

6. **Weekday Pattern** (>80% on Mon-Fri)
   - Transactions predominantly on weekdays

7. **Flexible** (fallback)
   - No strong temporal pattern detected

#### Merchant Pattern Extraction

Extract common identifier from transaction descriptions:

```python
# Algorithm:
1. Normalize descriptions (uppercase, strip)
2. Find common prefix among all descriptions
3. If prefix >= 4 chars, use it
4. Otherwise, find longest common substring
5. Fallback: First word of first description
```

**Examples:**

- `["NETFLIX SUBSCRIPTION", "NETFLIX MONTHLY"]` → `"NETFLIX"`
- `["SPOTIFY PREM 123", "SPOTIFY PREM 456"]` → `"SPOTIFY PREM"`
- `["SALARY DEPOSIT ACH", "SALARY DEPOSIT"]` → `"SALARY DEPOSIT"`

#### Amount Pattern Analysis

```python
amounts = cluster_transactions['amount']

amount_mean = amounts.mean()
amount_std = amounts.std()
amount_min = amounts.min()
amount_max = amounts.max()

# Regularity score (inverse coefficient of variation)
amount_regularity = 1.0 / (1.0 + amount_std / (amount_mean + 1))
```

### Stage 3: Confidence Scoring

Multi-factor confidence calculation:

```python
confidence = (
    0.30 × interval_regularity +      # How consistent are intervals?
    0.20 × amount_regularity +         # How consistent are amounts?
    0.20 × sample_size_score +         # More samples = higher confidence
    0.30 × temporal_consistency        # How well does temporal pattern match?
)
```

**Component Definitions:**

- **interval_regularity**: `1.0 / (1.0 + std_interval / mean_interval)`
- **amount_regularity**: `1.0 / (1.0 + amount_std / amount_mean)`
- **sample_size_score**: `min(1.0, transaction_count / 12)`
- **temporal_consistency**: Percentage of transactions matching detected pattern

**Example Calculations:**

```
Netflix Subscription:
- 12 transactions over 12 months
- Mean interval: 30.2 days, Std: 1.5 days
- Interval regularity: 1.0 / (1.0 + 1.5/30.2) = 0.953
- Amount regularity: 1.0 / (1.0 + 0.0/14.99) = 1.000
- Sample size: 12/12 = 1.000
- Temporal consistency: 11/12 on day 15 = 0.917
- Confidence: 0.30×0.953 + 0.20×1.000 + 0.20×1.000 + 0.30×0.917 = 0.961
```

### Stage 4: Filtering & Output

```python
# Filter by minimum requirements
patterns = [
    pattern for pattern in detected_patterns
    if pattern.transaction_count >= 3
    and pattern.confidence_score >= 0.6
]

# Sort by confidence (descending)
patterns.sort(key=lambda p: p.confidence_score, reverse=True)
```

---

## API Design

### Endpoints

#### 1. Detect Recurring Charges

**Endpoint:** `POST /api/recurring-charges/detect`

**Description:** Analyzes user's transactions and detects recurring patterns.

**Request:**

```json
{
  "minOccurrences": 3,           // Optional, default: 3
  "minConfidence": 0.6,          // Optional, default: 0.6
  "startDate": 1672531200000,    // Optional, filter transactions
  "endDate": 1704067200000       // Optional, filter transactions
}
```

**Response:**

```json
{
  "patterns": [
    {
      "patternId": "550e8400-e29b-41d4-a716-446655440000",
      "merchantPattern": "NETFLIX",
      "frequency": "monthly",
      "temporalPattern": "day_of_month",
      "dayOfMonth": 15,
      "toleranceDays": 2,
      "confidence": 0.96,
      "transactionCount": 12,
      "amountMean": 14.99,
      "amountRange": {
        "min": 14.99,
        "max": 14.99
      },
      "firstOccurrence": 1672531200000,
      "lastOccurrence": 1701388800000,
      "nextPrediction": {
        "expectedDate": 1704067200000,
        "expectedAmount": 14.99,
        "daysUntil": 15,
        "confidence": 0.96
      },
      "suggestedCategoryId": null,
      "active": true
    },
    {
      "patternId": "650e8400-e29b-41d4-a716-446655440001",
      "merchantPattern": "SALARY DEPOSIT",
      "frequency": "monthly",
      "temporalPattern": "last_working_day",
      "confidence": 0.94,
      "transactionCount": 12,
      "amountMean": 5500.00,
      "amountRange": {
        "min": 5450.00,
        "max": 5550.00
      },
      "nextPrediction": {
        "expectedDate": 1704326400000,
        "expectedAmount": 5500.00,
        "daysUntil": 18,
        "confidence": 0.94
      }
    }
  ],
  "count": 2,
  "statistics": {
    "totalTransactionsAnalyzed": 1543,
    "clustersIdentified": 45,
    "patternsDetected": 12,
    "highConfidencePatterns": 2
  }
}
```

#### 2. Get Recurring Patterns

**Endpoint:** `GET /api/recurring-charges/patterns`

**Description:** Retrieve previously detected recurring charge patterns.

**Query Parameters:**
- `active`: boolean (filter by active status)
- `minConfidence`: float (filter by minimum confidence)

**Response:**

```json
{
  "patterns": [...],
  "count": 12
}
```

#### 3. Update Pattern

**Endpoint:** `PATCH /api/recurring-charges/patterns/{patternId}`

**Description:** Update a recurring charge pattern (e.g., deactivate, link to category).

**Request:**

```json
{
  "active": false,
  "suggestedCategoryId": "750e8400-e29b-41d4-a716-446655440002",
  "autoCategorize": true
}
```

**Response:**

```json
{
  "success": true,
  "pattern": {...}
}
```

#### 4. Predict Next Occurrences

**Endpoint:** `GET /api/recurring-charges/predictions`

**Description:** Get predictions for all upcoming recurring charges.

**Query Parameters:**
- `daysAhead`: int (default: 30, predict next N days)

**Response:**

```json
{
  "predictions": [
    {
      "patternId": "550e8400-e29b-41d4-a716-446655440000",
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

#### 5. Apply Pattern to Category

**Endpoint:** `POST /api/recurring-charges/patterns/{patternId}/apply-category`

**Description:** Link pattern to a category and optionally auto-categorize matching transactions.

**Request:**

```json
{
  "categoryId": "850e8400-e29b-41d4-a716-446655440003",
  "autoCategorize": true,
  "applyToExisting": true  // Apply to existing transactions
}
```

**Response:**

```json
{
  "success": true,
  "transactionsUpdated": 12,
  "ruleCreated": true
}
```

---

## Integration Points

### 1. Category Rule Engine Integration

Recurring patterns can automatically generate category rules:

```python
# When pattern is linked to category, create rule:
rule = CategoryRule(
    ruleId=f"recurring_{pattern.pattern_id}",
    fieldToMatch="description",
    condition=MatchCondition.CONTAINS,
    value=pattern.merchant_pattern,
    priority=100,  # High priority for recurring charges
    confidence=int(pattern.confidence_score * 100),
    enabled=True,
    autoSuggest=True
)

# Add amount constraint
rule.amount_min = pattern.amount_min * 0.9  # 10% tolerance
rule.amount_max = pattern.amount_max * 1.1
```

### 2. Transaction Categorization Workflow

```
New Transaction Arrives
    ↓
Check Against Recurring Patterns
    ↓
Match Found? → Yes → Auto-categorize (if enabled)
    ↓                     ↓
    No               Add to category with high confidence
    ↓
Continue with normal rule matching
```

### 3. Budget Forecasting

Recurring patterns enable accurate budget forecasting:

```python
def forecast_month(patterns: List[RecurringChargePattern], month: int) -> Dict:
    """Forecast expenses for a given month"""
    predictions = []
    total = 0.0
    
    for pattern in patterns:
        if pattern.frequency in [MONTHLY, BI_WEEKLY, WEEKLY]:
            prediction = predict_next_occurrence(pattern)
            if is_in_month(prediction.next_expected_date, month):
                predictions.append(prediction)
                total += float(prediction.expected_amount)
    
    return {
        'month': month,
        'predictions': predictions,
        'total_expected': total,
        'confidence': calculate_aggregate_confidence(predictions)
    }
```

### 4. Analytics Integration

Recurring patterns feed into analytics:

- **Spending Trends**: Track how recurring charges change over time
- **Subscription Management**: List all subscriptions with amounts
- **Budget Variance**: Compare actual vs predicted recurring charges
- **Savings Opportunities**: Identify redundant subscriptions

### 5. User Notification System

```python
# Notify user of upcoming charges
upcoming = get_predictions(days_ahead=7)
if upcoming:
    notify_user(
        title="Upcoming Recurring Charges",
        message=f"{len(upcoming)} charges totaling ${sum(p.expected_amount for p in upcoming):.2f} in next 7 days",
        charges=upcoming
    )
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1-2)

**Backend:**

1. **Create Models** (`backend/src/models/recurring_charge.py`)
   - RecurringChargePattern
   - RecurrenceFrequency enum
   - TemporalPatternType enum
   - RecurringChargePrediction

2. **DynamoDB Schema**
   - Create RecurringChargePatterns table
   - Set up GSI for pattern lookups
   - Add indices for userId queries

3. **Dependencies**
   ```bash
   pip install scikit-learn pandas numpy holidays
   ```

4. **Performance Monitoring**
   - Add processing time logging for each stage:
     - Transaction fetch time
     - Feature extraction time
     - Clustering time
     - Pattern analysis time
     - Total execution time
   - Log transaction count per execution
   - Monitor memory usage patterns

### Phase 2: Feature Engineering (Week 2-3)

**Backend:**

1. **RecurringChargeFeatureService** (`backend/src/services/recurring_charge_feature_service.py`)
   - Implement temporal feature extraction
   - Implement working day detection
   - Implement circular encoding
   - Implement TF-IDF vectorization
   - Implement feature vector construction

2. **Unit Tests**
   - Test temporal feature extraction
   - Test working day detection (with holidays)
   - Test circular encoding correctness
   - Test feature vector dimensions

### Phase 3: Detection Algorithm (Week 3-4)

**Backend:**

1. **RecurringChargeDetectionService** (`backend/src/services/recurring_charge_detection_service.py`)
   - Implement DBSCAN clustering
   - Implement pattern analysis per cluster
   - Implement frequency detection
   - Implement temporal pattern detection
   - Implement merchant extraction
   - Implement confidence scoring
   - Implement prediction engine

2. **Integration Tests**
   - Test with synthetic data (known patterns)
   - Test with real transaction samples
   - Validate confidence scores
   - Test edge cases (irregular patterns, sparse data)

### Phase 4: API Layer (Week 4-5)

**Backend:**

1. **Handler Implementation** (`backend/src/handlers/recurring_charge_operations.py`)
   - detect_recurring_charges_handler
   - get_patterns_handler
   - update_pattern_handler
   - predict_occurrences_handler
   - apply_pattern_to_category_handler

2. **API Gateway Configuration**
   - Add routes to `infrastructure/`
   - Configure CORS
   - Set up authentication

3. **DB Utils**
   - Add functions to save/retrieve patterns
   - Add pattern update functions

### Phase 5: Frontend Integration (Week 5-6)

**Frontend:**

1. **Services** (`frontend/src/services/recurringChargeService.ts`)
   - API client functions
   - Type definitions (TypeScript interfaces)

2. **Components**
   - RecurringChargesList
   - RecurringChargeCard
   - PatternConfidenceBadge
   - NextOccurrencePrediction
   - PatternToCategoryLinker

3. **Views**
   - RecurringChargesView (main page)
   - PatternDetailView (drill-down)

4. **Integration**
   - Add to transaction sidebar
   - Show pattern matches in transaction list
   - Add to category management

### Phase 6: Testing & Refinement (Week 6-7)

1. **End-to-End Testing**
   - Test full workflow with real user data
   - Validate pattern detection accuracy
   - Test prediction accuracy over time

2. **Performance Optimization**
   - Profile detection algorithm
   - Optimize feature extraction
   - Add caching for patterns

3. **User Experience**
   - Refine confidence thresholds
   - Improve merchant extraction
   - Add user feedback mechanism

### Phase 7: Documentation & Launch (Week 7-8)

1. **Documentation**
   - API documentation
   - User guide
   - Admin guide

2. **Monitoring**
   - Add CloudWatch metrics
   - Add error tracking
   - Add usage analytics

3. **Gradual Rollout**
   - Beta test with select users
   - Gather feedback
   - Full launch

---

## Performance Considerations

### Scalability

**Transaction Volume:**

- **Target**: Handle 10,000+ transactions per user
- **Clustering**: O(n log n) with DBSCAN
- **Feature Extraction**: O(n) linear time
- **Memory**: ~1MB per 10K transactions

**Optimization Strategies:**

1. **Batch Processing**: Process transactions in batches of 1000
2. **Caching**: Cache feature vectors for unchanged transactions
3. **Incremental Updates**: Re-detect only when new transactions added
4. **Sampling**: For users with >50K transactions, sample intelligently

### Lambda Considerations

**Execution Time:**

- Feature extraction: ~1-2 seconds per 1000 transactions
- Clustering: ~2-3 seconds per 1000 transactions
- Pattern analysis: ~0.5 seconds per cluster
- **Total**: ~5-10 seconds for 1000 transactions

**Memory:**

- Base: 512 MB
- With scikit-learn: 1024 MB recommended
- Peak usage: ~800 MB for 10K transactions

**Timeout:**

- Recommended: 30 seconds
- Maximum: 60 seconds for large datasets

### Database Performance

**DynamoDB:**

```
Table: RecurringChargePatterns
- Partition Key: userId
- Sort Key: patternId
- GSI: patternId (for direct lookups)

Estimated Storage: ~2KB per pattern
Read Capacity: 5 RCU (standard usage)
Write Capacity: 2 WCU (pattern updates are infrequent)
```

**Query Patterns:**

1. Get all patterns for user: Query on PK (userId)
2. Get specific pattern: Query on GSI (patternId)
3. Update pattern: UpdateItem

### Caching Strategy

```python
# Cache detected patterns in memory
pattern_cache = {
    'user_123': {
        'patterns': [...],
        'last_updated': timestamp,
        'transaction_count': 1543
    }
}

# Invalidate cache when:
# - New transactions imported (>10% increase)
# - Manual pattern update
# - 24 hours elapsed
```

---

## Iterative Improvement & Limitations

### Can This System Learn and Improve?

**Yes, with qualifications.** The current design is **unsupervised** (DBSCAN clustering), but it can improve significantly through **supervised feedback loops** and **parameter tuning**. However, there are **fundamental limits** based on data quality and pattern complexity.

### Performance Improvement Pathways

#### 1. **User Feedback Loop (Highest Impact)**

The system can dramatically improve by learning from user corrections:

```python
class PatternFeedback(BaseModel):
    """User feedback on pattern detection accuracy"""
    pattern_id: uuid.UUID
    feedback_type: str  # 'correct', 'incorrect', 'missed_transaction', 'false_positive'
    user_correction: Optional[Dict]  # What the user changed
    transaction_id: Optional[uuid.UUID]
    timestamp: int

# Iterative improvement algorithm:
def retrain_with_feedback(patterns: List[RecurringChargePattern], 
                         feedback: List[PatternFeedback]) -> Dict[str, float]:
    """
    Adjust algorithm parameters based on user feedback
    
    Improvements:
    1. Tune DBSCAN epsilon based on false negative rate
    2. Adjust confidence weights based on user corrections
    3. Learn merchant pattern variations from corrections
    4. Refine temporal pattern detection thresholds
    """
    
    # Calculate performance metrics from feedback
    correct_detections = sum(1 for f in feedback if f.feedback_type == 'correct')
    false_positives = sum(1 for f in feedback if f.feedback_type == 'incorrect')
    false_negatives = sum(1 for f in feedback if f.feedback_type == 'missed_transaction')
    
    precision = correct_detections / (correct_detections + false_positives)
    recall = correct_detections / (correct_detections + false_negatives)
    
    # Adjust parameters
    adjustments = {}
    
    # If too many false positives → increase confidence threshold
    if precision < 0.7:
        adjustments['min_confidence'] = current_threshold + 0.05
        adjustments['min_occurrences'] = current_min + 1
    
    # If too many false negatives → relax clustering parameters
    if recall < 0.7:
        adjustments['dbscan_eps'] = current_eps * 1.1
        adjustments['min_samples'] = max(2, current_min_samples - 1)
    
    return adjustments
```

**Expected Improvement:**
- **Week 1**: Baseline accuracy ~70%
- **Month 1**: With 100+ feedback events → ~82% accuracy
- **Month 3**: With 500+ feedback events → ~90% accuracy
- **Month 6**: With 2000+ feedback events → ~94% accuracy (approaching ceiling)

#### 2. **Semi-Supervised Learning Enhancement**

Add a supervised learning layer that learns from confirmed patterns:

```python
from sklearn.ensemble import RandomForestClassifier

class SupervisedPatternClassifier:
    """Learn from user-confirmed patterns to improve detection"""
    
    def __init__(self):
        self.classifier = RandomForestClassifier(n_estimators=100)
        self.is_trained = False
    
    def train_on_confirmed_patterns(self, 
                                   confirmed_patterns: List[RecurringChargePattern],
                                   all_transactions: List[Transaction]):
        """
        Train classifier on confirmed patterns
        
        Features: Same 60-dimensional feature vector from DBSCAN
        Labels: 1 if transaction belongs to recurring pattern, 0 otherwise
        """
        X_train = []
        y_train = []
        
        for pattern in confirmed_patterns:
            # Get transactions matching this pattern
            matching_txns = find_matching_transactions(pattern, all_transactions)
            
            for txn in all_transactions:
                features = extract_features(txn)
                label = 1 if txn in matching_txns else 0
                X_train.append(features)
                y_train.append(label)
        
        self.classifier.fit(X_train, y_train)
        self.is_trained = True
    
    def predict_recurring_probability(self, transaction: Transaction) -> float:
        """Predict probability that transaction is part of recurring pattern"""
        if not self.is_trained:
            return 0.5  # Neutral
        
        features = extract_features(transaction)
        proba = self.classifier.predict_proba([features])[0][1]
        return proba
```

**Improvement Mechanism:**
- Start with unsupervised DBSCAN (no training data needed)
- As users confirm/reject patterns, collect labeled data
- After 50+ confirmed patterns, train supervised classifier
- Use classifier to boost confidence scores or filter candidates
- Retrain weekly as more feedback accumulates

**Expected Improvement:**
- Reduces false positives by 30-40%
- Increases confidence calibration accuracy
- Better handles edge cases users care about

#### 3. **Parameter Optimization (Medium Impact)**

Continuously tune algorithm parameters based on aggregate performance:

```python
# A/B test different parameter sets
parameter_experiments = [
    {'name': 'conservative', 'dbscan_eps': 0.4, 'min_confidence': 0.7},
    {'name': 'balanced', 'dbscan_eps': 0.5, 'min_confidence': 0.6},
    {'name': 'aggressive', 'dbscan_eps': 0.6, 'min_confidence': 0.5}
]

# Track performance per parameter set
def evaluate_parameter_set(params: Dict, users: List[str]) -> Dict:
    """
    Run detection with params on sample of users
    Measure: precision, recall, user satisfaction
    """
    results = []
    for user in users:
        patterns = detect_with_params(user, params)
        feedback = get_user_feedback(user, patterns)
        metrics = calculate_metrics(patterns, feedback)
        results.append(metrics)
    
    return aggregate_metrics(results)

# Select best performing parameters
best_params = max(parameter_experiments, 
                 key=lambda p: evaluate_parameter_set(p, sample_users))
```

**Optimization Areas:**
- `dbscan_eps`: Clustering neighborhood radius (critical)
- `min_samples`: Minimum cluster size
- `min_confidence`: Threshold for showing patterns
- `tolerance_days`: How much date variance to allow
- `amount_tolerance_pct`: How much amount variance to allow
- Confidence score weights (0.30, 0.20, 0.20, 0.30)

**Expected Improvement:**
- 5-10% accuracy gain through optimal parameters
- Reduced over-clustering or under-clustering
- Better precision/recall balance

#### 4. **Merchant Database Expansion (Low-Medium Impact)**

Build merchant database from aggregate user data:

```python
def build_merchant_database_from_users():
    """
    Learn common merchant patterns across all users
    
    Algorithm:
    1. For each confirmed recurring pattern across all users
    2. Extract merchant name and category
    3. Build frequency map: merchant → category
    4. Use for pattern recognition in new users
    """
    merchant_category_map = defaultdict(Counter)
    
    for pattern in all_confirmed_patterns:
        merchant = normalize_merchant_name(pattern.merchant_pattern)
        category = pattern.suggested_category_id
        merchant_category_map[merchant][category] += 1
    
    # Filter to high-confidence mappings
    merchant_db = {}
    for merchant, categories in merchant_category_map.items():
        total = sum(categories.values())
        if total >= 10:  # At least 10 users
            top_category, count = categories.most_common(1)[0]
            confidence = count / total
            if confidence >= 0.7:  # 70% agreement
                merchant_db[merchant] = {
                    'category': top_category,
                    'confidence': confidence,
                    'sample_size': total
                }
    
    return merchant_db
```

**Expected Improvement:**
- Cold-start problem: Better detection for new users
- Category suggestions improve from ~60% → ~85% accuracy
- Faster pattern recognition

#### 5. **Feature Engineering Refinement (Medium Impact)**

Add new features based on observed patterns:

```python
# Additional features to add:
def extract_advanced_features(transaction: Transaction, 
                              user_history: List[Transaction]) -> np.ndarray:
    """
    Add features that improve pattern detection
    """
    basic_features = extract_features(transaction)
    
    # Time-series features
    rolling_avg_amount = calculate_rolling_average(transaction, user_history, window=30)
    amount_z_score = (transaction.amount - rolling_avg_amount) / rolling_std
    
    # Merchant-specific features
    merchant_transaction_count = count_similar_merchants(transaction, user_history)
    merchant_avg_interval = calculate_merchant_interval(transaction, user_history)
    
    # Contextual features
    hour_of_day = extract_hour(transaction.date)  # Some subscriptions charge at specific times
    day_of_year = extract_day_of_year(transaction.date)  # Annual patterns
    
    advanced_features = np.array([
        amount_z_score,
        merchant_transaction_count,
        merchant_avg_interval,
        hour_of_day,
        day_of_year
    ])
    
    return np.concatenate([basic_features, advanced_features])
```

**Expected Improvement:**
- 5-15% accuracy improvement
- Better handling of variable amounts
- Improved annual/quarterly pattern detection

### Fundamental Limitations

Despite iterative improvements, the system has inherent limits:

#### 1. **Data Quality Ceiling** (Hard Limit)

**Problem:** If transaction descriptions are poor, no ML can fix it.

```
Bad descriptions (common with some banks):
- "POS PURCHASE 12345"
- "CARD TRANSACTION"
- "ONLINE PAYMENT"

Result: Cannot cluster meaningfully → patterns undetectable
```

**Mitigation:**
- Encourage users to use banks with good transaction data
- Allow manual merchant name enrichment
- Use amount + temporal patterns when description fails
- Partner with Plaid/financial aggregators for enhanced data

**Hard Limit:** ~40-50% accuracy with poor data quality

#### 2. **Irregular Pattern Ceiling** (Soft Limit)

**Problem:** Some charges are legitimately irregular.

```
Examples:
- Utilities (amount varies by usage: $50-$200)
- Freelance income (timing varies by project)
- Medical bills (irregular timing and amounts)
- Variable subscriptions (Uber, DoorDash)

Result: Low confidence scores, frequent false positives
```

**Current Handling:**
- Set `frequency = IRREGULAR`
- Lower confidence scores
- Require more occurrences for detection
- Allow wider tolerance ranges

**Soft Limit:** ~70% accuracy for irregular patterns (vs 95% for regular)

#### 3. **Cold Start Problem** (Temporary Limit)

**Problem:** New users have no history.

```
User with 0-2 months of data:
- Most patterns undetectable (need ≥3 occurrences)
- Cannot detect monthly patterns until month 4
- Cannot detect quarterly until month 7+

Result: Low recall for new users
```

**Mitigation:**
- Use merchant database from other users (collective learning)
- Start with lower confidence thresholds
- Gradually increase confidence as data accumulates
- Pre-suggest common patterns (Netflix, Spotify, etc.)

**Time to Useful:** 3-4 months for most patterns

#### 4. **Computational Complexity Ceiling** (Scalability Limit)

**Problem:** Algorithm doesn't scale infinitely.

```
DBSCAN Complexity: O(n log n) with spatial indexing
                   O(n²) in worst case

For n = 100,000 transactions:
- Memory: ~2-3 GB
- Time: ~60-120 seconds
- Lambda: Would timeout (60s max)

Result: Cannot process entire history for power users
```

**Mitigation:**
- Sample recent transactions (last 2-3 years)
- Process incrementally (detect once, update periodically)
- Use more efficient clustering (MiniBatch K-Means as alternative)
- Consider moving to EC2/Fargate for large jobs

**Hard Limit:** ~50,000 transactions per detection run in Lambda

#### 5. **Confidence Calibration Ceiling** (Asymptotic)

**Problem:** Confidence scores can only be so accurate.

```
Current confidence formula is heuristic, not probabilistic.

Example:
- System says 95% confident
- Actual accuracy: 88%
- Calibration error: 7%

Result: Users trust system more/less than warranted
```

**Solution: Proper Calibration**

```python
from sklearn.calibration import CalibratedClassifierCV

def calibrate_confidence_scores(patterns: List[RecurringChargePattern],
                                feedback: List[PatternFeedback]):
    """
    Learn true probability mapping using isotonic regression
    
    Maps: predicted_confidence → actual_accuracy
    """
    X = np.array([p.confidence_score for p in patterns])
    y = np.array([1 if is_correct(p, feedback) else 0 for p in patterns])
    
    calibrator = CalibratedClassifierCV(method='isotonic')
    calibrator.fit(X.reshape(-1, 1), y)
    
    # Now can map raw confidence → calibrated probability
    return calibrator
```

**Expected Improvement:**
- Week 1: Calibration error ~15%
- Month 3: Calibration error ~8%
- Month 6: Calibration error ~5%
- **Asymptotic limit:** ~3-5% (due to inherent variance)

### Measurement & Monitoring

To track improvement over time:

```python
class PerformanceMetrics:
    """Track system performance over time"""
    
    def __init__(self):
        self.metrics_history = []
    
    def calculate_weekly_metrics(self, 
                                patterns: List[RecurringChargePattern],
                                feedback: List[PatternFeedback]) -> Dict:
        """
        Weekly performance snapshot
        """
        # Classification metrics
        precision = calculate_precision(patterns, feedback)
        recall = calculate_recall(patterns, feedback)
        f1_score = 2 * (precision * recall) / (precision + recall)
        
        # Confidence calibration
        calibration_error = calculate_calibration_error(patterns, feedback)
        
        # User experience
        user_satisfaction = calculate_satisfaction(feedback)
        false_positive_rate = calculate_fpr(patterns, feedback)
        false_negative_rate = calculate_fnr(patterns, feedback)
        
        # Business impact
        auto_categorization_rate = calculate_auto_cat_rate(patterns)
        forecast_accuracy = calculate_forecast_accuracy(patterns, actual_transactions)
        
        metrics = {
            'week': current_week,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'calibration_error': calibration_error,
            'user_satisfaction': user_satisfaction,
            'false_positive_rate': false_positive_rate,
            'false_negative_rate': false_negative_rate,
            'auto_categorization_rate': auto_categorization_rate,
            'forecast_accuracy': forecast_accuracy,
            'patterns_detected': len(patterns),
            'feedback_count': len(feedback)
        }
        
        self.metrics_history.append(metrics)
        return metrics
    
    def plot_improvement_curve(self):
        """Visualize improvement over time"""
        weeks = [m['week'] for m in self.metrics_history]
        f1_scores = [m['f1_score'] for m in self.metrics_history]
        
        # Shows learning curve: should increase and plateau
        plt.plot(weeks, f1_scores)
        plt.xlabel('Weeks Since Launch')
        plt.ylabel('F1 Score')
        plt.title('Pattern Detection Accuracy Over Time')
```

### Expected Performance Trajectory

```
Timeline         | Precision | Recall | F1 Score | Notes
-----------------|-----------|--------|----------|------------------
Week 1 (Launch)  | 68%       | 65%    | 0.665    | Baseline, no feedback
Week 4           | 74%       | 70%    | 0.720    | Initial tuning
Month 3          | 82%       | 78%    | 0.800    | Supervised learning active
Month 6          | 88%       | 84%    | 0.860    | Merchant DB built
Month 12         | 91%       | 87%    | 0.890    | Approaching ceiling
Month 18+        | 92%       | 88%    | 0.900    | Asymptotic limit
```

**Ceiling Factors:**
1. Data quality limitations (cannot exceed data quality)
2. Inherently irregular patterns (~20% of charges)
3. Edge cases that look recurring but aren't
4. User behavioral changes (moves, job changes)

### Actionable Improvement Strategy

**Immediate (Month 1-3):**
1. ✅ Implement feedback collection UI
2. ✅ Track precision/recall weekly
3. ✅ A/B test parameter sets
4. ✅ Build parameter adjustment automation

**Short-term (Month 3-6):**
1. ✅ Add semi-supervised learning layer
2. ✅ Implement confidence calibration
3. ✅ Build merchant database from user data
4. ✅ Add advanced features (rolling averages, etc.)

**Long-term (Month 6-12):**
1. ✅ Deploy full supervised ML model (Random Forest → XGBoost)
2. ✅ Implement active learning (ask users about uncertain cases)
3. ✅ Add time-series forecasting (LSTM/Prophet)
4. ✅ Cross-user pattern learning

### When to Declare Success

The system is "successful" when:

1. **F1 Score ≥ 0.85** (Good balance of precision/recall)
2. **User Satisfaction ≥ 4.0/5.0** (Users find it helpful)
3. **False Positive Rate ≤ 10%** (Low annoyance factor)
4. **Auto-categorization Rate ≥ 70%** (Saves user time)
5. **Forecast Accuracy ≥ 80%** (Useful for budgeting)

If after 6 months with active improvements these targets aren't met:
- Re-evaluate algorithm choice (try different clustering methods)
- Check data quality (might need better data sources)
- Reassess user needs (maybe pattern detection isn't the right approach)

### Summary: Can It Improve?

**Yes, significantly:**
- ✅ User feedback loop: 70% → 90% accuracy
- ✅ Parameter tuning: +5-10% improvement
- ✅ Supervised learning: +10-15% improvement
- ✅ Merchant database: Better cold-start performance
- ✅ Feature engineering: +5-15% improvement

**But with limits:**
- ⚠️ Data quality ceiling (cannot exceed ~95% with perfect data)
- ⚠️ Irregular patterns ceiling (~70% accuracy for variable charges)
- ⚠️ Cold start requires 3-4 months of data
- ⚠️ Computational limits at ~50K transactions
- ⚠️ Confidence calibration ceiling at ~95% accuracy

**Bottom line:** Expect continuous improvement from 70% → 90% over 6-12 months, with asymptotic limit around 92-95% for regular patterns.

---

## Future Enhancements

### Phase 2 Features

1. **Machine Learning Enhancements**
   - Use LSTM/RNN for time series prediction
   - Implement anomaly detection (missed payments)
   - Add semi-supervised learning with user feedback

2. **Advanced Pattern Types**
   - Bi-monthly patterns (every other month)
   - Quarterly with specific months (Q1, Q4)
   - Complex patterns (weekday + specific week)

3. **Smart Notifications**
   - Alert on missed recurring charges
   - Notify of amount changes (price increases)
   - Warn of duplicate subscriptions

4. **Budget Integration**
   - Auto-create budget items from patterns
   - Track budget vs actual for recurring charges
   - Forecast budget impact

5. **Merchant Intelligence**
   - Build merchant database from user data
   - Crowd-source category suggestions
   - Detect merchant rebranding

### Phase 3 Features

1. **Subscription Management**
   - Dedicated subscription tracking view
   - Cancel subscription reminders
   - Subscription comparison (is this too expensive?)

2. **Payment Prediction**
   - Predict exact payment date with ML
   - Account for variable working days
   - Handle regional holidays

3. **Cash Flow Forecasting**
   - Predict account balance 30/60/90 days out
   - Identify potential overdrafts
   - Optimize payment timing

4. **Collaborative Filtering**
   - "Users with similar patterns also categorize as..."
   - Suggest category based on crowd data
   - Improve pattern detection with collective learning

---

## Appendix

### A. Algorithm Complexity Analysis

| Operation | Time Complexity | Space Complexity |
|-----------|----------------|------------------|
| Feature Extraction | O(n) | O(n × f) where f = feature count |
| DBSCAN Clustering | O(n log n) | O(n) |
| Pattern Analysis | O(k × m) | O(k) where k = clusters, m = avg cluster size |
| Confidence Scoring | O(k) | O(1) per pattern |
| **Total** | **O(n log n)** | **O(n × f)** |

### B. Confidence Score Examples

| Pattern Type | Interval Reg | Amount Reg | Sample Size | Temporal Con | Final Confidence |
|-------------|--------------|------------|-------------|--------------|------------------|
| Netflix (perfect) | 0.95 | 1.00 | 1.00 | 0.92 | **0.96** |
| Salary (variable date) | 0.92 | 0.98 | 1.00 | 0.85 | **0.93** |
| Coffee (irregular) | 0.45 | 0.60 | 0.75 | 0.40 | **0.52** |
| Gym (monthly, varies) | 0.88 | 0.85 | 0.83 | 0.88 | **0.86** |

### C. Python Dependencies

```txt
# requirements.txt additions
scikit-learn>=1.3.0
pandas>=2.0.0
numpy>=1.24.0
holidays>=0.35
scipy>=1.11.0
```

### D. Testing Strategy

**Unit Tests:**
- Test each feature engineering function
- Test circular encoding correctness
- Test pattern detection logic
- Test confidence scoring formula

**Integration Tests:**
- Test full detection pipeline
- Test with synthetic datasets (known patterns)
- Test edge cases (sparse data, noise)

**End-to-End Tests:**
- Test API endpoints
- Test with real transaction data
- Validate accuracy over time

**Performance Tests:**
- Benchmark with 1K, 10K, 50K transactions
- Measure memory usage
- Measure execution time

### E. Monitoring Metrics

**CloudWatch Metrics:**
- Detection execution time (per user)
- Pattern count per user
- Confidence score distribution
- API latency
- Error rates
- Cache hit rates

**Business Metrics:**
- Pattern detection accuracy (user feedback)
- Category auto-application rate
- User engagement with recurring charge features
- Budget forecast accuracy

---

## Glossary

- **DBSCAN**: Density-Based Spatial Clustering of Applications with Noise
- **TF-IDF**: Term Frequency-Inverse Document Frequency (text vectorization)
- **Circular Encoding**: Sine/cosine transformation for cyclical features
- **Feature Vector**: Numerical representation of transaction attributes
- **Confidence Score**: 0.0-1.0 score indicating pattern reliability
- **Working Day**: Monday-Friday, excluding holidays
- **Tolerance**: Acceptable deviation (days or percentage)
- **Regularity Score**: Inverse coefficient of variation

---

## References

1. Ester, M., et al. (1996). "A density-based algorithm for discovering clusters"
2. scikit-learn Documentation: https://scikit-learn.org/
3. pandas Documentation: https://pandas.pydata.org/
4. AWS Lambda Best Practices: https://docs.aws.amazon.com/lambda/

---

**Document Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-02 | System | Initial design document |
| 1.1 | 2025-11-02 | System | Added "Iterative Improvement & Limitations" section |


