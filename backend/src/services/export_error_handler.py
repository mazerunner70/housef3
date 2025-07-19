"""
Export Error Handler for the import/export system.
Provides comprehensive error handling, retry logic, circuit breaker patterns, and detailed error reporting.
"""
import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Type, Union
from functools import wraps
import uuid

from models.export import ExportJob, ExportStatus

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_PROCESSING = "data_processing"
    S3_OPERATION = "s3_operation"
    NETWORK = "network"
    TIMEOUT = "timeout"
    MEMORY = "memory"
    DISK_SPACE = "disk_space"
    VALIDATION = "validation"
    SERIALIZATION = "serialization"
    COMPRESSION = "compression"
    UNKNOWN = "unknown"


class RetryStrategy(str, Enum):
    """Retry strategy types"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"
    NO_RETRY = "no_retry"


@dataclass
class ErrorDetails:
    """Detailed error information"""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    message: str = ""
    exception_type: str = ""
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    recoverable: bool = True
    user_facing_message: Optional[str] = None


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for fault tolerance"""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "closed"  # closed, open, half_open
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    success_threshold: int = 3  # successes needed to close circuit


class ExportErrorHandler:
    """Comprehensive error handler for export operations"""
    
    def __init__(self):
        self.error_history: List[ErrorDetails] = []
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.error_patterns: Dict[str, ErrorCategory] = self._build_error_patterns()
        self.retry_delays = {
            RetryStrategy.EXPONENTIAL_BACKOFF: lambda attempt: min(60, 2 ** attempt),
            RetryStrategy.LINEAR_BACKOFF: lambda attempt: min(60, attempt * 2),
            RetryStrategy.FIXED_DELAY: lambda attempt: 5,
            RetryStrategy.IMMEDIATE: lambda attempt: 0
        }
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorDetails:
        """
        Handle and classify an error
        
        Args:
            error: The exception that occurred
            context: Additional context information
            
        Returns:
            ErrorDetails object with classification and handling information
        """
        error_details = self._classify_error(error, context or {})
        
        # Log the error
        self._log_error(error_details)
        
        # Add to error history
        self.error_history.append(error_details)
        
        # Update circuit breaker if applicable
        if error_details.category in [ErrorCategory.S3_OPERATION, ErrorCategory.DATA_ACCESS]:
            self._update_circuit_breaker(error_details.category.value, False)
        
        # Determine if operation should be retried
        error_details.recoverable = self._is_error_recoverable(error_details)
        
        return error_details
    
    def should_retry(self, error_details: ErrorDetails, current_attempt: int) -> bool:
        """
        Determine if an operation should be retried
        
        Args:
            error_details: Error details from the failed operation
            current_attempt: Current attempt number (0-based)
            
        Returns:
            True if the operation should be retried
        """
        # Check circuit breaker
        if not self._check_circuit_breaker(error_details.category.value):
            return False
        
        # Check retry limits
        if current_attempt >= error_details.max_retries:
            return False
        
        # Check if error is recoverable
        if not error_details.recoverable:
            return False
        
        # Check retry strategy
        if error_details.retry_strategy == RetryStrategy.NO_RETRY:
            return False
        
        return True
    
    def get_retry_delay(self, error_details: ErrorDetails, attempt: int) -> float:
        """
        Get the delay before the next retry attempt
        
        Args:
            error_details: Error details
            attempt: Attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        delay_func = self.retry_delays.get(error_details.retry_strategy, 
                                         self.retry_delays[RetryStrategy.EXPONENTIAL_BACKOFF])
        return delay_func(attempt)
    
    def record_success(self, operation_category: str):
        """Record a successful operation for circuit breaker management"""
        self._update_circuit_breaker(operation_category, True)
    
    def with_error_handling(self, operation_name: str, 
                          max_retries: int = 3,
                          retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF):
        """
        Decorator for adding error handling and retry logic to functions
        
        Args:
            operation_name: Name of the operation for logging
            max_retries: Maximum number of retry attempts
            retry_strategy: Strategy for retry delays
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_error = Exception("Unknown export handler error")
                
                for attempt in range(max_retries + 1):
                    try:
                        result = func(*args, **kwargs)
                        
                        # Record success for circuit breaker
                        self.record_success(operation_name)
                        
                        if attempt > 0:
                            logger.info(f"{operation_name} succeeded after {attempt} retries")
                        
                        return result
                        
                    except Exception as e:
                        last_error = e
                        error_details = self.handle_error(e, {
                            'operation': operation_name,
                            'attempt': attempt,
                            'args': str(args)[:200],  # Truncate for logging
                            'kwargs': str(kwargs)[:200]
                        })
                        
                        error_details.max_retries = max_retries
                        error_details.retry_strategy = retry_strategy
                        
                        if self.should_retry(error_details, attempt):
                            delay = self.get_retry_delay(error_details, attempt)
                            logger.warning(f"{operation_name} failed (attempt {attempt + 1}/{max_retries + 1}), "
                                         f"retrying in {delay} seconds: {str(e)}")
                            
                            if delay > 0:
                                time.sleep(delay)
                            continue
                        else:
                            logger.error(f"{operation_name} failed permanently after {attempt + 1} attempts: {str(e)}")
                            break
                
                # All retries exhausted
                raise last_error
                
            return wrapper
        return decorator
    
    def create_export_error_summary(self, export_job: ExportJob) -> Dict[str, Any]:
        """
        Create a comprehensive error summary for an export job
        
        Args:
            export_job: The export job to create summary for
            
        Returns:
            Dictionary with error summary information
        """
        # Filter errors related to this export job
        job_errors = [
            error for error in self.error_history
            if error.context.get('export_id') == str(export_job.export_id)
        ]
        
        if not job_errors:
            return {
                'total_errors': 0,
                'error_summary': 'No errors recorded for this export job'
            }
        
        # Categorize errors
        error_categories = {}
        severity_counts = {}
        
        for error in job_errors:
            category = error.category.value
            severity = error.severity.value
            
            error_categories[category] = error_categories.get(category, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Find most recent critical error
        critical_errors = [e for e in job_errors if e.severity == ErrorSeverity.CRITICAL]
        most_recent_critical = max(critical_errors, key=lambda e: e.timestamp) if critical_errors else None
        
        return {
            'total_errors': len(job_errors),
            'error_categories': error_categories,
            'severity_breakdown': severity_counts,
            'most_recent_critical_error': {
                'message': most_recent_critical.user_facing_message or most_recent_critical.message,
                'timestamp': most_recent_critical.timestamp.isoformat(),
                'category': most_recent_critical.category.value
            } if most_recent_critical else None,
            'retry_summary': {
                'total_retries': sum(e.retry_count for e in job_errors),
                'max_retries_per_error': max((e.retry_count for e in job_errors), default=0)
            },
            'circuit_breaker_states': {
                name: {
                    'state': cb.state,
                    'failure_count': cb.failure_count,
                    'last_failure': cb.last_failure_time.isoformat() if cb.last_failure_time else None
                }
                for name, cb in self.circuit_breakers.items()
            }
        }
    
    def _classify_error(self, error: Exception, context: Dict[str, Any]) -> ErrorDetails:
        """Classify an error and create ErrorDetails"""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Determine category
        category = self._determine_error_category(error_type, error_message)
        
        # Determine severity
        severity = self._determine_error_severity(category, error_type, error_message)
        
        # Create user-facing message
        user_message = self._create_user_facing_message(category, error_message)
        
        return ErrorDetails(
            category=category,
            severity=severity,
            message=error_message,
            exception_type=error_type,
            stack_trace=traceback.format_exc(),
            context=context,
            user_facing_message=user_message
        )
    
    def _determine_error_category(self, error_type: str, error_message: str) -> ErrorCategory:
        """Determine error category based on type and message"""
        error_key = f"{error_type}:{error_message}".lower()
        
        # Check patterns
        for pattern, category in self.error_patterns.items():
            if pattern in error_key:
                return category
        
        # Fallback classification
        if 'auth' in error_key or 'unauthorized' in error_key:
            return ErrorCategory.AUTHENTICATION
        elif 'permission' in error_key or 'forbidden' in error_key:
            return ErrorCategory.AUTHORIZATION
        elif 's3' in error_key or 'bucket' in error_key:
            return ErrorCategory.S3_OPERATION
        elif 'timeout' in error_key or 'timed out' in error_key:
            return ErrorCategory.TIMEOUT
        elif 'memory' in error_key or 'out of memory' in error_key:
            return ErrorCategory.MEMORY
        elif 'disk' in error_key or 'space' in error_key:
            return ErrorCategory.DISK_SPACE
        elif 'network' in error_key or 'connection' in error_key:
            return ErrorCategory.NETWORK
        elif 'validation' in error_key or 'invalid' in error_key:
            return ErrorCategory.VALIDATION
        elif 'json' in error_key or 'serialize' in error_key:
            return ErrorCategory.SERIALIZATION
        
        return ErrorCategory.UNKNOWN
    
    def _determine_error_severity(self, category: ErrorCategory, error_type: str, 
                                error_message: str) -> ErrorSeverity:
        """Determine error severity"""
        # Critical errors
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION]:
            return ErrorSeverity.CRITICAL
        
        if 'out of memory' in error_message.lower():
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if category in [ErrorCategory.DATA_ACCESS, ErrorCategory.DISK_SPACE]:
            return ErrorSeverity.HIGH
        
        if error_type in ['PermissionError', 'OSError']:
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if category in [ErrorCategory.S3_OPERATION, ErrorCategory.NETWORK, ErrorCategory.TIMEOUT]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors (usually retryable)
        if category in [ErrorCategory.VALIDATION, ErrorCategory.SERIALIZATION]:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def _create_user_facing_message(self, category: ErrorCategory, error_message: str) -> str:
        """Create user-friendly error message"""
        messages = {
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please check your credentials.",
            ErrorCategory.AUTHORIZATION: "You don't have permission to access this resource.",
            ErrorCategory.DATA_ACCESS: "Unable to access your data. Please try again later.",
            ErrorCategory.S3_OPERATION: "File storage operation failed. Please try again.",
            ErrorCategory.NETWORK: "Network connection issue. Please check your internet connection.",
            ErrorCategory.TIMEOUT: "The operation took too long to complete. Please try again.",
            ErrorCategory.MEMORY: "Insufficient memory to complete the operation. Please try with a smaller dataset.",
            ErrorCategory.DISK_SPACE: "Insufficient disk space. Please free up space and try again.",
            ErrorCategory.VALIDATION: "Data validation failed. Please check your data format.",
            ErrorCategory.COMPRESSION: "File compression failed. Please try again.",
            ErrorCategory.UNKNOWN: "An unexpected error occurred. Please try again later."
        }
        
        return messages.get(category, "An error occurred during the export process.")
    
    def _is_error_recoverable(self, error_details: ErrorDetails) -> bool:
        """Determine if an error is recoverable"""
        # Non-recoverable errors
        non_recoverable = [
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.AUTHORIZATION,
            ErrorCategory.DISK_SPACE,
            ErrorCategory.MEMORY
        ]
        
        if error_details.category in non_recoverable:
            return False
        
        # Validation errors are usually not recoverable
        if error_details.category == ErrorCategory.VALIDATION and 'invalid' in error_details.message.lower():
            return False
        
        return True
    
    def _check_circuit_breaker(self, operation_category: str) -> bool:
        """Check if circuit breaker allows operation"""
        if operation_category not in self.circuit_breakers:
            self.circuit_breakers[operation_category] = CircuitBreakerState()
        
        cb = self.circuit_breakers[operation_category]
        
        if cb.state == "open":
            # Check if recovery timeout has elapsed
            if (cb.last_failure_time and 
                datetime.now(timezone.utc) - cb.last_failure_time > timedelta(seconds=cb.recovery_timeout)):
                cb.state = "half_open"
                return True
            return False
        
        return True
    
    def _update_circuit_breaker(self, operation_category: str, success: bool):
        """Update circuit breaker state"""
        if operation_category not in self.circuit_breakers:
            self.circuit_breakers[operation_category] = CircuitBreakerState()
        
        cb = self.circuit_breakers[operation_category]
        
        if success:
            if cb.state == "half_open":
                cb.failure_count = 0
                cb.state = "closed"
            elif cb.state == "closed":
                cb.failure_count = max(0, cb.failure_count - 1)
        else:
            cb.failure_count += 1
            cb.last_failure_time = datetime.now(timezone.utc)
            
            if cb.failure_count >= cb.failure_threshold:
                cb.state = "open"
    
    def _build_error_patterns(self) -> Dict[str, ErrorCategory]:
        """Build error pattern mappings"""
        return {
            'nosuchkey': ErrorCategory.S3_OPERATION,
            'accessdenied': ErrorCategory.AUTHORIZATION,
            'invalidaccesskeyid': ErrorCategory.AUTHENTICATION,
            'tokenerror': ErrorCategory.AUTHENTICATION,
            'connectionerror': ErrorCategory.NETWORK,
            'timeout': ErrorCategory.TIMEOUT,
            'memoryerror': ErrorCategory.MEMORY,
            'nosuchbucket': ErrorCategory.S3_OPERATION,
            'jsondecode': ErrorCategory.SERIALIZATION,
            'validationerror': ErrorCategory.VALIDATION,
            'compresserror': ErrorCategory.COMPRESSION,
            'gziperror': ErrorCategory.COMPRESSION,
            'clienterror': ErrorCategory.DATA_ACCESS,
            'botocoreerror': ErrorCategory.NETWORK,
            'ioerror': ErrorCategory.DISK_SPACE,
            'oserror': ErrorCategory.DISK_SPACE
        }
    
    def _log_error(self, error_details: ErrorDetails):
        """Log error with appropriate level"""
        log_message = f"[{error_details.error_id}] {error_details.category.value}: {error_details.message}"
        
        if error_details.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={'error_details': error_details})
        elif error_details.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra={'error_details': error_details})
        elif error_details.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra={'error_details': error_details})
        else:
            logger.info(log_message, extra={'error_details': error_details})
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        if not self.error_history:
            return {'total_errors': 0, 'message': 'No errors recorded'}
        
        total_errors = len(self.error_history)
        
        # Category breakdown
        category_counts: Dict[str, int] = {}
        for error in self.error_history:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Severity breakdown
        severity_counts: Dict[str, int] = {}
        for error in self.error_history:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Recent errors (last hour)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_errors = [e for e in self.error_history if e.timestamp > one_hour_ago]
        
        # Find most common category more efficiently
        most_common_category = None
        most_common_count = 0
        if category_counts:
            most_common_category = max(category_counts, key=lambda k: category_counts[k])
            most_common_count = category_counts[most_common_category]
        
        return {
            'total_errors': total_errors,
            'category_breakdown': category_counts,
            'severity_breakdown': severity_counts,
            'recent_errors_count': len(recent_errors),
            'circuit_breaker_states': {
                name: cb.state for name, cb in self.circuit_breakers.items()
            },
            'error_rate_last_hour': len(recent_errors),
            'most_common_category': most_common_category,
            'most_common_category_count': most_common_count
        }


# Global error handler instance
export_error_handler = ExportErrorHandler() 