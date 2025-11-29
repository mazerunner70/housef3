"""
Criteria Builder Services for Pattern Review.

These services help users build matching criteria from example transactions during
Phase 1 review. They analyze matched transactions to suggest optimal criteria values.
"""

import re
import logging
from typing import List, Dict, Optional, Callable
from decimal import Decimal
from datetime import datetime, timezone

import numpy as np

from models.recurring_charge import RecurrenceFrequency, TemporalPatternType

logger = logging.getLogger(__name__)


class MerchantCriteriaBuilder:
    """Helps users build merchant matching criteria from example transactions."""
    
    @staticmethod
    def extract_common_pattern(descriptions: List[str]) -> Dict:
        """
        Analyze matched transaction descriptions to find common patterns.
        
        Args:
            descriptions: List of transaction descriptions from matched cluster
            
        Returns:
            Dictionary containing:
            - common_substring: Longest common substring
            - common_prefix: Common prefix across all descriptions
            - common_suffix: Common suffix across all descriptions
            - variations: Parts that differ between descriptions
            - suggested_pattern: Suggested matching pattern
            - suggested_exclusions: Suggested exclusion words
            - match_type: Suggested match type (contains/exact/prefix/suffix)
            - confidence: Confidence in the suggestion (0.0-1.0)
        """
        if not descriptions:
            return {
                'common_substring': '',
                'common_prefix': '',
                'common_suffix': '',
                'variations': [],
                'suggested_pattern': '',
                'suggested_exclusions': [],
                'match_type': 'contains',
                'confidence': 0.0
            }
        
        # Normalize all descriptions
        normalized = [d.upper().strip() for d in descriptions]
        
        # Find longest common substring
        common_substring = MerchantCriteriaBuilder._find_longest_common_substring(
            normalized
        )
        
        # Check if they all start with the same text
        common_prefix = MerchantCriteriaBuilder._find_common_prefix(normalized)
        
        # Check if they all end with the same text
        common_suffix = MerchantCriteriaBuilder._find_common_suffix(normalized)
        
        # Extract variations (parts that differ)
        variations = MerchantCriteriaBuilder._find_variations(
            normalized, common_substring
        )
        
        # Determine best match type
        match_type = 'contains'
        suggested_pattern = common_substring
        
        if len(common_prefix) >= 5:  # Meaningful prefix
            match_type = 'prefix'
            suggested_pattern = common_prefix
        elif len(common_substring) >= 3:
            match_type = 'contains'
            suggested_pattern = common_substring
        
        # Calculate confidence
        confidence = MerchantCriteriaBuilder._calculate_confidence(
            normalized, suggested_pattern
        )
        
        return {
            'common_substring': common_substring,
            'common_prefix': common_prefix,
            'common_suffix': common_suffix,
            'variations': variations,
            'suggested_pattern': suggested_pattern,
            'suggested_exclusions': [],
            'match_type': match_type,
            'confidence': float(confidence)
        }
    
    @staticmethod
    def _find_longest_common_substring(strings: List[str]) -> str:
        """Find the longest substring common to all strings."""
        if not strings:
            return ""
        
        shortest = min(strings, key=len)
        
        for length in range(len(shortest), 0, -1):
            for start in range(len(shortest) - length + 1):
                substring = shortest[start:start + length]
                if all(substring in s for s in strings):
                    return substring
        
        return ""
    
    @staticmethod
    def _find_common_prefix(strings: List[str]) -> str:
        """Find common prefix of all strings."""
        if not strings:
            return ""
        
        prefix = strings[0]
        for s in strings[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""
        return prefix
    
    @staticmethod
    def _find_common_suffix(strings: List[str]) -> str:
        """Find common suffix of all strings."""
        if not strings:
            return ""
        
        # Reverse strings, find prefix, reverse back
        reversed_strings = [s[::-1] for s in strings]
        reversed_suffix = MerchantCriteriaBuilder._find_common_prefix(reversed_strings)
        return reversed_suffix[::-1]
    
    @staticmethod
    def _find_variations(strings: List[str], common: str) -> List[str]:
        """Find unique variations after removing common part."""
        variations = set()
        for s in strings:
            # Remove common part and extract what's left
            remaining = s.replace(common, '').strip()
            if remaining:
                # Split by common separators
                parts = remaining.replace('.', ' ').replace('-', ' ').split()
                variations.update(parts)
        
        return sorted(list(variations))
    
    @staticmethod
    def _calculate_confidence(strings: List[str], pattern: str) -> float:
        """Calculate confidence that pattern is meaningful."""
        if not pattern:
            return 0.0
        
        # Higher confidence for longer patterns
        length_score = min(len(pattern) / 10, 1.0)
        
        # Higher confidence if pattern appears in same position
        positions = [s.find(pattern) for s in strings]
        position_variance = max(positions) - min(positions)
        position_score = max(0.0, 1.0 - (position_variance / 100))
        
        return (length_score + position_score) / 2
    
    @staticmethod
    def build_matching_function(
        pattern: str,
        match_type: str,
        exclusions: Optional[List[str]] = None,
        case_sensitive: bool = False
    ) -> Callable[[str], bool]:
        """
        Build a function that matches descriptions based on criteria.
        
        Args:
            pattern: The text pattern to match
            match_type: 'contains', 'exact', 'prefix', 'suffix', or 'regex'
            exclusions: Words that disqualify a match
            case_sensitive: Whether matching is case-sensitive
            
        Returns:
            Function that takes a description and returns True/False
        """
        exclusions = exclusions or []
        
        def matcher(description: str) -> bool:
            # For regex, handle case sensitivity via flags, not uppercasing
            if match_type == 'regex':
                # Check exclusions first (case-sensitive for regex unless specified)
                excl = exclusions if case_sensitive else [e.upper() for e in exclusions]
                desc_for_excl = description if case_sensitive else description.upper()
                if any(ex in desc_for_excl for ex in excl):
                    return False
                
                # Apply regex with appropriate flags
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    return bool(re.search(pattern, description, flags))
                except re.error:
                    return False
            
            # For non-regex patterns, normalize via uppercasing
            desc = description if case_sensitive else description.upper()
            pat = pattern if case_sensitive else pattern.upper()
            excl = exclusions if case_sensitive else [e.upper() for e in exclusions]
            
            # Check exclusions first
            if any(ex in desc for ex in excl):
                return False
            
            # Apply match type
            if match_type == 'exact':
                return desc == pat
            elif match_type == 'contains':
                return pat in desc
            elif match_type == 'prefix':
                return desc.startswith(pat)
            elif match_type == 'suffix':
                return desc.endswith(pat)
            
            return False
        
        return matcher
    
    @staticmethod
    def to_regex_pattern(
        pattern: str,
        match_type: str,
        exclusions: Optional[List[str]] = None,
        case_sensitive: bool = False
    ) -> str:
        """
        Convert simple pattern to regex (for storage/Phase 2 matching).
        
        This is what gets stored in the database merchantPattern field.
        
        Args:
            pattern: The text pattern to match
            match_type: 'contains', 'exact', 'prefix', 'suffix', or 'regex'
            exclusions: Words that disqualify a match
            case_sensitive: Whether matching is case-sensitive
            
        Returns:
            Regex pattern string
        """
        exclusions = exclusions or []
        
        # Escape special regex characters in pattern (unless already regex)
        if match_type != 'regex':
            escaped_pattern = re.escape(pattern)
        else:
            escaped_pattern = pattern
        
        # Build regex based on match type
        if match_type == 'exact':
            regex = f"^{escaped_pattern}$"
        elif match_type == 'contains':
            regex = escaped_pattern
        elif match_type == 'prefix':
            regex = f"^{escaped_pattern}"
        elif match_type == 'suffix':
            regex = f"{escaped_pattern}$"
        elif match_type == 'regex':
            regex = pattern  # Already a regex
        else:
            regex = escaped_pattern
        
        # Add negative lookahead for exclusions
        if exclusions:
            # Create pattern that fails if any exclusion is found
            escaped_exclusions = [re.escape(ex) for ex in exclusions]
            exclusion_pattern = '|'.join(escaped_exclusions)
            regex = f"(?!.*({exclusion_pattern})).*{regex}"
        
        # Add case-insensitive flag if needed
        if not case_sensitive:
            regex = f"(?i){regex}"
        
        return regex


class AmountCriteriaBuilder:
    """Helps users build amount matching criteria from example transactions."""
    
    @staticmethod
    def analyze_amounts(amounts: List[Decimal]) -> Dict:
        """
        Analyze matched transaction amounts to suggest criteria.
        
        Args:
            amounts: List of transaction amounts (as positive Decimal values)
            
        Returns:
            Dictionary containing:
            - mean: Average amount
            - std: Standard deviation
            - min: Minimum amount
            - max: Maximum amount
            - suggested_tolerance_pct: Suggested tolerance percentage
            - all_identical: Whether all amounts are identical
            - has_outliers: Whether there are statistical outliers
            - outlier_indices: Indices of outlier amounts
        """
        if not amounts:
            return {
                'mean': Decimal('0'),
                'std': Decimal('0'),
                'min': Decimal('0'),
                'max': Decimal('0'),
                'suggested_tolerance_pct': Decimal('10.0'),
                'all_identical': False,
                'has_outliers': False,
                'outlier_indices': []
            }
        
        amounts_array = np.array([float(a) for a in amounts])
        
        mean = Decimal(str(np.mean(amounts_array)))
        std = Decimal(str(np.std(amounts_array)))
        min_amt = min(amounts)
        max_amt = max(amounts)
        
        # Check if all identical
        all_identical = len(set(amounts)) == 1
        
        # Suggest tolerance based on variation
        if all_identical:
            suggested_tolerance = Decimal("5.0")  # Small tolerance for identical amounts
        else:
            # Calculate natural variation percentage
            if mean > 0:
                variation_pct = (std / mean * 100)
            else:
                variation_pct = Decimal("10.0")
            
            # Round up to nearest 5%
            suggested_tolerance = Decimal(str(int(float(variation_pct) + 4.99) // 5 * 5))
            suggested_tolerance = max(Decimal("5.0"), min(suggested_tolerance, Decimal("25.0")))
        
        # Detect outliers (values > 2 std from mean)
        outlier_indices = []
        if std > 0:
            for i, amt in enumerate(amounts):
                z_score = abs((float(amt) - float(mean)) / float(std))
                if z_score > 2:
                    outlier_indices.append(i)
        
        return {
            'mean': mean,
            'std': std,
            'min': min_amt,
            'max': max_amt,
            'suggested_tolerance_pct': suggested_tolerance,
            'all_identical': all_identical,
            'has_outliers': len(outlier_indices) > 0,
            'outlier_indices': outlier_indices
        }
    
    @staticmethod
    def calculate_tolerance_range(
        mean: Decimal,
        tolerance_pct: Decimal
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate min/max range from mean and tolerance percentage.
        
        Args:
            mean: Average amount
            tolerance_pct: Tolerance percentage (e.g., 10 for ±10%)
            
        Returns:
            Tuple of (min_amount, max_amount)
        """
        tolerance_amount = mean * (tolerance_pct / Decimal("100"))
        min_amount = mean - tolerance_amount
        max_amount = mean + tolerance_amount
        return min_amount, max_amount
    
    @staticmethod
    def test_tolerance_coverage(
        amounts: List[Decimal],
        mean: Decimal,
        tolerance_pct: Decimal
    ) -> Dict:
        """
        Test how many amounts fall within tolerance.
        
        Args:
            amounts: List of amounts to test
            mean: Average amount
            tolerance_pct: Tolerance percentage
            
        Returns:
            Dictionary with coverage statistics
        """
        min_amt, max_amt = AmountCriteriaBuilder.calculate_tolerance_range(
            mean, tolerance_pct
        )
        
        within_range = [amt for amt in amounts if min_amt <= amt <= max_amt]
        outside_range = [amt for amt in amounts if not (min_amt <= amt <= max_amt)]
        
        coverage_pct = (len(within_range) / len(amounts) * 100) if amounts else 0
        
        return {
            'total': len(amounts),
            'within_range': len(within_range),
            'outside_range': len(outside_range),
            'coverage_pct': coverage_pct,
            'outside_amounts': outside_range,
            'min_allowed': min_amt,
            'max_allowed': max_amt
        }


class TemporalCriteriaBuilder:
    """Helps users build temporal matching criteria from example transactions."""
    
    @staticmethod
    def analyze_dates(dates: List[int]) -> Dict:
        """
        Analyze transaction dates to detect temporal patterns.
        
        Args:
            dates: List of timestamps (milliseconds since epoch)
            
        Returns:
            Dictionary containing:
            - frequency: Detected RecurrenceFrequency
            - temporal_pattern_type: Detected TemporalPatternType
            - day_of_month: Most common day of month (if applicable)
            - day_of_week: Most common day of week (if applicable)
            - suggested_tolerance_days: Suggested tolerance in days
            - date_distribution: Detailed distribution statistics
            - interval_analysis: Interval statistics between transactions
        """
        if not dates:
            return {
                'frequency': RecurrenceFrequency.IRREGULAR,
                'temporal_pattern_type': TemporalPatternType.FLEXIBLE,
                'day_of_month': None,
                'day_of_week': None,
                'suggested_tolerance_days': 2,
                'date_distribution': {},
                'interval_analysis': {}
            }
        
        datetimes = [
            datetime.fromtimestamp(d / 1000, tz=timezone.utc) 
            for d in sorted(dates)
        ]
        
        # Analyze day of month distribution
        days_of_month = [dt.day for dt in datetimes]
        day_of_month_counts = {}
        for day in days_of_month:
            day_of_month_counts[day] = day_of_month_counts.get(day, 0) + 1
        day_of_month_mode = max(day_of_month_counts, key=day_of_month_counts.get) if day_of_month_counts else None
        day_of_month_variance = np.std(days_of_month) if len(days_of_month) > 1 else 0
        
        # Analyze day of week distribution
        days_of_week = [dt.weekday() for dt in datetimes]
        day_of_week_counts = {}
        for day in days_of_week:
            day_of_week_counts[day] = day_of_week_counts.get(day, 0) + 1
        day_of_week_mode = max(day_of_week_counts, key=day_of_week_counts.get) if day_of_week_counts else None
        day_of_week_consistency = day_of_week_counts.get(day_of_week_mode, 0) / len(days_of_week) if day_of_week_mode is not None else 0
        
        # Analyze intervals between transactions
        intervals = []
        for i in range(1, len(datetimes)):
            delta = (datetimes[i] - datetimes[i-1]).days
            intervals.append(delta)
        
        avg_interval = float(np.mean(intervals)) if intervals else 0
        interval_std = float(np.std(intervals)) if len(intervals) > 1 else 0
        
        # Determine frequency
        frequency = TemporalCriteriaBuilder._detect_frequency(avg_interval)
        
        # Determine temporal pattern type
        pattern_type = TemporalPatternType.FLEXIBLE
        suggested_day = None
        
        if day_of_month_variance < 3:  # Consistent day of month
            pattern_type = TemporalPatternType.DAY_OF_MONTH
            suggested_day = day_of_month_mode
        elif day_of_week_consistency > 0.8:  # Consistent day of week
            pattern_type = TemporalPatternType.DAY_OF_WEEK
            suggested_day = day_of_week_mode
        
        # Suggest tolerance
        if pattern_type == TemporalPatternType.DAY_OF_MONTH:
            suggested_tolerance = max(2, int(day_of_month_variance * 2))
        else:
            suggested_tolerance = max(2, int(interval_std / 7)) if interval_std > 0 else 2
        
        return {
            'frequency': frequency,
            'temporal_pattern_type': pattern_type,
            'day_of_month': day_of_month_mode if pattern_type == TemporalPatternType.DAY_OF_MONTH else None,
            'day_of_week': day_of_week_mode if pattern_type == TemporalPatternType.DAY_OF_WEEK else None,
            'suggested_tolerance_days': suggested_tolerance,
            'date_distribution': {
                'days_of_month': days_of_month,
                'days_of_week': days_of_week,
                'day_of_month_mode': day_of_month_mode,
                'day_of_week_mode': day_of_week_mode,
                'day_of_month_variance': day_of_month_variance,
                'day_of_week_consistency': day_of_week_consistency
            },
            'interval_analysis': {
                'avg_interval_days': avg_interval,
                'interval_std': interval_std,
                'intervals': intervals
            }
        }
    
    @staticmethod
    def _detect_frequency(avg_interval_days: float) -> RecurrenceFrequency:
        """
        Detect frequency from average interval between transactions.
        
        Args:
            avg_interval_days: Average days between transactions
            
        Returns:
            Detected RecurrenceFrequency
        """
        if avg_interval_days < 2:
            return RecurrenceFrequency.DAILY
        elif 5 <= avg_interval_days <= 9:
            return RecurrenceFrequency.WEEKLY
        elif 12 <= avg_interval_days <= 16:
            return RecurrenceFrequency.BI_WEEKLY
        elif 27 <= avg_interval_days <= 33:
            return RecurrenceFrequency.MONTHLY
        elif 58 <= avg_interval_days <= 65:
            return RecurrenceFrequency.BI_MONTHLY
        elif 85 <= avg_interval_days <= 95:
            return RecurrenceFrequency.QUARTERLY
        elif 175 <= avg_interval_days <= 195:
            return RecurrenceFrequency.SEMI_ANNUALLY
        elif 350 <= avg_interval_days <= 380:
            return RecurrenceFrequency.ANNUALLY
        else:
            return RecurrenceFrequency.IRREGULAR

