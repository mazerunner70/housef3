#!/usr/bin/env python3
"""
Simple test script to debug pattern generation for SAINSBURYS transaction
"""

import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.pattern_extraction_service import PatternExtractionService

def test_sainsburys_pattern():
    """Test pattern generation for SAINSBURYS transaction"""
    
    print("=== SAINSBURYS Pattern Generation Debug ===")
    
    # Test description from the user
    test_description = "SAINSBURYS S/MKTS ON 19 JUN CPM"
    print(f"Input description: '{test_description}'")
    print()
    
    # Initialize pattern extraction service
    extractor = PatternExtractionService()
    
    # Generate patterns
    print("Generating patterns...")
    patterns = extractor.generate_patterns_from_description(test_description)
    
    print(f"Generated {len(patterns)} patterns:")
    print()
    
    for i, pattern in enumerate(patterns, 1):
        print(f"Pattern {i}:")
        print(f"  - Pattern: '{pattern.pattern}'")
        print(f"  - Type: {pattern.pattern_type}")
        print(f"  - Condition: {pattern.condition}")
        print(f"  - Field: {pattern.field}")
        print(f"  - Confidence: {pattern.confidence}%")
        print(f"  - Explanation: {pattern.explanation}")
        print()
    
    # Test specific pattern types
    print("=== Testing Individual Pattern Methods ===")
    print()
    
    normalized = test_description.upper()
    print(f"Normalized: '{normalized}'")
    print()
    
    # Test prefix pattern
    prefix_pattern = extractor._extract_prefix_pattern(normalized)
    if prefix_pattern:
        print(f"Prefix pattern: '{prefix_pattern.pattern}' (condition: {prefix_pattern.condition})")
    else:
        print("No prefix pattern generated")
    
    # Test keywords
    keywords = extractor._extract_keywords(normalized)
    print(f"Keywords: {keywords}")
    
    # Test merchant detection
    merchant_info = extractor.extract_merchant_from_description(test_description)
    if merchant_info:
        print(f"Merchant detected: {merchant_info.name} with patterns: {merchant_info.common_patterns}")
    else:
        print("No merchant detected")
    
    print()
    print("=== Testing Rule Matching Logic ===")
    
    # Test how the rule engine would match these patterns
    from services.category_rule_engine import CategoryRuleEngine
    from models.category import CategoryRule, MatchCondition
    
    rule_engine = CategoryRuleEngine()
    
    for pattern in patterns:
        print(f"\nTesting pattern: '{pattern.pattern}' with condition: {pattern.condition}")
        
        # Create a test rule
        test_rule = CategoryRule(
            ruleId="test",
            fieldToMatch=pattern.field,
            condition=pattern.condition,
            value=pattern.pattern,
            caseSensitive=False,
            priority=0,
            enabled=True,
            confidence=100,
            allowMultipleMatches=True,
            autoSuggest=True
        )
        
        # Test against our original description
        result = rule_engine._match_text_condition(test_rule, test_description)
        print(f"  Match result: {result}")
        
        # Also test the normalized version
        result_normalized = rule_engine._match_text_condition(test_rule, normalized)
        print(f"  Match result (normalized): {result_normalized}")

if __name__ == "__main__":
    test_sainsburys_pattern() 