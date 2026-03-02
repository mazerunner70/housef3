# Recurring Charge Detection - ML Architecture

**Version:** 2.0  
**Date:** November 7, 2025  
**Status:** Active

## Overview

ML-based system architecture for automatic detection of recurring charges using unsupervised learning (DBSCAN clustering).

See [ADR-0004](./adr/adr-0004-unsupervised-ml-recurring-charge-detection.md) for the decision rationale.

---

## Architecture Components

### 1. Feature Engineering Pipeline

**Service:** `RecurringChargeFeatureService`  
**Input:** Transaction list (date, amount, description, account metadata)  
**Output:** 67-dimensional feature vectors

#### Feature Breakdown

**Temporal Features (17 dimensions)**
- Circular encoding (8 features):
  - Day of week: `sin(2π × day/7)`, `cos(2π × day/7)`
  - Day of month: `sin(2π × day/31)`, `cos(2π × day/31)`
  - Month position: `sin(2π × normalized_pos)`, `cos(2π × normalized_pos)`
  - Week of month: `sin(2π × week/5)`, `cos(2π × week/5)`
- Boolean flags (8 features):
  - Working day (Mon-Fri, non-holiday)
  - First working day of month
  - Last working day of month
  - First weekday of month (by day-of-week)
  - Last weekday of month
  - Weekend (Sat/Sun)
- Position (1 feature):
  - Normalized day position in month (handles variable month lengths)

**Amount Features (1 dimension)**
- Log-scaled and normalized amount: `log(|amount| + 1) / normalization_factor`

**Description Features (49 dimensions)**
- TF-IDF vectorization of transaction descriptions
- Max features: 50, but reduced to 49 to reach exact 67 total
- Captures merchant name patterns

#### Circular Encoding Rationale

Temporal features are cyclical - day 31 should be close to day 1, Sunday close to Monday:

```python
# Without circular encoding (linear)
day_of_week = [0, 1, 2, 3, 4, 5, 6]  # Sunday (6) far from Monday (0)

# With circular encoding
day_of_week_sin = sin(2π × day/7)
day_of_week_cos = cos(2π × day/7)
# Sunday and Monday are now close in 2D space
```

### 2. Clustering Algorithm

**Algorithm:** DBSCAN (Density-Based Spatial Clustering of Applications with Noise)  
**Library:** scikit-learn 1.3.0+

#### Parameters

```python
eps = 0.5                          # Neighborhood radius
min_samples = max(3, n_samples × 0.01)  # Adaptive minimum cluster size
metric = 'euclidean'               # Distance metric
algorithm = 'auto'                 # Automatic algorithm selection
```

#### Why DBSCAN?

1. **No Pre-Specified Cluster Count**: We don't know how many recurring patterns exist
2. **Noise Detection**: Automatically identifies one-off transactions (cluster label = -1)
3. **Variable Density**: Handles patterns with different occurrence frequencies
4. **Arbitrary Shapes**: Doesn't assume spherical clusters like K-means

#### Complexity

- **Time:** O(n log n) with spatial indexing
- **Space:** O(n) for feature vectors
- **Scalability:** Tested up to 10,000 transactions per user

### 3. Pattern Analysis

**Service:** `RecurringChargeDetectionService`

For each cluster with ≥3 transactions:

#### A. Frequency Detection

Calculate mean interval between consecutive transactions:

```python
intervals = [days_between(txn[i+1], txn[i]) for i in range(len(txns)-1)]
mean_interval = mean(intervals)
std_interval = std(intervals)
```

Map to frequency type:

| Mean Interval | Frequency | Tolerance |
|--------------|-----------|-----------|
| ~1 day | DAILY | ±1 day |
| ~7 days | WEEKLY | ±2 days |
| ~14 days | BI_WEEKLY | ±2 days |
| ~15 days | SEMI_MONTHLY | ±3 days |
| ~30 days | MONTHLY | ±3 days |
| ~90 days | QUARTERLY | ±7 days |
| ~180 days | SEMI_ANNUALLY | ±10 days |
| ~365 days | ANNUALLY | ±14 days |
| Other | IRREGULAR | - |

#### B. Temporal Pattern Detection

Detect which temporal pattern transactions follow (priority order):

1. **Last Working Day** (70% threshold)
   - Check if ≥70% of transactions occur on last business day of month

2. **First Working Day** (70% threshold)
   - Check if ≥70% occur on first business day

3. **Last Weekday of Month** (70% threshold)
   - Example: Last Thursday of each month
   - Calculate occurrence number: `(day - 1) // 7 + 1`
   - Check if last: `(days_in_month - day) < 7`

4. **First Weekday of Month** (70% threshold)
   - Example: First Friday of each month

5. **Nth Weekday of Month** (70% threshold)
   - Example: Second Tuesday of each month

6. **Specific Day of Month** (60% threshold)
   - Example: 15th of each month
   - Lower threshold due to month-end variations

7. **Specific Day of Week** (60% threshold)
   - Example: Every Tuesday

8. **Flexible** (fallback)
   - No clear temporal pattern

#### C. Merchant Pattern Extraction

Find common substring in transaction descriptions:

```python
def longest_common_substring(descriptions: List[str]) -> str:
    """Extract common merchant identifier."""
    if len(descriptions) == 1:
        return descriptions[0].strip()
    
    # Find longest common substring across all descriptions
    # Uses dynamic programming approach
    # Returns: "NETFLIX" from ["NETFLIX.COM", "NETFLIX STREAMING", "NETFLIX COM"]
```

#### D. Confidence Scoring

Multi-factor confidence score (0.0-1.0):

```python
confidence = (
    0.30 × interval_regularity +
    0.20 × amount_regularity +
    0.20 × sample_size_score +
    0.30 × temporal_consistency
)
```

**Interval Regularity:**
```python
interval_regularity = 1.0 / (1.0 + std_interval / (mean_interval + 1))
# Perfect regularity (std=0) → 1.0
# High variance → approaches 0.0
```

**Amount Regularity:**
```python
amount_regularity = 1.0 / (1.0 + std_amount / (abs(mean_amount) + 1))
# Consistent amounts → 1.0
# Variable amounts → approaches 0.0
```

**Sample Size Score:**
```python
sample_size_score = min(1.0, transaction_count / 12)
# 12+ transactions → 1.0
# 3 transactions → 0.25
```

**Temporal Consistency:**
```python
temporal_consistency = matching_transactions / total_transactions
# All match pattern → 1.0
# 60% match → 0.6
```

### 4. Filtering and Output

**Minimum Criteria:**
- ≥3 occurrences
- ≥0.6 confidence score

**Output:** List of `RecurringChargePattern` objects

---

## Data Flow

```
┌──────────────┐
│ Transactions │
│ (user's data)│
└──────┬───────┘
       │
       ▼
┌─────────────────────┐
│ Feature Engineering │
│ (67-dim vectors)    │
└──────┬──────────────┘
       │
       ▼
┌──────────────┐
│ DBSCAN       │
│ Clustering   │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Pattern Analysis │
│ (per cluster)    │
└──────┬───────────┘
       │
       ▼
┌──────────────┐       ┌────────────────┐
│ Filtering    │──────>│ Detected       │
│ (≥3, ≥0.6)   │       │ Patterns       │
└──────────────┘       └────────────────┘
```

---

## Performance Characteristics

### Execution Time (per 1,000 transactions)

| Stage | Target | Typical |
|-------|--------|---------|
| Feature Extraction | <2s | ~1.5s |
| DBSCAN Clustering | <3s | ~2.5s |
| Pattern Analysis | <1s | ~0.5s |
| **Total** | **<10s** | **~5s** |

### Memory Usage

- Feature vectors: ~0.5 MB per 1,000 transactions
- DBSCAN working memory: ~1 MB per 1,000 transactions
- Peak usage: ~1.5 MB per 1,000 transactions

### Lambda Configuration

```hcl
memory_size = 1024  # MB (required for scikit-learn)
timeout = 60        # seconds
runtime = "python3.12"
```

### Scalability Limits

- **Tested:** Up to 10,000 transactions (~50s)
- **Theoretical:** Up to 50,000 transactions (~250s, under Lambda timeout)
- **Mitigation:** Implement sampling for >50K transactions

---

## Expected Accuracy

### Baseline (No User Feedback)

| Metric | Value | Notes |
|--------|-------|-------|
| Precision | 68% | % of detected patterns that are correct |
| Recall | 65% | % of actual recurring charges detected |
| F1 Score | 0.665 | Harmonic mean |

### With User Feedback (3 months)

| Metric | Value | Notes |
|--------|-------|-------|
| Precision | 82% | Improved via feedback loop |
| Recall | 78% | Parameter tuning |
| F1 Score | 0.800 | - |

### Mature System (12 months)

| Metric | Value | Notes |
|--------|-------|-------|
| Precision | 91% | Approaching ceiling |
| Recall | 87% | - |
| F1 Score | 0.890 | Asymptotic limit |

---

## Integration Points

### Storage (DynamoDB)

**Tables:**
1. `recurring_charge_patterns` - Detected patterns
2. `recurring_charge_predictions` - Future occurrence predictions
3. `pattern_feedback` - User feedback for ML improvement

### API Layer

**Handlers:**
- `detect_recurring_charges_handler` - Trigger detection
- `get_patterns_handler` - List patterns
- `update_pattern_handler` - Modify pattern
- `predict_occurrences_handler` - Get predictions

### Async Processing

**EventBridge Consumer:**
- `recurring_charge_detection_consumer` - Processes detection events
- Updates operation status throughout detection (10%, 30%, 60%, 80%, 100%)

### Category System

When pattern is linked to category:
```python
CategoryRule(
    field="description",
    condition="contains",
    value=pattern.merchant_pattern,
    priority=100,  # High priority
    confidence=int(pattern.confidence_score * 100),
    amount_min=pattern.amount_min * 0.9,
    amount_max=pattern.amount_max * 1.1
)
```

---

## Dependencies

```txt
scikit-learn>=1.3.0    # DBSCAN clustering, TF-IDF
pandas>=2.0.0          # Data manipulation
numpy>=1.24.0          # Numerical operations
holidays>=0.35         # Working day detection (US holidays)
scipy>=1.11.0          # Statistical functions
```

---

## Limitations

### Fundamental Limitations

1. **Data Quality Ceiling**: Poor transaction descriptions → max ~40-50% accuracy
2. **Cold Start**: Need 3-4 months of history for reliable detection
3. **Irregular Patterns**: Variable amounts/timing → ~70% accuracy ceiling
4. **Asymptotic Accuracy**: Maximum ~92-95% for even regular patterns
5. **Computational Limits**: ~50K transactions per Lambda execution

### Known Edge Cases

1. **Variable Subscription Pricing**: Streaming services that change price
   - Mitigation: Amount tolerance (±10%)

2. **Calendar Edge Cases**: Day 31 doesn't exist in all months
   - Mitigation: Normalized month position feature

3. **Holiday Adjustments**: Bills moved due to weekends/holidays
   - Mitigation: Tolerance days (±2-3 days)

4. **Name Variations**: "AMZN MKTP", "AMAZON MARKETPLACE", "AMAZON.COM"
   - Mitigation: TF-IDF captures common tokens, longest common substring

5. **Multiple Subscriptions**: Same merchant, different plans
   - Mitigation: Amount clustering helps differentiate

---

## Future Enhancements

### Short Term (3-6 months)

1. **Supervised Learning Layer**: Use user feedback to train classifier
2. **Merchant Database**: Pre-built list of known subscriptions
3. **Confidence Tuning**: A/B test threshold values

### Medium Term (6-12 months)

1. **Cross-User Learning**: Aggregate patterns across users (privacy-safe)
2. **Anomaly Detection**: Detect missed or late payments
3. **Smart Notifications**: Alert on subscription price changes

### Long Term (12+ months)

1. **Semi-Supervised**: Bootstrap with known merchants
2. **Active Learning**: Intelligently select patterns for user review
3. **Transfer Learning**: Apply patterns across user accounts

---

## References

- **Decision Rationale**: [ADR-0004](./adr/adr-0004-unsupervised-ml-recurring-charge-detection.md)
- **Implementation Patterns**: `docs/features/recurring-charge-detection/implementation-guide.md`
- **Feature Documentation**: `docs/features/recurring-charge-detection/overview.md`
- **Delivery Status**: `docs/impl-log/recurring-charge-detection.md`
- **DBSCAN**: https://scikit-learn.org/stable/modules/clustering.html#dbscan
- **Circular Encoding**: https://ianlondon.github.io/blog/encoding-cyclical-features-24hour-time/

---

**Last Updated:** November 30, 2025

