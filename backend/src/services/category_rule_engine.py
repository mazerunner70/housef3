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
from collections import defaultdict

from models.category import Category, CategoryRule, MatchCondition, CategoryHierarchy, CategorySuggestionStrategy
from models.transaction import Transaction, TransactionCategoryAssignment, CategoryAssignmentStatus
from utils.db_utils import list_categories_by_user_from_db, list_user_transactions

logger = logging.getLogger(__name__)


class CategoryRuleEngine:
    """Enhanced rule engine for category matching and suggestion generation"""
    
    def __init__(self):
        self.compiled_patterns = {}  # Cache compiled regex patterns
        self.category_hierarchies = {}  # Cache category hierarchies
        
    def test_rule_against_transactions(
        self, 
        user_id: str, 
        rule: CategoryRule, 
        limit: int = 100
    ) -> List[Transaction]:
        """Test a rule against transactions and return matches"""
        try:
            # Get transactions for the user
            transactions, _, _ = list_user_transactions(user_id, limit=limit * 2)  # Get more to account for filtering
            
            matching_transactions = []
            for transaction in transactions:
                if self.rule_matches_transaction(rule, transaction):
                    matching_transactions.append(transaction)
                    if len(matching_transactions) >= limit:
                        break
            
            logger.info(f"Rule testing: {len(matching_transactions)} matches found out of {len(transactions)} transactions")
            return matching_transactions
            
        except Exception as e:
            logger.error(f"Error testing rule against transactions: {str(e)}")
            return []
    
    def rule_matches_transaction(self, rule: CategoryRule, transaction: Transaction) -> bool:
        """Check if a single rule matches a transaction"""
        if not rule.enabled:
            return False
            
        # Get the field value to match against
        field_value = self._get_transaction_field_value(transaction, rule.field_to_match)
        if field_value is None:
            return False
            
        # Handle amount-based conditions
        if rule.condition in [MatchCondition.AMOUNT_GREATER, MatchCondition.AMOUNT_LESS, MatchCondition.AMOUNT_BETWEEN]:
            return self._match_amount_condition(rule, transaction.amount)
        
        # Handle text-based conditions
        return self._match_text_condition(rule, field_value)
    
    def _get_transaction_field_value(self, transaction: Transaction, field_name: str) -> Optional[str]:
        """Extract the field value from transaction for matching"""
        field_mapping = {
            'description': transaction.description,
            'payee': getattr(transaction, 'payee', None),
            'memo': getattr(transaction, 'memo', None),
            'amount': str(transaction.amount)
        }
        return field_mapping.get(field_name)
    
    def _match_amount_condition(self, rule: CategoryRule, amount: Decimal) -> bool:
        """Match amount-based conditions"""
        try:
            amount_value = Decimal(str(amount))
            
            if rule.condition == MatchCondition.AMOUNT_GREATER:
                return rule.amount_min is not None and amount_value > rule.amount_min
            elif rule.condition == MatchCondition.AMOUNT_LESS:
                return rule.amount_max is not None and amount_value < rule.amount_max
            elif rule.condition == MatchCondition.AMOUNT_BETWEEN:
                return (rule.amount_min is not None and rule.amount_max is not None and 
                        rule.amount_min <= amount_value <= rule.amount_max)
            
        except (ValueError, TypeError):
            logger.warning(f"Invalid amount value for comparison: {amount}")
            
        return False
    
    def _match_text_condition(self, rule: CategoryRule, field_value: str) -> bool:
        """Match text-based conditions"""
        if not field_value:
            return False
            
        # Apply case sensitivity
        search_value = field_value if rule.case_sensitive else field_value.lower()
        pattern_value = rule.value if rule.case_sensitive else rule.value.lower()
        
        try:
            if rule.condition == MatchCondition.CONTAINS:
                return pattern_value in search_value
            elif rule.condition == MatchCondition.STARTS_WITH:
                return search_value.startswith(pattern_value)
            elif rule.condition == MatchCondition.ENDS_WITH:
                return search_value.endswith(pattern_value)
            elif rule.condition == MatchCondition.EQUALS:
                return search_value == pattern_value
            elif rule.condition == MatchCondition.REGEX:
                return self._match_regex_pattern(rule, search_value)
                
        except Exception as e:
            logger.warning(f"Error matching text condition: {str(e)}")
            
        return False
    
    def _match_regex_pattern(self, rule: CategoryRule, field_value: str) -> bool:
        """Match regex pattern with caching"""
        try:
            # Use cached compiled pattern if available
            pattern_key = f"{rule.rule_id}_{rule.case_sensitive}"
            if pattern_key not in self.compiled_patterns:
                flags = 0 if rule.case_sensitive else re.IGNORECASE
                self.compiled_patterns[pattern_key] = re.compile(rule.value, flags)
            
            pattern = self.compiled_patterns[pattern_key]
            return bool(pattern.search(field_value))
            
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{rule.value}': {str(e)}")
            return False
    
    def calculate_rule_confidence(self, rule: CategoryRule, transaction: Transaction) -> float:
        """Calculate confidence score for a rule match"""
        base_confidence = rule.confidence
        
        # Adjust confidence based on match type
        confidence_adjustments = {
            MatchCondition.EQUALS: 0.1,  # Exact matches get bonus
            MatchCondition.REGEX: 0.05,  # Regex gets slight bonus
            MatchCondition.STARTS_WITH: 0.02,
            MatchCondition.ENDS_WITH: 0.02,
            MatchCondition.CONTAINS: 0.0,  # No adjustment
            MatchCondition.AMOUNT_BETWEEN: 0.05,  # Amount ranges get bonus
            MatchCondition.AMOUNT_GREATER: 0.02,
            MatchCondition.AMOUNT_LESS: 0.02
        }
        
        adjustment = confidence_adjustments.get(rule.condition, 0.0)
        
        # Adjust based on field being matched
        field_adjustments = {
            'description': 0.0,  # Base field
            'payee': 0.05,  # Payee matches are often more reliable
            'memo': -0.02,  # Memo might be less reliable
            'amount': 0.03   # Amount matches are quite reliable
        }
        
        field_adjustment = field_adjustments.get(rule.field_to_match, 0.0)
        
        # Calculate final confidence, ensuring it stays within bounds
        final_confidence = min(1.0, max(0.0, base_confidence + adjustment + field_adjustment))
        return final_confidence
    
    def categorize_transaction(
        self,
        transaction: Transaction,
        user_categories: List[Category],
        suggestion_strategy: CategorySuggestionStrategy = CategorySuggestionStrategy.ALL_MATCHES
    ) -> List[TransactionCategoryAssignment]:
        """Categorize a single transaction, returning matching categories as suggestions"""
        
        potential_matches = []
        
        # Build category hierarchy for inheritance
        hierarchy_dict = self.build_category_hierarchy(user_categories)
        
        # Test each category against the transaction
        for category in user_categories:
            effective_rules = self.get_effective_rules(category, user_categories, hierarchy_dict)
            
            for rule in effective_rules:
                if not rule.auto_suggest:
                    continue
                    
                if self.rule_matches_transaction(rule, transaction):
                    confidence = self.calculate_rule_confidence(rule, transaction)
                    potential_matches.append((category, rule, confidence))
                    
                    # If multiple matches not allowed, use first match
                    if not rule.allow_multiple_matches:
                        break
        
        # Create suggestions based on strategy
        return self.create_category_suggestions(
            transaction, potential_matches, suggestion_strategy
        )
    
    def create_category_suggestions(
        self,
        transaction: Transaction,
        potential_matches: List[Tuple[Category, CategoryRule, float]],
        strategy: CategorySuggestionStrategy = CategorySuggestionStrategy.ALL_MATCHES
    ) -> List[TransactionCategoryAssignment]:
        """Create category suggestions based on strategy"""
        
        if not potential_matches:
            return []
        
        # Sort matches by confidence (highest first), then by rule priority
        sorted_matches = sorted(
            potential_matches, 
            key=lambda x: (x[2], x[1].priority), 
            reverse=True
        )
        
        suggestions = []
        
        if strategy == CategorySuggestionStrategy.ALL_MATCHES:
            suggestions = self._create_suggestions_from_all_matches(sorted_matches)
        elif strategy == CategorySuggestionStrategy.TOP_N_MATCHES:
            suggestions = self._create_top_n_suggestions(sorted_matches, n=3)
        elif strategy == CategorySuggestionStrategy.CONFIDENCE_THRESHOLD:
            suggestions = self._create_threshold_suggestions(sorted_matches, threshold=0.6)
        else:  # PRIORITY_FILTERED
            suggestions = self._create_priority_filtered_suggestions(sorted_matches)
        
        logger.info(f"Created {len(suggestions)} category suggestions for transaction {transaction.transaction_id}")
        return suggestions
    
    def _create_suggestions_from_all_matches(
        self, 
        matches: List[Tuple[Category, CategoryRule, float]]
    ) -> List[TransactionCategoryAssignment]:
        """Create suggestions from all matches"""
        suggestions = []
        seen_categories = set()
        
        for category, rule, confidence in matches:
            if category.categoryId not in seen_categories:
                suggestion = TransactionCategoryAssignment(
                    categoryId=category.categoryId,
                    confidence=confidence,
                    status=CategoryAssignmentStatus.SUGGESTED,
                    isManual=False,
                    ruleId=rule.rule_id
                )
                suggestions.append(suggestion)
                seen_categories.add(category.categoryId)
        
        return suggestions
    
    def _create_top_n_suggestions(
        self, 
        matches: List[Tuple[Category, CategoryRule, float]], 
        n: int = 3
    ) -> List[TransactionCategoryAssignment]:
        """Create suggestions from top N highest confidence matches"""
        suggestions = []
        seen_categories = set()
        
        for category, rule, confidence in matches[:n]:
            if category.categoryId not in seen_categories:
                suggestion = TransactionCategoryAssignment(
                    categoryId=category.categoryId,
                    confidence=confidence,
                    status=CategoryAssignmentStatus.SUGGESTED,
                    isManual=False,
                    ruleId=rule.rule_id
                )
                suggestions.append(suggestion)
                seen_categories.add(category.categoryId)
        
        return suggestions
    
    def _create_threshold_suggestions(
        self, 
        matches: List[Tuple[Category, CategoryRule, float]], 
        threshold: float = 0.6
    ) -> List[TransactionCategoryAssignment]:
        """Create suggestions only above confidence threshold"""
        suggestions = []
        seen_categories = set()
        
        for category, rule, confidence in matches:
            if confidence >= threshold and category.categoryId not in seen_categories:
                suggestion = TransactionCategoryAssignment(
                    categoryId=category.categoryId,
                    confidence=confidence,
                    status=CategoryAssignmentStatus.SUGGESTED,
                    isManual=False,
                    ruleId=rule.rule_id
                )
                suggestions.append(suggestion)
                seen_categories.add(category.categoryId)
        
        return suggestions
    
    def _create_priority_filtered_suggestions(
        self, 
        matches: List[Tuple[Category, CategoryRule, float]]
    ) -> List[TransactionCategoryAssignment]:
        """Create suggestions filtered by rule priority"""
        if not matches:
            return []
        
        # Find the highest priority
        max_priority = max(rule.priority for _, rule, _ in matches)
        
        suggestions = []
        seen_categories = set()
        
        # Only include matches with the highest priority
        for category, rule, confidence in matches:
            if rule.priority == max_priority and category.categoryId not in seen_categories:
                suggestion = TransactionCategoryAssignment(
                    categoryId=category.categoryId,
                    confidence=confidence,
                    status=CategoryAssignmentStatus.SUGGESTED,
                    isManual=False,
                    ruleId=rule.rule_id
                )
                suggestions.append(suggestion)
                seen_categories.add(category.categoryId)
        
        return suggestions
    
    def get_effective_rules(
        self,
        category: Category,
        all_categories: List[Category],
        hierarchy_dict: Optional[Dict[str, CategoryHierarchy]] = None
    ) -> List[CategoryRule]:
        """Get all effective rules for a category including inherited ones"""
        
        if hierarchy_dict is None:
            hierarchy_dict = self.build_category_hierarchy(all_categories)
        
        effective_rules = list(category.rules)  # Start with category's own rules
        
        # Add inherited rules if inheritance is enabled
        if category.inherit_parent_rules and category.parentCategoryId:
            parent_id = str(category.parentCategoryId)
            if parent_id in hierarchy_dict:
                parent_hierarchy = hierarchy_dict[parent_id]
                
                if category.rule_inheritance_mode == "additive":
                    # Add parent rules to existing rules
                    effective_rules.extend(parent_hierarchy.inherited_rules)
                elif category.rule_inheritance_mode == "override":
                    # Replace own rules with parent rules
                    effective_rules = list(parent_hierarchy.inherited_rules)
                # "disabled" mode uses only own rules (no change needed)
        
        # Sort by priority (highest first)
        effective_rules.sort(key=lambda rule: rule.priority, reverse=True)
        
        return effective_rules
    
    def build_category_hierarchy(
        self,
        categories: List[Category]
    ) -> Dict[str, CategoryHierarchy]:
        """Build hierarchical structure from flat category list"""
        
        hierarchy_dict = {}
        category_dict = {str(cat.categoryId): cat for cat in categories}
        
        # First pass: create hierarchy nodes
        for category in categories:
            hierarchy_dict[str(category.categoryId)] = CategoryHierarchy(
                category=category,
                children=[],
                depth=0,
                full_path=category.name,
                inherited_rules=[]  # Start empty - only actual inherited rules from parents go here
            )
        
        # Second pass: build parent-child relationships and calculate paths
        for category in categories:
            cat_id = str(category.categoryId)
            if category.parentCategoryId:
                parent_id = str(category.parentCategoryId)
                if parent_id in hierarchy_dict:
                    # Add to parent's children
                    hierarchy_dict[parent_id].children.append(hierarchy_dict[cat_id])
                    
                    # Calculate depth and full path
                    parent_hierarchy = hierarchy_dict[parent_id]
                    hierarchy_dict[cat_id].depth = parent_hierarchy.depth + 1
                    hierarchy_dict[cat_id].full_path = f"{parent_hierarchy.full_path} > {category.name}"
                    
                    # Inherit rules from parent
                    if category.inherit_parent_rules:
                        # Combine parent's own rules with parent's inherited rules
                        all_parent_rules = list(parent_hierarchy.category.rules) + list(parent_hierarchy.inherited_rules)
                        if category.rule_inheritance_mode == "additive":
                            hierarchy_dict[cat_id].inherited_rules.extend(all_parent_rules)
                        elif category.rule_inheritance_mode == "override":
                            hierarchy_dict[cat_id].inherited_rules = all_parent_rules
        
        return hierarchy_dict
    
    def apply_category_rules_bulk(
        self, 
        user_id: str, 
        transaction_ids: Optional[List[str]] = None,
        suggestion_strategy: CategorySuggestionStrategy = CategorySuggestionStrategy.ALL_MATCHES
    ) -> Dict[str, int]:
        """Apply all category rules to transactions and create suggestions for review"""
        
        try:
            # Get user's categories and transactions
            categories = list_categories_by_user_from_db(user_id)
            
            if transaction_ids:
                # Apply to specific transactions (would need additional implementation)
                # For now, get all user transactions
                transactions, _, _ = list_user_transactions(user_id)
                # Filter by transaction_ids if provided
                if transaction_ids:
                    transaction_id_set = set(transaction_ids)
                    transactions = [t for t in transactions if str(t.transaction_id) in transaction_id_set]
            else:
                # Apply to all user transactions
                transactions, _, _ = list_user_transactions(user_id)
            
            stats = {
                'processed': 0,
                'suggestions_created': 0,
                'errors': 0
            }
            
            for transaction in transactions:
                try:
                    suggestions = self.categorize_transaction(
                        transaction, categories, suggestion_strategy
                    )
                    
                    # Here you would save the suggestions to the database
                    # This would be implemented in the actual handler
                    stats['suggestions_created'] += len(suggestions)
                    stats['processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing transaction {transaction.transaction_id}: {str(e)}")
                    stats['errors'] += 1
            
            logger.info(f"Bulk rule application completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in bulk rule application: {str(e)}")
            return {'processed': 0, 'suggestions_created': 0, 'errors': 1}
    
    def generate_pattern_from_descriptions(
        self, 
        descriptions: List[str],
        pattern_type: str = "contains"
    ) -> Dict[str, Any]:
        """Generate patterns from sample transaction descriptions"""
        
        if not descriptions:
            return {'pattern': '', 'confidence': 0.0}
        
        if pattern_type == "contains":
            return self._generate_contains_pattern(descriptions)
        elif pattern_type == "regex":
            return self._generate_regex_pattern(descriptions)
        else:
            return self._generate_contains_pattern(descriptions)
    
    def _generate_contains_pattern(self, descriptions: List[str]) -> Dict[str, Any]:
        """Generate a simple 'contains' pattern from descriptions"""
        
        # Find common words/substrings
        if len(descriptions) == 1:
            # Single description - use the whole thing
            pattern = descriptions[0].strip()
            return {'pattern': pattern, 'confidence': 0.9}
        
        # Multiple descriptions - find common substrings
        common_words = set(descriptions[0].upper().split())
        for desc in descriptions[1:]:
            desc_words = set(desc.upper().split())
            common_words &= desc_words
        
        if common_words:
            # Use the longest common word
            pattern = max(common_words, key=len)
            confidence = min(0.95, 0.5 + (len(common_words) * 0.1))
            return {'pattern': pattern, 'confidence': confidence}
        
        # Find common substring
        common_substring = self._find_longest_common_substring(descriptions)
        if len(common_substring) >= 3:
            return {'pattern': common_substring, 'confidence': 0.7}
        
        # Fallback to first word of first description
        first_word = descriptions[0].split()[0] if descriptions[0].split() else descriptions[0]
        return {'pattern': first_word, 'confidence': 0.4}
    
    def _generate_regex_pattern(self, descriptions: List[str]) -> Dict[str, Any]:
        """Generate a regex pattern from descriptions (basic implementation)"""
        
        if len(descriptions) == 1:
            # Single description - escape and make it a contains pattern
            escaped = re.escape(descriptions[0])
            return {'pattern': f".*{escaped}.*", 'confidence': 0.8}
        
        # Multiple descriptions - find pattern
        # This is a simplified implementation
        common_pattern = self._generate_contains_pattern(descriptions)
        if common_pattern['pattern']:
            escaped = re.escape(common_pattern['pattern'])
            return {'pattern': f".*{escaped}.*", 'confidence': common_pattern['confidence'] * 0.9}
        
        return {'pattern': '', 'confidence': 0.0}
    
    def _find_longest_common_substring(self, descriptions: List[str]) -> str:
        """Find the longest common substring among descriptions"""
        
        if not descriptions:
            return ""
        
        if len(descriptions) == 1:
            return descriptions[0]
        
        # Start with first description
        common = descriptions[0].upper()
        
        for desc in descriptions[1:]:
            desc_upper = desc.upper()
            new_common = ""
            
            # Find longest common substring
            for i in range(len(common)):
                for j in range(i + 1, len(common) + 1):
                    substring = common[i:j]
                    if substring in desc_upper and len(substring) > len(new_common):
                        new_common = substring
            
            common = new_common
            if not common:
                break
        
        return common.strip()
    
    def validate_regex_pattern(self, pattern: str) -> Dict[str, Any]:
        """Validate a regex pattern and return validation results"""
        
        try:
            re.compile(pattern)
            return {
                'valid': True,
                'message': 'Valid regex pattern',
                'suggestions': []
            }
        except re.error as e:
            return {
                'valid': False,
                'message': f'Invalid regex pattern: {str(e)}',
                'suggestions': self._get_regex_suggestions(pattern, str(e))
            }
    
    def _get_regex_suggestions(self, pattern: str, error_msg: str) -> List[str]:
        """Provide suggestions for fixing common regex errors"""
        
        suggestions = []
        
        # Common regex fixes
        if "Unbalanced parenthesis" in error_msg or "unbalanced parenthesis" in error_msg:
            suggestions.append("Check that all opening parentheses '(' have matching closing ')' parentheses")
        
        if "Invalid character range" in error_msg:
            suggestions.append("Check character ranges in square brackets, e.g., [a-z] not [z-a]")
        
        if "Nothing to repeat" in error_msg:
            suggestions.append("Remove quantifiers (*,+,?) that don't follow a character or group")
        
        # Special characters that need escaping
        special_chars = set("()[]{}*+?.^$|\\")
        unescaped_special = [char for char in pattern if char in special_chars and f"\\{char}" not in pattern]
        
        if unescaped_special:
            suggestions.append(f"Consider escaping special characters: {', '.join(unescaped_special)}")
        
        if not suggestions:
            suggestions.append("Try a simpler pattern or use 'contains' matching instead of regex")
        
        return suggestions 