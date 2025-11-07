"""
Recurring Charge Detection Service.

This module implements ML-based recurring charge detection using DBSCAN clustering
and pattern analysis. Detects patterns in transaction history and calculates confidence scores.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from decimal import Decimal
from collections import Counter
from calendar import monthrange

import numpy as np
from sklearn.cluster import DBSCAN
import holidays

from models.transaction import Transaction
from models.recurring_charge import (
    RecurringChargePattern,
    RecurringChargePatternCreate,
    RecurrenceFrequency,
    TemporalPatternType
)
from services.recurring_charge_feature_service import RecurringChargeFeatureService
from utils.ml_performance import MLPerformanceTracker

logger = logging.getLogger(__name__)

# DBSCAN parameters
DEFAULT_EPS = 0.5  # Neighborhood radius
MIN_SAMPLES_RATIO = 0.01  # Minimum samples as ratio of dataset size
MIN_CLUSTER_SIZE = 3  # Minimum transactions to form a pattern
MIN_CONFIDENCE = 0.6  # Minimum confidence to surface pattern

# Frequency thresholds (in days)
FREQUENCY_THRESHOLDS = {
    RecurrenceFrequency.DAILY: (0.5, 1.5),
    RecurrenceFrequency.WEEKLY: (6, 8),
    RecurrenceFrequency.BI_WEEKLY: (12, 16),
    RecurrenceFrequency.SEMI_MONTHLY: (13, 17),
    RecurrenceFrequency.MONTHLY: (25, 35),
    RecurrenceFrequency.BI_MONTHLY: (55, 65),
    RecurrenceFrequency.QUARTERLY: (85, 95),
    RecurrenceFrequency.SEMI_ANNUALLY: (175, 190),
    RecurrenceFrequency.ANNUALLY: (355, 375),
}


class RecurringChargeDetectionService:
    """
    Service for detecting recurring charge patterns using ML.
    
    Uses DBSCAN clustering to group similar transactions, then analyzes
    each cluster to identify temporal patterns, frequencies, and merchant names.
    """
    
    def __init__(self, country_code: str = 'US'):
        """
        Initialize the detection service.
        
        Args:
            country_code: Country code for holiday detection (default: US)
        """
        self.country_code = country_code
        self.holidays = holidays.country_holidays(country_code)
        self.feature_service = RecurringChargeFeatureService(country_code)
    
    def detect_recurring_patterns(
        self,
        user_id: str,
        transactions: List[Transaction],
        min_occurrences: int = MIN_CLUSTER_SIZE,
        min_confidence: float = MIN_CONFIDENCE,
        eps: float = DEFAULT_EPS
    ) -> List[RecurringChargePatternCreate]:
        """
        Detect recurring charge patterns in transaction history.
        
        Args:
            user_id: User ID for pattern ownership
            transactions: List of Transaction objects
            min_occurrences: Minimum number of occurrences to form a pattern
            min_confidence: Minimum confidence score to include pattern
            eps: DBSCAN epsilon parameter (neighborhood radius)
            
        Returns:
            List of RecurringChargePatternCreate objects
        """
        if len(transactions) < min_occurrences:
            logger.info(f"Insufficient transactions ({len(transactions)}) for pattern detection")
            return []
        
        logger.info(f"Starting pattern detection for user {user_id} with {len(transactions)} transactions")
        
        with MLPerformanceTracker("recurring_charge_detection") as tracker:
            # Stage 1: Feature extraction
            tracker.start_stage("feature_extraction")
            feature_matrix, vectorizer = self.feature_service.extract_features_batch(transactions)
            tracker.end_stage("feature_extraction")
            
            # Stage 2: DBSCAN clustering
            tracker.start_stage("clustering")
            clusters = self._perform_clustering(feature_matrix, eps, len(transactions))
            tracker.end_stage("clustering")
            
            # Stage 3: Pattern analysis
            tracker.start_stage("pattern_analysis")
            patterns = self._analyze_clusters(
                user_id, transactions, clusters, min_occurrences, min_confidence
            )
            tracker.end_stage("pattern_analysis")
            
            logger.info(f"Detection complete: found {len(patterns)} patterns")
            tracker.log_metrics()
        
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
        min_samples = max(MIN_CLUSTER_SIZE, int(n_samples * MIN_SAMPLES_RATIO))
        
        logger.info(f"Running DBSCAN with eps={eps}, min_samples={min_samples}")
        
        dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
        cluster_labels = dbscan.fit_predict(feature_matrix)
        
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        n_noise = list(cluster_labels).count(-1)
        
        logger.info(f"DBSCAN complete: {n_clusters} clusters, {n_noise} noise points")
        
        return cluster_labels
    
    def _analyze_clusters(
        self,
        user_id: str,
        transactions: List[Transaction],
        cluster_labels: np.ndarray,
        min_occurrences: int,
        min_confidence: float
    ) -> List[RecurringChargePatternCreate]:
        """
        Analyze clusters to extract recurring patterns.
        
        Args:
            user_id: User ID
            transactions: List of transactions
            cluster_labels: Cluster labels from DBSCAN
            min_occurrences: Minimum occurrences
            min_confidence: Minimum confidence
            
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
            
            # Analyze pattern
            pattern = self._analyze_pattern(user_id, cluster_transactions, cluster_id)
            
            if pattern and pattern.confidence_score >= min_confidence:
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_pattern(
        self,
        user_id: str,
        cluster_transactions: List[Transaction],
        cluster_id: int
    ) -> Optional[RecurringChargePatternCreate]:
        """
        Analyze a cluster of transactions to extract pattern details.
        
        Args:
            user_id: User ID
            cluster_transactions: Transactions in cluster (sorted by date)
            cluster_id: Cluster ID
            
        Returns:
            RecurringChargePatternCreate or None if pattern invalid
        """
        # Detect frequency
        frequency = self._detect_frequency(cluster_transactions)
        
        # Detect temporal pattern
        temporal_info = self._analyze_temporal_pattern(cluster_transactions)
        
        # Extract merchant pattern
        merchant_pattern = self._extract_merchant_pattern(cluster_transactions)
        
        # Calculate amount statistics
        amounts = [abs(float(txn.amount)) for txn in cluster_transactions]
        amount_mean = Decimal(str(np.mean(amounts)))
        amount_std = Decimal(str(np.std(amounts)))
        amount_min = Decimal(str(min(amounts)))
        amount_max = Decimal(str(max(amounts)))
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            cluster_transactions, temporal_info
        )
        
        # Create pattern
        pattern = RecurringChargePatternCreate(
            userId=user_id,
            merchantPattern=merchant_pattern,
            frequency=frequency,
            temporalPatternType=temporal_info['pattern_type'],
            dayOfWeek=temporal_info.get('day_of_week'),
            dayOfMonth=temporal_info.get('day_of_month'),
            toleranceDays=2,  # Default tolerance
            amountMean=amount_mean,
            amountStd=amount_std,
            amountMin=amount_min,
            amountMax=amount_max,
            amountTolerancePct=10.0,  # Default 10% tolerance
            confidenceScore=confidence_score,
            transactionCount=len(cluster_transactions),
            firstOccurrence=cluster_transactions[0].date,
            lastOccurrence=cluster_transactions[-1].date,
            clusterId=cluster_id,
            active=True
        )
        
        return pattern
    
    def _detect_frequency(self, cluster_transactions: List[Transaction]) -> RecurrenceFrequency:
        """
        Detect recurrence frequency based on interval between transactions.
        
        Args:
            cluster_transactions: Sorted list of transactions
            
        Returns:
            RecurrenceFrequency enum
        """
        if len(cluster_transactions) < 2:
            return RecurrenceFrequency.IRREGULAR
        
        # Calculate intervals in days
        intervals = []
        for i in range(len(cluster_transactions) - 1):
            days = (cluster_transactions[i + 1].date - cluster_transactions[i].date) / (1000 * 60 * 60 * 24)
            intervals.append(days)
        
        mean_interval = np.mean(intervals)
        
        # Match to frequency category
        for frequency, (min_days, max_days) in FREQUENCY_THRESHOLDS.items():
            if min_days <= mean_interval <= max_days:
                return frequency
        
        return RecurrenceFrequency.IRREGULAR
    
    def _analyze_temporal_pattern(
        self,
        cluster_transactions: List[Transaction]
    ) -> Dict[str, Any]:
        """
        Analyze temporal pattern in cluster transactions.
        
        Detects pattern type in priority order:
        1. Last working day
        2. First working day
        3. Last weekday of month
        4. First weekday of month
        5. Specific day of month
        6. Specific day of week
        7. Flexible (no clear pattern)
        
        Args:
            cluster_transactions: List of transactions
            
        Returns:
            Dict with pattern_type, optional day_of_week/day_of_month, and consistency
        """
        dates = [datetime.fromtimestamp(txn.date / 1000, tz=timezone.utc) for txn in cluster_transactions]
        
        # Check last working day pattern
        last_working_matches = sum(1 for dt in dates if self._is_last_working_day(dt))
        last_working_pct = last_working_matches / len(dates)
        if last_working_pct >= 0.70:
            return {
                'pattern_type': TemporalPatternType.LAST_WORKING_DAY,
                'temporal_consistency': last_working_pct
            }
        
        # Check first working day pattern
        first_working_matches = sum(1 for dt in dates if self._is_first_working_day(dt))
        first_working_pct = first_working_matches / len(dates)
        if first_working_pct >= 0.70:
            return {
                'pattern_type': TemporalPatternType.FIRST_WORKING_DAY,
                'temporal_consistency': first_working_pct
            }
        
        # Check weekday-of-month patterns (last/first Thursday, etc.)
        weekday_pattern = self._detect_weekday_of_month_pattern(dates)
        if weekday_pattern:
            return weekday_pattern
        
        # Check specific day of month pattern
        days_of_month = [dt.day for dt in dates]
        day_counter = Counter(days_of_month)
        most_common_day, day_count = day_counter.most_common(1)[0]
        day_of_month_pct = day_count / len(dates)
        if day_of_month_pct >= 0.60:
            return {
                'pattern_type': TemporalPatternType.DAY_OF_MONTH,
                'day_of_month': most_common_day,
                'temporal_consistency': day_of_month_pct
            }
        
        # Check specific day of week pattern
        days_of_week = [dt.weekday() for dt in dates]
        weekday_counter = Counter(days_of_week)
        most_common_weekday, weekday_count = weekday_counter.most_common(1)[0]
        day_of_week_pct = weekday_count / len(dates)
        if day_of_week_pct >= 0.60:
            return {
                'pattern_type': TemporalPatternType.DAY_OF_WEEK,
                'day_of_week': most_common_weekday,
                'temporal_consistency': day_of_week_pct
            }
        
        # No clear pattern
        return {
            'pattern_type': TemporalPatternType.FLEXIBLE,
            'temporal_consistency': 0.5
        }
    
    def _detect_weekday_of_month_pattern(
        self,
        dates: List[datetime]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if transactions follow 'Nth weekday of month' pattern.
        
        Examples: Last Thursday, First Friday, Second Tuesday
        
        Args:
            dates: List of datetime objects
            
        Returns:
            Dict with pattern info or None
        """
        if len(dates) < 3:
            return None
        
        weekday_info = []
        for dt in dates:
            day_of_week = dt.weekday()
            day = dt.day
            days_in_month = monthrange(dt.year, dt.month)[1]
            
            # Which occurrence of this weekday? (1-5)
            occurrence = (day - 1) // 7 + 1
            
            # Is this the LAST occurrence?
            days_remaining = days_in_month - day
            is_last = days_remaining < 7
            
            # Is this the FIRST occurrence?
            is_first = occurrence == 1
            
            weekday_info.append({
                'day_of_week': day_of_week,
                'occurrence': occurrence,
                'is_last': is_last,
                'is_first': is_first
            })
        
        # Check for "last weekday of month" pattern
        last_weekday_matches = [w for w in weekday_info if w['is_last']]
        last_weekday_pct = len(last_weekday_matches) / len(weekday_info)
        
        if last_weekday_pct >= 0.70:
            weekdays = [w['day_of_week'] for w in last_weekday_matches]
            most_common_weekday = Counter(weekdays).most_common(1)[0][0]
            
            return {
                'pattern_type': TemporalPatternType.LAST_DAY_OF_MONTH,  # Using existing enum
                'day_of_week': most_common_weekday,
                'temporal_consistency': last_weekday_pct
            }
        
        # Check for "first weekday of month" pattern
        first_weekday_matches = [w for w in weekday_info if w['is_first']]
        first_weekday_pct = len(first_weekday_matches) / len(weekday_info)
        
        if first_weekday_pct >= 0.70:
            weekdays = [w['day_of_week'] for w in first_weekday_matches]
            most_common_weekday = Counter(weekdays).most_common(1)[0][0]
            
            return {
                'pattern_type': TemporalPatternType.FIRST_DAY_OF_MONTH,  # Using existing enum
                'day_of_week': most_common_weekday,
                'temporal_consistency': first_weekday_pct
            }
        
        return None
    
    def _extract_merchant_pattern(self, cluster_transactions: List[Transaction]) -> str:
        """
        Extract common merchant pattern from transaction descriptions.
        
        Finds the longest common substring or prefix that appears in
        most transaction descriptions.
        
        Args:
            cluster_transactions: List of transactions
            
        Returns:
            Merchant pattern string
        """
        descriptions = [txn.description.upper() for txn in cluster_transactions]
        
        if not descriptions:
            return "UNKNOWN"
        
        # Start with first description
        common = descriptions[0]
        
        # Find longest common substring
        for desc in descriptions[1:]:
            # Find longest common substring between common and desc
            new_common = self._longest_common_substring(common, desc)
            if new_common:
                common = new_common
            else:
                # Fall back to first word if no common substring
                words = descriptions[0].split()
                common = words[0] if words else "UNKNOWN"
                break
        
        # Clean up the pattern
        common = common.strip()
        
        # If too short, use first word from first description
        if len(common) < 3:
            words = descriptions[0].split()
            common = words[0] if words else "UNKNOWN"
        
        return common[:50]  # Limit length
    
    def _longest_common_substring(self, s1: str, s2: str) -> str:
        """
        Find longest common substring between two strings.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Longest common substring
        """
        m = len(s1)
        n = len(s2)
        
        # Create DP table
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        max_len = 0
        end_pos = 0
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                    if dp[i][j] > max_len:
                        max_len = dp[i][j]
                        end_pos = i
        
        return s1[end_pos - max_len:end_pos] if max_len > 0 else ""
    
    def _calculate_confidence_score(
        self,
        cluster_transactions: List[Transaction],
        temporal_info: Dict[str, Any]
    ) -> float:
        """
        Calculate multi-factor confidence score (0.0-1.0).
        
        Factors:
        - Interval regularity (30%)
        - Amount regularity (20%)
        - Sample size (20%)
        - Temporal consistency (30%)
        
        Args:
            cluster_transactions: List of transactions
            temporal_info: Temporal pattern info
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # 1. Interval Regularity (30% weight)
        if len(cluster_transactions) >= 2:
            intervals = []
            for i in range(len(cluster_transactions) - 1):
                days = (cluster_transactions[i + 1].date - cluster_transactions[i].date) / (1000 * 60 * 60 * 24)
                intervals.append(days)
            
            mean_interval = np.mean(intervals)
            std_interval = np.std(intervals)
            interval_regularity = 1.0 / (1.0 + std_interval / (mean_interval + 1))
        else:
            interval_regularity = 0.5
        
        # 2. Amount Regularity (20% weight)
        amounts = [abs(float(txn.amount)) for txn in cluster_transactions]
        mean_amount = np.mean(amounts)
        std_amount = np.std(amounts)
        amount_regularity = 1.0 / (1.0 + std_amount / (abs(mean_amount) + 1))
        
        # 3. Sample Size Score (20% weight)
        # More samples = higher confidence, cap at 12 (1 year monthly)
        sample_size_score = min(1.0, len(cluster_transactions) / 12)
        
        # 4. Temporal Consistency (30% weight)
        temporal_consistency = temporal_info.get('temporal_consistency', 0.5)
        
        # Weighted sum
        confidence = (
            0.30 * interval_regularity +
            0.20 * amount_regularity +
            0.20 * sample_size_score +
            0.30 * temporal_consistency
        )
        
        return round(confidence, 2)
    
    def _is_first_working_day(self, dt: datetime) -> bool:
        """Check if date is the first working day of the month."""
        year = dt.year
        month = dt.month
        
        for day in range(1, 32):
            try:
                candidate = datetime(year, month, day, tzinfo=timezone.utc)
                if candidate.weekday() < 5 and candidate.date() not in self.holidays:
                    return candidate.date() == dt.date()
            except ValueError:
                break
        
        return False
    
    def _is_last_working_day(self, dt: datetime) -> bool:
        """Check if date is the last working day of the month."""
        year = dt.year
        month = dt.month
        
        # Get last day of month
        if month == 12:
            next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        last_day = (next_month - datetime(year, month, 1, tzinfo=timezone.utc)).days
        
        # Search backwards for first working day
        for day in range(last_day, 0, -1):
            candidate = datetime(year, month, day, tzinfo=timezone.utc)
            if candidate.weekday() < 5 and candidate.date() not in self.holidays:
                return candidate.date() == dt.date()
        
        return False

