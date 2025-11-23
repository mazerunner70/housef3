"""
Account feature extractor.

Extracts 24 account-aware features that provide context about where transactions occur.
"""

import uuid
from typing import List, Dict
from collections import Counter

import numpy as np

from models.transaction import Transaction
from models.account import Account, AccountType
from services.recurring_charges.features.base import BaseFeatureExtractor


class AccountFeatureExtractor(BaseFeatureExtractor):
    """
    Extracts 24 account-aware features from transactions.
    
    Features capture account context that helps distinguish patterns:
    - Account type (6): One-hot encoding of account type
    - Account name keywords (8): Boolean flags for semantic keywords
    - Institution (5): One-hot encoding of top 4 institutions + other
    - Account activity (5): Normalized activity metrics
    """
    
    FEATURE_SIZE = 24
    
    # Account type one-hot encoding order
    ACCOUNT_TYPE_ORDER = [
        AccountType.CHECKING,
        AccountType.SAVINGS,
        AccountType.CREDIT_CARD,
        AccountType.INVESTMENT,
        AccountType.LOAN,
        AccountType.OTHER
    ]
    
    # Keywords to search for in account names
    ACCOUNT_NAME_KEYWORDS = {
        'business': 0,
        'personal': 1,
        'checking': 2,
        'savings': 3,
        'credit': 4,
        'joint': 5,
        'emergency': 6,
        'investment': 7
    }
    
    @property
    def feature_size(self) -> int:
        """Return the number of account features (24)."""
        return self.FEATURE_SIZE
    
    def extract_batch(
        self, 
        transactions: List[Transaction],
        accounts_map: Dict[uuid.UUID, Account],
        **kwargs
    ) -> np.ndarray:
        """
        Extract account features for a batch of transactions.
        
        Args:
            transactions: List of Transaction objects
            accounts_map: Dictionary mapping account_id to Account objects
            **kwargs: Additional arguments (unused)
            
        Returns:
            Array of shape (n_transactions, 24) with account features
        """
        # Extract each feature type
        account_type_features = self._extract_account_type_features(
            transactions, accounts_map
        )
        account_name_features = self._extract_account_name_features(
            transactions, accounts_map
        )
        institution_features = self._extract_institution_features(
            transactions, accounts_map
        )
        activity_features = self._extract_account_activity_features(
            transactions, accounts_map
        )
        
        # Combine all account features: 6 + 8 + 5 + 5 = 24
        features = np.hstack([
            account_type_features,   # 6
            account_name_features,   # 8
            institution_features,    # 5
            activity_features        # 5
        ])
        
        self.validate_output(features, len(transactions))
        return features
    
    def _extract_account_type_features(
        self,
        transactions: List[Transaction],
        accounts_map: Dict[uuid.UUID, Account]
    ) -> np.ndarray:
        """
        Extract one-hot encoded account type features (6 dimensions).
        
        Different account types have different recurring charge patterns:
        - CREDIT_CARD: Subscriptions, online services
        - CHECKING: Bills, direct debits, salary deposits
        - SAVINGS: Transfers, interest deposits
        - INVESTMENT: Regular contributions, dividends
        - LOAN: Monthly payments
        - OTHER: Miscellaneous
        """
        features = []
        
        for tx in transactions:
            one_hot = [0.0] * 6
            
            account = accounts_map.get(tx.account_id)
            if account and account.account_type:
                try:
                    idx = self.ACCOUNT_TYPE_ORDER.index(account.account_type)
                    one_hot[idx] = 1.0
                except (ValueError, AttributeError):
                    one_hot[5] = 1.0  # OTHER
            else:
                one_hot[5] = 1.0  # No account = OTHER
            
            features.append(one_hot)
        
        return np.array(features)
    
    def _extract_account_name_features(
        self,
        transactions: List[Transaction],
        accounts_map: Dict[uuid.UUID, Account]
    ) -> np.ndarray:
        """
        Extract keyword-based features from account names (8 dimensions).
        
        Account names contain semantic information:
        - "Business Checking" vs "Personal Checking"
        - "Emergency Savings" vs "Vacation Fund"
        """
        features = []
        
        for tx in transactions:
            flags = [0.0] * 8
            
            account = accounts_map.get(tx.account_id)
            if account and account.account_name:
                name_lower = account.account_name.lower()
                for keyword, idx in self.ACCOUNT_NAME_KEYWORDS.items():
                    if keyword in name_lower:
                        flags[idx] = 1.0
            
            features.append(flags)
        
        return np.array(features)
    
    def _extract_institution_features(
        self,
        transactions: List[Transaction],
        accounts_map: Dict[uuid.UUID, Account]
    ) -> np.ndarray:
        """
        Extract one-hot encoded institution features (5 dimensions).
        
        Encodes top 4 most common institutions in batch plus "other".
        """
        # First pass: count institutions
        institution_counts = Counter()
        for tx in transactions:
            account = accounts_map.get(tx.account_id)
            if account and account.institution:
                institution_counts[account.institution.lower()] += 1
        
        # Get top 4 institutions
        top_institutions = [inst for inst, _ in institution_counts.most_common(4)]
        
        # Second pass: encode features
        features = []
        for tx in transactions:
            one_hot = [0.0] * 5
            
            account = accounts_map.get(tx.account_id)
            if account and account.institution:
                inst_lower = account.institution.lower()
                if inst_lower in top_institutions:
                    idx = top_institutions.index(inst_lower)
                    one_hot[idx] = 1.0
                else:
                    one_hot[4] = 1.0  # Other
            else:
                one_hot[4] = 1.0  # No institution = other
            
            features.append(one_hot)
        
        return np.array(features)
    
    def _extract_account_activity_features(
        self,
        transactions: List[Transaction],
        accounts_map: Dict[uuid.UUID, Account]
    ) -> np.ndarray:
        """
        Extract account-level activity metrics (5 dimensions).
        
        Features:
        - Transaction count (normalized)
        - Amount relative to account average
        - Account age (normalized)
        - Transaction frequency
        - Active status flag
        """
        # First pass: group transactions by account
        account_txs = {}
        for tx in transactions:
            if tx.account_id not in account_txs:
                account_txs[tx.account_id] = []
            account_txs[tx.account_id].append(tx)
        
        # Calculate per-account statistics
        account_stats = {}
        for account_id, txs in account_txs.items():
            amounts = [abs(float(tx.amount)) for tx in txs if tx.amount is not None]
            avg_amount = np.mean(amounts) if amounts else 1.0
            
            account = accounts_map.get(account_id)
            
            # Calculate account age
            if account and account.first_transaction_date:
                latest_date = max(tx.date for tx in txs)
                account_age_days = (latest_date - account.first_transaction_date) / (1000 * 60 * 60 * 24)
            else:
                account_age_days = 0
            
            # Calculate transaction frequency
            tx_frequency = len(txs) / account_age_days if account_age_days > 0 else 0
            
            account_stats[account_id] = {
                'count': len(txs),
                'avg_amount': avg_amount,
                'age_days': account_age_days,
                'frequency': tx_frequency,
                'is_active': account.is_active if account else True
            }
        
        # Second pass: create features for each transaction
        features = []
        for tx in transactions:
            stats = account_stats.get(tx.account_id)
            
            if stats:
                tx_amount = abs(float(tx.amount)) if tx.amount else 0
                amount_ratio = tx_amount / stats['avg_amount'] if stats['avg_amount'] > 0 else 0
                
                feature_vector = [
                    min(1.0, stats['count'] / 1000.0),      # Normalized count (max 1000)
                    min(1.0, amount_ratio / 10.0),          # Normalized amount ratio (max 10x)
                    min(1.0, stats['age_days'] / 3650.0),   # Normalized age (max 10 years)
                    min(1.0, stats['frequency'] * 10.0),    # Normalized frequency
                    1.0 if stats['is_active'] else 0.0      # Active flag
                ]
            else:
                feature_vector = [0.0, 0.0, 0.0, 0.0, 1.0]
            
            features.append(feature_vector)
        
        return np.array(features)

