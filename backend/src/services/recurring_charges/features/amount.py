"""
Amount feature extractor.

Extracts 1 amount feature using log-scale transformation and normalization.
"""

from typing import List

import numpy as np

from models.transaction import Transaction
from services.recurring_charges.features.base import BaseFeatureExtractor


class AmountFeatureExtractor(BaseFeatureExtractor):
    """
    Extracts 1 amount feature from transactions.
    
    Uses log-scale transformation and normalization to handle the wide range
    of transaction amounts typically seen in financial data.
    """
    
    FEATURE_SIZE = 1
    
    @property
    def feature_size(self) -> int:
        """Return the number of amount features (1)."""
        return self.FEATURE_SIZE
    
    def extract_batch(self, transactions: List[Transaction], **kwargs) -> np.ndarray:
        """
        Extract amount features for a batch of transactions.
        
        Uses log-scale transformation (log1p to handle zeros) and normalization
        to [0, 1] range based on the min/max of the batch.
        
        Args:
            transactions: List of Transaction objects
            **kwargs: Additional arguments (unused for amount features)
            
        Returns:
            Array of shape (n_transactions, 1) with normalized log amounts
        """
        # Extract amounts as floats (use absolute value)
        amounts = np.array([float(abs(tx.amount)) for tx in transactions])
        
        # Log-scale transformation (add 1 to avoid log(0))
        log_amounts = np.log1p(amounts)
        
        # Normalize to [0, 1] range based on batch statistics
        if len(log_amounts) > 1:
            min_val = log_amounts.min()
            max_val = log_amounts.max()
            if max_val > min_val:
                normalized = (log_amounts - min_val) / (max_val - min_val)
            else:
                # All amounts are the same
                normalized = np.ones_like(log_amounts) * 0.5
        else:
            # Single transaction
            normalized = np.array([0.5])
        
        features = normalized.reshape(-1, 1)
        self.validate_output(features, len(transactions))
        return features

