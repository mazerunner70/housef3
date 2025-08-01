"""
CloudWatch metrics and monitoring for FZIP backup/restore operations.
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
    
    # ========================================================================
    # BACKUP METRICS
    # ========================================================================
    
    def record_backup_duration(self, duration_seconds: float, success: bool, 
                              backup_type: str = "complete", user_id: Optional[str] = None):
        """Record FZIP backup processing duration."""
        try:
            dimensions = [
                {'Name': 'Success', 'Value': str(success)},
                {'Name': 'BackupType', 'Value': backup_type}
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
                        'MetricName': 'BackupDuration',
                        'Dimensions': dimensions,
                        'Value': duration_seconds,
                        'Unit': 'Seconds',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            
            logger.info(f"Recorded backup duration metric: {duration_seconds}s, success={success}")
            
        except Exception as e:
            logger.error(f"Failed to record backup duration metric: {str(e)}")
    
    def record_backup_package_size(self, size_bytes: int, backup_type: str = "complete"):
        """Record FZIP backup package size."""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'BackupPackageSize',
                        'Dimensions': [
                            {'Name': 'BackupType', 'Value': backup_type}
                        ],
                        'Value': size_bytes,
                        'Unit': 'Bytes',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            
            logger.info(f"Recorded backup package size metric: {size_bytes} bytes")
            
        except Exception as e:
            logger.error(f"Failed to record backup package size metric: {str(e)}")
    
    def record_backup_data_volume(self, entity_counts: Dict[str, int], backup_type: str = "complete"):
        """Record the volume of data backed up by entity type."""
        try:
            metric_data = []
            
            for entity_type, count in entity_counts.items():
                metric_data.append({
                    'MetricName': 'BackupDataVolume',
                    'Dimensions': [
                        {'Name': 'EntityType', 'Value': entity_type},
                        {'Name': 'BackupType', 'Value': backup_type}
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
            
            logger.info(f"Recorded backup data volume metrics: {entity_counts}")
            
        except Exception as e:
            logger.error(f"Failed to record backup data volume metrics: {str(e)}")
    
    def record_backup_success_rate(self, success_count: int, total_count: int):
        """Record FZIP backup success rate."""
        try:
            if total_count > 0:
                success_rate = (success_count / total_count) * 100
                
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=[
                        {
                            'MetricName': 'BackupSuccessRate',
                            'Value': success_rate,
                            'Unit': 'Percent',
                            'Timestamp': datetime.utcnow()
                        },
                        {
                            'MetricName': 'BackupCount',
                            'Dimensions': [
                                {'Name': 'Result', 'Value': 'Success'}
                            ],
                            'Value': success_count,
                            'Unit': 'Count',
                            'Timestamp': datetime.utcnow()
                        },
                        {
                            'MetricName': 'BackupCount',
                            'Dimensions': [
                                {'Name': 'Result', 'Value': 'Total'}
                            ],
                            'Value': total_count,
                            'Unit': 'Count',
                            'Timestamp': datetime.utcnow()
                        }
                    ]
                )
                
                logger.info(f"Recorded backup success rate: {success_rate}% ({success_count}/{total_count})")
                
        except Exception as e:
            logger.error(f"Failed to record backup success rate metric: {str(e)}")
    
    def record_backup_error(self, error_type: str, error_message: str, 
                           backup_type: str = "complete", phase: str = "unknown"):
        """Record FZIP backup error details."""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'BackupErrors',
                        'Dimensions': [
                            {'Name': 'ErrorType', 'Value': error_type},
                            {'Name': 'BackupType', 'Value': backup_type},
                            {'Name': 'Phase', 'Value': phase}
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            
            logger.error(f"Recorded backup error metric: {error_type} in {phase} phase - {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to record backup error metric: {str(e)}")

    @contextmanager
    def measure_backup_duration(self, backup_type: str = "complete", user_id: Optional[str] = None):
        """Context manager to measure and record backup duration."""
        start_time = time.time()
        success = False
        
        try:
            yield
            success = True
        finally:
            duration = time.time() - start_time
            self.record_backup_duration(duration, success, backup_type, user_id)
    
    # ========================================================================
    # RESTORE METRICS
    # ========================================================================
    
    def record_restore_duration(self, duration_seconds: float, success: bool, 
                               restore_type: str = "complete", user_id: Optional[str] = None):
        """Record FZIP restore processing duration."""
        try:
            dimensions = [
                {'Name': 'Success', 'Value': str(success)},
                {'Name': 'RestoreType', 'Value': restore_type}
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
                        'MetricName': 'RestoreDuration',
                        'Dimensions': dimensions,
                        'Value': duration_seconds,
                        'Unit': 'Seconds',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            
            logger.info(f"Recorded restore duration metric: {duration_seconds}s, success={success}")
            
        except Exception as e:
            logger.error(f"Failed to record restore duration metric: {str(e)}")
    
    def record_restore_validation_results(self, validation_results: Dict[str, Any]):
        """Record FZIP restore validation results."""
        try:
            metric_data = []
            
            # Record overall validation status
            overall_valid = validation_results.get('overall_valid', False)
            metric_data.append({
                'MetricName': 'RestoreValidation',
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
                        'MetricName': 'RestoreValidationDetails',
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
            
            logger.info(f"Recorded restore validation metrics: overall_valid={overall_valid}")
            
        except Exception as e:
            logger.error(f"Failed to record restore validation metrics: {str(e)}")

    def record_restore_error(self, error_type: str, error_message: str, 
                            restore_type: str = "complete", phase: str = "unknown"):
        """Record FZIP restore error details."""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'RestoreErrors',
                        'Dimensions': [
                            {'Name': 'ErrorType', 'Value': error_type},
                            {'Name': 'RestoreType', 'Value': restore_type},
                            {'Name': 'Phase', 'Value': phase}
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            
            logger.error(f"Recorded restore error metric: {error_type} in {phase} phase - {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to record restore error metric: {str(e)}")

    @contextmanager
    def measure_restore_duration(self, restore_type: str = "complete", user_id: Optional[str] = None):
        """Context manager to measure and record restore duration."""
        start_time = time.time()
        success = False
        
        try:
            yield
            success = True
        finally:
            duration = time.time() - start_time
            self.record_restore_duration(duration, success, restore_type, user_id)


# Global metrics instance
fzip_metrics = FZIPMetrics()


# ========================================================================
# DECORATORS
# ========================================================================

def record_backup_metrics(func):
    """Decorator to automatically record metrics for backup functions."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        success = False
        
        try:
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            fzip_metrics.record_backup_error(
                error_type=type(e).__name__,
                error_message=str(e),
                phase=func.__name__
            )
            raise
        finally:
            duration = time.time() - start_time
            fzip_metrics.record_backup_duration(duration, success)
    
    return wrapper


def record_restore_metrics(func):
    """Decorator to automatically record metrics for restore functions."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        success = False
        
        try:
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            fzip_metrics.record_restore_error(
                error_type=type(e).__name__,
                error_message=str(e),
                phase=func.__name__
            )
            raise
        finally:
            duration = time.time() - start_time
            fzip_metrics.record_restore_duration(duration, success)
    
    return wrapper