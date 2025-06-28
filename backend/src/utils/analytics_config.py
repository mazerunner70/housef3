"""
Analytics configuration settings.

This module contains all configurable thresholds and settings for the analytics system.
These values can be adjusted without code changes for system tuning.
"""
import os
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AnalyticsConfig:
    """Configuration class for analytics system thresholds and settings."""
    
    # Data Quality Assessment Thresholds
    data_recency_threshold_days: int = 60  # Days after which data is considered outdated
    transaction_density_threshold: float = 0.1  # Minimum transactions per day for good quality
    
    # Sparse Data Detection
    sparse_data_date_span_days: int = 90  # Minimum date span to check for sparse data
    sparse_data_min_transactions: int = 10  # Minimum transactions for date span
    
    # Precomputation Settings
    precomputation_recent_upload_days: int = 7  # Days to consider uploads "recent"
    precomputation_account_threshold: float = 0.7  # Percentage of accounts needed for precomputation
    
    # Computation Scheduling
    default_computation_interval_days: int = 7  # Default recomputation interval
    health_metrics_interval_days: int = 14  # Interval for financial health metrics
    
    # Data Gap Thresholds
    outdated_data_threshold_days: int = 30  # Days after which data is considered outdated for gaps

    @classmethod
    def from_environment(cls) -> 'AnalyticsConfig':
        """
        Create configuration from environment variables with fallback to defaults.
        
        Environment variables:
        - ANALYTICS_DATA_RECENCY_DAYS
        - ANALYTICS_TRANSACTION_DENSITY
        - ANALYTICS_SPARSE_DATA_SPAN_DAYS
        - ANALYTICS_SPARSE_DATA_MIN_TRANSACTIONS
        - ANALYTICS_PRECOMPUTE_UPLOAD_DAYS
        - ANALYTICS_PRECOMPUTE_ACCOUNT_THRESHOLD
        - ANALYTICS_DEFAULT_INTERVAL_DAYS
        - ANALYTICS_HEALTH_INTERVAL_DAYS
        - ANALYTICS_OUTDATED_DATA_DAYS
        """
        return cls(
            data_recency_threshold_days=int(os.getenv('ANALYTICS_DATA_RECENCY_DAYS', 60)),
            transaction_density_threshold=float(os.getenv('ANALYTICS_TRANSACTION_DENSITY', 0.1)),
            sparse_data_date_span_days=int(os.getenv('ANALYTICS_SPARSE_DATA_SPAN_DAYS', 90)),
            sparse_data_min_transactions=int(os.getenv('ANALYTICS_SPARSE_DATA_MIN_TRANSACTIONS', 10)),
            precomputation_recent_upload_days=int(os.getenv('ANALYTICS_PRECOMPUTE_UPLOAD_DAYS', 7)),
            precomputation_account_threshold=float(os.getenv('ANALYTICS_PRECOMPUTE_ACCOUNT_THRESHOLD', 0.7)),
            default_computation_interval_days=int(os.getenv('ANALYTICS_DEFAULT_INTERVAL_DAYS', 7)),
            health_metrics_interval_days=int(os.getenv('ANALYTICS_HEALTH_INTERVAL_DAYS', 14)),
            outdated_data_threshold_days=int(os.getenv('ANALYTICS_OUTDATED_DATA_DAYS', 30))
        )

    def get_computation_interval(self, analytic_type_name: str) -> int:
        """
        Get computation interval for specific analytic types.
        
        Args:
            analytic_type_name: Name of the analytic type
            
        Returns:
            Interval in days
        """
        # Financial health and credit utilization metrics update less frequently
        health_analytics = ['FINANCIAL_HEALTH', 'CREDIT_UTILIZATION']
        
        if analytic_type_name in health_analytics:
            return self.health_metrics_interval_days
        else:
            return self.default_computation_interval_days


# Global configuration instance
analytics_config = AnalyticsConfig.from_environment()


def get_analytics_config() -> AnalyticsConfig:
    """Get the global analytics configuration instance."""
    return analytics_config


def update_config_from_dict(config_dict: Dict[str, Any]) -> None:
    """
    Update configuration from a dictionary (useful for testing).
    
    Args:
        config_dict: Dictionary with configuration values
    """
    global analytics_config
    
    # Create a new config instance with updated values
    current_values = {
        field.name: getattr(analytics_config, field.name)
        for field in analytics_config.__dataclass_fields__.values()
    }
    current_values.update(config_dict)
    
    analytics_config = AnalyticsConfig(**current_values) 