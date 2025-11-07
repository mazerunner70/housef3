"""
Temporal Utility Functions.

This module provides utility functions for working with dates, calendars,
and temporal patterns, particularly for recurring charge detection.
"""

from datetime import datetime, timezone
from typing import Any


def is_first_working_day(dt: datetime, holidays_calendar: Any) -> bool:
    """
    Check if date is the first working day of the month.
    
    A working day is defined as a weekday (Monday-Friday) that is not a holiday.
    
    Args:
        dt: Datetime object to check
        holidays_calendar: Holiday calendar object (from holidays library)
        
    Returns:
        True if the date is the first working day of the month, False otherwise
    """
    year = dt.year
    month = dt.month
    
    for day in range(1, 32):
        try:
            candidate = datetime(year, month, day, tzinfo=timezone.utc)
            if candidate.weekday() < 5 and candidate.date() not in holidays_calendar:
                return candidate.date() == dt.date()
        except ValueError:
            break
    
    return False


def is_last_working_day(dt: datetime, holidays_calendar: Any) -> bool:
    """
    Check if date is the last working day of the month.
    
    A working day is defined as a weekday (Monday-Friday) that is not a holiday.
    
    Args:
        dt: Datetime object to check
        holidays_calendar: Holiday calendar object (from holidays library)
        
    Returns:
        True if the date is the last working day of the month, False otherwise
    """
    year = dt.year
    month = dt.month
    
    # Get last day of month
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    
    last_day = (next_month - datetime(year, month, 1, tzinfo=timezone.utc)).days
    
    # Search backwards for first working day
    for day in range(last_day, 0, -1):
        candidate = datetime(year, month, day, tzinfo=timezone.utc)
        if candidate.weekday() < 5 and candidate.date() not in holidays_calendar:
            return candidate.date() == dt.date()
    
    return False

