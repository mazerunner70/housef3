"""
Recurring Charge Feature Engineering Service.

This module orchestrates feature extraction from transactions for ML-based
recurring charge detection using specialized, composable feature extractors.

Base mode (67 dimensions):
- 17 temporal features (circular encoding + boolean flags)
- 1 amount feature (log-scaled and normalized)
- 49 description features (TF-IDF vectorization)

Account-aware mode (91 dimensions):
- 67 base features (above)
- 24 account features:
  - 6 account type features (one-hot encoded)
  - 8 account name features (keyword boolean flags)
  - 5 institution features (top 4 + other)
  - 5 account activity features (continuous metrics)
"""

import logging
import uuid
from typing import List, Dict, Tuple, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from models.transaction import Transaction
from models.account import Account
from services.recurring_charges.features import (
    TemporalFeatureExtractor,
    AmountFeatureExtractor,
    DescriptionFeatureExtractor,
    AccountFeatureExtractor
)

logger = logging.getLogger(__name__)

# Feature size constants
TEMPORAL_FEATURE_SIZE = 17
AMOUNT_FEATURE_SIZE = 1
DESCRIPTION_FEATURE_SIZE = 49
ACCOUNT_FEATURE_SIZE = 24

# Total feature sizes
FEATURE_VECTOR_SIZE = 67  # Base: 17 + 1 + 49
ENHANCED_FEATURE_VECTOR_SIZE = 91  # Enhanced: 67 + 24


class RecurringChargeFeatureService:
    """
    Orchestrates feature extraction from multiple specialized extractors.
    
    This service composes features from:
    - TemporalFeatureExtractor: When charges occur (17 dims)
    - AmountFeatureExtractor: How much charges cost (1 dim)
    - DescriptionFeatureExtractor: Merchant patterns (49 dims)
    - AccountFeatureExtractor: Account context (24 dims, optional)
    
    Mode selection:
    - Base mode (67-dim): When accounts_map is None
    - Account-aware mode (91-dim): When accounts_map is provided
    """
    
    def __init__(self, country_code: str = 'US'):
        """
        Initialize the feature service with specialized extractors.
        
        Args:
            country_code: Country code for holiday detection (default: US)
        """
        self.country_code = country_code
        
        # Initialize specialized feature extractors
        self.temporal_extractor = TemporalFeatureExtractor(country_code)
        self.amount_extractor = AmountFeatureExtractor()
        self.description_extractor = DescriptionFeatureExtractor()
        self.account_extractor = AccountFeatureExtractor()
        
        logger.info(f"Initialized RecurringChargeFeatureService for {country_code}")
    
    def extract_features_batch(
        self,
        transactions: List[Transaction],
        accounts_map: Optional[Dict[uuid.UUID, Account]] = None
    ) -> Tuple[np.ndarray, Optional[TfidfVectorizer]]:
        """
        Extract features from a batch of transactions.
        
        Orchestrates multiple specialized extractors to create complete
        feature vectors for ML-based pattern detection.
        
        Args:
            transactions: List of Transaction objects
            accounts_map: Optional dictionary mapping account_id to Account objects.
                         If None, extracts base features only (67-dim).
                         If provided, extracts account-aware features (91-dim).
            
        Returns:
            Tuple of (feature_matrix, fitted_vectorizer)
            - feature_matrix: numpy array of shape (n_transactions, 67 or 91)
            - fitted_vectorizer: Fitted TF-IDF vectorizer (None if failed)
        """
        if not transactions:
            # Check if accounts_map is not None AND not empty
            feature_size = ENHANCED_FEATURE_VECTOR_SIZE if (accounts_map is not None) else FEATURE_VECTOR_SIZE
            return np.array([]).reshape(0, feature_size), None
        
        # Log extraction mode
        mode = "account-aware (91-dim)" if accounts_map else "base (67-dim)"
        logger.info(f"Extracting {mode} features from {len(transactions)} transactions")
        
        # Extract base features using specialized extractors
        temporal_features = self.temporal_extractor.extract_batch(transactions)
        amount_features = self.amount_extractor.extract_batch(transactions)
        
        # Description extractor returns both features and vectorizer
        description_features, vectorizer = self.description_extractor.extract_batch(transactions)
        
        # Compose base features: 17 + 1 + 49 = 67 dimensions
        base_features = np.hstack([
            temporal_features,      # 17
            amount_features,        # 1
            description_features    # 49
        ])
        
        # Validate base feature dimensions
        expected_base_shape = (len(transactions), FEATURE_VECTOR_SIZE)
        if base_features.shape != expected_base_shape:
            raise ValueError(
                f"Base feature composition error: expected {expected_base_shape}, "
                f"got {base_features.shape}"
            )
        
        # Return base features if no account map provided
        if not accounts_map:
            logger.info(f"Base feature extraction complete: shape={base_features.shape}")
            return base_features, vectorizer
        
        # Extract account-aware features: 24 dimensions
        account_features = self.account_extractor.extract_batch(
            transactions, 
            accounts_map
        )
        
        # Compose enhanced features: 67 + 24 = 91 dimensions
        enhanced_features = np.hstack([
            base_features,      # 67
            account_features    # 24
        ])
        
        # Validate enhanced feature dimensions
        expected_enhanced_shape = (len(transactions), ENHANCED_FEATURE_VECTOR_SIZE)
        if enhanced_features.shape != expected_enhanced_shape:
            raise ValueError(
                f"Enhanced feature composition error: expected {expected_enhanced_shape}, "
                f"got {enhanced_features.shape}"
            )
        
        logger.info(f"Account-aware feature extraction complete: shape={enhanced_features.shape}")
        return enhanced_features, vectorizer
