"""
Configuration classes for recurring charge detection.

Centralizes all configuration parameters, thresholds, and weights used
in the detection pipeline.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional

from models.recurring_charge import RecurrenceFrequency


@dataclass
class ClusteringConfig:
    """Configuration for DBSCAN clustering algorithm."""
    
    default_eps: float = 0.5
    """Default epsilon (neighborhood radius) for DBSCAN."""
    
    min_samples_ratio: float = 0.01
    """Minimum samples as ratio of dataset size."""
    
    min_cluster_size: int = 3
    """Minimum number of transactions to form a valid cluster/pattern."""


@dataclass
class ConfidenceWeights:
    """
    Weights for multi-factor confidence score calculation.
    
    All weights must sum to 1.0 for proper normalization.
    """
    
    interval_regularity: float = 0.30
    """Weight for interval regularity score (how consistent are time gaps)."""
    
    amount_regularity: float = 0.20
    """Weight for amount regularity score (how consistent are amounts)."""
    
    sample_size: float = 0.20
    """Weight for sample size score (how many occurrences)."""
    
    temporal_consistency: float = 0.30
    """Weight for temporal consistency score (how consistent is timing pattern)."""
    
    def __post_init__(self):
        """Validate that weights sum to 1.0."""
        total = (
            self.interval_regularity +
            self.amount_regularity +
            self.sample_size +
            self.temporal_consistency
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"Confidence weights must sum to 1.0, got {total}. "
                f"Weights: interval={self.interval_regularity}, "
                f"amount={self.amount_regularity}, "
                f"sample_size={self.sample_size}, "
                f"temporal={self.temporal_consistency}"
            )


@dataclass
class FrequencyThresholds:
    """
    Day range thresholds for frequency classification.
    
    Each threshold is a tuple of (min_days, max_days) that defines
    the acceptable interval range for that frequency category.
    """
    
    daily: Tuple[float, float] = (0.5, 1.5)
    """Daily recurrence: 0.5 to 1.5 days between occurrences."""
    
    weekly: Tuple[float, float] = (6, 8)
    """Weekly recurrence: 6 to 8 days between occurrences."""
    
    bi_weekly: Tuple[float, float] = (12, 16)
    """Bi-weekly recurrence: 12 to 16 days between occurrences."""
    
    semi_monthly: Tuple[float, float] = (13, 17)
    """Semi-monthly recurrence: 13 to 17 days between occurrences."""
    
    monthly: Tuple[float, float] = (25, 35)
    """Monthly recurrence: 25 to 35 days between occurrences."""
    
    bi_monthly: Tuple[float, float] = (55, 65)
    """Bi-monthly recurrence: 55 to 65 days between occurrences."""
    
    quarterly: Tuple[float, float] = (85, 95)
    """Quarterly recurrence: 85 to 95 days between occurrences."""
    
    semi_annually: Tuple[float, float] = (175, 190)
    """Semi-annual recurrence: 175 to 190 days between occurrences."""
    
    annually: Tuple[float, float] = (355, 375)
    """Annual recurrence: 355 to 375 days between occurrences."""
    
    def to_dict(self) -> Dict[RecurrenceFrequency, Tuple[float, float]]:
        """
        Convert thresholds to a dictionary mapping frequency enum to ranges.
        
        Returns:
            Dictionary mapping RecurrenceFrequency to (min_days, max_days) tuple
        """
        return {
            RecurrenceFrequency.DAILY: self.daily,
            RecurrenceFrequency.WEEKLY: self.weekly,
            RecurrenceFrequency.BI_WEEKLY: self.bi_weekly,
            RecurrenceFrequency.SEMI_MONTHLY: self.semi_monthly,
            RecurrenceFrequency.MONTHLY: self.monthly,
            RecurrenceFrequency.BI_MONTHLY: self.bi_monthly,
            RecurrenceFrequency.QUARTERLY: self.quarterly,
            RecurrenceFrequency.SEMI_ANNUALLY: self.semi_annually,
            RecurrenceFrequency.ANNUALLY: self.annually,
        }


@dataclass
class TemporalPatternConfig:
    """Configuration for temporal pattern detection."""
    
    consistency_threshold: float = 0.70
    """
    Minimum percentage of transactions matching a pattern to consider it valid.
    
    For example, 0.70 means at least 70% of transactions must match
    the pattern (e.g., all on last working day) to be classified as such.
    """
    
    weekday_detection_threshold: float = 0.70
    """Threshold for first/last weekday of month detection."""
    
    day_threshold: float = 0.60
    """Threshold for specific day of month/week pattern detection."""


class DetectionConfig:
    """
    Master configuration for recurring charge detection.
    
    Aggregates all configuration classes into a single configuration object.
    """
    
    def __init__(
        self,
        clustering: Optional[ClusteringConfig] = None,
        confidence_weights: Optional[ConfidenceWeights] = None,
        frequency_thresholds: Optional[FrequencyThresholds] = None,
        temporal_pattern: Optional[TemporalPatternConfig] = None,
        min_confidence: float = 0.6,
        min_occurrences: int = 3
    ):
        """
        Initialize detection configuration.
        
        Args:
            clustering: DBSCAN clustering config (creates default if None)
            confidence_weights: Confidence weights config (creates default if None)
            frequency_thresholds: Frequency thresholds config (creates default if None)
            temporal_pattern: Temporal pattern config (creates default if None)
            min_confidence: Minimum confidence threshold
            min_occurrences: Minimum occurrences threshold
        """
        self.clustering = clustering or ClusteringConfig()
        self.confidence_weights = confidence_weights or ConfidenceWeights()
        self.frequency_thresholds = frequency_thresholds or FrequencyThresholds()
        self.temporal_pattern = temporal_pattern or TemporalPatternConfig()
        self.min_confidence = min_confidence
        self.min_occurrences = min_occurrences


# Default configuration instance
DEFAULT_CONFIG = DetectionConfig()


# Legacy constants for backward compatibility
# These map to the default configuration values
MIN_CLUSTER_SIZE = DEFAULT_CONFIG.min_occurrences
MIN_CONFIDENCE = DEFAULT_CONFIG.min_confidence
DEFAULT_EPS = DEFAULT_CONFIG.clustering.default_eps
MIN_SAMPLES_RATIO = DEFAULT_CONFIG.clustering.min_samples_ratio

FREQUENCY_THRESHOLDS = DEFAULT_CONFIG.frequency_thresholds.to_dict()

