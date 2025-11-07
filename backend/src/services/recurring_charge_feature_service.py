"""
Recurring Charge Feature Engineering Service.

This module extracts features from transactions for ML-based recurring charge detection.
Produces a 67-dimensional feature vector:
- 17 temporal features (circular encoding + boolean flags)
- 1 amount feature (log-scaled and normalized)
- 49 description features (TF-IDF vectorization, reduced from 50 to fit total)
"""

import logging
import math
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from decimal import Decimal

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import csr_matrix
import holidays

from models.transaction import Transaction
from utils.temporal_utils import is_first_working_day, is_last_working_day

logger = logging.getLogger(__name__)

# Constants for feature engineering
FEATURE_VECTOR_SIZE = 67
TEMPORAL_FEATURE_SIZE = 17
AMOUNT_FEATURE_SIZE = 1
DESCRIPTION_FEATURE_SIZE = 49  # TF-IDF features


class RecurringChargeFeatureService:
    """
    Service for extracting ML features from transactions.
    
    Features are designed to capture patterns in:
    - Temporal behavior (when charges occur)
    - Amount patterns (how much charges cost)
    - Description patterns (merchant names)
    """
    
    def __init__(self, country_code: str = 'US'):
        """
        Initialize the feature service.
        
        Args:
            country_code: Country code for holiday detection (default: US)
        """
        self.country_code = country_code
        self.holidays = holidays.country_holidays(country_code)
        self.tfidf_vectorizer = None  # Initialized during fit
        
    def extract_features_batch(
        self,
        transactions: List[Transaction]
    ) -> Tuple[np.ndarray, Optional[TfidfVectorizer]]:
        """
        Extract features from a batch of transactions.
        
        Args:
            transactions: List of Transaction objects
            
        Returns:
            Tuple of (feature_matrix, fitted_vectorizer)
            - feature_matrix: numpy array of shape (n_transactions, 67)
            - fitted_vectorizer: Fitted TF-IDF vectorizer for descriptions (None if empty or failed)
        """
        if not transactions:
            return np.array([]).reshape(0, FEATURE_VECTOR_SIZE), None
            
        logger.info(f"Extracting features from {len(transactions)} transactions")
        
        # Extract temporal features
        temporal_features = np.array([
            self.extract_temporal_features(txn) for txn in transactions
        ])
        
        # Extract amount features
        amount_features = self.extract_amount_features_batch(transactions)
        
        # Extract description features
        description_features, vectorizer = self.extract_description_features_batch(transactions)
        
        # Combine all features
        feature_matrix = np.hstack([
            temporal_features,
            amount_features,
            description_features
        ])
        
        logger.info(f"Feature extraction complete: shape={feature_matrix.shape}")
        
        return feature_matrix, vectorizer
    
    def extract_temporal_features(self, transaction: Transaction) -> List[float]:
        """
        Extract 17 temporal features from a transaction.
        
        Features:
        - Circular encoding (8): day_of_week (sin/cos), day_of_month (sin/cos),
          month_position (sin/cos), week_of_month (sin/cos)
        - Boolean flags (8): is_working_day, is_first_working_day, is_last_working_day,
          is_first_weekday, is_last_weekday, is_weekend, is_first_day, is_last_day
        - Position (1): normalized_day_position
        
        Args:
            transaction: Transaction object
            
        Returns:
            List of 17 float values
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
        
        # Circular encoding
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
        is_working_day = 1.0 if (day_of_week < 5 and dt.date() not in self.holidays) else 0.0
        
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
            is_working_day, is_first_working_day_flag, is_last_working_day_flag,
            is_first_weekday, is_last_weekday, is_weekend,
            is_first_day, is_last_day,
            # Position (1 feature)
            normalized_day_position
        ]
    
    def extract_amount_features_batch(self, transactions: List[Transaction]) -> np.ndarray:
        """
        Extract amount features from a batch of transactions.
        
        Uses log-scale transformation and normalization to handle
        wide range of transaction amounts.
        
        Args:
            transactions: List of Transaction objects
            
        Returns:
            numpy array of shape (n_transactions, 1)
        """
        # Extract amounts as floats
        amounts = np.array([float(abs(txn.amount)) for txn in transactions])
        
        # Log-scale transformation (add 1 to avoid log(0))
        log_amounts = np.log1p(amounts)
        
        # Normalize to [0, 1] range
        if len(log_amounts) > 1:
            min_val = log_amounts.min()
            max_val = log_amounts.max()
            if max_val > min_val:
                normalized = (log_amounts - min_val) / (max_val - min_val)
            else:
                normalized = np.ones_like(log_amounts) * 0.5
        else:
            normalized = np.array([0.5])
        
        return normalized.reshape(-1, 1)
    
    def extract_description_features_batch(
        self,
        transactions: List[Transaction]
    ) -> Tuple[np.ndarray, Optional[TfidfVectorizer]]:
        """
        Extract description features using TF-IDF vectorization.
        
        Converts transaction descriptions into a 49-dimensional vector
        that captures merchant name patterns.
        
        Args:
            transactions: List of Transaction objects
            
        Returns:
            Tuple of (feature_matrix, vectorizer)
            - feature_matrix: numpy array of shape (n_transactions, 49)
            - vectorizer: Fitted TfidfVectorizer (None if vectorization failed)
        """
        # Extract descriptions
        descriptions = [txn.description.lower() for txn in transactions if txn.description]
        
        # Initialize and fit TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=DESCRIPTION_FEATURE_SIZE,
            ngram_range=(1, 2),  # Unigrams and bigrams
            min_df=1,  # Minimum document frequency
            max_df=0.95,  # Maximum document frequency (ignore very common words)
            strip_accents='unicode',
            lowercase=True,
            token_pattern=r'\b[a-z]{2,}\b'  # Words with 2+ letters
        )
        
        try:
            tfidf_matrix: csr_matrix = vectorizer.fit_transform(descriptions)  # type: ignore[assignment]
            feature_matrix = tfidf_matrix.toarray()
            
            # Ensure we have exactly DESCRIPTION_FEATURE_SIZE features
            if feature_matrix.shape[1] < DESCRIPTION_FEATURE_SIZE:
                # Pad with zeros if we have fewer features
                padding = np.zeros((feature_matrix.shape[0], DESCRIPTION_FEATURE_SIZE - feature_matrix.shape[1]))
                feature_matrix = np.hstack([feature_matrix, padding])
            elif feature_matrix.shape[1] > DESCRIPTION_FEATURE_SIZE:
                # Truncate if we have more features (shouldn't happen with max_features)
                feature_matrix = feature_matrix[:, :DESCRIPTION_FEATURE_SIZE]
                
        except ValueError as e:
            # Handle case where vocabulary is empty or too small
            logger.warning(f"TF-IDF vectorization failed: {e}. Using zero vectors.", exc_info=True)
            feature_matrix = np.zeros((len(transactions), DESCRIPTION_FEATURE_SIZE))
            vectorizer = None
        
        return feature_matrix, vectorizer
    
    def _is_first_weekday_of_month(self, dt: datetime) -> bool:
        """Check if date is the first occurrence of its weekday in the month."""
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
        """Check if date is the last occurrence of its weekday in the month."""
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
    
    def construct_feature_vector(
        self,
        temporal_features: List[float],
        amount_feature: float,
        description_features: List[float]
    ) -> List[float]:
        """
        Construct a complete 67-dimensional feature vector.
        
        Args:
            temporal_features: 17 temporal features
            amount_feature: 1 amount feature
            description_features: 49 description features
            
        Returns:
            List of 67 float values
        """
        if len(temporal_features) != TEMPORAL_FEATURE_SIZE:
            raise ValueError(f"Expected {TEMPORAL_FEATURE_SIZE} temporal features, got {len(temporal_features)}")
        if len(description_features) != DESCRIPTION_FEATURE_SIZE:
            raise ValueError(f"Expected {DESCRIPTION_FEATURE_SIZE} description features, got {len(description_features)}")
        
        return temporal_features + [amount_feature] + description_features

