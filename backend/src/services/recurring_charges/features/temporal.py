"""
Temporal feature extractor.

Extracts 17 temporal features from transactions that capture when charges occur.
"""

import math
from typing import List
from datetime import datetime, timezone

import numpy as np
import holidays

from models.transaction import Transaction
from utils.temporal_utils import is_first_working_day, is_last_working_day
from services.recurring_charges.features.base import BaseFeatureExtractor


class TemporalFeatureExtractor(BaseFeatureExtractor):
    """
    Extracts 17 temporal features from transactions.
    
    Features capture patterns in when charges occur:
    - Circular encoding (8): day_of_week, day_of_month, month_position, week_of_month
    - Boolean flags (8): working_day, first/last working day, first/last weekday, 
                         weekend, first/last day
    - Position (1): normalized_day_position
    """
    
    FEATURE_SIZE = 17
    
    def __init__(self, country_code: str = 'US'):
        """
        Initialize temporal feature extractor.
        
        Args:
            country_code: Country code for holiday detection (default: US)
        """
        self.country_code = country_code
        self.holidays = holidays.country_holidays(country_code)
    
    @property
    def feature_size(self) -> int:
        """Return the number of temporal features (17)."""
        return self.FEATURE_SIZE
    
    def extract_batch(self, transactions: List[Transaction], **kwargs) -> np.ndarray:
        """
        Extract temporal features for a batch of transactions.
        
        Args:
            transactions: List of Transaction objects
            **kwargs: Additional arguments (unused for temporal features)
            
        Returns:
            Array of shape (n_transactions, 17) with temporal features
        """
        features = np.array([self.extract_single(tx) for tx in transactions])
        self.validate_output(features, len(transactions))
        return features
    
    def extract_single(self, transaction: Transaction) -> List[float]:
        """
        Extract 17 temporal features from a single transaction.
        
        Args:
            transaction: Transaction object
            
        Returns:
            List of 17 float values representing temporal features
        """
        # Convert timestamp (ms) to datetime
        dt = datetime.fromtimestamp(transaction.date / 1000, tz=timezone.utc)
        
        # Extract basic temporal components
        day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
        day_of_month = dt.day
        month = dt.month
        year = dt.year
        
        # Calculate days in month
        if month == 12:
            next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        days_in_month = (next_month - datetime(year, month, 1, tzinfo=timezone.utc)).days
        
        # Calculate week of month (1-5)
        week_of_month = (day_of_month - 1) // 7 + 1
        
        # Circular encoding (prevents discontinuity at boundaries)
        day_of_week_sin = math.sin(2 * math.pi * day_of_week / 7)
        day_of_week_cos = math.cos(2 * math.pi * day_of_week / 7)
        
        day_of_month_sin = math.sin(2 * math.pi * day_of_month / 31)
        day_of_month_cos = math.cos(2 * math.pi * day_of_month / 31)
        
        month_position_sin = math.sin(2 * math.pi * (day_of_month - 1) / days_in_month)
        month_position_cos = math.cos(2 * math.pi * (day_of_month - 1) / days_in_month)
        
        week_of_month_sin = math.sin(2 * math.pi * week_of_month / 5)
        week_of_month_cos = math.cos(2 * math.pi * week_of_month / 5)
        
        # Boolean flags
        is_weekend = 1.0 if day_of_week >= 5 else 0.0  # Saturday or Sunday
        is_working_day_flag = 1.0 if (day_of_week < 5 and dt.date() not in self.holidays) else 0.0
        
        # First/last day flags
        is_first_day = 1.0 if day_of_month == 1 else 0.0
        is_last_day = 1.0 if day_of_month == days_in_month else 0.0
        
        # First/last working day
        is_first_working_day_flag = 1.0 if is_first_working_day(dt, self.holidays) else 0.0
        is_last_working_day_flag = 1.0 if is_last_working_day(dt, self.holidays) else 0.0
        
        # First/last weekday of month
        is_first_weekday = 1.0 if self._is_first_weekday_of_month(dt) else 0.0
        is_last_weekday = 1.0 if self._is_last_weekday_of_month(dt) else 0.0
        
        # Normalized day position (0.0 to 1.0)
        normalized_day_position = (day_of_month - 1) / (days_in_month - 1) if days_in_month > 1 else 0.5
        
        return [
            # Circular encoding (8 features)
            day_of_week_sin, day_of_week_cos,
            day_of_month_sin, day_of_month_cos,
            month_position_sin, month_position_cos,
            week_of_month_sin, week_of_month_cos,
            # Boolean flags (8 features)
            is_working_day_flag, is_first_working_day_flag, is_last_working_day_flag,
            is_first_weekday, is_last_weekday, is_weekend,
            is_first_day, is_last_day,
            # Position (1 feature)
            normalized_day_position
        ]
    
    def _is_first_weekday_of_month(self, dt: datetime) -> bool:
        """
        Check if date is the first occurrence of its weekday in the month.
        
        Args:
            dt: Datetime to check
            
        Returns:
            True if this is the first occurrence of this weekday in the month
        """
        year = dt.year
        month = dt.month
        target_weekday = dt.weekday()
        
        for day in range(1, 8):  # First week
            try:
                candidate = datetime(year, month, day, tzinfo=timezone.utc)
                if candidate.weekday() == target_weekday:
                    return candidate.date() == dt.date()
            except ValueError:
                break
        
        return False
    
    def _is_last_weekday_of_month(self, dt: datetime) -> bool:
        """
        Check if date is the last occurrence of its weekday in the month.
        
        Args:
            dt: Datetime to check
            
        Returns:
            True if this is the last occurrence of this weekday in the month
        """
        year = dt.year
        month = dt.month
        target_weekday = dt.weekday()
        
        # Get last day of month
        if month == 12:
            next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        last_day = (next_month - datetime(year, month, 1, tzinfo=timezone.utc)).days
        
        # Search backwards for last occurrence of target weekday
        for day in range(last_day, 0, -1):
            try:
                candidate = datetime(year, month, day, tzinfo=timezone.utc)
                if candidate.weekday() == target_weekday:
                    return candidate.date() == dt.date()
            except ValueError:
                continue
        
        return False

