"""
Unit tests for Pattern Review Service.

Tests user review actions on detected patterns including confirm, reject,
and edit operations with validation.
"""

import unittest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import List

from models.transaction import Transaction
from models.recurring_charge import (
    RecurringChargePattern,
    PatternStatus,
    PatternReviewAction,
    RecurrenceFrequency,
    TemporalPatternType,
    PatternCriteriaValidation
)
from services.recurring_charges.pattern_review_service import PatternReviewService
from services.recurring_charges.pattern_validation_service import PatternValidationService


class MockValidationService(PatternValidationService):
    """Mock validation service for testing."""
    
    def __init__(self, is_valid: bool = True, warnings: List[str] = None):
        """
        Initialize mock with predetermined validation result.
        
        Args:
            is_valid: Whether validation should pass
            warnings: Optional warnings to include in result
        """
        super().__init__()
        self.is_valid = is_valid
        self.warnings = warnings or []
    
    def validate_pattern_criteria(
        self,
        pattern: RecurringChargePattern,
        all_transactions: List[Transaction]
    ) -> PatternCriteriaValidation:
        """Return predetermined validation result."""
        return PatternCriteriaValidation(
            patternId=pattern.pattern_id,
            isValid=self.is_valid,
            originalCount=3,
            criteriaMatchCount=3 if self.is_valid else 2,
            allOriginalMatchCriteria=self.is_valid,
            noFalsePositives=self.is_valid,
            perfectMatch=self.is_valid,
            warnings=self.warnings
        )


class TestPatternReviewService(unittest.TestCase):
    """Test cases for PatternReviewService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test_user_123"
        self.pattern_id = uuid.uuid4()
        self.file_id = uuid.uuid4()
        self.account_id = uuid.uuid4()
        
        # Create a sample detected pattern
        self.pattern = RecurringChargePattern(
            patternId=self.pattern_id,
            userId=self.user_id,
            merchantPattern="Netflix",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            dayOfMonth=15,
            toleranceDays=2,
            amountMean=Decimal("15.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("15.99"),
            amountMax=Decimal("15.99"),
            amountTolerancePct=Decimal("10.0"),
            confidenceScore=Decimal("0.95"),
            transactionCount=12,
            firstOccurrence=int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp() * 1000),
            lastOccurrence=int(datetime(2024, 12, 15, tzinfo=timezone.utc).timestamp() * 1000),
            status=PatternStatus.DETECTED,
            active=False,
            criteriaValidated=False
        )
        
        # Create sample transactions (minimal for testing)
        self.transactions = [
            Transaction(
                transactionId=uuid.uuid4(),
                userId=self.user_id,
                fileId=self.file_id,
                accountId=self.account_id,
                description="Netflix subscription",
                amount=Decimal("15.99"),
                date=int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp() * 1000)
            ),
            Transaction(
                transactionId=uuid.uuid4(),
                userId=self.user_id,
                fileId=self.file_id,
                accountId=self.account_id,
                description="Netflix subscription",
                amount=Decimal("15.99"),
                date=int(datetime(2024, 2, 15, tzinfo=timezone.utc).timestamp() * 1000)
            ),
            Transaction(
                transactionId=uuid.uuid4(),
                userId=self.user_id,
                fileId=self.file_id,
                accountId=self.account_id,
                description="Netflix subscription",
                amount=Decimal("15.99"),
                date=int(datetime(2024, 3, 15, tzinfo=timezone.utc).timestamp() * 1000)
            )
        ]
    
    def test_edit_pattern_with_validation_failure_sets_confirmed_status(self):
        """
        Test that when pattern edit results in validation failure,
        the pattern status is set to CONFIRMED (not left in DETECTED).
        
        This ensures edited patterns move forward in the workflow even if
        validation fails, while the criteria_validated flag prevents activation.
        """
        # Arrange: Create service with mock that will return validation failure
        mock_validation = MockValidationService(
            is_valid=False,
            warnings=["Edited criteria do not match all original cluster transactions"]
        )
        review_service = PatternReviewService(validation_service=mock_validation)
        
        review_action = PatternReviewAction(
            patternId=self.pattern_id,
            action="edit",
            userId=self.user_id,
            editedMerchantPattern="Netflix.*"  # Edit the merchant pattern
        )
        
        # Act: Edit the pattern
        updated_pattern, validation_result = review_service.review_pattern(
            self.pattern,
            review_action,
            self.transactions
        )
        
        # Assert: Pattern should be CONFIRMED even though validation failed
        self.assertEqual(updated_pattern.status, PatternStatus.CONFIRMED)
        self.assertFalse(updated_pattern.criteria_validated)
        self.assertEqual(
            updated_pattern.criteria_validation_errors,
            ["Edited criteria do not match all original cluster transactions"]
        )
        self.assertFalse(updated_pattern.active)
        self.assertEqual(updated_pattern.merchant_pattern, "Netflix.*")
    
    def test_edit_pattern_with_validation_success_sets_confirmed_status(self):
        """Test that when pattern edit succeeds validation, status is CONFIRMED."""
        # Arrange: Create service with mock that will return validation success
        mock_validation = MockValidationService(is_valid=True, warnings=[])
        review_service = PatternReviewService(validation_service=mock_validation)
        
        review_action = PatternReviewAction(
            patternId=self.pattern_id,
            action="edit",
            userId=self.user_id,
            editedAmountTolerancePct=Decimal("15.0")
        )
        
        # Act: Edit the pattern
        updated_pattern, validation_result = review_service.review_pattern(
            self.pattern,
            review_action,
            self.transactions
        )
        
        # Assert: Pattern should be CONFIRMED with validation passing
        self.assertEqual(updated_pattern.status, PatternStatus.CONFIRMED)
        self.assertTrue(updated_pattern.criteria_validated)
        self.assertEqual(updated_pattern.criteria_validation_errors, [])
        self.assertFalse(updated_pattern.active)  # Not activated without flag
        self.assertEqual(updated_pattern.amount_tolerance_pct, Decimal("15.0"))
    
    def test_edit_pattern_with_activate_and_validation_failure_does_not_activate(self):
        """
        Test that when edit includes activate_immediately but validation fails,
        the pattern is CONFIRMED but not ACTIVE.
        """
        # Arrange: Create service with mock that will return validation failure
        mock_validation = MockValidationService(
            is_valid=False,
            warnings=["Amount tolerance too wide for cluster"]
        )
        review_service = PatternReviewService(validation_service=mock_validation)
        
        review_action = PatternReviewAction(
            patternId=self.pattern_id,
            action="edit",
            userId=self.user_id,
            editedAmountTolerancePct=Decimal("50.0"),
            activateImmediately=True  # Request activation
        )
        
        # Act: Edit the pattern
        updated_pattern, validation_result = review_service.review_pattern(
            self.pattern,
            review_action,
            self.transactions
        )
        
        # Assert: Pattern should be CONFIRMED but NOT ACTIVE due to validation failure
        self.assertEqual(updated_pattern.status, PatternStatus.CONFIRMED)
        self.assertFalse(updated_pattern.criteria_validated)
        self.assertFalse(updated_pattern.active)
        self.assertEqual(updated_pattern.amount_tolerance_pct, Decimal("50.0"))
    
    def test_edit_pattern_with_activate_and_validation_success_activates(self):
        """
        Test that when edit includes activate_immediately and validation succeeds,
        the pattern is set to ACTIVE.
        """
        # Arrange: Create service with mock that will return validation success
        mock_validation = MockValidationService(is_valid=True, warnings=[])
        review_service = PatternReviewService(validation_service=mock_validation)
        
        review_action = PatternReviewAction(
            patternId=self.pattern_id,
            action="edit",
            userId=self.user_id,
            editedToleranceDays=3,
            activateImmediately=True
        )
        
        # Act: Edit the pattern
        updated_pattern, validation_result = review_service.review_pattern(
            self.pattern,
            review_action,
            self.transactions
        )
        
        # Assert: Pattern should be ACTIVE
        self.assertEqual(updated_pattern.status, PatternStatus.ACTIVE)
        self.assertTrue(updated_pattern.criteria_validated)
        self.assertTrue(updated_pattern.active)
        self.assertEqual(updated_pattern.tolerance_days, 3)
    
    def test_reject_pattern(self):
        """Test pattern rejection."""
        review_service = PatternReviewService()
        
        review_action = PatternReviewAction(
            patternId=self.pattern_id,
            action="reject",
            userId=self.user_id,
            notes="Not a real recurring charge"
        )
        
        # Act: Reject the pattern
        updated_pattern, validation_result = review_service.review_pattern(
            self.pattern,
            review_action,
            self.transactions
        )
        
        # Assert: Pattern should be REJECTED
        self.assertEqual(updated_pattern.status, PatternStatus.REJECTED)
        self.assertFalse(updated_pattern.active)
        self.assertIsNone(validation_result)
    
    def test_confirm_pattern_with_validation_success(self):
        """Test confirming a pattern that passes validation."""
        # Arrange: Create service with mock that will return validation success
        mock_validation = MockValidationService(is_valid=True, warnings=[])
        review_service = PatternReviewService(validation_service=mock_validation)
        
        review_action = PatternReviewAction(
            patternId=self.pattern_id,
            action="confirm",
            userId=self.user_id
        )
        
        # Act: Confirm the pattern
        updated_pattern, validation_result = review_service.review_pattern(
            self.pattern,
            review_action,
            self.transactions
        )
        
        # Assert: Pattern should be CONFIRMED
        self.assertEqual(updated_pattern.status, PatternStatus.CONFIRMED)
        self.assertTrue(updated_pattern.criteria_validated)
        self.assertFalse(updated_pattern.active)  # Not activated without flag


if __name__ == "__main__":
    unittest.main()

