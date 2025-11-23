"""
Base feature extractor class.

Defines the interface that all feature extractors must implement.
"""

from abc import ABC, abstractmethod
from typing import List
import numpy as np

from models.transaction import Transaction


class BaseFeatureExtractor(ABC):
    """
    Abstract base class for feature extractors.
    
    All feature extractors should inherit from this class and implement
    the abstract methods and properties.
    """
    
    @property
    @abstractmethod
    def feature_size(self) -> int:
        """
        Return the number of features this extractor produces.
        
        Returns:
            Integer representing the dimensionality of the feature vector
        """
        pass
    
    @abstractmethod
    def extract_batch(self, transactions: List[Transaction], **kwargs) -> np.ndarray:
        """
        Extract features for a batch of transactions.
        
        Args:
            transactions: List of Transaction objects to extract features from
            **kwargs: Additional arguments specific to the extractor
            
        Returns:
            Numpy array of shape (n_transactions, feature_size)
        """
        pass
    
    def validate_output(self, features: np.ndarray, n_transactions: int) -> None:
        """
        Validate that the extracted features have the correct shape.
        
        Args:
            features: Extracted feature matrix
            n_transactions: Expected number of transactions
            
        Raises:
            ValueError: If features have incorrect shape
        """
        expected_shape = (n_transactions, self.feature_size)
        if features.shape != expected_shape:
            raise ValueError(
                f"{self.__class__.__name__} produced incorrect shape: "
                f"expected {expected_shape}, got {features.shape}"
            )

