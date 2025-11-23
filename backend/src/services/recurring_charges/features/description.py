"""
Description feature extractor.

Extracts 49 TF-IDF features from transaction descriptions to capture merchant patterns.
"""

import logging
from typing import List, Tuple, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import csr_matrix

from models.transaction import Transaction
from services.recurring_charges.features.base import BaseFeatureExtractor

logger = logging.getLogger(__name__)


class DescriptionFeatureExtractor(BaseFeatureExtractor):
    """
    Extracts 49 TF-IDF features from transaction descriptions.
    
    Converts merchant names into a semantic vector space where similar
    merchants (e.g., "NETFLIX.COM" and "NETFLIX STREAMING") are close together.
    """
    
    FEATURE_SIZE = 49
    
    @property
    def feature_size(self) -> int:
        """Return the number of description features (49)."""
        return self.FEATURE_SIZE
    
    def extract_batch(
        self, 
        transactions: List[Transaction], 
        **kwargs
    ) -> Tuple[np.ndarray, Optional[TfidfVectorizer]]:
        """
        Extract TF-IDF features for a batch of transactions.
        
        NOTE: This extractor returns both features AND the fitted vectorizer,
        which is needed for potential future transformations.
        
        Args:
            transactions: List of Transaction objects
            **kwargs: Additional arguments (unused for description features)
            
        Returns:
            Tuple of:
                - Array of shape (n_transactions, 49) with TF-IDF features
                - Fitted TfidfVectorizer (or None if vectorization failed)
        """
        # Extract descriptions (lowercase for normalization)
        descriptions = [tx.description.lower() for tx in transactions if tx.description]
        
        # Initialize TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=self.FEATURE_SIZE,
            ngram_range=(1, 2),  # Unigrams and bigrams
            min_df=1,  # Minimum document frequency
            max_df=0.95,  # Maximum document frequency (ignore very common words)
            strip_accents='unicode',
            lowercase=True,
            token_pattern=r'\b[a-z]{2,}\b'  # Words with 2+ letters
        )
        
        try:
            # Fit and transform descriptions
            tfidf_matrix: csr_matrix = vectorizer.fit_transform(descriptions)  # type: ignore
            feature_matrix = tfidf_matrix.toarray()
            
            # Ensure we have exactly FEATURE_SIZE features
            if feature_matrix.shape[1] < self.FEATURE_SIZE:
                # Pad with zeros if we have fewer features
                padding = np.zeros((
                    feature_matrix.shape[0], 
                    self.FEATURE_SIZE - feature_matrix.shape[1]
                ))
                feature_matrix = np.hstack([feature_matrix, padding])
            elif feature_matrix.shape[1] > self.FEATURE_SIZE:
                # Truncate if we have more features (shouldn't happen with max_features)
                feature_matrix = feature_matrix[:, :self.FEATURE_SIZE]
            
            self.validate_output(feature_matrix, len(transactions))
            return feature_matrix, vectorizer
            
        except ValueError as e:
            # Handle case where vocabulary is empty or too small
            logger.warning(
                f"TF-IDF vectorization failed: {e}. Using zero vectors.", 
                exc_info=True
            )
            feature_matrix = np.zeros((len(transactions), self.FEATURE_SIZE))
            self.validate_output(feature_matrix, len(transactions))
            return feature_matrix, None

