"""
CloudWatch metrics and monitoring for FZIP import/export operations.
"""
import boto3
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class FZIPMetrics:
    """CloudWatch metrics recorder for FZIP operations."""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = 'HouseF3/FZIP'
    
    def record_export_duration(self, duration_seconds: float, success: bool, 
                              export_type: str = "complete", user_id: Optional[str] = None):
        """Record FZIP export processing duration."""
        try:
            dimensions = [
                {'Name': 'Success', 'Value': str(success)},
                {'Name': 'ExportType', 'Value': export_type}
            ]
            
            if user_id:
                # Hash user_id for privacy
                import hashlib
                user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:8]
                dimensions.append({'Name': 'UserHash', 'Value': user_hash})
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'ExportDuration',
                        'Dimensions': dimensions,
                        'Value': duration_seconds,
                        'Unit': 'Seconds',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            
            logger.info(f"Recorded export duration metric: {duration_seconds}s, success={success}")
            
        except Exception as e:
            logger.error(f"Failed to record export duration metric: {str(e)}")
    
    def record_export_package_size(self, size_bytes: int, export_type: str = "complete"):
        """Record FZIP export package size."""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'ExportPackageSize',
                        'Dimensions': [
                            {'Name': 'ExportType', 'Value': export_type}
                        ],
                        'Value': size_bytes,
                        'Unit': 'Bytes',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            
            logger.info(f"Recorded export package size metric: {size_bytes} bytes")
            
        except Exception as e:
            logger.error(f"Failed to record export package size metric: {str(e)}")
    
    def record_export_data_volume(self, entity_counts: Dict[str, int], export_type: str = "complete"):
        """Record the volume of data exported by entity type."""
        try:
            metric_data = []
            
            for entity_type, count in entity_counts.items():
                metric_data.append({
                    'MetricName': 'ExportDataVolume',
                    'Dimensions': [
                        {'Name': 'EntityType', 'Value': entity_type},
                        {'Name': 'ExportType', 'Value': export_type}
                    ],
                    'Value': count,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                })
            
            # Send metrics in batches of 20 (CloudWatch limit)
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            logger.info(f"Recorded export data volume metrics: {entity_counts}")
            
        except Exception as e:
            logger.error(f"Failed to record export data volume metrics: {str(e)}")
    
    def record_export_success_rate(self, success_count: int, total_count: int):
        """Record FZIP export success rate."""
        try:
            if total_count > 0:
                success_rate = (success_count / total_count) * 100
                
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=[
                        {
                            'MetricName': 'ExportSuccessRate',
                            'Value': success_rate,
                            'Unit': 'Percent',
                            'Timestamp': datetime.utcnow()
                        },
                        {
                            'MetricName': 'ExportCount',
                            'Dimensions': [
                                {'Name': 'Result', 'Value': 'Success'}
                            ],
                            'Value': success_count,
                            'Unit': 'Count',
                            'Timestamp': datetime.utcnow()
                        },
                        {
                            'MetricName': 'ExportCount',
                            'Dimensions': [
                                {'Name': 'Result', 'Value': 'Total'}
                            ],
                            'Value': total_count,
                            'Unit': 'Count',
                            'Timestamp': datetime.utcnow()
                        }
                    ]
                )
                
                logger.info(f"Recorded export success rate: {success_rate}% ({success_count}/{total_count})")
                
        except Exception as e:
            logger.error(f"Failed to record export success rate metric: {str(e)}")
    
    def record_export_error(self, error_type: str, error_message: str, 
                           export_type: str = "complete", phase: str = "unknown"):
        """Record FZIP export error details."""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'ExportErrors',
                        'Dimensions': [
                            {'Name': 'ErrorType', 'Value': error_type},
                            {'Name': 'ExportType', 'Value': export_type},
                            {'Name': 'Phase', 'Value': phase}
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            
            logger.error(f"Recorded export error metric: {error_type} in {phase} phase - {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to record export error metric: {str(e)}")
    
    def record_import_duration(self, duration_seconds: float, success: bool, 
                              import_type: str = "complete", user_id: Optional[str] = None):
        """Record FZIP import processing duration."""
        try:
            dimensions = [
                {'Name': 'Success', 'Value': str(success)},
                {'Name': 'ImportType', 'Value': import_type}
            ]
            
            if user_id:
                # Hash user_id for privacy
                import hashlib
                user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:8]
                dimensions.append({'Name': 'UserHash', 'Value': user_hash})
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'ImportDuration',
                        'Dimensions': dimensions,
                        'Value': duration_seconds,
                        'Unit': 'Seconds',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            
            logger.info(f"Recorded import duration metric: {duration_seconds}s, success={success}")
            
        except Exception as e:
            logger.error(f"Failed to record import duration metric: {str(e)}")
    
    def record_import_validation_results(self, validation_results: Dict[str, Any]):
        """Record FZIP import validation results."""
        try:
            metric_data = []
            
            # Record overall validation status
            overall_valid = validation_results.get('overall_valid', False)
            metric_data.append({
                'MetricName': 'ImportValidation',
                'Dimensions': [
                    {'Name': 'Result', 'Value': 'Valid' if overall_valid else 'Invalid'}
                ],
                'Value': 1,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            })
            
            # Record validation details by type
            for validation_type, result in validation_results.items():
                if isinstance(result, dict) and 'valid' in result:
                    metric_data.append({
                        'MetricName': 'ImportValidationDetails',
                        'Dimensions': [
                            {'Name': 'ValidationType', 'Value': validation_type},
                            {'Name': 'Result', 'Value': 'Valid' if result['valid'] else 'Invalid'}
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    })
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )
            
            logger.info(f"Recorded import validation metrics: overall_valid={overall_valid}")
            
        except Exception as e:
            logger.error(f"Failed to record import validation metrics: {str(e)}")
    
    @contextmanager
    def measure_export_duration(self, export_type: str = "complete", user_id: Optional[str] = None):
        """Context manager to measure and record export duration."""
        start_time = time.time()
        success = False
        
        try:
            yield
            success = True
        finally:
            duration = time.time() - start_time
            self.record_export_duration(duration, success, export_type, user_id)
    
    @contextmanager
    def measure_import_duration(self, import_type: str = "complete", user_id: Optional[str] = None):
        """Context manager to measure and record import duration."""
        start_time = time.time()
        success = False
        
        try:
            yield
            success = True
        finally:
            duration = time.time() - start_time
            self.record_import_duration(duration, success, import_type, user_id)


# Global metrics instance
fzip_metrics = FZIPMetrics()


def record_export_metrics(func):
    """Decorator to automatically record metrics for export functions."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        success = False
        
        try:
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            fzip_metrics.record_export_error(
                error_type=type(e).__name__,
                error_message=str(e),
                phase=func.__name__
            )
            raise
        finally:
            duration = time.time() - start_time
            fzip_metrics.record_export_duration(duration, success)
    
    return wrapper


def record_import_metrics(func):
    """Decorator to automatically record metrics for import functions."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        success = False
        
        try:
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            fzip_metrics.record_export_error(
                error_type=type(e).__name__,
                error_message=str(e),
                phase=func.__name__
            )
            raise
        finally:
            duration = time.time() - start_time
            fzip_metrics.record_import_duration(duration, success)
    
    return wrapper