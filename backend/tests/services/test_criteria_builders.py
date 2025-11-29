"""
Unit tests for Criteria Builder Services.

Tests the MerchantCriteriaBuilder, AmountCriteriaBuilder, and TemporalCriteriaBuilder
that help users build matching criteria from example transactions during Phase 1 review.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from services.recurring_charges.criteria_builders import (
    MerchantCriteriaBuilder,
    AmountCriteriaBuilder,
    TemporalCriteriaBuilder
)
from models.recurring_charge import RecurrenceFrequency, TemporalPatternType


class TestMerchantCriteriaBuilder:
    """Test suite for MerchantCriteriaBuilder."""
    
    def test_extract_common_pattern_identical_descriptions(self):
        """Test pattern extraction when all descriptions are identical."""
        descriptions = [
            "NETFLIX SUBSCRIPTION",
            "NETFLIX SUBSCRIPTION",
            "NETFLIX SUBSCRIPTION"
        ]
        
        result = MerchantCriteriaBuilder.extract_common_pattern(descriptions)
        
        assert result['common_substring'] == "NETFLIX SUBSCRIPTION"
        assert result['common_prefix'] == "NETFLIX SUBSCRIPTION"
        assert result['match_type'] == 'prefix'
        assert result['confidence'] > 0.8
    
    def test_extract_common_pattern_with_variations(self):
        """Test pattern extraction with variations in descriptions."""
        descriptions = [
            "NETFLIX.COM SUBSCRIPTION",
            "NETFLIX.COM MONTHLY",
            "NETFLIX.COM PAYMENT"
        ]
        
        result = MerchantCriteriaBuilder.extract_common_pattern(descriptions)
        
        assert "NETFLIX" in result['common_substring']
        assert result['match_type'] in ['prefix', 'contains']
        assert len(result['variations']) > 0
    
    def test_extract_common_pattern_empty_list(self):
        """Test pattern extraction with empty description list."""
        result = MerchantCriteriaBuilder.extract_common_pattern([])
        
        assert result['common_substring'] == ''
        assert result['suggested_pattern'] == ''
        assert result['confidence'] == 0.0
    
    def test_build_matching_function_exact(self):
        """Test building exact match function."""
        matcher = MerchantCriteriaBuilder.build_matching_function(
            pattern="NETFLIX",
            match_type='exact',
            case_sensitive=False
        )
        
        assert matcher("NETFLIX") is True
        assert matcher("netflix") is True
        assert matcher("NETFLIX SUBSCRIPTION") is False
    
    def test_build_matching_function_contains(self):
        """Test building contains match function."""
        matcher = MerchantCriteriaBuilder.build_matching_function(
            pattern="NETFLIX",
            match_type='contains',
            case_sensitive=False
        )
        
        assert matcher("NETFLIX SUBSCRIPTION") is True
        assert matcher("MY NETFLIX ACCOUNT") is True
        assert matcher("SPOTIFY") is False
    
    def test_build_matching_function_prefix(self):
        """Test building prefix match function."""
        matcher = MerchantCriteriaBuilder.build_matching_function(
            pattern="NETFLIX",
            match_type='prefix',
            case_sensitive=False
        )
        
        assert matcher("NETFLIX SUBSCRIPTION") is True
        assert matcher("netflix premium") is True
        assert matcher("MY NETFLIX") is False
    
    def test_build_matching_function_suffix(self):
        """Test building suffix match function."""
        matcher = MerchantCriteriaBuilder.build_matching_function(
            pattern="SUBSCRIPTION",
            match_type='suffix',
            case_sensitive=False
        )
        
        assert matcher("NETFLIX SUBSCRIPTION") is True
        assert matcher("spotify subscription") is True
        assert matcher("SUBSCRIPTION SERVICE") is False
    
    def test_build_matching_function_with_exclusions(self):
        """Test building match function with exclusion words."""
        matcher = MerchantCriteriaBuilder.build_matching_function(
            pattern="NETFLIX",
            match_type='contains',
            exclusions=["REFUND", "CANCEL"],
            case_sensitive=False
        )
        
        assert matcher("NETFLIX SUBSCRIPTION") is True
        assert matcher("NETFLIX REFUND") is False
        assert matcher("NETFLIX CANCEL") is False
    
    def test_build_matching_function_case_sensitive(self):
        """Test case-sensitive matching."""
        matcher = MerchantCriteriaBuilder.build_matching_function(
            pattern="NETFLIX",
            match_type='contains',
            case_sensitive=True
        )
        
        assert matcher("NETFLIX SUBSCRIPTION") is True
        assert matcher("netflix subscription") is False
    
    def test_build_matching_function_regex_with_word_chars(self):
        """Test regex pattern with \\w metacharacter and case-insensitive matching."""
        # This is the critical test for the bug fix
        matcher = MerchantCriteriaBuilder.build_matching_function(
            pattern=r"NETFLIX\s+\w+",
            match_type='regex',
            case_sensitive=False
        )
        
        # All these should match regardless of case
        assert matcher("Netflix ABC123") is True
        assert matcher("NETFLIX xyz789") is True
        assert matcher("netflix DEF456") is True
        assert matcher("NETFLIX") is False  # No word chars after
    
    def test_build_matching_function_regex_with_character_class(self):
        """Test regex pattern with character class [a-z] and case-insensitive matching."""
        matcher = MerchantCriteriaBuilder.build_matching_function(
            pattern=r"SPOTIFY\s+[a-z]+",
            match_type='regex',
            case_sensitive=False
        )
        
        # All these should match - lowercase letters should work regardless of case
        assert matcher("Spotify Premium") is True
        assert matcher("SPOTIFY basic") is True
        assert matcher("spotify family") is True
        assert matcher("SPOTIFY 123") is False  # Numbers don't match [a-z]
    
    def test_build_matching_function_regex_case_sensitive(self):
        """Test case-sensitive regex matching."""
        matcher = MerchantCriteriaBuilder.build_matching_function(
            pattern=r"AMAZON\s+\w+",
            match_type='regex',
            case_sensitive=True
        )
        
        assert matcher("AMAZON Prime") is True
        assert matcher("Amazon Prime") is False  # Wrong case
        assert matcher("amazon prime") is False  # Wrong case
    
    def test_build_matching_function_regex_with_exclusions(self):
        """Test regex matching with exclusions."""
        matcher = MerchantCriteriaBuilder.build_matching_function(
            pattern=r"NETFLIX.*",
            match_type='regex',
            exclusions=["REFUND"],
            case_sensitive=False
        )
        
        assert matcher("Netflix Premium") is True
        assert matcher("NETFLIX REFUND") is False
        assert matcher("netflix refund payment") is False
    
    def test_build_matching_function_regex_invalid_pattern(self):
        """Test regex matching with invalid pattern returns False."""
        matcher = MerchantCriteriaBuilder.build_matching_function(
            pattern=r"[invalid(",
            match_type='regex',
            case_sensitive=False
        )
        
        # Invalid regex should not crash, just return False
        assert matcher("anything") is False
    
    def test_to_regex_pattern_exact(self):
        """Test converting exact match to regex."""
        regex = MerchantCriteriaBuilder.to_regex_pattern(
            pattern="NETFLIX",
            match_type='exact',
            case_sensitive=False
        )
        
        assert regex.startswith("(?i)")
        assert "^" in regex
        assert "$" in regex
    
    def test_to_regex_pattern_contains(self):
        """Test converting contains match to regex."""
        regex = MerchantCriteriaBuilder.to_regex_pattern(
            pattern="NETFLIX",
            match_type='contains',
            case_sensitive=False
        )
        
        assert regex.startswith("(?i)")
        assert "NETFLIX" in regex
    
    def test_to_regex_pattern_with_exclusions(self):
        """Test converting pattern with exclusions to regex."""
        regex = MerchantCriteriaBuilder.to_regex_pattern(
            pattern="NETFLIX",
            match_type='contains',
            exclusions=["REFUND"],
            case_sensitive=False
        )
        
        assert "(?!" in regex  # Negative lookahead
        assert "REFUND" in regex


class TestAmountCriteriaBuilder:
    """Test suite for AmountCriteriaBuilder."""
    
    def test_analyze_amounts_identical(self):
        """Test analyzing identical amounts."""
        amounts = [Decimal("14.99")] * 5
        
        result = AmountCriteriaBuilder.analyze_amounts(amounts)
        
        assert result['mean'] == Decimal("14.99")
        assert result['std'] == Decimal("0")
        assert result['all_identical'] is True
        assert result['suggested_tolerance_pct'] == Decimal("5.0")
    
    def test_analyze_amounts_with_variation(self):
        """Test analyzing amounts with variation."""
        amounts = [
            Decimal("14.99"),
            Decimal("15.99"),
            Decimal("14.99"),
            Decimal("16.99")
        ]
        
        result = AmountCriteriaBuilder.analyze_amounts(amounts)
        
        assert result['mean'] > Decimal("0")
        assert result['std'] > Decimal("0")
        assert result['all_identical'] is False
        assert Decimal("5.0") <= result['suggested_tolerance_pct'] <= Decimal("25.0")
    
    def test_analyze_amounts_empty_list(self):
        """Test analyzing empty amount list."""
        result = AmountCriteriaBuilder.analyze_amounts([])
        
        assert result['mean'] == Decimal("0")
        assert result['all_identical'] is False
    
    def test_calculate_tolerance_range(self):
        """Test calculating tolerance range."""
        mean = Decimal("100.00")
        tolerance_pct = Decimal("10.0")
        
        min_amt, max_amt = AmountCriteriaBuilder.calculate_tolerance_range(
            mean, tolerance_pct
        )
        
        assert min_amt == Decimal("90.00")
        assert max_amt == Decimal("110.00")
    
    def test_test_tolerance_coverage_full(self):
        """Test tolerance coverage when all amounts are within range."""
        amounts = [
            Decimal("95.00"),
            Decimal("100.00"),
            Decimal("105.00")
        ]
        mean = Decimal("100.00")
        tolerance_pct = Decimal("10.0")
        
        result = AmountCriteriaBuilder.test_tolerance_coverage(
            amounts, mean, tolerance_pct
        )
        
        assert result['total'] == 3
        assert result['within_range'] == 3
        assert result['outside_range'] == 0
        assert result['coverage_pct'] == 100.0
    
    def test_test_tolerance_coverage_partial(self):
        """Test tolerance coverage when some amounts are outside range."""
        amounts = [
            Decimal("80.00"),   # Outside
            Decimal("95.00"),   # Within
            Decimal("100.00"),  # Within
            Decimal("120.00")   # Outside
        ]
        mean = Decimal("100.00")
        tolerance_pct = Decimal("10.0")
        
        result = AmountCriteriaBuilder.test_tolerance_coverage(
            amounts, mean, tolerance_pct
        )
        
        assert result['total'] == 4
        assert result['within_range'] == 2
        assert result['outside_range'] == 2
        assert result['coverage_pct'] == 50.0
        assert len(result['outside_amounts']) == 2


class TestTemporalCriteriaBuilder:
    """Test suite for TemporalCriteriaBuilder."""
    
    def test_analyze_dates_monthly_pattern(self):
        """Test analyzing dates with monthly pattern."""
        # Create dates on the 15th of each month
        dates = [
            int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp() * 1000),
            int(datetime(2024, 2, 15, tzinfo=timezone.utc).timestamp() * 1000),
            int(datetime(2024, 3, 15, tzinfo=timezone.utc).timestamp() * 1000),
            int(datetime(2024, 4, 15, tzinfo=timezone.utc).timestamp() * 1000),
        ]
        
        result = TemporalCriteriaBuilder.analyze_dates(dates)
        
        assert result['frequency'] == RecurrenceFrequency.MONTHLY
        assert result['temporal_pattern_type'] == TemporalPatternType.DAY_OF_MONTH
        assert result['day_of_month'] == 15
        assert result['suggested_tolerance_days'] >= 2
    
    def test_analyze_dates_weekly_pattern(self):
        """Test analyzing dates with weekly pattern."""
        # Create dates every Monday
        dates = [
            int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000),   # Monday
            int(datetime(2024, 1, 8, tzinfo=timezone.utc).timestamp() * 1000),   # Monday
            int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp() * 1000),  # Monday
            int(datetime(2024, 1, 22, tzinfo=timezone.utc).timestamp() * 1000),  # Monday
        ]
        
        result = TemporalCriteriaBuilder.analyze_dates(dates)
        
        assert result['frequency'] == RecurrenceFrequency.WEEKLY
        # Day of week pattern detection depends on consistency
        assert 'day_of_week' in result
    
    def test_analyze_dates_empty_list(self):
        """Test analyzing empty date list."""
        result = TemporalCriteriaBuilder.analyze_dates([])
        
        assert result['frequency'] == RecurrenceFrequency.IRREGULAR
        assert result['temporal_pattern_type'] == TemporalPatternType.FLEXIBLE
        assert result['day_of_month'] is None
    
    def test_detect_frequency_daily(self):
        """Test frequency detection for daily pattern."""
        from services.recurring_charges.criteria_builders import TemporalCriteriaBuilder
        
        freq = TemporalCriteriaBuilder._detect_frequency(1.0)
        assert freq == RecurrenceFrequency.DAILY
    
    def test_detect_frequency_weekly(self):
        """Test frequency detection for weekly pattern."""
        from services.recurring_charges.criteria_builders import TemporalCriteriaBuilder
        
        freq = TemporalCriteriaBuilder._detect_frequency(7.0)
        assert freq == RecurrenceFrequency.WEEKLY
    
    def test_detect_frequency_monthly(self):
        """Test frequency detection for monthly pattern."""
        from services.recurring_charges.criteria_builders import TemporalCriteriaBuilder
        
        freq = TemporalCriteriaBuilder._detect_frequency(30.0)
        assert freq == RecurrenceFrequency.MONTHLY
    
    def test_detect_frequency_quarterly(self):
        """Test frequency detection for quarterly pattern."""
        from services.recurring_charges.criteria_builders import TemporalCriteriaBuilder
        
        freq = TemporalCriteriaBuilder._detect_frequency(90.0)
        assert freq == RecurrenceFrequency.QUARTERLY
    
    def test_detect_frequency_annually(self):
        """Test frequency detection for annual pattern."""
        from services.recurring_charges.criteria_builders import TemporalCriteriaBuilder
        
        freq = TemporalCriteriaBuilder._detect_frequency(365.0)
        assert freq == RecurrenceFrequency.ANNUALLY
    
    def test_detect_frequency_irregular(self):
        """Test frequency detection for irregular pattern."""
        from services.recurring_charges.criteria_builders import TemporalCriteriaBuilder
        
        freq = TemporalCriteriaBuilder._detect_frequency(45.0)  # Between monthly and bi-monthly
        assert freq == RecurrenceFrequency.IRREGULAR

