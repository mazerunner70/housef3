"""
Recurring Charge Detection Service.

This module orchestrates ML-based recurring charge detection using DBSCAN clustering
and specialized pattern analyzers.

## Detection Pipeline

```mermaid
graph TD
    A[Transactions + Accounts] --> B[Feature Extraction]
    B --> C{Account-Aware?}
    C -->|Yes| D[91-dim features]
    C -->|No| E[67-dim features]
    D --> F[DBSCAN Clustering]
    E --> F
    F --> G[Pattern Analysis]
    G --> H[FrequencyAnalyzer]
    G --> I[TemporalPatternAnalyzer]
    G --> J[MerchantPatternAnalyzer]
    H --> K[ConfidenceScoreCalculator]
    I --> K
    J --> K
    K --> L{Account Adjustments?}
    L -->|Yes| M[Adjusted Score]
    L -->|No| N[Base Score]
    M --> O[Filter by Min Confidence]
    N --> O
    O --> P[RecurringChargePatterns]
```

## Feature Dimensions
- **Base**: 67 dimensions (17 temporal + 1 amount + 49 description)
- **Enhanced**: 91 dimensions (67 base + 24 account-aware)
"""

import logging
import uuid
from typing import List, Dict, Optional
from decimal import Decimal

import numpy as np
from sklearn.cluster import DBSCAN

from models.transaction import Transaction
from models.account import Account
from models.recurring_charge import (
    RecurringChargePatternCreate,
)
from services.recurring_charges.feature_service import RecurringChargeFeatureService
from services.recurring_charges.analyzers import (
    FrequencyAnalyzer,
    TemporalPatternAnalyzer,
    MerchantPatternAnalyzer,
    ConfidenceScoreCalculator
)
from services.recurring_charges.config import (
    DetectionConfig,
    DEFAULT_CONFIG,
    # Legacy constants for backward compatibility
    MIN_CLUSTER_SIZE,
    MIN_CONFIDENCE,
    DEFAULT_EPS,
)
from utils.ml_performance import MLPerformanceTracker

logger = logging.getLogger(__name__)


class RecurringChargeDetectionService:
    """
    Orchestrates recurring charge detection using specialized analyzers.
    
    Uses DBSCAN clustering to group similar transactions, then applies
    specialized analyzers to extract patterns, calculate confidence, and
    optionally adjust scores based on account context.
    """
    
    def __init__(
        self, 
        country_code: str = 'US', 
        use_account_features: bool = True,
        config: Optional[DetectionConfig] = None
    ):
        """
        Initialize the detection service.
        
        Args:
            country_code: Country code for holiday detection (default: US)
            use_account_features: Whether to use account-aware features (default: True)
            config: Optional detection configuration. If None, uses DEFAULT_CONFIG.
        """
        self.country_code = country_code
        self.use_account_features = use_account_features
        self.config = config or DEFAULT_CONFIG
        
        # Initialize feature service
        self.feature_service = RecurringChargeFeatureService(country_code)
        
        # Initialize specialized analyzers
        import holidays
        self.holidays = holidays.country_holidays(country_code)
        
        self.frequency_analyzer = FrequencyAnalyzer(
            frequency_thresholds=self.config.frequency_thresholds.to_dict()
        )
        
        self.temporal_analyzer = TemporalPatternAnalyzer(
            holidays=self.holidays,
            consistency_threshold=self.config.temporal_pattern.consistency_threshold,
            weekday_detection_threshold=self.config.temporal_pattern.weekday_detection_threshold,
            day_threshold=self.config.temporal_pattern.day_threshold
        )
        
        self.merchant_analyzer = MerchantPatternAnalyzer()
        
        self.confidence_calculator = ConfidenceScoreCalculator(
            weights=self.config.confidence_weights
        )
    
    def detect_recurring_patterns(
        self,
        user_id: str,
        transactions: List[Transaction],
        min_occurrences: int = MIN_CLUSTER_SIZE,
        min_confidence: float = MIN_CONFIDENCE,
        eps: float = DEFAULT_EPS,
        accounts_map: Optional[Dict[uuid.UUID, Account]] = None
    ) -> List[RecurringChargePatternCreate]:
        """
        Detect recurring charge patterns in transaction history.
        
        Args:
            user_id: User ID for pattern ownership
            transactions: List of Transaction objects
            min_occurrences: Minimum number of occurrences to form a pattern
            min_confidence: Minimum confidence score to include pattern
            eps: DBSCAN epsilon parameter (neighborhood radius)
            accounts_map: Optional dictionary mapping account_id to Account objects
            
        Returns:
            List of RecurringChargePatternCreate objects
        """
        if len(transactions) < min_occurrences:
            logger.info(f"Insufficient transactions ({len(transactions)}) for pattern detection")
            return []
        
        # Log detection mode
        if self.use_account_features and accounts_map:
            logger.info(
                f"Starting account-aware pattern detection for user {user_id} "
                f"with {len(transactions)} transactions across {len(accounts_map)} accounts"
            )
        else:
            logger.info(f"Starting pattern detection for user {user_id} with {len(transactions)} transactions")
        
        with MLPerformanceTracker("recurring_charge_detection") as tracker:
            tracker.set_transaction_count(len(transactions))
            
            # Stage 1: Feature extraction
            with tracker.stage("feature_extraction"):
                if self.use_account_features and accounts_map:
                    feature_matrix, _ = self.feature_service.extract_features_batch(
                        transactions, accounts_map
                    )
                else:
                    feature_matrix, _ = self.feature_service.extract_features_batch(transactions)
            
            # Stage 2: DBSCAN clustering
            with tracker.stage("clustering"):
                clusters = self._perform_clustering(feature_matrix, eps, len(transactions))
                tracker.set_clusters_identified(len(set(clusters)) - (1 if -1 in clusters else 0))
            
            # Stage 3: Pattern analysis
            with tracker.stage("pattern_analysis"):
                patterns = self._analyze_clusters(
                    user_id, transactions, clusters, min_occurrences, min_confidence,
                    accounts_map=accounts_map
                )
                tracker.set_patterns_detected(len(patterns))
            
            logger.info(f"Detection complete: found {len(patterns)} patterns")
        
        return patterns
    
    def _perform_clustering(
        self,
        feature_matrix: np.ndarray,
        eps: float,
        n_samples: int
    ) -> np.ndarray:
        """
        Perform DBSCAN clustering on feature matrix.
        
        Args:
            feature_matrix: Feature matrix of shape (n_samples, n_features)
            eps: DBSCAN epsilon parameter
            n_samples: Number of samples
            
        Returns:
            Array of cluster labels (-1 for noise)
        """
        min_samples = max(
            self.config.clustering.min_cluster_size,
            int(n_samples * self.config.clustering.min_samples_ratio)
        )
        
        logger.info(f"Running DBSCAN with eps={eps}, min_samples={min_samples}")
        
        dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
        cluster_labels = dbscan.fit_predict(feature_matrix)
        
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        n_noise = int(np.sum(cluster_labels == -1))
        
        logger.info(f"DBSCAN complete: {n_clusters} clusters, {n_noise} noise points")
        
        return cluster_labels
    
    def _analyze_clusters(
        self,
        user_id: str,
        transactions: List[Transaction],
        cluster_labels: np.ndarray,
        min_occurrences: int,
        min_confidence: float,
        accounts_map: Optional[Dict[uuid.UUID, Account]] = None
    ) -> List[RecurringChargePatternCreate]:
        """
        Analyze clusters to extract recurring patterns.
        
        Args:
            user_id: User ID
            transactions: List of transactions
            cluster_labels: Cluster labels from DBSCAN
            min_occurrences: Minimum occurrences
            min_confidence: Minimum confidence
            accounts_map: Optional account mapping for account-aware adjustments
            
        Returns:
            List of pattern create objects
        """
        patterns = []
        unique_clusters = set(cluster_labels)
        unique_clusters.discard(-1)  # Remove noise label
        
        for cluster_id in unique_clusters:
            # Get transactions in this cluster
            cluster_mask = cluster_labels == cluster_id
            cluster_transactions = [txn for i, txn in enumerate(transactions) if cluster_mask[i]]
            
            if len(cluster_transactions) < min_occurrences:
                continue
            
            # Sort by date
            cluster_transactions.sort(key=lambda t: t.date)
            
            # Analyze pattern using specialized analyzers
            pattern = self._analyze_pattern(
                user_id, cluster_transactions, cluster_id, accounts_map
            )
            
            if pattern and pattern.confidence_score >= min_confidence:
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_pattern(
        self,
        user_id: str,
        cluster_transactions: List[Transaction],
        cluster_id: int,
        accounts_map: Optional[Dict[uuid.UUID, Account]] = None
    ) -> Optional[RecurringChargePatternCreate]:
        """
        Analyze a cluster using specialized analyzers.
        
        Args:
            user_id: User ID
            cluster_transactions: Transactions in cluster (sorted by date)
            cluster_id: Cluster ID
            accounts_map: Optional account mapping
            
        Returns:
            RecurringChargePatternCreate or None if pattern invalid
        """
        # Use FrequencyAnalyzer to detect frequency
        frequency = self.frequency_analyzer.detect_frequency(cluster_transactions)
        
        # Use TemporalPatternAnalyzer to detect temporal patterns
        temporal_info = self.temporal_analyzer.analyze(cluster_transactions)
        
        # Use MerchantPatternAnalyzer to extract merchant pattern
        merchant_pattern = self.merchant_analyzer.extract_pattern(cluster_transactions)
        
        # Calculate amount statistics
        amounts = [abs(float(txn.amount)) for txn in cluster_transactions]
        amount_mean = Decimal(str(np.mean(amounts)))
        amount_std = Decimal(str(np.std(amounts)))
        amount_min = Decimal(str(min(amounts)))
        amount_max = Decimal(str(max(amounts)))
        
        # Use ConfidenceScoreCalculator to calculate base confidence
        base_confidence = self.confidence_calculator.calculate(
            cluster_transactions, temporal_info
        )
        
        # Apply account-aware confidence adjustments if available
        if accounts_map and self.use_account_features:
            confidence_score = self.confidence_calculator.apply_account_adjustments(
                base_confidence, cluster_transactions, frequency, 
                merchant_pattern, accounts_map
            )
        else:
            confidence_score = base_confidence
        
        # Create pattern
        pattern = RecurringChargePatternCreate(
            userId=user_id,
            merchantPattern=merchant_pattern,
            frequency=frequency,
            temporalPatternType=temporal_info['pattern_type'],
            dayOfWeek=temporal_info.get('day_of_week'),
            dayOfMonth=temporal_info.get('day_of_month'),
            toleranceDays=2,
            amountMean=amount_mean,
            amountStd=amount_std,
            amountMin=amount_min,
            amountMax=amount_max,
            amountTolerancePct=10.0,
            confidenceScore=confidence_score,
            transactionCount=len(cluster_transactions),
            firstOccurrence=cluster_transactions[0].date,
            lastOccurrence=cluster_transactions[-1].date,
            clusterId=cluster_id,
            active=True
        )
        
        return pattern
