"""
Unit tests for RecurringChargePredictionService.

Tests next occurrence prediction for all temporal pattern types.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid

from services.recurring_charges.prediction_service import (
    RecurringChargePredictionService,
    FREQUENCY_DAYS
)
from models.recurring_charge import (
    RecurringChargePattern,
    RecurrenceFrequency,
    TemporalPatternType
)


class TestRecurringChargePredictionService:
    """Test suite for RecurringChargePredictionService."""
    
    @pytest.fixture
    def prediction_service(self):
        """Create prediction service instance."""
        return RecurringChargePredictionService(country_code='US')
    
    @pytest.fixture
    def monthly_pattern_day_15(self):
        """Create a monthly pattern on day 15."""
        return RecurringChargePattern(
            userId="user123",
            merchantPattern="NETFLIX",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            dayOfMonth=15,
            amountMean=Decimal("14.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("14.99"),
            amountMax=Decimal("14.99"),
            confidenceScore=0.95,
            transactionCount=12,
            firstOccurrence=int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp() * 1000),
            lastOccurrence=int(datetime(2024, 12, 15, tzinfo=timezone.utc).timestamp() * 1000)
        )
    
    def test_predict_next_occurrence_day_of_month(self, prediction_service, monthly_pattern_day_15):
        """Test prediction for day of month pattern."""
        from_date = datetime(2024, 12, 20, tzinfo=timezone.utc)
        
        prediction = prediction_service.predict_next_occurrence(monthly_pattern_day_15, from_date)
        
        # Should predict January 15, 2025
        expected_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        predicted_date = datetime.fromtimestamp(prediction.next_expected_date / 1000, tz=timezone.utc)
        
        assert predicted_date.year == expected_date.year
        assert predicted_date.month == expected_date.month
        assert predicted_date.day == expected_date.day
        
        # Check amount
        assert prediction.expected_amount == Decimal("14.99")
        
        # Check days until
        assert prediction.days_until_due == (expected_date - from_date).days
    
    def test_predict_next_occurrence_day_of_month_edge_case(self, prediction_service):
        """Test prediction for day 31 in months with fewer days."""
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="RENT",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            dayOfMonth=31,
            amountMean=Decimal("1500.00"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("1500.00"),
            amountMax=Decimal("1500.00"),
            confidenceScore=0.90,
            transactionCount=12,
            firstOccurrence=int(datetime(2024, 1, 31, tzinfo=timezone.utc).timestamp() * 1000),
            lastOccurrence=int(datetime(2024, 10, 31, tzinfo=timezone.utc).timestamp() * 1000)
        )
        
        # Predict from November (30 days)
        from_date = datetime(2024, 11, 1, tzinfo=timezone.utc)
        prediction = prediction_service.predict_next_occurrence(pattern, from_date)
        
        # Should predict November 30 (last day of November)
        predicted_date = datetime.fromtimestamp(prediction.next_expected_date / 1000, tz=timezone.utc)
        assert predicted_date.day == 30
        assert predicted_date.month == 11
    
    def test_predict_next_occurrence_day_of_week(self, prediction_service):
        """Test prediction for day of week pattern."""
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="GYM",
            frequency=RecurrenceFrequency.WEEKLY,
            temporalPatternType=TemporalPatternType.DAY_OF_WEEK,
            dayOfWeek=0,  # Monday
            amountMean=Decimal("45.00"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("45.00"),
            amountMax=Decimal("45.00"),
            confidenceScore=0.92,
            transactionCount=12,
            firstOccurrence=int(datetime(2024, 1, 8, tzinfo=timezone.utc).timestamp() * 1000),
            lastOccurrence=int(datetime(2024, 12, 16, tzinfo=timezone.utc).timestamp() * 1000)
        )
        
        # Predict from Wednesday
        from_date = datetime(2024, 12, 18, tzinfo=timezone.utc)  # Wednesday
        prediction = prediction_service.predict_next_occurrence(pattern, from_date)
        
        # Should predict next Monday (December 23)
        predicted_date = datetime.fromtimestamp(prediction.next_expected_date / 1000, tz=timezone.utc)
        assert predicted_date.weekday() == 0  # Monday
        assert predicted_date.day == 23
    
    def test_predict_next_occurrence_first_working_day(self, prediction_service):
        """Test prediction for first working day pattern."""
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="BILL",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.FIRST_WORKING_DAY,
            amountMean=Decimal("100.00"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("100.00"),
            amountMax=Decimal("100.00"),
            confidenceScore=0.88,
            transactionCount=6,
            firstOccurrence=int(datetime(2024, 7, 1, tzinfo=timezone.utc).timestamp() * 1000),
            lastOccurrence=int(datetime(2024, 12, 2, tzinfo=timezone.utc).timestamp() * 1000)
        )
        
        from_date = datetime(2024, 12, 20, tzinfo=timezone.utc)
        prediction = prediction_service.predict_next_occurrence(pattern, from_date)
        
        # Should predict first working day of January 2025
        predicted_date = datetime.fromtimestamp(prediction.next_expected_date / 1000, tz=timezone.utc)
        assert predicted_date.year == 2025
        assert predicted_date.month == 1
        assert predicted_date.weekday() < 5  # Weekday
    
    def test_predict_next_occurrence_last_working_day(self, prediction_service):
        """Test prediction for last working day pattern."""
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="SALARY",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.LAST_WORKING_DAY,
            amountMean=Decimal("3500.00"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("3500.00"),
            amountMax=Decimal("3500.00"),
            confidenceScore=0.98,
            transactionCount=12,
            firstOccurrence=int(datetime(2024, 1, 31, tzinfo=timezone.utc).timestamp() * 1000),
            lastOccurrence=int(datetime(2024, 12, 31, tzinfo=timezone.utc).timestamp() * 1000)
        )
        
        from_date = datetime(2024, 12, 15, tzinfo=timezone.utc)
        prediction = prediction_service.predict_next_occurrence(pattern, from_date)
        
        # Should predict last working day of December 2024
        predicted_date = datetime.fromtimestamp(prediction.next_expected_date / 1000, tz=timezone.utc)
        assert predicted_date.month == 12
        assert predicted_date.weekday() < 5  # Weekday
    
    def test_predict_next_occurrence_first_weekday_of_month(self, prediction_service):
        """Test prediction for first weekday of month pattern."""
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="MEETING FEE",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.FIRST_DAY_OF_MONTH,
            dayOfWeek=0,  # First Monday
            amountMean=Decimal("25.00"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("25.00"),
            amountMax=Decimal("25.00"),
            confidenceScore=0.85,
            transactionCount=6,
            firstOccurrence=int(datetime(2024, 7, 1, tzinfo=timezone.utc).timestamp() * 1000),
            lastOccurrence=int(datetime(2024, 12, 2, tzinfo=timezone.utc).timestamp() * 1000)
        )
        
        from_date = datetime(2024, 12, 20, tzinfo=timezone.utc)
        prediction = prediction_service.predict_next_occurrence(pattern, from_date)
        
        # Should predict first Monday of January 2025
        predicted_date = datetime.fromtimestamp(prediction.next_expected_date / 1000, tz=timezone.utc)
        assert predicted_date.year == 2025
        assert predicted_date.month == 1
        assert predicted_date.weekday() == 0  # Monday
        assert predicted_date.day <= 7  # First week
    
    def test_predict_next_occurrence_last_weekday_of_month(self, prediction_service):
        """Test prediction for last weekday of month pattern."""
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="PAYROLL",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.LAST_DAY_OF_MONTH,
            dayOfWeek=4,  # Last Friday
            amountMean=Decimal("3200.00"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("3200.00"),
            amountMax=Decimal("3200.00"),
            confidenceScore=0.94,
            transactionCount=12,
            firstOccurrence=int(datetime(2024, 1, 26, tzinfo=timezone.utc).timestamp() * 1000),
            lastOccurrence=int(datetime(2024, 12, 27, tzinfo=timezone.utc).timestamp() * 1000)
        )
        
        from_date = datetime(2024, 12, 15, tzinfo=timezone.utc)
        prediction = prediction_service.predict_next_occurrence(pattern, from_date)
        
        # Should predict last Friday of December 2024
        predicted_date = datetime.fromtimestamp(prediction.next_expected_date / 1000, tz=timezone.utc)
        assert predicted_date.month == 12
        assert predicted_date.weekday() == 4  # Friday
        assert predicted_date.day >= 24  # Last week
    
    def test_predict_multiple_occurrences(self, prediction_service, monthly_pattern_day_15):
        """Test predicting multiple future occurrences."""
        from_date = datetime(2024, 12, 20, tzinfo=timezone.utc)
        
        predictions = prediction_service.predict_multiple_occurrences(
            monthly_pattern_day_15,
            num_occurrences=3,
            from_date=from_date
        )
        
        assert len(predictions) == 3
        
        # Should predict Jan 15, Feb 15, Mar 15 (2025)
        dates = [datetime.fromtimestamp(p.next_expected_date / 1000, tz=timezone.utc) for p in predictions]
        
        assert dates[0].month == 1 and dates[0].day == 15
        assert dates[1].month == 2 and dates[1].day == 15
        assert dates[2].month == 3 and dates[2].day == 15
    
    def test_predict_confidence_decay(self, prediction_service):
        """Test that confidence decreases with time since last occurrence."""
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="TEST",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            dayOfMonth=15,
            amountMean=Decimal("50.00"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("50.00"),
            amountMax=Decimal("50.00"),
            confidenceScore=0.90,
            transactionCount=12,
            firstOccurrence=int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp() * 1000),
            lastOccurrence=int(datetime(2024, 6, 15, tzinfo=timezone.utc).timestamp() * 1000)
        )
        
        # Predict shortly after last occurrence
        from_date_recent = datetime(2024, 6, 20, tzinfo=timezone.utc)
        prediction_recent = prediction_service.predict_next_occurrence(pattern, from_date_recent)
        
        # Predict long after last occurrence
        from_date_old = datetime(2024, 12, 20, tzinfo=timezone.utc)
        prediction_old = prediction_service.predict_next_occurrence(pattern, from_date_old)
        
        # Confidence should be lower for older prediction
        assert prediction_old.confidence < prediction_recent.confidence
    
    def test_predict_amount_range(self, prediction_service):
        """Test amount range calculation with tolerance."""
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="GYM",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            dayOfMonth=1,
            amountMean=Decimal("50.00"),
            amountStd=Decimal("5.00"),
            amountMin=Decimal("45.00"),
            amountMax=Decimal("55.00"),
            amountTolerancePct=10.0,  # 10% tolerance
            confidenceScore=0.85,
            transactionCount=6,
            firstOccurrence=int(datetime(2024, 7, 1, tzinfo=timezone.utc).timestamp() * 1000),
            lastOccurrence=int(datetime(2024, 12, 1, tzinfo=timezone.utc).timestamp() * 1000)
        )
        
        from_date = datetime(2024, 12, 15, tzinfo=timezone.utc)
        prediction = prediction_service.predict_next_occurrence(pattern, from_date)
        
        # Check amount range
        assert prediction.amount_range['min'] == Decimal("50.00") * Decimal("0.9")
        assert prediction.amount_range['max'] == Decimal("50.00") * Decimal("1.1")
    
    def test_next_day_of_month_handles_february(self, prediction_service):
        """Test that day 31 prediction handles February correctly."""
        # February 2024 (leap year, 29 days)
        from_date = datetime(2024, 2, 1, tzinfo=timezone.utc)
        next_date = prediction_service._next_day_of_month(from_date, 31)
        
        # Should predict February 29 (last day of Feb in leap year)
        assert next_date.month == 2
        assert next_date.day == 29
    
    def test_next_weekend(self, prediction_service):
        """Test next weekend prediction."""
        # From Monday
        from_date = datetime(2024, 12, 16, tzinfo=timezone.utc)  # Monday
        next_date = prediction_service._next_weekend(from_date)
        
        # Should be Saturday
        assert next_date.weekday() == 5
    
    def test_next_weekday(self, prediction_service):
        """Test next weekday prediction."""
        # From Saturday
        from_date = datetime(2024, 12, 14, tzinfo=timezone.utc)  # Saturday
        next_date = prediction_service._next_weekday(from_date)
        
        # Should be Monday
        assert next_date.weekday() == 0
        assert next_date.day == 16
    
    def test_frequency_based_prediction(self, prediction_service):
        """Test prediction based on frequency when pattern is flexible."""
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="VARIABLE",
            frequency=RecurrenceFrequency.QUARTERLY,
            temporalPatternType=TemporalPatternType.FLEXIBLE,
            amountMean=Decimal("200.00"),
            amountStd=Decimal("10.00"),
            amountMin=Decimal("190.00"),
            amountMax=Decimal("210.00"),
            confidenceScore=0.70,
            transactionCount=4,
            firstOccurrence=int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp() * 1000),
            lastOccurrence=int(datetime(2024, 10, 15, tzinfo=timezone.utc).timestamp() * 1000)
        )
        
        from_date = datetime(2024, 11, 1, tzinfo=timezone.utc)
        prediction = prediction_service.predict_next_occurrence(pattern, from_date)
        
        # Should predict approximately 90 days after last occurrence
        predicted_date = datetime.fromtimestamp(prediction.next_expected_date / 1000, tz=timezone.utc)
        last_occurrence_date = datetime(2024, 10, 15, tzinfo=timezone.utc)
        
        days_diff = (predicted_date - last_occurrence_date).days
        assert 85 <= days_diff <= 95  # Approximately quarterly

