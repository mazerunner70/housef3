# ADR-0004: Unsupervised ML for Recurring Charge Detection

**Date:** November 3, 2025  
**Status:** Accepted  
**Deciders:** Engineering Team

## Context

Users need automatic detection of recurring charges (subscriptions, bills, salaries) in transaction history to enable:
- Automatic categorization of future charges
- Budget forecasting for predictable expenses
- Subscription management and tracking

The system must identify patterns without requiring users to manually define rules or provide labeled training data.

## Decision

Implement unsupervised machine learning using **DBSCAN (Density-Based Spatial Clustering of Applications with Noise)** to automatically detect recurring charge patterns from transaction history.

### Key Components

**1. Feature Engineering (67-dimensional vectors)**
- **Temporal features (17)**: Circular sin/cos encoding for cyclical time patterns, boolean flags for working days
- **Amount features (1)**: Log-scaled and normalized transaction amounts
- **Description features (49)**: TF-IDF vectorization of merchant names

**2. DBSCAN Clustering**
- `eps = 0.5` (neighborhood radius)
- `min_samples = max(3, n_samples × 0.01)` (adaptive)
- Automatically identifies noise and outliers
- No need to pre-specify number of clusters

**3. Pattern Analysis**
- Detect 9 frequency types (daily, weekly, bi-weekly, semi-monthly, monthly, quarterly, semi-annually, annually, irregular)
- Detect 14 temporal pattern types (day of month, day of week, first/last working day, Nth weekday of month, etc.)
- Multi-factor confidence scoring (0.0-1.0): interval regularity (30%), amount regularity (20%), sample size (20%), temporal consistency (30%)
- Surface patterns with ≥3 occurrences and ≥0.6 confidence

## Alternatives Considered

### 1. Rule-Based Pattern Matching
**Approach:** Users manually define rules (e.g., "NETFLIX every month on the 15th")

**Pros:**
- Simple to implement
- Deterministic behavior
- No ML dependencies

**Cons:**
- Requires manual setup for every recurring charge
- Poor UX - users must know patterns exist
- Can't detect patterns users don't know about
- No adaptation to changing patterns

**Rejected:** Too much manual effort, defeats purpose of automatic detection

### 2. Supervised Machine Learning
**Approach:** Train model on labeled examples of recurring vs. non-recurring transactions

**Pros:**
- Can achieve high accuracy with enough training data
- Learns from labeled patterns
- Well-established techniques

**Cons:**
- Cold start problem - need labeled data before system works
- Requires significant labeling effort
- Doesn't transfer well across users (different merchants, patterns)
- Model maintenance and retraining overhead

**Rejected:** Impractical cold start, expensive labeling requirements

### 3. K-Means Clustering
**Approach:** Use K-means instead of DBSCAN

**Pros:**
- Faster algorithm (O(n) vs O(n log n))
- Simpler to tune
- Well-understood algorithm

**Cons:**
- Requires pre-specifying number of clusters (K) - unknown in our case
- Assumes spherical clusters - not suitable for our feature space
- Sensitive to outliers and noise
- Forces all points into clusters (no noise detection)

**Rejected:** Fundamental mismatch with problem (unknown K, need noise detection)

### 4. Time Series Forecasting (ARIMA, Prophet)
**Approach:** Model each merchant separately as time series

**Pros:**
- Designed for temporal patterns
- Can predict future occurrences
- Handles seasonality

**Cons:**
- Requires separate model per merchant
- Assumes single merchant name (doesn't handle variations)
- Poor performance with sparse data (<12 months)
- Computationally expensive for many merchants
- Doesn't naturally group similar transactions

**Rejected:** Doesn't scale to unknown number of merchants, requires too much data

## Consequences

### Positive

1. **Zero Manual Setup**: System works immediately with historical data, no user configuration required
2. **Discovers Unknown Patterns**: Finds recurring charges users might not know about (forgotten subscriptions, irregular bills)
3. **Handles Variation**: Clusters similar transactions despite description variations ("NETFLIX.COM", "NETFLIX STREAMING")
4. **No Training Data**: Unsupervised approach works from day one without labeled examples
5. **Adaptive**: Automatically adjusts to new patterns as transaction history grows
6. **Noise Handling**: DBSCAN naturally identifies one-off transactions vs. patterns

### Negative

1. **Accuracy Ceiling**: Unsupervised ML has lower theoretical accuracy than supervised (~92-95% max vs. 98%+)
2. **Cold Start**: Needs 3-4 months of transaction history for reliable detection
3. **Computational Cost**: Requires ML libraries (scikit-learn) in Lambda, 1024 MB memory
4. **False Positives**: May detect coincidental patterns (e.g., two coffee purchases on same weekday)
5. **Parameter Sensitivity**: DBSCAN performance depends on eps and min_samples tuning
6. **Irregular Patterns**: Lower confidence for variable-amount or variable-timing charges

### Mitigation Strategies

1. **Accuracy**: Implement user feedback loop to improve over time (target 82% by month 3)
2. **Cold Start**: Show user messaging about minimum data requirements, allow manual pattern creation
3. **Computational Cost**: Use Lambda with 1024 MB memory, optimize feature extraction, consider sampling for >50K transactions
4. **False Positives**: High confidence threshold (≥0.6), require ≥3 occurrences, allow user to reject patterns
5. **Parameter Tuning**: Start with conservative defaults, collect performance metrics, iterate
6. **Irregular Patterns**: Multi-factor confidence score handles variability, lower confidence = manual review

## Performance Expectations

### Baseline (Week 1)
- Precision: ~68%
- Recall: ~65%
- F1 Score: ~0.665

### With Feedback (Month 3)
- Precision: ~82%
- Recall: ~78%
- F1 Score: ~0.800

### Mature System (Month 12)
- Precision: ~91%
- Recall: ~87%
- F1 Score: ~0.890

## Future Improvements

1. **Supervised Learning Layer**: Use user feedback to train classification model on top of DBSCAN
2. **Merchant Database**: Build common merchant name database from aggregate user data
3. **Cross-User Learning**: Learn patterns across users (privacy-safe aggregation)
4. **Anomaly Detection**: Detect missed payments or unusual timing
5. **Semi-Supervised**: Bootstrap with known subscription merchants (Netflix, Spotify, etc.)

## References

- **DBSCAN Paper**: Ester, M., et al. (1996). "A density-based algorithm for discovering clusters in large spatial databases with noise"
- **scikit-learn DBSCAN**: https://scikit-learn.org/stable/modules/clustering.html#dbscan
- **Circular Feature Encoding**: https://ianlondon.github.io/blog/encoding-cyclical-features-24hour-time/
- **Implementation**: See `docs/features/recurring-charge-detection/design.md`
- **Delivery Timeline**: See `docs/impl-log/recurring-charge-detection.md`

