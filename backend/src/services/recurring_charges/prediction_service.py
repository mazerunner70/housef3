"""
Recurring Charge Prediction Service.

This module predicts next occurrences of recurring charges based on detected patterns.
Handles all temporal pattern types and edge cases (holidays, month boundaries, etc.).
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from calendar import monthrange

import holidays

from models.recurring_charge import (
    RecurringChargePattern,
    RecurringChargePrediction,
    RecurringChargePredictionCreate,
    RecurrenceFrequency,
    TemporalPatternType
)

logger = logging.getLogger(__name__)

# Frequency to days mapping (approximate)
FREQUENCY_DAYS = {
    RecurrenceFrequency.DAILY: 1,
    RecurrenceFrequency.WEEKLY: 7,
    RecurrenceFrequency.BI_WEEKLY: 14,
    RecurrenceFrequency.SEMI_MONTHLY: 15,
    RecurrenceFrequency.MONTHLY: 30,
    RecurrenceFrequency.BI_MONTHLY: 60,
    RecurrenceFrequency.QUARTERLY: 90,
    RecurrenceFrequency.SEMI_ANNUALLY: 182,
    RecurrenceFrequency.ANNUALLY: 365,
}


class RecurringChargePredictionService:
    """
    Service for predicting next occurrences of recurring charges.
    
    Handles complex temporal patterns including:
    - Day of month (with month boundary handling)
    - Day of week
    - First/last working day
    - First/last weekday of month
    - Holiday adjustments
    """
    
    def __init__(self, country_code: str = 'US'):
        """
        Initialize the prediction service.
        
        Args:
            country_code: Country code for holiday detection (default: US)
        """
        self.country_code = country_code
        self.holidays = holidays.country_holidays(country_code)
    
    def predict_next_occurrence(
        self,
        pattern: RecurringChargePattern,
        from_date: Optional[datetime] = None
    ) -> RecurringChargePredictionCreate:
        """
        Predict the next occurrence of a recurring charge.
        
        Args:
            pattern: RecurringChargePattern object
            from_date: Date to predict from (default: now)
            
        Returns:
            RecurringChargePredictionCreate object
        """
        if from_date is None:
            from_date = datetime.now(timezone.utc)
        
        # Get last occurrence date
        last_occurrence = datetime.fromtimestamp(pattern.last_occurrence / 1000, tz=timezone.utc)
        
        # Calculate next expected date based on pattern type
        next_date = self._calculate_next_date(pattern, from_date, last_occurrence)
        
        # Calculate days until due
        days_until = (next_date - from_date).days
        
        # Calculate expected amount and range
        expected_amount = pattern.amount_mean
        tolerance_pct = pattern.amount_tolerance_pct / 100.0
        amount_range = {
            'min': pattern.amount_mean * Decimal(str(1 - tolerance_pct)),
            'max': pattern.amount_mean * Decimal(str(1 + tolerance_pct))
        }
        
        # Confidence is based on pattern confidence and time since last occurrence
        confidence = self._calculate_prediction_confidence(pattern, last_occurrence, from_date)
        
        prediction = RecurringChargePredictionCreate(
            patternId=pattern.pattern_id,
            nextExpectedDate=int(next_date.timestamp() * 1000),
            expectedAmount=expected_amount,
            confidence=confidence,
            daysUntilDue=days_until,
            amountRange=amount_range
        )
        
        return prediction
    
    def predict_multiple_occurrences(
        self,
        pattern: RecurringChargePattern,
        num_occurrences: int = 3,
        from_date: Optional[datetime] = None
    ) -> List[RecurringChargePredictionCreate]:
        """
        Predict multiple future occurrences.
        
        Args:
            pattern: RecurringChargePattern object
            num_occurrences: Number of occurrences to predict
            from_date: Date to predict from (default: now)
            
        Returns:
            List of RecurringChargePredictionCreate objects
        """
        if from_date is None:
            from_date = datetime.now(timezone.utc)
        
        predictions = []
        current_date = from_date
        
        for _ in range(num_occurrences):
            # Predict next occurrence from current date
            prediction = self.predict_next_occurrence(pattern, current_date)
            predictions.append(prediction)
            
            # Move to day after predicted date for next iteration
            next_date = datetime.fromtimestamp(prediction.next_expected_date / 1000, tz=timezone.utc)
            current_date = next_date + timedelta(days=1)
        
        return predictions
    
    def _calculate_next_date(
        self,
        pattern: RecurringChargePattern,
        from_date: datetime,
        last_occurrence: datetime
    ) -> datetime:
        """
        Calculate next expected date based on temporal pattern type.
        
        Args:
            pattern: RecurringChargePattern
            from_date: Date to predict from
            last_occurrence: Last occurrence date
            
        Returns:
            Next expected datetime
        """
        pattern_type = pattern.temporal_pattern_type
        
        # Handle patterns requiring special logic
        if type(pattern_type).__name__ == "TemporalPatternType" and pattern_type.name == "DAY_OF_MONTH":
            return self._handle_day_of_month(pattern, from_date, last_occurrence)
        
        if type(pattern_type).__name__ == "TemporalPatternType" and pattern_type.name == "DAY_OF_WEEK":
            return self._handle_day_of_week(pattern, from_date, last_occurrence)
        
        if type(pattern_type).__name__ == "TemporalPatternType" and pattern_type.name == "FIRST_DAY_OF_MONTH":
            return self._handle_first_day_of_month(pattern, from_date)
        
        if type(pattern_type).__name__ == "TemporalPatternType" and pattern_type.name == "LAST_DAY_OF_MONTH":
            return self._handle_last_day_of_month(pattern, from_date)
        
        # Simple pattern type mappings
        simple_handlers = {
            TemporalPatternType.FIRST_WORKING_DAY: lambda: self._next_first_working_day(from_date),
            TemporalPatternType.LAST_WORKING_DAY: lambda: self._next_last_working_day(from_date),
            TemporalPatternType.WEEKEND: lambda: self._next_weekend(from_date),
            TemporalPatternType.WEEKDAY: lambda: self._next_weekday(from_date),
        }
        
        handler = simple_handlers.get(pattern_type)
        if handler:
            return handler()
        
        # Default: FLEXIBLE or unknown - use frequency-based prediction
        return self._next_by_frequency(from_date, last_occurrence, pattern.frequency)
    
    def _handle_day_of_month(
        self,
        pattern: RecurringChargePattern,
        from_date: datetime,
        last_occurrence: datetime
    ) -> datetime:
        """Handle DAY_OF_MONTH pattern type."""
        if pattern.day_of_month is None:
            return self._next_by_frequency(from_date, last_occurrence, pattern.frequency)
        return self._next_day_of_month(from_date, pattern.day_of_month)
    
    def _handle_day_of_week(
        self,
        pattern: RecurringChargePattern,
        from_date: datetime,
        last_occurrence: datetime
    ) -> datetime:
        """Handle DAY_OF_WEEK pattern type."""
        if pattern.day_of_week is None:
            return self._next_by_frequency(from_date, last_occurrence, pattern.frequency)
        return self._next_day_of_week(from_date, pattern.day_of_week, pattern.frequency)
    
    def _handle_first_day_of_month(
        self,
        pattern: RecurringChargePattern,
        from_date: datetime
    ) -> datetime:
        """Handle FIRST_DAY_OF_MONTH pattern type."""
        if pattern.day_of_week is not None:
            # First occurrence of specific weekday
            return self._next_first_weekday_of_month(from_date, pattern.day_of_week)
        # First day of month
        return self._next_day_of_month(from_date, 1)
    
    def _handle_last_day_of_month(
        self,
        pattern: RecurringChargePattern,
        from_date: datetime
    ) -> datetime:
        """Handle LAST_DAY_OF_MONTH pattern type."""
        if pattern.day_of_week is not None:
            # Last occurrence of specific weekday
            return self._next_last_weekday_of_month(from_date, pattern.day_of_week)
        # Last day of month
        return self._next_last_day_of_month(from_date)
    
    def _next_day_of_month(self, from_date: datetime, day: int) -> datetime:
        """
        Find next occurrence of specific day of month.
        
        Handles edge cases like day 31 in months with fewer days.
        """
        # Try current month
        year = from_date.year
        month = from_date.month
        
        # Get days in current month
        days_in_month = monthrange(year, month)[1]
        actual_day = min(day, days_in_month)
        
        try:
            candidate = datetime(year, month, actual_day, tzinfo=timezone.utc)
            if candidate > from_date:
                return candidate
        except ValueError:
            pass
        
        # Try next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        
        days_in_month = monthrange(year, month)[1]
        actual_day = min(day, days_in_month)
        
        return datetime(year, month, actual_day, tzinfo=timezone.utc)
    
    def _next_day_of_week(
        self,
        from_date: datetime,
        day_of_week: int,
        frequency: RecurrenceFrequency
    ) -> datetime:
        """Find next occurrence of specific day of week."""
        current_day = from_date.weekday()
        days_ahead = (day_of_week - current_day) % 7
        
        if days_ahead == 0:
            # Same day of week, move to next occurrence based on frequency
            if type(frequency).__name__ == "RecurrenceFrequency" and frequency.name == "WEEKLY":
                days_ahead = 7
            elif type(frequency).__name__ == "RecurrenceFrequency" and frequency.name == "BI_WEEKLY":
                days_ahead = 14
            else:
                days_ahead = 7  # Default to weekly
        
        return from_date + timedelta(days=days_ahead)
    
    def _next_first_working_day(self, from_date: datetime) -> datetime:
        """Find next first working day of month."""
        # Try current month
        year = from_date.year
        month = from_date.month
        
        first_working = self._find_first_working_day(year, month)
        if first_working and first_working > from_date.date():
            return datetime.combine(first_working, datetime.min.time(), tzinfo=timezone.utc)
        
        # Try next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        
        first_working = self._find_first_working_day(year, month)
        if first_working:
            return datetime.combine(first_working, datetime.min.time(), tzinfo=timezone.utc)
        
        # Fallback: return first day of next month if no working day found
        return datetime(year, month, 1, tzinfo=timezone.utc)
    
    def _next_last_working_day(self, from_date: datetime) -> datetime:
        """Find next last working day of month."""
        # Try current month
        year = from_date.year
        month = from_date.month
        
        last_working = self._find_last_working_day(year, month)
        if last_working and last_working > from_date.date():
            return datetime.combine(last_working, datetime.min.time(), tzinfo=timezone.utc)
        
        # Try next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        
        last_working = self._find_last_working_day(year, month)
        if last_working:
            return datetime.combine(last_working, datetime.min.time(), tzinfo=timezone.utc)
        
        # Fallback: return last day of month if no working day found
        last_day = monthrange(year, month)[1]
        return datetime(year, month, last_day, tzinfo=timezone.utc)
    
    def _next_first_weekday_of_month(self, from_date: datetime, day_of_week: int) -> datetime:
        """Find next first occurrence of specific weekday in month."""
        # Try current month
        year = from_date.year
        month = from_date.month
        
        first_weekday = self._find_first_weekday_of_month(year, month, day_of_week)
        if first_weekday and first_weekday > from_date.date():
            return datetime.combine(first_weekday, datetime.min.time(), tzinfo=timezone.utc)
        
        # Try next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        
        first_weekday = self._find_first_weekday_of_month(year, month, day_of_week)
        if first_weekday:
            return datetime.combine(first_weekday, datetime.min.time(), tzinfo=timezone.utc)
        
        # Fallback: should never happen, but return first day of month
        return datetime(year, month, 1, tzinfo=timezone.utc)
    
    def _next_last_weekday_of_month(self, from_date: datetime, day_of_week: int) -> datetime:
        """Find next last occurrence of specific weekday in month."""
        # Try current month
        year = from_date.year
        month = from_date.month
        
        last_weekday = self._find_last_weekday_of_month(year, month, day_of_week)
        if last_weekday and last_weekday > from_date.date():
            return datetime.combine(last_weekday, datetime.min.time(), tzinfo=timezone.utc)
        
        # Try next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        
        last_weekday = self._find_last_weekday_of_month(year, month, day_of_week)
        if last_weekday:
            return datetime.combine(last_weekday, datetime.min.time(), tzinfo=timezone.utc)
        
        # Fallback: should never happen, but return last day of month
        last_day = monthrange(year, month)[1]
        return datetime(year, month, last_day, tzinfo=timezone.utc)
    
    def _next_last_day_of_month(self, from_date: datetime) -> datetime:
        """Find next last day of month."""
        year = from_date.year
        month = from_date.month
        
        # Get last day of current month
        last_day = monthrange(year, month)[1]
        candidate = datetime(year, month, last_day, tzinfo=timezone.utc)
        
        if candidate > from_date:
            return candidate
        
        # Next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        
        last_day = monthrange(year, month)[1]
        return datetime(year, month, last_day, tzinfo=timezone.utc)
    
    def _next_weekend(self, from_date: datetime) -> datetime:
        """Find next weekend day (Saturday or Sunday)."""
        current_day = from_date.weekday()
        
        if current_day < 5:  # Monday-Friday
            days_ahead = 5 - current_day  # Next Saturday
        elif current_day == 5:  # Saturday
            days_ahead = 1  # Sunday
        else:  # Sunday
            days_ahead = 6  # Next Saturday
        
        return from_date + timedelta(days=days_ahead)
    
    def _next_weekday(self, from_date: datetime) -> datetime:
        """Find next weekday (Monday-Friday)."""
        current_day = from_date.weekday()
        
        if current_day < 4:  # Monday-Thursday
            days_ahead = 1  # Next day
        elif current_day == 4:  # Friday
            days_ahead = 3  # Monday
        elif current_day == 5:  # Saturday
            days_ahead = 2  # Monday
        else:  # Sunday
            days_ahead = 1  # Monday
        
        return from_date + timedelta(days=days_ahead)
    
    def _next_by_frequency(
        self,
        from_date: datetime,
        last_occurrence: datetime,
        frequency: RecurrenceFrequency
    ) -> datetime:
        """Predict next date based on frequency from last occurrence."""
        if type(frequency).__name__ == "RecurrenceFrequency" and frequency.name == "IRREGULAR":
            # Use 30 days as default
            days = 30
        else:
            days = FREQUENCY_DAYS.get(frequency, 30)
        
        # Calculate next date from last occurrence
        next_date = last_occurrence + timedelta(days=days)
        
        # If that's in the past, add more intervals
        while next_date <= from_date:
            next_date += timedelta(days=days)
        
        return next_date
    
    def _find_first_working_day(self, year: int, month: int):
        """Find first working day of month."""
        for day in range(1, 32):
            try:
                candidate = datetime(year, month, day, tzinfo=timezone.utc)
                if candidate.weekday() < 5 and candidate.date() not in self.holidays:
                    return candidate.date()
            except ValueError:
                break
        return None
    
    def _find_last_working_day(self, year: int, month: int):
        """Find last working day of month."""
        last_day = monthrange(year, month)[1]
        
        for day in range(last_day, 0, -1):
            candidate = datetime(year, month, day, tzinfo=timezone.utc)
            if candidate.weekday() < 5 and candidate.date() not in self.holidays:
                return candidate.date()
        
        return None
    
    def _find_first_weekday_of_month(self, year: int, month: int, day_of_week: int):
        """Find first occurrence of specific weekday in month."""
        for day in range(1, 8):
            try:
                candidate = datetime(year, month, day, tzinfo=timezone.utc)
                if candidate.weekday() == day_of_week:
                    return candidate.date()
            except ValueError:
                break
        return None
    
    def _find_last_weekday_of_month(self, year: int, month: int, day_of_week: int):
        """Find last occurrence of specific weekday in month."""
        last_day = monthrange(year, month)[1]
        
        for day in range(last_day, 0, -1):
            candidate = datetime(year, month, day, tzinfo=timezone.utc)
            if candidate.weekday() == day_of_week:
                return candidate.date()
        
        return None
    
    def _calculate_prediction_confidence(
        self,
        pattern: RecurringChargePattern,
        last_occurrence: datetime,
        from_date: datetime
    ) -> float:
        """
        Calculate confidence in prediction.
        
        Confidence decreases if:
        - Pattern confidence is low
        - Long time since last occurrence
        - Few historical occurrences
        """
        base_confidence = pattern.confidence_score
        
        # Time decay factor
        days_since_last = (from_date - last_occurrence).days
        expected_interval = FREQUENCY_DAYS.get(pattern.frequency, 30)
        
        if days_since_last <= expected_interval * 1.5:
            time_factor = 1.0
        elif days_since_last <= expected_interval * 2:
            time_factor = 0.9
        elif days_since_last <= expected_interval * 3:
            time_factor = 0.8
        else:
            time_factor = 0.7
        
        # Sample size factor
        if pattern.transaction_count >= 12:
            sample_factor = 1.0
        elif pattern.transaction_count >= 6:
            sample_factor = 0.95
        else:
            sample_factor = 0.90
        
        confidence = base_confidence * time_factor * sample_factor
        
        return round(min(confidence, 1.0), 2)

