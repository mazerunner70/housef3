"""
Frequency analyzer for recurring charge detection.

Analyzes transaction intervals to detect recurrence frequency.
"""

import logging
from typing import List, Dict, Tuple

import numpy as np

from models.transaction import Transaction
from models.recurring_charge import RecurrenceFrequency

logger = logging.getLogger(__name__)


class FrequencyAnalyzer:
    """
    Analyzes transaction intervals to detect recurrence frequency.
    
    Calculates mean interval between transactions and matches it to
    standard frequency categories (daily, weekly, monthly, etc.).
    """
    
    def __init__(self, frequency_thresholds: Dict[RecurrenceFrequency, Tuple[float, float]]):
        """
        Initialize the frequency analyzer.
        
        Args:
            frequency_thresholds: Dictionary mapping RecurrenceFrequency to (min_days, max_days) tuples
        """
        self.frequency_thresholds = frequency_thresholds
    
    def detect_frequency(self, cluster_transactions: List[Transaction]) -> RecurrenceFrequency:
        """
        Detect recurrence frequency based on interval between transactions.
        
        Args:
            cluster_transactions: Sorted list of transactions
            
        Returns:
            RecurrenceFrequency enum indicating the detected frequency
        """
        if len(cluster_transactions) < 2:
            return RecurrenceFrequency.IRREGULAR
        
        # Calculate intervals in days
        intervals = self._calculate_intervals(cluster_transactions)
        mean_interval = np.mean(intervals)
        
        # Match to frequency category
        return self._match_to_frequency(mean_interval)
    
    def _calculate_intervals(self, transactions: List[Transaction]) -> List[float]:
        """
        Calculate day intervals between consecutive transactions.
        
        Args:
            transactions: Sorted list of transactions
            
        Returns:
            List of intervals in days
        """
        intervals = []
        for i in range(len(transactions) - 1):
            days = (transactions[i + 1].date - transactions[i].date) / (1000 * 60 * 60 * 24)
            intervals.append(days)
        return intervals
    
    def _match_to_frequency(self, mean_interval: float) -> RecurrenceFrequency:
        """
        Match mean interval to frequency category.
        
        Args:
            mean_interval: Mean interval in days
            
        Returns:
            RecurrenceFrequency that best matches the interval
        """
        for frequency, (min_days, max_days) in self.frequency_thresholds.items():
            if min_days <= mean_interval <= max_days:
                return frequency
        
        return RecurrenceFrequency.IRREGULAR
    
    def get_interval_statistics(self, cluster_transactions: List[Transaction]) -> Dict[str, float]:
        """
        Calculate detailed interval statistics.
        
        Args:
            cluster_transactions: List of transactions
            
        Returns:
            Dictionary with mean, std, min, max intervals
        """
        if len(cluster_transactions) < 2:
            return {
                'mean': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0
            }
        
        intervals = self._calculate_intervals(cluster_transactions)
        
        return {
            'mean': float(np.mean(intervals)),
            'std': float(np.std(intervals)),
            'min': float(min(intervals)),
            'max': float(max(intervals))
        }

