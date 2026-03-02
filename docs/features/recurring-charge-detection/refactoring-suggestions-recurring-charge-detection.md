# Refactoring Suggestions: Recurring Charge Detection System

## Overview

The recurring charge detection system has been consolidated into a single module architecture. This document provides suggestions for making the codebase easier to reason about and maintain.

## Current Architecture (Post-Consolidation)

### File Structure
```
backend/src/services/
├── recurring_charge_feature_service.py      (529 lines) - Feature extraction
├── recurring_charge_detection_service.py    (798 lines) - Detection orchestration
└── recurring_charge_operations.py           (376 lines) - API handlers

backend/src/consumers/
└── recurring_charge_detection_consumer.py   (200+ lines) - Event processing

backend/src/models/
└── recurring_charge.py                      - Data models
```

### Key Improvements from Consolidation
1. **Single Source of Truth**: All feature extraction in one module
2. **Automatic Mode Selection**: Features adapt based on whether `accounts_map` is provided
3. **Eliminated Inheritance**: No need to choose between base and enhanced classes
4. **Simpler Imports**: One import instead of two conditional imports

---

## Refactoring Suggestions

### 1. **Feature Extraction: Split by Concern** ⭐ HIGH IMPACT

**Problem**: `recurring_charge_feature_service.py` (529 lines) does too much in one class.

**Solution**: Extract feature groups into separate, composable classes.

```python
# services/recurring_charge_features/
# ├── __init__.py
# ├── base.py                    # RecurringChargeFeatureService (orchestrator)
# ├── temporal_features.py       # TemporalFeatureExtractor
# ├── amount_features.py         # AmountFeatureExtractor
# ├── description_features.py    # DescriptionFeatureExtractor
# └── account_features.py        # AccountFeatureExtractor

# Example: temporal_features.py
class TemporalFeatureExtractor:
    """Extracts 17 temporal features from transactions."""
    
    FEATURE_SIZE = 17
    
    def __init__(self, country_code: str = 'US'):
        self.holidays = holidays.country_holidays(country_code)
    
    def extract(self, transaction: Transaction) -> List[float]:
        """Extract temporal features for a single transaction."""
        # 17 features...
        
    def extract_batch(self, transactions: List[Transaction]) -> np.ndarray:
        """Extract temporal features for multiple transactions."""
        return np.array([self.extract(tx) for tx in transactions])

# Example: base.py
class RecurringChargeFeatureService:
    """Orchestrates feature extraction from multiple extractors."""
    
    def __init__(self, country_code: str = 'US'):
        self.temporal = TemporalFeatureExtractor(country_code)
        self.amount = AmountFeatureExtractor()
        self.description = DescriptionFeatureExtractor()
        self.account = AccountFeatureExtractor()
    
    def extract_features_batch(
        self,
        transactions: List[Transaction],
        accounts_map: Optional[Dict[uuid.UUID, Account]] = None
    ) -> Tuple[np.ndarray, Optional[TfidfVectorizer]]:
        """Compose features from all extractors."""
        temporal = self.temporal.extract_batch(transactions)
        amount = self.amount.extract_batch(transactions)
        description, vectorizer = self.description.extract_batch(transactions)
        
        if accounts_map:
            account = self.account.extract_batch(transactions, accounts_map)
            return np.hstack([temporal, amount, description, account]), vectorizer
        else:
            return np.hstack([temporal, amount, description]), vectorizer
```

**Benefits**:
- Each extractor is independently testable
- Clear single responsibility
- Easier to add new feature types
- Simpler to understand each component
- Can reuse extractors in other contexts

**Effort**: Medium (2-3 hours)

---

### 2. **Pattern Analysis: Extract Pattern Analyzers** ⭐ HIGH IMPACT

**Problem**: `recurring_charge_detection_service.py` (798 lines) has multiple analysis responsibilities mixed together.

**Solution**: Extract pattern analysis logic into separate analyzer classes.

```python
# services/recurring_charge_analyzers/
# ├── __init__.py
# ├── frequency_analyzer.py      # FrequencyAnalyzer
# ├── temporal_analyzer.py       # TemporalPatternAnalyzer
# ├── merchant_analyzer.py       # MerchantPatternAnalyzer
# ├── confidence_calculator.py   # ConfidenceScoreCalculator
# └── account_adjuster.py        # AccountConfidenceAdjuster

# Example: frequency_analyzer.py
class FrequencyAnalyzer:
    """Analyzes transaction intervals to detect recurrence frequency."""
    
    THRESHOLDS = {
        RecurrenceFrequency.DAILY: (0.5, 1.5),
        RecurrenceFrequency.WEEKLY: (6, 8),
        # ... etc
    }
    
    def detect_frequency(self, transactions: List[Transaction]) -> RecurrenceFrequency:
        """Detect frequency from sorted transactions."""
        if len(transactions) < 2:
            return RecurrenceFrequency.IRREGULAR
        
        intervals = self._calculate_intervals(transactions)
        mean_interval = np.mean(intervals)
        
        return self._match_to_frequency(mean_interval)
    
    def _calculate_intervals(self, transactions: List[Transaction]) -> List[float]:
        """Calculate day intervals between consecutive transactions."""
        # ...
    
    def _match_to_frequency(self, mean_interval: float) -> RecurrenceFrequency:
        """Match mean interval to frequency category."""
        # ...

# Example: confidence_calculator.py
class ConfidenceScoreCalculator:
    """Calculates multi-factor confidence scores for patterns."""
    
    WEIGHTS = {
        'interval_regularity': 0.30,
        'amount_regularity': 0.20,
        'sample_size': 0.20,
        'temporal_consistency': 0.30
    }
    
    def calculate(
        self,
        transactions: List[Transaction],
        temporal_info: Dict[str, Any]
    ) -> float:
        """Calculate weighted confidence score."""
        scores = {
            'interval_regularity': self._interval_score(transactions),
            'amount_regularity': self._amount_score(transactions),
            'sample_size': self._sample_size_score(transactions),
            'temporal_consistency': temporal_info.get('temporal_consistency', 0.5)
        }
        
        return sum(score * self.WEIGHTS[key] for key, score in scores.items())
    
    def _interval_score(self, transactions: List[Transaction]) -> float:
        """Calculate interval regularity score."""
        # ...

# Main detection service becomes orchestrator
class RecurringChargeDetectionService:
    """Orchestrates recurring charge detection using specialized analyzers."""
    
    def __init__(self, country_code: str = 'US', use_account_features: bool = True):
        self.feature_service = RecurringChargeFeatureService(country_code)
        self.frequency_analyzer = FrequencyAnalyzer()
        self.temporal_analyzer = TemporalPatternAnalyzer(country_code)
        self.merchant_analyzer = MerchantPatternAnalyzer()
        self.confidence_calculator = ConfidenceScoreCalculator()
        self.account_adjuster = AccountConfidenceAdjuster()
        self.use_account_features = use_account_features
    
    def _analyze_pattern(
        self,
        user_id: str,
        cluster_transactions: List[Transaction],
        cluster_id: int,
        accounts_map: Optional[Dict[uuid.UUID, Account]] = None
    ) -> Optional[RecurringChargePatternCreate]:
        """Analyze pattern using specialized analyzers."""
        frequency = self.frequency_analyzer.detect_frequency(cluster_transactions)
        temporal_info = self.temporal_analyzer.analyze(cluster_transactions)
        merchant_pattern = self.merchant_analyzer.extract_pattern(cluster_transactions)
        
        base_confidence = self.confidence_calculator.calculate(
            cluster_transactions, temporal_info
        )
        
        if accounts_map and self.use_account_features:
            confidence = self.account_adjuster.adjust(
                base_confidence, cluster_transactions, frequency,
                merchant_pattern, accounts_map
            )
        else:
            confidence = base_confidence
        
        # Create pattern object...
```

**Benefits**:
- Each analyzer has a clear, focused purpose
- Easier to test each component in isolation
- Can swap analyzers for different detection strategies
- Main service becomes a clean orchestrator
- Easier to understand the detection pipeline

**Effort**: Medium-High (3-4 hours)

---

### 3. **Configuration: Extract Magic Numbers** ⭐ MEDIUM IMPACT

**Problem**: Constants scattered throughout code, some duplicated, hard to tune.

**Solution**: Centralize configuration in dedicated config classes.

```python
# services/recurring_charge_config.py
from dataclasses import dataclass
from typing import Dict, Tuple
from models.recurring_charge import RecurrenceFrequency

@dataclass
class ClusteringConfig:
    """Configuration for DBSCAN clustering."""
    default_eps: float = 0.5
    min_samples_ratio: float = 0.01
    min_cluster_size: int = 3

@dataclass
class ConfidenceWeights:
    """Weights for confidence score calculation."""
    interval_regularity: float = 0.30
    amount_regularity: float = 0.20
    sample_size: float = 0.20
    temporal_consistency: float = 0.30
    
    def __post_init__(self):
        """Validate weights sum to 1.0."""
        total = sum([
            self.interval_regularity,
            self.amount_regularity,
            self.sample_size,
            self.temporal_consistency
        ])
        if not abs(total - 1.0) < 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

@dataclass
class FrequencyThresholds:
    """Day range thresholds for frequency classification."""
    daily: Tuple[float, float] = (0.5, 1.5)
    weekly: Tuple[float, float] = (6, 8)
    bi_weekly: Tuple[float, float] = (12, 16)
    semi_monthly: Tuple[float, float] = (13, 17)
    monthly: Tuple[float, float] = (25, 35)
    bi_monthly: Tuple[float, float] = (55, 65)
    quarterly: Tuple[float, float] = (85, 95)
    semi_annually: Tuple[float, float] = (175, 190)
    annually: Tuple[float, float] = (355, 375)
    
    def to_dict(self) -> Dict[RecurrenceFrequency, Tuple[float, float]]:
        """Convert to frequency enum mapping."""
        return {
            RecurrenceFrequency.DAILY: self.daily,
            RecurrenceFrequency.WEEKLY: self.weekly,
            RecurrenceFrequency.BI_WEEKLY: self.bi_weekly,
            RecurrenceFrequency.SEMI_MONTHLY: self.semi_monthly,
            RecurrenceFrequency.MONTHLY: self.monthly,
            RecurrenceFrequency.BI_MONTHLY: self.bi_monthly,
            RecurrenceFrequency.QUARTERLY: self.quarterly,
            RecurrenceFrequency.SEMI_ANNUALLY: self.semi_annually,
            RecurrenceFrequency.ANNUALLY: self.annually,
        }

@dataclass
class DetectionConfig:
    """Master configuration for recurring charge detection."""
    clustering: ClusteringConfig = ClusteringConfig()
    confidence_weights: ConfidenceWeights = ConfidenceWeights()
    frequency_thresholds: FrequencyThresholds = FrequencyThresholds()
    min_confidence: float = 0.6
    min_occurrences: int = 3
    temporal_consistency_threshold: float = 0.70

# Usage:
config = DetectionConfig()
dbscan = DBSCAN(eps=config.clustering.default_eps, ...)
```

**Benefits**:
- Single place to tune detection parameters
- Type safety with dataclasses
- Validation at configuration time
- Easy to create different configs for testing
- Documentation embedded in config classes

**Effort**: Low-Medium (1-2 hours)

---

### 4. **Testing: Create Feature Testing Utilities** ⭐ LOW-MEDIUM IMPACT

**Problem**: Creating test fixtures for account-aware features is verbose.

**Solution**: Create factory functions and fixtures.

```python
# tests/fixtures/recurring_charge_fixtures.py
from typing import List, Dict
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

from models.transaction import Transaction
from models.account import Account, AccountType

def create_test_account(
    user_id: str = "test-user",
    account_type: AccountType = AccountType.CHECKING,
    account_name: str = "Test Account",
    institution: str = "Test Bank"
) -> Account:
    """Create a test account with sensible defaults."""
    return Account(
        userId=user_id,
        accountId=uuid.uuid4(),
        accountName=account_name,
        accountType=account_type,
        institution=institution,
        firstTransactionDate=int((datetime.now() - timedelta(days=365)).timestamp() * 1000),
        is_active=True
    )

def create_monthly_transactions(
    user_id: str,
    account_id: uuid.UUID,
    merchant: str,
    amount: Decimal,
    start_date: datetime,
    count: int = 12,
    day_of_month: int = 15
) -> List[Transaction]:
    """Create a series of monthly transactions."""
    transactions = []
    
    for i in range(count):
        date = start_date.replace(day=day_of_month) + timedelta(days=30 * i)
        tx = Transaction(
            userId=user_id,
            fileId=uuid.uuid4(),
            accountId=account_id,
            date=int(date.timestamp() * 1000),
            description=f"{merchant} {i+1:03d}",
            amount=amount
        )
        transactions.append(tx)
    
    return transactions

def create_test_scenario(
    scenario_type: str = "credit_card_subscription"
) -> Dict:
    """Create complete test scenarios with accounts and transactions."""
    scenarios = {
        "credit_card_subscription": {
            "account": create_test_account(
                account_type=AccountType.CREDIT_CARD,
                account_name="Rewards Credit Card",
                institution="Chase"
            ),
            "transactions": lambda account: create_monthly_transactions(
                user_id=account.user_id,
                account_id=account.account_id,
                merchant="NETFLIX",
                amount=Decimal("-15.99"),
                start_date=datetime.now() - timedelta(days=365)
            )
        },
        # Add more scenarios...
    }
    
    scenario = scenarios[scenario_type]
    account = scenario["account"]
    transactions = scenario["transactions"](account)
    
    return {
        "account": account,
        "transactions": transactions,
        "accounts_map": {account.account_id: account}
    }
```

**Benefits**:
- Reduce test boilerplate
- Consistent test data
- Named scenarios for readability
- Easy to add new test patterns

**Effort**: Low (1 hour)

---

### 5. **Documentation: Add Pipeline Diagrams** ⭐ LOW IMPACT

**Problem**: Hard to visualize the detection flow.

**Solution**: Add mermaid diagrams to docstrings and docs.

```python
class RecurringChargeDetectionService:
    """
    Orchestrates recurring charge detection using ML clustering.
    
    Detection Pipeline:
    
    ```mermaid
    graph TD
        A[Transactions + Accounts] --> B[Feature Extraction]
        B --> C{Account-Aware?}
        C -->|Yes| D[91-dim features]
        C -->|No| E[67-dim features]
        D --> F[DBSCAN Clustering]
        E --> F
        F --> G[Pattern Analysis]
        G --> H{Frequency Detection}
        G --> I{Temporal Analysis}
        G --> J{Merchant Extraction}
        H --> K[Confidence Scoring]
        I --> K
        J --> K
        K --> L{Account Adjustment?}
        L -->|Yes| M[Adjusted Score]
        L -->|No| N[Base Score]
        M --> O[Filter by Min Confidence]
        N --> O
        O --> P[RecurringChargePatterns]
    ```
    
    Feature Dimensions:
    - Base: 67 dimensions (17 temporal + 1 amount + 49 description)
    - Enhanced: 91 dimensions (67 base + 24 account-aware)
    """
```

**Benefits**:
- Visual understanding of the system
- Easier onboarding for new developers
- Clear documentation of data flow

**Effort**: Low (30 minutes)

---

## Priority Recommendations

### Immediate (Do Now)
1. **Extract Configuration** (#3) - Quick win, immediate benefits
2. **Add Testing Utilities** (#4) - Makes testing easier going forward

### Short-term (Next Sprint)
3. **Split Feature Extraction** (#1) - High impact, manageable scope
4. **Extract Pattern Analyzers** (#2) - Makes detection logic clearer

### Long-term (Future Enhancement)
5. **Add Documentation** (#5) - Continuous improvement
6. **Performance Profiling** - Identify bottlenecks in feature extraction
7. **Caching Layer** - Cache account stats for repeated detections

---

## Additional Considerations

### Type Safety
Consider adding more type hints and using `mypy --strict`:
```python
# Instead of:
def analyze(transactions):
    # ...

# Use:
def analyze(transactions: List[Transaction]) -> AnalysisResult:
    # ...
```

### Error Handling
Create custom exception classes for better error handling:
```python
# services/recurring_charge_exceptions.py
class RecurringChargeDetectionError(Exception):
    """Base exception for detection errors."""
    pass

class InsufficientDataError(RecurringChargeDetectionError):
    """Raised when not enough transactions for detection."""
    pass

class FeatureExtractionError(RecurringChargeDetectionError):
    """Raised when feature extraction fails."""
    pass
```

### Logging Strategy
Standardize logging with structured fields:
```python
logger.info(
    "Pattern detected",
    extra={
        "user_id": user_id,
        "pattern_id": pattern.pattern_id,
        "merchant": pattern.merchant_pattern,
        "confidence": pattern.confidence_score,
        "frequency": pattern.frequency.value
    }
)
```

---

## Summary

The consolidation of account-aware features into a single module was a great first step. The suggested refactorings focus on:

1. **Separation of Concerns**: Each class does one thing well
2. **Composability**: Small, focused components that work together
3. **Testability**: Easy to test individual pieces
4. **Maintainability**: Clear structure, easy to modify
5. **Discoverability**: Easy to find and understand code

Start with the quick wins (config and test utilities), then tackle the larger refactorings (feature extraction and pattern analyzers) when you have time.

