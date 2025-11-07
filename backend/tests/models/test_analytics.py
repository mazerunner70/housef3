"""
Test for Analytics model enum conversion and serialization.

This test verifies that Analytics models properly handle enum conversion
for DataQuality, AnalyticType, and ComputationStatus fields.
"""
from datetime import date, datetime, timezone
from typing import Dict, Any

import pytest

from models.analytics import (
    DataQuality,
    AnalyticType,
    ComputationStatus,
    AccountDataRange,
    AnalyticsProcessingStatus
)


class TestAnalyticsEnumConversion:
    """Test Analytics model enum conversion."""

    def test_account_data_range_preserves_data_quality_enum(self):
        """
        Test that AccountDataRange preserves DataQuality enum objects.
        
        This test verifies that:
        1. DataQuality enum objects are preserved (not converted to strings)
        2. .value attribute access works without AttributeError
        3. Enum type checking works correctly
        """
        # Arrange: Create AccountDataRange with enum
        data_range = AccountDataRange(
            account_id='test-account-123',
            earliestTransactionDate=date(2024, 1, 1),
            latestTransactionDate=date(2024, 12, 31),
            lastStatementUpload=datetime(2024, 12, 31, 12, 0, 0, tzinfo=timezone.utc),
            dataQuality=DataQuality.COMPLETE,  # Enum object
            transactionCount=150
        )
        
        # Assert: DataQuality should be an actual enum object, not a string
        assert data_range.data_quality is not None, "DataQuality should not be None"
        assert isinstance(data_range.data_quality, DataQuality), \
            f"Expected DataQuality enum, got {type(data_range.data_quality)}"
        
        # Critical test: .value attribute should work without AttributeError
        try:
            quality_value = data_range.data_quality.value
            assert quality_value == 'complete', f"Expected 'complete', got {quality_value}"
        except AttributeError as e:
            pytest.fail(f"DataQuality enum should have .value attribute: {e}")
        
        # Use type checking for string-based enums
        assert type(data_range.data_quality).__name__ == 'DataQuality', \
            f"Expected DataQuality type, got {type(data_range.data_quality).__name__}"

    def test_account_data_range_from_dict_with_string_enum(self):
        """
        Test that AccountDataRange can be created from dict with string enum values.
        
        This simulates deserialization from DynamoDB or API.
        """
        # Arrange: Mock data with string enum value
        data = {
            'account_id': 'test-account-123',
            'earliestTransactionDate': '2024-01-01',
            'latestTransactionDate': '2024-12-31',
            'lastStatementUpload': '2024-12-31T12:00:00Z',
            'dataQuality': 'partial',  # String value
            'transactionCount': 100
        }
        
        # Act: Create using model_validate
        data_range = AccountDataRange.model_validate(data)
        
        # Assert: DataQuality should be converted to enum object
        assert isinstance(data_range.data_quality, DataQuality), \
            f"Expected DataQuality enum, got {type(data_range.data_quality)}"
        assert data_range.data_quality == DataQuality.PARTIAL
        
        # Critical test: .value attribute should work
        try:
            quality_value = data_range.data_quality.value
            assert quality_value == 'partial'
        except AttributeError as e:
            pytest.fail(f"DataQuality enum should have .value attribute: {e}")

    def test_analytics_processing_status_preserves_enums(self):
        """
        Test that AnalyticsProcessingStatus preserves both AnalyticType and ComputationStatus enums.
        """
        # Arrange: Create with enums
        status = AnalyticsProcessingStatus(
            userId='test-user',
            analyticType=AnalyticType.CASH_FLOW,  # Enum object
            lastComputedDate=date(2024, 12, 1),
            dataAvailableThrough=date(2024, 12, 31),
            status=ComputationStatus.COMPLETED  # Enum object
        )
        
        # Assert: AnalyticType should be an enum object
        assert isinstance(status.analytic_type, AnalyticType), \
            f"Expected AnalyticType enum, got {type(status.analytic_type)}"
        
        # Critical test: .value attribute should work
        try:
            analytic_value = status.analytic_type.value
            assert analytic_value == 'cash_flow'
        except AttributeError as e:
            pytest.fail(f"AnalyticType enum should have .value attribute: {e}")
        
        # Assert: ComputationStatus should be an enum object
        assert isinstance(status.status, ComputationStatus), \
            f"Expected ComputationStatus enum, got {type(status.status)}"
        
        # Critical test: .value attribute should work
        try:
            status_value = status.status.value
            assert status_value == 'completed'
        except AttributeError as e:
            pytest.fail(f"ComputationStatus enum should have .value attribute: {e}")

    def test_analytics_processing_status_from_dict_with_string_enums(self):
        """
        Test that AnalyticsProcessingStatus can be created from dict with string enum values.
        """
        # Arrange: Mock data with string enum values
        data = {
            'userId': 'test-user',
            'analyticType': 'category_trends',  # String value
            'lastComputedDate': '2024-12-01',
            'dataAvailableThrough': '2024-12-31',
            'status': 'in_progress',  # String value
            'processingPriority': 1
        }
        
        # Act: Create using model_validate
        processing_status = AnalyticsProcessingStatus.model_validate(data)
        
        # Assert: Enums should be converted to enum objects
        assert isinstance(processing_status.analytic_type, AnalyticType), \
            f"Expected AnalyticType enum, got {type(processing_status.analytic_type)}"
        assert processing_status.analytic_type == AnalyticType.CATEGORY_TRENDS
        
        assert isinstance(processing_status.status, ComputationStatus), \
            f"Expected ComputationStatus enum, got {type(processing_status.status)}"
        assert processing_status.status == ComputationStatus.IN_PROGRESS

    def test_analytics_roundtrip_serialization(self):
        """
        Test that AnalyticsProcessingStatus can be serialized and deserialized.
        """
        # Arrange: Create with enums
        original = AnalyticsProcessingStatus(
            userId='test-user',
            analyticType=AnalyticType.BUDGET_PERFORMANCE,
            lastComputedDate=date(2024, 11, 1),
            dataAvailableThrough=date(2024, 11, 30),
            status=ComputationStatus.PENDING,
            processingPriority=2
        )
        
        # Act: Serialize to dict (simulating DynamoDB)
        serialized = original.model_dump(by_alias=True, mode='json')
        
        # Assert: Enums should be serialized as strings
        assert isinstance(serialized['analyticType'], str), \
            "Serialized analyticType should be string"
        assert serialized['analyticType'] == 'budget_performance'
        assert isinstance(serialized['status'], str), \
            "Serialized status should be string"
        assert serialized['status'] == 'pending'
        
        # Act: Deserialize back
        deserialized = AnalyticsProcessingStatus.model_validate(serialized)
        
        # Assert: Enums should be restored
        assert isinstance(deserialized.analytic_type, AnalyticType), \
            "Deserialized analyticType should be AnalyticType enum"
        assert deserialized.analytic_type == AnalyticType.BUDGET_PERFORMANCE
        assert isinstance(deserialized.status, ComputationStatus), \
            "Deserialized status should be ComputationStatus enum"
        assert deserialized.status == ComputationStatus.PENDING

    def test_all_data_quality_values(self):
        """Test that all DataQuality enum values work correctly."""
        qualities = [
            DataQuality.COMPLETE,
            DataQuality.PARTIAL,
            DataQuality.GAPS
        ]
        
        for quality in qualities:
            # Arrange: Create with specific quality
            data_range = AccountDataRange(
                account_id='test-account',
                earliestTransactionDate=date(2024, 1, 1),
                latestTransactionDate=date(2024, 12, 31),
                lastStatementUpload=datetime(2024, 12, 31, 12, 0, 0, tzinfo=timezone.utc),
                dataQuality=quality,
                transactionCount=50
            )
            
            # Assert: Enum is preserved
            assert isinstance(data_range.data_quality, DataQuality)
            assert data_range.data_quality == quality
            
            # Act: Serialize and deserialize
            serialized = data_range.model_dump(by_alias=True, mode='json')
            deserialized = AccountDataRange.model_validate(serialized)
            
            # Assert: Enum is preserved after roundtrip
            assert isinstance(deserialized.data_quality, DataQuality)
            assert deserialized.data_quality == quality

    def test_all_analytic_types(self):
        """Test that all AnalyticType enum values work correctly."""
        analytic_types = [
            AnalyticType.CASH_FLOW,
            AnalyticType.CATEGORY_TRENDS,
            AnalyticType.BUDGET_PERFORMANCE,
            AnalyticType.FINANCIAL_HEALTH,
            AnalyticType.CREDIT_UTILIZATION,
            AnalyticType.PAYMENT_PATTERNS,
            AnalyticType.ACCOUNT_EFFICIENCY,
            AnalyticType.MERCHANT_ANALYSIS,
            AnalyticType.GOAL_PROGRESS,
            AnalyticType.RECOMMENDATIONS
        ]
        
        for analytic_type in analytic_types:
            # Arrange: Create with specific type
            status = AnalyticsProcessingStatus(
                userId='test-user',
                analyticType=analytic_type,
                lastComputedDate=date(2024, 12, 1),
                dataAvailableThrough=date(2024, 12, 31),
                status=ComputationStatus.PENDING
            )
            
            # Assert: Enum is preserved
            assert isinstance(status.analytic_type, AnalyticType)
            assert status.analytic_type == analytic_type
            
            # Act: Serialize and deserialize
            serialized = status.model_dump(by_alias=True, mode='json')
            deserialized = AnalyticsProcessingStatus.model_validate(serialized)
            
            # Assert: Enum is preserved after roundtrip
            assert isinstance(deserialized.analytic_type, AnalyticType)
            assert deserialized.analytic_type == analytic_type

    def test_all_computation_statuses(self):
        """Test that all ComputationStatus enum values work correctly."""
        statuses = [
            ComputationStatus.PENDING,
            ComputationStatus.IN_PROGRESS,
            ComputationStatus.COMPLETED,
            ComputationStatus.FAILED,
            ComputationStatus.STALE
        ]
        
        for computation_status in statuses:
            # Arrange: Create with specific status
            status = AnalyticsProcessingStatus(
                userId='test-user',
                analyticType=AnalyticType.CASH_FLOW,
                lastComputedDate=date(2024, 12, 1),
                dataAvailableThrough=date(2024, 12, 31),
                status=computation_status
            )
            
            # Assert: Enum is preserved
            assert isinstance(status.status, ComputationStatus)
            assert status.status == computation_status
            
            # Act: Serialize and deserialize
            serialized = status.model_dump(by_alias=True, mode='json')
            deserialized = AnalyticsProcessingStatus.model_validate(serialized)
            
            # Assert: Enum is preserved after roundtrip
            assert isinstance(deserialized.status, ComputationStatus)
            assert deserialized.status == computation_status


if __name__ == "__main__":
    # Run the specific test
    pytest.main([__file__, "-v"])

