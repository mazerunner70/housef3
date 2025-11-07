"""
Serialization and deserialization utility functions for models.

This module contains helper functions for converting between different data formats
and types, particularly for use with Pydantic models and DynamoDB.

Naming Conventions:
- to_X: Convert TO a type (e.g., to_currency, to_db_id)
- from_X: Convert FROM a type (e.g., from_db_id, from_dynamodb_item)
"""
from typing import Any, Optional
from models.money import Currency


def to_currency(value: Any) -> Optional[Currency]:
    """
    Convert input value to Currency enum.
    
    Accepts string currency codes, Currency enum objects, or None.
    Use this for API input handling before creating model instances.
    
    Args:
        value: String currency code, Currency enum, or None
        
    Returns:
        Currency enum or None
        
    Raises:
        ValueError: If value is invalid or not a supported currency
        
    Examples:
        >>> to_currency("USD")
        <Currency.USD: 'USD'>
        
        >>> to_currency(Currency.EUR)
        <Currency.EUR: 'EUR'>
        
        >>> to_currency(None)
        None
        
        >>> to_currency("INVALID")
        ValueError: Invalid currency value: 'INVALID'. Valid options are: USD, EUR, GBP, CAD, JPY, AUD, CHF, CNY, other
    """
    if value is None:
        return None
    if isinstance(value, Currency):
        return value
    if isinstance(value, str):
        try:
            return Currency(value)
        except ValueError:
            raise ValueError(
                f"Invalid currency value: '{value}'. "
                f"Valid options are: {', '.join([c.value for c in Currency])}"
            )
    raise ValueError(
        f"Currency must be a string or Currency enum, "
        f"got {type(value).__name__}: {value}"
    )

