"""
Recurring Charge Detection and Prediction Services.

This package provides ML-based recurring charge detection, feature extraction,
and prediction services.

Public API:
    - RecurringChargeDetectionService: ML-based pattern detection using DBSCAN
    - RecurringChargeFeatureService: Feature extraction (67-dim base, 91-dim account-aware)
    - RecurringChargePredictionService: Predicts next occurrence of recurring charges
    - DetectionConfig: Configuration for detection parameters
    - DEFAULT_CONFIG: Default configuration instance
"""

from services.recurring_charges.detection_service import RecurringChargeDetectionService
from services.recurring_charges.feature_service import (
    RecurringChargeFeatureService,
    FEATURE_VECTOR_SIZE,
    ENHANCED_FEATURE_VECTOR_SIZE,
    TEMPORAL_FEATURE_SIZE,
    AMOUNT_FEATURE_SIZE,
    DESCRIPTION_FEATURE_SIZE,
    ACCOUNT_FEATURE_SIZE
)
from services.recurring_charges.prediction_service import RecurringChargePredictionService
from services.recurring_charges.config import (
    DetectionConfig,
    DEFAULT_CONFIG,
    ClusteringConfig,
    ConfidenceWeights,
    FrequencyThresholds,
    TemporalPatternConfig,
)
from services.recurring_charges.analyzers import (
    FrequencyAnalyzer,
    TemporalPatternAnalyzer,
    MerchantPatternAnalyzer,
    ConfidenceScoreCalculator,
)

__all__ = [
    'RecurringChargeDetectionService',
    'RecurringChargeFeatureService',
    'RecurringChargePredictionService',
    'DetectionConfig',
    'DEFAULT_CONFIG',
    'ClusteringConfig',
    'ConfidenceWeights',
    'FrequencyThresholds',
    'TemporalPatternConfig',
    'FEATURE_VECTOR_SIZE',
    'ENHANCED_FEATURE_VECTOR_SIZE',
    'TEMPORAL_FEATURE_SIZE',
    'AMOUNT_FEATURE_SIZE',
    'DESCRIPTION_FEATURE_SIZE',
    'ACCOUNT_FEATURE_SIZE',
    'FrequencyAnalyzer',
    'TemporalPatternAnalyzer',
    'MerchantPatternAnalyzer',
    'ConfidenceScoreCalculator',
]

