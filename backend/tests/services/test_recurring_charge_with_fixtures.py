"""
Example tests using the new test fixtures.

Demonstrates how to use the recurring charge test fixtures for cleaner,
more maintainable tests.
"""

import pytest
from decimal import Decimal

from services.recurring_charges import RecurringChargeDetectionService, DetectionConfig
from tests.fixtures.recurring_charge_fixtures import (
    create_test_scenario,
    create_test_account,
    create_monthly_transactions,
)
from models.recurring_charge import RecurrenceFrequency


class TestRecurringChargeWithFixtures:
    """Test recurring charge detection using test fixtures."""
    
    def test_credit_card_subscription_detection(self):
        """Test detection of monthly subscription on credit card."""
        # Use predefined scenario
        scenario = create_test_scenario("credit_card_subscription")
        
        # Use larger eps for account-aware features (91 dimensions)
        service = RecurringChargeDetectionService()
        patterns = service.detect_recurring_patterns(
            user_id="test-user",
            transactions=scenario["transactions"],
            accounts_map=scenario["accounts_map"],
            eps=2.0  # Larger eps for high-dimensional space
        )
        
        # Should detect the Netflix pattern
        assert len(patterns) >= 1, f"Expected at least 1 pattern, got {len(patterns)}"
        
        # Verify pattern properties
        pattern = patterns[0]
        assert pattern.frequency == RecurrenceFrequency.MONTHLY
        assert "NETFLIX" in pattern.merchant_pattern
        assert abs(float(pattern.amount_mean) - 15.99) < 1.0
        assert pattern.confidence_score >= 0.6
    
    def test_checking_utility_bill_detection(self):
        """Test detection of utility bill with varying amounts."""
        scenario = create_test_scenario("checking_utility")
        
        service = RecurringChargeDetectionService()
        patterns = service.detect_recurring_patterns(
            user_id="test-user",
            transactions=scenario["transactions"],
            accounts_map=scenario["accounts_map"],
            eps=2.0  # Larger eps for high-dimensional space
        )
        
        assert len(patterns) >= 1
        pattern = patterns[0]
        assert pattern.frequency == RecurrenceFrequency.MONTHLY
        assert "ELECTRIC" in pattern.merchant_pattern
    
    def test_salary_deposit_detection(self):
        """Test detection of bi-weekly salary deposits."""
        scenario = create_test_scenario("salary_deposit")
        
        service = RecurringChargeDetectionService()
        patterns = service.detect_recurring_patterns(
            user_id="test-user",
            transactions=scenario["transactions"],
            accounts_map=scenario["accounts_map"],
            eps=2.0  # Larger eps for high-dimensional space
        )
        
        assert len(patterns) >= 1, f"Expected at least 1 pattern, got {len(patterns)}"
        pattern = patterns[0]
        # Bi-weekly can sometimes be detected as irregular due to calendar variance
        assert pattern.frequency in [RecurrenceFrequency.BI_WEEKLY, RecurrenceFrequency.IRREGULAR]
        assert "PAYROLL" in pattern.merchant_pattern
        assert float(pattern.amount_mean) > 0  # Deposits are positive
    
    def test_custom_scenario_creation(self):
        """Test creating a custom scenario with factory functions."""
        from models.account import AccountType
        
        # Create account
        account = create_test_account(
            user_id="test-user",
            account_type=AccountType.CREDIT_CARD,
            account_name="My Card",
            institution="Citi"
        )
        
        # Create transactions
        transactions = create_monthly_transactions(
            user_id="test-user",
            account_id=account.account_id,
            merchant="SPOTIFY PREMIUM",
            amount=Decimal("-9.99"),
            count=12,
            day_of_month=15
        )
        
        # Run detection
        service = RecurringChargeDetectionService()
        patterns = service.detect_recurring_patterns(
            user_id="test-user",
            transactions=transactions,
            accounts_map={account.account_id: account},
            eps=2.0  # Larger eps for high-dimensional space
        )
        
        assert len(patterns) >= 1
        assert "SPOTIFY" in patterns[0].merchant_pattern
    
    def test_detection_with_custom_config(self):
        """Test detection with custom configuration."""
        from services.recurring_charges import ClusteringConfig, ConfidenceWeights
        
        # Create custom config with stricter confidence requirements
        custom_config = DetectionConfig(
            confidence_weights=ConfidenceWeights(
                interval_regularity=0.40,  # Increase weight on regularity
                amount_regularity=0.30,
                sample_size=0.10,
                temporal_consistency=0.20
            ),
            min_confidence=0.75,  # Higher threshold
            min_occurrences=4  # More samples required
        )
        
        scenario = create_test_scenario("credit_card_subscription")
        
        service = RecurringChargeDetectionService(config=custom_config)
        patterns = service.detect_recurring_patterns(
            user_id="test-user",
            transactions=scenario["transactions"],
            accounts_map=scenario["accounts_map"]
        )
        
        # With stricter config, may or may not detect patterns
        # But all detected patterns should meet the higher threshold
        for pattern in patterns:
            assert pattern.confidence_score >= 0.75
            assert pattern.transaction_count >= 4
    
    def test_mixed_accounts_scenario(self):
        """Test detection across multiple accounts."""
        scenario = create_test_scenario("mixed_accounts")
        
        service = RecurringChargeDetectionService()
        patterns = service.detect_recurring_patterns(
            user_id="test-user",
            transactions=scenario["transactions"],
            accounts_map=scenario["accounts_map"],
            eps=2.0  # Larger eps for high-dimensional space
        )
        
        # Should detect Netflix, Spotify, and Rent patterns
        assert len(patterns) >= 3, f"Expected at least 3 patterns, got {len(patterns)}"
        
        merchants = [p.merchant_pattern for p in patterns]
        assert any("NETFLIX" in m for m in merchants)
        assert any("SPOTIFY" in m for m in merchants)
        assert any("RENT" in m for m in merchants)

