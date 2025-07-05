"""
Pattern Extraction Service for intelligent merchant recognition and category suggestions.

This service provides smart pattern extraction from transaction descriptions,
merchant recognition, and category name suggestions for quick categorization workflows.
"""

import logging
import re
import uuid
from collections import Counter
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from decimal import Decimal

from models.category import Category, CategoryType
from models.transaction import Transaction
from utils.db_utils import list_user_transactions

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@dataclass
class PatternSuggestion:
    """Represents a suggested pattern for category rules"""
    pattern: str
    confidence: float
    match_count: int
    field: str  # 'description', 'payee', 'memo'
    explanation: str
    pattern_type: str  # 'merchant', 'keyword', 'prefix', 'suffix'
    
    @property
    def condition(self):
        """Return MatchCondition for backward compatibility"""
        from models.category import MatchCondition
        if self.pattern_type == 'prefix':
            return MatchCondition.STARTS_WITH
        elif self.pattern_type == 'suffix':
            return MatchCondition.ENDS_WITH
        else:
            return MatchCondition.CONTAINS


@dataclass
class CategorySuggestion:
    """Represents a suggested category name and type"""
    name: str
    category_type: CategoryType
    suggested_patterns: List[PatternSuggestion]
    confidence: float
    merchant_name: str = ""
    icon: str = "📁"


@dataclass
class MerchantInfo:
    """Information about a recognized merchant"""
    name: str
    normalized_name: str
    suggested_category: str
    category_type: CategoryType
    confidence: float
    common_patterns: List[str]


class PatternExtractionService:
    """Service for extracting patterns and suggesting categories from transaction descriptions"""
    
    def __init__(self):
        self.merchant_database = self._build_merchant_database()
        self.common_prefixes = self._build_common_prefixes()
        self.amount_indicators = self._build_amount_indicators()
    
    def _build_merchant_database(self) -> Dict[str, MerchantInfo]:
        """Build a database of known merchants and their category mappings"""
        return {
            # Food & Dining
            'starbucks': MerchantInfo(
                name='Starbucks',
                normalized_name='STARBUCKS',
                suggested_category='Coffee & Cafes',
                category_type=CategoryType.EXPENSE,
                confidence=0.95,
                common_patterns=['STARBUCKS', 'SBX', 'STARBUCK']
            ),
            'mcdonalds': MerchantInfo(
                name="McDonald's",
                normalized_name='MCDONALDS',
                suggested_category='Fast Food',
                category_type=CategoryType.EXPENSE,
                confidence=0.95,
                common_patterns=['MCDONALDS', 'MCD', 'MCDONALD']
            ),
            'subway': MerchantInfo(
                name='Subway',
                normalized_name='SUBWAY',
                suggested_category='Fast Food',
                category_type=CategoryType.EXPENSE,
                confidence=0.90,
                common_patterns=['SUBWAY']
            ),
            'dominos': MerchantInfo(
                name="Domino's Pizza",
                normalized_name='DOMINOS',
                suggested_category='Restaurants',
                category_type=CategoryType.EXPENSE,
                confidence=0.92,
                common_patterns=['DOMINOS', "DOMINO'S"]
            ),
            
            # Shopping
            'amazon': MerchantInfo(
                name='Amazon',
                normalized_name='AMAZON',
                suggested_category='Online Shopping',
                category_type=CategoryType.EXPENSE,
                confidence=0.98,
                common_patterns=['AMAZON', 'AMZN', 'AMZ']
            ),
            'walmart': MerchantInfo(
                name='Walmart',
                normalized_name='WALMART',
                suggested_category='Shopping',
                category_type=CategoryType.EXPENSE,
                confidence=0.95,
                common_patterns=['WALMART', 'WAL-MART', 'WM']
            ),
            'target': MerchantInfo(
                name='Target',
                normalized_name='TARGET',
                suggested_category='Shopping',
                category_type=CategoryType.EXPENSE,
                confidence=0.90,
                common_patterns=['TARGET', 'TGT']
            ),
            'costco': MerchantInfo(
                name='Costco',
                normalized_name='COSTCO',
                suggested_category='Shopping',
                category_type=CategoryType.EXPENSE,
                confidence=0.95,
                common_patterns=['COSTCO', 'COSTCO WHOLESALE']
            ),
            
            # Gas & Fuel
            'shell': MerchantInfo(
                name='Shell',
                normalized_name='SHELL',
                suggested_category='Gas & Fuel',
                category_type=CategoryType.EXPENSE,
                confidence=0.95,
                common_patterns=['SHELL', 'SHELL OIL']
            ),
            'exxon': MerchantInfo(
                name='Exxon',
                normalized_name='EXXON',
                suggested_category='Gas & Fuel',
                category_type=CategoryType.EXPENSE,
                confidence=0.95,
                common_patterns=['EXXON', 'EXXONMOBIL', 'ESSO']
            ),
            'bp': MerchantInfo(
                name='BP',
                normalized_name='BP',
                suggested_category='Gas & Fuel',
                category_type=CategoryType.EXPENSE,
                confidence=0.90,
                common_patterns=['BP', 'BRITISH PETROLEUM']
            ),
            'chevron': MerchantInfo(
                name='Chevron',
                normalized_name='CHEVRON',
                suggested_category='Gas & Fuel',
                category_type=CategoryType.EXPENSE,
                confidence=0.95,
                common_patterns=['CHEVRON', 'TEXACO']
            ),
            
            # Banking & Finance
            'bank of america': MerchantInfo(
                name='Bank of America',
                normalized_name='BANK OF AMERICA',
                suggested_category='Bank Fees',
                category_type=CategoryType.EXPENSE,
                confidence=0.95,
                common_patterns=['BANK OF AMERICA', 'BofA', 'BOA']
            ),
            'chase': MerchantInfo(
                name='Chase Bank',
                normalized_name='CHASE',
                suggested_category='Bank Fees',
                category_type=CategoryType.EXPENSE,
                confidence=0.92,
                common_patterns=['CHASE', 'JPMORGAN CHASE']
            ),
            'wells fargo': MerchantInfo(
                name='Wells Fargo',
                normalized_name='WELLS FARGO',
                suggested_category='Bank Fees',
                category_type=CategoryType.EXPENSE,
                confidence=0.95,
                common_patterns=['WELLS FARGO', 'WF', 'WFARGO']
            ),
            
            # Transportation
            'uber': MerchantInfo(
                name='Uber',
                normalized_name='UBER',
                suggested_category='Transportation',
                category_type=CategoryType.EXPENSE,
                confidence=0.98,
                common_patterns=['UBER', 'UBER TRIP']
            ),
            'lyft': MerchantInfo(
                name='Lyft',
                normalized_name='LYFT',
                suggested_category='Transportation',
                category_type=CategoryType.EXPENSE,
                confidence=0.98,
                common_patterns=['LYFT']
            ),
            
            # Utilities
            'electric': MerchantInfo(
                name='Electric Company',
                normalized_name='ELECTRIC',
                suggested_category='Utilities',
                category_type=CategoryType.EXPENSE,
                confidence=0.85,
                common_patterns=['ELECTRIC', 'POWER', 'ENERGY']
            ),
            'gas company': MerchantInfo(
                name='Gas Company',
                normalized_name='GAS COMPANY',
                suggested_category='Utilities',
                category_type=CategoryType.EXPENSE,
                confidence=0.85,
                common_patterns=['GAS COMPANY', 'NATURAL GAS']
            ),
            
            # Subscriptions
            'netflix': MerchantInfo(
                name='Netflix',
                normalized_name='NETFLIX',
                suggested_category='Entertainment',
                category_type=CategoryType.EXPENSE,
                confidence=0.98,
                common_patterns=['NETFLIX']
            ),
            'spotify': MerchantInfo(
                name='Spotify',
                normalized_name='SPOTIFY',
                suggested_category='Entertainment',
                category_type=CategoryType.EXPENSE,
                confidence=0.98,
                common_patterns=['SPOTIFY']
            ),
            'apple': MerchantInfo(
                name='Apple',
                normalized_name='APPLE',
                suggested_category='Software & Apps',
                category_type=CategoryType.EXPENSE,
                confidence=0.85,
                common_patterns=['APPLE', 'ITUNES', 'APP STORE']
            ),
        }
    
    def _build_common_prefixes(self) -> List[str]:
        """Build list of common transaction prefixes to ignore"""
        return [
            'PAYMENT TO',
            'TRANSFER TO',
            'DEPOSIT FROM',
            'WITHDRAWAL AT',
            'CHECK #',
            'DEBIT CARD',
            'CREDIT CARD',
            'ATM WITHDRAWAL',
            'PURCHASE AT',
            'PAYMENT FOR',
            'CHARGE FROM',
            'PMT',
            'TFR',
            'DEP',
            'WDL',
            'CHK',
            'DEB',
            'CRD',
        ]
    
    def _build_amount_indicators(self) -> Dict[str, CategoryType]:
        """Build mapping of amount-related keywords to category types"""
        return {
            'salary': CategoryType.INCOME,
            'payroll': CategoryType.INCOME,
            'bonus': CategoryType.INCOME,
            'refund': CategoryType.INCOME,
            'dividend': CategoryType.INCOME,
            'interest': CategoryType.INCOME,
            'fee': CategoryType.EXPENSE,
            'charge': CategoryType.EXPENSE,
            'payment': CategoryType.EXPENSE,
            'purchase': CategoryType.EXPENSE,
        }
    
    def extract_merchant_from_description(self, description: str) -> Optional[MerchantInfo]:
        """Extract merchant information from transaction description"""
        if not description:
            return None
        
        # Normalize description for matching
        normalized_desc = description.upper().strip()
        
        # Remove common prefixes
        for prefix in self.common_prefixes:
            if normalized_desc.startswith(prefix):
                normalized_desc = normalized_desc[len(prefix):].strip()
        
        # Try to match known merchants
        for merchant_key, merchant_info in self.merchant_database.items():
            for pattern in merchant_info.common_patterns:
                if pattern in normalized_desc:
                    return merchant_info
        
        # Try partial matching for new merchants
        return self._extract_unknown_merchant(normalized_desc)
    
    def _extract_unknown_merchant(self, description: str) -> Optional[MerchantInfo]:
        """Extract merchant name from unknown merchant descriptions"""
        # Remove common suffixes and prefixes
        cleaned = description
        
        # Remove location codes (e.g., "SEATTLE WA", "12345")
        cleaned = re.sub(r'\b[A-Z]{2}\b', '', cleaned)  # State codes
        cleaned = re.sub(r'\b\d{5,}\b', '', cleaned)   # Long numbers
        cleaned = re.sub(r'\b\d{2}/\d{2}\b', '', cleaned)  # Dates
        
        # Extract the first meaningful part
        words = cleaned.split()
        if words:
            merchant_name = words[0]
            if len(merchant_name) >= 3:  # Minimum length for meaningful merchant name
                return MerchantInfo(
                    name=merchant_name.title(),
                    normalized_name=merchant_name,
                    suggested_category='General',
                    category_type=CategoryType.EXPENSE,
                    confidence=0.60,
                    common_patterns=[merchant_name]
                )
        
        return None
    
    def generate_patterns_from_description(self, description: str) -> List[PatternSuggestion]:
        """Generate pattern suggestions from a transaction description"""
        patterns = []
        
        if not description:
            return patterns
        
        # Extract merchant info
        merchant_info = self.extract_merchant_from_description(description)
        
        if merchant_info:
            # Create patterns for known merchant
            for pattern in merchant_info.common_patterns:
                patterns.append(PatternSuggestion(
                    pattern=pattern,
                    confidence=merchant_info.confidence,
                    match_count=0,  # Will be calculated when testing
                    field='description',
                    explanation=f"Matches {merchant_info.name} transactions",
                    pattern_type='merchant'
                ))
        
        # Generate keyword-based patterns
        normalized = description.upper()
        
        # Look for meaningful keywords
        keywords = self._extract_keywords(normalized)
        for keyword in keywords:
            patterns.append(PatternSuggestion(
                pattern=keyword,
                confidence=0.75,
                match_count=0,
                field='description',
                explanation=f"Matches transactions containing '{keyword}'",
                pattern_type='keyword'
            ))
        
        # Generate prefix/suffix patterns if applicable
        prefix_pattern = self._extract_prefix_pattern(normalized)
        if prefix_pattern:
            patterns.append(prefix_pattern)
        
        suffix_pattern = self._extract_suffix_pattern(normalized)
        if suffix_pattern:
            patterns.append(suffix_pattern)
        
        return patterns[:5]  # Return top 5 patterns
    
    def _extract_keywords(self, description: str) -> List[str]:
        """Extract meaningful keywords from description"""
        # Remove noise words
        noise_words = {'THE', 'AND', 'OR', 'AT', 'TO', 'FROM', 'FOR', 'OF', 'IN', 'ON', 'WITH'}
        
        # Split into words and filter
        words = re.findall(r'\b[A-Z]{3,}\b', description)  # 3+ letter words
        meaningful_words = [word for word in words if word not in noise_words and len(word) >= 3]
        
        return meaningful_words[:3]  # Return top 3 keywords
    
    def _extract_prefix_pattern(self, description: str) -> Optional[PatternSuggestion]:
        """Extract prefix-based pattern if description follows common pattern"""
        # Look for patterns like "AMAZON.*", "STARBUCKS.*"
        words = description.split()
        if words and len(words[0]) >= 4:
            return PatternSuggestion(
                pattern=f"{words[0]}.*",
                confidence=0.80,
                match_count=0,
                field='description',
                explanation=f"Matches transactions starting with '{words[0]}'",
                pattern_type='prefix'
            )
        return None
    
    def _extract_suffix_pattern(self, description: str) -> Optional[PatternSuggestion]:
        """Extract suffix-based pattern if applicable"""
        # Look for patterns ending with specific suffixes
        common_suffixes = ['PAYMENT', 'CHARGE', 'FEE', 'PURCHASE', 'SUBSCRIPTION']
        
        for suffix in common_suffixes:
            if description.endswith(suffix):
                return PatternSuggestion(
                    pattern=f".*{suffix}",
                    confidence=0.70,
                    match_count=0,
                    field='description',
                    explanation=f"Matches transactions ending with '{suffix}'",
                    pattern_type='suffix'
                )
        return None
    
    def suggest_category_from_transaction(self, transaction: Transaction) -> Optional[CategorySuggestion]:
        """Suggest category name and type based on transaction data"""
        # First try merchant recognition
        merchant_info = self.extract_merchant_from_description(transaction.description)
        
        if merchant_info and merchant_info.confidence > 0.8:
            patterns = self.generate_patterns_from_description(transaction.description)
            return CategorySuggestion(
                name=merchant_info.suggested_category,
                category_type=merchant_info.category_type,
                suggested_patterns=patterns,
                confidence=merchant_info.confidence,
                merchant_name=merchant_info.name,
                icon=self._suggest_icon_for_category(merchant_info.suggested_category)
            )
        
        # Fallback to amount-based categorization
        return self._suggest_category_by_amount_and_keywords(transaction)
    
    def _suggest_category_by_amount_and_keywords(self, transaction: Transaction) -> Optional[CategorySuggestion]:
        """Suggest category based on amount and keywords when merchant is unknown"""
        description = transaction.description.lower()
        amount = float(transaction.amount) if transaction.amount else 0
        
        # Check for income indicators
        if amount > 0:  # Positive amount typically indicates income
            income_keywords = ['salary', 'payroll', 'bonus', 'refund', 'dividend', 'interest']
            for keyword in income_keywords:
                if keyword in description:
                    return CategorySuggestion(
                        name=keyword.title(),
                        category_type=CategoryType.INCOME,
                        suggested_patterns=self.generate_patterns_from_description(transaction.description),
                        confidence=0.75
                    )
            
            return CategorySuggestion(
                name='Income',
                category_type=CategoryType.INCOME,
                suggested_patterns=self.generate_patterns_from_description(transaction.description),
                confidence=0.60
            )
        
        # Check for expense categories by keywords
        expense_keywords = {
            'gas': 'Gas & Fuel',
            'fuel': 'Gas & Fuel',
            'grocery': 'Groceries',
            'food': 'Food & Dining',
            'restaurant': 'Restaurants',
            'coffee': 'Coffee & Cafes',
            'electric': 'Utilities',
            'power': 'Utilities',
            'insurance': 'Insurance',
            'medical': 'Healthcare',
            'pharmacy': 'Healthcare',
            'rent': 'Housing',
            'mortgage': 'Housing',
        }
        
        for keyword, category_name in expense_keywords.items():
            if keyword in description:
                return CategorySuggestion(
                    name=category_name,
                    category_type=CategoryType.EXPENSE,
                    suggested_patterns=self.generate_patterns_from_description(transaction.description),
                    confidence=0.70
                )
        
        # Default to general expense
        return CategorySuggestion(
            name='General',
            category_type=CategoryType.EXPENSE,
            suggested_patterns=self.generate_patterns_from_description(transaction.description),
            confidence=0.50
        )
    
    def generate_patterns_from_samples(self, descriptions: List[str]) -> List[PatternSuggestion]:
        """Generate patterns from multiple sample descriptions"""
        if not descriptions:
            return []
        
        # Find common substrings
        common_patterns = self._find_common_substrings(descriptions)
        
        # Convert to pattern suggestions
        suggestions = []
        for pattern, frequency in common_patterns.items():
            confidence = min(0.95, 0.5 + (frequency / len(descriptions)) * 0.5)
            suggestions.append(PatternSuggestion(
                pattern=pattern,
                confidence=confidence,
                match_count=frequency,
                field='description',
                explanation=f"Common pattern found in {frequency}/{len(descriptions)} samples",
                pattern_type='common'
            ))
        
        return sorted(suggestions, key=lambda x: x.confidence, reverse=True)[:5]
    
    def _find_common_substrings(self, descriptions: List[str]) -> Dict[str, int]:
        """Find common substrings across multiple descriptions"""
        # Normalize descriptions
        normalized = [desc.upper().strip() for desc in descriptions]
        
        # Find substrings that appear in multiple descriptions
        substring_counts = Counter()
        
        for desc in normalized:
            # Extract meaningful words (3+ characters)
            words = re.findall(r'\b[A-Z]{3,}\b', desc)
            for word in words:
                substring_counts[word] += 1
        
        # Return substrings that appear in at least 2 descriptions
        return {pattern: count for pattern, count in substring_counts.items() 
                if count >= 2 and len(pattern) >= 3}
    
    async def calculate_pattern_match_count(self, pattern: str, user_id: str, field: str = 'description') -> int:
        """Calculate how many transactions would match a given pattern"""
        try:
            # Get user's transactions - unpack the tuple
            transactions, _, _ = list_user_transactions(user_id)
            
            match_count = 0
            for transaction in transactions:
                field_value = getattr(transaction, field, '') or ''
                if self._pattern_matches(pattern, field_value):
                    match_count += 1
            
            return match_count
        except Exception as e:
            logger.error(f"Error calculating pattern match count: {str(e)}")
            return 0
    
    def _pattern_matches(self, pattern: str, text: str) -> bool:
        """Check if a pattern matches text (supports simple contains and basic regex)"""
        if not pattern or not text:
            return False
        
        try:
            # Try as regex first
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            # Fallback to simple contains
            return pattern.upper() in text.upper()
    
    def get_similar_transactions(self, transaction: Transaction, user_id: str, limit: int = 10) -> List[Transaction]:
        """Find transactions similar to the given transaction"""
        try:
            # Extract patterns from the transaction
            patterns = self.generate_patterns_from_description(transaction.description)
            
            if not patterns:
                return []
            
            # Get user's transactions - unpack the tuple
            all_transactions, _, _ = list_user_transactions(user_id)
            
            # Score transactions by similarity 
            scored_transactions = []
            for t in all_transactions:
                # Skip comparison with same transaction (simplified approach)
                if hasattr(t, 'transaction_id') and hasattr(transaction, 'transaction_id'):
                    try:
                        if str(getattr(t, 'transaction_id')) == str(getattr(transaction, 'transaction_id')):
                            continue
                    except (AttributeError, TypeError):
                        pass
                
                try:
                    similarity_score = self._calculate_similarity(transaction, t, patterns)
                    if similarity_score > 0.3:  # Minimum similarity threshold
                        scored_transactions.append((t, similarity_score))
                except (AttributeError, TypeError) as e:
                    logger.warning(f"Error calculating similarity: {str(e)}")
                    continue
            
            # Sort by similarity and return top matches
            scored_transactions.sort(key=lambda x: x[1], reverse=True)
            return [t for t, score in scored_transactions[:limit]]
            
        except Exception as e:
            logger.error(f"Error finding similar transactions: {str(e)}")
            return []
    
    def _calculate_similarity(self, t1: Transaction, t2: Transaction, patterns: List[PatternSuggestion]) -> float:
        """Calculate similarity score between two transactions"""
        score = 0.0
        
        # Check pattern matches
        for pattern in patterns:
            if self._pattern_matches(pattern.pattern, t2.description):
                score += pattern.confidence * 0.6  # 60% weight for pattern match
        
        # Check amount similarity (if amounts are close)
        if t1.amount and t2.amount:
            amount_diff = abs(float(t1.amount) - float(t2.amount))
            if amount_diff < 5.0:  # Within $5
                score += 0.2
            elif amount_diff < 20.0:  # Within $20
                score += 0.1
        
        # Check date proximity (bonus for recent transactions)
        if t1.date and t2.date:
            date_diff = abs(t1.date - t2.date)
            if date_diff < 30 * 24 * 60 * 60 * 1000:  # Within 30 days
                score += 0.1
        
        return min(score, 1.0)
    
    def extract_patterns_from_description(self, description: str) -> List[PatternSuggestion]:
        """Alias for generate_patterns_from_description for backward compatibility"""
        return self.generate_patterns_from_description(description)
    
    def create_category_with_rule(
        self, 
        category_name: str, 
        category_type: str, 
        pattern: str, 
        field_to_match: str = 'description',
        condition = None  # Will be MatchCondition from models.category
    ) -> Dict[str, Any]:
        """Create category data structure with pre-populated rule"""
        try:
            import uuid
            from models.category import MatchCondition, CategoryType
            
            category_id = str(uuid.uuid4())
            rule_id = f"rule_{uuid.uuid4().hex[:8]}"
            
            # Handle condition parameter
            if condition is None:
                from models.category import MatchCondition
                condition = MatchCondition.CONTAINS
            
            # Convert string category_type to CategoryType enum if needed
            if isinstance(category_type, str):
                try:
                    category_type_enum = CategoryType(category_type.upper())
                except ValueError:
                    category_type_enum = CategoryType.EXPENSE  # Default fallback
            else:
                category_type_enum = category_type
            
            rule_data = {
                "ruleId": rule_id,
                "fieldToMatch": field_to_match,
                "condition": condition.value if hasattr(condition, 'value') else str(condition),
                "value": pattern,
                "caseSensitive": False,
                "priority": 0,
                "enabled": True,
                "confidence": 1.0,
                "allowMultipleMatches": True,
                "autoSuggest": True
            }
            
            category_data = {
                "categoryId": category_id,
                "name": category_name,
                "type": category_type_enum.value,
                "rules": [rule_data],
                "icon": self._suggest_icon_for_category(category_name),
                "color": self._suggest_color_for_category(category_name)
            }
            
            return {
                "category": category_data,
                "rule": rule_data,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error creating category with rule: {str(e)}")
            return {
                "error": f"Failed to create category with rule: {str(e)}",
                "success": False
            }
    
    def _suggest_icon_for_category(self, category_name: str) -> str:
        """Suggest an appropriate icon for a category"""
        name_lower = category_name.lower()
        
        icon_mapping = {
            'food': '🍽️', 'coffee': '☕', 'gas': '⛽', 'shopping': '🛍️',
            'amazon': '📦', 'medical': '🏥', 'bank': '🏦', 'income': '💰',
            'fast food': '🍔', 'restaurants': '🍽️', 'groceries': '🛒',
            'utilities': '🏠', 'entertainment': '🎬', 'transportation': '🚗',
            'healthcare': '⚕️', 'insurance': '🛡️', 'housing': '🏡'
        }
        
        for keyword, icon in icon_mapping.items():
            if keyword in name_lower:
                return icon
        
        return '📁'
    
    def _suggest_color_for_category(self, category_name: str) -> str:
        """Suggest an appropriate color for a category"""
        name_lower = category_name.lower()
        
        color_mapping = {
            'income': '#4CAF50',     # Green
            'food': '#FF9800',       # Orange
            'shopping': '#E91E63',   # Pink
            'gas': '#795548',        # Brown
            'utilities': '#607D8B',  # Blue Grey
            'entertainment': '#9C27B0', # Purple
            'transportation': '#2196F3', # Blue
            'healthcare': '#F44336', # Red
            'bank': '#3F51B5',       # Indigo
        }
        
        for keyword, color in color_mapping.items():
            if keyword in name_lower:
                return color
        
        return '#74B9FF'  # Default blue 