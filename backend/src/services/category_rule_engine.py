"""
Category Rule Engine Service

This service handles pattern matching of transactions against category rules,
generates category suggestions with confidence scores, and manages the suggestion workflow.
"""

import logging
from math import log
import re
import uuid
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from enum import Enum
from collections import defaultdict
from datetime import datetime, timezone

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
        limit: int = 100,
        uncategorized_only: bool = False
    ) -> Dict[str, Any]:
        """Test a rule against transactions and return matches with full count information"""
        try:
            logger.info(f"RULE_DEBUG: Testing rule - field: {rule.field_to_match}, condition: {rule.condition}, value: '{rule.value}'")
            
            # For pattern testing, we want to check more transactions to ensure we find matches
            if uncategorized_only:
                # When testing against uncategorized only, get ALL uncategorized transactions using pagination
                transactions = []
                last_evaluated_key = None
                batch_size = 1000
                
                while True:
                    batch, last_evaluated_key, _ = list_user_transactions(
                        user_id, 
                        limit=batch_size,
                        last_evaluated_key=last_evaluated_key,
                        uncategorized_only=True
                    )
                    
                    if not batch:
                        break
                    
                    transactions.extend(batch)
                    logger.info(f"RULE_DEBUG: Retrieved batch of {len(batch)} uncategorized transactions (total so far: {len(transactions)})")
                    
                    if not last_evaluated_key:
                        break
                
                logger.info(f"RULE_DEBUG: Found {len(transactions)} total uncategorized transactions to test against")
            else:
                # For all transactions, use a reasonable search limit to avoid performance issues
                search_limit = max(1000, limit * 10)  # Search at least 1000 transactions or 10x the result limit
                logger.info(f"RULE_DEBUG: Searching through {search_limit} transactions (sample limit: {limit})")
                
                transactions, _, _ = list_user_transactions(user_id, limit=search_limit, uncategorized_only=False)
                logger.info(f"RULE_DEBUG: Found {len(transactions)} total transactions to test against")
            
            # Check if we might be hitting the limit (only relevant when not using pagination)
            if not uncategorized_only and len(transactions) >= search_limit:
                logger.warning(f"RULE_DEBUG: Retrieved {len(transactions)} transactions which equals our search limit of {search_limit}. There may be more transactions that weren't checked!")
            
            # Log some sample transaction descriptions for debugging
            sample_count = min(10, len(transactions))
            if sample_count > 0:
                logger.info(f"RULE_DEBUG: Sample transaction descriptions (first {sample_count}):")
                for i in range(sample_count):
                    tx = transactions[i]
                    desc = getattr(tx, 'description', 'NO_DESCRIPTION')
                    logger.info(f"RULE_DEBUG: Sample {i+1}: '{desc}'")
                
                # Check specifically for SAINSBURYS transactions (for debugging)
                sainsburys_count = 0
                for tx in transactions:
                    desc = getattr(tx, 'description', '')
                    if desc and 'SAINSBURYS' in desc.upper():
                        sainsburys_count += 1
                        if sainsburys_count <= 3:  # Log first 3 SAINSBURYS transactions
                            logger.info(f"RULE_DEBUG: Found SAINSBURYS transaction: '{desc}'")
                
                logger.info(f"RULE_DEBUG: Total SAINSBURYS transactions found: {sainsburys_count}")
            else:
                logger.warning("RULE_DEBUG: No transactions found for user!")
            
            # First pass: count ALL matching transactions and collect time-span info
            total_matches = 0
            sample_transactions = []
            earliest_date = None
            latest_date = None
            
            for i, transaction in enumerate(transactions):
                try:
                    # Track time-span of all transactions scanned
                    if transaction.date:
                        # Convert timestamp (milliseconds since epoch) to datetime
                        tx_date = datetime.fromtimestamp(transaction.date / 1000, timezone.utc)
                        if earliest_date is None or tx_date < earliest_date:
                            earliest_date = tx_date
                        if latest_date is None or tx_date > latest_date:
                            latest_date = tx_date
                    
                    field_value = self._get_transaction_field_value(transaction, rule.field_to_match)
                    logger.debug(f"RULE_DEBUG: Transaction {i+1}: '{field_value}' (ID: {getattr(transaction, 'transaction_id', 'N/A')})")
                    
                    if self.rule_matches_transaction(rule, transaction):
                        total_matches += 1
                        
                        # Only collect sample transactions up to the limit
                        if len(sample_transactions) < limit:
                            logger.info(f"RULE_DEBUG: MATCH found! Transaction {i+1}: '{field_value}' (Sample #{len(sample_transactions)+1})")
                            sample_transactions.append(transaction)
                        elif len(sample_transactions) == limit:
                            logger.info(f"RULE_DEBUG: MATCH found! Transaction {i+1}: '{field_value}' (Not included in sample - sample limit reached)")
                        
                    else:
                        logger.debug(f"RULE_DEBUG: No match for transaction {i+1}")
                        
                except Exception as e:
                    logger.warning(f"RULE_DEBUG: Error processing transaction {i+1}: {str(e)}")
                    continue
            
            logger.info(f"RULE_DEBUG: Rule testing completed: {total_matches} total matches found out of {len(transactions)} transactions (returning {len(sample_transactions)} sample transactions)")
            
            # Format time-span information
            time_span_info = {
                'earliest_date': earliest_date.isoformat() if earliest_date else None,
                'latest_date': latest_date.isoformat() if latest_date else None,
                'days_span': None
            }
            
            if earliest_date and latest_date:
                days_span = (latest_date - earliest_date).days
                time_span_info['days_span'] = days_span
                logger.info(f"RULE_DEBUG: Time span scanned: {days_span} days (from {earliest_date.date()} to {latest_date.date()})")
            
            # Calculate search truncation info
            if uncategorized_only:
                # When using pagination for uncategorized transactions, we checked all of them
                truncated_search = False
                effective_search_limit = len(transactions)  # We got all uncategorized transactions
            else:
                # For all transactions, we may have hit the search limit
                truncated_search = len(transactions) >= search_limit
                effective_search_limit = search_limit
            
            return {
                'total_matches': total_matches,
                'total_transactions_checked': len(transactions),
                'sample_transactions': sample_transactions,
                'sample_limit': limit,
                'truncated_search': truncated_search,
                'search_limit': effective_search_limit,
                'time_span': time_span_info
            }
            
        except Exception as e:
            logger.error(f"RULE_DEBUG: Error testing rule against transactions: {str(e)}")
            return {
                'total_matches': 0,
                'total_transactions_checked': 0,
                'sample_transactions': [],
                'sample_limit': limit,
                'truncated_search': False,
                'search_limit': 0,
                'error': str(e)
            }
    
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
            logger.debug(f"RULE_DEBUG: No field value to match against")
            return False
            
        # Apply case sensitivity
        search_value = field_value if rule.case_sensitive else field_value.lower()
        pattern_value = rule.value if rule.case_sensitive else rule.value.lower()
        
        logger.debug(f"RULE_DEBUG: Matching condition '{rule.condition}' - pattern: '{pattern_value}' against value: '{search_value}'")
        
        try:
            result = False
            if rule.condition == MatchCondition.CONTAINS:
                result = pattern_value in search_value
                logger.debug(f"RULE_DEBUG: CONTAINS check: '{pattern_value}' in '{search_value}' = {result}")
            elif rule.condition == MatchCondition.STARTS_WITH:
                result = search_value.startswith(pattern_value)
                logger.debug(f"RULE_DEBUG: STARTS_WITH check: '{search_value}'.startswith('{pattern_value}') = {result}")
            elif rule.condition == MatchCondition.ENDS_WITH:
                result = search_value.endswith(pattern_value)
                logger.debug(f"RULE_DEBUG: ENDS_WITH check: '{search_value}'.endswith('{pattern_value}') = {result}")
            elif rule.condition == MatchCondition.EQUALS:
                result = search_value == pattern_value
                logger.debug(f"RULE_DEBUG: EQUALS check: '{search_value}' == '{pattern_value}' = {result}")
            elif rule.condition == MatchCondition.REGEX:
                result = self._match_regex_pattern(rule, search_value)
                logger.debug(f"RULE_DEBUG: REGEX check: pattern '{rule.value}' against '{search_value}' = {result}")
            
            logger.debug(f"RULE_DEBUG: Match result: {result}")
            return result
                
        except Exception as e:
            logger.warning(f"RULE_DEBUG: Error matching text condition: {str(e)}")
            
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
    
    def calculate_rule_confidence(self, rule: CategoryRule, transaction: Transaction) -> int:
        """Calculate confidence score for a rule match"""
        base_confidence = rule.confidence
        
        # Adjust confidence based on match type
        confidence_adjustments = {
            MatchCondition.EQUALS: 10,  # Exact matches get bonus
            MatchCondition.REGEX: 5,  # Regex gets slight bonus
            MatchCondition.STARTS_WITH: 2,
            MatchCondition.ENDS_WITH: 2,
            MatchCondition.CONTAINS: 0,  # No adjustment
            MatchCondition.AMOUNT_BETWEEN: 5,  # Amount ranges get bonus
            MatchCondition.AMOUNT_GREATER: 2,
            MatchCondition.AMOUNT_LESS: 2
        }
        
        adjustment = confidence_adjustments.get(rule.condition, 0)
        
        # Adjust based on field being matched
        field_adjustments = {
            'description': 0,  # Base field
            'payee': 5,  # Payee matches are often more reliable
            'memo': -2,  # Memo might be less reliable
            'amount': 3   # Amount matches are quite reliable
        }
        
        field_adjustment = field_adjustments.get(rule.field_to_match, 0)
        
        # Calculate final confidence, ensuring it stays within bounds
        final_confidence = min(100, max(0, int(base_confidence + adjustment + field_adjustment)))
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
        potential_matches: List[Tuple[Category, CategoryRule, int]],
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
            suggestions = self._create_threshold_suggestions(sorted_matches, threshold=60)
        else:  # PRIORITY_FILTERED
            suggestions = self._create_priority_filtered_suggestions(sorted_matches)
        
        logger.info(f"Created {len(suggestions)} category suggestions for transaction {transaction.transaction_id}")
        return suggestions
    
    def _create_suggestions_from_all_matches(
        self, 
        matches: List[Tuple[Category, CategoryRule, int]]
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
        matches: List[Tuple[Category, CategoryRule, int]], 
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
        matches: List[Tuple[Category, CategoryRule, int]], 
        threshold: int = 60
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
        matches: List[Tuple[Category, CategoryRule, int]]
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
                # Apply to specific transactions - get all transactions then filter
                # This is less efficient but necessary for specific transaction IDs
                transactions, _, _ = list_user_transactions(user_id)
                transaction_id_set = set(transaction_ids)
                transactions = [t for t in transactions if str(t.transaction_id) in transaction_id_set]
            else:
                # Apply to all uncategorized transactions using pagination to ensure none are missed
                transactions = []
                last_evaluated_key = None
                batch_size = 1000
                
                while True:
                    batch, last_evaluated_key, _ = list_user_transactions(
                        user_id, 
                        limit=batch_size,
                        last_evaluated_key=last_evaluated_key,
                        uncategorized_only=True
                    )
                    
                    if not batch:
                        break
                    
                    transactions.extend(batch)
                    logger.info(f"Retrieved batch of {len(batch)} uncategorized transactions (total so far: {len(transactions)})")
                    
                    if not last_evaluated_key:
                        break
            
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
    
    def apply_category_rules_for_category(
        self,
        user_id: str,
        category_id: str,
        transaction_ids: Optional[List[str]] = None,
        suggestion_strategy: CategorySuggestionStrategy = CategorySuggestionStrategy.ALL_MATCHES,
        create_suggestions: bool = True
    ) -> Dict[str, int]:
        """Apply rules from a specific category to existing transactions"""
        
        try:
            from utils.db_utils import get_category_by_id_from_db, update_transaction
            from models.transaction import Transaction
            import uuid
            
            # Get the specific category
            category = get_category_by_id_from_db(uuid.UUID(category_id), user_id)
            if not category:
                logger.error(f"Category {category_id} not found for user {user_id}")
                return {'processed': 0, 'categorized': 0, 'errors': 1}
            
            # Get all categories for hierarchy processing
            all_categories = list_categories_by_user_from_db(user_id)
            
            # Get effective rules for this category (including inherited)
            effective_rules = self.get_effective_rules(category, all_categories)
            
            if not effective_rules:
                logger.info(f"No rules found for category {category_id}")
                return {'processed': 0, 'categorized': 0, 'errors': 0}
            
            # Get transactions to process
            if transaction_ids:
                # Get specific transactions - get all transactions then filter
                # This is less efficient but necessary for specific transaction IDs
                transactions, _, _ = list_user_transactions(user_id)
                transaction_id_set = set(transaction_ids)
                transactions = [t for t in transactions if str(t.transaction_id) in transaction_id_set]
            else:
                # Get all uncategorized transactions using pagination to ensure none are missed
                transactions = []
                last_evaluated_key = None
                batch_size = 1000
                
                while True:
                    batch, last_evaluated_key, _ = list_user_transactions(
                        user_id, 
                        limit=batch_size,
                        last_evaluated_key=last_evaluated_key,
                        uncategorized_only=True
                    )
                    
                    if not batch:
                        break
                    
                    transactions.extend(batch)
                    logger.info(f"Retrieved batch of {len(batch)} uncategorized transactions (total so far: {len(transactions)})")
                    
                    if not last_evaluated_key:
                        break
            
            logger.info(f"Processing {len(transactions)} transactions for category {category.name} with {len(effective_rules)} rules")
            
            stats = {
                'processed': 0,
                'categorized': 0,
                'errors': 0,
                'applied_count': 0  # Add this for consistency with handler expectations
            }
            
            for transaction in transactions:
                try:
                    # Check if transaction matches any rule from this category
                    matched_rules = []
                    for rule in effective_rules:
                        if rule.enabled and self.rule_matches_transaction(rule, transaction):
                            matched_rules.append(rule)
                    
                    if matched_rules:
                        # Apply the category to the transaction
                        if create_suggestions:
                            # Create suggestions for manual review
                            for rule in matched_rules:
                                confidence = self.calculate_rule_confidence(rule, transaction)
                                # Add as suggestion to transaction
                                transaction.add_category_suggestion(
                                    category_id=uuid.UUID(category_id),
                                    confidence=confidence,
                                    rule_id=rule.rule_id
                                )
                        else:
                            # Apply category directly
                            transaction.add_manual_category(
                                category_id=uuid.UUID(category_id),
                                set_as_primary=True
                            )
                        logger.info(f"Transaction {transaction} categorized with category {category.name}")
                        # Save updated transaction using db_utils (proper architectural layer)
                        logger.info(f"Saving updated transaction {transaction}")
                        update_transaction(transaction)
                        
                        stats['categorized'] += 1
                        stats['applied_count'] += 1  # Track applied count for handler
                        logger.debug(f"Applied category {category.name} to transaction {transaction.transaction_id}")
                    
                    stats['processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing transaction {transaction.transaction_id}: {str(e)}")
                    stats['errors'] += 1
            
            logger.info(f"Category rule application completed for {category.name}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in category rule application: {str(e)}")
            return {'processed': 0, 'categorized': 0, 'errors': 1, 'applied_count': 0}
    
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