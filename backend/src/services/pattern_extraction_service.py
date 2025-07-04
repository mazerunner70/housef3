"""
Pattern Extraction Service

This service handles intelligent pattern extraction from transaction descriptions,
merchant recognition, and category name suggestions for Phase 4.1.
"""

import logging
import re
import uuid
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from dataclasses import dataclass

from models.category import Category, CategoryRule, MatchCondition
from models.transaction import Transaction

logger = logging.getLogger(__name__)


@dataclass
class PatternSuggestion:
    """Represents a suggested pattern for rule creation"""
    pattern: str
    confidence: float
    match_count: int
    field: str  # 'description', 'payee', 'memo'
    explanation: str
    condition: MatchCondition = MatchCondition.CONTAINS


@dataclass
class CategorySuggestion:
    """Represents a suggested category name and type"""
    name: str
    category_type: str
    suggested_patterns: List[PatternSuggestion]
    confidence: float
    icon: Optional[str] = None


class PatternExtractionService:
    """Service for extracting patterns and suggesting categories from transactions"""
    
    def __init__(self):
        # Merchant-to-category mapping database
        self.merchant_category_mapping = {
            # Food & Dining
            'STARBUCKS': {'category': 'Coffee & Cafes', 'type': 'Expense', 'icon': '☕'},
            'MCDONALDS': {'category': 'Fast Food', 'type': 'Expense', 'icon': '🍔'},
            'AMAZON': {'category': 'Online Shopping', 'type': 'Expense', 'icon': '📦'},
            'WALMART': {'category': 'Groceries', 'type': 'Expense', 'icon': '🛒'},
            'TARGET': {'category': 'Shopping', 'type': 'Expense', 'icon': '🎯'},
            'SHELL': {'category': 'Gas & Fuel', 'type': 'Expense', 'icon': '⛽'},
            'UBER': {'category': 'Rideshare', 'type': 'Expense', 'icon': '🚗'},
        }
    
    def suggest_category_from_transaction(self, transaction: Transaction) -> CategorySuggestion:
        """Suggest a category name and type based on transaction details"""
        try:
            patterns = self.extract_patterns_from_description(transaction.description)
            
            # Try to match against known merchants
            merchant_match = self._find_merchant_match(transaction.description)
            
            if merchant_match:
                category_info = self.merchant_category_mapping[merchant_match]
                return CategorySuggestion(
                    name=category_info['category'],
                    category_type=category_info['type'],
                    suggested_patterns=patterns,
                    confidence=0.9,
                    icon=category_info.get('icon')
                )
            else:
                suggested_name = self._generate_category_name_from_patterns(patterns, transaction)
                return CategorySuggestion(
                    name=suggested_name,
                    category_type='Expense',
                    suggested_patterns=patterns,
                    confidence=0.7,
                    icon='📁'
                )
                
        except Exception as e:
            logger.error(f"Error suggesting category from transaction: {str(e)}")
            return CategorySuggestion(
                name='Uncategorized',
                category_type='Expense',
                suggested_patterns=[],
                confidence=0.1
            )
    
    def extract_patterns_from_description(self, description: str) -> List[PatternSuggestion]:
        """Extract multiple pattern suggestions from a transaction description"""
        patterns = []
        
        # Clean and normalize description
        cleaned = self._clean_description(description)
        
        # Extract potential merchant name
        merchant_name = self._extract_merchant_name(cleaned)
        if merchant_name:
            patterns.append(PatternSuggestion(
                pattern=merchant_name,
                confidence=0.9,
                match_count=1,
                field='description',
                explanation=f"Extracted merchant name: '{merchant_name}'",
                condition=MatchCondition.CONTAINS
            ))
        
        return patterns
    
    def create_category_with_rule(
        self, 
        category_name: str, 
        category_type: str, 
        pattern: str, 
        field_to_match: str = 'description',
        condition: MatchCondition = MatchCondition.CONTAINS
    ) -> Dict[str, Any]:
        """Create category data structure with pre-populated rule"""
        try:
            category_id = str(uuid.uuid4())
            rule_id = f"rule_{uuid.uuid4().hex[:8]}"
            
            rule_data = {
                "ruleId": rule_id,
                "fieldToMatch": field_to_match,
                "condition": condition.value,
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
                "type": category_type,
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
    
    def _find_merchant_match(self, description: str) -> Optional[str]:
        """Find if description matches any known merchant"""
        upper_desc = description.upper()
        for merchant in self.merchant_category_mapping.keys():
            if merchant in upper_desc:
                return merchant
        return None
    
    def _clean_description(self, description: str) -> str:
        """Clean transaction description for pattern extraction"""
        return description.upper().strip()
    
    def _extract_merchant_name(self, cleaned_description: str) -> Optional[str]:
        """Extract the most likely merchant name from cleaned description"""
        words = cleaned_description.split()
        if not words:
            return None
        
        merchant_words = []
        for word in words:
            if len(word) >= 3 and not word.isdigit():
                merchant_words.append(word)
            elif merchant_words:
                break
        
        if merchant_words:
            return ' '.join(merchant_words[:2])
        
        return None
    
    def _generate_category_name_from_patterns(
        self, 
        patterns: List[PatternSuggestion], 
        transaction: Transaction
    ) -> str:
        """Generate a category name based on extracted patterns"""
        if not patterns:
            return 'Uncategorized'
        
        primary_pattern = patterns[0].pattern
        return primary_pattern.title()
    
    def _suggest_icon_for_category(self, category_name: str) -> str:
        """Suggest an appropriate icon for a category"""
        name_lower = category_name.lower()
        
        icon_mapping = {
            'food': '🍽️', 'coffee': '☕', 'gas': '⛽', 'shopping': '🛍️',
            'amazon': '📦', 'medical': '🏥', 'bank': '🏦', 'income': '💰'
        }
        
        for keyword, icon in icon_mapping.items():
            if keyword in name_lower:
                return icon
        
        return '📁'
    
    def _suggest_color_for_category(self, category_name: str) -> str:
        """Suggest an appropriate color for a category"""
        return '#74B9FF'  # Default blue 