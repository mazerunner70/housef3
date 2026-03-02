"""
Pattern Validation Service.

This service validates that pattern criteria correctly match the original cluster
of transactions that were used to create the pattern. This is the bridge between
Phase 1 (review) and Phase 2 (auto-categorization).
"""

import re
import logging
from typing import List, Set
from datetime import datetime, timezone
from decimal import Decimal

from models.transaction import Transaction
from models.recurring_charge import (
    RecurringChargePattern,
    PatternCriteriaValidation,
    TemporalPatternType
)

logger = logging.getLogger(__name__)


class PatternValidationService:
    """Validates pattern criteria against original matched transactions."""
    
    def validate_pattern_criteria(
        self,
        pattern: RecurringChargePattern,
        all_transactions: List[Transaction]
    ) -> PatternCriteriaValidation:
        """
        Validate that pattern criteria correctly match the original cluster.
        
        This ensures that the criteria (merchant pattern, amount tolerance, date rules)
        that will be used in Phase 2 auto-categorization actually match the original
        transactions that were clustered together in Phase 1.
        
        Args:
            pattern: The pattern to validate
            all_transactions: All user transactions (must include original matches)
            
        Returns:
            Validation result with detailed analysis
            
        Raises:
            ValueError: If pattern has no matched_transaction_ids
        """
        if not pattern.matched_transaction_ids:
            raise ValueError("Pattern has no matched_transaction_ids to validate against")
        
        # Get original cluster transactions
        original_tx_map = {tx.transaction_id: tx for tx in all_transactions}
        original_matches = [
            original_tx_map[tx_id] 
            for tx_id in pattern.matched_transaction_ids 
            if tx_id in original_tx_map
        ]
        
        if len(original_matches) != len(pattern.matched_transaction_ids):
            missing_count = len(pattern.matched_transaction_ids) - len(original_matches)
            logger.warning(
                f"Pattern {pattern.pattern_id}: {missing_count} original transactions not found"
            )
        
        # Apply criteria-based matching to ALL transactions
        criteria_matches = self._match_transactions_by_criteria(pattern, all_transactions)
        
        # Analyze overlap
        original_ids = set(pattern.matched_transaction_ids)
        criteria_ids = {tx.transaction_id for tx in criteria_matches}
        
        missing_from_criteria = original_ids - criteria_ids
        extra_from_criteria = criteria_ids - original_ids
        
        all_original_match = len(missing_from_criteria) == 0
        no_false_positives = len(extra_from_criteria) == 0
        perfect_match = all_original_match and no_false_positives
        
        # Generate warnings and suggestions
        warnings = []
        suggestions = []
        
        if missing_from_criteria:
            warnings.append(
                f"{len(missing_from_criteria)} original transactions don't match criteria"
            )
            suggestions.append("Consider loosening amount tolerance or date tolerance")
        
        if extra_from_criteria:
            warnings.append(
                f"{len(extra_from_criteria)} additional transactions match criteria"
            )
            suggestions.append("Consider tightening merchant pattern or amount tolerance")
        
        if perfect_match:
            suggestions.append("Criteria perfectly match original cluster - ready to activate")
        
        logger.info(
            f"Validation for pattern {pattern.pattern_id}: "
            f"original={len(original_matches)}, criteria={len(criteria_matches)}, "
            f"missing={len(missing_from_criteria)}, extra={len(extra_from_criteria)}"
        )
        
        return PatternCriteriaValidation(
            patternId=pattern.pattern_id,
            isValid=all_original_match,  # Valid if all originals match (extra is OK)
            originalCount=len(original_matches),
            criteriaMatchCount=len(criteria_matches),
            allOriginalMatchCriteria=all_original_match,
            noFalsePositives=no_false_positives,
            perfectMatch=perfect_match,
            missingFromCriteria=list(missing_from_criteria),
            extraFromCriteria=list(extra_from_criteria),
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _match_transactions_by_criteria(
        self,
        pattern: RecurringChargePattern,
        transactions: List[Transaction]
    ) -> List[Transaction]:
        """
        Match transactions using pattern criteria (Phase 2 matching logic).
        
        This is the same logic that will be used for auto-categorization.
        
        Args:
            pattern: Pattern with criteria to match against
            transactions: List of transactions to test
            
        Returns:
            List of transactions that match the pattern criteria
        """
        matches = []
        
        for tx in transactions:
            # Only consider transactions in the pattern's time range
            # (or slightly before/after for patterns that might be ongoing)
            if tx.date < pattern.first_occurrence or tx.date > pattern.last_occurrence:
                continue
            
            # Check merchant pattern
            if not self._matches_merchant_pattern(tx.description, pattern.merchant_pattern):
                continue
            
            # Check amount tolerance
            if not self._amount_within_tolerance(tx.amount, pattern):
                continue
            
            # Check temporal pattern (if applicable)
            if not self._matches_temporal_pattern(tx.date, pattern):
                continue
            
            matches.append(tx)
        
        return matches
    
    def _matches_merchant_pattern(self, description: str, pattern: str) -> bool:
        """
        Check if transaction description matches merchant pattern.
        
        The pattern can be:
        - Simple substring (e.g., "NETFLIX")
        - Regex pattern (e.g., "(?i)NETFLIX")
        
        Args:
            description: Transaction description
            pattern: Merchant pattern (string or regex)
            
        Returns:
            True if description matches pattern
        """
        try:
            # Try as regex first (if pattern contains regex syntax)
            if any(char in pattern for char in ['(', ')', '[', ']', '^', '$', '?']):
                return bool(re.search(pattern, description))
            else:
                # Simple case-insensitive substring match
                return pattern.upper() in description.upper()
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
            # Fall back to substring match
            return pattern.upper() in description.upper()
    
    def _amount_within_tolerance(
        self, 
        amount: Decimal, 
        pattern: RecurringChargePattern
    ) -> bool:
        """
        Check if amount is within pattern tolerance.
        
        Args:
            amount: Transaction amount (can be negative)
            pattern: Pattern with amount criteria
            
        Returns:
            True if amount is within tolerance
        """
        abs_amount = abs(amount)
        tolerance = pattern.amount_mean * (pattern.amount_tolerance_pct / Decimal("100"))
        min_amount = pattern.amount_mean - tolerance
        max_amount = pattern.amount_mean + tolerance
        return min_amount <= abs_amount <= max_amount
    
    def _matches_temporal_pattern(
        self, 
        tx_date: int, 
        pattern: RecurringChargePattern
    ) -> bool:
        """
        Check if transaction date matches temporal pattern.
        
        Args:
            tx_date: Transaction date (timestamp in milliseconds)
            pattern: Pattern with temporal criteria
            
        Returns:
            True if date matches temporal pattern
        """
        dt = datetime.fromtimestamp(tx_date / 1000, tz=timezone.utc)
        
        # Check day of week if specified
        if pattern.temporal_pattern_type == TemporalPatternType.DAY_OF_WEEK:
            if pattern.day_of_week is not None:
                # Allow tolerance in days (e.g., Tuesday ± 1 day)
                actual_day = dt.weekday()
                target_day = pattern.day_of_week
                day_diff = abs(actual_day - target_day)
                # Handle week wrapping (e.g., Sunday to Monday)
                day_diff = min(day_diff, 7 - day_diff)
                if day_diff > pattern.tolerance_days:
                    return False
        
        # Check day of month if specified
        elif pattern.temporal_pattern_type == TemporalPatternType.DAY_OF_MONTH:
            if pattern.day_of_month is not None:
                day_diff = abs(dt.day - pattern.day_of_month)
                if day_diff > pattern.tolerance_days:
                    return False
        
        # Check first working day
        elif pattern.temporal_pattern_type == TemporalPatternType.FIRST_WORKING_DAY:
            # Transaction should be within first few days of month on a weekday
            if dt.day > 5 or dt.weekday() >= 5:  # Not first week or is weekend
                return False
        
        # Check last working day
        elif pattern.temporal_pattern_type == TemporalPatternType.LAST_WORKING_DAY:
            # Transaction should be within last few days of month on a weekday
            # This is approximate - would need calendar logic for exact last business day
            import calendar
            last_day = calendar.monthrange(dt.year, dt.month)[1]
            days_from_end = last_day - dt.day
            if days_from_end > 5 or dt.weekday() >= 5:
                return False
        
        # FLEXIBLE and other types - no strict temporal requirements
        # All dates match
        
        return True
    
    def get_matching_transactions(
        self,
        pattern: RecurringChargePattern,
        transactions: List[Transaction]
    ) -> List[Transaction]:
        """
        Get all transactions that match a pattern's criteria.
        
        This is a public method for Phase 2 usage:
        - Retroactive categorization
        - Showing current matches in UI
        - Pattern effectiveness analysis
        
        Args:
            pattern: Pattern with criteria
            transactions: All transactions to test
            
        Returns:
            List of matching transactions
        """
        # Remove time range restriction for this public method
        # (we want to find ALL matches, not just in original time range)
        matches = []
        
        for tx in transactions:
            # Check merchant pattern
            if not self._matches_merchant_pattern(tx.description, pattern.merchant_pattern):
                continue
            
            # Check amount tolerance
            if not self._amount_within_tolerance(tx.amount, pattern):
                continue
            
            # Check temporal pattern
            if not self._matches_temporal_pattern(tx.date, pattern):
                continue
            
            matches.append(tx)
        
        return matches

