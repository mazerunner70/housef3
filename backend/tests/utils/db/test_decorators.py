"""
Unit tests for database decorators.

Tests the decorator functionality including:
- Error handling (dynamodb_operation)
- Retry logic (retry_on_throttle)
- Performance monitoring (monitor_performance)
- Parameter validation (validate_params)
- Caching (cache_result)
"""

import unittest
import time
import uuid as uuid_module
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from pydantic import ValidationError

from utils.db.base import (
    dynamodb_operation,
    retry_on_throttle,
    monitor_performance,
    validate_params,
    cache_result,
    is_valid_uuid,
    is_positive_int,
    is_valid_limit,
)


class TestDynamoDBOperationDecorator(unittest.TestCase):
    """Tests for @dynamodb_operation decorator."""
    
    def test_successful_operation(self):
        """Test decorator handles successful operation."""
        @dynamodb_operation("test_op")
        def successful_function():
            return "success"
        
        result = successful_function()
        self.assertEqual(result, "success")
    
    def test_client_error_handling(self):
        """Test decorator handles ClientError correctly."""
        @dynamodb_operation("test_op")
        def failing_function():
            raise ClientError(
                {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
                'GetItem'
            )
        
        with self.assertRaises(ClientError):
            failing_function()
    
    def test_validation_error_converted(self):
        """Test ValidationError is converted to ValueError."""
        from pydantic import BaseModel, field_validator
        
        class TestModel(BaseModel):
            value: int
            
            @field_validator('value')
            @classmethod
            def validate_value(cls, v):
                if v < 0:
                    raise ValueError('Must be positive')
                return v
        
        @dynamodb_operation("test_op")
        def validation_failing_function():
            # This will raise ValidationError
            TestModel(value=-1)
            return "should not reach here"
        
        with self.assertRaises(ValueError) as context:
            validation_failing_function()
        self.assertIn("Invalid data", str(context.exception))
    
    def test_generic_exception_handling(self):
        """Test decorator handles generic exceptions."""
        @dynamodb_operation("test_op")
        def generic_failing_function():
            raise RuntimeError("Something went wrong")
        
        with self.assertRaises(RuntimeError):
            generic_failing_function()


class TestRetryOnThrottleDecorator(unittest.TestCase):
    """Tests for @retry_on_throttle decorator."""
    
    def test_retries_on_throttle(self):
        """Test retry decorator retries throttled requests."""
        attempt_count = [0]
        
        @retry_on_throttle(max_attempts=3, base_delay=0.01)
        def throttled_function():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise ClientError(
                    {'Error': {'Code': 'ThrottlingException', 'Message': 'Throttled'}},
                    'Query'
                )
            return "success"
        
        result = throttled_function()
        self.assertEqual(result, "success")
        self.assertEqual(attempt_count[0], 3)
    
    def test_gives_up_after_max_attempts(self):
        """Test retry decorator stops after max attempts."""
        @retry_on_throttle(max_attempts=3, base_delay=0.01)
        def always_throttled():
            raise ClientError(
                {'Error': {'Code': 'ThrottlingException', 'Message': 'Throttled'}},
                'Query'
            )
        
        with self.assertRaises(ClientError):
            always_throttled()
    
    def test_does_not_retry_non_throttle_errors(self):
        """Test retry decorator doesn't retry non-throttle errors."""
        attempt_count = [0]
        
        @retry_on_throttle(max_attempts=3, base_delay=0.01)
        def non_throttle_error():
            attempt_count[0] += 1
            raise ClientError(
                {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
                'GetItem'
            )
        
        with self.assertRaises(ClientError):
            non_throttle_error()
        
        # Should only try once since it's not a throttle error
        self.assertEqual(attempt_count[0], 1)
    
    def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        attempt_times = []
        
        @retry_on_throttle(max_attempts=3, base_delay=0.1, exponential_base=2)
        def timed_throttled_function():
            attempt_times.append(time.time())
            if len(attempt_times) < 3:
                raise ClientError(
                    {'Error': {'Code': 'ThrottlingException', 'Message': 'Throttled'}},
                    'Query'
                )
            return "success"
        
        result = timed_throttled_function()
        
        self.assertEqual(result, "success")
        self.assertEqual(len(attempt_times), 3)
        
        # Check delays are roughly exponential
        delay1 = attempt_times[1] - attempt_times[0]
        delay2 = attempt_times[2] - attempt_times[1]
        
        # Allow some tolerance for timing
        self.assertGreater(delay1, 0.08)
        self.assertLess(delay1, 0.15)
        self.assertGreater(delay2, 0.18)
        self.assertLess(delay2, 0.25)


class TestMonitorPerformanceDecorator(unittest.TestCase):
    """Tests for @monitor_performance decorator."""
    
    def test_measures_execution_time(self):
        """Test performance monitoring measures execution time."""
        @monitor_performance(warn_threshold_ms=100, error_threshold_ms=500)
        def timed_function():
            time.sleep(0.05)  # 50ms
            return "done"
        
        # Should complete without warnings since it's under threshold
        result = timed_function()
        self.assertEqual(result, "done")
    
    def test_function_result_preserved(self):
        """Test decorator preserves function return value."""
        @monitor_performance()
        def returning_function():
            return {"key": "value"}
        
        result = returning_function()
        self.assertEqual(result, {"key": "value"})
    
    def test_exception_still_raised(self):
        """Test decorator doesn't suppress exceptions."""
        @monitor_performance()
        def failing_function():
            raise ValueError("Test error")
        
        with self.assertRaises(ValueError):
            failing_function()


class TestValidateParamsDecorator(unittest.TestCase):
    """Tests for @validate_params decorator."""
    
    def test_valid_params_pass(self):
        """Test valid parameters pass validation."""
        @validate_params(
            value=is_positive_int,
            limit=is_valid_limit
        )
        def validated_function(value: int, limit: int = 10):
            return value + limit
        
        result = validated_function(5, 20)
        self.assertEqual(result, 25)
    
    def test_invalid_param_raises_error(self):
        """Test invalid parameter raises ValueError."""
        @validate_params(value=is_positive_int)
        def validated_function(value: int):
            return value
        
        with self.assertRaises(ValueError) as context:
            validated_function(-5)
        
        self.assertIn("Invalid value for parameter 'value'", str(context.exception))
    
    def test_optional_param_with_none(self):
        """Test optional parameter with None value."""
        @validate_params(value=is_valid_uuid)
        def validated_function(value=None):
            return value
        
        # Should not raise since None is valid for optional UUIDs
        result = validated_function(None)
        self.assertIsNone(result)


class TestCacheResultDecorator(unittest.TestCase):
    """Tests for @cache_result decorator."""
    
    def test_caches_results(self):
        """Test caching works for repeated calls."""
        call_count = [0]
        
        @cache_result(ttl_seconds=60, maxsize=10)
        def expensive_function(x):
            call_count[0] += 1
            return x * 2
        
        # First call - cache miss
        result1 = expensive_function(5)
        self.assertEqual(result1, 10)
        self.assertEqual(call_count[0], 1)
        
        # Second call - cache hit
        result2 = expensive_function(5)
        self.assertEqual(result2, 10)
        self.assertEqual(call_count[0], 1)  # Should not increment
    
    def test_different_args_different_cache(self):
        """Test different arguments create different cache entries."""
        call_count = [0]
        
        @cache_result(ttl_seconds=60)
        def cached_function(x):
            call_count[0] += 1
            return x * 2
        
        result1 = cached_function(5)
        result2 = cached_function(10)
        
        self.assertEqual(result1, 10)
        self.assertEqual(result2, 20)
        self.assertEqual(call_count[0], 2)  # Two different calls
    
    def test_ttl_expiration(self):
        """Test cache expires after TTL."""
        call_count = [0]
        
        @cache_result(ttl_seconds=0.1, maxsize=10)
        def expiring_function(x):
            call_count[0] += 1
            return x * 2
        
        # First call
        _ = expiring_function(5)
        self.assertEqual(call_count[0], 1)
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Second call - should re-execute
        _ = expiring_function(5)
        self.assertEqual(call_count[0], 2)
    
    def test_cache_clear(self):
        """Test manual cache clearing."""
        call_count = [0]
        
        @cache_result(ttl_seconds=60)
        def clearable_function(x):
            call_count[0] += 1
            return x * 2
        
        _ = clearable_function(5)
        self.assertEqual(call_count[0], 1)
        
        # Clear cache
        clearable_function.cache_clear()
        
        # Should re-execute
        _ = clearable_function(5)
        self.assertEqual(call_count[0], 2)
    
    def test_cache_info(self):
        """Test cache statistics."""
        @cache_result(ttl_seconds=60, maxsize=10)
        def info_function(x):
            return x * 2
        
        info_function(5)
        info_function(10)
        
        info = info_function.cache_info()
        self.assertEqual(info['size'], 2)
        self.assertEqual(info['maxsize'], 10)
        self.assertEqual(info['ttl_seconds'], 60)
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        @cache_result(ttl_seconds=60, maxsize=2)
        def limited_cache_function(x):
            return x * 2
        
        # Fill cache
        limited_cache_function(1)
        limited_cache_function(2)
        
        # This should evict the oldest entry
        limited_cache_function(3)
        
        info = limited_cache_function.cache_info()
        self.assertEqual(info['size'], 2)  # Should not exceed maxsize


class TestValidators(unittest.TestCase):
    """Tests for validator functions."""
    
    def test_is_valid_uuid(self):
        """Test UUID validator."""
        # Valid UUID
        self.assertTrue(is_valid_uuid(uuid_module.uuid4()))
        self.assertTrue(is_valid_uuid(str(uuid_module.uuid4())))
        self.assertTrue(is_valid_uuid(None))  # None is valid for optional
        
        # Invalid UUID
        self.assertFalse(is_valid_uuid("not-a-uuid"))
        self.assertFalse(is_valid_uuid(123))
    
    def test_is_positive_int(self):
        """Test positive integer validator."""
        self.assertTrue(is_positive_int(1))
        self.assertTrue(is_positive_int(100))
        
        self.assertFalse(is_positive_int(0))
        self.assertFalse(is_positive_int(-1))
        self.assertFalse(is_positive_int(1.5))
        self.assertFalse(is_positive_int("1"))
    
    def test_is_valid_limit(self):
        """Test pagination limit validator."""
        self.assertTrue(is_valid_limit(1))
        self.assertTrue(is_valid_limit(500))
        self.assertTrue(is_valid_limit(1000))
        
        self.assertFalse(is_valid_limit(0))
        self.assertFalse(is_valid_limit(-1))
        self.assertFalse(is_valid_limit(1001))
        self.assertFalse(is_valid_limit("100"))  # type: ignore


class TestDecoratorComposition(unittest.TestCase):
    """Tests for combining multiple decorators."""
    
    def test_stacked_decorators(self):
        """Test multiple decorators work together."""
        call_count = [0]
        
        @cache_result(ttl_seconds=60)
        @monitor_performance(warn_threshold_ms=1000)
        @retry_on_throttle(max_attempts=2, base_delay=0.01)
        @dynamodb_operation("composed_function")
        def composed_function(x):
            call_count[0] += 1
            return x * 2
        
        # First call
        result1 = composed_function(5)
        self.assertEqual(result1, 10)
        self.assertEqual(call_count[0], 1)
        
        # Second call - should be cached
        result2 = composed_function(5)
        self.assertEqual(result2, 10)
        self.assertEqual(call_count[0], 1)  # Should not increment due to cache
    
    def test_decorator_order_matters(self):
        """Test decorator execution order."""
        execution_log = []
        
        @monitor_performance(warn_threshold_ms=1000)
        @dynamodb_operation("ordered_function")
        def ordered_function():
            execution_log.append("function")
            return "done"
        
        result = ordered_function()
        self.assertEqual(result, "done")
        # Function should execute (logged by function itself)
        self.assertIn("function", execution_log)


if __name__ == '__main__':
    unittest.main()
