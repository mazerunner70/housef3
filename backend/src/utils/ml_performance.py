"""
Performance monitoring utilities for ML operations.

This module provides decorators and utilities for monitoring the performance
of ML-based recurring charge detection operations, including:
- Transaction fetch time
- Feature extraction time
- Clustering time
- Pattern analysis time
- Total execution time
- Memory usage tracking
"""

import time
import logging
import functools
from typing import Callable, TypeVar, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Optional dependency for memory tracking
try:
    import psutil  # type: ignore[import-not-found]
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class MLPerformanceMetrics:
    """Container for ML operation performance metrics."""
    operation_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    elapsed_ms: Optional[float] = None
    transaction_count: int = 0
    feature_extraction_ms: Optional[float] = None
    clustering_ms: Optional[float] = None
    pattern_analysis_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    patterns_detected: int = 0
    clusters_identified: int = 0
    
    def finish(self):
        """Mark the operation as finished and calculate elapsed time."""
        self.end_time = time.time()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for logging."""
        return {
            'operation_name': self.operation_name,
            'elapsed_ms': self.elapsed_ms,
            'transaction_count': self.transaction_count,
            'feature_extraction_ms': self.feature_extraction_ms,
            'clustering_ms': self.clustering_ms,
            'pattern_analysis_ms': self.pattern_analysis_ms,
            'memory_usage_mb': self.memory_usage_mb,
            'patterns_detected': self.patterns_detected,
            'clusters_identified': self.clusters_identified,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def log_metrics(self):
        """Log the performance metrics."""
        metrics = self.to_dict()
        
        # Determine log level based on performance
        if self.elapsed_ms and self.elapsed_ms > 30000:  # > 30 seconds
            logger.error(
                f"SLOW ML OPERATION: {self.operation_name} took {self.elapsed_ms:.2f}ms",
                extra={'ml_metrics': metrics}
            )
        elif self.elapsed_ms and self.elapsed_ms > 10000:  # > 10 seconds
            logger.warning(
                f"Slow ML operation: {self.operation_name} took {self.elapsed_ms:.2f}ms",
                extra={'ml_metrics': metrics}
            )
        else:
            logger.info(
                f"ML operation completed: {self.operation_name} in {self.elapsed_ms:.2f}ms",
                extra={'ml_metrics': metrics}
            )
        
        # Log breakdown if available
        if self.feature_extraction_ms or self.clustering_ms or self.pattern_analysis_ms:
            breakdown = []
            if self.feature_extraction_ms:
                breakdown.append(f"feature_extraction: {self.feature_extraction_ms:.2f}ms")
            if self.clustering_ms:
                breakdown.append(f"clustering: {self.clustering_ms:.2f}ms")
            if self.pattern_analysis_ms:
                breakdown.append(f"pattern_analysis: {self.pattern_analysis_ms:.2f}ms")
            
            logger.debug(
                f"ML operation breakdown for {self.operation_name}: {', '.join(breakdown)}",
                extra={'ml_metrics': metrics}
            )


def monitor_ml_operation(operation_name: Optional[str] = None):
    """
    Decorator for monitoring ML operation performance.
    
    Tracks:
    - Total execution time
    - Transaction count (if provided in result)
    - Automatic logging with appropriate log levels
    
    Usage:
        @monitor_ml_operation("detect_recurring_charges")
        def detect_patterns(transactions: List[Transaction]) -> Dict:
            ...
            return {
                'patterns': patterns,
                'transaction_count': len(transactions),
                'patterns_detected': len(patterns)
            }
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            op_name = operation_name or func.__name__
            metrics = MLPerformanceMetrics(operation_name=op_name)
            
            try:
                logger.debug(f"Starting ML operation: {op_name}")
                result = func(*args, **kwargs)
                
                # Extract metrics from result if it's a dict
                if isinstance(result, dict):
                    metrics.transaction_count = result.get('transaction_count', 0)
                    metrics.patterns_detected = result.get('patterns_detected', 0)
                    metrics.clusters_identified = result.get('clusters_identified', 0)
                    
                    # Extract timing breakdown if provided
                    if 'performance_metrics' in result:
                        perf = result['performance_metrics']
                        metrics.feature_extraction_ms = perf.get('feature_extraction_ms')
                        metrics.clustering_ms = perf.get('clustering_ms')
                        metrics.pattern_analysis_ms = perf.get('pattern_analysis_ms')
                
                return result
            finally:
                metrics.finish()
                metrics.log_metrics()
        
        return wrapper
    return decorator


def track_stage_time(metrics: MLPerformanceMetrics, stage_name: str):
    """
    Context manager for tracking individual stage timing within an ML operation.
    
    Usage:
        metrics = MLPerformanceMetrics(operation_name="detect_patterns")
        
        with track_stage_time(metrics, 'feature_extraction'):
            features = extract_features(transactions)
        
        with track_stage_time(metrics, 'clustering'):
            clusters = perform_clustering(features)
    """
    class StageTimer:
        def __init__(self, metrics: MLPerformanceMetrics, stage: str):
            self.metrics = metrics
            self.stage = stage
            self.start_time: float = 0.0
        
        def __enter__(self):
            self.start_time = time.time()
            logger.debug(f"Starting stage: {self.stage}")
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed_ms = (time.time() - self.start_time) * 1000
            
            # Store timing in appropriate metric field
            if self.stage == 'feature_extraction':
                self.metrics.feature_extraction_ms = elapsed_ms
            elif self.stage == 'clustering':
                self.metrics.clustering_ms = elapsed_ms
            elif self.stage == 'pattern_analysis':
                self.metrics.pattern_analysis_ms = elapsed_ms
            
            logger.debug(f"Completed stage {self.stage} in {elapsed_ms:.2f}ms")
    
    return StageTimer(metrics, stage_name)


def get_memory_usage_mb() -> float:
    """
    Get current memory usage in MB.
    
    Returns:
        Memory usage in MB, or 0.0 if unable to determine
    """
    if not PSUTIL_AVAILABLE:
        return 0.0
    
    try:
        import os
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return memory_info.rss / (1024 * 1024)  # Convert bytes to MB
    except Exception as e:
        logger.exception(f"Unable to get memory usage: {e}")
        return 0.0


def log_ml_statistics(
    operation_name: str,
    transaction_count: int,
    patterns_detected: int,
    clusters_identified: int,
    high_confidence_patterns: int,
    elapsed_ms: float
):
    """
    Log ML operation statistics in a structured format.
    
    Args:
        operation_name: Name of the ML operation
        transaction_count: Number of transactions analyzed
        patterns_detected: Number of patterns detected
        clusters_identified: Number of clusters identified
        high_confidence_patterns: Number of high-confidence patterns
        elapsed_ms: Total elapsed time in milliseconds
    """
    statistics = {
        'operation': operation_name,
        'transaction_count': transaction_count,
        'patterns_detected': patterns_detected,
        'clusters_identified': clusters_identified,
        'high_confidence_patterns': high_confidence_patterns,
        'elapsed_ms': elapsed_ms,
        'transactions_per_second': (transaction_count / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0,
        'avg_ms_per_transaction': (elapsed_ms / transaction_count) if transaction_count > 0 else 0,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    logger.info(
        f"ML Statistics - {operation_name}: "
        f"{transaction_count} transactions, {patterns_detected} patterns, "
        f"{elapsed_ms:.2f}ms total",
        extra={'ml_statistics': statistics}
    )


class MLPerformanceTracker:
    """
    Context manager for comprehensive ML performance tracking.
    
    Usage:
        with MLPerformanceTracker("detect_recurring_charges") as tracker:
            # Fetch transactions
            transactions = fetch_transactions(user_id)
            tracker.set_transaction_count(len(transactions))
            
            # Extract features
            with tracker.stage('feature_extraction'):
                features = extract_features(transactions)
            
            # Perform clustering
            with tracker.stage('clustering'):
                clusters = cluster_transactions(features)
            tracker.set_clusters_identified(len(set(clusters)))
            
            # Analyze patterns
            with tracker.stage('pattern_analysis'):
                patterns = analyze_patterns(clusters)
            tracker.set_patterns_detected(len(patterns))
    """
    
    def __init__(self, operation_name: str):
        self.metrics = MLPerformanceMetrics(operation_name=operation_name)
        self.memory_at_start = get_memory_usage_mb()
    
    def __enter__(self):
        logger.info(f"Starting ML operation: {self.metrics.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.metrics.finish()
        
        # Calculate memory usage
        memory_at_end = get_memory_usage_mb()
        if memory_at_end > 0 and self.memory_at_start > 0:
            self.metrics.memory_usage_mb = memory_at_end - self.memory_at_start
        
        # Log metrics
        self.metrics.log_metrics()
        
        # Log statistics if we have the data
        if self.metrics.transaction_count > 0:
            high_confidence = 0  # This would need to be set explicitly if needed
            log_ml_statistics(
                operation_name=self.metrics.operation_name,
                transaction_count=self.metrics.transaction_count,
                patterns_detected=self.metrics.patterns_detected,
                clusters_identified=self.metrics.clusters_identified,
                high_confidence_patterns=high_confidence,
                elapsed_ms=self.metrics.elapsed_ms or 0
            )
    
    def stage(self, stage_name: str):
        """Create a context manager for tracking a stage."""
        return track_stage_time(self.metrics, stage_name)
    
    def set_transaction_count(self, count: int):
        """Set the number of transactions being processed."""
        self.metrics.transaction_count = count
    
    def set_patterns_detected(self, count: int):
        """Set the number of patterns detected."""
        self.metrics.patterns_detected = count
    
    def set_clusters_identified(self, count: int):
        """Set the number of clusters identified."""
        self.metrics.clusters_identified = count

