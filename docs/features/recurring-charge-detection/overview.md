# Recurring Charge Detection - ML Overview

**Version:** 1.0  
**Date:** November 7, 2025  
**Audience:** Product managers, stakeholders, non-technical users

---

## How the ML Works

The system uses **unsupervised machine learning** (DBSCAN clustering) to automatically identify recurring charges without requiring labeled training data. 

**Feature Engineering:** Each transaction is transformed into a 60-dimensional feature vector combining temporal features (day of month/week using circular sine/cosine encoding, working days, holidays), amount features (log-scaled and normalized), and description features (TF-IDF vectorization capturing merchant name patterns).

**Clustering:** DBSCAN groups similar transactions together based on these features, automatically identifying noise and outliers without requiring a pre-specified number of clusters.

**Pattern Analysis:** For each cluster with ≥3 transactions, the system analyzes interval regularity (daily, weekly, monthly, etc.), detects temporal patterns (specific day of month, first/last working day), extracts merchant identifiers from descriptions, and calculates amount statistics.

**Confidence Scoring:** A multi-factor confidence score (0.0-1.0) combines interval regularity (30%), amount consistency (20%), sample size (20%), and temporal consistency (30%). Patterns scoring ≥0.6 confidence with ≥3 occurrences are surfaced to users.

The system improves over time through user feedback, learning which patterns are correct and adjusting parameters accordingly.

---

## Glossary of Terms

### Machine Learning Terms

**DBSCAN (Density-Based Spatial Clustering of Applications with Noise)**  
A clustering algorithm that groups similar data points together without needing to know the number of groups in advance. It automatically identifies outliers (noise) and works well with high-dimensional data.

**Unsupervised Learning**  
Machine learning where the algorithm finds patterns in data without being told what to look for (no labeled examples needed). The system discovers recurring patterns on its own.

**Feature Engineering**  
The process of transforming raw transaction data (date, amount, description) into numerical features that machine learning algorithms can process.

**Feature Vector**  
A numerical representation of a transaction. Think of it as converting "Netflix $14.99 on Jan 15" into an array of 60 numbers that capture all relevant patterns.

**Clustering**  
Grouping similar items together. In our case, grouping transactions that appear to be the same recurring charge (e.g., all Netflix payments).

**Confidence Score**  
A number between 0.0 and 1.0 indicating how certain the system is that a detected pattern is a true recurring charge. Higher scores mean more reliable patterns.

### Financial Terms

**Recurring Charge**  
A transaction that happens repeatedly at regular intervals, such as subscriptions (Netflix, Spotify), bills (electricity, rent), or income (salary).

**Merchant Pattern**  
The identifying text from transaction descriptions that indicates the merchant (e.g., "NETFLIX", "SPOTIFY PREM", "SALARY DEPOSIT").

**Temporal Pattern**  
The timing pattern of when transactions occur (e.g., "15th of each month", "last working day", "every Tuesday").

**Working Day**  
Monday through Friday, excluding federal holidays. Many bills and salaries are paid on working days.

### Feature Engineering Terms

**Circular Encoding (Sine/Cosine Transformation)**  
A mathematical technique to represent cyclical data (like days of the week or month) so that the end connects to the beginning. For example, day 31 of the month is close to day 1, and Sunday is close to Monday.

**TF-IDF (Term Frequency-Inverse Document Frequency)**  
A text analysis technique that converts transaction descriptions into numbers. It identifies important words that distinguish one merchant from another.

**Log-Scaled Amount**  
A mathematical transformation (logarithm) applied to transaction amounts to reduce the impact of very large values and make patterns easier to detect.

**Normalized**  
Adjusting values to a common scale (typically 0 to 1) so that different features can be compared fairly.

### Pattern Detection Terms

**Interval Regularity**  
How consistent the time gaps are between transactions. Perfect regularity means exactly the same number of days between each occurrence.

**Amount Regularity**  
How consistent the transaction amounts are. A subscription that's always $14.99 has perfect amount regularity.

**Sample Size**  
The number of transactions in a pattern. More transactions generally mean higher confidence.

**Temporal Consistency**  
The percentage of transactions that match the detected temporal pattern. For example, if 11 out of 12 transactions occur on the 15th of the month, temporal consistency is 92%.

**Tolerance**  
Acceptable variation from the expected pattern. For dates, typically ±2 days. For amounts, typically ±10%.

### Frequency Types

**Daily**  
Transactions occurring approximately every day (~1 day intervals).

**Weekly**  
Transactions occurring approximately every week (~7 day intervals).

**Bi-Weekly**  
Transactions occurring approximately every two weeks (~14 day intervals).

**Semi-Monthly**  
Transactions occurring twice per month, typically on the 1st and 15th (~15 day intervals).

**Monthly**  
Transactions occurring approximately once per month (~30 day intervals).

**Quarterly**  
Transactions occurring approximately every three months (~90 day intervals).

**Annually**  
Transactions occurring approximately once per year (~365 day intervals).

**Irregular**  
Transactions that recur but without a clear consistent interval.

### Temporal Pattern Types

**Day of Week**  
Transactions that occur on the same day of the week (e.g., every Tuesday).

**Day of Month**  
Transactions that occur on the same date each month (e.g., 15th of every month).

**First Working Day**  
Transactions that occur on the first business day of each month.

**Last Working Day**  
Transactions that occur on the last business day of each month.

**First Day of Month**  
Transactions that occur on the 1st of each month.

**Last Day of Month**  
Transactions that occur on the last day of each month (28th-31st depending on month).

**Weekend**  
Transactions that predominantly occur on Saturdays or Sundays.

**Weekday**  
Transactions that predominantly occur Monday through Friday.

**Flexible**  
No strict temporal pattern detected; timing varies.

### System Terms

**Auto-Categorize**  
Automatically assigning a category to transactions that match a recurring pattern, without requiring user review.

**Feedback Loop**  
The process where users confirm or reject detected patterns, which helps the system learn and improve over time.

**Cold Start Problem**  
The challenge of detecting patterns for new users who don't have much transaction history yet (typically need 3-4 months of data).

**False Positive**  
When the system incorrectly identifies a pattern as recurring when it's not (e.g., two random coffee purchases detected as a subscription).

**False Negative**  
When the system fails to detect a pattern that actually is recurring (e.g., missing a Netflix subscription).

**Precision**  
The percentage of detected patterns that are actually correct. High precision means few false positives.

**Recall**  
The percentage of actual recurring charges that the system successfully detects. High recall means few false negatives.

---

## References & Further Reading

### Detailed Design Documents

**For Technical Implementation Details:**
- `ml-recurring-charge-detection-design.md` - Complete ML algorithm design, feature engineering details, and performance analysis (1680 lines)
- `recurring-charge-integration-design.md` - System integration, API design, frontend/backend implementation (1761 lines)
- `recurring-charge-phase1-implementation.md` - Step-by-step implementation guide (527 lines)

### Key Sections by Topic

**Understanding the Algorithm:**
- ML Design Doc, Section: "Detection Algorithm" (lines 339-498)
- ML Design Doc, Section: "Feature Engineering" (lines 246-336)

**How Confidence Scores Work:**
- ML Design Doc, Section: "Stage 3: Confidence Scoring" (lines 454-483)
- ML Design Doc, Appendix B: "Confidence Score Examples" (lines 1589-1597)

**System Improvement & Learning:**
- ML Design Doc, Section: "Iterative Improvement & Limitations" (lines 996-1520)
- Covers feedback loops, performance trajectory, and accuracy expectations

**Integration with Existing System:**
- Integration Design Doc, Section: "Architecture Integration" (lines 20-53)
- Integration Design Doc, Section: "Backend Implementation" (lines 56-810)
- Integration Design Doc, Section: "Frontend Implementation" (lines 813-1348)

**API Usage:**
- ML Design Doc, Section: "API Design" (lines 501-679)
- Integration Design Doc, Section: "Handler: Trigger Detection" (lines 427-737)

**Performance & Scalability:**
- ML Design Doc, Section: "Performance Considerations" (lines 916-993)
- ML Design Doc, Appendix A: "Algorithm Complexity Analysis" (lines 1580-1587)

**Expected Accuracy & Limitations:**
- ML Design Doc, Section: "Fundamental Limitations" (lines 1251-1520)
- ML Design Doc, Section: "Expected Performance Trajectory" (lines 1450-1468)

### External Resources

**DBSCAN Clustering Algorithm:**
- Original Paper: Ester, M., et al. (1996). "A density-based algorithm for discovering clusters in large spatial databases with noise"
- scikit-learn Documentation: https://scikit-learn.org/stable/modules/clustering.html#dbscan
- Visual Explanation: https://www.naftaliharris.com/blog/visualizing-dbscan-clustering/

**Feature Engineering Techniques:**
- scikit-learn Feature Extraction: https://scikit-learn.org/stable/modules/feature_extraction.html
- TF-IDF Explained: https://en.wikipedia.org/wiki/Tf%E2%80%93idf
- Circular Features for Time Data: https://ianlondon.github.io/blog/encoding-cyclical-features-24hour-time/

**Machine Learning Libraries:**
- scikit-learn: https://scikit-learn.org/ (clustering, feature extraction)
- pandas: https://pandas.pydata.org/ (data manipulation)
- NumPy: https://numpy.org/ (numerical computations)
- holidays: https://pypi.org/project/holidays/ (working day detection)

**AWS Services:**
- Lambda Best Practices: https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html
- DynamoDB Design Patterns: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html
- EventBridge: https://docs.aws.amazon.com/eventbridge/latest/userguide/

### Academic Background

**Clustering & Pattern Recognition:**
- "Pattern Recognition and Machine Learning" by Christopher Bishop
- "The Elements of Statistical Learning" by Hastie, Tibshirani, and Friedman

**Time Series Analysis:**
- "Forecasting: Principles and Practice" by Hyndman & Athanasopoulos (free online: https://otexts.com/fpp3/)
- "Time Series Analysis and Its Applications" by Shumway & Stoffer

**Financial Data Analysis:**
- "Advances in Financial Machine Learning" by Marcos López de Prado
- "Machine Learning for Asset Managers" by Marcos López de Prado

---

## Quick Reference: Where to Find Information

| What You Want to Know | Where to Look |
|----------------------|---------------|
| How does the ML algorithm work? | ML Design Doc → "Detection Algorithm" section |
| What features are extracted from transactions? | ML Design Doc → "Feature Engineering" section |
| How accurate will it be? | ML Design Doc → "Expected Performance Trajectory" |
| How do I integrate this into my app? | Integration Design Doc → "Frontend Implementation" |
| What APIs are available? | ML Design Doc → "API Design" section |
| How long does detection take? | ML Design Doc → "Performance Considerations" |
| What are the limitations? | ML Design Doc → "Fundamental Limitations" |
| How do I implement this step-by-step? | Phase 1 Implementation Doc (entire document) |
| What happens when a user triggers detection? | Integration Design Doc → "System Flow" diagram |
| How does the system improve over time? | ML Design Doc → "User Feedback Loop" |
| What infrastructure is needed? | Integration Design Doc → "Infrastructure" section |
| How do I test the system? | ML Design Doc → Appendix D: "Testing Strategy" |

---

## Summary

The recurring charge detection system uses machine learning to automatically find patterns in your transaction history. It looks at when transactions occur, how much they cost, and what the descriptions say to group similar transactions together. Each pattern gets a confidence score based on how regular and consistent it is. Users can confirm or reject patterns, which helps the system learn and improve over time.

**Key Benefits:**
- No manual setup required - just trigger detection
- Learns from your feedback to get better
- Provides confidence scores so you know what to trust
- Integrates with existing categorization system
- Predicts future charges for budgeting

**Expected Performance:**
- Week 1: ~70% accuracy (baseline)
- Month 3: ~82% accuracy (with feedback)
- Month 6: ~88% accuracy (approaching ceiling)
- Month 12+: ~92% accuracy (asymptotic limit)

---

**Document Version:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-07 | System | Initial overview document |

