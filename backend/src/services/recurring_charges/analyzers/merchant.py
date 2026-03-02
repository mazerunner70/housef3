"""
Merchant pattern analyzer for recurring charge detection.

Extracts common merchant patterns from transaction descriptions.
"""

import logging
from typing import List

from models.transaction import Transaction

logger = logging.getLogger(__name__)


class MerchantPatternAnalyzer:
    """
    Extracts common merchant patterns from transaction descriptions.
    
    Finds the longest common substring or prefix that appears in
    most transaction descriptions to identify the merchant.
    """
    
    def __init__(self, min_pattern_length: int = 3, max_pattern_length: int = 50):
        """
        Initialize the merchant pattern analyzer.
        
        Args:
            min_pattern_length: Minimum length for extracted pattern (default: 3)
            max_pattern_length: Maximum length for extracted pattern (default: 50)
        """
        self.min_pattern_length = min_pattern_length
        self.max_pattern_length = max_pattern_length
    
    def extract_pattern(self, cluster_transactions: List[Transaction]) -> str:
        """
        Extract common merchant pattern from transaction descriptions.
        
        Args:
            cluster_transactions: List of transactions
            
        Returns:
            Merchant pattern string
        """
        descriptions = [txn.description.upper() for txn in cluster_transactions]
        
        if not descriptions:
            return "UNKNOWN"
        
        # Start with first description
        common = descriptions[0]
        
        # Find longest common substring
        for desc in descriptions[1:]:
            new_common = self._longest_common_substring(common, desc)
            if new_common:
                common = new_common
            else:
                # Fall back to first word if no common substring
                words = descriptions[0].split()
                common = words[0] if words else "UNKNOWN"
                break
        
        # Clean up the pattern
        common = common.strip()
        
        # If too short, use first word from first description
        if len(common) < self.min_pattern_length:
            words = descriptions[0].split()
            common = words[0] if words else "UNKNOWN"
        
        # Limit length
        return common[:self.max_pattern_length]
    
    def _longest_common_substring(self, s1: str, s2: str) -> str:
        """
        Find longest common substring between two strings using dynamic programming.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Longest common substring
        """
        m = len(s1)
        n = len(s2)
        
        # Create DP table
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        max_len = 0
        end_pos = 0
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                    if dp[i][j] > max_len:
                        max_len = dp[i][j]
                        end_pos = i
        
        return s1[end_pos - max_len:end_pos] if max_len > 0 else ""
    
    def get_pattern_coverage(
        self, 
        cluster_transactions: List[Transaction], 
        pattern: str
    ) -> float:
        """
        Calculate what percentage of transactions contain the pattern.
        
        Args:
            cluster_transactions: List of transactions
            pattern: Merchant pattern to check
            
        Returns:
            Percentage of transactions containing the pattern (0.0-1.0)
        """
        if not cluster_transactions or not pattern:
            return 0.0
        
        pattern_upper = pattern.upper()
        matches = sum(
            1 for txn in cluster_transactions 
            if pattern_upper in txn.description.upper()
        )
        
        return matches / len(cluster_transactions)

