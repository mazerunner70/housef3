"""
Temporal pattern analyzer for recurring charge detection.

Analyzes when charges occur to detect temporal patterns like
"last working day", "15th of month", "every Friday", etc.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from collections import Counter
from calendar import monthrange

from models.transaction import Transaction
from models.recurring_charge import TemporalPatternType
from utils.temporal_utils import is_first_working_day, is_last_working_day

logger = logging.getLogger(__name__)


class TemporalPatternAnalyzer:
    """
    Analyzes temporal patterns in recurring charges.
    
    Detects patterns in priority order:
    1. Last working day
    2. First working day
    3. Last weekday of month (e.g., last Friday)
    4. First weekday of month (e.g., first Monday)
    5. Specific day of month (e.g., 15th)
    6. Specific day of week (e.g., every Tuesday)
    7. Flexible (no clear pattern)
    """
    
    def __init__(
        self,
        holidays,
        consistency_threshold: float = 0.70,
        weekday_detection_threshold: float = 0.70,
        day_threshold: float = 0.60
    ):
        """
        Initialize the temporal pattern analyzer.
        
        Args:
            holidays: Holidays object for working day detection
            consistency_threshold: Minimum percentage for working day patterns (default: 0.70)
            weekday_detection_threshold: Minimum percentage for weekday patterns (default: 0.70)
            day_threshold: Minimum percentage for day of month/week patterns (default: 0.60)
        """
        self.holidays = holidays
        self.consistency_threshold = consistency_threshold
        self.weekday_detection_threshold = weekday_detection_threshold
        self.day_threshold = day_threshold
    
    def analyze(self, cluster_transactions: List[Transaction]) -> Dict[str, Any]:
        """
        Analyze temporal pattern in cluster transactions.
        
        Args:
            cluster_transactions: List of transactions
            
        Returns:
            Dict with pattern_type, optional day_of_week/day_of_month, and temporal_consistency
        """
        dates = [
            datetime.fromtimestamp(txn.date / 1000, tz=timezone.utc) 
            for txn in cluster_transactions
        ]
        
        # Check patterns in priority order
        
        # 1. Last working day pattern
        pattern = self._check_last_working_day(dates)
        if pattern:
            return pattern
        
        # 2. First working day pattern
        pattern = self._check_first_working_day(dates)
        if pattern:
            return pattern
        
        # 3. Weekday-of-month patterns (last/first Thursday, etc.)
        pattern = self._detect_weekday_of_month_pattern(dates)
        if pattern:
            return pattern
        
        # 4. Specific day of month pattern
        pattern = self._check_day_of_month(dates)
        if pattern:
            return pattern
        
        # 5. Specific day of week pattern
        pattern = self._check_day_of_week(dates)
        if pattern:
            return pattern
        
        # 6. No clear pattern
        return {
            'pattern_type': TemporalPatternType.FLEXIBLE,
            'temporal_consistency': 0.5
        }
    
    def _check_last_working_day(self, dates: List[datetime]) -> Optional[Dict[str, Any]]:
        """Check if transactions occur on the last working day of the month."""
        last_working_matches = sum(1 for dt in dates if is_last_working_day(dt, self.holidays))
        last_working_pct = last_working_matches / len(dates)
        
        if last_working_pct >= self.consistency_threshold:
            return {
                'pattern_type': TemporalPatternType.LAST_WORKING_DAY,
                'temporal_consistency': last_working_pct
            }
        return None
    
    def _check_first_working_day(self, dates: List[datetime]) -> Optional[Dict[str, Any]]:
        """Check if transactions occur on the first working day of the month."""
        first_working_matches = sum(1 for dt in dates if is_first_working_day(dt, self.holidays))
        first_working_pct = first_working_matches / len(dates)
        
        if first_working_pct >= self.consistency_threshold:
            return {
                'pattern_type': TemporalPatternType.FIRST_WORKING_DAY,
                'temporal_consistency': first_working_pct
            }
        return None
    
    def _check_day_of_month(self, dates: List[datetime]) -> Optional[Dict[str, Any]]:
        """Check if transactions occur on a specific day of the month."""
        days_of_month = [dt.day for dt in dates]
        day_counter = Counter(days_of_month)
        most_common_day, day_count = day_counter.most_common(1)[0]
        day_of_month_pct = day_count / len(dates)
        
        if day_of_month_pct >= self.day_threshold:
            return {
                'pattern_type': TemporalPatternType.DAY_OF_MONTH,
                'day_of_month': most_common_day,
                'temporal_consistency': day_of_month_pct
            }
        return None
    
    def _check_day_of_week(self, dates: List[datetime]) -> Optional[Dict[str, Any]]:
        """Check if transactions occur on a specific day of the week."""
        days_of_week = [dt.weekday() for dt in dates]
        weekday_counter = Counter(days_of_week)
        most_common_weekday, weekday_count = weekday_counter.most_common(1)[0]
        day_of_week_pct = weekday_count / len(dates)
        
        if day_of_week_pct >= self.day_threshold:
            return {
                'pattern_type': TemporalPatternType.DAY_OF_WEEK,
                'day_of_week': most_common_weekday,
                'temporal_consistency': day_of_week_pct
            }
        return None
    
    def _detect_weekday_of_month_pattern(self, dates: List[datetime]) -> Optional[Dict[str, Any]]:
        """
        Detect if transactions follow 'Nth weekday of month' pattern.
        
        Examples: Last Thursday, First Friday, Second Tuesday
        
        Args:
            dates: List of datetime objects
            
        Returns:
            Dict with pattern info or None
        """
        if len(dates) < 3:
            return None
        
        weekday_info = []
        for dt in dates:
            day_of_week = dt.weekday()
            day = dt.day
            days_in_month = monthrange(dt.year, dt.month)[1]
            
            # Which occurrence of this weekday? (1-5)
            occurrence = (day - 1) // 7 + 1
            
            # Is this the LAST occurrence?
            days_remaining = days_in_month - day
            is_last = days_remaining < 7
            
            # Is this the FIRST occurrence?
            is_first = occurrence == 1
            
            weekday_info.append({
                'day_of_week': day_of_week,
                'occurrence': occurrence,
                'is_last': is_last,
                'is_first': is_first
            })
        
        # Check for "last weekday of month" pattern
        last_weekday_matches = [w for w in weekday_info if w['is_last']]
        last_weekday_pct = len(last_weekday_matches) / len(weekday_info)
        
        if last_weekday_pct >= self.weekday_detection_threshold:
            weekdays = [w['day_of_week'] for w in last_weekday_matches]
            most_common_weekday = Counter(weekdays).most_common(1)[0][0]
            
            return {
                'pattern_type': TemporalPatternType.LAST_DAY_OF_MONTH,
                'day_of_week': most_common_weekday,
                'temporal_consistency': last_weekday_pct
            }
        
        # Check for "first weekday of month" pattern
        first_weekday_matches = [w for w in weekday_info if w['is_first']]
        first_weekday_pct = len(first_weekday_matches) / len(weekday_info)
        
        if first_weekday_pct >= self.weekday_detection_threshold:
            weekdays = [w['day_of_week'] for w in first_weekday_matches]
            most_common_weekday = Counter(weekdays).most_common(1)[0][0]
            
            return {
                'pattern_type': TemporalPatternType.FIRST_DAY_OF_MONTH,
                'day_of_week': most_common_weekday,
                'temporal_consistency': first_weekday_pct
            }
        
        return None

