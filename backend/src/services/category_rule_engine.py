"""
Category Rule Engine Service

This service handles pattern matching of transactions against category rules,
generates category suggestions with confidence scores, and manages the suggestion workflow.
"""

import logging
import re
import uuid
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from enum import Enum

from models.category import Category, CategoryRule
from models.transaction import Transaction, TransactionCategoryAssignment, CategoryAssignmentStatus
from utils.db_utils import list_categories_by_user_from_db, list_user_transactions

logger = logging.getLogger(__name__)


class MatchCondition(str, Enum):
    """Enhanced pattern matching conditions for category rules"""
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    EQUALS = "equals"
    REGEX = "regex"
    AMOUNT_GREATER = "amount_greater"
    AMOUNT_LESS = "amount_less"
    AMOUNT_BETWEEN = "amount_between"


class CategorySuggestionStrategy(str, Enum):
    """Strategy for handling multiple category matches"""
    ALL_MATCHES = "all_matches"              # Show all matching categories as suggestions
    TOP_N_MATCHES = "top_n_matches"          # Show only top N highest confidence matches
    CONFIDENCE_THRESHOLD = "confidence_threshold"  # Show only matches above threshold
    PRIORITY_FILTERED = "priority_filtered"   # Show matches filtered by rule priority


class CategoryRuleEngine:
    """
    Core engine for category rule processing and suggestion generation.
    
    Handles pattern matching, confidence scoring, and multiple category suggestion workflows.
    """
    
    def __init__(self, suggestion_strategy: CategorySuggestionStrategy = CategorySuggestionStrategy.ALL_MATCHES):
        self.suggestion_strategy = suggestion_strategy
        self.compiled_patterns: Dict[str, re.Pattern] = {}  # Cache for compiled regex patterns
        self.category_cache: Dict[str, List[Category]] = {}  # Cache for user categories
        
    def categorize_transaction(
        self, 
        transaction: Transaction, 
        user_id: str,
        create_suggestions: bool = True
    ) -> List[TransactionCategoryAssignment]:
        """
        Analyze a transaction and return all matching category assignments as suggestions.
        
        Args:
            transaction: The transaction to categorize
            user_id: User ID for category lookup
            create_suggestions: Whether to create suggestions or just return matches
            
        Returns:
            List of category assignments (suggestions) for the transaction
        """
        try:
            # Get user's categories
            categories = self._get_user_categories(user_id)
            
            # Find all matching categories
            matches = self._find_matching_categories(transaction, categories)
            
            if not matches:
                return []
            
            # Create suggestions based on strategy
            suggestions = self._create_suggestions_from_matches(matches)
            
            if create_suggestions:
                # Add suggestions to transaction (in-memory, caller needs to persist)
                for suggestion in suggestions:
                    transaction.add_category_suggestion(
                        suggestion.category_id,
                        suggestion.confidence,
                        suggestion.rule_id
                    )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error categorizing transaction {transaction.transaction_id}: {str(e)}")
            return []
    
    def test_rule_against_transactions(
        self, 
        user_id: str, 
        rule: CategoryRule, 
        field_to_match: str = "description",
        limit: int = 100
    ) -> List[Transaction]:
        """
        Test a category rule against user's transactions and return matches.
        
        Args:
            user_id: User ID
            rule: The category rule to test
            field_to_match: Transaction field to match against
            limit: Maximum number of results to return
            
        Returns:
            List of matching transactions
        """
        try:
            # Get user's transactions
            transactions = self._get_user_transactions(user_id, limit * 2)  # Get more to account for filtering
            
            matching_transactions = []
            
            for transaction in transactions:
                if len(matching_transactions) >= limit:
                    break
                    
                if self._rule_matches_transaction(rule, transaction, field_to_match):
                    matching_transactions.append(transaction)
            
            return matching_transactions
            
        except Exception as e:
            logger.error(f"Error testing rule against transactions: {str(e)}")
            return []
    
    def apply_category_rules_bulk(
        self, 
        user_id: str, 
        category_id: Optional[str] = None,
        transaction_ids: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Apply category rules to transactions in bulk and create suggestions.
        
        Args:
            user_id: User ID
            category_id: Specific category to apply rules for (optional)
            transaction_ids: Specific transactions to process (optional)
            
        Returns:
            Dictionary with processing statistics
        """
        try:
            processed = 0
            suggestions_created = 0
            errors = 0
            
            # Get transactions to process
            if transaction_ids:
                transactions = self._get_transactions_by_ids(user_id, transaction_ids)
            else:
                transactions = self._get_user_transactions(user_id)
            
            # Get categories to apply
            if category_id:
                category = self._get_category_by_id(user_id, category_id)
                categories = [category] if category else []
            else:
                categories = self._get_user_categories(user_id)
            
            for transaction in transactions:
                try:
                    # Only process transactions that don't already have confirmed categories
                    if not transaction.confirmed_categories:
                        suggestions = self.categorize_transaction(transaction, user_id)
                        suggestions_created += len(suggestions)
                    
                    processed += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing transaction {transaction.transaction_id}: {str(e)}")
                    errors += 1
            
            return {
                "processed": processed,
                "suggestions_created": suggestions_created,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error in bulk rule application: {str(e)}")
            return {"processed": 0, "suggestions_created": 0, "errors": 1}
    
    def calculate_rule_confidence(
        self, 
        rule: CategoryRule, 
        transaction: Transaction,
        field_to_match: str = "description"
    ) -> float:
        """
        Calculate confidence score for a rule match.
        
        Args:
            rule: The category rule
            transaction: The transaction
            field_to_match: Field being matched
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            base_confidence = 0.8  # Base confidence for any match
            
            # Adjust confidence based on match type
            condition = getattr(rule, 'condition', 'contains')
            
            if condition == MatchCondition.EQUALS:
                confidence_boost = 0.2  # Exact matches are more confident
            elif condition == MatchCondition.REGEX:
                confidence_boost = 0.15  # Regex matches are fairly confident
            elif condition in [MatchCondition.STARTS_WITH, MatchCondition.ENDS_WITH]:
                confidence_boost = 0.1   # Position-specific matches
            else:  # CONTAINS
                confidence_boost = 0.05  # Contains matches are less specific
            
            # Adjust based on field being matched
            field_confidence_multiplier = {
                "description": 1.0,     # Description is most reliable
                "memo": 0.9,           # Memo is fairly reliable
                "transaction_type": 0.8, # Transaction type is less reliable
                "amount": 0.7          # Amount-based rules are context-dependent
            }.get(field_to_match, 0.8)
            
            # Calculate final confidence
            final_confidence = min(1.0, (base_confidence + confidence_boost) * field_confidence_multiplier)
            
            return round(final_confidence, 2)
            
        except Exception as e:
            logger.warning(f"Error calculating rule confidence: {str(e)}")
            return 0.5  # Default confidence
    
    def validate_regex_pattern(self, pattern: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a regex pattern for syntax errors.
        
        Args:
            pattern: The regex pattern to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            re.compile(pattern)
            return True, None
        except re.error as e:
            return False, f"Invalid regex pattern: {str(e)}"
    
    def generate_simple_pattern(self, sample_descriptions: List[str]) -> Optional[str]:
        """
        Generate a simple pattern from sample transaction descriptions.
        
        Args:
            sample_descriptions: List of sample transaction descriptions
            
        Returns:
            Generated pattern or None if no common pattern found
        """
        try:
            if not sample_descriptions:
                return None
            
            # Find common words across all descriptions
            common_words = self._find_common_words(sample_descriptions)
            
            if common_words:
                # Return the most common word as a simple pattern
                return common_words[0]
            
            # Fallback: find common prefixes
            common_prefix = self._find_common_prefix(sample_descriptions)
            if len(common_prefix) >= 3:  # Minimum meaningful prefix
                return common_prefix
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating simple pattern: {str(e)}")
            return None
    
    # Private helper methods
    
    def _get_user_categories(self, user_id: str) -> List[Category]:
        """Get and cache user's categories"""
        if user_id not in self.category_cache:
            try:
                self.category_cache[user_id] = list_categories_by_user_from_db(user_id)
            except Exception as e:
                logger.error(f"Error fetching categories for user {user_id}: {str(e)}")
                self.category_cache[user_id] = []
        
        return self.category_cache[user_id]
    
    def _get_user_transactions(self, user_id: str, limit: int = 1000) -> List[Transaction]:
        """Get user's transactions for rule testing"""
        try:
            return list_user_transactions(user_id, limit=limit)
        except Exception as e:
            logger.error(f"Error fetching transactions for user {user_id}: {str(e)}")
            return []
    
    def _get_category_by_id(self, user_id: str, category_id: str) -> Optional[Category]:
        """Get a specific category by ID"""
        categories = self._get_user_categories(user_id)
        return next((cat for cat in categories if str(cat.categoryId) == category_id), None)
    
    def _get_transactions_by_ids(self, user_id: str, transaction_ids: List[str]) -> List[Transaction]:
        """Get specific transactions by IDs (placeholder - would need implementation in db_utils)"""
        # This would need to be implemented in db_utils.py
        # For now, return empty list
        logger.warning("_get_transactions_by_ids not implemented yet")
        return []
    
    def _find_matching_categories(
        self, 
        transaction: Transaction, 
        categories: List[Category]
    ) -> List[Tuple[Category, CategoryRule, float]]:
        """Find all categories that match a transaction"""
        matches = []
        
        for category in categories:
            for rule in category.rules:
                if self._rule_matches_transaction(rule, transaction):
                    confidence = self.calculate_rule_confidence(rule, transaction, rule.fieldToMatch)
                    matches.append((category, rule, confidence))
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x[2], reverse=True)
        
        return matches
    
    def _rule_matches_transaction(
        self, 
        rule: CategoryRule, 
        transaction: Transaction,
        field_to_match: Optional[str] = None
    ) -> bool:
        """Check if a rule matches a transaction"""
        try:
            # Determine field to match
            if field_to_match is None:
                field_to_match = getattr(rule, 'fieldToMatch', 'description')
            
            # Get transaction field value
            transaction_value = self._get_transaction_field_value(transaction, field_to_match)
            if transaction_value is None:
                return False
            
            # Get rule pattern
            pattern = str(rule.value)
            condition = getattr(rule, 'condition', 'contains')
            
            # Handle amount-based conditions
            if condition in [MatchCondition.AMOUNT_GREATER, MatchCondition.AMOUNT_LESS, MatchCondition.AMOUNT_BETWEEN]:
                return self._match_amount_condition(transaction.amount, pattern, condition)
            
            # Handle text-based conditions
            return self._match_text_condition(transaction_value, pattern, condition)
            
        except Exception as e:
            logger.warning(f"Error matching rule against transaction: {str(e)}")
            return False
    
    def _get_transaction_field_value(self, transaction: Transaction, field_name: str) -> Optional[str]:
        """Get the value of a transaction field for matching"""
        field_mapping = {
            'description': transaction.description,
            'memo': transaction.memo,
            'transaction_type': transaction.transaction_type,
            'check_number': transaction.check_number,
            'amount': str(transaction.amount)
        }
        
        return field_mapping.get(field_name)
    
    def _match_text_condition(self, text: str, pattern: str, condition: str) -> bool:
        """Match text against pattern with given condition"""
        if not text:
            return False
        
        text = text.lower()  # Case-insensitive matching
        pattern = pattern.lower()
        
        if condition == MatchCondition.CONTAINS:
            return pattern in text
        elif condition == MatchCondition.STARTS_WITH:
            return text.startswith(pattern)
        elif condition == MatchCondition.ENDS_WITH:
            return text.endswith(pattern)
        elif condition == MatchCondition.EQUALS:
            return text == pattern
        elif condition == MatchCondition.REGEX:
            return self._match_regex_pattern(text, pattern)
        
        return False
    
    def _match_amount_condition(self, amount: Decimal, pattern: str, condition: str) -> bool:
        """Match amount against pattern with given condition"""
        try:
            if condition == MatchCondition.AMOUNT_GREATER:
                threshold = Decimal(pattern)
                return abs(amount) > threshold
            elif condition == MatchCondition.AMOUNT_LESS:
                threshold = Decimal(pattern)
                return abs(amount) < threshold
            elif condition == MatchCondition.AMOUNT_BETWEEN:
                # Pattern should be "min,max"
                min_val, max_val = pattern.split(',')
                min_amount = Decimal(min_val.strip())
                max_amount = Decimal(max_val.strip())
                abs_amount = abs(amount)
                return min_amount <= abs_amount <= max_amount
            
            return False
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing amount condition: {str(e)}")
            return False
    
    def _match_regex_pattern(self, text: str, pattern: str) -> bool:
        """Match text against regex pattern with caching"""
        try:
            # Use cached compiled pattern if available
            if pattern not in self.compiled_patterns:
                self.compiled_patterns[pattern] = re.compile(pattern, re.IGNORECASE)
            
            compiled_pattern = self.compiled_patterns[pattern]
            return bool(compiled_pattern.search(text))
            
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {str(e)}")
            return False
    
    def _create_suggestions_from_matches(
        self, 
        matches: List[Tuple[Category, CategoryRule, float]]
    ) -> List[TransactionCategoryAssignment]:
        """Create category assignment suggestions from matches based on strategy"""
        if not matches:
            return []
        
        if self.suggestion_strategy == CategorySuggestionStrategy.ALL_MATCHES:
            return self._create_all_match_suggestions(matches)
        elif self.suggestion_strategy == CategorySuggestionStrategy.TOP_N_MATCHES:
            return self._create_top_n_suggestions(matches, n=3)
        elif self.suggestion_strategy == CategorySuggestionStrategy.CONFIDENCE_THRESHOLD:
            return self._create_threshold_suggestions(matches, threshold=0.6)
        else:  # PRIORITY_FILTERED
            return self._create_priority_filtered_suggestions(matches)
    
    def _create_all_match_suggestions(
        self, 
        matches: List[Tuple[Category, CategoryRule, float]]
    ) -> List[TransactionCategoryAssignment]:
        """Create suggestions from all matches"""
        suggestions = []
        
        for category, rule, confidence in matches:
            suggestion = TransactionCategoryAssignment(
                categoryId=category.categoryId,
                confidence=confidence,
                status=CategoryAssignmentStatus.SUGGESTED,
                isManual=False,
                ruleId=getattr(rule, 'rule_id', f"rule_{category.categoryId}")
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _create_top_n_suggestions(
        self, 
        matches: List[Tuple[Category, CategoryRule, float]], 
        n: int = 3
    ) -> List[TransactionCategoryAssignment]:
        """Create suggestions from top N matches"""
        top_matches = matches[:n]
        return self._create_all_match_suggestions(top_matches)
    
    def _create_threshold_suggestions(
        self, 
        matches: List[Tuple[Category, CategoryRule, float]], 
        threshold: float = 0.6
    ) -> List[TransactionCategoryAssignment]:
        """Create suggestions from matches above confidence threshold"""
        filtered_matches = [(cat, rule, conf) for cat, rule, conf in matches if conf >= threshold]
        return self._create_all_match_suggestions(filtered_matches)
    
    def _create_priority_filtered_suggestions(
        self, 
        matches: List[Tuple[Category, CategoryRule, float]]
    ) -> List[TransactionCategoryAssignment]:
        """Create suggestions filtered by rule priority (placeholder implementation)"""
        # For now, just return top 3 matches
        # In future, this could consider rule priority fields
        return self._create_top_n_suggestions(matches, n=3)
    
    def _find_common_words(self, descriptions: List[str]) -> List[str]:
        """Find common words across transaction descriptions"""
        if not descriptions:
            return []
        
        # Simple implementation - find words that appear in all descriptions
        all_words = []
        for desc in descriptions:
            words = desc.lower().split()
            all_words.extend(words)
        
        # Count word frequencies
        word_counts = {}
        for word in all_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Return words sorted by frequency
        common_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in common_words if len(word) >= 3]
    
    def _find_common_prefix(self, descriptions: List[str]) -> str:
        """Find common prefix across transaction descriptions"""
        if not descriptions:
            return ""
        
        if len(descriptions) == 1:
            return descriptions[0][:10] if len(descriptions[0]) >= 10 else descriptions[0]
        
        # Find common prefix
        prefix = descriptions[0]
        for desc in descriptions[1:]:
            while prefix and not desc.startswith(prefix):
                prefix = prefix[:-1]
        
        return prefix.strip() 