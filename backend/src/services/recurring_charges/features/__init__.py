"""
Feature extractors for recurring charge detection.

This package provides specialized feature extractors that compose to create
complete feature vectors for ML-based pattern detection.
"""

from services.recurring_charges.features.base import BaseFeatureExtractor
from services.recurring_charges.features.temporal import TemporalFeatureExtractor
from services.recurring_charges.features.amount import AmountFeatureExtractor
from services.recurring_charges.features.description import DescriptionFeatureExtractor
from services.recurring_charges.features.account import AccountFeatureExtractor

__all__ = [
    'BaseFeatureExtractor',
    'TemporalFeatureExtractor',
    'AmountFeatureExtractor',
    'DescriptionFeatureExtractor',
    'AccountFeatureExtractor',
]
