"""
Test for Category model enum conversion and serialization.

This test verifies that Category models properly handle enum conversion
for CategoryType and MatchCondition fields.
"""
import uuid
from decimal import Decimal
from typing import Dict, Any

import pytest

from models.category import Category, CategoryType, MatchCondition, CategoryRule


def create_mock_category_data() -> Dict[str, Any]:
    """Create mock category data with string enum values."""
    return {
        'userId': 'd6d21224-5041-704e-9705-0e9a48538059',
        'name': 'Groceries',
        'type': 'EXPENSE',  # String value
        'categoryId': str(uuid.uuid4()),
        'icon': '🛒',
        'color': '#4CAF50',
        'rules': [],
        'createdAt': 1749992863526,
        'updatedAt': 1749992863526
    }


def create_mock_category_rule_data() -> Dict[str, Any]:
    """Create mock category rule data with string enum values."""
    return {
        'ruleId': 'rule_test123',
        'fieldToMatch': 'description',
        'condition': 'contains',  # String value
        'value': 'WALMART',
        'caseSensitive': False,
        'priority': 50,
        'enabled': True,
        'confidence': 90,
        'allowMultipleMatches': True,
        'autoSuggest': True
    }


class TestCategoryEnumConversion:
    """Test Category enum conversion."""

    def test_category_preserves_category_type_enum(self):
        """
        Test that Category preserves CategoryType enum objects.
        
        This test verifies that:
        1. CategoryType enum objects are preserved (not converted to strings)
        2. .value attribute access works without AttributeError
        3. Enum type checking works correctly
        """
        # Arrange: Create category with enum
        category = Category(
            userId='test-user',
            name='Test Category',
            type=CategoryType.EXPENSE  # Enum object
        )
        
        # Assert: CategoryType should be an actual enum object, not a string
        assert category.type is not None, "CategoryType should not be None"
        assert isinstance(category.type, CategoryType), \
            f"Expected CategoryType enum, got {type(category.type)}"
        
        # Critical test: .value attribute should work without AttributeError
        try:
            type_value = category.type.value
            assert type_value == 'EXPENSE', f"Expected 'EXPENSE', got {type_value}"
        except AttributeError as e:
            pytest.fail(f"CategoryType enum should have .value attribute: {e}")
        
        # Use type checking for string-based enums
        assert type(category.type).__name__ == 'CategoryType', \
            f"Expected CategoryType type, got {type(category.type).__name__}"

    def test_category_from_dict_with_string_enum(self):
        """
        Test that Category can be created from dict with string enum values.
        
        This simulates deserialization from DynamoDB or API.
        """
        # Arrange: Mock data with string enum value
        category_data = create_mock_category_data()
        
        # Act: Create category using model_validate
        category = Category.model_validate(category_data)
        
        # Assert: CategoryType should be converted to enum object
        assert isinstance(category.type, CategoryType), \
            f"Expected CategoryType enum, got {type(category.type)}"
        assert category.type == CategoryType.EXPENSE
        
        # Critical test: .value attribute should work
        try:
            type_value = category.type.value
            assert type_value == 'EXPENSE'
        except AttributeError as e:
            pytest.fail(f"CategoryType enum should have .value attribute: {e}")

    def test_category_rule_preserves_match_condition_enum(self):
        """
        Test that CategoryRule preserves MatchCondition enum objects.
        """
        # Arrange: Create rule with enum
        rule = CategoryRule(
            fieldToMatch='description',
            condition=MatchCondition.CONTAINS,  # Enum object
            value='TEST'
        )
        
        # Assert: MatchCondition should be an actual enum object
        assert isinstance(rule.condition, MatchCondition), \
            f"Expected MatchCondition enum, got {type(rule.condition)}"
        
        # Critical test: .value attribute should work without AttributeError
        try:
            condition_value = rule.condition.value
            assert condition_value == 'contains', f"Expected 'contains', got {condition_value}"
        except AttributeError as e:
            pytest.fail(f"MatchCondition enum should have .value attribute: {e}")

    def test_category_rule_from_dict_with_string_enum(self):
        """
        Test that CategoryRule can be created from dict with string enum values.
        """
        # Arrange: Mock data with string enum value
        rule_data = create_mock_category_rule_data()
        
        # Act: Create rule using model_validate
        rule = CategoryRule.model_validate(rule_data)
        
        # Assert: MatchCondition should be converted to enum object
        assert isinstance(rule.condition, MatchCondition), \
            f"Expected MatchCondition enum, got {type(rule.condition)}"
        assert rule.condition == MatchCondition.CONTAINS
        
        # Critical test: .value attribute should work
        try:
            condition_value = rule.condition.value
            assert condition_value == 'contains'
        except AttributeError as e:
            pytest.fail(f"MatchCondition enum should have .value attribute: {e}")

    def test_category_with_rules_roundtrip_serialization(self):
        """
        Test that Category with rules can be serialized and deserialized.
        """
        # Arrange: Create category with rules
        original_category = Category(
            userId='test-user',
            name='Dining',
            type=CategoryType.EXPENSE,
            rules=[
                CategoryRule(
                    fieldToMatch='description',
                    condition=MatchCondition.CONTAINS,
                    value='RESTAURANT'
                ),
                CategoryRule(
                    fieldToMatch='amount',
                    condition=MatchCondition.AMOUNT_BETWEEN,
                    value='0',
                    amountMin=Decimal('10.00'),
                    amountMax=Decimal('100.00')
                )
            ]
        )
        
        # Act: Serialize to dict (simulating DynamoDB)
        serialized = original_category.model_dump(by_alias=True, mode='json')
        
        # Assert: Enums should be serialized as strings
        assert isinstance(serialized['type'], str), \
            "Serialized type should be string"
        assert serialized['type'] == 'EXPENSE'
        assert isinstance(serialized['rules'][0]['condition'], str), \
            "Serialized condition should be string"
        assert serialized['rules'][0]['condition'] == 'contains'
        
        # Act: Deserialize back
        deserialized_category = Category.model_validate(serialized)
        
        # Assert: Enums should be restored
        assert isinstance(deserialized_category.type, CategoryType), \
            "Deserialized type should be CategoryType enum"
        assert deserialized_category.type == CategoryType.EXPENSE
        assert isinstance(deserialized_category.rules[0].condition, MatchCondition), \
            "Deserialized condition should be MatchCondition enum"
        assert deserialized_category.rules[0].condition == MatchCondition.CONTAINS

    def test_all_category_types(self):
        """Test that all CategoryType enum values work correctly."""
        category_types = [
            CategoryType.INCOME,
            CategoryType.EXPENSE,
            CategoryType.TRANSFER
        ]
        
        for category_type in category_types:
            # Arrange: Create category with specific type
            category = Category(
                userId='test-user',
                name=f'Test {category_type.value}',
                type=category_type
            )
            
            # Assert: Enum is preserved
            assert isinstance(category.type, CategoryType)
            assert category.type == category_type
            
            # Act: Serialize and deserialize
            serialized = category.model_dump(by_alias=True, mode='json')
            deserialized = Category.model_validate(serialized)
            
            # Assert: Enum is preserved after roundtrip
            assert isinstance(deserialized.type, CategoryType)
            assert deserialized.type == category_type

    def test_all_match_conditions(self):
        """Test that all MatchCondition enum values work correctly."""
        match_conditions = [
            MatchCondition.CONTAINS,
            MatchCondition.STARTS_WITH,
            MatchCondition.ENDS_WITH,
            MatchCondition.EQUALS,
            MatchCondition.REGEX,
            MatchCondition.AMOUNT_GREATER,
            MatchCondition.AMOUNT_LESS,
            MatchCondition.AMOUNT_BETWEEN
        ]
        
        for condition in match_conditions:
            # Arrange: Create rule with specific condition
            rule = CategoryRule(
                fieldToMatch='description',
                condition=condition,
                value='TEST'
            )
            
            # Assert: Enum is preserved
            assert isinstance(rule.condition, MatchCondition)
            assert rule.condition == condition
            
            # Act: Serialize and deserialize
            serialized = rule.model_dump(by_alias=True, mode='json')
            deserialized = CategoryRule.model_validate(serialized)
            
            # Assert: Enum is preserved after roundtrip
            assert isinstance(deserialized.condition, MatchCondition)
            assert deserialized.condition == condition

    def test_category_model_dump_preserves_enum_without_json_mode(self):
        """
        Test model_dump() without mode='json' to understand current behavior.
        
        With use_enum_values=True, this returns string values.
        Without use_enum_values=True, this returns enum objects.
        """
        # Arrange: Create category
        category = Category(
            userId='test-user',
            name='Test',
            type=CategoryType.INCOME
        )
        
        # Act: Dump without mode='json'
        dumped = category.model_dump(by_alias=True)
        
        # Assert: Check what type we get
        # With use_enum_values=True: dumped['type'] will be 'INCOME' (string)
        # Without use_enum_values=True: dumped['type'] will be CategoryType.INCOME (enum)
        # This test documents the current behavior
        type_in_dump = dumped['type']
        print(f"Type in dump: {type_in_dump}, isinstance str: {isinstance(type_in_dump, str)}, "
              f"isinstance CategoryType: {isinstance(type_in_dump, CategoryType)}")


if __name__ == "__main__":
    # Run the specific test
    pytest.main([__file__, "-v"])

