"""
Confidence score calculator for recurring charge detection.

Calculates multi-factor confidence scores with optional account-aware adjustments.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from collections import Counter

import numpy as np

from models.transaction import Transaction
from models.account import Account, AccountType
from models.recurring_charge import RecurrenceFrequency
from services.recurring_charges.config import ConfidenceWeights

logger = logging.getLogger(__name__)


class ConfidenceScoreCalculator:
    """
    Calculates multi-factor confidence scores for recurring charge patterns.
    
    Considers:
    - Interval regularity (how consistent are the intervals)
    - Amount regularity (how consistent are the amounts)
    - Sample size (more samples = higher confidence)
    - Temporal consistency (how well does it match the detected pattern)
    
    Optionally applies account-aware adjustments based on account type
    and pattern appropriateness.
    """
    
    def __init__(self, weights: Optional[ConfidenceWeights] = None):
        """
        Initialize the confidence score calculator.
        
        Args:
            weights: Optional custom weights for scoring factors.
                    If None, uses default weights (30%, 20%, 20%, 30%)
        """
        self.weights = weights or ConfidenceWeights()
    
    def calculate(
        self,
        cluster_transactions: List[Transaction],
        temporal_info: Dict[str, Any]
    ) -> float:
        """
        Calculate base confidence score (0.0-1.0).
        
        Args:
            cluster_transactions: List of transactions in the pattern
            temporal_info: Temporal pattern info with temporal_consistency
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # 1. Interval Regularity
        interval_regularity = self._calculate_interval_regularity(cluster_transactions)
        
        # 2. Amount Regularity
        amount_regularity = self._calculate_amount_regularity(cluster_transactions)
        
        # 3. Sample Size Score
        sample_size_score = self._calculate_sample_size_score(cluster_transactions)
        
        # 4. Temporal Consistency
        temporal_consistency = temporal_info.get('temporal_consistency', 0.5)
        
        # Weighted sum
        confidence = (
            self.weights.interval_regularity * interval_regularity +
            self.weights.amount_regularity * amount_regularity +
            self.weights.sample_size * sample_size_score +
            self.weights.temporal_consistency * temporal_consistency
        )
        
        return round(confidence, 2)
    
    def _calculate_interval_regularity(self, transactions: List[Transaction]) -> float:
        """
        Calculate how regular the intervals are between transactions.
        
        Uses coefficient of variation (std/mean) inverted to [0,1] range.
        Lower variation = higher score.
        
        Args:
            transactions: Sorted list of transactions
            
        Returns:
            Regularity score (0.0-1.0)
        """
        if len(transactions) < 2:
            return 0.5
        
        # Calculate intervals in days
        intervals = []
        for i in range(len(transactions) - 1):
            days = (transactions[i + 1].date - transactions[i].date) / (1000 * 60 * 60 * 24)
            intervals.append(days)
        
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        # Convert coefficient of variation to regularity score
        regularity = 1.0 / (1.0 + std_interval / (mean_interval + 1))
        
        return regularity
    
    def _calculate_amount_regularity(self, transactions: List[Transaction]) -> float:
        """
        Calculate how regular the amounts are across transactions.
        
        Uses coefficient of variation (std/mean) inverted to [0,1] range.
        Lower variation = higher score.
        
        Args:
            transactions: List of transactions
            
        Returns:
            Regularity score (0.0-1.0)
        """
        amounts = [abs(float(txn.amount)) for txn in transactions]
        mean_amount = np.mean(amounts)
        std_amount = np.std(amounts)
        
        # Convert coefficient of variation to regularity score
        regularity = 1.0 / (1.0 + std_amount / (abs(mean_amount) + 1))
        
        return regularity
    
    def _calculate_sample_size_score(self, transactions: List[Transaction]) -> float:
        """
        Calculate score based on number of samples.
        
        More samples = higher confidence, capped at 12 (1 year monthly).
        
        Args:
            transactions: List of transactions
            
        Returns:
            Sample size score (0.0-1.0)
        """
        return min(1.0, len(transactions) / 12)
    
    def apply_account_adjustments(
        self,
        base_confidence: float,
        cluster_transactions: List[Transaction],
        frequency: RecurrenceFrequency,
        merchant_pattern: str,
        accounts_map: Dict[uuid.UUID, Account]
    ) -> float:
        """
        Apply account-aware confidence score adjustments.
        
        Different account types have different expected patterns. This method
        boosts confidence for patterns that match expected account behavior
        and reduces it for unusual patterns.
        
        Args:
            base_confidence: Base confidence score (0.0-1.0)
            cluster_transactions: Transactions in the pattern
            frequency: Detected recurrence frequency
            merchant_pattern: Extracted merchant name pattern
            accounts_map: Dictionary mapping account_id to Account objects
            
        Returns:
            Adjusted confidence score (0.0-1.0)
        """
        # Get the most common account type in this cluster
        account_types = []
        for tx in cluster_transactions:
            account = accounts_map.get(tx.account_id)
            if account and account.account_type:
                account_types.append(account.account_type)
        
        if not account_types:
            return base_confidence
        
        # Use the most common account type
        account_type_counts = Counter(account_types)
        primary_account_type = account_type_counts.most_common(1)[0][0]
        
        # Categorize the pattern
        pattern_category = self._categorize_pattern(merchant_pattern, cluster_transactions)
        
        # Get adjustment for this pattern
        key = (primary_account_type, frequency, pattern_category)
        adjustment = self._get_confidence_adjustments().get(key, 0.0)
        
        # Apply adjustment
        adjusted_confidence = base_confidence + adjustment
        
        # Log significant adjustments
        if abs(adjustment) >= 0.05:
            logger.info(
                f"Account-aware confidence adjustment: {base_confidence:.3f} -> "
                f"{adjusted_confidence:.3f} ({adjustment:+.3f}) for "
                f"{primary_account_type.value} / {frequency.value} / {pattern_category}"
            )
        
        return min(1.0, max(0.0, adjusted_confidence))
    
    def _categorize_pattern(
        self, 
        merchant_pattern: str, 
        cluster_transactions: List[Transaction]
    ) -> str:
        """
        Categorize a pattern based on merchant name and transaction characteristics.
        
        Args:
            merchant_pattern: Merchant name pattern
            cluster_transactions: Transactions in the pattern
            
        Returns:
            Pattern category string
        """
        pattern_upper = merchant_pattern.upper()
        
        # Check if it's income (positive amounts)
        amounts = [float(txn.amount) for txn in cluster_transactions]
        avg_amount = np.mean(amounts)
        if avg_amount > 0:
            if any(keyword in pattern_upper for keyword in ['SALARY', 'PAYROLL', 'DEPOSIT', 'PAYMENT RECEIVED']):
                return 'income'
            return 'deposit'
        
        # Check subscription services
        subscription_keywords = [
            'NETFLIX', 'SPOTIFY', 'HULU', 'DISNEY', 'HBO', 'AMAZON PRIME',
            'APPLE', 'GOOGLE', 'MICROSOFT', 'ADOBE', 'ZOOM', 'SLACK',
            'SUBSCRIPTION', 'MEMBERSHIP', 'PREMIUM'
        ]
        if any(keyword in pattern_upper for keyword in subscription_keywords):
            return 'subscription'
        
        # Check utilities
        utility_keywords = [
            'ELECTRIC', 'GAS', 'WATER', 'UTILITY', 'POWER', 'ENERGY',
            'INTERNET', 'CABLE', 'PHONE', 'WIRELESS', 'MOBILE'
        ]
        if any(keyword in pattern_upper for keyword in utility_keywords):
            return 'utility'
        
        # Check bills
        bill_keywords = [
            'INSURANCE', 'RENT', 'MORTGAGE', 'HOA', 'ASSOCIATION',
            'BILL', 'INVOICE', 'PAYMENT'
        ]
        if any(keyword in pattern_upper for keyword in bill_keywords):
            return 'bill'
        
        # Check transfers
        transfer_keywords = ['TRANSFER', 'XFER', 'FROM', 'TO']
        if any(keyword in pattern_upper for keyword in transfer_keywords):
            return 'transfer'
        
        # Check contributions/investments
        contribution_keywords = [
            'CONTRIBUTION', '401K', 'IRA', 'RETIREMENT', 'INVEST',
            'SAVINGS', 'DEPOSIT'
        ]
        if any(keyword in pattern_upper for keyword in contribution_keywords):
            return 'contribution'
        
        # Check loan payments
        loan_keywords = [
            'LOAN', 'CREDIT', 'PAYMENT', 'FINANCING', 'AUTO LOAN',
            'STUDENT LOAN', 'PERSONAL LOAN'
        ]
        if any(keyword in pattern_upper for keyword in loan_keywords):
            return 'payment'
        
        # Check fees
        fee_keywords = ['FEE', 'CHARGE', 'SERVICE CHARGE', 'MAINTENANCE']
        if any(keyword in pattern_upper for keyword in fee_keywords):
            return 'fee'
        
        # Check interest/dividends
        interest_keywords = ['INTEREST', 'DIVIDEND', 'EARNINGS']
        if any(keyword in pattern_upper for keyword in interest_keywords):
            if avg_amount > 0:
                return 'interest'
            return 'interest_charge'
        
        # Default to generic categories
        if avg_amount > 0:
            return 'income'
        return 'expense'
    
    def _get_confidence_adjustments(self) -> Dict[tuple, float]:
        """
        Get confidence adjustments for (account_type, frequency, pattern_category).
        
        Returns:
            Dictionary mapping (AccountType, RecurrenceFrequency, str) to float adjustment
        """
        return {
            # Credit Card patterns
            (AccountType.CREDIT_CARD, RecurrenceFrequency.MONTHLY, 'subscription'): +0.10,
            (AccountType.CREDIT_CARD, RecurrenceFrequency.ANNUALLY, 'subscription'): +0.10,
            (AccountType.CREDIT_CARD, RecurrenceFrequency.MONTHLY, 'service'): +0.08,
            (AccountType.CREDIT_CARD, RecurrenceFrequency.WEEKLY, 'expense'): -0.05,
            
            # Checking Account patterns
            (AccountType.CHECKING, RecurrenceFrequency.MONTHLY, 'utility'): +0.12,
            (AccountType.CHECKING, RecurrenceFrequency.MONTHLY, 'bill'): +0.12,
            (AccountType.CHECKING, RecurrenceFrequency.BI_WEEKLY, 'income'): +0.15,
            (AccountType.CHECKING, RecurrenceFrequency.MONTHLY, 'subscription'): -0.03,
            (AccountType.CHECKING, RecurrenceFrequency.SEMI_MONTHLY, 'income'): +0.15,
            
            # Savings Account patterns (unusual to have many recurring charges)
            (AccountType.SAVINGS, RecurrenceFrequency.MONTHLY, 'transfer'): +0.10,
            (AccountType.SAVINGS, RecurrenceFrequency.MONTHLY, 'interest'): +0.12,
            (AccountType.SAVINGS, RecurrenceFrequency.WEEKLY, 'expense'): -0.15,
            (AccountType.SAVINGS, RecurrenceFrequency.DAILY, 'expense'): -0.20,
            
            # Investment Account patterns
            (AccountType.INVESTMENT, RecurrenceFrequency.MONTHLY, 'contribution'): +0.15,
            (AccountType.INVESTMENT, RecurrenceFrequency.BI_WEEKLY, 'contribution'): +0.15,
            (AccountType.INVESTMENT, RecurrenceFrequency.QUARTERLY, 'dividend'): +0.12,
            (AccountType.INVESTMENT, RecurrenceFrequency.MONTHLY, 'fee'): +0.10,
            
            # Loan Account patterns (should be very regular)
            (AccountType.LOAN, RecurrenceFrequency.MONTHLY, 'payment'): +0.20,
            (AccountType.LOAN, RecurrenceFrequency.MONTHLY, 'interest'): +0.15,
            (AccountType.LOAN, RecurrenceFrequency.IRREGULAR, 'payment'): -0.15,
        }

