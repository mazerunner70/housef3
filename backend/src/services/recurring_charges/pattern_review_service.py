"""
Pattern Review Service.

This service handles user review actions on detected patterns, including
confirm, reject, and edit operations. It integrates with the validation
service to ensure pattern criteria are sound before activation.
"""

import logging
from typing import List, Optional, Tuple
from datetime import datetime, timezone

from models.transaction import Transaction
from models.recurring_charge import (
    RecurringChargePattern,
    PatternStatus,
    PatternReviewAction,
    PatternCriteriaValidation
)
from services.recurring_charges.pattern_validation_service import PatternValidationService

logger = logging.getLogger(__name__)


class PatternReviewService:
    """Handles user review actions on detected patterns."""
    
    def __init__(self, validation_service: Optional[PatternValidationService] = None):
        """
        Initialize the review service.
        
        Args:
            validation_service: Optional validation service. If not provided, creates one.
        """
        self.validation_service = validation_service or PatternValidationService()
    
    def review_pattern(
        self,
        pattern: RecurringChargePattern,
        review_action: PatternReviewAction,
        all_transactions: List[Transaction]
    ) -> Tuple[RecurringChargePattern, Optional[PatternCriteriaValidation]]:
        """
        Process user review of a pattern.
        
        Args:
            pattern: The pattern being reviewed
            review_action: User's review action
            all_transactions: All user transactions (for validation)
            
        Returns:
            Tuple of (updated pattern, validation result if applicable)
            
        Raises:
            ValueError: If pattern status doesn't allow review or action is invalid
        """
        if pattern.status not in [PatternStatus.DETECTED, PatternStatus.CONFIRMED]:
            raise ValueError(
                f"Pattern status {pattern.status.value} cannot be reviewed. "
                f"Only DETECTED or CONFIRMED patterns can be reviewed."
            )
        
        # Record review metadata
        pattern.reviewed_by = review_action.user_id
        pattern.reviewed_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        validation_result = None
        
        if review_action.action == "reject":
            pattern = self._reject_pattern(pattern, review_action)
        
        elif review_action.action == "edit":
            pattern, validation_result = self._edit_pattern(
                pattern, review_action, all_transactions
            )
        
        elif review_action.action == "confirm":
            pattern, validation_result = self._confirm_pattern(
                pattern, review_action, all_transactions
            )
        
        else:
            raise ValueError(f"Invalid review action: {review_action.action}")
        
        pattern.updated_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        return pattern, validation_result
    
    def _reject_pattern(
        self,
        pattern: RecurringChargePattern,
        review_action: PatternReviewAction
    ) -> RecurringChargePattern:
        """
        Reject a pattern.
        
        Args:
            pattern: Pattern to reject
            review_action: Review action with optional notes
            
        Returns:
            Updated pattern
        """
        pattern.status = PatternStatus.REJECTED
        pattern.active = False
        
        logger.info(
            f"Pattern {pattern.pattern_id} rejected by user {review_action.user_id}"
            + (f": {review_action.notes}" if review_action.notes else "")
        )
        
        return pattern
    
    def _edit_pattern(
        self,
        pattern: RecurringChargePattern,
        review_action: PatternReviewAction,
        all_transactions: List[Transaction]
    ) -> Tuple[RecurringChargePattern, PatternCriteriaValidation]:
        """
        Edit pattern criteria and re-validate.
        
        Args:
            pattern: Pattern to edit
            review_action: Review action with edited fields
            all_transactions: All transactions for validation
            
        Returns:
            Tuple of (updated pattern, validation result)
        """
        # Apply user edits
        if review_action.edited_merchant_pattern is not None:
            pattern.merchant_pattern = review_action.edited_merchant_pattern
            logger.info(
                f"Pattern {pattern.pattern_id}: merchant pattern updated to "
                f"'{review_action.edited_merchant_pattern}'"
            )
        
        if review_action.edited_amount_tolerance_pct is not None:
            pattern.amount_tolerance_pct = review_action.edited_amount_tolerance_pct
            logger.info(
                f"Pattern {pattern.pattern_id}: amount tolerance updated to "
                f"{review_action.edited_amount_tolerance_pct}%"
            )
        
        if review_action.edited_tolerance_days is not None:
            pattern.tolerance_days = review_action.edited_tolerance_days
            logger.info(
                f"Pattern {pattern.pattern_id}: date tolerance updated to "
                f"±{review_action.edited_tolerance_days} days"
            )
        
        if review_action.edited_suggested_category_id is not None:
            pattern.suggested_category_id = review_action.edited_suggested_category_id
            logger.info(
                f"Pattern {pattern.pattern_id}: category updated to "
                f"{review_action.edited_suggested_category_id}"
            )
        
        # Re-validate with new criteria
        validation_result = self.validation_service.validate_pattern_criteria(
            pattern, all_transactions
        )
        
        pattern.criteria_validated = validation_result.is_valid
        pattern.criteria_validation_errors = validation_result.warnings
        
        # Update status based on validation
        # Always move to CONFIRMED after edit (user review), but validation state
        # determines whether pattern can be activated
        pattern.status = PatternStatus.CONFIRMED
        
        if validation_result.is_valid:
            if review_action.activate_immediately:
                pattern.status = PatternStatus.ACTIVE
                pattern.active = True
                logger.info(
                    f"Pattern {pattern.pattern_id} edited, validated, and activated"
                )
            else:
                logger.info(
                    f"Pattern {pattern.pattern_id} edited and validated successfully"
                )
        else:
            logger.warning(
                f"Pattern {pattern.pattern_id} edited and confirmed but validation failed: "
                f"{validation_result.warnings}. Pattern cannot be activated until "
                f"criteria are corrected."
            )
        
        return pattern, validation_result
    
    def _confirm_pattern(
        self,
        pattern: RecurringChargePattern,
        review_action: PatternReviewAction,
        all_transactions: List[Transaction]
    ) -> Tuple[RecurringChargePattern, PatternCriteriaValidation]:
        """
        Confirm pattern and validate criteria.
        
        Args:
            pattern: Pattern to confirm
            review_action: Review action
            all_transactions: All transactions for validation
            
        Returns:
            Tuple of (updated pattern, validation result)
        """
        # Validate criteria match original cluster
        validation_result = self.validation_service.validate_pattern_criteria(
            pattern, all_transactions
        )
        
        pattern.criteria_validated = validation_result.is_valid
        pattern.criteria_validation_errors = validation_result.warnings
        
        # Update status
        pattern.status = PatternStatus.CONFIRMED
        
        if review_action.activate_immediately and validation_result.is_valid:
            pattern.status = PatternStatus.ACTIVE
            pattern.active = True
            logger.info(
                f"Pattern {pattern.pattern_id} confirmed and activated "
                f"(valid={validation_result.is_valid})"
            )
        else:
            logger.info(
                f"Pattern {pattern.pattern_id} confirmed "
                f"(valid={validation_result.is_valid}, active={pattern.active})"
            )
            
            if not validation_result.is_valid:
                logger.warning(
                    f"Pattern {pattern.pattern_id} confirmed but validation shows issues: "
                    f"{validation_result.warnings}"
                )
        
        return pattern, validation_result
    
    def activate_pattern(self, pattern: RecurringChargePattern) -> RecurringChargePattern:
        """
        Activate a confirmed pattern for auto-categorization.
        
        Args:
            pattern: Pattern to activate
            
        Returns:
            Updated pattern
            
        Raises:
            ValueError: If pattern is not in CONFIRMED status or not validated
        """
        if pattern.status != PatternStatus.CONFIRMED:
            raise ValueError(
                f"Only CONFIRMED patterns can be activated (current: {pattern.status.value})"
            )
        
        if not pattern.criteria_validated:
            raise ValueError(
                "Pattern criteria must be validated before activation. "
                "Run review with 'confirm' action first."
            )
        
        pattern.status = PatternStatus.ACTIVE
        pattern.active = True
        pattern.updated_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        logger.info(f"Pattern {pattern.pattern_id} activated for auto-categorization")
        
        return pattern
    
    def pause_pattern(self, pattern: RecurringChargePattern) -> RecurringChargePattern:
        """
        Temporarily pause an active pattern.
        
        Args:
            pattern: Pattern to pause
            
        Returns:
            Updated pattern
            
        Raises:
            ValueError: If pattern is not in ACTIVE status
        """
        if pattern.status != PatternStatus.ACTIVE:
            raise ValueError(
                f"Only ACTIVE patterns can be paused (current: {pattern.status.value})"
            )
        
        pattern.status = PatternStatus.PAUSED
        pattern.active = False
        pattern.updated_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        logger.info(f"Pattern {pattern.pattern_id} paused")
        
        return pattern
    
    def resume_pattern(self, pattern: RecurringChargePattern) -> RecurringChargePattern:
        """
        Resume a paused pattern.
        
        Args:
            pattern: Pattern to resume
            
        Returns:
            Updated pattern
            
        Raises:
            ValueError: If pattern is not in PAUSED status
        """
        if pattern.status != PatternStatus.PAUSED:
            raise ValueError(
                f"Only PAUSED patterns can be resumed (current: {pattern.status.value})"
            )
        
        pattern.status = PatternStatus.ACTIVE
        pattern.active = True
        pattern.updated_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        logger.info(f"Pattern {pattern.pattern_id} resumed")
        
        return pattern

